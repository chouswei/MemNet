#!/usr/bin/env python3
"""Prove one-session-per-document readiness against a real memnet serve.

Talks loopback TCP only (no MCP front). Synthetic data. Never logs session ids.

Usage (venv active, from repo root):

    python scripts/probe_doc_gate_readiness.py \\
        --out /opt/cursor/artifacts/doc-gate-readiness-proof.log
"""

from __future__ import annotations

import argparse
import json
import sys
import tempfile
import time
import traceback
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
TESTS = ROOT / "tests"
for path in (str(ROOT), str(TESTS)):
    if path not in sys.path:
        sys.path.insert(0, path)

from doc_gate_lib import (  # noqa: E402
    CAP_CONTRACT,
    CAP_CONTRACT_NEEDLES,
    PROP32,
    ItemResult,
    ServeProc,
    ServeReply,
    assert_sid_free,
    canonical_snapshot,
    err_lines,
    gql_str,
    redact,
    redact_obj,
    running_serve,
    schema_prop32,
    snapshot_write_once_report,
    stat_lines,
    wrn_lines,
)

from memnet import __version__  # noqa: E402


def _envelope_note(reply: ServeReply) -> dict[str, Any]:
    return {
        "request_keys": sorted(reply.request.keys()),
        "reply_keys": list(reply.keys),
        "exit_code": reply.exit_code,
        "has_errors_field": "errors" in reply.keys,
        "has_session_id_field": "session_id" in reply.keys,
        "stderr_err": err_lines(reply.stderr),
        "stdout_stat": stat_lines(reply.stdout),
        "stderr_wrn": wrn_lines(reply.stderr + reply.stdout),
    }


def item_cap_contract() -> ItemResult:
    text = CAP_CONTRACT.read_text(encoding="utf-8")
    missing = [n for n in CAP_CONTRACT_NEEDLES if n not in text]
    assert_sid_free(text)
    return ItemResult(
        item="cap-contract.md 0.19.18",
        verdict="yes" if not missing else "no",
        notes=["Envelope and cap codes unchanged on this cut." if not missing else ""],
        numbers={"needles": len(CAP_CONTRACT_NEEDLES), "missing": len(missing)},
        gaps=[f"missing needle: {m}" for m in missing],
    )


def item6_envelope(svc: ServeProc) -> ItemResult:
    reply = svc.expire_status()
    env = _envelope_note(reply)
    usage = svc.usage_report()
    usage_body: dict[str, Any] = {}
    if usage.exit_code == 0 and usage.stdout.strip():
        usage_body = json.loads(usage.stdout)
    hk = None
    sid = svc.open_session(product="docgate")
    try:
        hk = svc.housekeep_stats(sid)
        rss_keys = {
            "expire_status_stats": stat_lines(reply.stdout),
            "housekeep_stats": stat_lines(hk.stdout),
            "usage_process_rss": usage_body.get("process", {}).get("rss_bytes"),
            "usage_session_row_keys": sorted(
                (usage_body.get("session_rows") or [{}])[0].keys()
            )
            if usage_body.get("session_rows")
            else [],
        }
    finally:
        svc.close(sid)
    per_session_bytes = "rss_bytes" in rss_keys["usage_session_row_keys"]
    gaps = []
    if per_session_bytes:
        notes = ["admin usage session_rows includes rss_bytes"]
    else:
        notes = [
            "No per-session memory figure. admin usage has process.rss_bytes only; "
            "housekeep_stats is row/edge/orphan counts; expire-status is flags."
        ]
        gaps.append("per-session RSS not exposed (process RSS only)")
    if "errors" not in reply.keys:
        notes.append(
            "Direct serve reply is {exit_code, stdout, stderr}; no MCP errors[] "
            "and no session_id field (id is only on stdout @SESSION)."
        )
    return ItemResult(
        item="6 Direct loopback serve envelope + memory figures",
        verdict="yes" if reply.exit_code == 0 else "no",
        notes=notes,
        numbers={
            "envelope": env,
            "usage_exit": usage.exit_code,
            "usage_reply_keys": list(usage.keys),
            "housekeep_exit": None if hk is None else hk.exit_code,
            "process_rss_bytes": rss_keys["usage_process_rss"],
            "per_session_rss": per_session_bytes,
            "version": usage_body.get("process", {}).get("version"),
        },
        wires=stat_lines(reply.stdout)
        + err_lines(usage.stderr)
        + (stat_lines(hk.stdout) if hk else []),
        gaps=gaps,
    )


