"""Path-B PinMapIngest engines (MN-REQ-11 / MN-REQ-12.7 / #31).

Engines *build* a bounded NODE|EDGE pin map from an external artefact using
stable locators (path=, qname=, …). Client ``NEW`` is illegal for source pins.
Wire = GQL only. Ship order: Sysml first; other domains share the interface
but remain NotImplemented until landed (do not stub-as-done).
"""

from __future__ import annotations

import re
from collections.abc import Iterable, Sequence
from dataclasses import dataclass, field
from pathlib import Path

from memnet.exceptions import MemNetError
from memnet.gql import _emit_props, _escape_str
from memnet.id_allocator import IdAllocator
from memnet.mutate_gate import MutateGate

# Module-level: Sysml shipped; others still roadmap.
IMPLEMENTED_SYSML = True
IMPLEMENTED = IMPLEMENTED_SYSML  # at least one Path-B engine available

_NEW_TOKEN = re.compile(
    r"""(?:id\s*:\s*['\"]NEW['\"]|\[\s*NEW\s\]|\bid\s*=\s*NEW\b)""",
    re.IGNORECASE,
)

_BLOCK_COMMENT = re.compile(r"/\*.*?\*/", re.DOTALL)
_LINE_COMMENT = re.compile(r"//.*?$", re.MULTILINE)

# Structural defs we promote to pin kinds (bounded selective projection).
_DEF_HEAD = re.compile(
    r"^[ \t]*(?:(?:public|private|protected|abstract|override|readonly)\s+)*"
    r"(?P<kw>"
    r"package|"
    r"part\s+def|requirement\s+def|port\s+def|item\s+def|"
    r"connection\s+def|interface\s+def|action\s+def|state\s+def|"
    r"verification\s+def|view\s+def|viewpoint\s+def|"
    r"part|port|requirement|item"
    r")\s+(?P<name>[A-Za-z_][\w]*)",
    re.MULTILINE,
)

_REQ_ID_ATTR = re.compile(
    r'attribute\s+requirementId\s*:\s*String\s*=\s*["\']([^"\']+)["\']',
    re.IGNORECASE,
)

_SATISFY = re.compile(
    r"\bsatisfy\s+((?:[A-Za-z_][\w]*::)*[A-Za-z_][\w]*)",
)

_KIND_FOR_KW: dict[str, str] = {
    "package": "PKG",
    "part def": "PRT",
    "part": "PRT",
    "requirement def": "REQ",
    "requirement": "REQ",
    "port def": "POR",
    "port": "POR",
    "item def": "PRT",
    "item": "PRT",
    "connection def": "PRT",
    "interface def": "PRT",
    "action def": "PRT",
    "state def": "PRT",
    "verification def": "PRT",
    "view def": "PRT",
    "viewpoint def": "PRT",
}


@dataclass
class IngestResult:
    """Outcome of a Path-B ingest commit (or dry-run projection)."""

    domain: str
    gql_lines: list[str]
    node_ids: list[str] = field(default_factory=list)
    edge_ids: list[str] = field(default_factory=list)
    anchors: list[str] = field(default_factory=list)
    committed: bool = False

    @property
    def node_count(self) -> int:
        return len(self.node_ids)

    @property
    def edge_count(self) -> int:
        return len(self.edge_ids)


def reject_client_new(lines: Sequence[str]) -> None:
    """MN-REQ-11.16 — pin-map ingest SHALL NOT accept client NEW for source pins."""
    for i, line in enumerate(lines, start=1):
        if _NEW_TOKEN.search(line):
            raise MemNetError(
                "new_illegal",
                f"pin-map ingest rejects client NEW (line {i})",
                example="use locator-derived ground ids (path=, qname=)",
            )


def _strip_comments(text: str) -> str:
    text = _BLOCK_COMMENT.sub(" ", text)
    return _LINE_COMMENT.sub(" ", text)


def _norm_kw(raw: str) -> str:
    return re.sub(r"\s+", " ", raw.strip().lower())


