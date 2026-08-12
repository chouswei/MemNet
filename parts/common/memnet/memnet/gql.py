"""Gated openCypher-shaped GQL wire (MemNet M2 agent surface).

Parses / emits the mutate + shaped-read subset in
``docs/grammar/gql-wire-profile.md``. Not full openCypher / every CIP.
Maps to the same NodeRec / EdgeRec / Op atoms used by MutateGate commit.
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from typing import Any

from memnet.tier_a import Document, EdgeRec, Field, NodeRec, Op, Section

_IDENT = r"[A-Za-z_][A-Za-z0-9_]*"
_LABEL = r"[A-Za-z_][A-Za-z0-9_]*"
_RELTYPE = r"[A-Za-z_][A-Za-z0-9_]*"

_STMT_START = re.compile(
    r"^(CREATE|MATCH|MERGE|DELETE|DETACH)\b",
    re.IGNORECASE,
)
_RE_SECTION = re.compile(r"^##\s+([A-Za-z][A-Za-z0-9_ ]*)\s*$")
_RE_SHAPED_NODE = re.compile(
    rf"^\(\s*(?::({_LABEL}))?\s*(\{{.*\}})\s*\)\s*$",
    re.DOTALL,
)
_RE_SHAPED_EDGE = re.compile(
    rf"^\(\s*(?::({_LABEL}))?\s*(\{{[^{{}}]*\}})\s*\)\s*"
    rf"-\s*\[\s*:({_RELTYPE})\s*(\{{[^{{}}]*\}})?\s*\]\s*->\s*"
    rf"\(\s*(?::({_LABEL}))?\s*(\{{[^{{}}]*\}})\s*\)\s*$",
    re.DOTALL,
)

# CREATE (n:Label {…}) or CREATE (:Label {…})
_RE_CREATE_NODE = re.compile(
    rf"^CREATE\s+\(\s*(?:({_IDENT})\s*)?(?::({_LABEL}))?\s*(\{{.*\}})?\s*\)\s*$",
    re.IGNORECASE | re.DOTALL,
)

# CREATE (a)-[:TYPE {…}]->(b)  — vars or inline nodes
_RE_CREATE_REL = re.compile(
    rf"^CREATE\s+\(\s*({_IDENT})\s*\)\s*"
    rf"-\s*\[\s*:({_RELTYPE})\s*(\{{[^{{}}]*\}})?\s*\]\s*->\s*"
    rf"\(\s*({_IDENT})\s*\)\s*$",
    re.IGNORECASE | re.DOTALL,
)

# MATCH (a:Label? {id:…}), (b …)  [CREATE|SET|DETACH DELETE|DELETE …]
_RE_MATCH_HEAD = re.compile(r"^MATCH\s+(.+)$", re.IGNORECASE | re.DOTALL)
_RE_MERGE = re.compile(
    rf"^MERGE\s+\(\s*(?:({_IDENT})\s*)?(?::({_LABEL}))?\s*(\{{.*\}})\s*\)\s*(.*)$",
    re.IGNORECASE | re.DOTALL,
)

_WS = re.compile(r"\s+")


class ParseError(Exception):
    def __init__(self, message: str, line: int | None = None) -> None:
        super().__init__(message)
        self.line = line


@dataclass
class LintIssue:
    severity: str
    code: str
    message: str
    line: int | None = None


@dataclass
class _NodePattern:
    var: str | None = None
    label: str | None = None
    props: dict[str, Any] = field(default_factory=dict)


def looks_like_gql(line: str) -> bool:
    """True when a non-empty line is gated GQL mutate or shaped present."""
    s = line.strip().lstrip("\ufeff")
    if not s or s.startswith("@"):
        return False
    # Section markers (pin-map / seed grouping) — not # comments
    if s.startswith("##"):
        return True
    if s.startswith("#"):
        return False
    if _STMT_START.match(s):
        return True
    if s.startswith("(") and (")-[" in s or s.endswith(")")):
        return True
    # Continuation of a prior MATCH/CREATE batch line (property-only rare)
    if s.upper().startswith("SET ") or s.upper().startswith("DELETE "):
        return True
    return False


def looks_like_legacy_layer_or_tier_a(line: str) -> bool:
    """Detect retired Layer / Tier A agent lines (reject on product path)."""
    s = line.strip().lstrip("\ufeff")
    if not s or s.startswith("#") or s.startswith("@"):
        return False
    if s.startswith(("+", "~", "-")) and not s.upper().startswith("DELETE"):
        # Tier A mutate ops; GQL uses CREATE/MATCH/MERGE/DELETE words
        return True
    if re.match(r"^LAW[A-Za-z0-9_.-]+\s+\w+", s) and not s.upper().startswith("CREATE"):
        return True
    # Tier A / Layer present: KIND [id] or CST [id] ; …
    if re.match(rf"^({_LABEL})\s+\[({_IDENT})\]", s):
        return True
    # Layer bare edge: E_x [a] --rel--> [b] or [a.port] --bind--> …
    if re.search(r"--[A-Za-z_].*-->", s) or re.search(r"--\([a-z]", s):
        return True
    if "ports=" in s or "law=" in s:
        return True
    return False


# ---------------------------------------------------------------------------
# Property / value scanner
# ---------------------------------------------------------------------------


def _skip_ws(s: str, i: int) -> int:
    while i < len(s) and s[i].isspace():
        i += 1
    return i


def _parse_string(s: str, i: int) -> tuple[str, int]:
    quote = s[i]
    if quote not in "'\"":
        raise ParseError(f"expected string at {i}")
    i += 1
    out: list[str] = []
    while i < len(s):
        ch = s[i]
        if ch == "\\" and i + 1 < len(s):
            nxt = s[i + 1]
            mapping = {"\\": "\\", "'": "'", '"': '"', "n": "\n", "r": "\r", "t": "\t"}
            if nxt not in mapping:
                raise ParseError(f"unknown string escape \\{nxt}")
            out.append(mapping[nxt])
            i += 2
            continue
        if ch == quote:
            return "".join(out), i + 1
        out.append(ch)
        i += 1
    raise ParseError("unterminated string")


def _parse_value(s: str, i: int) -> tuple[Any, int]:
    i = _skip_ws(s, i)
    if i >= len(s):
        raise ParseError("expected value")
    ch = s[i]
    if ch in "'\"":
        return _parse_string(s, i)
    if ch == "{":
        return _parse_map(s, i)
    if ch == "[":
        return _parse_list(s, i)
    if ch == "$":
        # Parameter token — treat name as literal placeholder string
        m = re.match(rf"\$({_IDENT})", s[i:])
        if not m:
            raise ParseError("bad parameter")
        return f"${m.group(1)}", i + m.end()
    # number / bool / bare ident (unquoted id-like)
    m = re.match(r"-?\d+(?:\.\d+)?", s[i:])
    if m:
        raw = m.group(0)
        val: Any = float(raw) if "." in raw else int(raw)
        return val, i + m.end()
    m = re.match(r"(?i)true\b", s[i:])
    if m:
        return True, i + m.end()
    m = re.match(r"(?i)false\b", s[i:])
    if m:
        return False, i + m.end()
    m = re.match(r"(?i)null\b", s[i:])
    if m:
        return None, i + m.end()
    m = re.match(rf"({_IDENT})", s[i:])
    if m:
        return m.group(1), i + m.end()
    raise ParseError(f"unrecognised value near {s[i:i+20]!r}")


def _parse_map(s: str, i: int) -> tuple[dict[str, Any], int]:
    i = _skip_ws(s, i)
    if i >= len(s) or s[i] != "{":
        raise ParseError("expected '{'")
    i += 1
    props: dict[str, Any] = {}
    i = _skip_ws(s, i)
    if i < len(s) and s[i] == "}":
        return props, i + 1
    while i < len(s):
        i = _skip_ws(s, i)
        m = re.match(rf"({_IDENT})\s*:", s[i:])
        if not m:
            raise ParseError(f"expected key: near {s[i:i+20]!r}")
        key = m.group(1)
        i += m.end()
        val, i = _parse_value(s, i)
        props[key] = val
        i = _skip_ws(s, i)
        if i < len(s) and s[i] == ",":
            i += 1
            continue
        if i < len(s) and s[i] == "}":
            return props, i + 1
        raise ParseError(f"expected ',' or '}}' near {s[i:i+20]!r}")
    raise ParseError("unterminated map")


def _parse_list(s: str, i: int) -> tuple[list[Any], int]:
    i = _skip_ws(s, i)
    if i >= len(s) or s[i] != "[":
        raise ParseError("expected '['")
    i += 1
    items: list[Any] = []
    i = _skip_ws(s, i)
    if i < len(s) and s[i] == "]":
        return items, i + 1
    while i < len(s):
        val, i = _parse_value(s, i)
        items.append(val)
        i = _skip_ws(s, i)
        if i < len(s) and s[i] == ",":
            i += 1
            continue
        if i < len(s) and s[i] == "]":
            return items, i + 1
        raise ParseError("expected ',' or ']' in list")
    raise ParseError("unterminated list")


def parse_props(text: str | None) -> dict[str, Any]:
    if not text or not text.strip():
        return {}
    props, end = _parse_map(text.strip(), 0)
    if end != len(text.strip()):
        raise ParseError("trailing junk after property map")
    return props


def _value_to_store(val: Any) -> str:
    if val is None:
        return ""
    if isinstance(val, bool):
        return "true" if val else "false"
    if isinstance(val, (int, float)):
        return str(val)
    if isinstance(val, (dict, list)):
        return json.dumps(val, ensure_ascii=True, separators=(",", ":"))
    return str(val)


def _props_to_fields(props: dict[str, Any], *, skip: set[str] | None = None) -> list[Field]:
    skip = skip or set()
    out: list[Field] = []
    for k, v in props.items():
        if k in skip:
            continue
        out.append(Field(key=k, op="=", value=_value_to_store(v)))
    return out


def _id_from_props(props: dict[str, Any], default: str = "NEW") -> str:
    if "id" not in props:
        return default
    raw = props["id"]
    if raw is None:
        return default
    text = str(raw)
    if text.startswith("$"):
        # Unbound parameter — treat as mint token when literally NEW-like
        return "NEW" if text.upper() in ("$ID", "$NEW") else text.lstrip("$")
    return text


# ---------------------------------------------------------------------------
# Statement splitting
# ---------------------------------------------------------------------------


def _split_statements(text: str) -> list[tuple[int, str]]:
    """Return (start_line_no, statement_text) for each GQL statement."""
    statements: list[tuple[int, str]] = []
    buf: list[str] = []
    start_line = 1
    for line_no, raw in enumerate(text.splitlines(), start=1):
        s = raw.strip()
        if not s or s.startswith("#"):
            continue
        if s.startswith("##"):
            if buf:
                statements.append((start_line, " ".join(buf)))
                buf = []
            statements.append((line_no, s))
            continue
        if _STMT_START.match(s) or (s.startswith("(") and not buf):
            if buf:
                prev_u = buf[0].upper()
                su = s.upper()
                # MATCH … CREATE (a)-[:R]->(b) / SET / DELETE — same query.
                # Do NOT swallow a following CREATE (:Label …) node into the MATCH.
                rel_create = su.startswith("CREATE") and "-[" in s
                continue_match = prev_u.startswith("MATCH") and (
                    rel_create
                    or su.startswith(("SET", "DELETE", "DETACH"))
                )
                continue_merge = prev_u.startswith("MERGE") and su.startswith("SET")
                if continue_match or continue_merge:
                    buf.append(s)
                    continue
                statements.append((start_line, " ".join(buf)))
            buf = [s]
            start_line = line_no
            continue
        if not buf:
            buf = [s]
            start_line = line_no
        else:
            buf.append(s)
    if buf:
        statements.append((start_line, " ".join(buf)))
    return statements


def _parse_node_patterns(chunk: str) -> tuple[list[_NodePattern], int, str]:
    """Parse MATCH pattern list: (a:L {…}), (b {id:…})."""
    patterns: list[_NodePattern] = []
    i = 0
    s = chunk.strip()
    while i < len(s):
        i = _skip_ws(s, i)
        if i >= len(s):
            break
        if s[i] == ",":
            i += 1
            continue
        if s[i] != "(":
            break
        i += 1
        i = _skip_ws(s, i)
        var = None
        label = None
        m = re.match(rf"({_IDENT})", s[i:])
        if m and not s[i : i + m.end()].startswith(":"):
            # var name (not a bare ':Label')
            var = m.group(1)
            i += m.end()
            i = _skip_ws(s, i)
        if i < len(s) and s[i] == ":":
            i += 1
            m = re.match(rf"({_LABEL})", s[i:])
            if not m:
                raise ParseError("expected label after ':'")
            label = m.group(1)
            i += m.end()
            i = _skip_ws(s, i)
        props: dict[str, Any] = {}
        if i < len(s) and s[i] == "{":
            props, i = _parse_map(s, i)
            i = _skip_ws(s, i)
        if i >= len(s) or s[i] != ")":
            raise ParseError("expected ')' after node pattern")
        i += 1
        patterns.append(_NodePattern(var=var, label=label, props=props))
        i = _skip_ws(s, i)
        if i < len(s) and s[i] == ",":
            i += 1
            continue
        break
    return patterns, i, s


def _split_match_body(body: str) -> tuple[str, str]:
    """Split MATCH body into (patterns_chunk, rest_starting_at_CREATE|SET|DELETE)."""
    upper = body.upper()
    for kw in (" CREATE ", " SET ", " DETACH ", " DELETE "):
        idx = upper.find(kw)
        if idx >= 0:
            return body[:idx].strip(), body[idx:].strip()
    return body.strip(), ""


def _parse_set_clause(set_text: str, default_var: str | None) -> list[Field]:
    """Parse SET n.k = v, n += {…}, n.id = 'x'."""
    text = set_text.strip()
    if text.upper().startswith("SET"):
        text = text[3:].strip()
    fields: list[Field] = []
    i = 0
    while i < len(text):
        i = _skip_ws(text, i)
        if i >= len(text):
            break
        m = re.match(rf"(?:({_IDENT})\s*)?\+\=\s*", text[i:])
        if m:
            # n += {…}
            i += m.end()
            props, i = _parse_map(text, i)
            fields.extend(_props_to_fields(props))
            i = _skip_ws(text, i)
            if i < len(text) and text[i] == ",":
                i += 1
            continue
        m = re.match(rf"(?:({_IDENT})\.)?({_IDENT})\s*=\s*", text[i:])
        if not m:
            raise ParseError(f"bad SET clause near {text[i:i+30]!r}")
        i += m.end()
        key = m.group(2)
        val, i = _parse_value(text, i)
        fields.append(Field(key=key, op="=", value=_value_to_store(val)))
        i = _skip_ws(text, i)
        if i < len(text) and text[i] == ",":
            i += 1
            continue
        break
    del default_var
    return fields


def _bind_port_fields(props: dict[str, Any]) -> list[Field]:
    """Map GQL fromPort/toPort/carries onto store + wire field names."""
    fields = _props_to_fields(props, skip={"id"})
    # Keep fromPort/toPort names on the item; MutateGate maps to src_port/dist_port
    return fields


def soft_validate(doc: Document) -> list[LintIssue]:
    """Grain checks: bind needs both ports; relation must not mix ports."""
    issues: list[LintIssue] = []
    for it in doc.items:
        if not isinstance(it, EdgeRec):
            continue
        keys = {f.key for f in it.fields}
        has_fp = "fromPort" in keys or "src_port" in keys
        has_tp = "toPort" in keys or "dist_port" in keys
        if it.rel == "bind":
            if not (has_fp and has_tp):
                issues.append(
                    LintIssue(
                        "error",
                        "bind_ports_required",
                        "bind relationships require fromPort and toPort",
                    )
                )
        else:
            if has_fp or has_tp:
                issues.append(
                    LintIssue(
                        "error",
                        "mixed_grain",
                        f"relation {it.rel!r} must not carry fromPort/toPort",
                    )
                )
        if any(f.key == "law" for f in it.fields):
            issues.append(
                LintIssue(
                    "error",
                    "law_on_edge",
                    "law must live on the node, never on a relationship",
                )
            )
    return issues


def parse_statement(stmt: str, line_no: int = 1) -> list[Section | NodeRec | EdgeRec]:
    s = stmt.strip()
    if not s:
        return []
    if s.startswith("##"):
        m = _RE_SECTION.match(s)
        name = m.group(1) if m else s[2:].strip()
        return [Section(name=name, raw=s)]

    # Shaped present (pin-map emit / display-only)
    if s.startswith("(") and not _STMT_START.match(s):
        return [_parse_shaped_present(s, line_no)]

    try:
        if s.upper().startswith("CREATE"):
            return [_parse_create(s, line_no)]
        if s.upper().startswith("MERGE"):
            return [_parse_merge(s, line_no)]
        if s.upper().startswith("MATCH"):
            return _parse_match(s, line_no)
        if s.upper().startswith("DETACH") or s.upper().startswith("DELETE"):
            raise ParseError(
                "DELETE requires MATCH … DETACH DELETE / DELETE (gated subset)",
                line_no,
            )
    except ParseError as exc:
        if exc.line is None:
            exc.line = line_no
        raise
    raise ParseError(f"unrecognised GQL statement: {s[:80]!r}", line_no)


def _parse_shaped_present(s: str, line_no: int) -> NodeRec | EdgeRec:
    me = _RE_SHAPED_EDGE.match(s)
    if me:
        src_label, src_props_s, rel, rel_props_s, dst_label, dst_props_s = me.groups()
        src_props = parse_props(src_props_s)
        dst_props = parse_props(dst_props_s)
        rel_props = parse_props(rel_props_s) if rel_props_s else {}
        return EdgeRec(
            op=Op.PRESENT,
            edge_id=_id_from_props(rel_props, default=""),
            frm=_id_from_props(src_props, default=""),
            rel=rel,
            to=_id_from_props(dst_props, default=""),
            fields=_bind_port_fields(rel_props),
            raw=s,
        )
    mn = _RE_SHAPED_NODE.match(s)
    if mn:
        label, props_s = mn.groups()
        props = parse_props(props_s)
        rid = _id_from_props(props, default="")
        kind = label or "NODE"
        return NodeRec(
            op=Op.PRESENT,
            kind=kind,
            id=rid,
            fields=_props_to_fields(props, skip={"id"}),
            raw=s,
        )
    raise ParseError(f"bad shaped present line: {s[:80]!r}", line_no)


def _parse_create(s: str, line_no: int) -> NodeRec | EdgeRec:
    m = _RE_CREATE_REL.match(s)
    if m:
        frm, rel, props_s, to = m.groups()
        props = parse_props(props_s) if props_s else {}
        eid = _id_from_props(props, default="NEW")
        return EdgeRec(
            op=Op.CREATE,
            edge_id=eid,
            frm=frm,
            rel=rel,
            to=to,
            fields=_bind_port_fields(props),
            raw=s,
        )
    m = _RE_CREATE_NODE.match(s)
    if m:
        _var, label, props_s = m.groups()
        props = parse_props(props_s) if props_s else {}
        if not label:
            raise ParseError("CREATE node requires a primary label", line_no)
        rid = _id_from_props(props, default="NEW")
        return NodeRec(
            op=Op.CREATE,
            kind=label,
            id=rid,
            fields=_props_to_fields(props, skip={"id"}),
            raw=s,
        )
    raise ParseError(f"unsupported CREATE shape: {s[:80]!r}", line_no)


def _parse_merge(s: str, line_no: int) -> NodeRec:
    m = _RE_MERGE.match(s)
    if not m:
        raise ParseError(f"unsupported MERGE shape: {s[:80]!r}", line_no)
    _var, label, props_s, rest = m.groups()
    props = parse_props(props_s)
    rid = _id_from_props(props, default="")
    if not rid or rid == "NEW":
        raise ParseError("MERGE requires a ground id (NEW illegal)", line_no)
    fields = _props_to_fields(props, skip={"id"})
    if rest and rest.upper().lstrip().startswith("SET"):
        fields.extend(_parse_set_clause(rest, _var))
    # MERGE uses PATCH op; MutateGate expands to create-or-patch
    kind = label or ""
    return NodeRec(op=Op.PATCH, kind=kind, id=rid, fields=fields, raw=s)


def _parse_match(s: str, line_no: int) -> list[NodeRec | EdgeRec]:
    m = _RE_MATCH_HEAD.match(s)
    if not m:
        raise ParseError("bad MATCH", line_no)
    patterns_chunk, rest = _split_match_body(m.group(1))
    try:
        patterns, _consumed, _full = _parse_node_patterns(patterns_chunk)
    except ParseError as exc:
        # Relationship MATCH for delete: ()-[r {id:…}]-()
        return _parse_match_rel_delete(s, line_no, rest)
    if not patterns and not rest:
        raise ParseError("MATCH needs node patterns", line_no)

    # Resolve var → id from props
    var_ids: dict[str, str] = {}
    for p in patterns:
        pid = _id_from_props(p.props, default="")
        if p.var and pid:
            var_ids[p.var] = pid

    rest_u = rest.upper()
    if rest_u.startswith("CREATE"):
        # CREATE (a)-[:TYPE {…}]->(b)
        cm = _RE_CREATE_REL.match(rest)
        if not cm:
            # Inline CREATE node after MATCH is unusual; reject
            raise ParseError(
                "MATCH … CREATE only supports relationship create "
                "(a)-[:TYPE]->(b) with known end ids",
                line_no,
            )
        frm_v, rel, props_s, to_v = cm.groups()
        props = parse_props(props_s) if props_s else {}
        frm = var_ids.get(frm_v, frm_v)
        to = var_ids.get(to_v, to_v)
        if frm == "NEW" or to == "NEW" or not frm or not to:
            raise ParseError(
                "relationship ends must be known ids (pin map or earlier create)",
                line_no,
            )
        eid = _id_from_props(props, default="NEW")
        return [
            EdgeRec(
                op=Op.CREATE,
                edge_id=eid,
                frm=frm,
                rel=rel,
                to=to,
                fields=_bind_port_fields(props),
                raw=s,
            )
        ]

    if rest_u.startswith("SET"):
        if len(patterns) != 1:
            raise ParseError("SET after MATCH expects one node pattern", line_no)
        p = patterns[0]
        rid = _id_from_props(p.props, default="")
        if not rid or rid == "NEW":
            raise ParseError("SET requires a ground id", line_no)
        fields = _parse_set_clause(rest, p.var)
        return [
            NodeRec(
                op=Op.PATCH,
                kind=p.label or "",
                id=rid,
                fields=fields,
                raw=s,
            )
        ]

    if rest_u.startswith("DETACH DELETE") or rest_u.startswith("DELETE"):
        if len(patterns) != 1:
            raise ParseError("DELETE after MATCH expects one node pattern", line_no)
        p = patterns[0]
        rid = _id_from_props(p.props, default="")
        if not rid or rid == "NEW":
            raise ParseError("DELETE requires a ground id", line_no)
        # Represent node drop as EdgeRec DROP with edge_id=node id for gate,
        # or NodeRec with DROP — Tier A uses - id for both. Use EdgeRec DROP
        # only for edges; for nodes use a NodeRec with op DROP via kind.
        return [
            NodeRec(op=Op.DROP, kind=p.label or "", id=rid, fields=[], raw=s)
        ]

    raise ParseError(f"unsupported MATCH continuation: {rest[:60]!r}", line_no)


def _parse_match_rel_delete(
    s: str, line_no: int, rest: str
) -> list[NodeRec | EdgeRec]:
    """MATCH ()-[r {id:'E1'}]-() DELETE r  (simplified gated form)."""
    m = re.search(
        rf"\[\s*(?:({_IDENT})\s*)?(?::({_RELTYPE}))?\s*(\{{[^{{}}]*\}})?\s*\]",
        s,
        re.IGNORECASE,
    )
    if not m:
        raise ParseError(f"unsupported MATCH shape: {s[:80]!r}", line_no)
    props = parse_props(m.group(3)) if m.group(3) else {}
    eid = _id_from_props(props, default="")
    if not eid or eid == "NEW":
        raise ParseError("relationship DELETE requires ground id", line_no)
    rest_u = (rest or "").upper()
    if "DELETE" not in s.upper() and "DELETE" not in rest_u:
        raise ParseError("relationship MATCH without DELETE is not agent-read", line_no)
    return [
        EdgeRec(
            op=Op.DROP,
            edge_id=eid,
            frm="",
            rel=m.group(2) or "",
            to="",
            fields=[],
            raw=s,
        )
    ]


def parse(text: str) -> Document:
    items: list[Section | NodeRec | EdgeRec] = []
    for line_no, stmt in _split_statements(text):
        items.extend(parse_statement(stmt, line_no))
    return Document(items=items)


# ---------------------------------------------------------------------------
# Emit (shaped subgraph / ack)
# ---------------------------------------------------------------------------


def _escape_str(val: str) -> str:
    return (
        val.replace("\\", "\\\\")
        .replace("'", "\\'")
        .replace("\n", "\\n")
        .replace("\r", "\\r")
        .replace("\t", "\\t")
    )


def _emit_value(val: str) -> str:
    if val == "":
        return "''"
    # JSON nested?
    if (val.startswith("{") and val.endswith("}")) or (
        val.startswith("[") and val.endswith("]")
    ):
        try:
            obj = json.loads(val)
            return _emit_py(obj)
        except json.JSONDecodeError:
            pass
    # bool / number
    if val in ("true", "false"):
        return val
    try:
        if "." in val:
            float(val)
            return val
        int(val)
        return val
    except ValueError:
        pass
    return f"'{_escape_str(val)}'"


def _emit_py(obj: Any) -> str:
    if obj is None:
        return "null"
    if isinstance(obj, bool):
        return "true" if obj else "false"
    if isinstance(obj, (int, float)):
        return str(obj)
    if isinstance(obj, str):
        return f"'{_escape_str(obj)}'"
    if isinstance(obj, list):
        return "[" + ", ".join(_emit_py(x) for x in obj) + "]"
    if isinstance(obj, dict):
        parts = [f"{k}: {_emit_py(v)}" for k, v in obj.items()]
        return "{" + ", ".join(parts) + "}"
    return f"'{_escape_str(str(obj))}'"


def _emit_props(props: dict[str, str], *, omit_empty: bool = True) -> str:
    parts: list[str] = []
    for k, v in props.items():
        if omit_empty and v == "":
            continue
        parts.append(f"{k}: {_emit_value(v)}")
    return "{" + ", ".join(parts) + "}"


def emit_node_shaped(kind: str, rid: str, fields: dict[str, str]) -> str:
    props = {"id": rid}
    for k, v in fields.items():
        if k == "id":
            continue
        if k == "recycle" and v == "persistent":
            continue
        if v == "":
            continue
        props[k] = v
    return f"(:{kind} {_emit_props(props)})"


def emit_edge_shaped(
    *,
    src_kind: str,
    src_id: str,
    rel: str,
    dst_kind: str,
    dst_id: str,
    edge_id: str,
    fields: dict[str, str],
) -> str:
    rel_props: dict[str, str] = {"id": edge_id}
    # Prefer GQL fromPort/toPort names on the wire
    for store_key, wire_key in (
        ("fromPort", "fromPort"),
        ("toPort", "toPort"),
        ("src_port", "fromPort"),
        ("dist_port", "toPort"),
        ("carries", "carries"),
    ):
        if store_key in fields and fields[store_key]:
            rel_props[wire_key] = fields[store_key]
    for k, v in fields.items():
        if k in (
            "id",
            "src",
            "dist",
            "relation",
            "fromPort",
            "toPort",
            "src_port",
            "dist_port",
            "carries",
            "wire",
            "at",
        ):
            continue
        if k == "recycle" and v == "persistent":
            continue
        if k == "attrs" and not v:
            continue
        if v == "":
            continue
        # note often lives in attrs
        if k == "attrs":
            rel_props.setdefault("note", v)
            continue
        rel_props[k] = v
    return (
        f"(:{src_kind} {{id: '{_escape_str(src_id)}'}})"
        f"-[:{rel} {_emit_props(rel_props)}]->"
        f"(:{dst_kind} {{id: '{_escape_str(dst_id)}'}})"
    )


def emit_item(it: NodeRec | EdgeRec | Section, *, as_mutate: bool = False) -> str:
    if isinstance(it, Section):
        return f"## {it.name}"
    if isinstance(it, EdgeRec):
        props = {f.key: f.value for f in it.fields}
        if it.edge_id:
            props = {"id": it.edge_id, **props}
        if as_mutate and it.op == Op.CREATE:
            # Prefer MATCH ends + CREATE when ends known; ack uses CREATE vars form
            return (
                f"CREATE ({it.frm})-[:{it.rel} {_emit_props(props)}]->({it.to})"
            )
        if as_mutate and it.op == Op.DROP:
            return (
                f"MATCH ()-[r {{id: '{_escape_str(it.edge_id or '')}'}}]-() DELETE r"
            )
        return emit_edge_shaped(
            src_kind="NODE",
            src_id=it.frm,
            rel=it.rel,
            dst_kind="NODE",
            dst_id=it.to,
            edge_id=it.edge_id or "",
            fields=props,
        )
    # NodeRec
    props = {"id": it.id, **{f.key: f.value for f in it.fields}}
    if as_mutate and it.op == Op.CREATE:
        return f"CREATE (:{it.kind} {_emit_props(props)})"
    if as_mutate and it.op == Op.PATCH:
        sets = ", ".join(f"n.{f.key} = {_emit_value(f.value)}" for f in it.fields)
        return f"MATCH (n {{id: '{_escape_str(it.id)}'}}) SET {sets}"
    if as_mutate and it.op == Op.DROP:
        return f"MATCH (n {{id: '{_escape_str(it.id)}'}}) DETACH DELETE n"
    return emit_node_shaped(it.kind or "NODE", it.id, props)


def emit(doc: Document, *, as_mutate: bool = False) -> str:
    lines = [
        emit_item(it, as_mutate=as_mutate)
        for it in doc.items
        if not isinstance(it, Section) or True
    ]
    return "\n".join(lines) + ("\n" if lines else "")


def round_trip_ok(text: str) -> bool:
    try:
        doc = parse(text)
        soft_validate(doc)
        return True
    except ParseError:
        return False