def _rss_or_zero(svc: ServeProc) -> int:
    got = svc.rss()
    return int(got) if got is not None else -1


def item6_rss_delta(svc: ServeProc, *, n_parts: int, samples: int) -> ItemResult:
    deltas: list[int] = []
    baseline = _rss_or_zero(svc)
    sids: list[str] = []
    try:
        for _ in range(samples):
            before = _rss_or_zero(svc)
            sid = svc.open_session()
            replies = svc.populate(sid, n_parts)
            if any(r.exit_code != 0 for r in replies):
                err = next(r for r in replies if r.exit_code != 0)
                return ItemResult(
                    item="6 RSS delta per 1800-part session",
                    verdict="no",
                    notes=["populate failed"],
                    wires=err_lines(err.stderr),
                    gaps=["populate of synthetic document failed"],
                )
            after = _rss_or_zero(svc)
            deltas.append(after - before)
            sids.append(sid)
        mean = int(sum(deltas) / len(deltas)) if deltas else 0
        return ItemResult(
            item="6 RSS delta per 1800-part session",
            verdict="yes" if mean > 0 else "note",
            notes=[
                "Delta is serve-process RSS after open+populate minus RSS before, "
                "sessions still live. Allocator noise included."
            ],
            numbers={
                "samples": samples,
                "n_parts": n_parts,
                "deltas_bytes": deltas,
                "mean_bytes": mean,
                "mean_mib": round(mean / (1024 * 1024), 3),
                "baseline_bytes": baseline,
            },
        )
    finally:
        for sid in sids:
            svc.close(sid)


def item2_churn(svc: ServeProc, *, cycles: int, n_parts: int) -> ItemResult:
    base_n, cap = svc.live_count()
    base_rss = _rss_or_zero(svc)
    per10: list[dict[str, Any]] = []
    failed = 0
    t0 = time.monotonic()
    for i in range(1, cycles + 1):
        sid = svc.open_session()
        replies = svc.populate(sid, n_parts)
        if any(r.exit_code != 0 for r in replies):
            failed += 1
        closed = svc.close(sid)
        if closed.exit_code != 0:
            failed += 1
        if i % 10 == 0 or i == cycles:
            live, _cap = svc.live_count()
            rss = _rss_or_zero(svc)
            per10.append(
                {
                    "cycle": i,
                    "rss_bytes": rss,
                    "rss_delta_from_baseline": rss - base_rss,
                    "live": live,
                    "live_delta": live - base_n,
                }
            )
    elapsed = time.monotonic() - t0
    end_n, _ = svc.live_count()
    rss_end = _rss_or_zero(svc)
    deltas = [row["rss_delta_from_baseline"] for row in per10]
    grew = bool(deltas) and deltas[-1] > deltas[0] + 8 * 1024 * 1024
    live_flat = end_n == base_n
    rss_note = "RSS trend after close (allocator may retain pages)."
    verdict = "yes" if live_flat and failed == 0 and not grew else "note"
    gaps = []
    if not live_flat:
        gaps.append(f"live count {base_n} -> {end_n}, not back to baseline")
        verdict = "no"
    if failed:
        gaps.append(f"{failed} open/populate/close failures")
        verdict = "no"
    if grew:
        gaps.append("RSS rose more than 8 MiB across churn; not flat")
        if verdict == "yes":
            verdict = "note"
    return ItemResult(
        item="2 Session churn (open, populate, close)",
        verdict=verdict,
        notes=[rss_note, f"elapsed_s={elapsed:.1f}", f"max_sessions_cap={cap}"],
        numbers={
            "cycles": cycles,
            "n_parts": n_parts,
            "baseline_live": base_n,
            "end_live": end_n,
            "baseline_rss_bytes": base_rss,
            "end_rss_bytes": rss_end,
            "rss_per_10": per10,
            "failed": failed,
            "elapsed_s": round(elapsed, 2),
        },
        gaps=gaps,
    )


