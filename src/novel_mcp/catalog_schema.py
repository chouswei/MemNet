"""Instance-driven @ART catalog schema (genre-agnostic core)."""

from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from novel_mcp.paths import workspace_root
from novel_mcp.setup_graph import read_usr_by_key

USR_CATALOG_SCHEMA_KEY = "catalog_schema"


@dataclass(frozen=True)
class ActionTemplate:
    id: str
    label: str
    template: str

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> ActionTemplate:
        return cls(
            id=str(data["id"]),
            label=str(data["label"]),
            template=str(data["template"]),
        )

    def to_dict(self) -> dict[str, str]:
        return {"id": self.id, "label": self.label, "template": self.template}


@dataclass(frozen=True)
class ItemActionsConfig:
    kind_source: tuple[str, ...] = ("name_rules", "prd")
    name_rules: tuple[tuple[str, str], ...] = ()
    by_kind: dict[str, tuple[ActionTemplate, ...]] = field(default_factory=dict)
    default: tuple[ActionTemplate, ...] = ()

    @classmethod
    def from_dict(cls, data: dict[str, Any] | None) -> ItemActionsConfig | None:
        if not data:
            return None
        rules: list[tuple[str, str]] = []
        for rule in data.get("name_rules") or []:
            rules.append((str(rule["match"]), str(rule["kind"])))
        by_kind: dict[str, tuple[ActionTemplate, ...]] = {}
        for kind, actions in (data.get("by_kind") or {}).items():
            by_kind[kind] = tuple(ActionTemplate.from_dict(a) for a in actions)
        default = tuple(ActionTemplate.from_dict(a) for a in (data.get("default") or []))
        return cls(
            kind_source=tuple(data.get("kind_source") or ("name_rules", "prd")),
            name_rules=tuple(rules),
            by_kind=by_kind,
            default=default,
        )


@dataclass(frozen=True)
class MartialActionsConfig:
    default: tuple[ActionTemplate, ...] = ()

    @classmethod
    def from_dict(cls, data: dict[str, Any] | None) -> MartialActionsConfig | None:
        if not data:
            return None
        default = tuple(ActionTemplate.from_dict(a) for a in (data.get("default") or []))
        return cls(default=default)


@dataclass(frozen=True)
class ProductionConfig:
    tec_tag: str = "TEC"
    prd_tag: str = "PRD"
    capacity_usr_key: str = "tec_lines_{tec_id}"
    installed_usr_key: str = "tec_installed_{tec_id}"
    relations: dict[str, str] = field(
        default_factory=lambda: {
            "produce": "produce",
            "develop": "develop",
            "belongs": "belongs",
            "requires": "requires",
        }
    )
    asset_mode_by_tec: dict[str, str] = field(default_factory=dict)
    prd_asset_links: dict[str, dict[str, Any]] = field(default_factory=dict)
    status_locked: tuple[str, ...] = ("未解鎖", "鎖定", "locked")
    status_unlocked: tuple[str, ...] = ("已解鎖", "解鎖", "unlocked")
    expandable_when_unlocked: bool = True
    action_templates: dict[str, ActionTemplate] = field(default_factory=dict)
    tec_overrides: dict[str, dict[str, Any]] = field(default_factory=dict)

    @classmethod
    def from_dict(cls, data: dict[str, Any] | None) -> ProductionConfig | None:
        if not data:
            return None
        templates: dict[str, ActionTemplate] = {}
        for key, tpl in (data.get("action_templates") or {}).items():
            entry = dict(tpl)
            entry.setdefault("id", key)
            templates[key] = ActionTemplate.from_dict(entry)
        default_relations = {
            "produce": "produce",
            "develop": "develop",
            "belongs": "belongs",
            "requires": "requires",
        }
        relations = {**default_relations, **(data.get("relations") or {})}
        return cls(
            tec_tag=str(data.get("tec_tag", "TEC")),
            prd_tag=str(data.get("prd_tag", "PRD")),
            capacity_usr_key=str(data.get("capacity_usr_key", "tec_lines_{tec_id}")),
            installed_usr_key=str(data.get("installed_usr_key", "tec_installed_{tec_id}")),
            relations=relations,
            asset_mode_by_tec=dict(data.get("asset_mode_by_tec") or {}),
            prd_asset_links=dict(data.get("prd_asset_links") or {}),
            status_locked=tuple(data.get("status_locked") or ("未解鎖", "鎖定", "locked")),
            status_unlocked=tuple(data.get("status_unlocked") or ("已解鎖", "解鎖", "unlocked")),
            expandable_when_unlocked=bool(data.get("expandable_when_unlocked", True)),
            action_templates=templates,
            tec_overrides=dict(data.get("tec_overrides") or {}),
        )


