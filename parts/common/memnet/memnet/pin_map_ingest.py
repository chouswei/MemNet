"""Path-B PinMapIngest engines (MN-REQ-11 / MN-REQ-12.7 / #31 / #64).

Engines *build* a bounded NODE|EDGE pin map from an external artefact using
stable locators (path=, qname=, refdes=, skill_id=, …). Client ``NEW`` is
illegal for source pins. Wire = GQL only. All four domain engines ship:
Sysml, Codebase, PcbaAto, SkillsRules.
"""

from __future__ import annotations

import ast
import re
from collections.abc import Iterable, Sequence
from dataclasses import dataclass, field
from pathlib import Path

from memnet.exceptions import MemNetError
from memnet.gql import _emit_props
from memnet.id_allocator import IdAllocator
from memnet.mutate_gate import MutateGate

# Module-level: Path-B domain engines (MN-REQ-11).
IMPLEMENTED_SYSML = True
IMPLEMENTED_CODEBASE = True
IMPLEMENTED_PCBA = True
IMPLEMENTED_SKILLS = True
IMPLEMENTED = True  # all Path-B domain engines available

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
        node_lines = [
            ln
            for ln in result.gql_lines
            if ln.lstrip().upper().startswith("CREATE") and "-[" not in ln
        ]
        edge_lines = [
            ln
            for ln in result.gql_lines
            if ln.lstrip().upper().startswith("MATCH") or "-[" in ln.lstrip()[:40]
        ]
        gate = MutateGate(session)
        batch = node_lines + edge_lines
        if batch:
            gate.apply(batch, mode="add", allow_new_relation=True)
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
        node_ids = [n.get("qname") or n.get("name") or "" for n in nodes]
        edge_ids = [e[2] for e in edges]
        anchors = node_ids[:8]
        return IngestResult(
            domain=self.domain,
            gql_lines=gql,
            node_ids=node_ids,
            edge_ids=edge_ids,
            anchors=anchors,
        )


class PinMapIngest_Codebase(PinMapIngestBase):
    """Selective codebase pins — MOD/SYM with path=/line=/signature=."""

    domain = "codebase"
    implemented = IMPLEMENTED_CODEBASE

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
        files = _collect_code_files(path_p, max_files=max_files)
        if not files:
            raise MemNetError("no_artefact", f"no supported source files under {path}")
        root_path = Path(root).resolve() if root else _infer_root(files, path_arg=path_p)
        alloc = IdAllocator()
        nodes: list[dict[str, str]] = []
        edges: list[tuple[str, str, str, str]] = []
        sym_index: dict[str, str] = {}  # simple name → id (last wins)
        mod_index: dict[str, str] = {}  # rel path / module stem → id

        for fpath in files:
            rel = _rel_path(fpath, root_path)
            _project_code_file(
                fpath,
                rel_path=rel,
                alloc=alloc,
                nodes=nodes,
                edges=edges,
                sym_index=sym_index,
                mod_index=mod_index,
                max_nodes=max_nodes,
            )

        gql = _nodes_edges_to_gql(nodes, edges)
        reject_client_new(gql)
        node_ids = [n.get("path") or n.get("signature") or n.get("name") or "" for n in nodes]
        edge_ids = [e[2] for e in edges]
        return IngestResult(
            domain=self.domain,
            gql_lines=gql,
            node_ids=node_ids,
            edge_ids=edge_ids,
            anchors=node_ids[:8],
        )


