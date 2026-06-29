"""Live HTTP E2E: novel-mobile world create, setup FSM, N beats."""

from __future__ import annotations

import argparse
import json
import socket
import sys
import time
import urllib.error
import urllib.request
import uuid
from typing import Any

ROOT = __import__("pathlib").Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "applications" / "novel_cursor"))

from env_load import load_dotenv  # noqa: E402

load_dotenv()

USER_HEADER = "X-Novel-User-Id"
WORLD_HEADER = "X-Novel-World-Id"
ACK_STEPS = frozenset({"narrate_open", "narrate_pre_pick", "narrate_transmigration"})
BEAT_TIMEOUT_S = 600
POLL_INTERVAL_S = 2


class E2EClient:
    def __init__(self, base_url: str, user_id: str, token: str | None = None) -> None:
        self.base = base_url.rstrip("/")
        self.user_id = user_id
        self.token = token
        self.world_id: str | None = None

    def _headers(self) -> dict[str, str]:
        h: dict[str, str] = {"Content-Type": "application/json", USER_HEADER: self.user_id}
        if self.world_id:
            h[WORLD_HEADER] = self.world_id
        if self.token:
            h["Authorization"] = f"Bearer {self.token}"
        return h

    def request(
        self,
        method: str,
        path: str,
        body: dict[str, Any] | None = None,
    ) -> tuple[int, Any]:
        data = None
        if body is not None:
            data = json.dumps(body, ensure_ascii=False).encode("utf-8")
        req = urllib.request.Request(
            self.base + path,
            data=data,
            headers=self._headers(),
            method=method,
        )
        try:
            with urllib.request.urlopen(req, timeout=120) as resp:
                raw = resp.read().decode("utf-8")
                return resp.status, json.loads(raw) if raw else None
        except urllib.error.HTTPError as err:
            raw = err.read().decode("utf-8")
            try:
                payload = json.loads(raw) if raw else {"error": err.reason}
            except json.JSONDecodeError:
                payload = {"raw": raw, "error": err.reason}
            return err.code, payload

    def get(self, path: str) -> tuple[int, Any]:
        return self.request("GET", path)

    def post(self, path: str, body: dict[str, Any] | None = None) -> tuple[int, Any]:
        return self.request("POST", path, body)


def _port_open(host: str, port: int) -> bool:
    s = socket.socket()
    try:
        return s.connect_ex((host, port)) == 0
    finally:
        s.close()


def _fail(msg: str, code: int = 1) -> int:
    print(f"FAIL: {msg}", file=sys.stderr)
    return code


def _setup_step(client: E2EClient, setup: dict[str, Any]) -> bool:
    """Return True when setup_complete."""
    if setup.get("setup_complete"):
        return True
    guidance = setup.get("setup_guidance") or {}
    na = guidance.get("next_action", "")
    print(f"  setup next_action={na}", file=sys.stderr)

    if na == "start_play":
        return bool(setup.get("setup_complete"))

    if na in ACK_STEPS:
        code, data = client.post("/api/setup/ack", {"step": na})
        if code != 200:
            raise RuntimeError(f"ack {na} HTTP {code}: {data}")
        return bool(data.get("setup_complete"))

    if na == "narrate_ask_name":
        code, data = client.post("/api/setup/profile", {"name": "北見硝"})
        if code != 200:
            raise RuntimeError(f"profile name HTTP {code}: {data}")
        return bool(data.get("setup_complete"))

    if na == "narrate_ask_gender":
        code, data = client.post("/api/setup/profile", {"gender": "男"})
        if code != 200:
            raise RuntimeError(f"profile gender HTTP {code}: {data}")
        return bool(data.get("setup_complete"))

    if na == "commit_player_profile":
        prof = setup.get("profile") or {}
        body: dict[str, str] = {}
        if not prof.get("name_set"):
            body["name"] = "北見硝"
        if not prof.get("gender_set"):
            body["gender"] = "男"
        code, data = client.post("/api/setup/profile", body)
        if code != 200:
            raise RuntimeError(f"profile fix HTTP {code}: {data}")
        return bool(data.get("setup_complete"))

    if na.startswith("pick_"):
        slot = na.replace("pick_", "", 1)
        code, cat = client.get("/api/catalog")
        if code != 200:
            raise RuntimeError(f"catalog HTTP {code}: {cat}")
        slot_data = (cat.get("slots") or {}).get(slot) or {}
        offer_ids = slot_data.get("offer_ids") or []
        if not offer_ids:
            arts = slot_data.get("arts") or []
            if arts:
                offer_ids = [arts[0].get("id")]
        if not offer_ids:
            raise RuntimeError(f"no offers for slot {slot}")
        art_id = offer_ids[0]
        code, data = client.post("/api/setup/pick", {"slot": slot, "art_id": art_id})
        if code != 200:
            raise RuntimeError(f"pick {slot} HTTP {code}: {data}")
        return bool(data.get("setup_complete"))

    raise RuntimeError(f"unhandled setup action: {na}")


