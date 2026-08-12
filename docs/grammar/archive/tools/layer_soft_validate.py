"""Soft-validate MemNetLayer (proposed 1.x) after ANTLR parse.

Hung off ``docs/grammar/antlr`` generated Python + ``antlr4-python3-runtime``.
Does **not** patch the 0.3 engine / ``memnet.tier_a``.

Rules (mission freeze — ``memnet-multi-layer.md``):
1. Both EDGE ends same grain (port↔port or bare↔bare).
2. No ``law=`` on EDGE.
3. Bag denylist on dialect keys ``law`` / ``pseudo`` / ``recycle`` / ``role`` / ``view``.
4. ``@ident`` inside ``LAW_SEG`` ⊆ bag ``ALIAS_REF`` aliases on that NODE.
"""

from __future__ import annotations

import re
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Iterator

from antlr4 import CommonTokenStream, InputStream
from antlr4.error.ErrorListener import ErrorListener

ANTLR_DIR = Path(__file__).resolve().parents[1] / "antlr"
GENERATED_DIR = ANTLR_DIR / "generated"

if str(GENERATED_DIR) not in sys.path:
    sys.path.insert(0, str(GENERATED_DIR))

from MemNetLayerLexer import MemNetLayerLexer  # noqa: E402
from MemNetLayerParser import MemNetLayerParser  # noqa: E402

BAG_DENYLIST = frozenset({"law", "pseudo", "recycle", "role", "view"})
_ALIAS_IN_LAW = re.compile(r"@([A-Za-z_][A-Za-z0-9_]*)")
_EXPECT_RE = re.compile(r"^#\s*expect:\s*(\S+)", re.I)


@dataclass(frozen=True)
class LintIssue:
    severity: str  # error | warning
    code: str
    message: str


@dataclass
class FieldRec:
    key: str
    is_bag: bool = False
    law_segs: list[str] = field(default_factory=list)
    aliases: set[str] = field(default_factory=set)


@dataclass
class NodeRec:
    kind: str
    node_id: str
    fields: list[FieldRec] = field(default_factory=list)
    line: int = 0


@dataclass
class EdgeRec:
    edge_id: str | None
    frm_port: bool
    to_port: bool
    frm_text: str
    to_text: str
    label: str
    fields: list[FieldRec] = field(default_factory=list)
    line: int = 0


@dataclass
class Document:
    nodes: list[NodeRec] = field(default_factory=list)
    edges: list[EdgeRec] = field(default_factory=list)
    raw: str = ""


class ParseError(ValueError):
    """MemNetLayer syntax / recovery failure."""


class _Collect(ErrorListener):
    def __init__(self) -> None:
        super().__init__()
        self.errors: list[str] = []

    def syntaxError(self, recognizer, offendingSymbol, line, column, msg, e):  # noqa: N802
        self.errors.append(f"line {line}:{column} {msg}")


def expect_from_text(text: str) -> str | None:
    """Read ``# expect: parse-ok|parse-reject|lint-reject`` from fixture header."""
    for line in text.splitlines()[:8]:
        m = _EXPECT_RE.match(line.strip())
        if m:
            return m.group(1).lower()
    return None


def parse(text: str) -> Document:
    """Parse shared-dialect layer lines; raise ``ParseError`` on syntax errors."""
    lexer = MemNetLayerLexer(InputStream(text))
    stream = CommonTokenStream(lexer)
    parser = MemNetLayerParser(stream)
    sink = _Collect()
    parser.removeErrorListeners()
    parser.addErrorListener(sink)
    tree = parser.document()
    if sink.errors or parser.getNumberOfSyntaxErrors():
        detail = "; ".join(sink.errors) or f"{parser.getNumberOfSyntaxErrors()} syntax error(s)"
        raise ParseError(detail)
    doc = _extract(tree)
    doc.raw = text
    return doc