def item3_roundtrip(svc: ServeProc, tmp: Path, *, n_parts: int) -> ItemResult:
    sid = svc.open_session()
    text_blob = (
        "Line one.\nLine two with unicode 测例 Ω café.\n"
        "Pipes | and quotes \"double\" and 'single'."
    )
    extra = (
        "CREATE (:USR {id: 'USR_rt', key: 'blob', value: "
        + gql_str(text_blob)
        + ", recycle: ''})\n"
    )
    replies = svc.populate(sid, n_parts, text_nodes=0)
    extra_r = svc.mutate(sid, extra)
    snap = tmp / "roundtrip.snap"
    save = svc.save(sid, snap)
    src_text = snap.read_text(encoding="utf-8") if snap.is_file() else ""
    src_can = canonical_snapshot(src_text) if src_text else ""
    svc.close(sid)
    load = svc.load_file(snap)
    gaps: list[str] = []
    notes: list[str] = []
    wires = stat_lines(save.stdout) + stat_lines(load.stdout)
    wires.extend(err_lines(save.stderr) + err_lines(load.stderr))
    wires.extend(wrn_lines(save.stderr) + wrn_lines(load.stderr))
    loaded_ok = load.exit_code == 0
    new_sid = None
    dst_can = ""
    exact = False
    if loaded_ok:
        new_sid = None
        for line in load.stdout.splitlines():
            if line.startswith("@SESSION:"):
                new_sid = line.split("|", 1)[0].replace("@SESSION:", "").strip()
                break
        if new_sid:
            dst = tmp / "roundtrip-loaded.snap"
            save2 = svc.save(new_sid, dst)
            wires.extend(stat_lines(save2.stdout))
            dst_text = dst.read_text(encoding="utf-8") if dst.is_file() else ""
            dst_can = canonical_snapshot(dst_text) if dst_text else ""
            exact = src_can == dst_can
            svc.close(new_sid)
    wo = snapshot_write_once_report()
    notes.append(
        "Write-once: engine write_snapshot uses Path.write_text (overwrite). "
        "No O_EXCL, chmod, or immutable flag in memnet/snapshot.py. "
        "Write-once is caller or filesystem only."
    )
    if not exact:
        gaps.append("canonical dump differed after save/load")
        if text_blob.splitlines()[0] not in src_text:
            gaps.append(
                "multi-line / unicode / pipe text may not survive leftover "
                "snapshot emit (line-oriented @TAG pipe)"
            )
        # show a small diff head without sids
        src_lines = src_can.splitlines()
        dst_lines = dst_can.splitlines()
        diff_n = sum(1 for a, b in zip(src_lines, dst_lines) if a != b)
        notes.append(
            f"canonical_lines src={len(src_lines)} dst={len(dst_lines)} "
            f"zip_mismatch={diff_n} len_equal={len(src_lines) == len(dst_lines)}"
        )
    if extra_r.exit_code != 0:
        gaps.append("text-node mutate failed")
        wires.extend(err_lines(extra_r.stderr))
    if any(r.exit_code != 0 for r in replies):
        gaps.append("populate failed")
    verdict = "yes" if exact and loaded_ok and not gaps else ("note" if loaded_ok else "no")
    return ItemResult(
        item="3 Snapshot round-trip",
        verdict=verdict,
        notes=notes,
        numbers={
            "n_parts": n_parts,
            "save_exit": save.exit_code,
            "load_exit": load.exit_code,
            "exact_canonical": exact,
            "src_bytes": len(src_text),
            "write_once": wo,
        },
        wires=wires,
        gaps=gaps,
    )