def run_setup(client: E2EClient) -> dict[str, Any]:
    for i in range(40):
        code, setup = client.get("/api/setup")
        if code != 200:
            raise RuntimeError(f"setup GET HTTP {code}: {setup}")
        if _setup_step(client, setup):
            code, setup = client.get("/api/setup")
            if code != 200:
                raise RuntimeError(f"setup verify HTTP {code}")
            if setup.get("setup_complete"):
                print("setup complete", file=sys.stderr)
                return setup
        time.sleep(0.2)
    raise RuntimeError("setup did not complete within 40 steps")


def poll_beat_job(client: E2EClient, job_id: str) -> dict[str, Any]:
    deadline = time.time() + BEAT_TIMEOUT_S
    while time.time() < deadline:
        code, job = client.get(f"/api/beat/jobs/{job_id}")
        if code != 200:
            raise RuntimeError(f"job poll HTTP {code}: {job}")
        status = job.get("status")
        phase = job.get("phase")
        if phase:
            print(f"    phase={phase}", file=sys.stderr)
        if status == "done":
            result = job.get("result") or {}
            if int(result.get("exit_code", 1)) != 0:
                raise RuntimeError(result.get("error") or "beat failed")
            return result
        if status == "error":
            raise RuntimeError(job.get("error") or "beat job error")
        time.sleep(POLL_INTERVAL_S)
    raise RuntimeError(f"beat job {job_id} timed out after {BEAT_TIMEOUT_S}s")


def run_beats(client: E2EClient, n: int, choice: int) -> list[dict[str, Any]]:
    results: list[dict[str, Any]] = []
    for i in range(1, n + 1):
        print(f"BEAT {i}/{n} choice={choice}", file=sys.stderr)
        t0 = time.perf_counter()
        code, body = client.post("/api/beat", {"choice": choice})
        if code != 202:
            raise RuntimeError(f"beat POST HTTP {code}: {body}")
        job_id = body.get("job_id")
        if not job_id:
            raise RuntimeError(f"no job_id: {body}")
        result = poll_beat_job(client, job_id)
        prose = str(result.get("prose") or "").strip()
        if not prose:
            raise RuntimeError("empty prose in beat result")
        elapsed = time.perf_counter() - t0
        print(
            f"  ok prose_len={len(prose)} elapsed={elapsed:.1f}s session={result.get('session')}",
            file=sys.stderr,
        )
        results.append(result)
    return results


def main() -> int:
    parser = argparse.ArgumentParser(description="Novel mobile live E2E")
    parser.add_argument("--base-url", default="http://127.0.0.1:8765")
    parser.add_argument("--beats", type=int, default=5)
    parser.add_argument("--choice", type=int, default=1)
    parser.add_argument("--user-id", default="")
    parser.add_argument("--token", default="")
    parser.add_argument(
        "--expand-catalog",
        choices=("true", "false", "default"),
        default="false",
        help="World bootstrap catalog expand (default: false for speed)",
    )
    args = parser.parse_args()

    if not _port_open("127.0.0.1", 8765):
        return _fail("novel-mobile not reachable on :8765")
    if not _port_open("127.0.0.1", 18765):
        return _fail("memnet serve not reachable on :18765")

    user_id = args.user_id.strip() or f"e2e-{uuid.uuid4()}"
    token = args.token.strip() or None
    client = E2EClient(args.base_url, user_id, token=token)

    code, auth_cfg = client.get("/api/auth/config")
    if code != 200:
        return _fail(f"auth/config HTTP {code}: {auth_cfg}")
    mode = auth_cfg.get("auth_mode", "open")
    if mode == "google" and not token:
        return _fail("google auth enabled; pass --token with app JWT")
    if mode == "token" and not token:
        import os

        token = os.environ.get("NOVEL_MOBILE_TOKEN", "").strip() or None
        if not token:
            return _fail("token auth enabled; set NOVEL_MOBILE_TOKEN or --token")
        client.token = token

    expand: bool | None
    if args.expand_catalog == "default":
        expand = None
    else:
        expand = args.expand_catalog == "true"

    print(f"create world user={user_id} expand_catalog={expand}", file=sys.stderr)
    create_body: dict[str, Any] = {"title": "E2E test"}
    if expand is not None:
        create_body["expand_catalog"] = expand
    code, created = client.post("/api/worlds", create_body)
    if code != 200:
        return _fail(f"world create HTTP {code}: {created}")
    client.world_id = created.get("world_id")
    if not client.world_id:
        return _fail(f"no world_id in response: {created}")
    print(
        f"world_id={client.world_id} session={created.get('session_id')}",
        file=sys.stderr,
    )

    try:
        run_setup(client)
        results = run_beats(client, args.beats, args.choice)
    except RuntimeError as err:
        return _fail(str(err))

    summary = {
        "user_id": user_id,
        "world_id": client.world_id,
        "beats": args.beats,
        "results": [
            {
                "prose_len": len(r.get("prose") or ""),
                "session": r.get("session"),
                "beat_stage": r.get("beat_stage"),
            }
            for r in results
        ],
    }
    print(json.dumps(summary, ensure_ascii=False, indent=2))
    print("PASS", file=sys.stderr)
    return 0


if __name__ == "__main__":
    sys.exit(main())
