"""PinMapIngest_* roadmap stubs (MN-REQ-11). Deterministic locators; no client NEW."""

from __future__ import annotations

IMPLEMENTED = False


class PinMapIngestBase:
    implemented = False

    def ingest(self, *_args, **_kwargs) -> list:
        raise NotImplementedError(f"{type(self).__name__} is a roadmap stub")


class PinMapIngest_Sysml(PinMapIngestBase):
    """Selective SysML v2 pin maps as NODE|EDGE."""


class PinMapIngest_Codebase(PinMapIngestBase):
    """Selective codebase pins (modules/symbols)."""


class PinMapIngest_PcbaAto(PinMapIngestBase):
    """PCBA schematic pin maps from Atopile .ato (stable locators, not NEW)."""


class PinMapIngest_SkillsRules(PinMapIngestBase):
    """Agent skills/rules pin maps."""
