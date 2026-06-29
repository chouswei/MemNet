"""Holder acquaintance — `@EDG` is the single SSOT for who knows what, and how well.

Positive wires: `knows`, `knows_via`, `soul_knows` with depth in `attrs`.
No wire ⇒ POV must not use the entity's canonical name.
`unknows` edges are explicit negatives and do **not** imply acquaintance.
"""

from __future__ import annotations

import re
from typing import Any

from novel_mcp.character_gender import npc_appearance, npc_traits
from novel_mcp.setup_graph import list_tag_data_rows

_ROW_RE = re.compile(r"^@(\w+):\s*(.+)$")

KNOWLEDGE_RELATIONS = frozenset({"knows", "knows_via", "soul_knows"})
PLR_KNOWS_RELATION = "knows"

# Ordinal depth (higher = more acquaintance / mastery).
DEPTH_RANK: dict[str, int] = {
    "未知": 0,
    "耳聞": 1,
    "初識": 2,
    "粗識": 3,
    "能述": 4,
    "能作": 5,
    "熟識": 6,
}

_KnowledgeIndex = dict[tuple[str, str], tuple[str, str]]

# Entity tags whose col-2 is a display label in warm stdout.
_LABEL_TAGS = frozenset({"KNW", "TEC", "BIZ", "NPC", "PLR", "LOC", "GLO", "PRD", "LIB"})


def depth_rank(depth: str) -> int:
    return DEPTH_RANK.get((depth or "").strip(), 0)


def can_speak_about(depth: str, *, min_depth: str = "粗識") -> bool:
    """True when holder may reference this entity in dialogue at min_depth."""
    return depth_rank(depth) >= depth_rank(min_depth)


def load_holder_knowledge(session: str | None) -> _KnowledgeIndex:
    """Map (holder_id, entity_id) → (relation, attrs) from session EDG rows."""
    out: _KnowledgeIndex = {}
    if not session:
        return out
    for parts in list_tag_data_rows(session, "EDG"):
        _ingest_edg_parts(parts, out)
    return out


def load_holder_knowledge_from_warm(stdout: str) -> _KnowledgeIndex:
    """Map (holder_id, entity_id) → (relation, attrs) from warm @EDG lines."""
    out: _KnowledgeIndex = {}
    for line in stdout.splitlines():
        m = _ROW_RE.match(line.strip())
        if not m or m.group(1) != "EDG":
            continue
        _ingest_edg_parts(m.group(2).split("|"), out)
    return out


def merge_knowledge_index(
    session: str | None,
    warm_stdout: str = "",
) -> _KnowledgeIndex:
    """Session EDG wins; warm EDG fills gaps (tests / pre-persist slices)."""
    merged = load_holder_knowledge_from_warm(warm_stdout)
    session_idx = load_holder_knowledge(session)
    merged.update(session_idx)
    return merged


def _ingest_edg_parts(parts: list[str], out: _KnowledgeIndex) -> None:
    if len(parts) < 4:
        return
    rel = parts[2]
    if rel not in KNOWLEDGE_RELATIONS:
        return
    attrs = parts[5] if len(parts) > 5 else (parts[4] if len(parts) > 4 else "")
    out[(parts[1], parts[3])] = (rel, str(attrs))


def holder_knows_entity(
    session: str | None,
    holder_id: str | None,
    entity_id: str,
    *,
    index: _KnowledgeIndex | None = None,
    warm_stdout: str = "",
) -> bool:
    """True when a positive knowledge edge exists (or holder is the entity)."""
    if not entity_id:
        return True
    if not holder_id:
        return True
    if holder_id == entity_id:
        return True
    idx = _resolve_index(index, session, warm_stdout)
    return (holder_id, entity_id) in idx


