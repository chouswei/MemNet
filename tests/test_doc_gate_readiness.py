"""One session per document over serve: helpers + a live loopback serve."""

from __future__ import annotations

from pathlib import Path

import pytest

from doc_gate_lib import (
    CAP_CONTRACT,
    CAP_CONTRACT_NEEDLES,
    PROP32,
    ServeProc,
    assert_sid_free,
    canonical_snapshot,
    err_lines,
    gql_str,
    populate_batches,
    redact,
    running_serve,
    schema_prop32,
    snapshot_write_once_report,
    stat_lines,
)
from memnet import __version__
from memnet.snapshot import SNAPSHOT_MAGIC


def test_version_is_0_19_18():
    assert __version__ == "0.19.18"


def test_cap_contract_needles_unchanged():
    text = CAP_CONTRACT.read_text(encoding="utf-8")
    assert_sid_free(text)
    for needle in CAP_CONTRACT_NEEDLES:
        assert needle in text, needle


def test_redact_hides_session_prefix():
    sample = "opened " + "mn_" + "deadbeef" + " ok"
    assert redact(sample) == "opened <session> ok"
    assert_sid_free(redact(sample))


def test_canonical_snapshot_drops_snap_meta_and_sids(tmp_path: Path):
    sid = "mn_" + "00ff00aa"
    text = (
        f"{SNAPSHOT_MAGIC}\n"
        f"@SNAP: 1|{sid}|2026-01-01T00:00:00Z|2026-01-01T01:00:00Z|60|1|-\n"
        "# map\nSCHEMA SEC ; fields=id heading\n"
        "# relations\n@REL: contains\n"
        "# records\n@SEC: SEC_0001|Part 1\n"
    )
    can = canonical_snapshot(text)
    assert "@SNAP: <meta>" in can
    assert sid not in can
    assert "mn_" not in can
    assert "@SEC: SEC_0001|Part 1" in can


def test_write_snapshot_is_not_write_once():
    report = snapshot_write_once_report()
    assert report["write_snapshot_uses_path_write_text"] is True
    assert report["engine_o_excl"] is False
    assert report["engine_chmod"] is False
    assert report["caller_or_filesystem_only"] is True


def test_populate_batches_split_and_sid_free():
    batches = populate_batches(1800, text_nodes=8, edges=40, batch_lines=900)
    assert len(batches) >= 2
    joined = "".join(batches)
    assert joined.count("CREATE (:SEC") == 1800
    assert "测例" in joined
    assert "Pipes |" in joined
    assert_sid_free(joined)
    assert all(chunk.count("\n") <= 900 for chunk in batches)


def test_prop32_schema_has_32_fields():
    assert len(PROP32) == 32
    line = schema_prop32().splitlines()[0]
    fields = line.split("fields=", 1)[1].split()
    assert len(fields) == 32


@pytest.fixture
def doc_serve(tmp_path: Path):
    with running_serve(tmp_path) as svc:
        yield svc


def _open_ok(svc: ServeProc) -> str:
    sid = svc.open_session()
    assert sid.startswith("mn_")
    return sid


def test_serve_envelope_has_no_mcp_errors_field(doc_serve: ServeProc):
    reply = doc_serve.expire_status()
    assert reply.exit_code == 0
    assert set(reply.keys) == {"exit_code", "stdout", "stderr"}
    assert "errors" not in reply.keys
    assert "session_id" not in reply.keys
    assert reply.request["args"] == ["session", "expire-status"]
    stats = stat_lines(reply.stdout)
    assert any(s.startswith("@STAT: save_on_expire|1|") for s in stats)
    assert any(s.startswith("@STAT: expire_snapshot_dir_set|1|") for s in stats)
    assert_sid_free(redact(reply.stdout), redact(reply.stderr))


def test_housekeep_stats_and_usage_have_no_per_session_rss(doc_serve: ServeProc):
    import json

    sid = _open_ok(doc_serve)
    hk = doc_serve.housekeep_stats(sid)
    assert hk.exit_code == 0, redact(hk.stderr)
    joined = hk.stdout + hk.stderr
    assert "rss" not in joined.lower()
    usage = doc_serve.usage_report()
    assert usage.exit_code == 0, redact(usage.stderr)
    body = json.loads(usage.stdout)
    assert "rss_bytes" in body["process"]
    assert all("rss" not in row for row in body["session_rows"])
    assert "mn_" not in usage.stdout
    doc_serve.close(sid)