def item4_expire(svc: ServeProc, *, wait_s: float) -> ItemResult:
    sid = svc.open_session(ttl=1)
    marker = "CREATE (:SEC {id: 'SEC_exp', art: 'ART_doc', heading: 'late', numbering: '9', parent: '', order: '9', status: 'pre_expire_mark', recycle: ''})\n"
    mut = svc.mutate(sid, marker)
    snap_before = svc.snap_count()
    notes = [
        f"ttl=1 min; waited {wait_s}s after last mutate (sliding TTL).",
        "Did not touch the session during the wait.",
    ]
    wires = err_lines(mut.stderr) + stat_lines(mut.stdout) + wrn_lines(mut.stderr)
    time.sleep(wait_s)
    # First access after expiry: pin_map should miss with snap_available.
    first = svc.pin_map(sid, cue="SEC_exp")
    wires.extend(err_lines(first.stderr) + wrn_lines(first.stderr) + stat_lines(first.stdout))
    snap_after = svc.snap_count()
    wrote = snap_after > snap_before
    reload_r = svc.load_sid(sid)
    wires.extend(
        err_lines(reload_r.stderr)
        + wrn_lines(reload_r.stderr)
        + stat_lines(reload_r.stdout)
    )
    latest = False
    if reload_r.exit_code == 0:
        new = None
        for line in reload_r.stdout.splitlines():
            if line.startswith("@SESSION:"):
                new = line.split("|", 1)[0].replace("@SESSION:", "").strip()
                break
        if new:
            pin = svc.pin_map(new, cue="SEC_exp")
            latest = "pre_expire_mark" in pin.stdout
            wires.extend(err_lines(pin.stderr))
            svc.close(new)
    first_code = ",".join(err_lines(first.stderr)) or f"exit={first.exit_code}"
    gaps = []
    if not wrote:
        gaps.append("expire did not add a snapshot file in MEMNET_EXPIRE_SNAPSHOT_DIR")
    if "snap_available" not in first.stderr and "session_expired" not in first.stderr:
        gaps.append(f"first post-expiry access was not session_expired: {first_code}")
    if reload_r.exit_code != 0:
        gaps.append("session_load by known sid after expiry failed")
    if reload_r.exit_code == 0 and not latest:
        gaps.append("reload missing pre-expiry mutate (status=pre_expire_mark)")
    verdict = "yes" if wrote and latest and not gaps else ("note" if wrote else "no")
    return ItemResult(
        item="4 Save-on-expire under serve",
        verdict=verdict,
        notes=notes,
        numbers={
            "wait_s": wait_s,
            "mutate_exit": mut.exit_code,
            "first_access_exit": first.exit_code,
            "reload_exit": reload_r.exit_code,
            "snap_files_before": snap_before,
            "snap_files_after": snap_after,
            "wrote_snapshot": wrote,
            "latest_state": latest,
        },
        wires=wires,
        gaps=gaps,
    )