class PinMapIngest_PcbaAto(PinMapIngestBase):
    """PCBA schematic pin maps from Atopile .ato — CMP/NET/PIN."""

    domain = "pcbaAto"
    implemented = IMPLEMENTED_PCBA

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
        files = _collect_ato_files(path_p, max_files=max_files)
        if not files:
            raise MemNetError("no_artefact", f"no .ato files under {path}")
        root_path = Path(root).resolve() if root else _infer_root(files, path_arg=path_p)
        alloc = IdAllocator()
        nodes: list[dict[str, str]] = []
        edges: list[tuple[str, str, str, str]] = []
        ref_index: dict[str, str] = {}
        net_index: dict[str, str] = {}
        pin_index: dict[str, str] = {}  # "refdes.pin" → id

        for fpath in files:
            rel = _rel_path(fpath, root_path)
            _project_ato_file(
                fpath,
                rel_path=rel,
                alloc=alloc,
                nodes=nodes,
                edges=edges,
                ref_index=ref_index,
                net_index=net_index,
                pin_index=pin_index,
                max_nodes=max_nodes,
            )

        gql = _nodes_edges_to_gql(nodes, edges)
        reject_client_new(gql)
        node_ids = [n.get("path") or n.get("signature") or n.get("name") or "" for n in nodes]
        edge_ids = [e[2] for e in edges]
        return IngestResult(
            domain=self.domain,
            gql_lines=gql,
            node_ids=node_ids,
            edge_ids=edge_ids,
            anchors=node_ids[:8],
        )


class PinMapIngest_SkillsRules(PinMapIngestBase):
    """Agent skills/rules pin maps — SKL/RUL with skill_id=/phrase=."""

    domain = "skillsRules"
    implemented = IMPLEMENTED_SKILLS

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
        files = _collect_skill_files(path_p, max_files=max_files)
        if not files:
            raise MemNetError(
                "no_artefact",
                f"no SKILL.md / .mdc files under {path}",
            )
        root_path = Path(root).resolve() if root else _infer_root(files, path_arg=path_p)
        alloc = IdAllocator()
        nodes: list[dict[str, str]] = []
        edges: list[tuple[str, str, str, str]] = []
        skill_index: dict[str, str] = {}

        for fpath in files:
            rel = _rel_path(fpath, root_path)
            _project_skill_file(
                fpath,
                rel_path=rel,
                alloc=alloc,
                nodes=nodes,
                edges=edges,
                skill_index=skill_index,
                max_nodes=max_nodes,
            )

        # Second pass: resolve deferred related/paired edges now that index is full.
        _resolve_skill_edges(nodes, edges, skill_index, alloc)

        gql = _nodes_edges_to_gql(nodes, edges)
        reject_client_new(gql)
        node_ids = [n.get("path") or n.get("signature") or n.get("name") or "" for n in nodes]
        edge_ids = [e[2] for e in edges]
        return IngestResult(
            domain=self.domain,
            gql_lines=gql,
            node_ids=node_ids,
            edge_ids=edge_ids,
            anchors=node_ids[:8],
        )


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


def ingest_codebase(
    session,
    path: str | Path,
    *,
    max_nodes: int = 200,
    max_files: int = 64,
    root: str | Path | None = None,
    dry_run: bool = False,
) -> IngestResult:
    """Convenience: project (+ optionally commit) codebase Path-B pins."""
    eng = PinMapIngest_Codebase()
    result = eng.project(path, max_nodes=max_nodes, max_files=max_files, root=root)
    if dry_run:
        return result
    return eng.commit(session, result)


def ingest_pcba(
    session,
    path: str | Path,
    *,
    max_nodes: int = 200,
    max_files: int = 64,
    root: str | Path | None = None,
    dry_run: bool = False,
) -> IngestResult:
    """Convenience: project (+ optionally commit) PCBA .ato Path-B pins."""
    eng = PinMapIngest_PcbaAto()
    result = eng.project(path, max_nodes=max_nodes, max_files=max_files, root=root)
    if dry_run:
        return result
    return eng.commit(session, result)


def ingest_skills(
    session,
    path: str | Path,
    *,
    max_nodes: int = 200,
    max_files: int = 64,
    root: str | Path | None = None,
    dry_run: bool = False,
) -> IngestResult:
    """Convenience: project (+ optionally commit) skills/rules Path-B pins."""
    eng = PinMapIngest_SkillsRules()
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
            "_kind": pin_kind,
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


