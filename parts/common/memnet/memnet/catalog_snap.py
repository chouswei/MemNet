"""0.15 catalog Snap + SysML model Snap (session strata).

Snap(one model) → catalog session + package interiors. Look = pin_map.
Join = Path-B Absorb of a slice. Not Layer; not ANN; not one session per REQ.
Hid stays off the wire. Locators are properties.
"""

from __future__ import annotations

import hashlib
import re
from collections.abc import Sequence
from dataclasses import dataclass, field
from pathlib import Path

from memnet.config import DEFAULT_QUERY_MAX_ROWS, Caps, examples_dir
from memnet.exceptions import MemNetError
from memnet.gql import _emit_props
from memnet.pin_map_ingest import (
    IngestResult,
    PinMapIngest_Sysml,
    _collect_sysml_files,
    _nodes_edges_to_gql,
    _strip_comments,
    project_sysml_parts,
)
from memnet.session import SessionStore, close_session, list_sessions, open_session

_PKG_HEAD = re.compile(
    r"^[ \t]*package\s+(?P<name>[A-Za-z_][\w]*)",
    re.MULTILINE,
)
_IMPORT = re.compile(
    r"^[ \t]*(?:private|public|protected)?\s*import\s+"
    r"(?P<name>[A-Za-z_][\w]*)\s*::",
    re.MULTILINE,
)
_KIND_BAND_ORDER = ("REQ", "PRT", "POR", "PKG")


@dataclass
class InteriorRef:
    """Catalog locator for one interior session of a model Snap."""

    session_id: str
    qname: str
    grain: str
    path: str = ""
    kind_band: str = ""
    node_count: int = 0


@dataclass
class CrossCutRef:
    """Catalog locator for a satisfy edge whose ends live in two interiors.

    Not a merge of those interiors. Hid stays off the wire. Join is still
    Path-B Absorb of a slice, or a second pin_map on the dest session=.
    """

    relation: str
    src_qname: str
    src_kind: str
    src_name: str
    src_session: str
    src_package: str
    dst_qname: str
    dst_kind: str
    dst_name: str
    dst_session: str
    dst_package: str
    dst_requirement_id: str = ""
    src_path: str = ""
    dst_path: str = ""


SlicePlan = tuple[InteriorRef, list[dict[str, str]], list[tuple[str, str, str, str]]]


@dataclass
class CatalogSnapResult:
    """Outcome of Snap(model) — catalog plus interiors; not a mission dump."""

    catalog_session_id: str
    interiors: list[InteriorRef] = field(default_factory=list)
    cross_cuts: list[CrossCutRef] = field(default_factory=list)
    cross_cut_misses: int = 0
    skipped: bool = False

    @property
    def session_ids(self) -> list[str]:
        ids = [self.catalog_session_id]
        ids.extend(row.session_id for row in self.interiors)
        return ids


def default_sysml_map_file() -> Path:
    return examples_dir() / "schema.sysml.example.txt"


