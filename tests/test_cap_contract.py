"""Cap contract: live probes must match docs/cap-contract.md. No session ids."""

from __future__ import annotations

import os
import re
from pathlib import Path

from cap_contract_lib import (
    _SID_RE,
    collect_all,
    defaults_record,
    redact,
    render_proof,
)

_DOC = Path("docs/cap-contract.md")


def test_defaults_match_library():
    d = defaults_record()
    assert d["max_rows"] == 5000
    assert d["max_relations"] == 200
    assert d["max_law"] == 100
    assert d["max_tags"] == 64
    assert d["max_fields"] == 32
    assert d["max_value_bytes"] == 4096
    assert d["max_line_bytes"] == 32768
    assert d["max_batch_lines"] == 1000
    assert d["max_sessions"] == 1024
    assert d["max_depth"] == 4
    assert d["max_fanout"] == 256
    assert d["lock_timeout_ms"] == 2000
    assert d["ingest_max_nodes"] == 2000
    assert d["ingest_max_edges"] == 2000
    assert d["ingest_max_files"] == 64
    assert d["query_max_rows"] == 50
    assert d["query_depth"] == 2
    assert d["ttl_minutes"] == 60
    assert d["serve_max_frame_bytes"] == 4 * 1024 * 1024
    assert d["shell_max_nodes"] == 8
    assert d["shell_max_edges"] == 12
    assert d["warn_budget"] == 12
    assert d["outline_exemplar_limit"] == 3