_KIND_PREFIXES = (
    "PKG",
    "PRT",
    "REQ",
    "POR",
    "MOD",
    "SYM",
    "CMP",
    "NET",
    "PIN",
    "SKL",
    "RUL",
)


def _match_props_for_node(n: dict[str, str]) -> str:
    """Locator properties for pattern MATCH (not a store key)."""
    prefer = (
        "qname",
        "requirementId",
        "skill_id",
        "signature",
        "refdes",
        "net",
        "pin",
        "path",
        "name",
    )
    props: dict[str, str] = {}
    for key in prefer:
        val = n.get(key, "")
        if val:
            props[key] = val
            if key in ("qname", "requirementId", "skill_id", "signature"):
                break
    if not props:
        props = {
            k: v
            for k, v in n.items()
            if k not in {"id", "_kind"} and v and not str(k).startswith("_")
        }
    return _emit_props(props)


def _nodes_edges_to_gql(
    nodes: Iterable[dict[str, str]],
    edges: Iterable[tuple[str, str, str, str]],
) -> list[str]:
    lines: list[str] = []
    by_id: dict[str, dict[str, str]] = {}
    for n in nodes:
        nid = n.get("id", "")
        kind = n.get("_kind", "")
        if not kind:
            kind = nid.split("_", 1)[0] if "_" in nid else "PRT"
            for prefix in _KIND_PREFIXES:
                if nid.startswith(prefix + "_"):
                    kind = prefix
                    break
        n = dict(n)
        n["_kind"] = kind
        if nid:
            by_id[nid] = n
        props = {
            k: v
            for k, v in n.items()
            if k not in {"id", "_kind"} and v and not str(k).startswith("_")
        }
        prop_s = _emit_props(props)
        lines.append(f"CREATE (:{kind} {prop_s})")

    for _eid, src, rel, dst in edges:
        a = by_id.get(src, {"id": src, "_kind": "PRT"})
        b = by_id.get(dst, {"id": dst, "_kind": "PRT"})
        ak = a.get("_kind") or "PRT"
        bk = b.get("_kind") or "PRT"
        lines.append(
            f"MATCH (a:{ak} {_match_props_for_node(a)}), "
            f"(b:{bk} {_match_props_for_node(b)})\n"
            f"CREATE (a)-[:{rel}]->(b)"
        )
    flat: list[str] = []
    for line in lines:
        if "\n" in line:
            parts = line.split("\n")
            flat.append("\n".join(parts))
        else:
            flat.append(line)
    return flat


# ---------------------------------------------------------------------------
# Codebase projection helpers (Python AST; cheap selective pins)
# ---------------------------------------------------------------------------

_CODE_SUFFIXES = {".py"}


def _collect_code_files(path: str | Path, *, max_files: int) -> list[Path]:
    p = Path(path)
    if not p.exists():
        raise MemNetError("no_artefact", f"path not found: {path}")
    if p.is_file():
        if p.suffix.lower() not in _CODE_SUFFIXES:
            raise MemNetError(
                "bad_artefact",
                f"expected source file ({', '.join(sorted(_CODE_SUFFIXES))}), got {p.name}",
            )
        return [p.resolve()]
    files = sorted(
        x.resolve()
        for x in p.rglob("*")
        if x.is_file()
        and x.suffix.lower() in _CODE_SUFFIXES
        and "/." not in ("/" + x.as_posix())
        and "node_modules" not in x.parts
        and "__pycache__" not in x.parts
        and ".venv" not in x.parts
    )
    if len(files) > max_files:
        raise MemNetError(
            "ingest_budget",
            f"too many source files ({len(files)} > max_files={max_files})",
        )
    return files


def _budget_check(nodes: list[dict[str, str]], max_nodes: int) -> None:
    if len(nodes) >= max_nodes:
        raise MemNetError(
            "ingest_budget",
            f"pin budget exceeded (max_nodes={max_nodes})",
        )