def knowledge_record(
    session: str | None,
    holder_id: str | None,
    entity_id: str,
    *,
    index: _KnowledgeIndex | None = None,
    warm_stdout: str = "",
) -> dict[str, str] | None:
    """Return relation + attrs + depth when holder knows entity."""
    if not holder_knows_entity(
        session, holder_id, entity_id, index=index, warm_stdout=warm_stdout
    ):
        return None
    idx = _resolve_index(index, session, warm_stdout)
    rel, attrs = idx.get((holder_id or "", entity_id), ("", ""))
    depth = depth_from_attrs(attrs)
    return {
        "relation": rel,
        "attrs": attrs,
        "depth": depth,
        "depth_rank": str(depth_rank(depth)),
    }


def depth_from_attrs(attrs: str) -> str:
    text = (attrs or "").strip()
    if not text:
        return "初識"
    for label in DEPTH_RANK:
        if label in text:
            return label
    head = text.split(";")[0].split("：")[0].strip()
    return head[:8] if head else "初識"


_depth_from_attrs = depth_from_attrs  # legacy alias within module


def entity_kind(entity_id: str) -> str:
    if not entity_id:
        return "unknown"
    if entity_id.startswith("N"):
        return "npc"
    if entity_id.startswith("B"):
        return "biz"
    if entity_id.startswith("LOC"):
        return "place"
    if entity_id.startswith("KNW"):
        return "knw"
    if entity_id.startswith(("TEC", "PRD", "GLO")):
        return "tech"
    if entity_id.startswith("LIB"):
        return "place"
    return "entity"


def can_show_canonical_name(
    rec: dict[str, str] | None,
    *,
    entity_kind: str = "entity",
) -> bool:
    """Whether POV may use the graph canonical name for this entity."""
    if not rec:
        return False
    rel = rec.get("relation", "")
    if rel == "soul_knows":
        return True
    rank = depth_rank(rec.get("depth", "未知"))
    if rel == "knows":
        return rank >= depth_rank("初識")
    if rel == "knows_via":
        min_r = depth_rank("粗識") if entity_kind == "npc" else depth_rank("耳聞")
        return rank >= min_r
    return False


def can_show_precise_location(rec: dict[str, str] | None) -> bool:
    if not rec:
        return False
    return depth_rank(rec.get("depth", "未知")) >= depth_rank("粗識")


def entity_labels_from_warm(stdout: str) -> dict[str, str]:
    """Resolve entity id → canonical label from warm catalog rows."""
    labels: dict[str, str] = {}
    for line in stdout.splitlines():
        m = _ROW_RE.match(line.strip())
        if not m:
            continue
        tag, body = m.group(1), m.group(2)
        if tag not in _LABEL_TAGS:
            continue
        parts = body.split("|")
        if len(parts) >= 2 and parts[0] and parts[1]:
            labels[parts[0]] = parts[1]
    return labels


def holder_labels_from_warm(stdout: str) -> dict[str, str]:
    labels: dict[str, str] = {}
    for line in stdout.splitlines():
        m = _ROW_RE.match(line.strip())
        if not m:
            continue
        tag, body = m.group(1), m.group(2)
        if tag not in ("PLR", "NPC"):
            continue
        parts = body.split("|")
        if len(parts) >= 2:
            labels[parts[0]] = parts[1]
    return labels


def knowledge_meta(
    session: str | None,
    holder_id: str | None,
    entity_id: str,
    *,
    index: _KnowledgeIndex | None = None,
    warm_stdout: str = "",
) -> dict[str, Any]:
    rec = knowledge_record(
        session, holder_id, entity_id, index=index, warm_stdout=warm_stdout
    )
    known = holder_knows_entity(
        session, holder_id, entity_id, index=index, warm_stdout=warm_stdout
    )
    out: dict[str, Any] = {"known": known}
    if rec:
        out["knowledge_relation"] = rec["relation"]
        out["knowledge_depth"] = rec["depth"]
        out["knowledge_depth_rank"] = depth_rank(rec["depth"])
        out["name_visible"] = can_show_canonical_name(
            rec, entity_kind=entity_kind(entity_id)
        )
    else:
        out["knowledge_relation"] = None
        out["knowledge_depth"] = None
        out["knowledge_depth_rank"] = 0
        out["name_visible"] = False
    return out