def snap_model(
    root: str | Path,
    *,
    map_file: str | Path | None = None,
    map_lines: list[str] | None = None,
    max_nodes: int = 200,
    max_files: int = 64,
    goldfish_m: int = DEFAULT_QUERY_MAX_ROWS,
    ttl_minutes: int | None = None,
    caps: Caps | None = None,
) -> CatalogSnapResult:
    """Snap one SysML load tree into a catalog + package interiors.

    Empty catalog seed → skip (no sessions minted). Package grain first;
    optional kind-band / child-package split when an interior exceeds ~2M.
    SHALL NOT mint a session per requirement def. SHALL NOT Commit the
    whole model into one session. Absorb of a whole S is not this path.
    """
    caps = caps or Caps()
    path = Path(root)
    files = _collect_sysml_files(path, max_files=max_files)
    if not files:
        raise MemNetError("no_artefact", f"no .sysml files under {root}")
    root_dir = path.resolve() if path.is_dir() else path.parent.resolve()
    packages = _interior_packages(files)
    if not packages:
        raise MemNetError(
            "empty_catalog",
            "no package interiors to Snap; skip catalog seed",
            example="package grain under the load-tree root",
        )

    interiors_plan: list[SlicePlan] = []
    satisfy_events: list[tuple[str, str]] = []
    projected_edges: list[tuple[str, str, str, str]] = []
    band_limit = max(1, 2 * goldfish_m)
    for qname, pkg_files in packages:
        nodes, edges = _project_package(
            pkg_files,
            root_dir=root_dir,
            max_nodes=max_nodes,
            satisfy_events=satisfy_events,
        )
        if not nodes:
            continue
        projected_edges.extend(edges)
        interiors_plan.extend(_split_interior(qname, nodes, edges, band_limit=band_limit))

    if not interiors_plan:
        raise MemNetError(
            "empty_catalog",
            "no package interiors to Snap; skip catalog seed",
        )

    map_kw = _map_kwargs(map_file, map_lines)
    before = {row[0] for row in list_sessions(caps)}
    try:
        catalog = open_session(ttl_minutes=ttl_minutes, caps=caps, **map_kw)
        refs: list[InteriorRef] = []
        ingest = PinMapIngest_Sysml()
        for draft, nodes, edges in interiors_plan:
            interior = open_session(ttl_minutes=ttl_minutes, caps=caps, **map_kw)
            gql = _nodes_edges_to_gql(nodes, edges)
            ingest.commit(
                interior,
                IngestResult(
                    domain="sysml",
                    gql_lines=gql,
                    node_ids=[n.get("qname") or "" for n in nodes],
                    edge_ids=[e[2] for e in edges],
                    anchors=[n.get("qname") or "" for n in nodes[:8]],
                ),
            )
            draft.session_id = interior.session_id
            draft.node_count = len(nodes)
            refs.append(draft)
        cuts, misses = _resolve_cross_cuts(
            interiors_plan,
            satisfy_events=satisfy_events,
            projected_edges=projected_edges,
        )
        _commit_catalog(
            catalog,
            refs,
            cross_cuts=cuts,
            end_locator_limit=goldfish_m,
        )
        return CatalogSnapResult(
            catalog_session_id=catalog.session_id,
            interiors=refs,
            cross_cuts=cuts,
            cross_cut_misses=misses,
        )
    except Exception:
        _rollback_new_sessions(before, caps)
        raise


def catalog_session_ids(result: CatalogSnapResult) -> list[str]:
    """List session= ids from a Snap (catalog first)."""
    return result.session_ids


def _map_kwargs(
    map_file: str | Path | None,
    map_lines: list[str] | None,
) -> dict:
    if map_file:
        return {"map_file": str(map_file)}
    if map_lines:
        return {"map_lines": map_lines}
    default = default_sysml_map_file()
    if default.is_file():
        return {"map_file": str(default)}
    raise MemNetError("no_map", "provide map_file or map_lines for model Snap")


def _rollback_new_sessions(before: set[str], caps: Caps) -> None:
    for sid, *_rest in list_sessions(caps):
        if sid not in before:
            try:
                close_session(sid, caps)
            except MemNetError:
                continue


def _interior_packages(files: Sequence[Path]) -> list[tuple[str, list[Path]]]:
    """Package grain: load-tree imports, else top-level packages. Not one file = Snap."""
    declared: dict[str, list[Path]] = {}
    for fpath in files:
        name = _top_level_package(fpath)
        if not name:
            continue
        declared.setdefault(name, []).append(fpath)
    if not declared:
        return []
    root_file = _pick_root_file(files)
    imported: list[str] = []
    if root_file is not None:
        imported = _imported_names(root_file)
    root_pkg = _top_level_package(root_file) if root_file is not None else ""
    names = [n for n in imported if n in declared and n != root_pkg]
    if not names:
        names = [n for n in declared if n != root_pkg] or list(declared)
    return [(name, declared[name]) for name in names]


def _pick_root_file(files: Sequence[Path]) -> Path | None:
    for fpath in files:
        if fpath.name.lower() in {"root.sysml"} or fpath.name.lower().startswith("root-"):
            return fpath
    scored = sorted(files, key=lambda p: (-len(_imported_names(p)), p.name))
    if scored and _imported_names(scored[0]):
        return scored[0]
    return None


def _top_level_package(fpath: Path) -> str:
    text = _strip_comments(fpath.read_text(encoding="utf-8", errors="replace"))
    m = _PKG_HEAD.search(text)
    return m.group("name") if m else ""


def _imported_names(fpath: Path) -> list[str]:
    text = _strip_comments(fpath.read_text(encoding="utf-8", errors="replace"))
    return [m.group("name") for m in _IMPORT.finditer(text)]