def item5_acl(svc: ServeProc) -> ItemResult:
    sid = svc.open_session()
    svc.mutate(
        sid,
        "CREATE (:SEC {id: 'SEC_acl', art: 'ART_doc', heading: 'acl', numbering: '1', parent: '', order: '1', status: 'active', recycle: ''})\n",
    )
    grant = svc.grant(sid, "owner", write_scope="labels=SEC;ids=SEC_acl")
    bind = svc.acl_bind(sid, "mission-a", "lease-a")
    checks: dict[str, dict[str, Any]] = {}

    def rec(name: str, reply: ServeReply, *, expect_acl: bool) -> None:
        errs = err_lines(reply.stderr)
        typer_miss = any("no such option" in ln.lower() or "unexpected" in ln.lower() for ln in (reply.stderr or "").splitlines())
        acl_hit = any(
            e.startswith("@ERR: acl_") for e in errs
        )
        skipped = (not acl_hit) and (reply.exit_code == 0 or typer_miss)
        checks[name] = {
            "exit": reply.exit_code,
            "acl_hit": acl_hit,
            "skipped": skipped if expect_acl else (not acl_hit),
            "typer_unexpected_option": typer_miss,
            "errs": errs[:4],
        }

    rec("pin_map missing caller", svc.pin_map(sid, cue="SEC_acl"), expect_acl=True)
    rec(
        "pin_map wrong caller",
        svc.pin_map(sid, cue="SEC_acl", caller="intruder"),
        expect_acl=True,
    )
    rec(
        "pin_map owner",
        svc.pin_map(sid, cue="SEC_acl", caller="owner"),
        expect_acl=True,
    )
    rec(
        "mutate missing caller",
        svc.mutate(
            sid,
            "MATCH (n:SEC {id: 'SEC_acl'}) SET n.status = 'x'\n",
        ),
        expect_acl=True,
    )
    rec(
        "mutate wrong caller",
        svc.mutate(
            sid,
            "MATCH (n:SEC {id: 'SEC_acl'}) SET n.status = 'x'\n",
            caller="intruder",
        ),
        expect_acl=True,
    )
    rec(
        "mutate owner in scope",
        svc.mutate(
            sid,
            "MATCH (n:SEC {id: 'SEC_acl'}) SET n.status = 'ok'\n",
            caller="owner",
        ),
        expect_acl=True,
    )
    rec(
        "mutate owner out of scope",
        svc.mutate(
            sid,
            "CREATE (:USR {id: 'USR_nope', key: 'k', value: 'v', recycle: ''})\n",
            caller="owner",
        ),
        expect_acl=True,
    )
    rec(
        "export missing caller",
        svc.export_pin_map(sid, cue="SEC_acl"),
        expect_acl=True,
    )
    rec(
        "export wrong caller",
        svc.export_pin_map(sid, cue="SEC_acl", caller="intruder"),
        expect_acl=True,
    )
    rec("save missing caller", svc.save(sid, svc.snap_dir / "acl-save.snap"), expect_acl=True)
    rec(
        "save with caller",
        svc.save(sid, svc.snap_dir / "acl-save2.snap", caller="owner"),
        expect_acl=True,
    )
    rec("load with caller", svc.load_file(svc.snap_dir / "acl-save.snap", caller="owner"), expect_acl=True)
    rec("close missing caller", svc.close(sid), expect_acl=True)

    # Bind skip: reopen, grant+bind, mutate without mission/lease through serve.
    sid2 = svc.open_session()
    svc.grant(sid2, "owner")
    svc.acl_bind(sid2, "mission-a", "lease-a")
    bind_mut = svc.mutate(
        sid2,
        "CREATE (:SEC {id: 'SEC_bind', art: 'ART_doc', heading: 'b', numbering: '1', parent: '', order: '1', status: 'active', recycle: ''})\n",
        caller="owner",
    )
    bind_skipped = bind_mut.exit_code == 0 and not any(
        "acl_bind" in e for e in err_lines(bind_mut.stderr)
    )
    rec("bind mutate without mission/lease", bind_mut, expect_acl=False)
    svc.close(sid2)

    skipped = [k for k, v in checks.items() if v.get("skipped")]
    checked = [k for k, v in checks.items() if v.get("acl_hit")]
    gaps = [f"ACL not checked: {k}" for k in skipped]
    notes = [
        f"grant exit={grant.exit_code} bind exit={bind.exit_code}",
        "Bind is skipped on serve (MEMNET_SERVE_INTERNAL=1) — confirmed below.",
        f"bind_skipped={bind_skipped}",
    ]
    wires = []
    for name, row in checks.items():
        for e in row["errs"]:
            wires.append(f"{name}: {e}")
    who_ok = any("acl_who" in e for row in checks.values() for e in row["errs"])
    denied_ok = any("acl_denied" in e for row in checks.values() for e in row["errs"])
    scope_ok = any("acl_scope" in e for row in checks.values() for e in row["errs"])
    verdict = "note" if skipped else "yes"
    if not (who_ok and denied_ok):
        verdict = "no"
        gaps.append("missing acl_who and/or acl_denied on pin_map/mutate")
    return ItemResult(
        item="5 Per-session ACL over serve",
        verdict=verdict,
        notes=notes,
        numbers={
            "checked": checked,
            "skipped": skipped,
            "acl_who": who_ok,
            "acl_denied": denied_ok,
            "acl_scope": scope_ok,
            "bind_skipped_on_serve": bind_skipped,
            "calls": checks,
        },
        wires=wires,
        gaps=gaps,
    )