def npc_anonymous_label(parts: list[str]) -> str:
    traits = npc_traits(parts)
    if traits:
        chunk = traits.replace("、", "，").split("，")[0].strip()
        if chunk:
            return chunk[:12]
    app = npc_appearance(parts)
    if app:
        chunk = app.replace("、", "，").split("，")[0].strip()
        if chunk:
            return chunk[:12]
    cid = parts[0] if parts else "?"
    return f"陌生人({cid})"


def resolve_npc_display_name(
    session: str | None,
    holder_id: str | None,
    parts: list[str],
    *,
    index: _KnowledgeIndex | None = None,
    warm_stdout: str = "",
) -> str:
    if len(parts) <= 1:
        return parts[0] if parts else "?"
    graph_name = parts[1]
    eid = parts[0]
    rec = knowledge_record(
        session, holder_id, eid, index=index, warm_stdout=warm_stdout
    )
    if can_show_canonical_name(rec, entity_kind="npc"):
        return graph_name
    return npc_anonymous_label(parts)


def resolve_biz_display(
    session: str | None,
    holder_id: str | None,
    parts: list[str],
    *,
    index: _KnowledgeIndex | None = None,
    warm_stdout: str = "",
) -> dict[str, Any]:
    bid = parts[0] if parts else ""
    graph_name = parts[1] if len(parts) > 1 else bid
    kind = parts[2] if len(parts) > 2 else ""
    location = parts[3] if len(parts) > 3 else ""
    rec = knowledge_record(
        session, holder_id, bid, index=index, warm_stdout=warm_stdout
    )
    meta = knowledge_meta(
        session, holder_id, bid, index=index, warm_stdout=warm_stdout
    )
    if can_show_canonical_name(rec, entity_kind="biz"):
        loc = location if can_show_precise_location(rec) else ("附近" if location else "")
        return {
            "id": bid,
            "name": graph_name,
            "kind": kind,
            "location": loc,
            **meta,
        }
    return {
        "id": bid,
        "name": kind or "某處作坊",
        "kind": kind,
        "location": "附近" if location else "",
        **meta,
    }


def resolve_place_display_name(
    session: str | None,
    holder_id: str | None,
    place_id: str,
    graph_name: str,
    *,
    region: str = "",
    index: _KnowledgeIndex | None = None,
    warm_stdout: str = "",
) -> str:
    rec = knowledge_record(
        session, holder_id, place_id, index=index, warm_stdout=warm_stdout
    )
    if can_show_canonical_name(rec, entity_kind="place"):
        return graph_name
    if region:
        return f"{region}某地"
    return "某處"


def can_speak_entity_name(
    session: str | None,
    holder_id: str | None,
    entity_id: str,
    *,
    min_depth: str = "粗識",
    index: _KnowledgeIndex | None = None,
    warm_stdout: str = "",
) -> bool:
    rec = knowledge_record(
        session, holder_id, entity_id, index=index, warm_stdout=warm_stdout
    )
    if not rec:
        return False
    return depth_rank(rec["depth"]) >= depth_rank(min_depth)