class PinMapIngestBase:
    """Shared Path-B ingest interface (SysML nest: PinMapIngestBase)."""

    domain: str = ""
    implemented: bool = False

    def project(self, *_args, **_kwargs) -> IngestResult:
        raise MemNetError(
            "not_implemented",
            f"{type(self).__name__} Path-B ingest is not shipped yet "
            f"(domain={self.domain!r}); seed via add / seed_lines",
        )

    def ingest(self, session, *_args, **_kwargs) -> IngestResult:
        result = self.project(*_args, **_kwargs)
        return self.commit(session, result)

    def commit(self, session, result: IngestResult) -> IngestResult:
        reject_client_new(result.gql_lines)
        if not result.gql_lines:
            raise MemNetError("empty_ingest", "no pins projected from artefact")
        node_lines = [ln for ln in result.gql_lines if ln.lstrip().upper().startswith("MERGE")]
        edge_lines = [ln for ln in result.gql_lines if not ln.lstrip().upper().startswith("MERGE")]
        gate = MutateGate(session)
        if node_lines:
            gate.apply(node_lines, mode="add", allow_new_relation=True)
        fresh_edges: list[str] = []
        for ln in edge_lines:
            eid = _edge_id_from_gql(ln)
            if eid and session.store.get(eid) is not None:
                continue
            fresh_edges.append(ln)
        if fresh_edges:
            gate.apply(fresh_edges, mode="add", allow_new_relation=True)
        result.committed = True
        return result


class PinMapIngest_Sysml(PinMapIngestBase):
    """Selective SysML v2 .sysml → PKG|PRT|REQ|POR pins (first shipped engine)."""

    domain = "sysml"
    implemented = IMPLEMENTED_SYSML

    def project(
        self,
        path: str | Path,
        *,
        max_nodes: int = 200,
        max_files: int = 64,
        root: str | Path | None = None,
    ) -> IngestResult:
        if not self.implemented:
            return super().project()
        path_p = Path(path)
        files = _collect_sysml_files(path_p, max_files=max_files)
        if not files:
            raise MemNetError("no_artefact", f"no .sysml files under {path}")
        root_path = Path(root).resolve() if root else _infer_root(files, path_arg=path_p)
        alloc = IdAllocator()
        nodes: list[dict[str, str]] = []
        edges: list[tuple[str, str, str, str]] = []  # eid, src, rel, dst
        name_index: dict[str, str] = {}  # simple name → last id
        qname_index: dict[str, str] = {}

        for fpath in files:
            rel = _rel_path(fpath, root_path)
            _project_sysml_file(
                fpath,
                rel_path=rel,
                alloc=alloc,
                nodes=nodes,
                edges=edges,
                name_index=name_index,
                qname_index=qname_index,
                max_nodes=max_nodes,
            )

        gql = _nodes_edges_to_gql(nodes, edges)
        reject_client_new(gql)
        node_ids = [n["id"] for n in nodes]
        edge_ids = [e[0] for e in edges]
        anchors = node_ids[:8]
        return IngestResult(
            domain=self.domain,
            gql_lines=gql,
            node_ids=node_ids,
            edge_ids=edge_ids,
            anchors=anchors,
        )


class PinMapIngest_Codebase(PinMapIngestBase):
    """Selective codebase pins (modules/symbols) — interface only."""

    domain = "codebase"
    implemented = False


class PinMapIngest_PcbaAto(PinMapIngestBase):
    """PCBA schematic pin maps from Atopile .ato — interface only."""

    domain = "pcbaAto"
    implemented = False


class PinMapIngest_SkillsRules(PinMapIngestBase):
    """Agent skills/rules pin maps — interface only."""

    domain = "skillsRules"
    implemented = False


def get_engine(domain: str) -> PinMapIngestBase:
    """Resolve a Path-B engine by domainVariant name."""
    key = domain.strip().lower().replace("-", "").replace("_", "")
    mapping: dict[str, PinMapIngestBase] = {
        "sysml": PinMapIngest_Sysml(),
        "codebase": PinMapIngest_Codebase(),
        "pcbaato": PinMapIngest_PcbaAto(),
        "pcba": PinMapIngest_PcbaAto(),
        "ato": PinMapIngest_PcbaAto(),
        "skillsrules": PinMapIngest_SkillsRules(),
        "skills": PinMapIngest_SkillsRules(),
        "rules": PinMapIngest_SkillsRules(),
    }
    eng = mapping.get(key)
    if eng is None:
        raise MemNetError(
            "bad_domain",
            f"unknown PinMapIngest domain {domain!r}",
            example="sysml|codebase|pcbaAto|skillsRules",
        )
    return eng