def test_every_cap_and_write_proof(memnet_temp, tmp_path: Path):
    del memnet_temp
    cases = collect_all(tmp_path)
    by_name = {c.name: c for c in cases}

    ingest_n = by_name["ingest_node_budget"]
    assert ingest_n.library_code == "ingest_budget"
    assert ingest_n.library_message == "pin budget exceeded (max_nodes=1)"
    assert ingest_n.wire == "@ERR: ingest_budget|pin budget exceeded (max_nodes=1)"

    ingest_e = by_name["ingest_edge_budget"]
    assert ingest_e.library_code == "ingest_budget"
    assert "max_edges=1" in ingest_e.library_message
    assert ingest_e.wire.startswith("@ERR: ingest_budget|edge budget exceeded")

    ingest_f = by_name["ingest_file_budget"]
    assert ingest_f.library_code == "ingest_budget"
    assert ingest_f.wire == ("@ERR: ingest_budget|too many .sysml files (3 > max_files=2)")

    rows = by_name["session_row_cap"]
    assert rows.library_code == "limit_exceeded"
    assert rows.library_message == "rows|3/2"
    assert rows.wire == "@ERR: limit_exceeded|rows 3/2"
    assert rows.extra["evicted"] == "False"
    assert rows.extra["rows_after_refuse"] == "2"
    assert "ok=0 fail=1" in rows.extra["ok_fail"]
    assert rows.mcp.startswith("@ERR: limit_exceeded|rows 3/2") or rows.mcp.endswith(
        "@ERR: limit_exceeded|rows 3/2"
    )

    rollback = by_name["row_cap_batch_rollback"]
    assert rollback.library_code == "limit_exceeded"
    assert rollback.extra["remaining_non_law_rows"] == "0"
    assert rollback.extra["rollback"] == "all-or-nothing"

    rel = by_name["relation_type_cap"]
    seed_n = int(rel.extra["seed_relation_count"])
    assert rel.library_code == "limit_exceeded"
    assert rel.library_message == f"relations|{seed_n + 1}/{seed_n}"
    assert rel.wire == f"@ERR: limit_exceeded|relations {seed_n + 1}/{seed_n}"

    unk = by_name["unknown_relation"]
    assert unk.library_code == "unknown_relation"
    assert unk.wire.startswith("@ERR: unknown_relation|zz_new")

    law = by_name["law_cap"]
    assert law.library_code == "limit_exceeded"
    assert law.library_message == "law|2/1"
    assert law.wire == "@ERR: limit_exceeded|law 2/1"

    tags = by_name["tag_map_cap"]
    assert tags.wire == "@ERR: limit_exceeded|tags 2/1"
    fields = by_name["fields_per_tag"]
    assert fields.wire == "@ERR: limit_exceeded|fields 4/2"

    val = by_name["pipe_value_bytes"]
    assert val.library_code == "limit_exceeded"
    assert val.wire.startswith("@ERR: limit_exceeded|value_bytes")
    lineb = by_name["pipe_line_bytes"]
    assert lineb.wire.startswith("@ERR: limit_exceeded|line_bytes")

    batch = by_name["mutate_batch_lines"]
    assert batch.wire == "@ERR: limit_exceeded|batch_lines 3/2"
    assert batch.extra["exit_code"] == "1"

    pin = by_name["pin_map_max_rows"]
    assert pin.kind == "signalled_clip"
    assert pin.wire.startswith("## Truncation truncated=true")
    assert "reason=max_rows" in pin.wire

    depth = by_name["pin_map_depth"]
    assert "reason=depth" in depth.wire
    assert depth.wire.startswith("## Truncation truncated=true")

    fan = by_name["pin_map_fanout"]
    assert "reason=fanout" in fan.wire

    shell = by_name["pin_map_shell"]
    assert "reason=shell" in shell.wire

    walk = by_name["query_walk_max_rows"]
    assert walk.kind == "silent_clip"
    assert walk.extra["hop_count"] == "3"
    assert walk.bug

    ctx = by_name["leftover_query_context"]
    assert ctx.kind == "silent_clip"
    assert ctx.bug

    outline = by_name["session_outline_max_rows"]
    assert "reason=max_rows" in outline.wire

    cue = by_name["find_limit_cue_conflict"]
    assert cue.wire.startswith("## CueConflict |Q|=")

    sess = by_name["max_sessions"]
    assert sess.wire == "@ERR: limit_exceeded|sessions 2/1"

    snap_pre = by_name["snap_model_session_precheck"]
    assert snap_pre.library_code == "limit_exceeded"
    assert snap_pre.wire.startswith("@ERR: limit_exceeded|sessions")
    assert snap_pre.extra["rollback"] == "nothing-created"
    assert snap_pre.extra["sessions_after"] == snap_pre.extra["sessions_before"]

    expired = by_name["ttl_expire_unsaved"]
    assert expired.library_code == "session_expired"
    assert expired.library_message == "snap_missing"
    assert expired.wire == "@ERR: session_expired|snap_missing"

    saved = by_name["ttl_expire_save_on"]
    assert saved.library_code == "session_expired"
    assert saved.library_message == "snap_available"
    assert saved.wire == "@ERR: session_expired|snap_available"
    assert saved.extra["snap_files"] == "1"

    nodir = by_name["ttl_save_on_expire_no_dir"]
    assert nodir.library_message == "snap_missing"

    who = by_name["acl_who"]
    assert who.wire.startswith("@ERR: acl_who|")
    assert "pass --caller or MEMNET_CALLER" in who.wire
    denied = by_name["acl_denied"]
    assert denied.wire.startswith("@ERR: acl_denied|")
    forbidden = by_name["acl_forbidden"]
    assert forbidden.wire.startswith("@ERR: acl_forbidden|")
    bind = by_name["acl_bind"]
    assert bind.wire.startswith("@ERR: acl_bind|")
    assert bind.bug
    scope = by_name["acl_scope"]
    assert scope.wire == ("@ERR: acl_scope|id/label outside WorkerWriteScope (GRANT)")

    rsv = by_name["reserve_conflict"]
    assert rsv.library_code == "reserve_conflict"
    assert rsv.wire.startswith("@ERR: reserve_conflict|")

    frame = by_name["serve_frame_cap"]
    assert "frame_too_large" in frame.wire
    assert frame.extra["exit_code"] == "1"

    lock = by_name["lock_timeout_ms"]
    assert lock.kind == "configured_not_enforced"
    assert lock.extra["stored"] == "2000"

    wrn = by_name["warn_budget"]
    assert wrn.extra["emitted"] == "12"
    assert wrn.extra["dropped"] == "8"

    ingest_row = by_name["ingest_commit_row_cap"]
    assert ingest_row.library_code == "limit_exceeded"
    assert ingest_row.extra["rollback"] == "all-or-nothing"

    proof = render_proof(cases, defaults=defaults_record())
    assert _SID_RE.search(proof) is None
    proof_default = str(tmp_path / "cap-contract-proof.log")
    dest = Path(os.environ.get("MEMNET_CAP_CONTRACT_PROOF", proof_default))
    dest.parent.mkdir(parents=True, exist_ok=True)
    dest.write_text(proof, encoding="utf-8")
    assert dest.is_file()


def test_doc_lists_live_defaults_and_wires():
    text = _DOC.read_text(encoding="utf-8")
    assert "mn_" not in text
    for needle in (
        "MEMNET_MAX_ROWS",
        "5000",
        "MEMNET_MAX_RELATIONS",
        "200",
        "ingest_budget",
        "pin budget exceeded (max_nodes=",
        "@ERR: limit_exceeded|rows",
        "## Truncation truncated=true",
        "snap_missing",
        "snap_available",
        "acl_bind",
        "MEMNET_SAVE_ON_EXPIRE",
        "MEMNET_EXPIRE_SNAPSHOT_DIR",
        "all-or-nothing",
        "Never treat a clipped read as complete",
        "Never retry a hard refuse unchanged",
        "serve_timeout",
        "snap_model",
        "1 catalog + N interiors",
    ):
        assert needle in text, needle


def test_redact_hides_session_prefix():
    sample = "opened " + "mn_" + "deadbeef" + " ok"
    assert redact(sample) == "opened <session> ok"
    assert not re.search(r"mn_[0-9a-fA-F]+", redact(sample))