def _project_code_file(
    fpath: Path,
    *,
    rel_path: str,
    alloc: IdAllocator,
    nodes: list[dict[str, str]],
    edges: list[tuple[str, str, str, str]],
    sym_index: dict[str, str],
    mod_index: dict[str, str],
    max_nodes: int,
) -> None:
    _budget_check(nodes, max_nodes)
    mid = alloc.allocate_from_locator("MOD", rel_path)
    nodes.append(
        {
            "id": mid,
            "path": rel_path,
            "name": fpath.stem,
            "recycle": "persistent",
        }
    )
    mod_index[rel_path] = mid
    mod_index[fpath.stem] = mid

    if fpath.suffix.lower() != ".py":
        return
    try:
        tree = ast.parse(fpath.read_text(encoding="utf-8", errors="replace"), filename=rel_path)
    except SyntaxError:
        return

    local_syms: dict[str, str] = {}  # unqualified name → SYM id in this file

    def add_sym(
        name: str,
        *,
        kind: str,
        lineno: int,
        signature: str,
        owner: str | None = None,
    ) -> str | None:
        _budget_check(nodes, max_nodes)
        locator = f"{rel_path}:{name}"
        sid = alloc.allocate_from_locator("SYM", locator)
        nodes.append(
            {
                "id": sid,
                "name": name,
                "kind": kind,
                "path": rel_path,
                "line": str(lineno),
                "signature": signature,
                "recycle": "persistent",
            }
        )
        sym_index[name] = sid
        local_syms[name] = sid
        eid = alloc.allocate_from_locator("E", f"defines_{mid}_{sid}")
        edges.append((eid, mid, "defines", sid))
        if owner and owner in local_syms:
            oid = local_syms[owner]
            eid2 = alloc.allocate_from_locator("E", f"owns_{oid}_{sid}")
            edges.append((eid2, oid, "owns", sid))
        return sid

    for node in tree.body:
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            sig = _py_signature(node)
            add_sym(node.name, kind="function", lineno=node.lineno, signature=sig)
        elif isinstance(node, ast.ClassDef):
            add_sym(node.name, kind="class", lineno=node.lineno, signature=f"class {node.name}")
            for item in node.body:
                if isinstance(item, (ast.FunctionDef, ast.AsyncFunctionDef)):
                    sig = _py_signature(item)
                    add_sym(
                        f"{node.name}.{item.name}",
                        kind="method",
                        lineno=item.lineno,
                        signature=sig,
                        owner=node.name,
                    )
        elif isinstance(node, (ast.Import, ast.ImportFrom)):
            _code_import_edges(node, mid=mid, alloc=alloc, edges=edges, mod_index=mod_index)

    # Cheap same-file call edges (Name targets only).
    for node in ast.walk(tree):
        if not isinstance(node, ast.Call):
            continue
        callee = None
        if isinstance(node.func, ast.Name):
            callee = node.func.id
        elif isinstance(node.func, ast.Attribute) and isinstance(node.func.value, ast.Name):
            # Skip instance.method; keep Module.func style only when both local
            callee = None
        if not callee or callee not in local_syms:
            continue
        # Find enclosing def for source
        # Walk parents is expensive without parent map — skip; use module-level later.
    # Enclosing-function calls via a second annotated walk:
    _code_call_edges(tree, local_syms=local_syms, alloc=alloc, edges=edges)


def _py_signature(node: ast.AST) -> str:
    if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
        args = []
        for a in node.args.args:
            args.append(a.arg)
        prefix = "async def" if isinstance(node, ast.AsyncFunctionDef) else "def"
        return f"{prefix} {node.name}({', '.join(args)})"
    return getattr(node, "name", "?")