def soft_validate(doc: Document) -> list[LintIssue]:
    """Return soft lint issues (severity error/warning)."""
    issues: list[LintIssue] = []
    for edge in doc.edges:
        if edge.frm_port != edge.to_port:
            issues.append(
                LintIssue(
                    "error",
                    "mixed_endpoints",
                    f"mixed endpoint grains {edge.frm_text!r} ↔ {edge.to_text!r}",
                )
            )
        for f in edge.fields:
            if f.key == "law":
                issues.append(
                    LintIssue(
                        "error",
                        "law_on_edge",
                        "law= forbidden on EDGE; put law on NODE",
                    )
                )
            if f.key in BAG_DENYLIST and f.is_bag:
                issues.append(
                    LintIssue(
                        "error",
                        "bag_denylist",
                        f"{f.key}= must not be a brace-group / bag",
                    )
                )
    for node in doc.nodes:
        aliases = set()
        for f in node.fields:
            aliases |= f.aliases
            if f.key in BAG_DENYLIST and f.is_bag:
                issues.append(
                    LintIssue(
                        "error",
                        "bag_denylist",
                        f"{f.key}= must not be a brace-group / bag",
                    )
                )
        for f in node.fields:
            if f.key != "law":
                continue
            for seg in f.law_segs:
                for m in _ALIAS_IN_LAW.finditer(seg):
                    name = m.group(1)
                    if name not in aliases:
                        issues.append(
                            LintIssue(
                                "error",
                                "orphan_law_alias",
                                f"@{name} in law= not declared as bag alias on [{node.node_id}]",
                            )
                        )
    return _dedupe(issues)


def lint(doc: Document) -> list[LintIssue]:
    """Alias for ``soft_validate`` (golden harness naming parity with tier_a)."""
    return soft_validate(doc)


def _dedupe(issues: list[LintIssue]) -> list[LintIssue]:
    seen: set[tuple[str, str]] = set()
    out: list[LintIssue] = []
    for i in issues:
        key = (i.code, i.message)
        if key in seen:
            continue
        seen.add(key)
        out.append(i)
    return out


def _extract(tree: MemNetLayerParser.DocumentContext) -> Document:
    doc = Document()
    for line_ctx in tree.line():
        if isinstance(line_ctx, MemNetLayerParser.PresentNodeLineContext):
            doc.nodes.append(_node_from(line_ctx.presentNode(), kind_from="present"))
        elif isinstance(line_ctx, MemNetLayerParser.CreateNodeLineContext):
            doc.nodes.append(_node_from(line_ctx.createNode(), kind_from="create"))
        elif isinstance(line_ctx, MemNetLayerParser.PatchNodeLineContext):
            doc.nodes.append(_node_from(line_ctx.patchNode(), kind_from="patch"))
        elif isinstance(line_ctx, MemNetLayerParser.PresentEdgeLineContext):
            doc.edges.append(_edge_from(line_ctx.presentEdge()))
        elif isinstance(line_ctx, MemNetLayerParser.CreateEdgeLineContext):
            doc.edges.append(_edge_from(line_ctx.createEdge()))
        elif isinstance(line_ctx, MemNetLayerParser.PatchEdgeLineContext):
            pe = line_ctx.patchEdge()
            # ~ Eid ; fields  — no endpoints; skip grain checks
            if pe.endpoint() and len(pe.endpoint()) >= 2:
                doc.edges.append(_edge_from(pe))
        # dropEdge: no soft rules in this slice
    return doc


def _node_from(ctx, *, kind_from: str) -> NodeRec:
    if kind_from == "present":
        kind = ctx.IDENT(0).getText()
        node_id = ctx.IDENT(1).getText()
        fields = [_field_from(f) for f in ctx.field()]
        line = ctx.start.line if ctx.start else 0
    elif kind_from == "create":
        kind = ctx.IDENT().getText()
        node_id = ctx.idAtom().getText()
        fields = [_field_from(f) for f in ctx.field()]
        line = ctx.start.line if ctx.start else 0
    else:  # patch
        kind = ""
        node_id = ctx.IDENT().getText()
        fields = [_field_from(f) for f in ctx.field()]
        line = ctx.start.line if ctx.start else 0
    return NodeRec(kind=kind, node_id=node_id, fields=fields, line=line)