def _project_package(
    pkg_files: Sequence[Path],
    *,
    root_dir: Path,
    max_nodes: int,
    satisfy_events: list[tuple[str, str]] | None = None,
) -> tuple[list[dict[str, str]], list[tuple[str, str, str, str]]]:
    nodes: list[dict[str, str]] = []
    edges: list[tuple[str, str, str, str]] = []
    for fpath in pkg_files:
        part_nodes, part_edges, _root = project_sysml_parts(
            fpath,
            max_nodes=max_nodes,
            max_files=1,
            root=root_dir,
            satisfy_events=satisfy_events,
        )
        nodes.extend(part_nodes)
        edges.extend(part_edges)
    return nodes, edges


def _split_interior(
    qname: str,
    nodes: list[dict[str, str]],
    edges: list[tuple[str, str, str, str]],
    *,
    band_limit: int,
) -> list[SlicePlan]:
    """Split a fat package by kind band or child package — never per REQ."""
    path = next((n.get("path", "") for n in nodes if n.get("path")), "")

    def _row(
        *,
        grain: str,
        slice_qname: str,
        kind_band: str,
        slice_nodes: list[dict[str, str]],
    ) -> SlicePlan:
        return (
            InteriorRef(
                session_id="",
                qname=slice_qname,
                grain=grain,
                path=path,
                kind_band=kind_band,
            ),
            slice_nodes,
            _edges_in(slice_nodes, edges),
        )

    if len(nodes) <= band_limit:
        return [_row(grain="package", slice_qname=qname, kind_band="", slice_nodes=nodes)]
    by_kind: dict[str, list[dict[str, str]]] = {}
    for n in nodes:
        by_kind.setdefault(n.get("_kind") or "PRT", []).append(n)
    non_pkg = {k: v for k, v in by_kind.items() if k != "PKG"}
    if len(non_pkg) >= 2:
        pkg_nodes = by_kind.get("PKG", [])
        bands = []
        for kind in _KIND_BAND_ORDER:
            if kind == "PKG":
                continue
            band_nodes = by_kind.get(kind, [])
            if not band_nodes:
                continue
            bands.append(
                _row(
                    grain="kind",
                    slice_qname=qname,
                    kind_band=kind,
                    slice_nodes=pkg_nodes + band_nodes,
                )
            )
        if bands:
            return bands
    children: dict[str, list[dict[str, str]]] = {}
    for n in nodes:
        nq = n.get("qname") or qname
        parts = nq.split("::")
        key = "::".join(parts[:2]) if len(parts) >= 2 else qname
        children.setdefault(key, []).append(n)
    if len(children) >= 2:
        return [
            _row(grain="child_package", slice_qname=key, kind_band="", slice_nodes=group)
            for key, group in children.items()
            if group
        ]
    return [_row(grain="package", slice_qname=qname, kind_band="", slice_nodes=nodes)]


def _edges_in(
    nodes: list[dict[str, str]],
    edges: list[tuple[str, str, str, str]],
) -> list[tuple[str, str, str, str]]:
    ids = {n.get("id", "") for n in nodes}
    return [e for e in edges if e[1] in ids and e[3] in ids]


_NICK_SAFE = re.compile(r"[^A-Za-z0-9_.-]+")
_NICK_PREFIX = {
    "PKG": "pkg",
    "REQ": "req",
    "PRT": "prt",
    "POR": "por",
    "CON": "con",
}


def leftover_catalog_pin_nick(
    qname: str,
    *,
    kind: str = "PKG",
    kind_band: str = "",
    grain: str = "",
    used: set[str] | None = None,
) -> str:
    """leftover snapshot nickname for a catalog locator row.

    GraphElement identity stays the hid. Optional ``id`` is a nickname so
    ``session_save`` / ``session_load`` can parse wire fields (length 1-64).
    Cue remains kind + ``qname`` / locators — do not teach identity-by-id.
    """
    used = used if used is not None else set()
    prefix = _NICK_PREFIX.get(kind, "pin")
    bits = [qname]
    if kind_band:
        bits.append(kind_band)
    if grain and grain not in {"package", ""}:
        bits.append(grain)
    raw = "|".join([prefix, *bits])
    slug = _NICK_SAFE.sub("_", "_".join(bits)).strip("._-")
    nick = f"{prefix}_{slug}" if slug else ""
    if not nick or len(nick) > 64:
        digest = hashlib.sha256(raw.encode()).hexdigest()[:16]
        nick = f"{prefix}_{digest}"
    if nick in used:
        digest = hashlib.sha256(f"{raw}|{nick}".encode()).hexdigest()[:12]
        base = f"{prefix}_{digest}"
        nick = base
        n = 2
        while nick in used:
            nick = f"{base}{n}"[:64]
            n += 1
    used.add(nick)
    return nick