def build_knowledge_view(
    warm_stdout: str,
    *,
    session: str | None = None,
) -> dict[str, Any]:
    """Holder → entity acquaintance view from merged EDG + warm entity labels."""
    labels = entity_labels_from_warm(warm_stdout)
    holder_labels = holder_labels_from_warm(warm_stdout)
    idx = merge_knowledge_index(session, warm_stdout)
    holdings: list[dict[str, Any]] = []
    holders_in_warm: set[str] = set(holder_labels)

    for (holder, entity), (rel, attrs) in sorted(idx.items()):
        holders_in_warm.add(holder)
        depth = depth_from_attrs(attrs)
        holdings.append(
            {
                "持有者": holder,
                "持有者名": holder_labels.get(holder, holder),
                "entity_id": entity,
                "知識": entity,
                "名稱": labels.get(entity, entity),
                "relation": rel,
                "深度": depth,
                "depth_rank": depth_rank(depth),
                "attrs": attrs,
            }
        )

    by_holder: dict[str, list[dict[str, Any]]] = {}
    for row in holdings:
        by_holder.setdefault(row["持有者"], []).append(row)

    catalog = [
        {"id": eid, "名稱": name, "領域": "", "時代": ""}
        for eid, name in sorted(labels.items())
        if eid.startswith("KNW")
    ]

    return {
        "catalog": catalog,
        "holdings": holdings,
        "by_holder": by_holder,
        "scene_holders": sorted(holders_in_warm),
    }


def format_knowledge_hud(
    graph: dict[str, Any],
    *,
    holders: list[str] | None = None,
    min_depth: str = "粗識",
) -> str:
    """Compact HUD: who knows what at depth ≥ min_depth (EDG SSOT)."""
    by_holder = graph.get("by_holder") or {}
    target = holders or graph.get("scene_holders") or []
    bits: list[str] = []
    min_r = depth_rank(min_depth)
    for hid in target:
        rows = by_holder.get(hid, [])
        label = rows[0].get("持有者名", hid) if rows else hid
        items = [
            f"{h.get('名稱', h.get('entity_id', '?'))}({h['深度']})"
            for h in rows
            if h.get("depth_rank", 0) >= min_r
        ]
        if items:
            bits.append(f"{label}:{';'.join(items)}")
    return "｜".join(bits) if bits else "—"


def knowledge_gate_hint(
    holder: str,
    entity_name: str,
    graph: dict[str, Any],
    *,
    min_depth: str = "粗識",
) -> str | None:
    """Return hint when holder should not speak about entity_name yet."""
    for h in graph.get("by_holder", {}).get(holder, []):
        name = h.get("名稱") or h.get("entity_id", "")
        if name == entity_name or h.get("entity_id") == entity_name:
            if not can_speak_about(h.get("深度", "未知"), min_depth=min_depth):
                return (
                    f"{holder} 對「{entity_name}」僅 {h.get('深度', '未知')}，"
                    f"不可作能述/能作對白"
                )
            return None
    return f"{holder} 圖中無「{entity_name}」認識接線，不可憑空引用"


def entity_refs_missing_from_warm(warm_stdout: str) -> list[str]:
    """Entity ids referenced by @EDG in warm but absent as catalog rows."""
    present: set[str] = set()
    refs: set[str] = set()
    for line in warm_stdout.splitlines():
        m = _ROW_RE.match(line.strip())
        if not m:
            continue
        tag, body = m.group(1), m.group(2)
        parts = body.split("|")
        if tag in _LABEL_TAGS and parts:
            present.add(parts[0])
        elif tag == "EDG" and len(parts) >= 4 and parts[2] in KNOWLEDGE_RELATIONS:
            refs.add(parts[3])
    return sorted(eid for eid in refs if eid not in present)


def merge_warm_catalog_lines(warm_stdout: str, extra_lines: str) -> str:
    """Append supplemental catalog wire lines to a warm stdout blob."""
    extra = [ln.strip() for ln in extra_lines.splitlines() if ln.strip()]
    if not extra:
        return warm_stdout
    base = warm_stdout.rstrip()
    return base + "\n" + "\n".join(extra) + "\n"


def _resolve_index(
    index: _KnowledgeIndex | None,
    session: str | None,
    warm_stdout: str,
) -> _KnowledgeIndex:
    if index is not None:
        return index
    return merge_knowledge_index(session, warm_stdout)


# Legacy aliases
plr_knows_character = holder_knows_entity
parse_warm_knowledge = build_knowledge_view
