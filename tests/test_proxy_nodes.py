"""One-hop PROXY nodes (MN-REQ-15): write shape, reads unchanged, query follow, housekeep.

Sessions are opened in-process; target session ids are the ids these tests just
opened, or synthetic strings (``sess_target``) where no live session is needed.
"""

from __future__ import annotations

import pytest

from memnet.cli import app
from memnet.in_process_engine import run_argv
from memnet.registry import get_entry
from memnet.session import close_session, open_session
from memnet.snapshot import load_snapshot, write_snapshot
from memnet.tag_map import load_map_from_lines

MAP = ["SCHEMA TSK ; fields=id goal status"]


@pytest.fixture
def two(memnet_temp):
    a = open_session(map_lines=MAP, ttl_minutes=60)
    b = open_session(map_lines=MAP, ttl_minutes=60)
    yield a, b
    for ss in (a, b):
        try:
            close_session(ss.session_id)
        except Exception:
            pass


def _run(argv: list[str], stdin: str | None = None) -> dict:
    return run_argv(argv, stdin=stdin)


def _mutate(sid: str, text: str) -> dict:
    return _run(["mutate", "--stdin", "--session", sid], stdin=text + "\n")


def _ok(got: dict) -> dict:
    assert got["exit_code"] == 0, got
    return got


def _proxy(sid: str, pid: str, target_session: str, target: str, backend: str = "") -> None:
    extra = f", target_backend: '{backend}'" if backend else ""
    _ok(
        _mutate(
            sid,
            f"CREATE (:PROXY {{id: '{pid}', target_session: '{target_session}', "
            f"target: '{target}'{extra}}})",
        )
    )


def _follow(sid: str, pid: str, *extra: str) -> dict:
    return _run(["query", "follow", "--id", pid, "--session", sid, *extra])


def _proxies(sid: str) -> list:
    return list(get_entry(sid).store.list_records("PROXY"))


# 1. write + existing reads show the PROXY with its target fields, no hop


def test_write_proxy_and_existing_reads_show_it_without_hop(two):
    a, b = two
    _ok(_mutate(b.session_id, "CREATE (:TSK {id: 'T1', goal: 'far goal', status: 'open'})"))
    _proxy(a.session_id, "P1", b.session_id, "T1", backend="pi-b")
    pin = _ok(_run(["query", "pin-map", "--kind", "PROXY", "--session", a.session_id]))
    assert "(:PROXY {" in pin["stdout"]
    assert f"target_session: '{b.session_id}'" in pin["stdout"]
    assert "target: 'T1'" in pin["stdout"] and "target_backend: 'pi-b'" in pin["stdout"]
    assert "far goal" not in pin["stdout"], "pin_map must not follow a PROXY"
    found = _ok(
        _run(["query", "find", "--kind", "PROXY", "--limit", "5", "--session", a.session_id])
    )
    assert "target: 'T1'" in found["stdout"] and "far goal" not in found["stdout"]
    walk = _run(["query", "walk", "--anchor", "P1", "--session", a.session_id])
    assert "far goal" not in walk["stdout"]


def test_empty_target_backend_is_omitted_like_other_empty_fields(two):
    a, _b = two
    _proxy(a.session_id, "P1", "sess_target", "T1")
    pin = _ok(_run(["query", "pin-map", "--kind", "PROXY", "--session", a.session_id]))
    assert "target_backend" not in pin["stdout"]
    assert "target_session: 'sess_target'" in pin["stdout"]


def test_proxy_is_a_fixed_tag_that_cannot_be_redefined(memnet_temp):
    from memnet.config import ORPHAN_EXEMPT_TAGS, RESERVED_TAGS
    from memnet.exceptions import MemNetError
    from memnet.fixed_tags import FIXED_TAGS

    assert FIXED_TAGS["PROXY"].fields == ["id", "target_session", "target", "target_backend"]
    assert FIXED_TAGS["PROXY"].kind == "node"
    assert "PROXY" not in RESERVED_TAGS
    assert "PROXY" in ORPHAN_EXEMPT_TAGS
    with pytest.raises(MemNetError) as exc:
        load_map_from_lines(["SCHEMA PROXY ; fields=id x"])
    assert exc.value.code == "user_proxy_tag"
    assert "PROXYH" in (exc.value.example or "")


