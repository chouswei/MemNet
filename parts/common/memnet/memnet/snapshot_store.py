"""SnapshotStore — named-session durable file (MN-REQ-01; not MN-REQ-11 pins)."""

from __future__ import annotations

from memnet.snapshot import load_snapshot, snapshot_text, write_snapshot

SnapshotStore = type(
    "SnapshotStore",
    (),
    {
        "write": staticmethod(write_snapshot),
        "load": staticmethod(load_snapshot),
        "text": staticmethod(snapshot_text),
    },
)

__all__ = ["SnapshotStore", "load_snapshot", "snapshot_text", "write_snapshot"]
