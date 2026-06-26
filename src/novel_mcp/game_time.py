"""Seed-agnostic simulation clock: canonical ISO hour axis for compare / advance."""

from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import datetime, timedelta

_ISO_RE = re.compile(
    r"^(?P<y>\d{4})-(?P<m>\d{2})-(?P<d>\d{2})T(?P<h>\d{2})$"
)
_YEAR_IN_PARENS_RE = re.compile(r"\((\d{4})\)")


@dataclass(frozen=True)
class GameTime:
    """In-world instant on the simulation axis: Y-M-D + hour (0–23), no minutes."""

    year: int
    month: int
    day: int
    hour: int

    def to_canonical(self) -> str:
        return f"{self.year:04d}-{self.month:02d}-{self.day:02d}T{self.hour:02d}"

    def to_datetime(self) -> datetime:
        return datetime(self.year, self.month, self.day, self.hour)

    def advance_hours(self, hours: int) -> GameTime:
        dt = self.to_datetime() + timedelta(hours=hours)
        return GameTime(dt.year, dt.month, dt.day, dt.hour)


def parse_game_time(value: str) -> GameTime | None:
    """Parse canonical axis field or legacy free-text containing (YYYY)."""
    value = value.strip()
    m = _ISO_RE.match(value)
    if m:
        return GameTime(
            int(m.group("y")),
            int(m.group("m")),
            int(m.group("d")),
            int(m.group("h")),
        )
    ym = _YEAR_IN_PARENS_RE.search(value)
    if ym:
        # Legacy: year only — neutral fallback for age math until ISO migration
        return GameTime(int(ym.group(1)), 1, 1, 0)
    if value[:4].isdigit() and len(value) >= 4:
        return GameTime(int(value[:4]), 1, 1, 0)
    return None


def year_from_sys_time(value: str) -> int | None:
    gt = parse_game_time(value)
    return gt.year if gt else None


def advance_sys_time(value: str, *, hours: int) -> str:
    """Return canonical @SYS 時間 field after advancing on the axis."""
    gt = parse_game_time(value)
    if gt is None:
        raise ValueError(f"cannot parse game time: {value!r}")
    return gt.advance_hours(hours).to_canonical()


def is_canonical_time(value: str) -> bool:
    return bool(_ISO_RE.match(value.strip()))


def sys_time_field_from_wire(line: str) -> str | None:
    line = line.strip()
    if not line.startswith("@SYS:"):
        return None
    body = line.split(":", 1)[1].strip()
    parts = body.split("|")
    return parts[2].strip() if len(parts) >= 3 else None


def check_sys_time_update(old: str, new: str) -> str | None:
    """Return @ERR wire fragment if update is invalid; None if ok."""
    new = new.strip()
    old = old.strip()
    if old == new:
        return None
    if not is_canonical_time(new):
        return f"@ERR: time_format|need YYYY-MM-DDTHH got {new!r}"
    new_gt = parse_game_time(new)
    if new_gt is None:
        return f"@ERR: time_format|need YYYY-MM-DDTHH got {new!r}"
    old_gt = parse_game_time(old)
    if old_gt is None:
        return None  # legacy → first ISO write allowed
    if new_gt.to_datetime() < old_gt.to_datetime():
        return (
            f"@ERR: time_regress|{old_gt.to_canonical()}->{new_gt.to_canonical()}"
        )
    return None