def test_proxy_can_be_an_edge_end_inside_its_session(two):
    a, _b = two
    _ok(_mutate(a.session_id, "CREATE (:TSK {id: 'T0', goal: 'here', status: 'open'})"))
    _proxy(a.session_id, "P1", "sess_target", "X1")
    _ok(
        _run(
            ["mutate", "--stdin", "--allow-new-relation", "--session", a.session_id],
            stdin="MATCH (t {id: 'T0'}), (p {id: 'P1'}) CREATE (t)-[:dependsOn]->(p)\n",
        )
    )
    pin = _ok(_run(["query", "pin-map", "--cue", "T0", "--session", a.session_id]))
    assert "-[:dependsOn]->(:PROXY" in pin["stdout"]


# 2. / 3. follow: another live session, and the same session


def test_follow_returns_target_node_in_another_live_session(two):
    a, b = two
    _ok(_mutate(b.session_id, "CREATE (:TSK {id: 'T1', goal: 'far goal', status: 'open'})"))
    _proxy(a.session_id, "P1", b.session_id, "T1")
    got = _ok(_follow(a.session_id, "P1"))
    lines = got["stdout"].splitlines()
    assert lines[0] == "@STAT: follow|ok"
    assert lines[1].startswith("(:TSK {") and "goal: 'far goal'" in lines[1]
    assert "_el" not in got["stdout"], "no raw hid on the product surface"


def test_follow_target_in_same_session(two):
    a, _b = two
    _ok(_mutate(a.session_id, "CREATE (:TSK {id: 'T2', goal: 'near goal', status: 'open'})"))
    _proxy(a.session_id, "P2", a.session_id, "T2")
    got = _ok(_follow(a.session_id, "P2"))
    assert got["stdout"].splitlines()[0] == "@STAT: follow|ok"
    assert "near goal" in got["stdout"]


# 4. / 5. not reachable vs dangling


def test_follow_target_session_missing_is_not_reachable(two):
    a, _b = two
    _proxy(a.session_id, "P1", "sess_target", "T1", backend="pi-b")
    got = _ok(_follow(a.session_id, "P1"))
    lines = got["stdout"].splitlines()
    assert lines[0].startswith("@STAT: follow|not_reachable")
    assert "target not reachable from here" in lines[0]
    assert "@FOLLOW: sess_target|T1|pi-b" in lines


def test_follow_target_session_closed_is_not_reachable(two):
    a, b = two
    _ok(_mutate(b.session_id, "CREATE (:TSK {id: 'T1', goal: 'g', status: 'open'})"))
    _proxy(a.session_id, "P1", b.session_id, "T1")
    close_session(b.session_id)
    got = _ok(_follow(a.session_id, "P1"))
    assert got["stdout"].startswith("@STAT: follow|not_reachable")


def test_follow_target_node_gone_is_dangling(two):
    a, b = two
    _proxy(a.session_id, "P1", b.session_id, "GONE")
    got = _ok(_follow(a.session_id, "P1"))
    assert got["stdout"].splitlines() == ["@STAT: follow|dangling|reason=target_missing"]


# 6. not a PROXY / not found


def test_follow_non_proxy_is_not_proxy(two):
    a, _b = two
    _ok(_mutate(a.session_id, "CREATE (:TSK {id: 'T1', goal: 'g', status: 'open'})"))
    got = _follow(a.session_id, "T1")
    assert got["exit_code"] != 0
    assert "@ERR: not_proxy|" in got["stderr"]


def test_follow_unknown_id_is_not_found(two):
    a, _b = two
    got = _follow(a.session_id, "NOPE")
    assert got["exit_code"] != 0 and "@ERR: not_found|" in got["stderr"]


def test_follow_id_less_proxy_by_handle(two):
    """pin_map hides nicknames; a handle is how an id-less PROXY is followed."""
    from memnet.typed_walk import handle_for

    a, b = two
    _ok(_mutate(b.session_id, "CREATE (:TSK {id: 'T1', goal: 'via handle', status: 'open'})"))
    _ok(
        _mutate(
            a.session_id,
            f"CREATE (:PROXY {{target_session: '{b.session_id}', target: 'T1'}})",
        )
    )
    (rec,) = _proxies(a.session_id)
    assert not rec.fields.get("id")
    handle = handle_for(a.session_id, rec, "node")
    got = _ok(_follow(a.session_id, handle))
    assert "via handle" in got["stdout"]