def _code_import_edges(
    node: ast.AST,
    *,
    mid: str,
    alloc: IdAllocator,
    edges: list[tuple[str, str, str, str]],
    mod_index: dict[str, str],
) -> None:
    names: list[str] = []
    if isinstance(node, ast.Import):
        names = [a.name.split(".")[0] for a in node.names]
    elif isinstance(node, ast.ImportFrom) and node.module:
        names = [node.module.split(".")[0]]
    for name in names:
        dst = mod_index.get(name)
        if not dst or dst == mid:
            continue
        eid = alloc.allocate_from_locator("E", f"includes_{mid}_{dst}")
        if (eid, mid, "includes", dst) not in edges:
            edges.append((eid, mid, "includes", dst))


def _code_call_edges(
    tree: ast.AST,
    *,
    local_syms: dict[str, str],
    alloc: IdAllocator,
    edges: list[tuple[str, str, str, str]],
) -> None:
    """Emit calls edges for top-level and class methods (Name callees only)."""

    def walk_fn(fn: ast.AST, src_key: str) -> None:
        src_id = local_syms.get(src_key)
        if not src_id:
            return
        for n in ast.walk(fn):
            if not isinstance(n, ast.Call) or not isinstance(n.func, ast.Name):
                continue
            dst_id = local_syms.get(n.func.id)
            if not dst_id or dst_id == src_id:
                continue
            eid = alloc.allocate_from_locator("E", f"calls_{src_id}_{dst_id}")
            trip = (eid, src_id, "calls", dst_id)
            if trip not in edges:
                edges.append(trip)

    for node in tree.body:
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            walk_fn(node, node.name)
        elif isinstance(node, ast.ClassDef):
            for item in node.body:
                if isinstance(item, (ast.FunctionDef, ast.AsyncFunctionDef)):
                    walk_fn(item, f"{node.name}.{item.name}")


# ---------------------------------------------------------------------------
# PCBA Atopile .ato projection helpers
# ---------------------------------------------------------------------------

_ATO_COMPONENT = re.compile(
    r"^(?P<indent>[ \t]*)(?:component|module)\s+(?P<name>[A-Za-z_][\w]*)\s*:",
    re.MULTILINE,
)
_ATO_SIGNAL = re.compile(
    r"^(?P<indent>[ \t]*)signal\s+(?P<name>[A-Za-z_][\w]*)\s*$",
    re.MULTILINE,
)
_ATO_PIN = re.compile(
    r"^(?P<indent>[ \t]*)pin\s+(?P<name>[A-Za-z_][\w]*|\d+|\"[^\"]+\")\s*$",
    re.MULTILINE,
)
_ATO_NEW = re.compile(
    r"^(?P<indent>[ \t]*)(?P<ref>[A-Za-z_][\w]*)\s*=\s*new\s+(?P<typ>[A-Za-z_][\w]*)",
    re.MULTILINE,
)
_ATO_CONNECT = re.compile(
    r"^(?P<indent>[ \t]*)(?P<a>[A-Za-z_][\w.]*(?:\[[^\]]+\])?)\s*~\s*"
    r"(?P<b>[A-Za-z_][\w.]*(?:\[[^\]]+\])?)\s*$",
    re.MULTILINE,
)
_ATO_NET_OVERRIDE = re.compile(
    r"^(?P<indent>[ \t]*)(?P<name>[A-Za-z_][\w.]*)\.override_net_name\s*=\s*"
    r"[\"'](?P<net>[^\"']+)[\"']",
    re.MULTILINE,
)


def _collect_ato_files(path: str | Path, *, max_files: int) -> list[Path]:
    p = Path(path)
    if not p.exists():
        raise MemNetError("no_artefact", f"path not found: {path}")
    if p.is_file():
        if p.suffix.lower() != ".ato":
            raise MemNetError("bad_artefact", f"expected .ato file, got {p.name}")
        return [p.resolve()]
    files = sorted(x.resolve() for x in p.rglob("*.ato") if x.is_file())
    if len(files) > max_files:
        raise MemNetError(
            "ingest_budget",
            f"too many .ato files ({len(files)} > max_files={max_files})",
        )
    return files


