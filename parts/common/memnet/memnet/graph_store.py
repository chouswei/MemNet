"""GraphStore — SysML alias for MemStore (NODE|EDGE indexes)."""

from __future__ import annotations

from memnet.mem_store import MemStore

GraphStore = MemStore

__all__ = ["GraphStore", "MemStore"]