def test_snapshot_roundtrip_unicode_pipe_quote(doc_serve: ServeProc, tmp_path: Path):
    sid = _open_ok(doc_serve)
    blob = "unicode 测例 Ω | pipe and quotes \"double\" and 'single'"
    gql = (
        "CREATE (:USR {id: 'USR_rt', key: 'blob', value: " + gql_str(blob) + ", recycle: ''})\n"
        "CREATE (:SEC {id: 'SEC_0001', art: 'ART_doc', heading: 'P1', "
        "numbering: '1', parent: '', order: '1', status: 'active', recycle: ''})\n"
    )
    mut = doc_serve.mutate(sid, gql)
    assert mut.exit_code == 0, redact(mut.stderr)
    snap = tmp_path / "rt.snap"
    save = doc_serve.save(sid, snap)
    assert save.exit_code == 0, redact(save.stderr)
    assert "@STAT: saved|" in save.stdout
    src = canonical_snapshot(snap.read_text(encoding="utf-8"))
    doc_serve.close(sid)
    load = doc_serve.load_file(snap)
    assert load.exit_code == 0, redact(load.stderr)
    new = None
    for line in load.stdout.splitlines():
        if line.startswith("@SESSION:"):
            new = line.split("|", 1)[0].replace("@SESSION:", "").strip()
    assert new
    snap2 = tmp_path / "rt2.snap"
    save2 = doc_serve.save(new, snap2)
    assert save2.exit_code == 0, redact(save2.stderr)
    dst = canonical_snapshot(snap2.read_text(encoding="utf-8"))
    assert src == dst
    pin = doc_serve.pin_map(new, cue="USR_rt")
    assert pin.exit_code == 0, redact(pin.stderr)
    assert "测例" in pin.stdout
    doc_serve.close(new)
    assert_sid_free(src, dst)


def test_snapshot_multiline_value_breaks_load(doc_serve: ServeProc, tmp_path: Path):
    """Gap: leftover snapshot emit does not escape newlines in field values."""
    sid = _open_ok(doc_serve)
    blob = "Line one.\nLine two."
    mut = doc_serve.mutate(
        sid,
        "CREATE (:USR {id: 'USR_nl', key: 'blob', value: " + gql_str(blob) + ", recycle: ''})\n",
    )
    assert mut.exit_code == 0, redact(mut.stderr)
    snap = tmp_path / "nl.snap"
    save = doc_serve.save(sid, snap)
    assert save.exit_code == 0, redact(save.stderr)
    doc_serve.close(sid)
    load = doc_serve.load_file(snap)
    assert load.exit_code != 0
    joined = "\n".join(err_lines(load.stderr))
    assert "FIELD_COUNT" in joined
    assert_sid_free(redact(load.stderr), redact(load.stdout))


def test_acl_who_denied_scope_and_skipped_lifecycle(doc_serve: ServeProc, tmp_path: Path):
    sid = _open_ok(doc_serve)
    doc_serve.mutate(
        sid,
        "CREATE (:SEC {id: 'SEC_acl', art: 'ART_doc', heading: 'acl', "
        "numbering: '1', parent: '', order: '1', status: 'active', recycle: ''})\n",
    )
    grant = doc_serve.grant(sid, "owner", write_scope="labels=SEC;ids=SEC_acl")
    assert grant.exit_code == 0, redact(grant.stderr)
    bind = doc_serve.acl_bind(sid, "mission-a", "lease-a")
    assert bind.exit_code == 0, redact(bind.stderr)

    who = doc_serve.pin_map(sid, cue="SEC_acl")
    assert who.exit_code != 0
    assert any(e.startswith("@ERR: acl_who|") for e in err_lines(who.stderr))

    denied = doc_serve.pin_map(sid, cue="SEC_acl", caller="intruder")
    assert any(e.startswith("@ERR: acl_denied|") for e in err_lines(denied.stderr))

    ok = doc_serve.pin_map(sid, cue="SEC_acl", caller="owner")
    assert ok.exit_code == 0, redact(ok.stderr)

    mut_who = doc_serve.mutate(sid, "MATCH (n:SEC {id: 'SEC_acl'}) SET n.status = 'x'\n")
    assert any(e.startswith("@ERR: acl_who|") for e in err_lines(mut_who.stderr))

    scope = doc_serve.mutate(
        sid,
        "CREATE (:USR {id: 'USR_nope', key: 'k', value: 'v', recycle: ''})\n",
        caller="owner",
    )
    assert any(e.startswith("@ERR: acl_scope|") for e in err_lines(scope.stderr))

    in_scope = doc_serve.mutate(
        sid,
        "MATCH (n:SEC {id: 'SEC_acl'}) SET n.status = 'ok'\n",
        caller="owner",
    )
    assert in_scope.exit_code == 0, redact(in_scope.stderr)

    exp = doc_serve.export_pin_map(sid, cue="SEC_acl")
    assert any(e.startswith("@ERR: acl_who|") for e in err_lines(exp.stderr))

    snap = tmp_path / "acl.snap"
    save = doc_serve.save(sid, snap)
    assert save.exit_code == 0, redact(save.stderr)

    save_caller = doc_serve.save(sid, tmp_path / "acl2.snap", caller="owner")
    assert save_caller.exit_code != 0
    assert not any(e.startswith("@ERR: acl_") for e in err_lines(save_caller.stderr))

    bind_mut = doc_serve.mutate(
        sid,
        "MATCH (n:SEC {id: 'SEC_acl'}) SET n.status = 'bound'\n",
        caller="owner",
    )
    assert bind_mut.exit_code == 0, redact(bind_mut.stderr)
    assert not any("acl_bind" in e for e in err_lines(bind_mut.stderr))

    closed = doc_serve.close(sid)
    assert closed.exit_code == 0, redact(closed.stderr)


