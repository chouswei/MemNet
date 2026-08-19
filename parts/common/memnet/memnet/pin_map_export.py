"""Pin-map export — write out a cue pin_map (or empty-q outline).

MN-REQ-11.1–11.5 / #66. Ingest ≠ export. This cut emits shaped GQL of
``PinMapComposer`` (hard bounds). Empty q is 0.11 outline, not a dump of S.
CueConflict if |Q|>1. Re-ingest / identity merge is a later path (11.5 SHOULD).
Not Absorb. Not SnapshotStore. Not a chat dump. Hidden handle stays off the wire.
leftover nickname ``--anchor`` is a cue, not a store key. MUST NOT MERGE-by-id
on the way out. MUST NOT ``rag_query``.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from memnet.config import DEFAULT_QUERY_DEPTH, DEFAULT_QUERY_MAX_ROWS
from memnet.exceptions import MemNetError
from memnet.pin_map_composer import PinMapComposer, parse_find_locators


@dataclass(frozen=True)
class PinMapExportResult:
    """Shaped GQL body plus a one-line product header (not session snapshot)."""

    body: str
    header: str
    row_count: int
    cue: str
    conflict: bool
    path: str | None


def describe_export_cue(
    *,
    kind: str | None,
    locators: list[tuple[str, str]] | None,
    keyword: str | None,
    leftover_nicks: list[str] | None,
) -> str:
    """Human cue token for @EXPORT. leftover nicknames are named leftover."""
    parts: list[str] = []
    if kind and kind.strip():
        parts.append(f"kind:{kind.strip()}")
    for key, val in locators or []:
        parts.append(f"{key}={val}")
    if keyword and keyword.strip():
        parts.append(f"keyword:{keyword.strip()}")
    if leftover_nicks:
        parts.append("nickname")
    return ",".join(parts) if parts else "outline"


def export_pin_map(
    ss,
    *,
    kind: str | None = None,
    locators: list[tuple[str, str]] | list[str] | None = None,
    keyword: str | None = None,
    leftover_nicks: list[str] | None = None,
    depth: int = DEFAULT_QUERY_DEPTH,
    max_rows: int = DEFAULT_QUERY_MAX_ROWS,
    view: str | None = None,
    caller: str | None = None,
    agent: str | None = None,
    out_path: str | Path | None = None,
) -> PinMapExportResult:
    """Emit a bounded cue pin_map (or outline) as shaped GQL. Read-only."""
    parsed: list[tuple[str, str]]
    if locators and isinstance(locators[0], str):
        parsed = parse_find_locators([str(item) for item in locators])
    else:
        parsed = list(locators or [])  # type: ignore[arg-type]

    nicks = [n for n in (leftover_nicks or []) if n and str(n).strip()]
    cue = describe_export_cue(
        kind=kind,
        locators=parsed,
        keyword=keyword,
        leftover_nicks=nicks,
    )
    composer = PinMapComposer(ss)
    rows, text = composer.compose(
        anchor=None,
        anchors=nicks or None,
        kind=kind,
        locators=parsed,
        keyword=keyword,
        depth=depth,
        max_rows=max_rows,
        active_only=True,
        require_anchor=False,
        view=view,
        caller=caller,
        agent=agent,
    )
    body = text or ""
    conflict = "## CueConflict" in body
    written: str | None = None
    if out_path is not None:
        path = Path(out_path)
        try:
            path.write_text(body, encoding="utf-8")
        except OSError as exc:
            raise MemNetError("export_io", f"cannot write {path}: {exc}") from exc
        written = str(path)
    bits = [f"pin-map|cue={cue}|rows={len(rows)}"]
    if conflict:
        bits.append("conflict=1")
    if written:
        bits.append(f"path={written}")
    header = "@EXPORT: " + "|".join(bits)
    return PinMapExportResult(
        body=body,
        header=header,
        row_count=len(rows),
        cue=cue,
        conflict=conflict,
        path=written,
    )
