"""ServeBridge — optional TCP client to TcpServeBridge (migration)."""

from __future__ import annotations

from memnet.serve import probe, send_command


class ServeBridge:
    """Optional TCP path; prefer InProcessEngine."""

    def probe(self) -> bool:
        return probe()

    def send(self, argv: list[str], *, stdin: str | None = None) -> dict:
        return send_command(argv, stdin=stdin)
