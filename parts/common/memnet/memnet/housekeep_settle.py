"""HousekeepSettle — stats / stale / prune facade (SysML HousekeepSettle)."""

from __future__ import annotations

from memnet import housekeep as _hk


class HousekeepSettle:
    def __init__(self, session_store) -> None:
        self.ss = session_store

    def stats(self) -> dict:
        return _hk.stats(self.ss)

    def stale(self):
        return _hk.stale_rows(self.ss)

    def orphans(self):
        return _hk.orphan_rows(self.ss)

    def dangling(self):
        return _hk.dangling_rows(self.ss)

    def recyclable(self):
        return _hk.recyclable_rows(self.ss)

    def prune(self, *args, **kwargs):
        return _hk.prune_rows(self.ss, *args, **kwargs)