@dataclass(frozen=True)
class BusinessConfig:
    """@BIZ industry sheet columns and EDG relation names."""

    tag: str = "BIZ"
    wire_columns: tuple[str, ...] = (
        "id",
        "名稱",
        "類型",
        "地點",
        "現金",
        "負債",
        "收入",
        "支出",
    )
    relations: dict[str, str] = field(
        default_factory=lambda: {
            "manager": "manages",
            "assists": "assists",
            "hiring": "hiring",
            "upgrade": "upgrades",
            "cite": "cite",
            "produce": "produce",
        }
    )
    npc_tag: str = "NPC"
    prd_tag: str = "PRD"
    lib_tag: str = "LIB"
    plr_relations: tuple[str, ...] = ("owns", "manages")

    @classmethod
    def from_dict(cls, data: dict[str, Any] | None) -> BusinessConfig | None:
        if not data:
            return None
        default_relations = {
            "manager": "manages",
            "assists": "assists",
            "hiring": "hiring",
            "upgrade": "upgrades",
            "cite": "cite",
            "produce": "produce",
        }
        relations = {**default_relations, **(data.get("relations") or {})}
        return cls(
            tag=str(data.get("tag", "BIZ")),
            wire_columns=tuple(
                data.get("wire_columns")
                or (
                    "id",
                    "名稱",
                    "類型",
                    "地點",
                    "現金",
                    "負債",
                    "收入",
                    "支出",
                )
            ),
            relations=relations,
            npc_tag=str(data.get("npc_tag", "NPC")),
            prd_tag=str(data.get("prd_tag", "PRD")),
            lib_tag=str(data.get("lib_tag", "LIB")),
            plr_relations=tuple(data.get("plr_relations") or ("owns", "manages")),
        )


@dataclass(frozen=True)
class UiConfig:
    tab_labels: dict[str, str] = field(default_factory=dict)

    @classmethod
    def from_dict(cls, data: dict[str, Any] | None) -> UiConfig | None:
        if not data:
            return None
        return cls(tab_labels=dict(data.get("tab_labels") or {}))


@dataclass(frozen=True)
class LoadoutConfig:
    """Instance-specific opening pick wiring (genre lives in catalog_specs json)."""

    slot_order: tuple[str, ...] = ()
    opening_ranks: dict[str, str] = field(default_factory=dict)
    proficiency_rank: str = "1"
    proficiency_tag: str | None = None
    body_stat_tag: str | None = None
    proficiency_mastery: str = "1"
    body_stat_mastery: dict[str, str] = field(default_factory=dict)
    knows_relation: str = "knows"
    has_proficiency_relation: str = "has_proficiency"
    for_art_relation: str = "for_art"
    skills_separator: str = "、"
    extra_wire_lines: tuple[str, ...] = ()
    pre_pick_line_usr_key: str | None = None
    opening_gift_usr_key: str | None = None
    mobility_stat_slot: str | None = None
    body_stat_ids: tuple[str, ...] = ()
    proficiency_id_template: str | None = None

    @classmethod
    def from_dict(cls, data: dict[str, Any] | None) -> LoadoutConfig:
        if not data:
            return cls()
        return cls(
            slot_order=tuple(data.get("slot_order") or ()),
            opening_ranks=dict(data.get("opening_ranks") or {}),
            proficiency_rank=str(data.get("proficiency_rank", "1")),
            proficiency_tag=data.get("proficiency_tag"),
            body_stat_tag=data.get("body_stat_tag"),
            proficiency_mastery=str(data.get("proficiency_mastery", "1")),
            body_stat_mastery=dict(data.get("body_stat_mastery") or {}),
            knows_relation=str(data.get("knows_relation", "knows")),
            has_proficiency_relation=str(
                data.get("has_proficiency_relation", "has_proficiency")
            ),
            for_art_relation=str(data.get("for_art_relation", "for_art")),
            skills_separator=str(data.get("skills_separator", "、")),
            extra_wire_lines=tuple(data.get("extra_wire_lines") or ()),
            pre_pick_line_usr_key=data.get("pre_pick_line_usr_key"),
            opening_gift_usr_key=data.get("opening_gift_usr_key"),
            mobility_stat_slot=data.get("mobility_stat_slot"),
            body_stat_ids=tuple(data.get("body_stat_ids") or ()),
            proficiency_id_template=data.get("proficiency_id_template"),
        )


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
    loadout: LoadoutConfig = field(default_factory=LoadoutConfig)
    item_actions: ItemActionsConfig | None = None
    martial_actions: MartialActionsConfig | None = None
    production: ProductionConfig | None = None
    business: BusinessConfig | None = None
    ui: UiConfig | None = None

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
            loadout=LoadoutConfig.from_dict(data.get("loadout")),
            item_actions=ItemActionsConfig.from_dict(data.get("item_actions")),
            martial_actions=MartialActionsConfig.from_dict(data.get("martial_actions")),
            production=ProductionConfig.from_dict(data.get("production")),
            business=BusinessConfig.from_dict(data.get("business")),
            ui=UiConfig.from_dict(data.get("ui")),
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