def test_follow_nickname_cue_conflict_is_refused(two):
    a, _b = two
    _ok(_mutate(a.session_id, "CREATE (:TSK {id: 'P1', goal: 'same nick', status: 'open'})"))
    _proxy(a.session_id, "P1", "sess_target", "T1")
    got = _follow(a.session_id, "P1")
    assert got["exit_code"] != 0 and "@ERR: cue_conflict|" in got["stderr"]


def test_follow_needs_exactly_one_of_id_or_resolved_id(two):
    a, _b = two
    got = _run(["query", "follow", "--session", a.session_id])
    assert got["exit_code"] != 0 and "@ERR: no_anchor|" in got["stderr"]


# 7. write shape


@pytest.mark.parametrize(
    "props",
    [
        "{target: 'T1'}",
        "{target_session: 's1'}",
        "{target_session: '  ', target: 'T1'}",
        "{target_session: 's1', target: ''}",
        "{target_session: 's 1', target: 'T1'}",
        "{target_session: 's1', target: 'T1', target_backend: 'not valid'}",
    ],
)
def test_write_without_pointer_fields_is_proxy_shape_and_writes_nothing(two, props):
    a, _b = two
    got = _mutate(a.session_id, f"CREATE (:PROXY {props})")
    assert got["exit_code"] != 0 and "@ERR: proxy_shape|" in got["stderr"], got
    assert _proxies(a.session_id) == []


def test_write_does_not_require_target_to_exist(two):
    a, _b = two
    _proxy(a.session_id, "P1", "sess_nowhere", "no_such_node")
    assert len(_proxies(a.session_id)) == 1


def test_set_retargets_and_rechecks_shape(two):
    a, b = two
    _ok(_mutate(b.session_id, "CREATE (:TSK {id: 'T9', goal: 'retarget', status: 'open'})"))
    _proxy(a.session_id, "P1", "sess_target", "T1")
    _ok(
        _mutate(
            a.session_id,
            f"MATCH (p:PROXY {{id: 'P1'}}) SET p.target_session = '{b.session_id}', "
            "p.target = 'T9'",
        )
    )
    assert "retarget" in _ok(_follow(a.session_id, "P1"))["stdout"]
    bad = _mutate(a.session_id, "MATCH (p:PROXY {id: 'P1'}) SET p.target = ''")
    assert bad["exit_code"] != 0 and "@ERR: proxy_shape|" in bad["stderr"]
    (rec,) = _proxies(a.session_id)
    assert rec.fields["target"] == "T9", "a refused SET leaves the row as it was"


def test_leftover_pipe_add_checks_shape(two):
    a, _b = two
    bad = _run(["add", "--stdin", "--session", a.session_id], stdin="@PROXY: P1||T1|\n")
    assert bad["exit_code"] != 0 and "proxy_shape" in bad["stderr"]
    assert _proxies(a.session_id) == []
    _ok(_run(["add", "--stdin", "--session", a.session_id], stdin="@PROXY: P1|s1|T1|\n"))
    assert len(_proxies(a.session_id)) == 1


def test_snapshot_load_refuses_bad_proxy_row(two, tmp_path):
    a, _b = two
    _proxy(a.session_id, "P1", "s1", "T1")
    path = tmp_path / "a.snap"
    write_snapshot(a, str(path))
    text = path.read_text(encoding="utf-8")
    assert "@PROXY: P1|s1|T1|" in text
    path.write_text(text.replace("@PROXY: P1|s1|T1|", "@PROXY: P1||T1|"), encoding="utf-8")
    got = _run(["session", "load", "--file", str(path)])
    assert got["exit_code"] != 0 and "proxy_shape" in got["stderr"]


# 8. ACL on both sessions


