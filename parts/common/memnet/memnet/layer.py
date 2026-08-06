"""MemNet Layer (proposed 1.x) codec — dual EDGE + structured ports=/law=.

Additive to 0.3.x ``tier_a``: same NODE|EDGE store; Layer wire forms and fields
coexist via optional ``src_port`` / ``dist_port`` / ``wire`` on EDG and opaque
``ports`` / ``law`` strings on NODE. Does **not** require antlr4 at runtime
(hand-rolled mirror of ``MemNetLayer.g4`` + soft rules from
``docs/grammar/tools/layer_soft_validate.py``).

Mission freeze: law on NODE; port↔port = bind; node↔node = relation; reject mixed.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Iterator, Literal

from memnet.tier_a import Field, Op

BAG_DENYLIST = frozenset({"law", "pseudo", "recycle", "role", "view"})
_ALIAS_IN_LAW = re.compile(r"@([A-Za-z_][A-Za-z0-9_]*)")
_ALIAS_REF = re.compile(r"@([A-Za-z_][A-Za-z0-9_]*)")
_IDENT = r"[A-Za-z_][A-Za-z0-9_]*"
_KIND = r"[A-Z][A-Z0-9_]*"

WireForm = Literal["directed", "non_directed", "bi_directed"]
Grain = Literal["bind", "relation"]


class ParseError(Exception):
    def __init__(self, message: str, line: int | None = None) -> None:
        super().__init__(message)
        self.line = line


@dataclass(frozen=True)
class LintIssue:
    severity: str  # error | warning
    code: str
    message: str
    line: int | None = None


@dataclass
class Endpoint:
    node_id: str
    port: str | None = None  # None = bare node grain

    @property
    def is_port(self) -> bool:
        return self.port is not None

    def wire_text(self) -> str:
        if self.port:
            return f"[{self.node_id}.{self.port}]"
        return f"[{self.node_id}]"


@dataclass
class LayerNodeRec:
    op: Op
    kind: str
    id: str
    fields: list[Field] = field(default_factory=list)
    raw: str = ""
    line: int = 0


@dataclass
class LayerEdgeRec:
    op: Op
    edge_id: str | None
    frm: Endpoint
    to: Endpoint
    rel: str
    wire: WireForm = "directed"
    fields: list[Field] = field(default_factory=list)
    raw: str = ""
    line: int = 0

    @property
    def grain(self) -> Grain:
        return "bind" if self.frm.is_port and self.to.is_port else "relation"


@dataclass
class Document:
    items: list[LayerNodeRec | LayerEdgeRec] = field(default_factory=list)
    raw: str = ""


def looks_like_layer(line: str) -> bool:
    """True when a non-empty line uses Layer wire / structured ports or law.

    Deliberately narrow so Tier A ``+ KIND [Id]`` batches stay on the 0.3 path
    unless Layer markers (ports=/law=/bare edge wire/CST/bare present) appear.
    """
    s = line.strip().lstrip("\ufeff")
    if not s or s.startswith("#") or s.startswith("@"):
        return False
    if s.startswith("##") or s.upper().startswith("SCHEMA"):
        return False
    # Tier A paren label — not Layer
    if re.search(r"--\([a-z][a-z0-9_]*\)-->", s):
        return False
    # Layer edge: ] --label--> [  /  ] --label-- [  /  ] <--label--> [
    if re.search(
        rf"\]\s*(?:<--|--)\s*{_IDENT}\s*(?:-->|--)\s*\[",
        s,
    ):
        return True
    if re.search(rf"\bports\s*=", s, re.I) and re.search(r":\s*\{", s):
        return True
    if re.search(rf"\blaw\s*=\s*\$", s, re.I):
        return True
    if re.search(rf"\blaw\s*=\s*\{{", s, re.I):
        return True  # bag-on-law (lint later)
    # Bare present KIND [Id] — Layer seed / fixture ingest (ops are mutate-only)
    if re.match(rf"^{_KIND}\s+\[", s):
        return True
    # Explicit CST create (Layer law-leaf kind)
    if re.match(rf"^\+\s+CST\s+\[", s):
        return True
    return False


def parse(text: str) -> Document:
    """Parse Layer shared-dialect lines; raise ``ParseError`` on syntax errors."""
    doc = Document(raw=text)
    for line_no, raw in enumerate(text.splitlines(), start=1):
        s = raw.strip()
        if not s or s.startswith("#"):
            continue
        item = parse_line(s, line_no)
        doc.items.append(item)
    return doc


def parse_line(line: str, line_no: int = 1) -> LayerNodeRec | LayerEdgeRec:
    s = line.strip()
    if not s:
        raise ParseError("empty line", line_no)

    if s.startswith("-") and not s.startswith("--") and not s.startswith("<--"):
        m = re.match(rf"^-\s+({_IDENT})\s*$", s)
        if not m:
            raise ParseError(f"bad drop: {s!r}", line_no)
        return LayerEdgeRec(
            op=Op.DROP,
            edge_id=m.group(1),
            frm=Endpoint(""),
            to=Endpoint(""),
            rel="",
            raw=s,
            line=line_no,
        )

    # Patch node: ~ [Id] ; …
    m = re.match(rf"^~\s+\[({_IDENT})\]\s*(.*)$", s)
    if m and "--" not in s and "<--" not in s:
        fields = _parse_fields(m.group(2), line_no)
        return LayerNodeRec(
            op=Op.PATCH, kind="", id=m.group(1), fields=fields, raw=s, line=line_no
        )

    # Patch edge bare: ~ Eid ; …  (no endpoints)
    m = re.match(rf"^~\s+({_IDENT})\s*(;.*)?$", s)
    if m and "--" not in s and "<--" not in s:
        fields = _parse_fields(m.group(2) or "", line_no)
        return LayerEdgeRec(
            op=Op.PATCH,
            edge_id=m.group(1),
            frm=Endpoint(""),
            to=Endpoint(""),
            rel="",
            fields=fields,
            raw=s,
            line=line_no,
        )

    edge = _try_parse_edge(s, line_no)
    if edge is not None:
        return edge

    node = _try_parse_node(s, line_no)
    if node is not None:
        return node

    raise ParseError(f"unrecognised Layer line: {s[:80]}", line_no)


def _try_parse_node(s: str, line_no: int) -> LayerNodeRec | None:
    m = re.match(rf"^\+\s+({_KIND})\s+\[(NEW|{_IDENT})\]\s*(.*)$", s)
    if m:
        return LayerNodeRec(
            op=Op.CREATE,
            kind=m.group(1),
            id=m.group(2),
            fields=_parse_fields(m.group(3), line_no),
            raw=s,
            line=line_no,
        )
    m = re.match(rf"^({_KIND})\s+\[({_IDENT})\]\s*(.*)$", s)
    if m:
        return LayerNodeRec(
            op=Op.PRESENT,
            kind=m.group(1),
            id=m.group(2),
            fields=_parse_fields(m.group(3), line_no),
            raw=s,
            line=line_no,
        )
    return None


_RE_EDGE_CORE = re.compile(
    rf"^(?P<head>.*?)\[(?P<frm>{_IDENT}(?:\.{_IDENT})?)\]\s*"
    rf"(?P<wire><--(?P<bi>{_IDENT})-->|--(?P<label>{_IDENT})(?P<tail>-->|--))\s*"
    rf"\[(?P<to>{_IDENT}(?:\.{_IDENT})?)\]\s*(?P<rest>.*)$"
)


def _try_parse_edge(s: str, line_no: int) -> LayerEdgeRec | None:
    m = _RE_EDGE_CORE.match(s)
    if not m:
        return None
    head = m.group("head").strip()
    label = m.group("bi") or m.group("label")
    if m.group("bi"):
        wire: WireForm = "bi_directed"
    elif m.group("tail") == "-->":
        wire = "directed"
    else:
        wire = "non_directed"
    frm = _endpoint(m.group("frm"))
    to = _endpoint(m.group("to"))
    fields = _parse_fields(m.group("rest"), line_no)
    op = Op.PRESENT
    edge_id: str | None = None
    if head.startswith("+"):
        op = Op.CREATE
        rest_head = head[1:].strip()
        if rest_head in ("NEW",) or (rest_head and re.fullmatch(_IDENT, rest_head)):
            edge_id = rest_head
        elif rest_head:
            raise ParseError(f"bad create edge head: {head!r}", line_no)
    elif head.startswith("~"):
        op = Op.PATCH
        rest_head = head[1:].strip()
        if rest_head and re.fullmatch(_IDENT, rest_head):
            edge_id = rest_head
        elif rest_head:
            raise ParseError(f"bad patch edge head: {head!r}", line_no)
    elif head:
        if not re.fullmatch(_IDENT, head):
            raise ParseError(f"bad present edge id: {head!r}", line_no)
        edge_id = head
        op = Op.PRESENT
    return LayerEdgeRec(
        op=op,
        edge_id=edge_id,
        frm=frm,
        to=to,
        rel=label,
        wire=wire,
        fields=fields,
        raw=s,
        line=line_no,
    )


def _endpoint(text: str) -> Endpoint:
    if "." in text:
        node, port = text.split(".", 1)
        return Endpoint(node_id=node, port=port)
    return Endpoint(node_id=text, port=None)


def _parse_fields(tail: str, line_no: int) -> list[Field]:
    tail = tail.strip()
    if not tail:
        return []
    if tail.startswith(";"):
        tail = tail[1:].strip()
    fields: list[Field] = []
    for part in _split_top_fields(tail):
        part = part.strip()
        if not part:
            continue
        m = re.match(rf"^({_IDENT})\s*(\+=|-=|=)\s*(.*)$", part, re.DOTALL)
        if not m:
            raise ParseError(f"bad field: {part!r}", line_no)
        key, op, raw_val = m.group(1), m.group(2), m.group(3).strip()
        if op in ("+=", "-="):
            if not re.fullmatch(r"[0-9]+(?:\.[0-9]+)?", raw_val):
                raise ParseError(f"{op} requires number, got {raw_val!r}", line_no)
            fields.append(Field(key=key, op=op, value=raw_val))
            continue
        _check_brace_depth(raw_val, line_no)
        fields.append(Field(key=key, op="=", value=_normalize_field_value(raw_val, line_no)))
    return fields


def _split_top_fields(s: str) -> list[str]:
    """Split on ';' outside quotes, braces, and $…$ law segments."""
    parts: list[str] = []
    buf: list[str] = []
    i = 0
    depth = 0
    in_str = False
    in_law = False
    while i < len(s):
        ch = s[i]
        if in_str:
            buf.append(ch)
            if ch == "\\" and i + 1 < len(s):
                buf.append(s[i + 1])
                i += 2
                continue
            if ch == '"':
                in_str = False
            i += 1
            continue
        if in_law:
            buf.append(ch)
            if ch == "$":
                in_law = False
            i += 1
            continue
        if ch == '"':
            in_str = True
            buf.append(ch)
            i += 1
            continue
        if ch == "$":
            in_law = True
            buf.append(ch)
            i += 1
            continue
        if ch == "{":
            depth += 1
            buf.append(ch)
            i += 1
            continue
        if ch == "}":
            depth = max(0, depth - 1)
            buf.append(ch)
            i += 1
            continue
        if ch == ";" and depth == 0:
            parts.append("".join(buf))
            buf = []
            i += 1
            continue
        buf.append(ch)
        i += 1
    parts.append("".join(buf))
    return parts


def _check_brace_depth(value: str, line_no: int) -> None:
    depth = 0
    in_str = False
    in_law = False
    i = 0
    while i < len(value):
        ch = value[i]
        if in_str:
            if ch == "\\" and i + 1 < len(value):
                i += 2
                continue
            if ch == '"':
                in_str = False
            i += 1
            continue
        if in_law:
            if ch == "$":
                in_law = False
            i += 1
            continue
        if ch == '"':
            in_str = True
            i += 1
            continue
        if ch == "$":
            in_law = True
            i += 1
            continue
        if ch == "{":
            depth += 1
            if depth > 2:
                raise ParseError("brace-group nesting depth exceeds 2", line_no)
            i += 1
            continue
        if ch == "}":
            depth = max(0, depth - 1)
            i += 1
            continue
        i += 1


def _normalize_field_value(raw: str, line_no: int) -> str:
    raw = raw.strip()
    if not raw:
        raise ParseError("empty field value", line_no)
    if raw.startswith('"') and raw.endswith('"') and len(raw) >= 2:
        return _unescape_string(raw[1:-1])
    return raw


def _unescape_string(body: str) -> str:
    out: list[str] = []
    i = 0
    while i < len(body):
        if body[i] == "\\" and i + 1 < len(body):
            nxt = body[i + 1]
            mapping = {"\\": "\\", '"': '"', "n": "\n", "r": "\r", "t": "\t"}
            if nxt not in mapping:
                raise ParseError(f"unknown string escape \\{nxt}")
            out.append(mapping[nxt])
            i += 2
            continue
        out.append(body[i])
        i += 1
    return "".join(out)


def _escape_string(s: str) -> str:
    return (
        s.replace("\\", "\\\\")
        .replace('"', '\\"')
        .replace("\n", "\\n")
        .replace("\r", "\\r")
        .replace("\t", "\\t")
    )


def _value_is_bag(value: str) -> bool:
    v = value.strip()
    return v.startswith("{") and v.endswith("}")


def _aliases_in_value(value: str) -> set[str]:
    return {m.group(1) for m in _ALIAS_REF.finditer(value)}


def soft_validate(doc: Document) -> list[LintIssue]:
    """Soft lint: dual EDGE grain, no law on EDGE, bag denylist, carries, aliases."""
    issues: list[LintIssue] = []
    for it in doc.items:
        if isinstance(it, LayerEdgeRec):
            if it.op == Op.DROP:
                continue
            if it.frm.node_id and it.to.node_id:
                if it.frm.is_port != it.to.is_port:
                    issues.append(
                        LintIssue(
                            "error",
                            "mixed_endpoints",
                            f"mixed endpoint grains {it.frm.wire_text()} ↔ {it.to.wire_text()}",
                            it.line,
                        )
                    )
            rel = it.rel
            if rel == "pipe":
                # accept-only; emit will normalise to bind
                pass
            for f in it.fields:
                if f.key == "law":
                    issues.append(
                        LintIssue(
                            "error",
                            "law_on_edge",
                            "law= forbidden on EDGE; put law on NODE",
                            it.line,
                        )
                    )
                if f.key in BAG_DENYLIST and _value_is_bag(f.value):
                    issues.append(
                        LintIssue(
                            "error",
                            "bag_denylist",
                            f"{f.key}= must not be a brace-group / bag",
                            it.line,
                        )
                    )
                if f.key == "carries" and not (
                    it.frm.is_port and it.to.is_port
                ):
                    issues.append(
                        LintIssue(
                            "error",
                            "carries_on_relation",
                            "carries= allowed on bind (port↔port) only",
                            it.line,
                        )
                    )
                if f.key == "carries" and f.value == "member":
                    issues.append(
                        LintIssue(
                            "error",
                            "carries_member",
                            "carries=member forbidden; use node↔node membership relation",
                            it.line,
                        )
                    )
        elif isinstance(it, LayerNodeRec):
            aliases: set[str] = set()
            for f in it.fields:
                if f.key == "ports" or _value_is_bag(f.value):
                    aliases |= _aliases_in_value(f.value)
                if f.key in BAG_DENYLIST and _value_is_bag(f.value):
                    issues.append(
                        LintIssue(
                            "error",
                            "bag_denylist",
                            f"{f.key}= must not be a brace-group / bag",
                            it.line,
                        )
                    )
            for f in it.fields:
                if f.key != "law":
                    continue
                for seg in _law_segments(f.value):
                    for m in _ALIAS_IN_LAW.finditer(seg):
                        name = m.group(1)
                        if name not in aliases:
                            issues.append(
                                LintIssue(
                                    "error",
                                    "orphan_law_alias",
                                    f"@{name} in law= not declared as bag alias on [{it.id}]",
                                    it.line,
                                )
                            )
    return _dedupe(issues)


def lint(doc: Document) -> list[LintIssue]:
    return soft_validate(doc)


def _law_segments(value: str) -> list[str]:
    v = value.strip()
    if v.startswith('"'):
        return [v]
    return re.findall(r"\$[^$]*\$", v) or ([v] if v else [])


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


def emit_item(item: LayerNodeRec | LayerEdgeRec) -> str:
    if isinstance(item, LayerNodeRec):
        if item.op == Op.PRESENT:
            head = f"{item.kind} [{item.id}]"
        elif item.op == Op.CREATE:
            head = f"+ {item.kind} [{item.id}]"
        else:
            head = f"~ [{item.id}]"
        fields = _format_fields(item.fields)
        return f"{head} ; {fields}" if fields else head

    assert isinstance(item, LayerEdgeRec)
    if item.op == Op.DROP:
        return f"- {item.edge_id}"
    if item.op == Op.PATCH and not item.frm.node_id:
        head = f"~ {item.edge_id}"
        fields = _format_fields(item.fields)
        return f"{head} ; {fields}" if fields else head

    rel = "bind" if item.rel == "pipe" else item.rel
    wire = _format_wire(rel, item.wire)
    if item.op == Op.PRESENT:
        head = f"{item.edge_id} {item.frm.wire_text()} {wire} {item.to.wire_text()}"
    else:
        op = "+" if item.op == Op.CREATE else "~"
        if item.edge_id:
            head = f"{op} {item.edge_id} {item.frm.wire_text()} {wire} {item.to.wire_text()}"
        else:
            head = f"{op} {item.frm.wire_text()} {wire} {item.to.wire_text()}"
    # Omit default recycle on Layer emit
    fields = _format_fields(
        [f for f in item.fields if not (f.key == "recycle" and f.value == "persistent")]
    )
    return f"{head} ; {fields}" if fields else head


def _format_wire(rel: str, wire: WireForm) -> str:
    if wire == "bi_directed":
        return f"<--{rel}-->"
    if wire == "non_directed":
        return f"--{rel}--"
    return f"--{rel}-->"


def _format_fields(fields: list[Field]) -> str:
    bits: list[str] = []
    for f in fields:
        if f.op in ("+=", "-="):
            bits.append(f"{f.key}{f.op}{f.value}")
            continue
        # Prefer raw Layer values (ports=/law= already structured); quote if needed
        if _needs_quote(f.value):
            bits.append(f'{f.key}="{_escape_string(f.value)}"')
        else:
            bits.append(f"{f.key}={f.value}")
    return " ; ".join(bits)


def _needs_quote(value: str) -> bool:
    if not value:
        return True
    if value.startswith("{") or value.startswith("$") or ": {" in value:
        return False
    if any(c in value for c in ";"):
        return True
    return False


def emit(doc: Document) -> str:
    lines = [emit_item(it) for it in doc.items]
    return "\n".join(lines) + ("\n" if lines else "")


def round_trip_present(text: str) -> bool:
    """Parse → emit → parse; compare structural present lines (ignore comments)."""
    doc = parse(text)
    errors = [i for i in soft_validate(doc) if i.severity == "error"]
    if errors:
        return False
    # Normalise PRESENT for round-trip compare
    emitted = emit(doc)
    doc2 = parse(emitted)
    return _structural_eq(doc, doc2)


def _structural_eq(a: Document, b: Document) -> bool:
    if len(a.items) != len(b.items):
        return False
    for x, y in zip(a.items, b.items, strict=True):
        if type(x) is not type(y):
            return False
        if isinstance(x, LayerNodeRec) and isinstance(y, LayerNodeRec):
            if (x.kind, x.id, _fields_dict(x.fields)) != (
                y.kind,
                y.id,
                _fields_dict(y.fields),
            ):
                return False
        elif isinstance(x, LayerEdgeRec) and isinstance(y, LayerEdgeRec):
            xr = "bind" if x.rel == "pipe" else x.rel
            yr = "bind" if y.rel == "pipe" else y.rel
            if (
                x.edge_id,
                x.frm,
                x.to,
                xr,
                x.wire,
                _fields_dict(x.fields),
            ) != (
                y.edge_id,
                y.frm,
                y.to,
                yr,
                y.wire,
                _fields_dict(y.fields),
            ):
                return False
    return True


def _fields_dict(fields: list[Field]) -> dict[str, str]:
    return {f.key: f.value for f in fields if f.op == "="}


# --- Store projection helpers -------------------------------------------------

LAYER_CST_FIELDS = ["id", "name", "role", "ports", "law", "pseudo", "recycle"]
LAYER_EDG_EXTRA = ("src_port", "dist_port", "wire")


def ensure_layer_schema(tag_map) -> None:
    """Register CST (open Layer law leaf) when missing — additive, no overwrite."""
    from memnet.models import TagDef

    if tag_map.get("CST") is None:
        tag_map.tags["CST"] = TagDef(tag="CST", fields=list(LAYER_CST_FIELDS), kind="node")


def node_to_fields(node: LayerNodeRec) -> dict[str, str]:
    fields: dict[str, str] = {"id": node.id}
    for f in node.fields:
        if f.op == "=":
            fields[f.key] = f.value
    return fields


def edge_to_store_fields(edge: LayerEdgeRec) -> dict[str, str]:
    """Project Layer EDGE to store fields (bare src/dist + optional ports).

    ``src_port`` / ``dist_port`` / ``wire`` / ``carries`` are free Record fields
    (not in fixed EDG TagDef) so 0.3 pipe ``@EDG:`` positional arity stays 7.
    """
    rel = "bind" if edge.rel == "pipe" else edge.rel
    fields: dict[str, str] = {
        "id": edge.edge_id or "",
        "src": edge.frm.node_id,
        "relation": rel,
        "dist": edge.to.node_id,
        "at": "",
        "attrs": "",
        "recycle": "persistent",
    }
    if edge.frm.port:
        fields["src_port"] = edge.frm.port
    if edge.to.port:
        fields["dist_port"] = edge.to.port
    fields["wire"] = edge.wire
    for f in edge.fields:
        if f.key in ("src", "relation", "dist", "at", "attrs", "recycle"):
            fields[f.key] = f.value
        elif f.key in ("src_port", "dist_port", "wire", "carries"):
            fields[f.key] = f.value
        elif f.key == "note":
            fields["attrs"] = f.value
        else:
            if fields["attrs"]:
                fields["attrs"] = f"{fields['attrs']};{f.key}={f.value}"
            else:
                fields["attrs"] = f"{f.key}={f.value}"
    return fields


def mint_layer_document(doc: Document, existing_ids: set[str]):
    """Mint NEW / missing edge ids on a Layer document (parallel to IdAllocator)."""
    from memnet.id_allocator import AssignedIdMap, IdAllocator

    alloc = IdAllocator(existing_ids)
    assigned = AssignedIdMap()
    for it in doc.items:
        if isinstance(it, LayerNodeRec) and it.id != "NEW":
            alloc.observe(it.id)
        elif isinstance(it, LayerEdgeRec):
            if it.edge_id and it.edge_id != "NEW":
                alloc.observe(it.edge_id)
            if it.frm.node_id and it.frm.node_id != "NEW":
                alloc.observe(it.frm.node_id)
            if it.to.node_id and it.to.node_id != "NEW":
                alloc.observe(it.to.node_id)

    new_node_i = 0
    new_edge_i = 0
    for it in doc.items:
        if isinstance(it, LayerNodeRec) and it.op in (Op.CREATE, Op.PRESENT) and it.id == "NEW":
            rid = alloc.mint(it.kind if it.kind else "N")
            assigned.mapping[f"NEW_node_{new_node_i}"] = rid
            new_node_i += 1
            it.id = rid
        elif isinstance(it, LayerEdgeRec) and it.op in (Op.CREATE, Op.PRESENT):
            if it.edge_id == "NEW" or it.edge_id is None:
                rid = alloc.mint("E")
                assigned.mapping[f"NEW_edge_{new_edge_i}"] = rid
                new_edge_i += 1
                it.edge_id = rid
            if it.frm.node_id == "NEW":
                it.frm = Endpoint(alloc.mint("N"), it.frm.port)
            if it.to.node_id == "NEW":
                it.to = Endpoint(alloc.mint("N"), it.to.port)
    return assigned


def record_to_layer_node(rec) -> LayerNodeRec:
    from memnet.models import Record

    assert isinstance(rec, Record)
    fields = [
        Field(key=k, op="=", value=v)
        for k, v in rec.fields.items()
        if k != "id" and v and not (k == "recycle" and v == "persistent")
    ]
    return LayerNodeRec(op=Op.PRESENT, kind=rec.tag, id=rec.id, fields=fields)


def record_to_layer_edge(rec) -> LayerEdgeRec:
    from memnet.models import Record

    assert isinstance(rec, Record)
    src_port = rec.fields.get("src_port") or None
    dist_port = rec.fields.get("dist_port") or None
    if src_port == "":
        src_port = None
    if dist_port == "":
        dist_port = None
    wire_raw = rec.fields.get("wire") or "directed"
    wire: WireForm = (
        wire_raw
        if wire_raw in ("directed", "non_directed", "bi_directed")
        else "directed"
    )
    skip = {"id", "src", "relation", "dist", "src_port", "dist_port", "wire", "at"}
    fields: list[Field] = []
    for k, v in rec.fields.items():
        if k in skip or not v:
            continue
        if k == "recycle" and v == "persistent":
            continue
        if k == "attrs":
            # Prefer structured carries= if present as own field
            continue
        fields.append(Field(key=k, op="=", value=v))
    carries = rec.fields.get("carries")
    if carries:
        fields.insert(0, Field(key="carries", op="=", value=carries))
    elif rec.fields.get("attrs", "").startswith("carries="):
        # legacy stash
        pass
    # Unpack attrs lightly for carries=
    attrs = rec.fields.get("attrs", "")
    if attrs and "carries=" in attrs and not carries:
        for part in attrs.split(";"):
            part = part.strip()
            if part.startswith("carries="):
                fields.append(Field(key="carries", op="=", value=part.split("=", 1)[1]))
    return LayerEdgeRec(
        op=Op.PRESENT,
        edge_id=rec.id,
        frm=Endpoint(rec.fields.get("src", ""), src_port),
        to=Endpoint(rec.fields.get("dist", ""), dist_port),
        rel=rec.fields.get("relation", ""),
        wire=wire,
        fields=fields,
    )


def is_layer_edge_record(rec) -> bool:
    """True when EDG was stored via Layer (wire set or port endpoints)."""
    sp = rec.fields.get("src_port", "")
    dp = rec.fields.get("dist_port", "")
    if sp or dp:
        return True
    wire = rec.fields.get("wire", "")
    return wire in ("directed", "non_directed", "bi_directed")


def iter_fixture_body_lines(text: str) -> Iterator[str]:
    """Yield non-comment fixture lines for ingest."""
    for line in text.splitlines():
        s = line.strip()
        if not s or s.startswith("#"):
            continue
        yield s