def _ato_pin_name(raw: str) -> str:
    return raw.strip().strip('"').strip("'")


def _project_ato_file(
    fpath: Path,
    *,
    rel_path: str,
    alloc: IdAllocator,
    nodes: list[dict[str, str]],
    edges: list[tuple[str, str, str, str]],
    ref_index: dict[str, str],
    net_index: dict[str, str],
    pin_index: dict[str, str],
    max_nodes: int,
) -> None:
    text = fpath.read_text(encoding="utf-8", errors="replace")
    # Strip # comments (line)
    text = re.sub(r"#.*?$", " ", text, flags=re.MULTILINE)

    # Pre-scan component type defs → pin names
    type_pins: dict[str, list[str]] = {}
    current_type: str | None = None
    current_indent = -1

    lines = text.splitlines()
    for line in lines:
        m_comp = re.match(
            r"^([ \t]*)(?:component|module)\s+([A-Za-z_][\w]*)\s*:",
            line,
        )
        if m_comp:
            current_type = m_comp.group(2)
            current_indent = len(m_comp.group(1).expandtabs(4))
            type_pins.setdefault(current_type, [])
            continue
        m_pin = re.match(r"^([ \t]*)pin\s+(\S+)\s*$", line)
        if m_pin and current_type is not None:
            ind = len(m_pin.group(1).expandtabs(4))
            if ind > current_indent:
                type_pins[current_type].append(_ato_pin_name(m_pin.group(2)))
                continue
        # leave block when indent collapses
        if current_type is not None and line.strip() and not line.startswith((" ", "\t")):
            current_type = None
            current_indent = -1

    def ensure_net(name: str) -> str:
        if name in net_index:
            return net_index[name]
        _budget_check(nodes, max_nodes)
        nid = alloc.allocate_from_locator("NET", f"{rel_path}:{name}")
        nodes.append(
            {
                "id": nid,
                "name": name,
                "net": name,
                "path": rel_path,
                "recycle": "persistent",
            }
        )
        net_index[name] = nid
        return nid

    def ensure_cmp(refdes: str, *, typ: str = "") -> str:
        if refdes in ref_index:
            return ref_index[refdes]
        _budget_check(nodes, max_nodes)
        cid = alloc.allocate_from_locator("CMP", f"{rel_path}:{refdes}")
        fields = {
            "id": cid,
            "name": refdes,
            "refdes": refdes,
            "path": rel_path,
            "recycle": "persistent",
        }
        if typ:
            fields["ato_type"] = typ
        nodes.append(fields)
        ref_index[refdes] = cid
        return cid

    def ensure_pin(refdes: str, pin: str) -> str:
        key = f"{refdes}.{pin}"
        if key in pin_index:
            return pin_index[key]
        cmp_id = ensure_cmp(refdes)
        _budget_check(nodes, max_nodes)
        pid = alloc.allocate_from_locator("PIN", f"{rel_path}:{key}")
        nodes.append(
            {
                "id": pid,
                "name": key,
                "refdes": refdes,
                "pin": pin,
                "path": rel_path,
                "recycle": "persistent",
            }
        )
        pin_index[key] = pid
        eid = alloc.allocate_from_locator("E", f"owns_{cmp_id}_{pid}")
        edges.append((eid, cmp_id, "owns", pid))
        return pid

    # Top-level signals → nets
    for m in _ATO_SIGNAL.finditer(text):
        ensure_net(m.group("name"))

    # Instances: ref = new Type → CMP + pins from type def
    for m in _ATO_NEW.finditer(text):
        refdes = m.group("ref")
        typ = m.group("typ")
        ensure_cmp(refdes, typ=typ)
        for pname in type_pins.get(typ, []):
            ensure_pin(refdes, pname)

    # Also promote named component defs that look like placed parts (no `new`)
    # when they declare pins and are not only types — skip abstract types
    # already covered by `new`. Types themselves are not CMP pins.

    def resolve_endpoint(token: str) -> tuple[str, str] | None:
        """Return (kind, id) for pin or net endpoint."""
        tok = token.strip()
        # strip [n] index
        tok = re.sub(r"\[[^\]]*\]$", "", tok)
        if tok in net_index:
            return ("NET", net_index[tok])
        if "." in tok:
            ref, pin = tok.split(".", 1)
            # unnamed[0] style already stripped brackets → pin name
            pid = ensure_pin(ref, pin)
            return ("PIN", pid)
        # bare name: prefer net, else treat as signal/net
        if re.match(r"^[A-Za-z_][\w]*$", tok):
            return ("NET", ensure_net(tok))
        return None

    for m in _ATO_CONNECT.finditer(text):
        left = resolve_endpoint(m.group("a"))
        right = resolve_endpoint(m.group("b"))
        if not left or not right:
            continue
        # Prefer PIN → NET; if PIN~PIN, invent a net from the pair
        if left[0] == "PIN" and right[0] == "NET":
            eid = alloc.allocate_from_locator("E", f"on_net_{left[1]}_{right[1]}")
            edges.append((eid, left[1], "on_net", right[1]))
        elif right[0] == "PIN" and left[0] == "NET":
            eid = alloc.allocate_from_locator("E", f"on_net_{right[1]}_{left[1]}")
            edges.append((eid, right[1], "on_net", left[1]))
        elif left[0] == "PIN" and right[0] == "PIN":
            net_name = f"n_{m.group('a').replace('.', '_')}_{m.group('b').replace('.', '_')}"
            nid = ensure_net(net_name)
            for pin_id in (left[1], right[1]):
                eid = alloc.allocate_from_locator("E", f"on_net_{pin_id}_{nid}")
                trip = (eid, pin_id, "on_net", nid)
                if trip not in edges:
                    edges.append(trip)
        elif left[0] == "NET" and right[0] == "NET" and left[1] != right[1]:
            # Alias: point smaller → keep both, soft-link via uses
            eid = alloc.allocate_from_locator("E", f"uses_{left[1]}_{right[1]}")
            edges.append((eid, left[1], "uses", right[1]))

    for m in _ATO_NET_OVERRIDE.finditer(text):
        ensure_net(m.group("net"))