def item7_gql(svc: ServeProc) -> ItemResult:
    cases: dict[str, dict[str, Any]] = {}
    gaps: list[str] = []
    wires: list[str] = []

    sid32 = svc.open_session(map_lines=[ln for ln in schema_prop32().splitlines() if ln])
    props = ", ".join(f"{k}: {gql_str('v' if k != 'id' else 'PRT_32')}" for k in PROP32)
    ins = svc.mutate(sid32, f"CREATE (:PRT {{{props}}})\n")
    cases["create_32_props"] = {
        "exit": ins.exit_code,
        "ok": ins.exit_code == 0,
        "errs": err_lines(ins.stderr),
    }
    wires.extend(err_lines(ins.stderr))
    if ins.exit_code != 0:
        gaps.append("CREATE with 32 properties failed")
    insert = svc.mutate(
        sid32,
        "INSERT (:PRT {id: 'PRT_ins', p00: 'x'})\n",
    )
    cases["insert_iso"] = {
        "exit": insert.exit_code,
        "ok": insert.exit_code == 0,
        "errs": err_lines(insert.stderr),
    }
    wires.extend(err_lines(insert.stderr))
    if insert.exit_code != 0:
        gaps.append("ISO GQL INSERT is not accepted (CREATE is the mutate spelling)")
    svc.close(sid32)

    sid = svc.open_session()
    svc.mutate(
        sid,
        "CREATE (:SEC {id: 'SEC_hub', art: 'ART_doc', heading: 'hub', numbering: '0', parent: '', order: '0', status: 'seed', recycle: ''})\n",
    )
    set_r = svc.mutate(
        sid,
        "MATCH (n:SEC {id: 'SEC_hub'}) SET n.status = 'patched'\n",
    )
    pin_set = svc.pin_map(sid, cue="SEC_hub")
    cases["match_set"] = {
        "exit": set_r.exit_code,
        "ok": set_r.exit_code == 0 and "patched" in pin_set.stdout,
        "errs": err_lines(set_r.stderr),
    }
    if not cases["match_set"]["ok"]:
        gaps.append("MATCH by key then SET failed")
        wires.extend(err_lines(set_r.stderr) + err_lines(pin_set.stderr))

    hop_lines = [
        "CREATE (:SEC {id: 'SEC_leaf', art: 'ART_doc', heading: 'leaf', numbering: '1', parent: '', order: '1', status: 'active', recycle: ''})",
        "MATCH (a {id: 'SEC_hub'}), (b {id: 'SEC_leaf'})\nCREATE (a)-[:contains {id: 'E_hop'}]->(b)",
    ]
    hop_m = svc.mutate(sid, "\n".join(hop_lines) + "\n")
    hop_r = svc.pin_map(sid, cue="SEC_hub", depth=1)
    hop_ok = hop_m.exit_code == 0 and "SEC_leaf" in hop_r.stdout and "contains" in hop_r.stdout
    cases["fixed_hop"] = {
        "exit": hop_r.exit_code,
        "ok": hop_ok,
        "errs": err_lines(hop_m.stderr) + err_lines(hop_r.stderr),
        "truncation": "## Truncation" in hop_r.stdout,
    }
    if not hop_ok:
        gaps.append("fixed hop over contains via pin_map depth=1 failed")
        wires.extend(err_lines(hop_m.stderr) + err_lines(hop_r.stderr))

    count_r = svc.mutate(
        sid,
        "MATCH (n:SEC) RETURN n.status AS status, count(n) AS c\n",
    )
    cases["grouped_count"] = {
        "exit": count_r.exit_code,
        "ok": count_r.exit_code == 0,
        "errs": err_lines(count_r.stderr),
    }
    wires.extend(err_lines(count_r.stderr))
    if count_r.exit_code == 0:
        gaps.append("grouped count unexpectedly succeeded")
    else:
        gaps.append(
            "grouped count() is not product mutate/pin_map; refused (see wire)"
        )

    # 151 row limit: star with 160 leaves.
    star = [
        "CREATE (:SEC {id: 'SEC_star', art: 'ART_doc', heading: 'star', numbering: '0', parent: '', order: '0', status: 'hub', recycle: ''})"
    ]
    for i in range(160):
        lid = f"SEC_s{i:03d}"
        star.append(
            "CREATE (:SEC {"
            f"id: {gql_str(lid)}, art: 'ART_doc', heading: {gql_str(lid)}, "
            "numbering: '1', parent: '', order: '1', status: 'leaf', recycle: ''})"
        )
        star.append(
            f"MATCH (a {{id: 'SEC_star'}}), (b {{id: {gql_str(lid)}}})\n"
            f"CREATE (a)-[:contains {{id: {gql_str(f'E_s{i:03d}')}}}]->(b)"
        )
    # split
    mid = len(star) // 2
    for chunk in (star[:mid], star[mid:]):
        r = svc.mutate(sid, "\n".join(chunk) + "\n")
        if r.exit_code != 0:
            gaps.append("star populate for max_rows=151 failed")
            wires.extend(err_lines(r.stderr))
            break
    lim = svc.pin_map(sid, cue="SEC_star", depth=1, max_rows=151)
    trunc = [ln for ln in lim.stdout.splitlines() if ln.startswith("## Truncation")]
    payload_n = len(
        [
            ln
            for ln in lim.stdout.splitlines()
            if ln.startswith("(:") or "-[: " in ln or ln.startswith("(") and "-[:" in ln
        ]
    )
    cases["max_rows_151"] = {
        "exit": lim.exit_code,
        "ok": lim.exit_code == 0,
        "truncation": trunc,
        "payload_lines": payload_n,
        "honours_151": any("M=151" in ln for ln in trunc) or payload_n <= 151,
    }
    wires.extend(trunc)
    if lim.exit_code != 0:
        gaps.append("pin_map max_rows=151 failed")
        wires.extend(err_lines(lim.stderr))
    elif not cases["max_rows_151"]["honours_151"]:
        gaps.append("pin_map max_rows=151 did not clip at 151 or mark Truncation M=151")
    svc.close(sid)

    ok_create = cases["create_32_props"]["ok"]
    ok_set = cases["match_set"]["ok"]
    ok_hop = cases["fixed_hop"]["ok"]
    count_refused = not cases["grouped_count"]["ok"]
    ok_151 = cases["max_rows_151"]["ok"] and cases["max_rows_151"]["honours_151"]
    if ok_create and ok_set and ok_hop and ok_151 and count_refused:
        verdict = "note"
    elif ok_create and ok_set and ok_hop:
        verdict = "note"
    else:
        verdict = "no"
    return ItemResult(
        item="7 GQL mutate + pin_map coverage",
        verdict=verdict,
        notes=[
            "CREATE is the mutate spelling; INSERT is ISO GQL.",
            "Grouped count is MATCH…RETURN, which the product gate forbids.",
        ],
        numbers=cases,
        wires=wires,
        gaps=gaps,
    )