def test_acl_denied_on_target_hides_target(two):
    a, b = two
    _ok(_mutate(b.session_id, "CREATE (:TSK {id: 'T1', goal: 'secret goal', status: 'open'})"))
    _proxy(a.session_id, "P1", b.session_id, "T1")
    _proxy(a.session_id, "P2", b.session_id, "GONE")
    a.grant_caller("alice")
    b.grant_caller("bob")
    expires = get_entry(b.session_id).meta.expires_at
    touch = get_entry(b.session_id).touch_seq
    for pid in ("P1", "P2"):
        got = _follow(a.session_id, pid, "--caller", "alice")
        assert got["exit_code"] != 0
        assert "@ERR: acl_" in got["stderr"]
        assert "secret" not in got["stdout"] + got["stderr"]
        assert "follow|" not in got["stdout"], "a denial says nothing about the target"
    entry = get_entry(b.session_id)
    assert entry.meta.expires_at == expires
    assert entry.touch_seq == touch
    b.grant_caller("alice")
    assert "secret goal" in _ok(_follow(a.session_id, "P1", "--caller", "alice"))["stdout"]


def test_acl_denied_on_source(two):
    a, b = two
    _ok(_mutate(b.session_id, "CREATE (:TSK {id: 'T1', goal: 'g', status: 'open'})"))
    _proxy(a.session_id, "P1", b.session_id, "T1")
    a.grant_caller("alice")
    got = _follow(a.session_id, "P1", "--caller", "mallory")
    assert got["exit_code"] != 0 and "@ERR: acl_" in got["stderr"]


def test_resolved_id_form_reads_this_session_only(two):
    a, _b = two
    _ok(_mutate(a.session_id, "CREATE (:TSK {id: 'T1', goal: 'local', status: 'open'})"))
    got = _ok(_run(["query", "follow", "--resolved-id", "T1", "--session", a.session_id]))
    assert got["stdout"].splitlines()[0] == "@STAT: follow|ok" and "local" in got["stdout"]
    miss = _ok(_run(["query", "follow", "--resolved-id", "ZZ", "--session", a.session_id]))
    assert miss["stdout"].strip() == "@STAT: follow|dangling|reason=target_missing"


# 10. housekeep lists, counts, never deletes


def test_housekeep_dangling_lists_proxy_with_reason_and_prune_keeps_it(two):
    a, b = two
    _ok(_mutate(b.session_id, "CREATE (:TSK {id: 'T1', goal: 'g', status: 'open'})"))
    _proxy(a.session_id, "P_OK", b.session_id, "T1")
    _proxy(a.session_id, "P_GONE", b.session_id, "GONE")
    _proxy(a.session_id, "P_FAR", "sess_target", "T1")
    stats_before = _ok(_run(["housekeep", "stats", "--session", a.session_id]))["stdout"]
    assert "@STAT: dangling|0|-" in stats_before
    assert "@STAT: dangling_proxies|2|-" in stats_before
    lines = _ok(_run(["housekeep", "dangling", "--session", a.session_id]))["stdout"].splitlines()
    assert lines == [
        "@PROXY: P_FAR|sess_target|T1|",
        "@STAT: dangling_proxy|reason=not_reachable",
        f"@PROXY: P_GONE|{b.session_id}|GONE|",
        "@STAT: dangling_proxy|reason=target_missing",
    ]
    _ok(_run(["housekeep", "prune", "dangling", "--apply", "--session", a.session_id]))
    assert {r.id for r in _proxies(a.session_id)} == {"P_OK", "P_GONE", "P_FAR"}
    _ok(_mutate(b.session_id, "CREATE (:TSK {id: 'GONE', goal: 'back', status: 'open'})"))
    stats_after = _ok(_run(["housekeep", "stats", "--session", a.session_id]))["stdout"]
    assert "@STAT: dangling_proxies|1|-" in stats_after