def _edge_from(ctx) -> EdgeRec:
    endpoints = ctx.endpoint()
    frm = endpoints[0]
    to = endpoints[1]
    frm_port, frm_text = _endpoint_info(frm)
    to_port, to_text = _endpoint_info(to)
    edge_id = None
    if hasattr(ctx, "IDENT") and ctx.IDENT() and not isinstance(
        ctx, MemNetLayerParser.CreateEdgeContext
    ):
        # presentEdge: first IDENT is edge id
        if isinstance(ctx, MemNetLayerParser.PresentEdgeContext):
            edge_id = ctx.IDENT().getText()
    if isinstance(ctx, MemNetLayerParser.CreateEdgeContext):
        eia = ctx.edgeIdAtom()
        if eia is not None:
            edge_id = eia.getText()
    if isinstance(ctx, MemNetLayerParser.PatchEdgeContext) and ctx.IDENT() and not endpoints:
        edge_id = ctx.IDENT().getText()
    label = _wire_label(ctx.edgeWire())
    fields = [_field_from(f) for f in ctx.field()]
    line = ctx.start.line if ctx.start else 0
    return EdgeRec(
        edge_id=edge_id,
        frm_port=frm_port,
        to_port=to_port,
        frm_text=frm_text,
        to_text=to_text,
        label=label,
        fields=fields,
        line=line,
    )


def _endpoint_info(ep: MemNetLayerParser.EndpointContext) -> tuple[bool, str]:
    atom = ep.endpointAtom()
    text = atom.getText()
    is_port = atom.DOT() is not None
    return is_port, f"[{text}]"


def _wire_label(wire: MemNetLayerParser.EdgeWireContext) -> str:
    # WireDirected / WireNonDirected / WireBiDirected
    child = wire.getChild(0)
    if hasattr(child, "IDENT") and child.IDENT():
        return child.IDENT().getText()
    return wire.getText()


def _field_from(fctx: MemNetLayerParser.FieldContext) -> FieldRec:
    key = fctx.IDENT().getText()
    # += / -= forms have no fieldValue
    if fctx.PLUS_EQ() or fctx.MINUS_EQ():
        return FieldRec(key=key)
    fv = fctx.fieldValue()
    is_bag = isinstance(fv, MemNetLayerParser.ValueRecordContext)
    law_segs: list[str] = []
    aliases: set[str] = set()
    if isinstance(fv, MemNetLayerParser.ValueLawListContext):
        law_segs = [seg.getText() for seg in fv.lawList().LAW_SEG()]
    elif isinstance(fv, MemNetLayerParser.ValueStringContext):
        # quoted whole-field law — still scan for @ident
        raw = fv.STRING().getText()
        if key == "law":
            law_segs = [raw]
    if isinstance(fv, MemNetLayerParser.ValuePortListContext):
        aliases |= _aliases_from_ports(fv.portList())
    # Also collect aliases from any bag attrs (instance meta etc.) — primary is ports=
    aliases |= _aliases_under(fv)
    return FieldRec(key=key, is_bag=is_bag, law_segs=law_segs, aliases=aliases)


def _aliases_from_ports(port_list: MemNetLayerParser.PortListContext) -> set[str]:
    found: set[str] = set()
    for pt in port_list.portToken():
        attrs = pt.attrList()
        if attrs is None:
            continue
        for attr in attrs.attr():
            found |= _aliases_from_attr_value(attr.attrValue())
    return found


def _aliases_under(ctx) -> set[str]:
    """Walk a fieldValue subtree for ALIAS_REF tokens (ports / nested bags)."""
    from antlr4.tree.Tree import TerminalNode

    found: set[str] = set()
    if ctx is None:
        return found

    def walk(node) -> Iterator:
        if node is None:
            return
        if isinstance(node, TerminalNode):
            yield node
            return
        for i in range(node.getChildCount()):
            yield from walk(node.getChild(i))

    for term in walk(ctx):
        sym = term.getSymbol()
        if sym.type == MemNetLayerLexer.ALIAS_REF:
            text = term.getText()
            if text.startswith("@"):
                found.add(text[1:])
    return found


def _aliases_from_attr_value(av: MemNetLayerParser.AttrValueContext) -> set[str]:
    return _aliases_under(av)


def iter_layer_fixtures(examples_dir: Path) -> Iterator[Path]:
    """Yield ``layer_*.txt`` under ``examples/`` or ``examples/layer/``."""
    direct = sorted(examples_dir.glob("layer_*.txt"))
    nested = sorted((examples_dir / "layer").glob("layer_*.txt")) if (examples_dir / "layer").is_dir() else []
    yield from nested if nested else direct
