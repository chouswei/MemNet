"""LocalIpcGateway — stub (MN-REQ-06.2). LocalIpcFlow unallocated until implemented."""

from __future__ import annotations

IMPLEMENTED = False


class LocalIpcGateway:
    """Named pipe / AF_UNIX share of session registry — not implemented."""

    implemented = False

    def __init__(self) -> None:
        raise NotImplementedError(
            "LocalIpcGateway is a roadmap stub; use InProcessEngine or TcpServeBridge"
        )