def art_display_name(art: dict[str, str], schema: CatalogSchema) -> str:
    if len(schema.wire_columns) > 1:
        col = schema.wire_columns[1]
        val = art.get(col, "").strip()
        if val:
            return val
    return art.get("id", "")


def default_burn_for_art(art: dict[str, str], schema: CatalogSchema) -> str:
    for col in schema.wire_columns:
        val = art.get(col, "")
        m = re.search(r"burn(\d+)", val)
        if m:
            return m.group(1)
    name = art_display_name(art, schema)
    for sub in schema.high_burn_substrings:
        if sub in name:
            return schema.high_burn
    return schema.default_burn


def slot_order(schema: CatalogSchema) -> tuple[str, ...]:
    """Opening pick slots — from loadout.slot_order or first-seen kind_to_slot values."""
    if schema.loadout.slot_order:
        return schema.loadout.slot_order
    seen: list[str] = []
    for slot in schema.kind_to_slot.values():
        if slot not in seen:
            seen.append(slot)
    return tuple(seen)


def setup_scene_usr_key(slot: str) -> str:
    return f"setup_scene_{slot}"


def opening_offer_usr_key(slot: str) -> str:
    return f"opening_offer_{slot}"


def opening_offer_roll_usr_key(slot: str) -> str:
    return f"opening_offer_roll_{slot}"


def slot_label(schema: CatalogSchema, slot: str) -> str:
    return schema.body_stat_labels.get(slot, slot)


def opening_rank(schema: CatalogSchema, slot: str) -> str:
    return schema.loadout.opening_ranks.get(slot, schema.loadout.proficiency_rank)


def resolve_item_actions(
    schema: CatalogSchema,
    *,
    name: str,
    kind: str,
) -> list[dict[str, str]]:
    cfg = schema.item_actions
    if not cfg:
        return []
    actions = cfg.by_kind.get(kind) or cfg.default
    return [_apply_name_template(a, name) for a in actions]


def resolve_martial_actions(
    schema: CatalogSchema,
    *,
    name: str,
) -> list[dict[str, str]]:
    cfg = schema.martial_actions
    if not cfg:
        return []
    return [_apply_name_template(a, name) for a in cfg.default]


def _apply_name_template(action: ActionTemplate, name: str) -> dict[str, str]:
    return {
        "id": action.id,
        "label": action.label.replace("{name}", name),
        "template": action.template.replace("{name}", name),
    }


def resolve_item_kind(
    schema: CatalogSchema,
    *,
    item_name: str,
    prd_rows: dict[str, list[str]],
) -> str:
    cfg = schema.item_actions
    if not cfg:
        return "default"
    for source in cfg.kind_source:
        if source == "name_rules":
            for match, kind in cfg.name_rules:
                if match in item_name:
                    return kind
        elif source == "prd":
            for prd_id, parts in prd_rows.items():
                if len(parts) > 1 and parts[1] == item_name and len(parts) > 2:
                    return parts[2]
    return "default"
