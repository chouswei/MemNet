"""HUD time labels from seed @USR game_time spec — novel_mcp stays calendar-agnostic."""

from __future__ import annotations

from collections.abc import Callable

from novel_mcp.game_time import GameTime

Formatter = Callable[[GameTime, dict[str, str]], str]

_FORMATTERS: dict[str, Formatter] = {}


def register_formatter(name: str, fn: Formatter) -> None:
    _FORMATTERS[name] = fn


def parse_time_spec(value: str) -> dict[str, str]:
    """Parse USR43 value: ``axis=iso;display=chongzhen_shichen;era_base=1628``."""
    out: dict[str, str] = {}
    for part in value.split(";"):
        part = part.strip()
        if not part:
            continue
        if "=" in part:
            key, val = part.split("=", 1)
            out[key.strip()] = val.strip()
        elif part == "iso_hour":
            out.setdefault("axis", "iso")
        else:
            out.setdefault("display", part)
    return out


def format_time_display(gt: GameTime, usr43_value: str | None) -> str:
    """HUD string: canonical axis + optional seed-registered era label."""
    canonical = gt.to_canonical()
    if not usr43_value:
        return canonical
    spec = parse_time_spec(usr43_value)
    display = spec.get("display")
    if not display or display in ("iso", "iso_only"):
        return canonical
    formatter = _FORMATTERS.get(display)
    if formatter is None:
        return canonical
    label = formatter(gt, spec)
    return f"{canonical}（{label}）"


def _register_builtin_formatters() -> None:
    from novel_mcp.calendars import chongzhen_shichen  # noqa: F401


_register_builtin_formatters()