def leftover_catalog_pkg_nick(
    qname: str,
    *,
    kind_band: str = "",
    grain: str = "",
    used: set[str] | None = None,
) -> str:
    """leftover snapshot nickname for a catalog PKG row."""
    return leftover_catalog_pin_nick(
        qname,
        kind="PKG",
        kind_band=kind_band,
        grain=grain,
        used=used,
    )


def _index_interior_nodes(
    interiors_plan: Sequence[SlicePlan],
) -> tuple[
    dict[str, tuple[InteriorRef, dict[str, str]]],
    dict[str, tuple[InteriorRef, dict[str, str]]],
    dict[str, list[tuple[InteriorRef, dict[str, str]]]],
]:
    by_id: dict[str, tuple[InteriorRef, dict[str, str]]] = {}
    by_qname: dict[str, tuple[InteriorRef, dict[str, str]]] = {}
    by_name: dict[str, list[tuple[InteriorRef, dict[str, str]]]] = {}
    for ref, nodes, _edges in interiors_plan:
        for node in nodes:
            nid = node.get("id", "")
            if nid:
                by_id[nid] = (ref, node)
            qname = node.get("qname", "")
            if qname:
                by_qname[qname] = (ref, node)
            name = node.get("name", "")
            if name:
                by_name.setdefault(name, []).append((ref, node))
    return by_id, by_qname, by_name


def _lookup_target(
    target: str,
    by_qname: dict[str, tuple[InteriorRef, dict[str, str]]],
    by_name: dict[str, list[tuple[InteriorRef, dict[str, str]]]],
) -> tuple[InteriorRef, dict[str, str]] | None:
    hit = by_qname.get(target)
    if hit:
        return hit
    leaf = target.split("::")[-1]
    suffix = f"::{leaf}"
    qhits = [row for qname, row in by_qname.items() if qname == leaf or qname.endswith(suffix)]
    if len(qhits) == 1:
        return qhits[0]
    names = by_name.get(leaf) or by_name.get(target) or []
    if len(names) == 1:
        return names[0]
    return None


def _cross_cut_from_pair(
    src: tuple[InteriorRef, dict[str, str]],
    dst: tuple[InteriorRef, dict[str, str]],
    *,
    relation: str = "satisfies",
) -> CrossCutRef | None:
    src_ref, src_node = src
    dst_ref, dst_node = dst
    if src_ref.session_id == dst_ref.session_id:
        return None
    src_qname = src_node.get("qname") or ""
    dst_qname = dst_node.get("qname") or ""
    if not src_qname or not dst_qname:
        return None
    return CrossCutRef(
        relation=relation,
        src_qname=src_qname,
        src_kind=src_node.get("_kind") or "PRT",
        src_name=src_node.get("name") or src_qname.split("::")[-1],
        src_session=src_ref.session_id,
        src_package=src_ref.qname,
        dst_qname=dst_qname,
        dst_kind=dst_node.get("_kind") or "REQ",
        dst_name=dst_node.get("name") or dst_qname.split("::")[-1],
        dst_session=dst_ref.session_id,
        dst_package=dst_ref.qname,
        dst_requirement_id=dst_node.get("requirementId") or "",
        src_path=src_node.get("path") or src_ref.path,
        dst_path=dst_node.get("path") or dst_ref.path,
    )


