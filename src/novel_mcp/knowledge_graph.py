"""Novel-layer knowledge view — @KNW/@KNH on top of generic MemNet warm slices."""

from __future__ import annotations

import re
from typing import Any

_ROW_RE = re.compile(r"^@(\w+):\s*(.+)$")

# Ordinal depth for comparisons (higher = more knowledge).
_DEPTH_RANK: dict[str, int] = {
    "未知": 0,
    "耳聞": 1,
    "粗識": 2,
    "能述": 3,
    "能作": 4,
}


def depth_rank(depth: str) -> int:
    return _DEPTH_RANK.get(depth.strip(), 0)


def can_speak_about(depth: str, *, min_depth: str = "粗識") -> bool:
    """True when holder may reference this knowledge in dialogue."""
    return depth_rank(depth) >= depth_rank(min_depth)


def knw_refs_missing_from_warm(warm_stdout: str) -> list[str]:
    """KNW ids referenced by @KNH in warm but not present as @KNW rows."""
    knw_present: set[str] = set()
    knh_refs: set[str] = set()
    for line in warm_stdout.splitlines():
        m = _ROW_RE.match(line.strip())
        if not m:
            continue
        tag, body = m.group(1), m.group(2)
        parts = body.split("|")
        if tag == "KNW" and parts:
            knw_present.add(parts[0])
        elif tag == "KNH" and len(parts) >= 3:
            ref = parts[2]
            if ref.startswith("KNW"):
                knh_refs.add(ref)
    return sorted(knh_refs - knw_present)


def merge_warm_knw_lines(warm_stdout: str, extra_lines: str) -> str:
    """Append supplemental @KNW wire lines to a warm stdout blob."""
    extra = [ln.strip() for ln in extra_lines.splitlines() if ln.strip()]
    if not extra:
        return warm_stdout
    base = warm_stdout.rstrip()
    return base + "\n" + "\n".join(extra) + "\n"


def _holder_labels_from_warm(stdout: str) -> dict[str, str]:
    labels: dict[str, str] = {}
    for line in stdout.splitlines():
        m = _ROW_RE.match(line.strip())
        if not m:
            continue
        tag, body = m.group(1), m.group(2)
        parts = body.split("|")
        if tag == "PLR" and len(parts) >= 2:
            labels[parts[0]] = parts[1]
        elif tag == "NPC" and len(parts) >= 2:
            labels[parts[0]] = parts[1]
    return labels


def parse_warm_knowledge(stdout: str) -> dict[str, Any]:
    """Build knowledge graph from warm stdout (novel @KNW/@KNH schema).

    Returns:
        catalog: list of KNW atoms (world knowledge, era-scoped)
        holdings: list of KNH rows (who knows what, at what depth, which beat)
        by_holder: holder_id -> list of holding dicts
        scene_holders: holder ids seen in warm (for HUD subset)
    """
    holder_labels = _holder_labels_from_warm(stdout)
    knw_catalog: dict[str, dict[str, str]] = {}
    knh_raw: list[tuple[list[str], dict[str, Any]]] = []
    holdings: list[dict[str, Any]] = []
    holders_in_warm: set[str] = set()

    for line in stdout.splitlines():
        m = _ROW_RE.match(line.strip())
        if not m:
            continue
        tag, body = m.group(1), m.group(2)
        parts = body.split("|")
        if tag == "KNW" and len(parts) >= 4:
            kid = parts[0]
            knw_catalog[kid] = {
                "id": kid,
                "名稱": parts[1],
                "領域": parts[2],
                "時代": parts[3],
            }
        elif tag == "KNH" and len(parts) >= 6:
            holder = parts[1]
            holders_in_warm.add(holder)
            rec: dict[str, Any] = {
                "id": parts[0],
                "持有者": holder,
                "持有者名": holder_labels.get(holder, holder),
                "知識": parts[2],
                "knw_id": parts[2] if parts[2].startswith("KNW") else "",
                "深度": parts[3],
                "獲得拍": parts[4],
                "來源": parts[5],
                "depth_rank": depth_rank(parts[3]),
            }
            knh_raw.append((parts, rec))
        elif tag == "PLR" and parts:
            holders_in_warm.add(parts[0])
        elif tag == "NPC" and parts:
            holders_in_warm.add(parts[0])

    for parts, rec in knh_raw:
        if rec["knw_id"] and rec["knw_id"] in knw_catalog:
            rec["名稱"] = knw_catalog[rec["knw_id"]]["名稱"]
            rec["領域"] = knw_catalog[rec["knw_id"]]["領域"]
            rec["時代"] = knw_catalog[rec["knw_id"]]["時代"]
        else:
            rec["名稱"] = parts[2]
        holdings.append(rec)

    by_holder: dict[str, list[dict[str, Any]]] = {}
    for h in holdings:
        by_holder.setdefault(h["持有者"], []).append(h)

    return {
        "catalog": list(knw_catalog.values()),
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
    """Compact HUD fragment: who knows what (depth ≥ min_depth)."""
    by_holder = graph.get("by_holder") or {}
    target = holders or graph.get("scene_holders") or []
    bits: list[str] = []
    min_r = depth_rank(min_depth)
    for hid in target:
        label = hid
        rows = by_holder.get(hid, [])
        if rows:
            label = rows[0].get("持有者名", hid)
        items = [
            f"{h.get('名稱', h.get('知識', '?'))}({h['深度']})"
            for h in rows
            if h.get("depth_rank", 0) >= min_r
        ]
        if items:
            bits.append(f"{label}:{';'.join(items)}")
    return "｜".join(bits) if bits else "—"


def knowledge_gate_hint(holder: str, knw_name: str, graph: dict[str, Any]) -> str | None:
    """Return hint when NPC/PLR should not speak about knw_name yet."""
    for h in graph.get("by_holder", {}).get(holder, []):
        name = h.get("名稱") or h.get("知識", "")
        if name == knw_name or h.get("knw_id") == knw_name:
            if not can_speak_about(h.get("深度", "未知")):
                return f"{holder} 對「{knw_name}」僅 {h.get('深度', '未知')}，不可作能述/能作對白"
            return None
    return f"{holder} 圖中無「{knw_name}」KNH 列，不可憑空引用"