def ingest_sysml(
    session,
    path: str | Path,
    *,
    max_nodes: int = 200,
    max_files: int = 64,
    root: str | Path | None = None,
    dry_run: bool = False,
) -> IngestResult:
    """Convenience: project (+ optionally commit) SysML Path-B pins."""
    eng = PinMapIngest_Sysml()
    result = eng.project(path, max_nodes=max_nodes, max_files=max_files, root=root)
    if dry_run:
        return result
    return eng.commit(session, result)


# ---------------------------------------------------------------------------
# SysML projection helpers
# ---------------------------------------------------------------------------


def _collect_sysml_files(path: str | Path, *, max_files: int) -> list[Path]:
    p = Path(path)
    if not p.exists():
        raise MemNetError("no_artefact", f"path not found: {path}")
    if p.is_file():
        if p.suffix.lower() != ".sysml":
            raise MemNetError("bad_artefact", f"expected .sysml file, got {p.name}")
        return [p.resolve()]
    files = sorted(x.resolve() for x in p.rglob("*.sysml") if x.is_file())
    if len(files) > max_files:
        raise MemNetError(
            "ingest_budget",
            f"too many .sysml files ({len(files)} > max_files={max_files})",
        )
    return files


def _infer_root(files: Sequence[Path], *, path_arg: Path | None = None) -> Path:
    if path_arg is not None and path_arg.is_dir():
        return path_arg.resolve()
    if len(files) == 1:
        return files[0].parent
    import os

    try:
        return Path(os.path.commonpath([str(f.parent) for f in files]))
    except ValueError:
        return files[0].parent


def _rel_path(fpath: Path, root: Path) -> str:
    try:
        return fpath.resolve().relative_to(root.resolve()).as_posix()
    except ValueError:
        return fpath.name


def _edge_id_from_gql(line: str) -> str | None:
    m = re.search(
        r"-\[:\w+[^\]]*\{[^}]*\bid:\s*'([^']+)'",
        line,
    )
    return m.group(1) if m else None


def _project_sysml_file(
    fpath: Path,
    *,
    rel_path: str,
    alloc: IdAllocator,
    nodes: list[dict[str, str]],
    edges: list[tuple[str, str, str, str]],
    name_index: dict[str, str],
    qname_index: dict[str, str],
    max_nodes: int,
) -> None:
    text = _strip_comments(fpath.read_text(encoding="utf-8", errors="replace"))
    # Event stream: def heads, braces, requirementId, satisfy.
    # Anonymous braces (e.g. #derivation connection {…}) must not corrupt nest.
    stack: list[tuple[str, str, str, int]] = []  # kind, name, id, depth
    depth = 0
    pending_push: tuple[str, str, str] | None = None
    events: list[tuple[int, str, re.Match[str]]] = []

    for m in _DEF_HEAD.finditer(text):
        events.append((m.start(), "def", m))
    for m in _REQ_ID_ATTR.finditer(text):
        events.append((m.start(), "reqid", m))
    for m in _SATISFY.finditer(text):
        events.append((m.start(), "sat", m))
    for m in re.finditer(r"[{}]", text):
        events.append((m.start(), "brace", m))
    events.sort(key=lambda e: (e[0], 0 if e[1] != "brace" else 1))

    for _pos, kind, m in events:
        if kind == "brace":
            ch = m.group(0)
            if ch == "{":
                depth += 1
                if pending_push is not None:
                    k0, name0, nid0 = pending_push
                    stack.append((k0, name0, nid0, depth))
                    pending_push = None
            else:
                while stack and stack[-1][3] == depth:
                    stack.pop()
                depth = max(0, depth - 1)
            continue

        if kind == "reqid":
            rid_val = m.group(1)
            if stack and stack[-1][0] == "REQ":
                _set_node_field(nodes, stack[-1][2], "requirementId", rid_val)
                new_id = alloc.allocate_from_locator("REQ", rid_val)
                if new_id != stack[-1][2]:
                    _retarget_node_id(
                        nodes,
                        edges,
                        name_index,
                        qname_index,
                        old_id=stack[-1][2],
                        new_id=new_id,
                    )
                    k0, name0, _, d0 = stack[-1]
                    stack[-1] = (k0, name0, new_id, d0)
            continue

        if kind == "sat":
            if not stack:
                continue
            target = m.group(1)
            src_id = stack[-1][2]
            leaf = target.split("::")[-1]
            dst_id = qname_index.get(target) or name_index.get(leaf)
            if dst_id and src_id != dst_id:
                eid = alloc.allocate_from_locator("E", f"sat_{src_id}_{dst_id}")
                if (eid, src_id, "satisfies", dst_id) not in edges:
                    edges.append((eid, src_id, "satisfies", dst_id))
            continue

        # def
        kw = _norm_kw(m.group("kw"))
        name = m.group("name")
        pin_kind = _KIND_FOR_KW.get(kw)
        if not pin_kind:
            continue
        if len(nodes) >= max_nodes:
            raise MemNetError(
                "ingest_budget",
                f"pin budget exceeded (max_nodes={max_nodes})",
            )
        parent_q = "::".join(s[1] for s in stack) if stack else ""
        qname = f"{parent_q}::{name}" if parent_q else name
        nid = alloc.allocate_from_locator(pin_kind, qname)
        fields = {
            "id": nid,
            "name": name,
            "qname": qname,
            "path": rel_path,
            "sysml_kind": kw.replace(" ", "_"),
            "recycle": "persistent",
        }
        nodes.append(fields)
        name_index[name] = nid
        qname_index[qname] = nid
        if stack:
            parent_id = stack[-1][2]
            eid = alloc.allocate_from_locator("E", f"contains_{parent_id}_{nid}")
            edges.append((eid, parent_id, "contains", nid))
        after = text[m.end() :]
        brace_i = after.find("{")
        semi_i = after.find(";")
        if brace_i >= 0 and (semi_i < 0 or brace_i < semi_i):
            pending_push = (pin_kind, name, nid)
        else:
            pending_push = None


