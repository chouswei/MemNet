"""Parse MemNet warm wire into a novel-agnostic index."""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Any

_ROW_RE = re.compile(r"^@(\w+):\s*(.+)$")


@dataclass
class LawRow:
    id: str
    name: str
    mechanism: str
    constraint: str
    raw: str

    @property
    def tokens(self) -> list[str]:
        if not self.constraint or self.constraint == "-":
            return []
        return [t.strip() for t in self.constraint.replace(";", ",").split(",") if t.strip()]


@dataclass
class WarmIndex:
    rows_by_tag: dict[str, list[str]] = field(default_factory=dict)
    usrs_by_key: dict[str, tuple[str, str]] = field(default_factory=dict)
    laws: dict[str, LawRow] = field(default_factory=dict)
    plr_rows: list[list[str]] = field(default_factory=list)
    npc_rows: list[list[str]] = field(default_factory=list)
    sys_rows: list[list[str]] = field(default_factory=list)
    biz_rows: list[list[str]] = field(default_factory=list)
    scn_rows: list[list[str]] = field(default_factory=list)
    raw: str = ""


def index_warm(stdout: str) -> WarmIndex:
    idx = WarmIndex(raw=stdout)
    for line in stdout.splitlines():
        m = _ROW_RE.match(line.strip())
        if not m:
            continue
        tag, body = m.group(1), m.group(2)
        idx.rows_by_tag.setdefault(tag, []).append(body)
        parts = body.split("|")
        if tag == "USR" and len(parts) >= 3:
            uid, key, value = parts[0], parts[1], parts[2]
            idx.usrs_by_key[key] = (uid, value)
        elif tag == "LAW" and len(parts) >= 5:
            idx.laws[parts[0]] = LawRow(
                id=parts[0],
                name=parts[1],
                mechanism=parts[3],
                constraint=parts[4],
                raw=body,
            )
        elif tag == "PLR":
            idx.plr_rows.append(parts)
        elif tag == "NPC":
            idx.npc_rows.append(parts)
        elif tag == "SYS":
            idx.sys_rows.append(parts)
        elif tag == "BIZ":
            idx.biz_rows.append(parts)
        elif tag == "SCN":
            idx.scn_rows.append(parts)
    return idx


def usr_value(index: WarmIndex, key: str) -> str | None:
    pair = index.usrs_by_key.get(key)
    return pair[1] if pair else None


def law_constraint_tokens(index: WarmIndex, law_id: str) -> list[str]:
    law = index.laws.get(law_id)
    if not law:
        return []
    if not law.constraint or law.constraint == "-":
        return []
    return [
        t.strip()
        for t in law.constraint.replace(";", ",").split(",")
        if t.strip() and t.strip() != "-"
    ]


def pipeline_no_bundle(index: WarmIndex) -> bool:
    """True when LAW-PIPE20 constraint includes no_bundle (strict stage FSM)."""
    return "no_bundle" in law_constraint_tokens(index, "LAW-PIPE20")


def laws_for_stage(index: WarmIndex, stage: str, *, for_options: bool = False) -> list[LawRow]:
    """Filter linked laws by generic mechanism / constraint shape."""
    out: list[LawRow] = []
    for law in sorted(index.laws.values(), key=lambda r: r.id):
        mech = law.mechanism.lower()
        tokens = " ".join(law.tokens).lower()
        if for_options:
            if "opt_" in mech or "opt_" in tokens or "full_sentence" in tokens:
                out.append(law)
            continue
        if stage in ("oln", "sbd", "scr"):
            if mech in ("warm_prose",) or "warm_prose" in tokens:
                continue
            if mech.startswith("opt_"):
                continue
            if law.id.startswith("LAW-WX"):
                continue
            if law.id.startswith("LAW-LIB"):
                continue
            if law.id.startswith("LAW-OPT"):
                continue
            if law.id.startswith("LAW-PROSE"):
                continue
        out.append(law)
    return out