def test_housekeep_acl_protected_target_is_not_reachable(two):
    a, b = two
    _ok(_mutate(b.session_id, "CREATE (:TSK {id: 'SECRET', goal: 'hidden', status: 'open'})"))
    _proxy(a.session_id, "Pyes", b.session_id, "SECRET")
    _proxy(a.session_id, "Pno", b.session_id, "GONE")
    a.grant_caller("alice")
    b.grant_caller("bob")
    dangling = _ok(_run(["housekeep", "dangling", "--caller", "alice", "--session", a.session_id]))[
        "stdout"
    ]
    assert "target_missing" not in dangling
    assert "hidden" not in dangling
    assert dangling.count("reason=not_reachable") == 2
    assert "Pyes" in dangling and "Pno" in dangling
    stats = _ok(_run(["housekeep", "stats", "--caller", "alice", "--session", a.session_id]))[
        "stdout"
    ]
    assert "@STAT: dangling_proxies|2|-" in stats
    for pid in ("Pyes", "Pno"):
        got = _follow(a.session_id, pid, "--caller", "alice")
        assert got["exit_code"] != 0 and "@ERR: acl_" in got["stderr"]
        assert "follow|" not in got["stdout"]
    b.grant_caller("alice")
    after = _ok(_run(["housekeep", "dangling", "--caller", "alice", "--session", a.session_id]))[
        "stdout"
    ]
    assert "Pyes" not in after
    assert "Pno" in after and "reason=target_missing" in after
    assert "not_reachable" not in after


def test_housekeep_does_not_touch_the_target_session(two):
    a, b = two
    _proxy(a.session_id, "P1", b.session_id, "GONE")
    before = (get_entry(b.session_id).meta.modified_at, get_entry(b.session_id).touch_seq)
    expires = get_entry(b.session_id).meta.expires_at
    _ok(_run(["housekeep", "dangling", "--session", a.session_id]))
    _ok(_run(["housekeep", "stats", "--session", a.session_id]))
    entry = get_entry(b.session_id)
    assert (entry.meta.modified_at, entry.touch_seq) == before
    assert entry.meta.expires_at == expires


def test_edgeless_proxy_survives_prune_orphans_non_proxy_orphan_is_pruned(two):
    a, _b = two
    _proxy(a.session_id, "P1", "sess_target", "T1")
    _ok(_mutate(a.session_id, "CREATE (:TSK {id: 'LONE', goal: 'orphan tsk', status: 'open'})"))
    listed = _ok(_run(["housekeep", "orphans", "--session", a.session_id]))["stdout"]
    dry = _ok(_run(["housekeep", "prune", "orphans", "--session", a.session_id]))
    assert "LONE" in listed and "P1" not in listed
    assert "LONE" in dry["stdout"] and "P1" not in dry["stdout"]
    assert "would-delete 1" in dry["stderr"]
    stats = _ok(_run(["housekeep", "stats", "--session", a.session_id]))["stdout"]
    assert "@STAT: orphans|1|-" in stats
    _ok(_run(["housekeep", "prune", "orphans", "--apply", "--session", a.session_id]))
    store = get_entry(a.session_id).store
    assert [r.id for r in store.list_records("PROXY")] == ["P1"]
    assert list(store.list_records("TSK")) == []


def test_edgeless_proxy_survives_prune_stale_non_proxy_orphan_is_pruned(two):
    a, _b = two
    _proxy(a.session_id, "P1", "sess_target", "T1")
    _ok(_mutate(a.session_id, "CREATE (:TSK {id: 'LONE', goal: 'orphan tsk', status: 'open'})"))
    listed = _ok(_run(["housekeep", "stale", "--session", a.session_id]))["stdout"]
    dry = _ok(_run(["housekeep", "prune", "stale", "--session", a.session_id]))
    assert "LONE" in listed and "P1" not in listed
    assert "LONE" in dry["stdout"] and "P1" not in dry["stdout"]
    assert "would-delete 1" in dry["stderr"]
    _ok(_run(["housekeep", "prune", "stale", "--apply", "--session", a.session_id]))
    store = get_entry(a.session_id).store
    assert [r.id for r in store.list_records("PROXY")] == ["P1"]
    assert list(store.list_records("TSK")) == []


def test_prune_dangling_with_a_dangling_edge_deletes_the_edge_not_the_proxy(two):
    a, _b = two
    _proxy(a.session_id, "P1", "sess_target", "T1")
    _ok(
        _run(
            ["add", "--stdin", "--allow-new-relation", "--session", a.session_id],
            stdin="@EDG: E9|P1|links|NOPE|||persistent\n",
        )
    )
    dangling = _ok(_run(["housekeep", "dangling", "--session", a.session_id]))["stdout"]
    assert dangling.splitlines()[0].startswith("@EDG: E9|")
    _ok(_run(["housekeep", "prune", "dangling", "--apply", "--session", a.session_id]))
    store = get_entry(a.session_id).store
    assert [r.id for r in store.list_records("PROXY")] == ["P1"]
    assert list(store.list_records("EDG")) == []


