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
    DEFAULT_BATCH_LINES,
    E16_P95_BAR_MS,
    FAT_PROBE_NODES,
    FAT_TEXT_NODES,
    FULLDOC_FAT,
    FULLDOC_NODES,
    HUB_SEC,
    LOAD_PROBE_NODES,
    PROP32,
    ItemResult,
    ServeProc,
    ServeReply,
    assert_sid_free,
    canonical_snapshot,
    citekeys_schema,
    cpu_model,
    edge_create,
    edge_delete,
    err_lines,
    fat_payload_bytes,
    fulldoc_edge_stmts,
    gql_str,
    latency_summary,
    make_fat_blob,
    make_special_blob,
    max_rows_count_report,
    mutate_byte_cap_report,
    pack_batches,
    parse_stat_int,
    populate_fat_batches,
    populate_fulldoc_batches,
    populate_node_batches,
    redact,
    redact_obj,
    running_serve,
    schema_prop32,
    sec_create,
    shaped_node_props,
    snapshot_load_cap_report,
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
            "usage_session_row_keys": sorted((usage_body.get("session_rows") or [{}])[0].keys())
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


def _sid_from(stdout: str) -> str | None:
    for line in stdout.splitlines():
        if line.startswith("@SESSION:"):
            return line.split("|", 1)[0].replace("@SESSION:", "").strip()
    return None


