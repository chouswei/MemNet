"""Instance-driven @ART catalog schema (genre-agnostic core)."""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from novel_mcp.paths import workspace_root
from novel_mcp.setup_graph import read_usr_by_key

USR_CATALOG_SCHEMA_KEY = "catalog_schema"


@dataclass(frozen=True)
class CatalogSchema:
    """Wire shape + validation + LLM expand templates for one story instance."""

    wire_columns: tuple[str, ...]
    kind_field: str
    tier_field: str
    coeff_field: str
    kind_to_slot: dict[str, str]
    valid_kinds: frozenset[str]
    valid_tiers: frozenset[str]
    tier_coeff_bands: dict[str, tuple[float, float]]
    min_slots: dict[str, int] = field(
        default_factory=lambda: {"neigong": 8, "martial": 15, "qinggong": 5}
    )
    id_prefix: str = "ART"
    name_max_len: int = 12
    universe_label: str = "story universe"
    content_rules: str = ""
    expand_extra_rules: str = ""
    high_burn_substrings: tuple[str, ...] = ()
    burn_usr_key: str | None = "art_neili_burn"
    burn_usr_id: str = "USR49"
    qinggong_wire_kind: str = "mobility"
    body_stat_labels: dict[str, str] = field(
        default_factory=lambda: {
            "neigong": "neigong",
            "martial": "martial",
            "qinggong": "mobility",
        }
    )
    high_burn: str = "2"
    default_burn: str = "1"

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> CatalogSchema:
        bands_raw = data.get("tier_coeff_bands") or {}
        bands = {k: (float(v[0]), float(v[1])) for k, v in bands_raw.items()}
        return cls(
            wire_columns=tuple(data["wire_columns"]),
            kind_field=data["kind_field"],
            tier_field=data["tier_field"],
            coeff_field=data["coeff_field"],
            kind_to_slot=dict(data["kind_to_slot"]),
            valid_kinds=frozenset(data["valid_kinds"]),
            valid_tiers=frozenset(data["valid_tiers"]),
            tier_coeff_bands=bands,
            min_slots=dict(data.get("min_slots") or {}),
            id_prefix=str(data.get("id_prefix", "ART")),
            name_max_len=int(data.get("name_max_len", 12)),
            universe_label=str(data.get("universe_label", "story universe")),
            content_rules=str(data.get("content_rules", "")),
            expand_extra_rules=str(data.get("expand_extra_rules", "")),
            high_burn_substrings=tuple(data.get("high_burn_substrings") or ()),
            burn_usr_key=data.get("burn_usr_key"),
            burn_usr_id=str(data.get("burn_usr_id", "USR49")),
            qinggong_wire_kind=str(data.get("qinggong_wire_kind", "mobility")),
            body_stat_labels=dict(
                data.get("body_stat_labels")
                or {"neigong": "neigong", "martial": "martial", "qinggong": "mobility"}
            ),
            default_burn=str(data.get("default_burn", "1")),
            high_burn=str(data.get("high_burn", "2")),
        )

    @classmethod
    def load_json(cls, path: str | Path) -> CatalogSchema:
        p = Path(path)
        return cls.from_dict(json.loads(p.read_text(encoding="utf-8")))


def read_catalog_schema(
    session: str | None,
    *,
    workspace_root_path: str | None = None,
    fallback: CatalogSchema | None = None,
) -> CatalogSchema | None:
    rel = read_usr_by_key(session, USR_CATALOG_SCHEMA_KEY) if session else None
    if not rel:
        return fallback
    root = workspace_root(workspace_root_path)
    path = root / rel.replace("\\", "/")
    if not path.is_file():
        return fallback
    return CatalogSchema.load_json(path)


def art_from_parts(parts: list[str], schema: CatalogSchema) -> dict[str, str]:
    art: dict[str, str] = {"id": parts[0]}
    for i, col in enumerate(schema.wire_columns):
        if col == "id":
            continue
        if i < len(parts):
            art[col] = parts[i]
    return art


def art_to_wire(art: dict[str, str], schema: CatalogSchema) -> str:
    vals: list[str] = []
    for col in schema.wire_columns:
        if col == "id":
            vals.append(art["id"])
        else:
            vals.append(art.get(col, ""))
    return "@ART: " + "|".join(vals)


def slot_for_kind(kind: str, schema: CatalogSchema) -> str | None:
    return schema.kind_to_slot.get(kind)


def default_burn_for_art(art: dict[str, str], schema: CatalogSchema) -> str:
    name = art.get(schema.wire_columns[1] if len(schema.wire_columns) > 1 else "name", "")
    for sub in schema.high_burn_substrings:
        if sub in name:
            return schema.high_burn
    return schema.default_burn