# ---------------------------------------------------------------------------
# Skills / rules projection helpers
# ---------------------------------------------------------------------------

_FRONTMATTER = re.compile(r"\A---\s*\n(.*?)\n---\s*\n?", re.DOTALL)
_FM_NAME = re.compile(r"(?m)^name\s*:\s*[\"']?([^\"'\n#]+)[\"']?")
_FM_DESC = re.compile(r"(?m)^description\s*:\s*[\"']?([^\"'\n#]+)[\"']?")
_FM_LIST_BLOCK = re.compile(
    r"(?ms)^(related|triggers|paired_with|governs|depends)\s*:\s*\n((?:[ \t]*-[ \t]+.+\n?)+)"
)
_FM_LIST_INLINE = re.compile(
    r"(?m)^(related|triggers|paired_with|governs|depends)\s*:\s*\[([^\]]*)\]"
)


def _collect_skill_files(path: str | Path, *, max_files: int) -> list[Path]:
    p = Path(path)
    if not p.exists():
        raise MemNetError("no_artefact", f"path not found: {path}")
    if p.is_file():
        name = p.name
        if name != "SKILL.md" and p.suffix.lower() != ".mdc":
            raise MemNetError(
                "bad_artefact",
                f"expected SKILL.md or .mdc file, got {p.name}",
            )
        return [p.resolve()]
    files: list[Path] = []
    for x in sorted(p.rglob("*")):
        if not x.is_file():
            continue
        if x.name == "SKILL.md" or x.suffix.lower() == ".mdc":
            files.append(x.resolve())
    if len(files) > max_files:
        raise MemNetError(
            "ingest_budget",
            f"too many skill/rule files ({len(files)} > max_files={max_files})",
        )
    return files