def _resolve_cross_cuts(
    interiors_plan: Sequence[SlicePlan],
    *,
    satisfy_events: Sequence[tuple[str, str]],
    projected_edges: Sequence[tuple[str, str, str, str]],
) -> tuple[list[CrossCutRef], int]:
    """Resolve satisfy that Snap dropped (other package or kind-band split)."""
    by_id, by_qname, by_name = _index_interior_nodes(interiors_plan)
    seen: set[tuple[str, str, str]] = set()
    cuts: list[CrossCutRef] = []
    misses = 0

    def _add(cut: CrossCutRef | None) -> None:
        if cut is None:
            return
        key = (cut.relation, cut.src_qname, cut.dst_qname)
        if key in seen:
            return
        seen.add(key)
        cuts.append(cut)

    for src_qname, target in satisfy_events:
        src = by_qname.get(src_qname)
        dst = _lookup_target(target, by_qname, by_name)
        if src is None or dst is None:
            misses += 1
            continue
        _add(_cross_cut_from_pair(src, dst))

    for _eid, src_id, rel, dst_id in projected_edges:
        if rel != "satisfies":
            continue
        src = by_id.get(src_id)
        dst = by_id.get(dst_id)
        if src is None or dst is None:
            misses += 1
            continue
        _add(_cross_cut_from_pair(src, dst, relation=rel))

    cuts.sort(key=lambda c: (c.src_qname, c.dst_qname))
    return cuts, misses


def _commit_catalog(
    catalog: SessionStore,
    refs: Sequence[InteriorRef],
    *,
    cross_cuts: Sequence[CrossCutRef] = (),
    end_locator_limit: int = DEFAULT_QUERY_MAX_ROWS,
) -> None:
    lines: list[str] = []
    used: set[str] = set()
    for ref in refs:
        nick = leftover_catalog_pkg_nick(
            ref.qname,
            kind_band=ref.kind_band,
            grain=ref.grain,
            used=used,
        )
        props = {
            "id": nick,
            "qname": ref.qname,
            "session": ref.session_id,
            "grain": ref.grain,
            "recycle": "persistent",
        }
        if ref.path:
            props["path"] = ref.path
        if ref.kind_band:
            props["kind_band"] = ref.kind_band
        lines.append(f"CREATE (:PKG {_emit_props(props)})")

    pkg_by_session = {ref.session_id: ref for ref in refs}
    pairs = {
        (cut.src_session, cut.dst_session, cut.relation)
        for cut in cross_cuts
        if cut.src_session in pkg_by_session and cut.dst_session in pkg_by_session
    }
    for src_sid, dst_sid, rel in sorted(pairs):
        src_ref = pkg_by_session[src_sid]
        dst_ref = pkg_by_session[dst_sid]
        lines.append(
            f"MATCH (a:PKG {_emit_props({'session': src_ref.session_id})}), "
            f"(b:PKG {_emit_props({'session': dst_ref.session_id})})\n"
            f"CREATE (a)-[:{rel}]->(b)"
        )

    end_qnames = {cut.src_qname for cut in cross_cuts} | {cut.dst_qname for cut in cross_cuts}
    if cross_cuts and len(end_qnames) <= end_locator_limit:
        seen_q: set[str] = set()
        for cut in cross_cuts:
            for kind, qname, name, session, rid, path in (
                (
                    cut.src_kind,
                    cut.src_qname,
                    cut.src_name,
                    cut.src_session,
                    "",
                    cut.src_path,
                ),
                (
                    cut.dst_kind,
                    cut.dst_qname,
                    cut.dst_name,
                    cut.dst_session,
                    cut.dst_requirement_id,
                    cut.dst_path,
                ),
            ):
                if qname in seen_q:
                    continue
                seen_q.add(qname)
                nick = leftover_catalog_pin_nick(
                    qname,
                    kind=kind,
                    grain="cross_cut",
                    used=used,
                )
                props = {
                    "id": nick,
                    "name": name,
                    "qname": qname,
                    "session": session,
                    "grain": "cross_cut",
                    "recycle": "persistent",
                }
                if rid:
                    props["requirementId"] = rid
                if path:
                    props["path"] = path
                lines.append(f"CREATE (:{kind} {_emit_props(props)})")
        for cut in cross_cuts:
            lines.append(
                f"MATCH (a:{cut.src_kind} {_emit_props({'qname': cut.src_qname})}), "
                f"(b:{cut.dst_kind} {_emit_props({'qname': cut.dst_qname})})\n"
                f"CREATE (a)-[:{cut.relation}]->(b)"
            )

    ingest = PinMapIngest_Sysml()
    ingest.commit(
        catalog,
        IngestResult(
            domain="sysml",
            gql_lines=lines,
            node_ids=[r.qname for r in refs],
            edge_ids=[],
            anchors=[r.qname for r in refs[:8]],
        ),
    )
