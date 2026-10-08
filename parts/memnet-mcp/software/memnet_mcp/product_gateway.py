"""MemNet product gateway — a memnet-mcp capability (MN-REQ-06.12).

One process routes a serve envelope to the owning ``memnet serve``.
Products never open a second product's sessions. Args and stdin are
forwarded unchanged. Engine ``@ERR`` / ``@WRN`` / ``@STAT`` lines and
``exit_code`` come back as the backend wrote them, except the session
list membership filter.

When ``MEMNET_GATEWAY_CONFIG`` is unset, this module is not started.
stdio and streamable-http memnet-mcp stay single-backend.
"""

from __future__ import annotations

import hashlib
import hmac
import ipaddress
import json
import os
import re
import sys
import threading
import time
from dataclasses import dataclass, field
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any
from urllib.parse import urlsplit

from memnet.serve import is_loopback_bind_host, probe, send_command

DEFAULT_BIND = "127.0.0.1"
DEFAULT_PORT = 18770
DEFAULT_PATH = "/gateway"
DEFAULT_BODY_MAX = 4 * 1024 * 1024
DEFAULT_TIMEOUT_S = 30.0
DEFAULT_VERSION_CACHE_S = 15.0
_CGNAT = ipaddress.ip_network("100.64.0.0/10")
_TAILSCALE_V6 = ipaddress.ip_network("fd7a:115c:a1e0::/48")
_STAT_SESSIONS = re.compile(r"^@STAT:\s*sessions\|(\d+)/(\d+)\s*$")
_CLIENT_TIMEOUT = "@ERR: serve_timeout|wait exceeded"
_PLACE_CMDS = frozenset({"open"})
_REFUSED_ARGV0 = frozenset({"admin", "serve"})


class GatewayConfigError(ValueError):
    """Registry file is not usable. The listener does not start."""


class GatewayBindError(RuntimeError):
    """Bind host is public, or is not loopback or tailnet."""


@dataclass
class HandleResult:
    http_status: int
    exit_code: int
    stdout: str
    stderr: str

    def envelope(self) -> dict[str, Any]:
        return {
            "exit_code": self.exit_code,
            "stdout": self.stdout,
            "stderr": self.stderr,
        }


@dataclass
class Backend:
    id: str
    host: str
    port: int


@dataclass
class Credential:
    id: str
    sha256: str
    revoked: bool = False


@dataclass
class Product:
    id: str
    backends: list[str]
    houses: dict[str, str]
    pinned_version: str
    credentials: list[Credential]


@dataclass
class OwnerRow:
    product: str
    backend: str


@dataclass
class Counts:
    requests: int = 0
    gateway_refusals: int = 0
    backend_errors: int = 0