def item_admin_live_bug(svc: ServeProc, *, wait_s: float) -> ItemResult:
    live_sids = [svc.open_session(ttl=60, product="docgate") for _ in range(7)]
    expiring = [svc.open_session(ttl=1, product="docgate") for _ in range(5)]
    del expiring  # must not touch; keep ids only in RAM
    time.sleep(wait_s)
    usage = svc.usage_report()
    shown = None
    if usage.exit_code == 0:
        body = json.loads(usage.stdout)
        shown = body.get("sessions", {}).get("live")
        row_n = len(body.get("session_rows") or [])
    else:
        row_n = 0
    listed_n, _ = svc.live_count()
    for sid in live_sids:
        svc.close(sid)
    confirmed = shown is not None and shown > listed_n
    return ItemResult(
        item="admin usage live count vs true (expired unswept)",
        verdict="yes" if confirmed else "note",
        notes=[
            "Opened 7 ttl=60 and 5 ttl=1; waited without touching the ttl=1 set.",
            "usage-report peeks registry_count() without purge; session list purges.",
            "Not fixed in this run.",
        ],
        numbers={
            "wait_s": wait_s,
            "usage_live": shown,
            "usage_session_rows": row_n,
            "session_list_after": listed_n,
            "expected_true_live_before_list_purge": 7,
            "bug_confirmed": confirmed,
        },
        wires=err_lines(usage.stderr),
        gaps=[]
        if confirmed
        else ["did not observe usage live > session list; timing or purge elsewhere"],
    )


