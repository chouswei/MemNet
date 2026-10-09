"""ServeBridge — optional TCP client to TcpServeBridge (migration)."""

from __future__ import annotations

from memnet.serve import probe, send_command


class ServeBridge:
    """Optional TCP path; prefer InProcessEngine."""

    def probe(self) -> bool:
        return probe()

    def send(self, argv: list[str], *, stdin: str | None = None) -> dict:
        from memnet.upgrade_retry import call_with_upgrade_retry

        def _once() -> dict:
            if not probe():
                raise ConnectionRefusedError("serve down")
            return send_command(argv, stdin=stdin)

        return call_with_upgrade_retry(_once)