# 11. upgrade: snapshot unchanged without PROXY; PROXY survives save/load; old map refuses


def test_snapshot_without_proxy_has_no_proxy_schema_line(two, tmp_path):
    a, _b = two
    _ok(_mutate(a.session_id, "CREATE (:TSK {id: 'T1', goal: 'g', status: 'open'})"))
    path = tmp_path / "a.snap"
    write_snapshot(a, str(path))
    text = path.read_text(encoding="utf-8")
    assert "PROXY" not in text
    assert "SCHEMA LAW ; fields=id name cycle mechanism constraint" in text


def test_proxy_session_survives_save_and_load_and_follow_still_works(two, tmp_path):
    a, b = two
    _ok(_mutate(b.session_id, "CREATE (:TSK {id: 'T1', goal: 'after load', status: 'open'})"))
    _proxy(a.session_id, "P1", b.session_id, "T1", backend="pi-b")
    path = tmp_path / "a.snap"
    write_snapshot(a, str(path))
    text = path.read_text(encoding="utf-8")
    assert "SCHEMA PROXY" not in text, "the loader merges the fixed tag back in"
    loaded = load_snapshot(str(path))
    (rec,) = list(loaded.store.list_records("PROXY"))
    assert rec.fields == {
        "id": "P1",
        "target_session": b.session_id,
        "target": "T1",
        "target_backend": "pi-b",
    }
    assert "after load" in _ok(_follow(loaded.session_id, "P1"))["stdout"]


def _inject_user_proxy(text: str, fields: list[str], row: str) -> str:
    """A 0.20.8 snapshot that declared PROXY as a user tag (SCHEMA line + row)."""
    schema = f"SCHEMA PROXY ; fields={' '.join(fields)}"
    needle = "SCHEMA TSK ; fields=id goal status\n"
    assert needle in text
    text = text.replace(needle, needle + schema + "\n", 1)
    return text.replace("# records\n", f"# records\n@PROXY: {row}\n", 1)


def _assert_no_remapped_user_proxy() -> None:
    from memnet.registry import list_entries

    for entry in list_entries():
        for rec in entry.store._by_hid.values():
            if rec.tag != "PROXY":
                continue
            assert rec.fields.get("target_session") != "squid01"
            assert rec.fields.get("target") != "3128"


@pytest.mark.parametrize(
    "fields,row",
    [
        (["id", "host"], "P1|squid01"),
        (["id", "host", "port", "proto"], "P1|squid01|3128|http"),
    ],
    ids=["two-field", "four-field"],
)
def test_session_load_refuses_user_proxy_tag_and_leaves_file(two, tmp_path, fields, row):
    a, _b = two
    _ok(_mutate(a.session_id, "CREATE (:TSK {id: 'T1', goal: 'g', status: 'open'})"))
    path = tmp_path / "user-proxy.snap"
    write_snapshot(a, str(path))
    close_session(a.session_id)
    before = _inject_user_proxy(path.read_text(encoding="utf-8"), fields, row)
    path.write_text(before, encoding="utf-8")
    raw = path.read_bytes()
    got = _run(["session", "load", "--file", str(path)])
    assert got["exit_code"] != 0
    assert "@ERR: user_proxy_tag|" in got["stderr"]
    assert path.read_bytes() == raw
    assert get_entry(a.session_id) is None
    _assert_no_remapped_user_proxy()


def test_map_file_declaring_proxy_is_refused_user_proxy_tag(memnet_temp, tmp_path):
    path = tmp_path / "user-proxy.map"
    path.write_text(
        "SCHEMA TSK ; fields=id goal status\nSCHEMA PROXY ; fields=id host\n",
        encoding="utf-8",
    )
    got = _run(["session", "open", "--map-file", str(path)])
    assert got["exit_code"] != 0
    assert "@ERR: user_proxy_tag|" in got["stderr"]
    assert "PROXYH" in got["stderr"]


