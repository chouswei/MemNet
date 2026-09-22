"""Look-only probes of MemNet services. No restart, no mutate."""

from __future__ import annotations

import socket
from collections.abc import Callable, Sequence
from dataclasses import dataclass
from urllib.parse import urlparse

import httpx


@dataclass(frozen=True)
class Probe:
    name: str
    target: str


@dataclass(frozen=True)
class ProbeResult:
    name: str
    target: str
    up: bool
    detail: str


def parse_probes(raw: str) -> tuple[Probe, ...]:
    """Parse 'name=target,name=target'. Targets are http(s):// or tcp://host:port."""
    items: list[Probe] = []
    seen: set[str] = set()
    for chunk in raw.split(","):
        piece = chunk.strip()
        if not piece:
            continue
        if "=" not in piece:
            raise SystemExit("MEMNET_STATUS_PROBES entries must be name=target")
        name, _, target = piece.partition("=")
        label = name.strip()
        dest = target.strip()
        if not label or not dest:
            raise SystemExit("MEMNET_STATUS_PROBES entries must be name=target")
        if label in seen:
            continue
        seen.add(label)
        items.append(Probe(name=label, target=dest))
    return tuple(items)


def probe_all(
    probes: Sequence[Probe],
    *,
    http_request: Callable[[str], int] | None = None,
    tcp_connect: Callable[[str, int], None] | None = None,
    timeout: float = 1.5,
) -> list[ProbeResult]:
    return [
        probe_one(item, http_request=http_request, tcp_connect=tcp_connect, timeout=timeout)
        for item in probes
    ]


def probe_one(
    probe: Probe,
    *,
    http_request: Callable[[str], int] | None = None,
    tcp_connect: Callable[[str, int], None] | None = None,
    timeout: float = 1.5,
) -> ProbeResult:
    target = probe.target
    if target.startswith("tcp://"):
        return _tcp(probe, tcp_connect=tcp_connect, timeout=timeout)
    if target.startswith("http://") or target.startswith("https://"):
        return _http(probe, http_request=http_request, timeout=timeout)
    return ProbeResult(probe.name, target, False, "unsupported target")


def _http(
    probe: Probe,
    *,
    http_request: Callable[[str], int] | None,
    timeout: float,
) -> ProbeResult:
    try:
        if http_request is None:
            response = httpx.get(probe.target, timeout=timeout, follow_redirects=False)
            code = response.status_code
        else:
            code = http_request(probe.target)
    except (httpx.HTTPError, OSError) as exc:
        return ProbeResult(probe.name, probe.target, False, type(exc).__name__)
    # Any HTTP answer means the listener is up (401 on /mcp is healthy for the gate).
    return ProbeResult(probe.name, probe.target, True, f"http {code}")


def _tcp(
    probe: Probe,
    *,
    tcp_connect: Callable[[str, int], None] | None,
    timeout: float,
) -> ProbeResult:
    parsed = urlparse(probe.target)
    host = parsed.hostname
    port = parsed.port
    if not host or not port:
        return ProbeResult(probe.name, probe.target, False, "bad tcp target")
    try:
        if tcp_connect is None:
            with socket.create_connection((host, port), timeout=timeout):
                pass
        else:
            tcp_connect(host, port)
    except OSError as exc:
        return ProbeResult(probe.name, probe.target, False, type(exc).__name__)
    return ProbeResult(probe.name, probe.target, True, "tcp open")