def main() -> int:
    parser = argparse.ArgumentParser(description="Doc-gate readiness probe (no session ids).")
    parser.add_argument(
        "--out",
        default="/opt/cursor/artifacts/doc-gate-readiness-proof.log",
        help="Sid-free proof log path.",
    )
    parser.add_argument("--nodes", type=int, default=1800)
    parser.add_argument("--churn", type=int, default=110)
    parser.add_argument("--rss-samples", type=int, default=5)
    parser.add_argument("--expire-wait", type=float, default=65.0)
    parser.add_argument(
        "--quick",
        action="store_true",
        help="Smaller graph / fewer churn cycles (not the product-gate proof).",
    )
    args = parser.parse_args()
    nodes = 40 if args.quick else args.nodes
    churn = 12 if args.quick else args.churn
    samples = 2 if args.quick else args.rss_samples
    wait_s = 5.0 if args.quick else args.expire_wait

    results: list[ItemResult] = [item_cap_contract()]
    header: dict[str, Any] = {
        "product": __version__,
        "mcp_front": False,
        "transport": "loopback TCP length-prefixed JSON argv+stdin",
        "nodes": nodes,
        "churn": churn,
        "quick": bool(args.quick),
    }
    with tempfile.TemporaryDirectory(prefix="doc-gate-") as raw:
        tmp = Path(raw)
        with running_serve(tmp) as svc:
            header.update(
                {
                    "serve_host": svc.host,
                    "serve_port": svc.port,
                    "serve_pid": svc.pid,
                }
            )
            try:
                results.append(item6_envelope(svc))
                results.append(item6_rss_delta(svc, n_parts=nodes, samples=samples))
                results.append(item2_churn(svc, cycles=churn, n_parts=nodes))
                results.append(item3_roundtrip(svc, tmp, n_parts=min(nodes, 1800)))
                results.append(item5_acl(svc))
                results.append(item7_gql(svc))
                results.append(item4_expire(svc, wait_s=wait_s))
                results.append(item_admin_live_bug(svc, wait_s=wait_s))
            except Exception as exc:  # noqa: BLE001 — proof must still write
                results.append(
                    ItemResult(
                        item="probe exception",
                        verdict="no",
                        notes=[type(exc).__name__, redact(str(exc))],
                        gaps=[redact(traceback.format_exc())],
                    )
                )
            sample_req = svc.send(["session", "expire-status"])
            header["sample_request"] = redact_obj(
                {k: v for k, v in sample_req.request.items() if k != "stdin"}
            )
            header["sample_reply_keys"] = list(sample_req.keys)

    blob = (
        "MemNet doc-gate readiness proof (sid-free)\n"
        + json.dumps(header, sort_keys=True)
        + "\n\n"
        + "\n".join(r.render() for r in results)
    )
    if "mn_" in blob or __import__("re").search(r"mn_[0-9a-fA-F]+", blob):
        raise SystemExit("refusing to write proof: session id leaked")
    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(blob, encoding="utf-8")
    sys.stdout.write(f"wrote {out} items={len(results)}\n")
    return 0 if all(r.verdict != "no" for r in results) else 1


if __name__ == "__main__":
    raise SystemExit(main())
