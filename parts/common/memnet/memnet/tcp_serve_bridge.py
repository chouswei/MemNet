"""TcpServeBridge — SysML name for memnet.serve (TCP localhost migration)."""

from __future__ import annotations

from memnet.serve import probe, run_serve, send_command

__all__ = ["probe", "run_serve", "send_command", "TcpServeBridge"]


class TcpServeBridge:
    """Length-prefixed JSON over TCP localhost (MN-REQ-06.3 migration)."""

    def run(self, host: str | None = None, port: int | None = None) -> None:
        run_serve(host=host, port=port)

    def send(self, argv: list[str], *, stdin: str | None = None) -> dict:
        return send_command(argv, stdin=stdin)

    def probe(self) -> bool:
        return probe()
