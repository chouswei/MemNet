"""One session per document over serve: helpers + a live loopback serve."""

from __future__ import annotations

from pathlib import Path

import pytest

from doc_gate_lib import (
    CAP_CONTRACT,
    CAP_CONTRACT_NEEDLES,
    DEFAULT_BATCH_LINES,
    HUB_SEC,
    PROP32,
    ServeProc,
    assert_sid_free,
    canonical_snapshot,
    citekeys_schema,
    cpu_model,
    edge_create,
    edge_delete,
    err_lines,
    gql_str,
    make_special_blob,
    max_rows_count_report,
    mutate_byte_cap_report,
    parse_stat_int,
    populate_batches,
    populate_fat_batches,
    populate_fulldoc_batches,
    populate_node_batches,
    redact,
    running_serve,
    schema_prop32,
    sec_create,
    shaped_node_props,
    snapshot_load_cap_report,
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
    assert "|" in joined
    assert "pipe" in joined
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


def test_populate_node_batches_3000_under_1000_lines():
    batches = populate_node_batches(3000, batch_lines=DEFAULT_BATCH_LINES)
    assert len(batches) == 3
    joined = "".join(batches)
    assert joined.count("CREATE (:SEC") == 3000
    assert all(chunk.count("\n") <= DEFAULT_BATCH_LINES for chunk in batches)
    assert_sid_free(joined)


def test_populate_fat_batches_byte_cap():
    batches = populate_fat_batches(40, 8, batch_lines=1000, batch_bytes=1_500_000)
    assert "".join(batches).count("CREATE (:USR") == 8
    assert "".join(batches).count("CREATE (:SEC") == 32
    assert all(len(chunk.encode("utf-8")) <= 1_500_000 for chunk in batches)
    assert all(chunk.count("\n") <= 1000 for chunk in batches)


def test_snapshot_load_not_ingest_budget_in_source():
    report = snapshot_load_cap_report()
    assert report["load_calls_parse_line"] is True
    assert report["load_calls_upsert"] is True
    assert report["load_mentions_ingest_budget"] is False
    assert report["ingest_budget_in_pin_map_ingest"] is True


def test_max_rows_count_report_nodes_and_edges():
    report = max_rows_count_report()
    assert report["default_value"] == 5000
    assert report["row_count_sums_non_law_tags"] is True
    assert report["upsert_edg_counts"] is True
    assert report["counts_nodes_plus_edges"] is True


def test_mutate_byte_cap_report_bug4():
    report = mutate_byte_cap_report()
    assert report["pipe_value_bytes_default"] == 4096
    assert report["pipe_line_bytes_default"] == 32768
    assert report["gql_mutate_checks_value_bytes"] is False
    assert report["gql_mutate_checks_line_bytes"] is False
    assert report["bug4_gql_skips_pipe_caps"] is True


def test_special_blob_has_required_glyphs():
    blob = make_special_blob(16 * 1024, newlines=True, pipes=True)
    assert len(blob.encode("utf-8")) == 16 * 1024
    for needle in ("\\frac", "{", "}", "$", '"', "'", "\n", "|", "测"):
        assert needle in blob


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


def test_e11_3000_node_snapshot_load_not_ingest_budget(doc_serve: ServeProc, tmp_path: Path):
    sid = _open_ok(doc_serve)
    replies = doc_serve.populate_stmts(sid, populate_node_batches(3000))
    assert all(r.exit_code == 0 for r in replies), redact(replies[-1].stderr)
    hk = doc_serve.housekeep_stats(sid)
    assert parse_stat_int(hk.stdout, "rows") == 3000
    assert parse_stat_int(hk.stdout, "edges") == 0
    snap = tmp_path / "e11.snap"
    save = doc_serve.save(sid, snap)
    assert save.exit_code == 0, redact(save.stderr)
    doc_serve.close(sid)
    load = doc_serve.load_file(snap)
    assert load.exit_code == 0, redact(load.stderr)
    assert not any("ingest_budget" in e for e in err_lines(load.stderr))
    new = None
    for line in load.stdout.splitlines():
        if line.startswith("@SESSION:"):
            new = line.split("|", 1)[0].replace("@SESSION:", "").strip()
    assert new
    hk2 = doc_serve.housekeep_stats(new)
    assert parse_stat_int(hk2.stdout, "rows") == 3000
    doc_serve.close(new)
    assert_sid_free(redact(load.stdout), redact(load.stderr))


def test_e12_max_rows_counts_nodes_and_edges(tmp_path: Path):
    with running_serve(tmp_path, extra_env={"MEMNET_MAX_ROWS": "4"}) as svc:
        sid = _open_ok(svc)
        n3 = svc.mutate(
            sid,
            "CREATE (:SEC {id: 'SEC_a', art: 'ART_doc', heading: 'a', numbering: '1', "
            "parent: '', order: '1', status: 'active', recycle: ''})\n"
            "CREATE (:SEC {id: 'SEC_b', art: 'ART_doc', heading: 'b', numbering: '2', "
            "parent: '', order: '2', status: 'active', recycle: ''})\n"
            "CREATE (:SEC {id: 'SEC_c', art: 'ART_doc', heading: 'c', numbering: '3', "
            "parent: '', order: '3', status: 'active', recycle: ''})\n",
        )
        assert n3.exit_code == 0, redact(n3.stderr)
        e1 = svc.mutate(
            sid,
            "MATCH (a {id: 'SEC_a'}), (b {id: 'SEC_b'})\n"
            "CREATE (a)-[:contains {id: 'E_ab'}]->(b)\n",
        )
        assert e1.exit_code == 0, redact(e1.stderr)
        hk = svc.housekeep_stats(sid)
        assert parse_stat_int(hk.stdout, "rows") == 4
        assert parse_stat_int(hk.stdout, "edges") == 1
        e2 = svc.mutate(
            sid,
            "MATCH (a {id: 'SEC_a'}), (b {id: 'SEC_c'})\n"
            "CREATE (a)-[:contains {id: 'E_ac'}]->(b)\n",
        )
        assert e2.exit_code != 0
        joined = "\n".join(err_lines(e2.stderr))
        assert "limit_exceeded" in joined
        assert "rows" in joined
        patch = svc.mutate(sid, "MATCH (n:SEC {id: 'SEC_a'}) SET n.status = 'still'\n")
        assert patch.exit_code == 0, redact(patch.stderr)
        svc.close(sid)


def test_e13_16kib_ram_roundtrip_snapshot_refused(doc_serve: ServeProc, tmp_path: Path):
    blob = make_special_blob(16 * 1024, newlines=True, pipes=True)
    sid = _open_ok(doc_serve)
    create = doc_serve.mutate(
        sid,
        "CREATE (:USR {id: 'USR_big', key: 'blob', value: " + gql_str(blob) + ", recycle: ''})\n",
    )
    assert create.exit_code == 0, redact(create.stderr)
    setted = doc_serve.mutate(
        sid,
        "MATCH (n:USR {id: 'USR_big'}) SET n.value = " + gql_str(blob) + "\n",
    )
    assert setted.exit_code == 0, redact(setted.stderr)
    pin = doc_serve.pin_map(sid, cue="USR_big")
    assert pin.exit_code == 0, redact(pin.stderr)
    props = shaped_node_props(pin.stdout)
    assert props is not None
    assert props.get("value") == blob
    snap = tmp_path / "e13.snap"
    save = doc_serve.save(sid, snap)
    assert save.exit_code == 0, redact(save.stderr)
    doc_serve.close(sid)
    load = doc_serve.load_file(snap)
    assert load.exit_code != 0
    joined = "\n".join(err_lines(load.stderr))
    assert "FIELD_COUNT" in joined or "value_bytes" in joined or "newline_in_value" in joined
    assert "ingest_budget" not in joined

    sid2 = _open_ok(doc_serve)
    plain = make_special_blob(16 * 1024, newlines=False, pipes=False)
    doc_serve.mutate(
        sid2,
        "CREATE (:USR {id: 'USR_p', key: 'blob', value: " + gql_str(plain) + ", recycle: ''})\n",
    )
    snap2 = tmp_path / "e13p.snap"
    doc_serve.save(sid2, snap2)
    doc_serve.close(sid2)
    load2 = doc_serve.load_file(snap2)
    assert load2.exit_code != 0
    assert "value_bytes" in "\n".join(err_lines(load2.stderr))


def test_e14_list_store_no_in_membership(doc_serve: ServeProc):
    sid = doc_serve.open_session(map_lines=[ln for ln in citekeys_schema().splitlines() if ln])
    create = doc_serve.mutate(
        sid,
        "CREATE (:USR {id: 'USR_cite', key: 'paper', value: 'v', "
        "citeKeys: ['k', 'other'], recycle: ''})\n"
        "CREATE (:USR {id: 'USR_miss', key: 'other', value: 'v', "
        "citeKeys: ['x'], recycle: ''})\n",
    )
    assert create.exit_code == 0, redact(create.stderr)
    pin = doc_serve.pin_map(sid, cue="USR_cite")
    props = shaped_node_props(pin.stdout)
    assert props is not None
    assert props.get("citeKeys") == ["k", "other"]
    loc = doc_serve.pin_map(sid, kind="USR", locator='citeKeys=["k","other"]')
    assert loc.exit_code == 0, redact(loc.stderr)
    in_mut = doc_serve.mutate(
        sid,
        "MATCH (p:USR) WHERE 'k' IN p.citeKeys SET p.key = 'hit'\n",
    )
    after = shaped_node_props(doc_serve.pin_map(sid, cue="USR_cite").stdout) or {}
    miss = shaped_node_props(doc_serve.pin_map(sid, cue="USR_miss").stdout) or {}
    membership = in_mut.exit_code == 0 and after.get("key") == "hit" and miss.get("key") != "hit"
    assert membership is False
    leftover = doc_serve.read_list(sid, tag="USR", where="citeKeys=*k*")
    assert leftover.exit_code == 0, redact(leftover.stderr)
    doc_serve.close(sid)


def test_fulldoc_batches_shape_and_line_cap():
    batches = populate_fulldoc_batches(40, 8)
    joined = "".join(batches)
    assert joined.count("CREATE (:SEC") == 32
    assert joined.count("CREATE (:USR") == 8
    assert joined.count("-[:inSection") == 8
    assert joined.count("-[:cites") == 32
    assert joined.count("-[:refersTo") == 8
    assert "order:" in joined
    assert "-[:order" not in joined
    assert all(chunk.count("\n") <= DEFAULT_BATCH_LINES for chunk in batches)
    assert_sid_free(joined)


def test_fulldoc_3000_edge_counts_without_building_fat_text():
    from doc_gate_lib import fulldoc_edge_stmts

    stmts = fulldoc_edge_stmts()
    assert len(stmts) == 4500
    assert sum(1 for s in stmts if ":inSection" in s) == 1500
    assert sum(1 for s in stmts if ":cites" in s) == 1500
    assert sum(1 for s in stmts if ":refersTo" in s) == 1500
    assert all("\n" not in s for s in stmts)


def test_e12_fulldoc_scaled_write_read_load(tmp_path: Path):
    """Scaled fulldoc: 40 nodes + edges at max_rows=50, then overflow load."""
    n_nodes, n_fat = 40, 8
    with running_serve(tmp_path / "low", extra_env={"MEMNET_MAX_ROWS": "50"}) as svc:
        sid = svc.open_session()
        nodes = populate_fulldoc_batches(n_nodes, n_fat, nodes_only=True)
        replies = svc.populate_stmts(sid, nodes)
        assert all(r.exit_code == 0 for r in replies), redact(replies[-1].stderr)
        fit = populate_fulldoc_batches(n_nodes, n_fat, max_edges=10)
        # fit includes nodes again — only take edge batches after node batches
        node_n = len(nodes)
        edge_fit = fit[node_n:]
        er = svc.populate_stmts(sid, edge_fit, allow_new_relation=True)
        assert all(r.exit_code == 0 for r in er), redact(er[-1].stderr)
        hk = svc.housekeep_stats(sid)
        assert parse_stat_int(hk.stdout, "rows") == 50
        extra = svc.mutate(
            sid,
            edge_create("cites", "E_overflow", "SEC_0002", "SEC_0003") + "\n",
            allow_new_relation=True,
        )
        assert extra.exit_code != 0
        joined = "\n".join(err_lines(extra.stderr))
        assert "limit_exceeded" in joined
        assert "rows" in joined
        pin = svc.pin_map(sid, cue=HUB_SEC, depth=1, max_rows=5)
        assert pin.exit_code == 0, redact(pin.stderr)
        assert any(ln.startswith("## Truncation") for ln in pin.stdout.splitlines())
        snap = tmp_path / "partial.snap"
        assert svc.save(sid, snap).exit_code == 0
        svc.close(sid)
        load = svc.load_file(snap)
        assert load.exit_code == 0, redact(load.stderr)
        new = None
        for line in load.stdout.splitlines():
            if line.startswith("@SESSION:"):
                new = line.split("|", 1)[0].replace("@SESSION:", "").strip()
        assert new
        svc.close(new)

    with running_serve(tmp_path / "high", extra_env={"MEMNET_MAX_ROWS": "200"}) as svc2:
        sid2 = svc2.open_session()
        full = svc2.populate_stmts(
            sid2, populate_fulldoc_batches(n_nodes, n_fat), allow_new_relation=True
        )
        assert all(r.exit_code == 0 for r in full), redact(full[-1].stderr)
        hk2 = svc2.housekeep_stats(sid2)
        assert parse_stat_int(hk2.stdout, "rows") == 88  # 40 nodes + 48 edges
        snap2 = tmp_path / "full.snap"
        assert svc2.save(sid2, snap2).exit_code == 0
        svc2.close(sid2)
        load2 = svc2.load_file(snap2)
        assert load2.exit_code == 0, redact(load2.stderr)
        assert not any("ingest_budget" in e for e in err_lines(load2.stderr))
        new2 = None
        for line in load2.stdout.splitlines():
            if line.startswith("@SESSION:"):
                new2 = line.split("|", 1)[0].replace("@SESSION:", "").strip()
        assert new2
        svc2.close(new2)

    with running_serve(tmp_path / "reload-low", extra_env={"MEMNET_MAX_ROWS": "50"}) as svc3:
        boom = svc3.load_file(tmp_path / "full.snap")
        assert boom.exit_code != 0
        joined = "\n".join(err_lines(boom.stderr))
        assert "ingest_budget" not in joined
        assert "limit_exceeded" in joined
        assert "rows" in joined


def test_e16_delete_not_refused_while_referenced(doc_serve: ServeProc):
    sid = _open_ok(doc_serve)
    setup = doc_serve.mutate(
        sid,
        sec_create(1)
        + "\n"
        + sec_create(2)
        + "\n"
        + sec_create(3)
        + "\n"
        + edge_create("contains", "E_ref1", "SEC_0001", "SEC_0002")
        + "\n"
        + edge_create("contains", "E_drop", "SEC_0001", "SEC_0003")
        + "\n",
    )
    assert setup.exit_code == 0, redact(setup.stderr)
    pin = doc_serve.pin_map(sid, cue="SEC_0002", depth=1, max_rows=20)
    assert pin.exit_code == 0, redact(pin.stderr)
    assert "contains" in pin.stdout
    documented = doc_serve.mutate(sid, "MATCH ()-[r {id: 'E_drop'}]-() DELETE r\n")
    assert documented.exit_code != 0
    joined_doc = "\n".join(err_lines(documented.stderr))
    assert "not_found" in joined_doc
    assert "DELETE matched no element" in joined_doc
    gone = doc_serve.mutate(sid, "MATCH (n:SEC {id: 'SEC_0002'}) DETACH DELETE n\n")
    assert gone.exit_code == 0, redact(gone.stderr)
    assert not any(e.startswith("@ERR:") for e in err_lines(gone.stderr))
    hk = doc_serve.housekeep_stats(sid)
    assert parse_stat_int(hk.stdout, "dangling") == 1
    batch = doc_serve.mutate(
        sid,
        "MATCH (n:SEC {id: 'SEC_0001'}) SET n.status = 'edited'\n"
        + edge_delete("E_drop")
        + "\n"
        + edge_create("contains", "E_new_a", "SEC_0001", "SEC_0003")
        + "\n"
        + edge_create("contains", "E_new_b", "SEC_0001", "SEC_0003")
        + "\n",
    )
    assert batch.exit_code == 0, redact(batch.stderr)
    pin1 = doc_serve.pin_map(sid, cue="SEC_0001")
    assert "edited" in pin1.stdout
    assert cpu_model()
    doc_serve.close(sid)