def item3_roundtrip(svc: ServeProc, tmp: Path, *, n_parts: int) -> ItemResult:
    gaps: list[str] = []
    notes: list[str] = []
    wires: list[str] = []
    wo = snapshot_write_once_report()
    notes.append(
        "Write-once: engine write_snapshot uses Path.write_text (overwrite). "
        "No O_EXCL, chmod, or immutable flag in memnet/snapshot.py. "
        "Write-once is caller or filesystem only."
    )

    sid = svc.open_session()
    replies = svc.populate(sid, n_parts, text_nodes=8)
    if any(r.exit_code != 0 for r in replies):
        gaps.append("populate failed")
        wires.extend(err_lines(replies[-1].stderr))
    snap = tmp / "roundtrip.snap"
    save = svc.save(sid, snap)
    wires.extend(stat_lines(save.stdout) + err_lines(save.stderr) + wrn_lines(save.stderr))
    src_text = snap.read_text(encoding="utf-8") if snap.is_file() else ""
    src_can = canonical_snapshot(src_text) if src_text else ""
    svc.close(sid)
    load = svc.load_file(snap)
    wires.extend(stat_lines(load.stdout) + err_lines(load.stderr))
    exact = False
    if load.exit_code == 0:
        new_sid = _sid_from(load.stdout)
        if new_sid:
            dst = tmp / "roundtrip-loaded.snap"
            save2 = svc.save(new_sid, dst)
            wires.extend(stat_lines(save2.stdout))
            dst_text = dst.read_text(encoding="utf-8") if dst.is_file() else ""
            dst_can = canonical_snapshot(dst_text) if dst_text else ""
            exact = src_can == dst_can
            svc.close(new_sid)
    else:
        gaps.append("single-line unicode/pipe/quote snapshot failed to load")

    sid_nl = svc.open_session()
    nl = "Line one.\nLine two with unicode 测例 Ω.\nPipes | and quotes."
    extra = svc.mutate(
        sid_nl,
        "CREATE (:USR {id: 'USR_nl', key: 'blob', value: " + gql_str(nl) + ", recycle: ''})\n",
    )
    snap_nl = tmp / "multiline.snap"
    save_nl = svc.save(sid_nl, snap_nl)
    svc.close(sid_nl)
    load_nl = svc.load_file(snap_nl)
    wires.extend(err_lines(extra.stderr) + err_lines(save_nl.stderr) + err_lines(load_nl.stderr))
    multiline_field_count = any("FIELD_COUNT" in e for e in err_lines(load_nl.stderr))
    if load_nl.exit_code == 0:
        gaps.append("multi-line text unexpectedly loaded")
    elif not multiline_field_count:
        gaps.append("multi-line load failed but not FIELD_COUNT")
    else:
        notes.append(
            "Raw newlines in a property survive mutate in RAM; leftover snapshot "
            "emit does not escape them, so load raises FIELD_COUNT."
        )

    if not exact:
        gaps.append("canonical dump differed after save/load (single-line text)")
    verdict = "note" if exact and multiline_field_count else ("yes" if exact else "no")
    if exact and multiline_field_count:
        verdict = "note"
    return ItemResult(
        item="3 Snapshot round-trip",
        verdict=verdict,
        notes=notes,
        numbers={
            "n_parts": n_parts,
            "save_exit": save.exit_code,
            "load_exit": load.exit_code,
            "exact_canonical_single_line": exact,
            "multiline_load_exit": load_nl.exit_code,
            "multiline_field_count": multiline_field_count,
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
        err_lines(reload_r.stderr) + wrn_lines(reload_r.stderr) + stat_lines(reload_r.stdout)
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

    lifecycle = {
        "save missing caller",
        "save with caller",
        "load with caller",
        "close missing caller",
        "bind mutate without mission/lease",
    }

    def rec(name: str, reply: ServeReply, *, expect_acl: bool) -> None:
        del expect_acl
        errs = err_lines(reply.stderr)
        typer_miss = any(
            "no such option" in ln.lower() or "unexpected" in ln.lower()
            for ln in (reply.stderr or "").splitlines()
        )
        acl_hit = any(e.startswith("@ERR: acl_") for e in errs)
        skipped = name in lifecycle and not acl_hit
        checks[name] = {
            "exit": reply.exit_code,
            "acl_hit": acl_hit,
            "skipped": skipped,
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
    rec(
        "load with caller",
        svc.load_file(svc.snap_dir / "acl-save.snap", caller="owner"),
        expect_acl=True,
    )
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
    hop_ok = (
        hop_m.exit_code == 0
        and hop_r.exit_code == 0
        and "leaf" in hop_r.stdout.lower()
        and "contains" in hop_r.stdout
    )
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
        gaps.append("grouped count() is not product mutate/pin_map; refused (see wire)")

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


def item_e11_load_budget(svc: ServeProc, tmp: Path, *, n_nodes: int) -> ItemResult:
    path_info = snapshot_load_cap_report()
    batches = populate_node_batches(n_nodes, batch_lines=DEFAULT_BATCH_LINES)
    over_batch = any(chunk.count("\n") > DEFAULT_BATCH_LINES for chunk in batches)
    sid = svc.open_session()
    replies = svc.populate_stmts(sid, batches)
    wires: list[str] = []
    gaps: list[str] = []
    if any(r.exit_code != 0 for r in replies):
        err = next(r for r in replies if r.exit_code != 0)
        wires.extend(err_lines(err.stderr))
        gaps.append("mutate populate of 3000-node graph failed")
    hk = svc.housekeep_stats(sid)
    rows_live = parse_stat_int(hk.stdout, "rows")
    edges_live = parse_stat_int(hk.stdout, "edges")
    snap = tmp / "e11-3000.snap"
    save = svc.save(sid, snap)
    wires.extend(stat_lines(save.stdout) + err_lines(save.stderr))
    svc.close(sid)
    load = svc.load_file(snap)
    wires.extend(stat_lines(load.stdout) + err_lines(load.stderr))
    loaded_rows = None
    ingest_hit = any("ingest_budget" in e for e in err_lines(load.stderr))
    rows_hit = any("limit_exceeded" in e and "rows" in e for e in err_lines(load.stderr))
    if load.exit_code == 0:
        new_sid = _sid_from(load.stdout)
        loaded_rows = parse_stat_int(load.stdout, "loaded")
        if new_sid:
            hk2 = svc.housekeep_stats(new_sid)
            loaded_rows = parse_stat_int(hk2.stdout, "rows") or loaded_rows
            wires.extend(stat_lines(hk2.stdout))
            svc.close(new_sid)
    else:
        gaps.append(
            "session_load refused: "
            + ("; ".join(err_lines(load.stderr)) or f"exit={load.exit_code}")
        )
    notes = [
        path_info["code_path"],
        "ingest_budget is Path-B ingest only; session_load does not call it.",
        "Other caps on this path: max_sessions at load start; MEMNET_MAX_ROWS at upsert; "
        "leftover parse_line value/line/newline/FIELD_COUNT.",
    ]
    if load.exit_code == 0:
        notes.append(
            "Load of 3000 nodes succeeded. Neither a batched load nor an ingest_budget "
            "exemption is required. If a larger snapshot hit MEMNET_MAX_ROWS, batched "
            "load would not help (upsert counts the whole store); split sessions or "
            "raise the row cap."
        )
        verdict = "yes"
    elif ingest_hit:
        notes.append(
            "Load refused ingest_budget. An exemption for session_load (not batched load) "
            "would be the right fix; ingest caps are Path-B artefact budgets, not snapshot restore."
        )
        verdict = "no"
        gaps.append("session_load applied ingest_budget (unexpected on this code path)")
    elif rows_hit:
        notes.append(
            "Load refused MEMNET_MAX_ROWS. Batched load would not help; ingest exemption "
            "would not either. Split sessions or raise max_rows."
        )
        verdict = "note"
    else:
        verdict = "no"
    if over_batch:
        gaps.append("populate batch exceeded 1000 lines")
        verdict = "no"
    return ItemResult(
        item="E11 session_load vs ingest budget (3000-node snapshot)",
        verdict=verdict,
        notes=notes,
        numbers={
            "n_nodes": n_nodes,
            "batch_count": len(batches),
            "max_batch_lines": max((c.count("\n") for c in batches), default=0),
            "mutate_ok": all(r.exit_code == 0 for r in replies),
            "rows_live": rows_live,
            "edges_live": edges_live,
            "save_exit": save.exit_code,
            "load_exit": load.exit_code,
            "loaded_rows": loaded_rows,
            "ingest_budget_on_load": ingest_hit,
            "rows_cap_on_load": rows_hit,
            "load_err": err_lines(load.stderr),
            "code": path_info,
        },
        wires=wires,
        gaps=gaps,
    )


def item_e12_max_rows(tmp: Path) -> ItemResult:
    cite = max_rows_count_report()
    gaps: list[str] = []
    wires: list[str] = []
    with running_serve(tmp / "e12", extra_env={"MEMNET_MAX_ROWS": "4"}) as svc:
        sid = svc.open_session()
        n3 = svc.mutate(
            sid,
            "\n".join(sec_create(i) for i in range(1, 4)) + "\n",
        )
        wires.extend(err_lines(n3.stderr))
        e1 = svc.mutate(
            sid,
            "MATCH (a {id: 'SEC_0001'}), (b {id: 'SEC_0002'})\n"
            "CREATE (a)-[:contains {id: 'E_ab'}]->(b)\n",
        )
        wires.extend(err_lines(e1.stderr))
        hk4 = svc.housekeep_stats(sid)
        rows4 = parse_stat_int(hk4.stdout, "rows")
        edges4 = parse_stat_int(hk4.stdout, "edges")
        e2 = svc.mutate(
            sid,
            "MATCH (a {id: 'SEC_0001'}), (b {id: 'SEC_0003'})\n"
            "CREATE (a)-[:contains {id: 'E_ac'}]->(b)\n",
        )
        wires.extend(err_lines(e2.stderr))
        rows_refuse = err_lines(e2.stderr)
        n4 = svc.mutate(sid, sec_create(4) + "\n")
        wires.extend(err_lines(n4.stderr))
        patch = svc.mutate(
            sid,
            "MATCH (n:SEC {id: 'SEC_0001'}) SET n.status = 'still'\n",
        )
        svc.close(sid)
    edge_counted = (
        e1.exit_code == 0
        and e2.exit_code != 0
        and any("limit_exceeded" in x and "rows" in x for x in rows_refuse)
    )
    if n3.exit_code != 0:
        gaps.append("three nodes at max_rows=4 failed")
    if e1.exit_code != 0:
        gaps.append("first edge (row 4) failed; edges may be excluded from MEMNET_MAX_ROWS")
    if e2.exit_code == 0:
        gaps.append("second edge succeeded at 5 rows — edges not counted")
    if not edge_counted:
        gaps.append("did not observe rows 5/4 on a new edge")
    verdict = "yes" if edge_counted and not gaps else "no"
    return ItemResult(
        item="E12 MEMNET_MAX_ROWS counts nodes plus edges",
        verdict=verdict,
        notes=[
            "Caps.max_rows default 5000 (MEMNET_MAX_ROWS). row_count_non_law sums every "
            "tag except LAW; upsert treats EDG as a non-LAW row. pin_map --max-rows is a "
            "different clip (DEFAULT_QUERY_MAX_ROWS=50).",
            f"housekeep after 3 nodes + 1 edge: rows={rows4} edges={edges4}",
            "SET of an existing hid still works at the cap.",
        ],
        numbers={
            "code": cite,
            "three_nodes_exit": n3.exit_code,
            "first_edge_exit": e1.exit_code,
            "rows_after_first_edge": rows4,
            "edges_after_first_edge": edges4,
            "second_edge_exit": e2.exit_code,
            "second_edge_err": rows_refuse,
            "fourth_node_exit": n4.exit_code,
            "patch_at_cap_exit": patch.exit_code,
            "counts_nodes_plus_edges": edge_counted,
        },
        wires=wires,
        gaps=gaps,
    )


def item_e13_strings(svc: ServeProc, tmp: Path) -> ItemResult:
    caps = mutate_byte_cap_report()
    target = 16 * 1024
    blob = make_special_blob(target, newlines=True, pipes=True)
    blob_plain = make_special_blob(target, newlines=False, pipes=False)
    blob_pipe = make_special_blob(target, newlines=False, pipes=True)
    gaps: list[str] = []
    wires: list[str] = []
    cases: dict[str, Any] = {
        "blob_bytes": len(blob.encode("utf-8")),
        "plain_bytes": len(blob_plain.encode("utf-8")),
        "pipe_bytes": len(blob_pipe.encode("utf-8")),
        "caps": caps,
    }

    sid = svc.open_session()
    insert_iso = svc.mutate(
        sid,
        "INSERT (:USR {id: 'USR_ins', key: 'k', value: 'x', recycle: ''})\n",
    )
    cases["insert_iso"] = {
        "exit": insert_iso.exit_code,
        "errs": err_lines(insert_iso.stderr),
    }
    wires.extend(err_lines(insert_iso.stderr))
    create = svc.mutate(
        sid,
        "CREATE (:USR {id: 'USR_big', key: 'blob', value: " + gql_str(blob) + ", recycle: ''})\n",
    )
    cases["create_16kib"] = {
        "exit": create.exit_code,
        "errs": err_lines(create.stderr),
    }
    wires.extend(err_lines(create.stderr))
    setted = svc.mutate(
        sid,
        "MATCH (n:USR {id: 'USR_big'}) SET n.value = " + gql_str(blob) + "\n",
    )
    cases["set_16kib"] = {"exit": setted.exit_code, "errs": err_lines(setted.stderr)}
    wires.extend(err_lines(setted.stderr))
    pin = svc.pin_map(sid, cue="USR_big")
    props = shaped_node_props(pin.stdout) or {}
    got = props.get("value")
    ram_ok = create.exit_code == 0 and setted.exit_code == 0 and got == blob
    cases["pin_map_roundtrip"] = ram_ok
    cases["pin_map_exit"] = pin.exit_code
    cases["pin_map_value_bytes"] = len(got.encode("utf-8")) if isinstance(got, str) else None
    if not ram_ok:
        gaps.append("16 KiB special blob did not round-trip CREATE/SET/pin_map")
        wires.extend(err_lines(pin.stderr))

    bad_esc = svc.mutate(
        sid,
        "CREATE (:USR {id: 'USR_esc', key: 'k', value: '\\q', recycle: ''})\n",
    )
    cases["unknown_escape"] = {
        "exit": bad_esc.exit_code,
        "errs": err_lines(bad_esc.stderr),
    }
    wires.extend(err_lines(bad_esc.stderr))

    snap = tmp / "e13-nl.snap"
    save = svc.save(sid, snap)
    svc.close(sid)
    load = svc.load_file(snap)
    cases["snap_nl"] = {
        "save_exit": save.exit_code,
        "load_exit": load.exit_code,
        "errs": err_lines(load.stderr),
    }
    wires.extend(err_lines(load.stderr))

    sid2 = svc.open_session()
    svc.mutate(
        sid2,
        "CREATE (:USR {id: 'USR_plain', key: 'blob', value: "
        + gql_str(blob_plain)
        + ", recycle: ''})\n",
    )
    snap2 = tmp / "e13-plain.snap"
    svc.save(sid2, snap2)
    svc.close(sid2)
    load2 = svc.load_file(snap2)
    cases["snap_plain"] = {
        "load_exit": load2.exit_code,
        "errs": err_lines(load2.stderr),
    }
    wires.extend(err_lines(load2.stderr))

    sid3 = svc.open_session()
    svc.mutate(
        sid3,
        "CREATE (:USR {id: 'USR_pipe', key: 'blob', value: "
        + gql_str(blob_pipe)
        + ", recycle: ''})\n",
    )
    snap3 = tmp / "e13-pipe.snap"
    svc.save(sid3, snap3)
    svc.close(sid3)
    load3 = svc.load_file(snap3)
    cases["snap_pipe"] = {
        "load_exit": load3.exit_code,
        "errs": err_lines(load3.stderr),
    }
    wires.extend(err_lines(load3.stderr))

    snap_ok = load.exit_code == 0 and load2.exit_code == 0 and load3.exit_code == 0
    if snap_ok:
        gaps.append("16 KiB snapshot load unexpectedly succeeded for all variants")
    notes = [
        "GQL string literals: single or double quotes; escapes are \\\\ \\' \\\" \\n \\r \\t only. "
        "Unknown escape -> parse_error (GraphGlot/ParseError). gql mutate does not enforce "
        "MEMNET_MAX_VALUE_BYTES=4096 or MEMNET_MAX_LINE_BYTES=32768 (cap-contract bug 4).",
        "Leftover parse_line: value_bytes 4096 -> @ERR: limit_exceeded|value_bytes {n}/{max} "
        "(inner pipe becomes space); line_bytes 32768 -> limit_exceeded|line_bytes; "
        "newline_in_value; FIELD_COUNT. Mutate stdin: batch_lines 1000. Serve frame 4 MiB.",
        "ISO INSERT is not the mutate spelling (CREATE is).",
    ]
    if ram_ok and not snap_ok:
        verdict = "note"
        notes.append(
            "16 KiB survives CREATE/SET/pin_map in RAM (bug 4). Snapshot save/load does not "
            "round-trip byte-for-byte. Newlines split leftover pipe lines (FIELD_COUNT). "
            "Leftover emit escapes | as \\| so a 16 KiB value with pipes still hits "
            "value_bytes 16384/4096, same as a plain 16 KiB value."
        )
    elif ram_ok and snap_ok:
        verdict = "yes"
    else:
        verdict = "no"
    return ItemResult(
        item="E13 16 KiB string properties + mutate/GQL byte caps",
        verdict=verdict,
        notes=notes,
        numbers=cases,
        wires=wires,
        gaps=gaps,
    )


def item_e14_lists(svc: ServeProc) -> ItemResult:
    gaps: list[str] = []
    wires: list[str] = []
    cases: dict[str, Any] = {}
    map_lines = [ln for ln in citekeys_schema().splitlines() if ln]
    sid = svc.open_session(map_lines=map_lines)
    create = svc.mutate(
        sid,
        "CREATE (:USR {id: 'USR_cite', key: 'paper', value: 'v', "
        "citeKeys: ['k', 'other'], recycle: ''})\n"
        "CREATE (:USR {id: 'USR_miss', key: 'other', value: 'v', "
        "citeKeys: ['x'], recycle: ''})\n",
    )
    cases["create_list"] = {"exit": create.exit_code, "errs": err_lines(create.stderr)}
    wires.extend(err_lines(create.stderr))
    pin = svc.pin_map(sid, cue="USR_cite")
    props = shaped_node_props(pin.stdout) or {}
    stored = props.get("citeKeys")
    cases["pin_map_citeKeys"] = stored
    store_ok = create.exit_code == 0 and stored == ["k", "other"]
    if not store_ok:
        gaps.append("list-valued citeKeys did not store/emit as a list")
        wires.extend(err_lines(pin.stderr))

    loc = svc.pin_map(sid, kind="USR", locator='citeKeys=["k","other"]')
    loc_hit = loc.exit_code == 0 and "paper" in loc.stdout
    cases["locator_equality"] = {
        "exit": loc.exit_code,
        "hit": loc_hit,
        "errs": err_lines(loc.stderr),
    }
    wires.extend(err_lines(loc.stderr))

    loc_member = svc.pin_map(sid, kind="USR", locator="citeKeys=k")
    cases["locator_bare_k"] = {
        "exit": loc_member.exit_code,
        "stdout_has_paper": "paper" in loc_member.stdout,
        "cue_miss": "## CueMiss" in loc_member.stdout,
        "errs": err_lines(loc_member.stderr),
    }

    in_stmt = "MATCH (p:USR) WHERE 'k' IN p.citeKeys SET p.key = 'hit'\n"
    in_mut = svc.mutate(sid, in_stmt)
    cases["where_in_set"] = {
        "exit": in_mut.exit_code,
        "errs": err_lines(in_mut.stderr),
        "ok_lines": [ln for ln in in_mut.stderr.splitlines() if "ok=" in ln][:2],
    }
    wires.extend(err_lines(in_mut.stderr))
    pin_after = svc.pin_map(sid, cue="USR_cite")
    pin_miss = svc.pin_map(sid, cue="USR_miss")
    props_hit = shaped_node_props(pin_after.stdout) or {}
    props_miss = shaped_node_props(pin_miss.stdout) or {}
    cases["after_where_in"] = {
        "cite_key": props_hit.get("key"),
        "miss_key": props_miss.get("key"),
    }
    membership_works = (
        in_mut.exit_code == 0 and props_hit.get("key") == "hit" and props_miss.get("key") != "hit"
    )
    where_ignored = (
        in_mut.exit_code == 0 and props_hit.get("key") == "hit" and props_miss.get("key") == "hit"
    )

    leftover = svc.read_list(sid, tag="USR", where="citeKeys=*k*")
    cases["leftover_where_glob"] = {
        "exit": leftover.exit_code,
        "lines": len(leftover.stdout.splitlines()),
        "has_cite": "USR_cite" in leftover.stdout or "paper" in leftover.stdout,
        "errs": err_lines(leftover.stderr),
    }
    find_kw = svc.find(sid, kind="USR", keyword="k")
    cases["find_keyword_k"] = {
        "exit": find_kw.exit_code,
        "errs": err_lines(find_kw.stderr),
        "has_cite": "k" in find_kw.stdout,
    }

    svc.close(sid)
    notes = [
        "GQL parser accepts [a, b] lists; _value_to_store json.dumps them into a string field. "
        "pin_map re-parses JSON-looking [ ] on emit.",
        "pin_map / find locators are KEY=VAL exact equality (no IN membership). leftover "
        "read list --where is field=value with * ? glob on the JSON string.",
        "MATCH…WHERE is not a product mutate form; leftover lowering has no IN operator.",
    ]
    if membership_works:
        verdict = "yes"
        notes.append("WHERE 'k' IN p.citeKeys unexpectedly filtered (product IN).")
    elif store_ok and not membership_works:
        verdict = "note"
        if where_ignored:
            notes.append(
                "WHERE 'k' IN p.citeKeys SET applied to every matched USR (WHERE ignored)."
            )
            gaps.append("WHERE IN is ignored on leftover MATCH…SET (not membership filter)")
        elif in_mut.exit_code != 0:
            notes.append(
                "WHERE IN mutate refused (see wire). Lists store; membership filter does not."
            )
        if not loc_hit:
            notes.append("locator equality on the JSON string is the only pin_map list lookup.")
    else:
        verdict = "no"
    return ItemResult(
        item="E14 list-valued properties and IN membership",
        verdict=verdict,
        notes=notes,
        numbers={
            **cases,
            "store_ok": store_ok,
            "membership_works": membership_works,
            "where_ignored": where_ignored,
            "locator_json_equality": loc_hit,
        },
        wires=wires,
        gaps=gaps,
    )


def item_fat_rss(
    svc: ServeProc,
    *,
    n_nodes: int,
    n_fat: int,
    samples: int,
) -> ItemResult:
    batches = populate_fat_batches(n_nodes, n_fat)
    payload = sum(fat_payload_bytes(j) for j in range(n_fat))
    deltas: list[int] = []
    baseline = _rss_or_zero(svc)
    sids: list[str] = []
    try:
        for _ in range(samples):
            before = _rss_or_zero(svc)
            sid = svc.open_session()
            replies = svc.populate_stmts(sid, batches)
            if any(r.exit_code != 0 for r in replies):
                err = next(r for r in replies if r.exit_code != 0)
                return ItemResult(
                    item="6b RSS delta per 3000-node fat session",
                    verdict="no",
                    notes=["fat populate failed"],
                    wires=err_lines(err.stderr),
                    gaps=["populate of 3000-node fat fixture failed"],
                    numbers={"payload_utf8_bytes": payload},
                )
            after = _rss_or_zero(svc)
            deltas.append(after - before)
            sids.append(sid)
        mean = int(sum(deltas) / len(deltas)) if deltas else 0
        return ItemResult(
            item="6b RSS delta per 3000-node fat session",
            verdict="yes" if mean > 0 else "note",
            notes=[
                "3000 nodes, no edges; 1500 USR values of 2/3/4 KiB.",
                "1500 x 2-4 KiB is about 3-6 MiB of text (not 1 MiB); "
                "payload_utf8_bytes is the sum.",
                "Delta is serve-process RSS after open+populate, sessions still live.",
            ],
            numbers={
                "samples": samples,
                "n_nodes": n_nodes,
                "n_fat": n_fat,
                "payload_utf8_bytes": payload,
                "payload_mib": round(payload / (1024 * 1024), 3),
                "deltas_bytes": deltas,
                "mean_bytes": mean,
                "mean_mib": round(mean / (1024 * 1024), 3),
                "baseline_bytes": baseline,
                "batch_count": len(batches),
            },
        )
    finally:
        for sid in sids:
            svc.close(sid)


def item_fat_churn(
    svc: ServeProc,
    *,
    cycles: int,
    n_nodes: int,
    n_fat: int,
) -> ItemResult:
    batches = populate_fat_batches(n_nodes, n_fat)
    base_n, cap = svc.live_count()
    base_rss = _rss_or_zero(svc)
    per: list[dict[str, Any]] = []
    failed = 0
    t0 = time.monotonic()
    for i in range(1, cycles + 1):
        sid = svc.open_session()
        replies = svc.populate_stmts(sid, batches)
        if any(r.exit_code != 0 for r in replies):
            failed += 1
        closed = svc.close(sid)
        if closed.exit_code != 0:
            failed += 1
        if i % max(1, min(4, cycles)) == 0 or i == cycles:
            live, _cap = svc.live_count()
            rss = _rss_or_zero(svc)
            per.append(
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
    deltas = [row["rss_delta_from_baseline"] for row in per]
    grew = bool(deltas) and deltas[-1] > deltas[0] + 8 * 1024 * 1024
    live_flat = end_n == base_n
    gaps = []
    verdict = "yes" if live_flat and failed == 0 and not grew else "note"
    if not live_flat:
        gaps.append(f"live count {base_n} -> {end_n}, not back to baseline")
        verdict = "no"
    if failed:
        gaps.append(f"{failed} open/populate/close failures")
        verdict = "no"
    if grew:
        gaps.append("RSS rose more than 8 MiB across fat churn; not flat")
        if verdict == "yes":
            verdict = "note"
    return ItemResult(
        item="2b Fat-session churn (3000 nodes, 2–4 KiB text)",
        verdict=verdict,
        notes=[
            "RSS trend after close (allocator may retain pages).",
            f"elapsed_s={elapsed:.1f}",
            f"max_sessions_cap={cap}",
            "110 cycles of this fixture is not feasible in this probe; default is a short run.",
        ],
        numbers={
            "cycles": cycles,
            "n_nodes": n_nodes,
            "n_fat": n_fat,
            "baseline_live": base_n,
            "end_live": end_n,
            "baseline_rss_bytes": base_rss,
            "end_rss_bytes": rss_end,
            "rss_samples": per,
            "failed": failed,
            "elapsed_s": round(elapsed, 2),
        },
        gaps=gaps,
    )


def _truncation_lines(stdout: str) -> list[str]:
    return [ln for ln in stdout.splitlines() if ln.startswith("## Truncation")]


def _time_call(fn):  # type: ignore[no-untyped-def]
    t0 = time.perf_counter()
    reply = fn()
    return time.perf_counter() - t0, reply


def run_fulldoc_e12_e16(
    tmp: Path,
    *,
    n_nodes: int,
    n_fat: int,
    e16_n: int,
    warmup: int = 10,
    cap_low: int = 5000,
    cap_high: int = 10000,
) -> list[ItemResult]:
    cite = max_rows_count_report()
    path_info = snapshot_load_cap_report()
    wires: list[str] = []
    gaps: list[str] = []
    numbers: dict[str, Any] = {
        "code": cite,
        "load_path": path_info,
        "n_nodes": n_nodes,
        "n_fat": n_fat,
        "n_edges_target": (n_nodes - n_fat) + 2 * n_fat,
        "cap_low": cap_low,
        "cap_high": cap_high,
        "cpu_model": cpu_model(),
    }
    snap_full = tmp / "fulldoc-7500.snap"
    snap_partial = tmp / "fulldoc-5000.snap"
    e16_result: ItemResult | None = None

    # --- default 5000: nodes fit; edges refuse ---
    with running_serve(
        tmp / "e12-5k", extra_env={"MEMNET_MAX_ROWS": str(cap_low)}, timeout_s=300.0
    ) as svc5:
        sid = svc5.open_session()
        node_batches = populate_fulldoc_batches(n_nodes, n_fat, nodes_only=True)
        node_replies = svc5.populate_stmts(sid, node_batches)
        node_ok = all(r.exit_code == 0 for r in node_replies)
        if not node_ok:
            wires.extend(err_lines(node_replies[-1].stderr))
            gaps.append("5000-cap: 3000-node fulldoc populate failed")
        hk_nodes = svc5.housekeep_stats(sid)
        rows_nodes = parse_stat_int(hk_nodes.stdout, "rows")
        edges_nodes = parse_stat_int(hk_nodes.stdout, "edges")
        edge_stmts = []
        n_thin = n_nodes - n_fat
        if node_ok:
            edge_stmts = fulldoc_edge_stmts(n_thin=n_thin, n_fat=n_fat)
        # Fill until cap_low rows (nodes + edges), then one more edge.
        fit_n = max(0, cap_low - n_nodes)
        fit_edges = edge_stmts[:fit_n]
        extra_edge = edge_stmts[fit_n : fit_n + 1]
        fit_batches = []
        if fit_edges:
            fit_batches = pack_batches(fit_edges, batch_lines=DEFAULT_BATCH_LINES)
        edge_fit = svc5.populate_stmts(sid, fit_batches, allow_new_relation=True)
        edge_fit_ok = bool(fit_batches) and all(r.exit_code == 0 for r in edge_fit)
        if fit_batches and not edge_fit_ok:
            wires.extend(err_lines(edge_fit[-1].stderr))
            gaps.append("5000-cap: first 2000 edges failed (expected to fit)")
        hk_full5 = svc5.housekeep_stats(sid)
        rows_at_cap = parse_stat_int(hk_full5.stdout, "rows")
        edges_at_cap = parse_stat_int(hk_full5.stdout, "edges")
        if extra_edge:
            refuse = svc5.mutate(sid, extra_edge[0] + "\n", allow_new_relation=True)
        else:
            refuse = svc5.mutate(sid, "CREATE (:SEC {id: 'SEC_overflow'})\n")
        refuse_err = err_lines(refuse.stderr)
        wires.extend(refuse_err + err_lines(pin4000.stderr))
        write_refused_rows = refuse.exit_code != 0 and any(
            "limit_exceeded" in e and "rows" in e for e in refuse_err
        )
        pin50 = svc5.pin_map(sid, cue=HUB_SEC, depth=1, max_rows=50)
        pin4000 = svc5.pin_map(sid, cue=HUB_SEC, depth=1, max_rows=4000)
        trunc50 = _truncation_lines(pin50.stdout)
        trunc4000 = _truncation_lines(pin4000.stdout)
        read_not_session_refuse = pin50.exit_code == 0
        save_p = svc5.save(sid, snap_partial)
        svc5.close(sid)
        load_p = svc5.load_file(snap_partial)
        wires.extend(err_lines(load_p.stderr) + stat_lines(load_p.stdout))
        load_partial_ok = load_p.exit_code == 0
        if load_partial_ok:
            loaded_sid = _sid_from(load_p.stdout)
            if loaded_sid:
                svc5.close(loaded_sid)
        numbers["at_5000"] = {
            "node_ok": node_ok,
            "rows_after_nodes": rows_nodes,
            "edges_after_nodes": edges_nodes,
            "edge_fit_ok": edge_fit_ok,
            "rows_at_cap": rows_at_cap,
            "edges_at_cap": edges_at_cap,
            "write_refuse_exit": refuse.exit_code,
            "write_refuse_err": refuse_err,
            "write_refused_rows": write_refused_rows,
            "pin_map_50_exit": pin50.exit_code,
            "pin_map_50_truncation": trunc50,
            "pin_map_4000_exit": pin4000.exit_code,
            "pin_map_4000_truncation": trunc4000,
            "pin_map_4000_err": err_lines(pin4000.stderr),
            "read_not_session_row_refuse": read_not_session_refuse,
            "partial_save_exit": save_p.exit_code,
            "partial_load_exit": load_p.exit_code,
            "partial_load_ok": load_partial_ok,
        }
        if not write_refused_rows:
            gaps.append("5000-cap write of edge 2001 did not refuse limit_exceeded|rows")
        if not trunc50:
            gaps.append("pin_map max_rows=50 on hub did not Truncation-clip")

    # --- 10000: full fixture fits; load is not ingest_budget ---
    with running_serve(
        tmp / "e12-10k", extra_env={"MEMNET_MAX_ROWS": str(cap_high)}, timeout_s=300.0
    ) as svc10:
        sid10 = svc10.open_session()
        full_batches = populate_fulldoc_batches(n_nodes, n_fat)
        full_replies = svc10.populate_stmts(sid10, full_batches, allow_new_relation=True)
        full_ok = all(r.exit_code == 0 for r in full_replies)
        if not full_ok:
            wires.extend(err_lines(full_replies[-1].stderr))
            gaps.append("10000-cap: fulldoc populate failed")
        hk10 = svc10.housekeep_stats(sid10)
        rows10 = parse_stat_int(hk10.stdout, "rows")
        edges10 = parse_stat_int(hk10.stdout, "edges")
        pin10_50 = svc10.pin_map(sid10, cue=HUB_SEC, depth=1, max_rows=50)
        pin10_4000 = svc10.pin_map(sid10, cue=HUB_SEC, depth=1, max_rows=4000)
        save10 = svc10.save(sid10, snap_full)
        load10 = None
        e16_result = item_e16(
            svc10,
            sid10,
            n=e16_n,
            warmup=warmup,
            n_thin=n_nodes - n_fat,
        )
        svc10.close(sid10)
        load10 = svc10.load_file(snap_full)
        ingest_hit = any("ingest_budget" in e for e in err_lines(load10.stderr))
        rows_hit = any("limit_exceeded" in e and "rows" in e for e in err_lines(load10.stderr))
        load10_ok = load10.exit_code == 0
        loaded_rows10 = parse_stat_int(load10.stdout, "loaded")
        if load10_ok:
            new10 = _sid_from(load10.stdout)
            if new10:
                hk_l = svc10.housekeep_stats(new10)
                loaded_rows10 = parse_stat_int(hk_l.stdout, "rows") or loaded_rows10
                svc10.close(new10)
        numbers["at_10000"] = {
            "populate_ok": full_ok,
            "rows": rows10,
            "edges": edges10,
            "pin_map_50_exit": pin10_50.exit_code,
            "pin_map_50_truncation": _truncation_lines(pin10_50.stdout),
            "pin_map_4000_exit": pin10_4000.exit_code,
            "pin_map_4000_truncation": _truncation_lines(pin10_4000.stdout),
            "pin_map_4000_err": err_lines(pin10_4000.stderr),
            "save_exit": save10.exit_code,
            "load_exit": load10.exit_code,
            "load_ok": load10_ok,
            "loaded_rows": loaded_rows10,
            "ingest_budget_on_load": ingest_hit,
            "rows_cap_on_load": rows_hit,
            "load_err": err_lines(load10.stderr),
        }
        wires.extend(
            err_lines(load10.stderr)
            + _truncation_lines(pin10_50.stdout)
            + _truncation_lines(pin10_4000.stdout)
        )
        if ingest_hit:
            gaps.append("10000-cap session_load refused ingest_budget (unexpected)")
        if not load10_ok:
            gaps.append("10000-cap session_load of fulldoc snapshot failed")

    # --- 5000 load of 7500-row snapshot ---
    load_7500_on_5k: dict[str, Any] = {}
    if snap_full.is_file():
        with running_serve(
            tmp / "e12-5k-load", extra_env={"MEMNET_MAX_ROWS": str(cap_low)}, timeout_s=300.0
        ) as svc_l:
            load_big = svc_l.load_file(snap_full)
            load_7500_on_5k = {
                "exit": load_big.exit_code,
                "errs": err_lines(load_big.stderr),
                "ingest_budget": any("ingest_budget" in e for e in err_lines(load_big.stderr)),
                "rows_cap": any(
                    "limit_exceeded" in e and "rows" in e for e in err_lines(load_big.stderr)
                ),
            }
            wires.extend(err_lines(load_big.stderr))
    numbers["load_7500_on_5000"] = load_7500_on_5k

    edges_count = bool(numbers.get("at_5000", {}).get("write_refused_rows"))
    e11_10000 = bool(numbers.get("at_10000", {}).get("load_ok")) and not bool(
        numbers.get("at_10000", {}).get("ingest_budget_on_load")
    )
    load_5k_rows = bool(load_7500_on_5k.get("rows_cap"))
    load_5k_ok = load_7500_on_5k.get("exit") == 0
    if load_5k_ok:
        gaps.append("5000-cap loaded 7500-row snapshot (edges would not count)")
    notes = [
        "MEMNET_MAX_ROWS counts nodes plus edges on write (upsert) and session_load "
        "(same upsert). pin_map read clips with ## Truncation (query M), not the "
        "session row cap.",
        path_info["code_path"],
        f"Fulldoc {n_nodes} nodes + {numbers['n_edges_target']} edges. "
        f"Cap {cap_low} refuses the next new row. Cap {cap_high} holds the fixture. "
        "session_load is not ingest_budget (2000-edge Path-B cap).",
        f"cpu_model={cpu_model()}",
    ]
    if edges_count and e11_10000 and load_5k_rows:
        verdict = "yes"
    elif edges_count and e11_10000 and load_7500_on_5k.get("exit") not in (None, 0):
        verdict = "note"
        if not load_5k_rows:
            gaps.append("7500-row snapshot load on 5000 did not show limit_exceeded|rows")
    else:
        verdict = "no"
    e12 = ItemResult(
        item="E12 revised fulldoc MEMNET_MAX_ROWS (5000 and 10000)",
        verdict=verdict,
        notes=notes,
        numbers=numbers,
        wires=wires,
        gaps=gaps,
    )
    out = [e12]
    if e16_result is not None:
        out.append(e16_result)
    return out


def item_e16(
    svc: ServeProc,
    sid: str,
    *,
    n: int,
    warmup: int,
    n_thin: int,
) -> ItemResult:
    gaps: list[str] = []
    wires: list[str] = []
    cpu = cpu_model()
    blob = make_fat_blob(2048)

    def atomic_batch(i: int) -> str:
        cit = f"E_cit{i:04d}"
        return (
            f"MATCH (n:USR {{id: 'USR_fat0000'}}) SET n.value = {gql_str(blob)}\n"
            + edge_delete(cit)
            + "\n"
            + edge_create(
                "cites",
                f"E_lata{i:04d}",
                "SEC_0002",
                "SEC_0003",
            )
            + "\n"
            + edge_create(
                "refersTo",
                f"E_latb{i:04d}",
                "SEC_0002",
                "SEC_0004",
            )
            + "\n"
        )

    # Discover delete-while-referenced on a sacrificial node (after lookups we
    # will know). Create SEC_probe_del with one inbound, then DELETE it.
    setup = svc.mutate(
        sid,
        sec_create(n_thin + 1)
        + "\n"
        + edge_create(
            "refersTo",
            "E_probe_del",
            "USR_fat0000",
            f"SEC_{n_thin + 1:04d}",
        )
        + "\n",
        allow_new_relation=True,
    )
    probe_id = f"SEC_{n_thin + 1:04d}"
    documented_edge_del = svc.mutate(sid, "MATCH ()-[r {id: 'E_probe_del'}]-() DELETE r\n")
    documented_edge_err = err_lines(documented_edge_del.stderr)
    del_probe = svc.mutate(
        sid,
        f"MATCH (n:SEC {{id: {gql_str(probe_id)}}}) DETACH DELETE n\n",
    )
    native_refuse = del_probe.exit_code != 0
    del_err = err_lines(del_probe.stderr)
    wires.extend(err_lines(setup.stderr) + documented_edge_err + del_err)
    # If DELETE succeeded, the node is gone and incident edge is dangling — no
    # native referenced check.

    a_samples: list[float] = []
    b_lookup: list[float] = []
    b_delete: list[float] = []
    b_pair: list[float] = []
    a_fail = 0
    start_i = 1
    total = warmup + n
    for i in range(start_i, start_i + total):
        dt, reply = _time_call(
            lambda i=i: svc.mutate(sid, atomic_batch(i), allow_new_relation=True)
        )
        if reply.exit_code != 0:
            a_fail += 1
            if i <= warmup + 3:
                wires.extend(err_lines(reply.stderr)[:2])
        if i > warmup:
            a_samples.append(dt)

    # Reverse lookup of hub (inbound inSection fan-in), then attempted DELETE.
    # If native refuse, DELETE the hub  n times (it stays). Else DELETE a
    # distinct existing SEC after save-equivalent: we still attempt hub DELETE
    # once per iter only when refused; otherwise lookup only + one documented try.
    delete_stmt = f"MATCH (n:SEC {{id: {gql_str(HUB_SEC)}}}) DETACH DELETE n\n"
    hub_still = True
    for i in range(total):
        t0 = time.perf_counter()
        look = svc.pin_map(sid, cue=HUB_SEC, depth=1, max_rows=400)
        t1 = time.perf_counter()
        if native_refuse:
            gone = svc.mutate(sid, delete_stmt)
            t2 = time.perf_counter()
            if i == 0:
                wires.extend(err_lines(gone.stderr)[:3])
        else:
            gone = None
            t2 = t1
            if i == 0:
                # One real attempt on the hub to confirm (destroys hub if it
                # succeeds; lookups after would miss). Skip: probe node already
                # showed DELETE succeeds. Keep hub for n reverse lookups.
                pass
        if i >= warmup:
            b_lookup.append(t1 - t0)
            if gone is not None:
                b_delete.append(t2 - t1)
                b_pair.append(t2 - t0)
    a_sum = latency_summary(a_samples)
    look_sum = latency_summary(b_lookup)
    del_sum = latency_summary(b_delete)
    pair_sum = latency_summary(b_pair)
    a_ok = a_sum["p95_ms"] is not None and a_sum["p95_ms"] <= E16_P95_BAR_MS and a_fail == 0
    b_ok = look_sum["p95_ms"] is not None and look_sum["p95_ms"] <= E16_P95_BAR_MS
    if pair_sum["p95_ms"] is not None:
        b_ok = b_ok and pair_sum["p95_ms"] <= E16_P95_BAR_MS
    notes = [
        f"cpu_model={cpu}",
        "Face host may be slower than this VM.",
        "Bar is 300 ms p95 on direct serve loopback, warm session, n>=200.",
    ]
    if native_refuse:
        notes.append("MemNet refused DELETE of a referenced node (native). Exact wire in numbers.")
    else:
        notes.append(
            "MemNet has no native delete-refused-while-referenced check. "
            "DETACH DELETE of a node with inbound edges deletes the node and leaves "
            "dangling edges (housekeep dangling). The product gate must refuse from "
            "the reverse lookup."
        )
        gaps.append("no native referenced-delete refuse")
    notes.append(
        "Documented MATCH ()-[r {id}]-() DELETE r lowers as a node DROP with empty id "
        "and refuses @ERR: not_found|DELETE matched no element. Atomic (a) uses "
        "MATCH (n WHERE true)-[r {id}]->() DELETE r, which reaches EdgeRec DROP."
    )
    if a_fail:
        gaps.append(f"{a_fail} atomic mutate failures")
    verdict = "yes" if a_ok and b_ok else "no"
    if a_ok and b_ok and not native_refuse:
        verdict = "note"
    return ItemResult(
        item="E16 fulldoc mutate and reverse-lookup latency",
        verdict=verdict,
        notes=notes,
        numbers={
            "cpu_model": cpu,
            "bar_p95_ms": E16_P95_BAR_MS,
            "warmup": warmup,
            "a_atomic_set_del_add": a_sum,
            "a_fail": a_fail,
            "b_reverse_lookup": look_sum,
            "b_delete_attempt": del_sum,
            "b_lookup_then_delete": pair_sum,
            "native_delete_refused": native_refuse,
            "delete_probe_exit": del_probe.exit_code,
            "delete_probe_err": del_err,
            "documented_edge_delete_exit": documented_edge_del.exit_code,
            "documented_edge_delete_err": documented_edge_err,
            "hub_survived": hub_still,
            "lookup_truncation_sample": _truncation_lines(look.stdout) if look else [],
        },
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
    parser.add_argument("--load-nodes", type=int, default=LOAD_PROBE_NODES)
    parser.add_argument("--fat-nodes", type=int, default=FAT_PROBE_NODES)
    parser.add_argument("--fat-text-nodes", type=int, default=FAT_TEXT_NODES)
    parser.add_argument("--fat-churn", type=int, default=8)
    parser.add_argument("--fat-rss-samples", type=int, default=3)
    parser.add_argument("--fulldoc-nodes", type=int, default=FULLDOC_NODES)
    parser.add_argument("--fulldoc-fat", type=int, default=FULLDOC_FAT)
    parser.add_argument("--e16-n", type=int, default=200)
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
    load_nodes = 80 if args.quick else args.load_nodes
    fat_nodes = 40 if args.quick else args.fat_nodes
    fat_text = 8 if args.quick else args.fat_text_nodes
    fat_churn = 2 if args.quick else args.fat_churn
    fat_samples = 1 if args.quick else args.fat_rss_samples
    fulldoc_nodes = 40 if args.quick else args.fulldoc_nodes
    fulldoc_fat = 8 if args.quick else args.fulldoc_fat
    e16_n = 20 if args.quick else args.e16_n
    cap_low = 50 if args.quick else 5000
    cap_high = 200 if args.quick else 10000

    results: list[ItemResult] = [item_cap_contract()]
    header: dict[str, Any] = {
        "product": __version__,
        "mcp_front": False,
        "transport": "loopback TCP length-prefixed JSON argv+stdin",
        "nodes": nodes,
        "churn": churn,
        "load_nodes": load_nodes,
        "fat_nodes": fat_nodes,
        "fat_text_nodes": fat_text,
        "fat_churn": fat_churn,
        "fulldoc_nodes": fulldoc_nodes,
        "e16_n": e16_n,
        "cpu_model": cpu_model(),
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
                if samples > 0:
                    results.append(item6_rss_delta(svc, n_parts=nodes, samples=samples))
                if churn > 0:
                    results.append(item2_churn(svc, cycles=churn, n_parts=nodes))
                results.append(item3_roundtrip(svc, tmp, n_parts=min(nodes, 1800)))
                results.append(item5_acl(svc))
                results.append(item7_gql(svc))
                if load_nodes > 0:
                    results.append(item_e11_load_budget(svc, tmp, n_nodes=load_nodes))
                results.append(item_e12_max_rows(tmp))
                results.append(item_e13_strings(svc, tmp))
                results.append(item_e14_lists(svc))
                if fulldoc_nodes > 0:
                    results.extend(
                        run_fulldoc_e12_e16(
                            tmp,
                            n_nodes=fulldoc_nodes,
                            n_fat=fulldoc_fat,
                            e16_n=e16_n,
                            cap_low=cap_low,
                            cap_high=cap_high,
                        )
                    )
                if fat_samples > 0:
                    results.append(
                        item_fat_rss(
                            svc,
                            n_nodes=fat_nodes,
                            n_fat=fat_text,
                            samples=fat_samples,
                        )
                    )
                if fat_churn > 0:
                    results.append(
                        item_fat_churn(
                            svc,
                            cycles=fat_churn,
                            n_nodes=fat_nodes,
                            n_fat=fat_text,
                        )
                    )
                if wait_s > 0:
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
