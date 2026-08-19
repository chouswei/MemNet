"""0.15 catalog Snap + SysML model Snap (session strata).

Snap(one model) → catalog session + package interiors. Look = pin_map.
Join = Path-B Absorb of a slice. Not Layer; not ANN; not one session per REQ.
Hid stays off the wire. Locators are properties.
"""

from __future__ import annotations

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


SlicePlan = tuple[InteriorRef, list[dict[str, str]], list[tuple[str, str, str, str]]]


@dataclass
class CatalogSnapResult:
    """Outcome of Snap(model) — catalog plus interiors; not a mission dump."""

    catalog_session_id: str
    interiors: list[InteriorRef] = field(default_factory=list)
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
    band_limit = max(1, 2 * goldfish_m)
    for qname, pkg_files in packages:
        nodes, edges = _project_package(
            pkg_files,
            root_dir=root_dir,
            max_nodes=max_nodes,
        )
        if not nodes:
            continue
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
        _commit_catalog(catalog, refs)
        return CatalogSnapResult(catalog_session_id=catalog.session_id, interiors=refs)
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
) -> tuple[list[dict[str, str]], list[tuple[str, str, str, str]]]:
    nodes: list[dict[str, str]] = []
    edges: list[tuple[str, str, str, str]] = []
    for fpath in pkg_files:
        part_nodes, part_edges, _root = project_sysml_parts(
            fpath,
            max_nodes=max_nodes,
            max_files=1,
            root=root_dir,
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


def _commit_catalog(catalog: SessionStore, refs: Sequence[InteriorRef]) -> None:
    lines: list[str] = []
    for ref in refs:
        props = {
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