@pytest.mark.parametrize(
    "fields,row",
    [
        (["id", "host"], "P1|squid01"),
        (["id", "host", "port", "proto"], "P1|squid01|3128|http"),
    ],
    ids=["two-field", "four-field"],
)
def test_upgrade_restore_refuses_user_proxy_tag_and_drops_half_live(
    memnet_temp, monkeypatch, tmp_path, fields, row
):
    import hashlib
    import json

    from memnet.session import reset_registry
    from memnet.upgrade import MANIFEST_NAME, prepare_upgrade, reset_drain_gate, restore_manifest

    token = "test-admin-token"
    monkeypatch.setenv("MEMNET_ADMIN_TOKEN", token)
    a = open_session(map_lines=MAP, ttl_minutes=60)
    b = open_session(map_lines=MAP, ttl_minutes=60)
    try:
        _ok(_mutate(a.session_id, "CREATE (:TSK {id: 'TA', goal: 'keep-a', status: 'open'})"))
        _ok(_mutate(b.session_id, "CREATE (:TSK {id: 'TB', goal: 'keep-b', status: 'open'})"))
        result = prepare_upgrade(token, directory=tmp_path)
        assert result.ready_to_stop is True
        manifest_path = tmp_path / MANIFEST_NAME
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        poisoned = None
        kept: dict[str, bytes] = {}
        for sess in manifest["sessions"]:
            snap = tmp_path / sess["file"]
            if sess["session_id"] == a.session_id:
                snap.write_text(
                    _inject_user_proxy(snap.read_text(encoding="utf-8"), fields, row),
                    encoding="utf-8",
                )
                sess["checksum_sha256"] = hashlib.sha256(snap.read_bytes()).hexdigest()
                poisoned = snap
            kept[sess["session_id"]] = snap.read_bytes()
        manifest_path.write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
        reset_registry()
        reset_drain_gate()
        report = restore_manifest(tmp_path)
        assert report.failed == 1 and report.ok == 1, report.errors
        assert report.errors[0]["code"] == "user_proxy_tag"
        assert get_entry(a.session_id) is None
        assert get_entry(b.session_id) is not None
        _assert_no_remapped_user_proxy()
        assert poisoned is not None and poisoned.read_bytes() == kept[a.session_id]
        for sess in manifest["sessions"]:
            assert (tmp_path / sess["file"]).read_bytes() == kept[sess["session_id"]]
    finally:
        reset_drain_gate()
        for sid in (a.session_id, b.session_id):
            if get_entry(sid) is not None:
                close_session(sid)


def test_upgrade_house_tags_omit_proxy_so_old_manifests_restore(memnet_temp, monkeypatch, tmp_path):
    """A 0.20.8 house_tags list has no PROXY; restore must not demand it."""
    import json

    from memnet.session import reset_registry
    from memnet.upgrade import (
        MANIFEST_NAME,
        _house_tags,
        prepare_upgrade,
        reset_drain_gate,
        restore_manifest,
    )

    token = "test-admin-token"
    monkeypatch.setenv("MEMNET_ADMIN_TOKEN", token)
    a = open_session(map_lines=MAP, ttl_minutes=60)
    try:
        _ok(_mutate(a.session_id, "CREATE (:TSK {id: 'T1', goal: 'g', status: 'open'})"))
        assert "PROXY" in a.tag_map.tags
        assert "PROXY" not in _house_tags(a.tag_map)
        result = prepare_upgrade(token, directory=tmp_path)
        assert result.ready_to_stop is True and result.unsaved == []
        manifest = json.loads((tmp_path / MANIFEST_NAME).read_text(encoding="utf-8"))
        for row in manifest["sessions"]:
            assert "PROXY" not in row["house_tags"]
            assert "LAW" in row["house_tags"] and "EDG" in row["house_tags"]
        reset_registry()
        reset_drain_gate()
        report = restore_manifest(tmp_path)
        assert report.failed == 0 and report.ok == 1, report.errors
    finally:
        reset_drain_gate()
        if get_entry(a.session_id) is not None:
            close_session(a.session_id)