@dataclass
class ProductGateway:
    """In-process router. ``start`` listens; ``handle`` is the contract."""

    backends: dict[str, Backend]
    products: dict[str, Product]
    bind_host: str
    bind_port: int
    path: str
    body_max_bytes: int
    state_path: str
    admin_sha256: str | None
    timeout_s: float = DEFAULT_TIMEOUT_S
    version_cache_s: float = DEFAULT_VERSION_CACHE_S
    owners: dict[str, OwnerRow] = field(default_factory=dict)
    counts: dict[str, Counts] = field(default_factory=dict)
    _lock: threading.Lock = field(default_factory=threading.Lock)
    _ver_cache: dict[str, tuple[float, str | None]] = field(default_factory=dict)
    _httpd: ThreadingHTTPServer | None = field(default=None, repr=False)
    _thread: threading.Thread | None = field(default=None, repr=False)

    @classmethod
    def load(
        cls,
        path: str,
        *,
        bind_host: str | None = None,
        bind_port: int | None = None,
    ) -> ProductGateway:
        try:
            raw = json.loads(Path(path).read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            raise GatewayConfigError(f"gateway config: {exc}") from exc
        if not isinstance(raw, dict):
            raise GatewayConfigError("gateway config must be a JSON object")
        return cls.from_dict(raw, bind_host=bind_host, bind_port=bind_port)

    @classmethod
    def from_dict(
        cls,
        raw: dict[str, Any],
        *,
        bind_host: str | None = None,
        bind_port: int | None = None,
    ) -> ProductGateway:
        backends = _parse_backends(raw.get("backends"))
        products = _parse_products(raw.get("products"), backends)
        host = bind_host if bind_host is not None else str(raw.get("bind") or DEFAULT_BIND)
        port = bind_port if bind_port is not None else int(raw.get("port") or DEFAULT_PORT)
        path = str(raw.get("path") or DEFAULT_PATH)
        if not path.startswith("/"):
            path = "/" + path
        body_max = int(raw.get("body_max_bytes") or DEFAULT_BODY_MAX)
        if body_max < 1:
            raise GatewayConfigError("body_max_bytes must be positive")
        state_path = str(raw.get("state_path") or "").strip()
        if not state_path:
            raise GatewayConfigError("state_path is required")
        admin = raw.get("admin") or {}
        admin_sha = None
        if isinstance(admin, dict) and admin.get("sha256"):
            admin_sha = _hex64(str(admin["sha256"]), what="admin.sha256")
        timeout_s = float(raw.get("backend_timeout_s") or DEFAULT_TIMEOUT_S)
        version_cache_s = float(
            raw["version_cache_s"] if "version_cache_s" in raw else DEFAULT_VERSION_CACHE_S
        )
        gw = cls(
            backends=backends,
            products=products,
            bind_host=host,
            bind_port=port,
            path=path.rstrip("/") or "/",
            body_max_bytes=body_max,
            state_path=state_path,
            admin_sha256=admin_sha,
            timeout_s=timeout_s,
            version_cache_s=version_cache_s,
            counts={pid: Counts() for pid in products},
        )
        gw._load_owners()
        return gw

    @property
    def admin_path(self) -> str:
        return self.path.rstrip("/") + "/admin/counts"

    @property
    def bound_port(self) -> int:
        if self._httpd is not None:
            return int(self._httpd.server_address[1])
        return self.bind_port

    def start(self) -> None:
        validate_gateway_bind(self.bind_host)
        handler = _handler_factory(self)
        self._httpd = ThreadingHTTPServer((self.bind_host, self.bind_port), handler)
        self._thread = threading.Thread(
            target=self._httpd.serve_forever,
            name="memnet-product-gateway",
            daemon=True,
        )
        self._thread.start()

    def serve_forever(self) -> None:
        validate_gateway_bind(self.bind_host)
        handler = _handler_factory(self)
        httpd = ThreadingHTTPServer((self.bind_host, self.bind_port), handler)
        self._httpd = httpd
        host, port = httpd.server_address[:2]
        names = ",".join(sorted(self.products))
        sys.stderr.write(f"MEMNET_GATEWAY={host}:{port}{self.path} products={names}\n")
        sys.stderr.flush()
        try:
            httpd.serve_forever()
        finally:
            httpd.server_close()

    def stop(self) -> None:
        if self._httpd is not None:
            self._httpd.shutdown()
            self._httpd.server_close()
            self._httpd = None
        if self._thread is not None:
            self._thread.join(timeout=2)
            self._thread = None

    def counts_public(self) -> dict[str, Any]:
        with self._lock:
            products = {
                pid: {
                    "requests": self.counts[pid].requests,
                    "gateway_refusals": self.counts[pid].gateway_refusals,
                    "backend_errors": self.counts[pid].backend_errors,
                }
                for pid in self.products
            }
        return {"products": products}

    def handle(
        self,
        *,
        method: str,
        path: str,
        authorization: str | None,
        body: bytes,
    ) -> HandleResult:
        route = urlsplit(path).path
        if method == "GET" and route == self.admin_path:
            return self._admin(authorization)
        if method != "POST" or route != self.path:
            return _gateway("bad_request", "POST " + self.path, http=404)
        if len(body) > self.body_max_bytes:
            return _gateway(
                "body_too_large",
                f"{len(body)} bytes exceeds {self.body_max_bytes}",
                http=413,
            )
        try:
            payload = json.loads(body.decode("utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError):
            return _gateway("bad_request", "body must be a JSON object", http=400)
        if not isinstance(payload, dict):
            return _gateway("bad_request", "body must be a JSON object", http=400)
        token = _bearer(authorization)
        product = self._product_for_token(token) if token else None
        if product is None:
            return _gateway("auth", "bearer required", http=401)
        self._bump(product.id, requests=1)
        result = self._dispatch(product, payload)
        if result.stderr.startswith("@ERR: gateway_"):
            self._bump(product.id, refusals=1)
        elif result.exit_code != 0:
            self._bump(product.id, backend_errors=1)
        return result

    def _admin(self, authorization: str | None) -> HandleResult:
        if not self.admin_sha256:
            return _gateway("unconfigured", "admin counts", http=404)
        token = _bearer(authorization)
        digest = hashlib.sha256(token.encode()).hexdigest() if token else ""
        if not token or not hmac.compare_digest(digest, self.admin_sha256):
            return _gateway("auth", "admin bearer required", http=401)
        body = json.dumps(self.counts_public(), ensure_ascii=False)
        return HandleResult(200, 0, body, "")

    def _dispatch(self, product: Product, payload: dict[str, Any]) -> HandleResult:
        namespace = payload.get("namespace", payload.get("product"))
        if namespace is not None and namespace != product.id:
            return _gateway("auth", "credential is not scoped to this namespace", http=401)
        args = payload.get("args")
        if not isinstance(args, list) or not all(isinstance(item, str) for item in args):
            return _gateway("bad_request", "args must be a list of strings", http=400)
        argv = list(args)
        stdin = payload.get("stdin", None)
        if stdin is not None and not isinstance(stdin, str):
            return _gateway("bad_request", "stdin must be a string", http=400)
        if not argv or argv[0] in _REFUSED_ARGV0:
            return _gateway("forbidden", "command is not forwarded", http=403)
        try:
            session = _session_of(payload, argv)
        except ValueError as exc:
            return _gateway("bad_request", str(exc), http=400)
        kind = _kind(argv)
        house = payload.get("house")
        backend_pin = payload.get("backend")
        if house is not None and not isinstance(house, str):
            return _gateway("bad_request", "house must be a string", http=400)
        if backend_pin is not None and not isinstance(backend_pin, str):
            return _gateway("bad_request", "backend must be a string", http=400)
        if kind == "list":
            return self._list(product, argv, stdin)
        if kind == "place":
            return self._place(product, argv, stdin, house=house, backend_pin=backend_pin)
        if kind == "probe":
            return self._probe(product, argv, stdin, house=house, backend_pin=backend_pin)
        if not session:
            return _gateway("bad_request", "session required", http=400)
        return self._owned(
            product,
            argv,
            stdin,
            session,
            house=house,
            backend_pin=backend_pin,
        )

    def _place(
        self,
        product: Product,
        argv: list[str],
        stdin: str | None,
        *,
        house: str | None,
        backend_pin: str | None,
    ) -> HandleResult:
        chosen, err = self._select_new(product, house=house, backend_pin=backend_pin)
        if err is not None or chosen is None:
            return err or _gateway("backend_unreachable", "no backend", http=502)
        raw = self._forward(chosen, argv, stdin)
        if raw is None:
            return _gateway("backend_unreachable", chosen.id, http=502)
        result = _from_backend(raw)
        if result.exit_code == 0:
            for sid in _sids(result.stdout, result.stderr):
                self._remember(sid, product.id, chosen.id)
        return result

    def _probe(
        self,
        product: Product,
        argv: list[str],
        stdin: str | None,
        *,
        house: str | None,
        backend_pin: str | None,
    ) -> HandleResult:
        chosen, err = self._select_new(product, house=house, backend_pin=backend_pin)
        if err is not None or chosen is None:
            return err or _gateway("backend_unreachable", "no backend", http=502)
        raw = self._forward(chosen, argv, stdin)
        if raw is None:
            return _gateway("backend_unreachable", chosen.id, http=502)
        return _from_backend(raw)

    def _owned(
        self,
        product: Product,
        argv: list[str],
        stdin: str | None,
        session: str,
        *,
        house: str | None,
        backend_pin: str | None,
    ) -> HandleResult:
        with self._lock:
            row = self.owners.get(session)
        if row is None or row.product != product.id or row.backend not in product.backends:
            return _gateway("forbidden_session", "not owned by this product", http=403)
        backend = self.backends[row.backend]
        pinned = self._named_backend(product, house=house, backend_pin=backend_pin)
        if isinstance(pinned, HandleResult):
            return pinned
        if pinned is not None and pinned.id != backend.id:
            return _gateway("forbidden_session", "session owned by another backend", http=403)
        check = self._require_live(backend, product)
        if check is not None:
            return check
        raw = self._forward(backend, argv, stdin)
        if raw is None:
            return _gateway("backend_unreachable", backend.id, http=502)
        result = _from_backend(raw)
        if result.exit_code == 0 and len(argv) >= 2 and argv[0] == "session" and argv[1] == "close":
            self._forget(session)
        elif result.exit_code == 0:
            for sid in _sids(result.stdout, result.stderr):
                self._remember_new(sid, product.id, backend.id)
        return result

    def _list(self, product: Product, argv: list[str], stdin: str | None) -> HandleResult:
        kept: list[str] = []
        others: list[str] = []
        stderr_parts: list[str] = []
        cap: str | None = None
        saw_ok = False
        gateway_err = False
        exit_code = 0
        for backend_id in product.backends:
            backend = self.backends[backend_id]
            check = self._require_live(backend, product)
            if check is not None:
                gateway_err = True
                stderr_parts.append(check.stderr)
                continue
            raw = self._forward(backend, argv, stdin)
            if raw is None:
                gateway_err = True
                stderr_parts.append(_gateway("backend_unreachable", backend.id, http=502).stderr)
                continue
            saw_ok = True
            if int(raw.get("exit_code", 1)) != 0 and exit_code == 0:
                exit_code = int(raw.get("exit_code", 1))
            stdout = raw.get("stdout") or ""
            stderr = raw.get("stderr") or ""
            if stderr:
                stderr_parts.append(stderr if stderr.endswith("\n") else stderr + "\n")
            owned = self._owned_sids(product.id, backend.id)
            piece, piece_cap = _filter_sessions(stdout, owned)
            kept.extend(piece)
            if piece_cap and cap is None:
                cap = piece_cap
            for line in stdout.splitlines():
                if line.startswith("@SESSION:"):
                    continue
                if _STAT_SESSIONS.match(line):
                    continue
                others.append(line)
        lines: list[str] = []
        if cap is not None or kept:
            lines.append(f"@STAT: sessions|{len(kept)}/{cap or 0}")
        lines.extend(kept)
        lines.extend(others)
        stdout_out = ("\n".join(lines) + "\n") if lines else ""
        if gateway_err:
            exit_code = 2
        if not saw_ok and gateway_err:
            return HandleResult(502, 2, stdout_out, "".join(stderr_parts))
        return HandleResult(200, exit_code, stdout_out, "".join(stderr_parts))

    def _select_new(
        self,
        product: Product,
        *,
        house: str | None,
        backend_pin: str | None,
    ) -> tuple[Backend | None, HandleResult | None]:
        named = self._named_backend(product, house=house, backend_pin=backend_pin)
        if isinstance(named, HandleResult):
            return None, named
        if named is not None:
            check = self._require_live(named, product)
            if check is not None:
                return None, check
            return named, None
        mismatch: HandleResult | None = None
        unreachable: HandleResult | None = None
        for backend_id in product.backends:
            backend = self.backends[backend_id]
            version = self._version(backend)
            if version is None:
                unreachable = _gateway("backend_unreachable", backend.id, http=502)
                continue
            if version != product.pinned_version:
                mismatch = _gateway(
                    "backend_version_mismatch",
                    f"{backend.id}|got {version}|pin {product.pinned_version}",
                    http=409,
                )
                continue
            return backend, None
        if mismatch is not None:
            return None, mismatch
        return None, unreachable or _gateway("backend_unreachable", "none", http=502)

    def _named_backend(
        self,
        product: Product,
        *,
        house: str | None,
        backend_pin: str | None,
    ) -> Backend | HandleResult | None:
        if backend_pin:
            if backend_pin not in product.backends or backend_pin not in self.backends:
                return _gateway("forbidden", "backend is not in this product", http=403)
            return self.backends[backend_pin]
        if house:
            target = product.houses.get(house)
            if not target or target not in product.backends:
                return _gateway("forbidden", "house is not in this product", http=403)
            return self.backends[target]
        return None

    def _require_live(self, backend: Backend, product: Product) -> HandleResult | None:
        version = self._version(backend)
        if version is None:
            return _gateway("backend_unreachable", backend.id, http=502)
        if version != product.pinned_version:
            return _gateway(
                "backend_version_mismatch",
                f"{backend.id}|got {version}|pin {product.pinned_version}",
                http=409,
            )
        return None

    def _version(self, backend: Backend) -> str | None:
        now = time.monotonic()
        with self._lock:
            hit = self._ver_cache.get(backend.id)
            if (
                hit is not None
                and self.version_cache_s > 0
                and (now - hit[0]) < self.version_cache_s
            ):
                return hit[1]
        version: str | None = None
        if probe(host=backend.host, port=backend.port):
            try:
                raw = send_command(
                    ["version"],
                    host=backend.host,
                    port=backend.port,
                    timeout=self.timeout_s,
                )
            except (OSError, json.JSONDecodeError):
                raw = None
            if isinstance(raw, dict):
                for line in (raw.get("stdout") or "").splitlines():
                    if line.startswith("@VER: memnet|"):
                        version = line.split("|", 1)[1].strip()
                        break
        with self._lock:
            self._ver_cache[backend.id] = (now, version)
        return version

    def _forward(
        self, backend: Backend, argv: list[str], stdin: str | None
    ) -> dict[str, Any] | None:
        try:
            raw = send_command(
                list(argv),
                stdin=stdin,
                host=backend.host,
                port=backend.port,
                timeout=self.timeout_s,
            )
        except (OSError, json.JSONDecodeError):
            return None
        if not isinstance(raw, dict):
            return None
        err = (raw.get("stderr") or "").strip()
        if err == _CLIENT_TIMEOUT and not (raw.get("stdout") or "").strip():
            return None
        return raw

    def _product_for_token(self, token: str) -> Product | None:
        digest = hashlib.sha256(token.encode()).hexdigest()
        found: Product | None = None
        for product in self.products.values():
            for cred in product.credentials:
                if cred.revoked:
                    continue
                if hmac.compare_digest(cred.sha256, digest):
                    if found is not None:
                        return None
                    found = product
        return found

    def _remember(self, sid: str, product_id: str, backend_id: str) -> None:
        with self._lock:
            current = self.owners.get(sid)
            if current is not None and (
                current.product != product_id or current.backend != backend_id
            ):
                return
            self.owners[sid] = OwnerRow(product=product_id, backend=backend_id)
            self._save_owners_locked()

    def _remember_new(self, sid: str, product_id: str, backend_id: str) -> None:
        with self._lock:
            if sid in self.owners:
                return
            self.owners[sid] = OwnerRow(product=product_id, backend=backend_id)
            self._save_owners_locked()

    def _forget(self, sid: str) -> None:
        with self._lock:
            if sid in self.owners:
                del self.owners[sid]
                self._save_owners_locked()

    def _owned_sids(self, product_id: str, backend_id: str) -> set[str]:
        with self._lock:
            return {
                sid
                for sid, row in self.owners.items()
                if row.product == product_id and row.backend == backend_id
            }

    def _bump(
        self,
        product_id: str,
        *,
        requests: int = 0,
        refusals: int = 0,
        backend_errors: int = 0,
    ) -> None:
        with self._lock:
            row = self.counts.setdefault(product_id, Counts())
            row.requests += requests
            row.gateway_refusals += refusals
            row.backend_errors += backend_errors

    def _load_owners(self) -> None:
        if not os.path.exists(self.state_path):
            return
        try:
            raw = json.loads(Path(self.state_path).read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            raise GatewayConfigError(f"owner state: {exc}") from exc
        sessions = raw.get("sessions") if isinstance(raw, dict) else None
        if not isinstance(sessions, dict):
            raise GatewayConfigError("owner state sessions must be an object")
        owners: dict[str, OwnerRow] = {}
        for sid, row in sessions.items():
            if not isinstance(sid, str) or not isinstance(row, dict):
                raise GatewayConfigError("owner row must map a session id to an object")
            product = row.get("product")
            backend = row.get("backend")
            if product not in self.products or backend not in self.backends:
                raise GatewayConfigError("owner row names an unknown product or backend")
            if backend not in self.products[product].backends:
                raise GatewayConfigError("owner row backend is outside the product")
            owners[sid] = OwnerRow(product=str(product), backend=str(backend))
        self.owners = owners

    def _save_owners_locked(self) -> None:
        parent = os.path.dirname(self.state_path)
        if parent:
            os.makedirs(parent, exist_ok=True)
        payload = {
            "sessions": {
                sid: {"product": row.product, "backend": row.backend}
                for sid, row in self.owners.items()
            }
        }
        tmp = self.state_path + ".tmp"
        Path(tmp).write_text(
            json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
        )
        os.replace(tmp, self.state_path)


def validate_gateway_bind(host: str) -> None:
    """Refuse a public bind unless MEMNET_GATEWAY_ALLOW_PUBLIC=1."""
    if is_loopback_bind_host(host) or _is_tailnet(host):
        return
    if _allow_public():
        sys.stderr.write(
            f"WARNING: memnet product gateway binding to public {host!r} "
            "(MEMNET_GATEWAY_ALLOW_PUBLIC=1).\n"
        )
        sys.stderr.flush()
        return
    raise GatewayBindError(
        f"refusing public gateway bind {host!r}: loopback or tailnet only "
        "(set MEMNET_GATEWAY_ALLOW_PUBLIC=1 to override)"
    )


def serve_from_env(*, host: str | None = None, port: int | None = None) -> None:
    path = os.environ.get("MEMNET_GATEWAY_CONFIG", "").strip()
    if not path:
        raise SystemExit(_unconfigured())
    try:
        gateway = ProductGateway.load(path, bind_host=host, bind_port=port)
    except (GatewayConfigError, GatewayBindError) as exc:
        sys.stderr.write(f"@ERR: gateway_bad_request|{exc}\n")
        raise SystemExit(2) from exc
    gateway.serve_forever()


def _unconfigured() -> int:
    sys.stderr.write("@ERR: gateway_unconfigured|set MEMNET_GATEWAY_CONFIG\n")
    return 2


def _allow_public() -> bool:
    raw = os.environ.get("MEMNET_GATEWAY_ALLOW_PUBLIC", "").strip().lower()
    return raw in {"1", "true", "yes", "on"}


def _is_tailnet(host: str) -> bool:
    try:
        addr = ipaddress.ip_address(host.strip())
    except ValueError:
        return False
    if addr.version == 4:
        return addr in _CGNAT
    return addr in _TAILSCALE_V6


def _gateway(code: str, detail: str, *, http: int) -> HandleResult:
    return HandleResult(
        http_status=http,
        exit_code=2,
        stdout="",
        stderr=f"@ERR: gateway_{code}|{detail}\n",
    )


def _from_backend(raw: dict[str, Any]) -> HandleResult:
    return HandleResult(
        http_status=200,
        exit_code=int(raw.get("exit_code", 1)),
        stdout=raw.get("stdout") or "",
        stderr=raw.get("stderr") or "",
    )


def _bearer(authorization: str | None) -> str | None:
    if not authorization:
        return None
    scheme, _, rest = authorization.strip().partition(" ")
    if scheme.lower() != "bearer":
        return None
    token = rest.strip()
    if not token or " " in token:
        return None
    return token


def _hex64(value: str, *, what: str) -> str:
    text = value.strip().lower()
    if len(text) != 64 or any(ch not in "0123456789abcdef" for ch in text):
        raise GatewayConfigError(f"{what} must be a sha256 hex digest")
    return text


def _parse_backends(raw: Any) -> dict[str, Backend]:
    if not isinstance(raw, dict) or not raw:
        raise GatewayConfigError("backends must be a non-empty object")
    out: dict[str, Backend] = {}
    for key, row in raw.items():
        if not isinstance(key, str) or not isinstance(row, dict):
            raise GatewayConfigError("backend entry must be an object")
        host = str(row.get("host") or "").strip()
        if not host:
            raise GatewayConfigError(f"backend {key} needs host")
        try:
            port = int(row["port"])
        except (KeyError, TypeError, ValueError) as exc:
            raise GatewayConfigError(f"backend {key} needs port") from exc
        if port < 1 or port > 65535:
            raise GatewayConfigError(f"backend {key} port out of range")
        out[key] = Backend(id=key, host=host, port=port)
    return out


def _parse_products(raw: Any, backends: dict[str, Backend]) -> dict[str, Product]:
    if not isinstance(raw, dict) or not raw:
        raise GatewayConfigError("products must be a non-empty object")
    out: dict[str, Product] = {}
    seen_hashes: dict[str, str] = {}
    for key, row in raw.items():
        if not isinstance(key, str) or not isinstance(row, dict):
            raise GatewayConfigError("product entry must be an object")
        allowed = row.get("backends")
        if not isinstance(allowed, list) or not allowed:
            raise GatewayConfigError(f"product {key} needs backends")
        if not all(isinstance(item, str) and item in backends for item in allowed):
            raise GatewayConfigError(f"product {key} names an unknown backend")
        houses_raw = row.get("houses") or {}
        if not isinstance(houses_raw, dict):
            raise GatewayConfigError(f"product {key} houses must be an object")
        houses: dict[str, str] = {}
        for house, backend_id in houses_raw.items():
            if not isinstance(house, str) or not isinstance(backend_id, str):
                raise GatewayConfigError(f"product {key} house must map to a backend id")
            if backend_id not in allowed:
                raise GatewayConfigError(f"product {key} house {house} is outside its backends")
            houses[house] = backend_id
        pin = str(row.get("pinned_version") or "").strip()
        if not pin:
            raise GatewayConfigError(f"product {key} needs pinned_version")
        creds_raw = row.get("credentials")
        if not isinstance(creds_raw, list) or not creds_raw:
            raise GatewayConfigError(f"product {key} needs credentials")
        creds: list[Credential] = []
        for cred in creds_raw:
            if not isinstance(cred, dict):
                raise GatewayConfigError(f"product {key} credential must be an object")
            cid = str(cred.get("id") or "").strip()
            if not cid:
                raise GatewayConfigError(f"product {key} credential needs id")
            digest = _hex64(str(cred.get("sha256") or ""), what=f"product {key} credential")
            revoked = bool(cred.get("revoked", False))
            if not revoked:
                other = seen_hashes.get(digest)
                if other is not None:
                    raise GatewayConfigError("credential hash is shared by two products")
                seen_hashes[digest] = key
            creds.append(Credential(id=cid, sha256=digest, revoked=revoked))
        out[key] = Product(
            id=key,
            backends=list(allowed),
            houses=houses,
            pinned_version=pin,
            credentials=creds,
        )
    return out


def _session_of(payload: dict[str, Any], argv: list[str]) -> str | None:
    field_sid = payload.get("session")
    if field_sid is not None and not isinstance(field_sid, str):
        raise ValueError("session must be a string")
    from_field = field_sid.strip() if isinstance(field_sid, str) and field_sid.strip() else None
    from_args: str | None = None
    if "--session" in argv:
        idx = argv.index("--session")
        if idx + 1 >= len(argv) or not argv[idx + 1]:
            raise ValueError("session flag needs a value")
        from_args = argv[idx + 1]
    elif len(argv) >= 3 and argv[0] == "session" and argv[1] == "close":
        from_args = argv[2]
    if from_field and from_args and from_field != from_args:
        raise ValueError("session field and args disagree")
    return from_field or from_args


def _kind(argv: list[str]) -> str:
    if argv[0] == "version":
        return "probe"
    if argv[0] == "session" and len(argv) >= 2:
        if argv[1] in _PLACE_CMDS:
            return "place"
        if argv[1] == "list":
            return "list"
        if argv[1] == "load" and "--file" in argv and "--session" not in argv:
            return "place"
        if argv[1] == "expire-status":
            return "probe"
    return "owned"


def _sids(stdout: str, stderr: str) -> list[str]:
    found: list[str] = []
    for block in (stdout, stderr):
        for line in block.splitlines():
            if not line.startswith("@SESSION:"):
                continue
            sid = line.split(":", 1)[1].strip().split("|", 1)[0].strip()
            if sid and sid not in {"none", "closed"} and sid not in found:
                found.append(sid)
    return found


def _filter_sessions(stdout: str, owned: set[str]) -> tuple[list[str], str | None]:
    kept: list[str] = []
    cap: str | None = None
    for line in stdout.splitlines():
        match = _STAT_SESSIONS.match(line)
        if match:
            cap = match.group(2)
            continue
        if line.startswith("@SESSION:"):
            sid = line.split(":", 1)[1].strip().split("|", 1)[0].strip()
            if sid in owned:
                kept.append(line)
    return kept, cap


def _handler_factory(gateway: ProductGateway) -> type[BaseHTTPRequestHandler]:
    class Handler(BaseHTTPRequestHandler):
        protocol_version = "HTTP/1.1"

        def do_POST(self) -> None:  # noqa: N802
            self._respond()

        def do_GET(self) -> None:  # noqa: N802
            self._respond()

        def _respond(self) -> None:
            length = int(self.headers.get("Content-Length") or "0")
            if length > gateway.body_max_bytes:
                result = _gateway(
                    "body_too_large",
                    f"{length} bytes exceeds {gateway.body_max_bytes}",
                    http=413,
                )
            else:
                data = self.rfile.read(length) if length else b""
                result = gateway.handle(
                    method=self.command,
                    path=self.path,
                    authorization=self.headers.get("Authorization"),
                    body=data,
                )
            encoded = json.dumps(result.envelope(), ensure_ascii=False).encode("utf-8")
            self.send_response(result.http_status)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.send_header("Content-Length", str(len(encoded)))
            self.end_headers()
            self.wfile.write(encoded)

        def log_message(self, fmt: str, *args: Any) -> None:
            return

    return Handler