def _parse_frontmatter(text: str) -> dict[str, object]:
    m = _FRONTMATTER.match(text)
    if not m:
        return {}
    body = m.group(1)
    out: dict[str, object] = {}
    nm = _FM_NAME.search(body)
    if nm:
        out["name"] = nm.group(1).strip()
    desc = _FM_DESC.search(body)
    if desc:
        out["description"] = desc.group(1).strip()
    for lm in _FM_LIST_BLOCK.finditer(body):
        key = lm.group(1)
        items = [
            re.sub(r"^[ \t]*-[ \t]+", "", ln).strip().strip("\"'")
            for ln in lm.group(2).splitlines()
            if ln.strip().startswith("-")
        ]
        out[key] = [i for i in items if i]
    for lm in _FM_LIST_INLINE.finditer(body):
        key = lm.group(1)
        items = [x.strip().strip("\"'") for x in lm.group(2).split(",") if x.strip()]
        out[key] = items
    return out


def _phrase_from_desc(desc: str, *, limit: int = 80) -> str:
    s = re.sub(r"\s+", " ", desc).strip()
    if len(s) > limit:
        s = s[: limit - 1].rstrip() + "…"
    return s


def _project_skill_file(
    fpath: Path,
    *,
    rel_path: str,
    alloc: IdAllocator,
    nodes: list[dict[str, str]],
    edges: list[tuple[str, str, str, str]],
    skill_index: dict[str, str],
    max_nodes: int,
) -> None:
    text = fpath.read_text(encoding="utf-8", errors="replace")
    fm = _parse_frontmatter(text)
    is_rule = fpath.suffix.lower() == ".mdc"
    kind = "RUL" if is_rule else "SKL"
    if is_rule:
        skill_id = str(fm.get("name") or fpath.stem)
    else:
        # Prefer frontmatter name; else parent directory (Cursor pack layout).
        skill_id = str(fm.get("name") or fpath.parent.name or fpath.stem)
    _budget_check(nodes, max_nodes)
    nid = alloc.allocate_from_locator(kind, skill_id)
    phrase = ""
    if "description" in fm:
        phrase = _phrase_from_desc(str(fm["description"]))
    fields = {
        "id": nid,
        "name": skill_id,
        "skill_id": skill_id,
        "path": rel_path,
        "recycle": "persistent",
    }
    if phrase:
        fields["phrase"] = phrase
    nodes.append(fields)
    skill_index[skill_id] = nid
    skill_index[skill_id.lower()] = nid
    # Stash pending relation targets on the node for resolve pass
    pending: list[str] = []
    for key in ("related", "paired_with", "triggers", "governs", "depends"):
        vals = fm.get(key)
        if isinstance(vals, list):
            for v in vals:
                pending.append(f"{key}:{v}")
    if pending:
        fields["_pending"] = "|".join(pending)


def _resolve_skill_edges(
    nodes: list[dict[str, str]],
    edges: list[tuple[str, str, str, str]],
    skill_index: dict[str, str],
    alloc: IdAllocator,
) -> None:
    rel_map = {
        "related": "paired_with",
        "paired_with": "paired_with",
        "triggers": "triggers",
        "governs": "governs",
        "depends": "uses",
    }
    for n in nodes:
        pending = n.pop("_pending", "")
        if not pending:
            continue
        src = n["id"]
        for item in pending.split("|"):
            if ":" not in item:
                continue
            key, target = item.split(":", 1)
            rel = rel_map.get(key)
            if not rel:
                continue
            dst = skill_index.get(target) or skill_index.get(target.lower())
            if not dst or dst == src:
                continue
            eid = alloc.allocate_from_locator("E", f"{rel}_{src}_{dst}")
            trip = (eid, src, rel, dst)
            if trip not in edges:
                edges.append(trip)