def test_gql_create_set_hop_count_and_max_rows_151(doc_serve: ServeProc):
    sid32 = doc_serve.open_session(map_lines=[ln for ln in schema_prop32().splitlines() if ln])
    props = ", ".join(f"{k}: {gql_str('v' if k != 'id' else 'PRT_32')}" for k in PROP32)
    created = doc_serve.mutate(sid32, f"CREATE (:PRT {{{props}}})\n")
    assert created.exit_code == 0, redact(created.stderr)
    insert = doc_serve.mutate(sid32, "INSERT (:PRT {id: 'PRT_ins', p00: 'x'})\n")
    assert insert.exit_code != 0
    assert err_lines(insert.stderr)
    doc_serve.close(sid32)

    sid = _open_ok(doc_serve)
    doc_serve.mutate(
        sid,
        "CREATE (:SEC {id: 'SEC_hub', art: 'ART_doc', heading: 'hub', "
        "numbering: '0', parent: '', order: '0', status: 'seed', recycle: ''})\n",
    )
    setted = doc_serve.mutate(sid, "MATCH (n:SEC {id: 'SEC_hub'}) SET n.status = 'patched'\n")
    assert setted.exit_code == 0, redact(setted.stderr)
    pin = doc_serve.pin_map(sid, cue="SEC_hub")
    assert "patched" in pin.stdout

    hop = doc_serve.mutate(
        sid,
        "CREATE (:SEC {id: 'SEC_leaf', art: 'ART_doc', heading: 'leaf', "
        "numbering: '1', parent: '', order: '1', status: 'active', recycle: ''})\n"
        "MATCH (a {id: 'SEC_hub'}), (b {id: 'SEC_leaf'})\n"
        "CREATE (a)-[:contains {id: 'E_hop'}]->(b)\n",
    )
    assert hop.exit_code == 0, redact(hop.stderr)
    hop_r = doc_serve.pin_map(sid, cue="SEC_hub", depth=1)
    assert hop_r.exit_code == 0, redact(hop_r.stderr)
    assert "leaf" in hop_r.stdout.lower() or "SEC_leaf" in hop_r.stdout

    count = doc_serve.mutate(sid, "MATCH (n:SEC) RETURN n.status AS status, count(n) AS c\n")
    assert count.exit_code != 0
    joined = "\n".join(err_lines(count.stderr))
    assert "product_gate" in joined or "RETURN" in joined

    star = [
        "CREATE (:SEC {id: 'SEC_star', art: 'ART_doc', heading: 'star', "
        "numbering: '0', parent: '', order: '0', status: 'hub', recycle: ''})"
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
    mid = len(star) // 2
    for chunk in (star[:mid], star[mid:]):
        r = doc_serve.mutate(sid, "\n".join(chunk) + "\n")
        assert r.exit_code == 0, redact(r.stderr)
    lim = doc_serve.pin_map(sid, cue="SEC_star", depth=1, max_rows=151)
    assert lim.exit_code == 0, redact(lim.stderr)
    trunc = [ln for ln in lim.stdout.splitlines() if ln.startswith("## Truncation")]
    assert trunc, lim.stdout[:500]
    assert any("M=151" in ln for ln in trunc)
    doc_serve.close(sid)


def test_churn_two_cycles_returns_live_count(doc_serve: ServeProc):
    base, cap = doc_serve.live_count()
    assert cap == 1024
    for _ in range(2):
        sid = _open_ok(doc_serve)
        replies = doc_serve.populate(sid, 40, text_nodes=2, edges=5)
        assert all(r.exit_code == 0 for r in replies), redact(replies[-1].stderr)
        closed = doc_serve.close(sid)
        assert closed.exit_code == 0, redact(closed.stderr)
    end, _ = doc_serve.live_count()
    assert end == base