def test_proxy_sessions_survive_admin_checkpoint_and_restore(memnet_temp, monkeypatch, tmp_path):
    from memnet.checkpoint import run_checkpoint
    from memnet.session import reset_registry
    from memnet.upgrade import restore_manifest

    token = "test-admin-token"
    monkeypatch.setenv("MEMNET_ADMIN_TOKEN", token)
    a = open_session(map_lines=MAP, ttl_minutes=60)
    b = open_session(map_lines=MAP, ttl_minutes=60)
    _ok(_mutate(b.session_id, "CREATE (:TSK {id: 'T1', goal: 'restored goal', status: 'open'})"))
    _proxy(a.session_id, "P1", b.session_id, "T1")
    _proxy(a.session_id, "P2", "sess_target", "T1")
    result = run_checkpoint(token, directory=tmp_path)
    assert result.exit_code == 0 and result.skipped == []
    reset_registry()
    assert get_entry(a.session_id) is None
    report = restore_manifest(tmp_path)
    assert not report.skipped
    assert "restored goal" in _ok(_follow(a.session_id, "P1"))["stdout"]
    assert _ok(_follow(a.session_id, "P2"))["stdout"].startswith("@STAT: follow|not_reachable")
    for sid in (a.session_id, b.session_id):
        close_session(sid)


def test_map_without_proxy_rejects_proxy_write_cleanly(memnet_temp):
    """An old server's map (no PROXY fixed tag) refuses the row unknown_tag."""
    from memnet.exceptions import MemNetError
    from memnet.fixed_tags import EDG_FIELDS, LAW_FIELDS
    from memnet.models import TagDef, TagMap
    from memnet.tag_map import parse_line

    old = TagMap(
        tags={
            "EDG": TagDef(tag="EDG", fields=EDG_FIELDS, kind="edge"),
            "LAW": TagDef(tag="LAW", fields=LAW_FIELDS, kind="node"),
            "TSK": TagDef(tag="TSK", fields=["id", "goal", "status"], kind="node"),
        }
    )
    with pytest.raises(MemNetError) as exc:
        parse_line("@PROXY: P1|s|n|", old)
    assert exc.value.code == "unknown_tag"
    ss = open_session(map_lines=MAP, ttl_minutes=60)
    try:
        get_entry(ss.session_id).tag_map = old
        got = _mutate(ss.session_id, "CREATE (:PROXY {target_session: 's', target: 'n'})")
        assert got["exit_code"] != 0 and "@ERR: unknown_tag|" in got["stderr"]
        assert len(get_entry(ss.session_id).store._by_hid) == 0
    finally:
        close_session(ss.session_id)


# 12. one hop only


def test_target_that_is_itself_a_proxy_is_returned_not_followed(two):
    a, b = two
    c = open_session(map_lines=MAP, ttl_minutes=60)
    try:
        _ok(_mutate(c.session_id, "CREATE (:TSK {id: 'T1', goal: 'two hops away', status: 'o'})"))
        _proxy(b.session_id, "PB", c.session_id, "T1")
        _proxy(a.session_id, "PA", b.session_id, "PB")
        got = _ok(_follow(a.session_id, "PA"))
        lines = got["stdout"].splitlines()
        assert lines[0] == "@STAT: follow|ok"
        assert lines[1].startswith("(:PROXY {") and f"target_session: '{c.session_id}'" in lines[1]
        assert "two hops away" not in got["stdout"]
    finally:
        close_session(c.session_id)


# 14. help


def _cli_option_flags(*path: str) -> set[str]:
    """Click option strings, independent of Rich wrapping ``--id`` as ``-`` + ``-id``."""
    import click
    from typer.main import get_command

    cmd = get_command(app)
    ctx = click.Context(cmd)
    for name in path:
        nxt = cmd.get_command(ctx, name)
        assert nxt is not None, f"missing CLI command {' '.join(path)}"
        cmd = nxt
        ctx = click.Context(cmd, parent=ctx)
    flags: set[str] = set()
    for param in cmd.get_params(ctx):
        flags.update(param.opts)
        flags.update(param.secondary_opts)
    return flags


def test_help_lists_follow():
    from typer.testing import CliRunner

    runner = CliRunner()
    assert runner.invoke(app, ["--help"]).exit_code == 0
    got = runner.invoke(app, ["query", "--help"])
    assert got.exit_code == 0 and "follow" in got.output
    # GitHub Actions paints help: Rich splits ``--id`` so it is not a substring.
    sub = runner.invoke(app, ["query", "follow", "--help"], color=True)
    assert sub.exit_code == 0
    flags = _cli_option_flags("query", "follow")
    assert {"--id", "--resolved-id", "--session", "--caller"} <= flags