def _set_node_field(nodes: list[dict[str, str]], nid: str, key: str, value: str) -> None:
    for n in nodes:
        if n["id"] == nid:
            n[key] = value
            return


def _retarget_node_id(
    nodes: list[dict[str, str]],
    edges: list[tuple[str, str, str, str]],
    name_index: dict[str, str],
    qname_index: dict[str, str],
    *,
    old_id: str,
    new_id: str,
) -> None:
    for n in nodes:
        if n["id"] == old_id:
            n["id"] = new_id
            break
    for i, (eid, src, rel, dst) in enumerate(edges):
        src2 = new_id if src == old_id else src
        dst2 = new_id if dst == old_id else dst
        edges[i] = (eid, src2, rel, dst2)
    for d in (name_index, qname_index):
        for k, v in list(d.items()):
            if v == old_id:
                d[k] = new_id


def _nodes_edges_to_gql(
    nodes: Iterable[dict[str, str]],
    edges: Iterable[tuple[str, str, str, str]],
) -> list[str]:
    lines: list[str] = []
    id_to_kind: dict[str, str] = {}
    for n in nodes:
        nid = n["id"]
        kind = nid.split("_", 1)[0] if "_" in nid else "PRT"
        # Prefer explicit kind from id prefix; fall back to PKG/PRT/REQ/POR
        for prefix in ("PKG", "PRT", "REQ", "POR"):
            if nid.startswith(prefix + "_"):
                kind = prefix
                break
        id_to_kind[nid] = kind
        props = {k: v for k, v in n.items() if k != "id" and v}
        lines.append(f"MERGE (:{kind} {{id: '{_escape_str(nid)}'}})")
        # MERGE alone may not set props on create in our codec — emit SET via
        # second form: MERGE (n:Kind {id}) SET n += {…}
        set_props = {**props}
        prop_s = _emit_props(set_props)
        lines[-1] = f"MERGE (n:{kind} {{id: '{_escape_str(nid)}'}}) SET n += {prop_s}"

    for eid, src, rel, dst in edges:
        lines.append(
            f"MATCH (a {{id: '{_escape_str(src)}'}}), (b {{id: '{_escape_str(dst)}'}})\n"
            f"CREATE (a)-[:{rel} {{id: '{_escape_str(eid)}', recycle: 'persistent'}}]->(b)"
        )
    # Flatten multi-line MATCH/CREATE into separate apply entries expected by MutateGate
    flat: list[str] = []
    buf: list[str] = []
    for line in lines:
        if "\n" in line:
            if buf:
                flat.extend(buf)
                buf = []
            parts = line.split("\n")
            # MutateGate accepts multi-statement as one string with newline
            flat.append("\n".join(parts))
        else:
            flat.append(line)
    return flat
