"""0.15 catalog Snap + session strata + model Snap."""

from __future__ import annotations

from pathlib import Path

import pytest
from typer.testing import CliRunner

from memnet.catalog_snap import (
    leftover_catalog_pkg_nick,
    reset_snap_cancel_check,
    set_snap_cancel_check,
    snap_model,
)
from memnet.cli import app
from memnet.config import Caps, examples_dir
from memnet.exceptions import MemNetError
from memnet.import_absorb import (
    WorkingMemorySlice,
    absorb_working_memory_slice,
    export_working_memory_slice,
)
from memnet.pin_map_composer import PinMapComposer
from memnet.session import close_session, get_session, list_sessions, open_session
from memnet.snapshot import load_snapshot, snapshot_text, write_snapshot
from memnet.tag_map import validate_id

runner = CliRunner()
_MAP = examples_dir() / "schema.sysml.example.txt"

_ROOT = """\
package DemoRoot {
  private import PkgReq::*;
  private import PkgPart::*;
}
"""

_REQ = """\
package PkgReq {
  requirement def ReqAlpha {
    attribute requirementId : String = "MN-REQ-DEMO.A";
  }
  requirement def ReqBeta {
    attribute requirementId : String = "MN-REQ-DEMO.B";
  }
}
"""

_PRT = """\
package PkgPart {
  part def PowerRail {
  }
}
"""

_PRT_SATISFY = """\
package PkgPart {
  part def PowerRail {
    satisfy PkgReq::ReqAlpha;
  }
}
"""

_FAT = """\
package FatPkg {
  requirement def R1 { attribute requirementId : String = "R1"; }
  requirement def R2 { attribute requirementId : String = "R2"; }
  requirement def R3 { attribute requirementId : String = "R3"; }
  part def P1 { }
  part def P2 { }
  part def P3 { }
}
"""


@pytest.fixture
def model_dir(tmp_path: Path) -> Path:
    root = tmp_path / "model"
    root.mkdir()
    (root / "root.sysml").write_text(_ROOT, encoding="utf-8")
    (root / "req.sysml").write_text(_REQ, encoding="utf-8")
    (root / "part.sysml").write_text(_PRT, encoding="utf-8")
    return root


def test_snap_model_catalog_and_package_interiors(memnet_temp, model_dir: Path):
    del memnet_temp
    result = snap_model(model_dir, map_file=_MAP)
    assert result.catalog_session_id.startswith("mn_")
    qnames = {row.qname for row in result.interiors}
    assert qnames == {"PkgReq", "PkgPart"}
    assert all(row.grain == "package" for row in result.interiors)
    assert result.catalog_session_id not in {row.session_id for row in result.interiors}

    catalog = get_session(result.catalog_session_id)
    pkgs = [r for r in catalog.store.list_records("PKG") if r.fields.get("session")]
    assert len(pkgs) == 2
    sessions = {r.fields.get("session") for r in pkgs}
    assert sessions == {row.session_id for row in result.interiors}
    nicks = {r.id for r in pkgs}
    assert all(nicks)
    for nick in nicks:
        validate_id(nick)
        assert nick.startswith("pkg_")
    assert not catalog.store.list_records("REQ")
    blob = PinMapComposer(catalog).compose(anchor=None, kind="PKG", locators=[], depth=1)[1]
    assert "PkgReq" in blob
    assert "_el" not in blob
    assert "_memnet_hid" not in blob

    req_sid = next(row.session_id for row in result.interiors if row.qname == "PkgReq")
    req_ss = get_session(req_sid)
    reqs = req_ss.store.list_records("REQ")
    assert {r.fields.get("requirementId") for r in reqs} == {"MN-REQ-DEMO.A", "MN-REQ-DEMO.B"}
    assert not req_ss.store.list_records("PRT") or all(
        r.fields.get("qname", "").startswith("PkgReq") for r in req_ss.store.list_records("PRT")
    )
    look = PinMapComposer(req_ss).compose(
        anchor=None,
        kind="REQ",
        locators=[("requirementId", "MN-REQ-DEMO.A")],
        depth=2,
    )[1]
    assert "MN-REQ-DEMO.A" in look
    assert "_el" not in look


def test_cross_cut_satisfy_is_catalog_locator_not_interior_dangle(memnet_temp, tmp_path: Path):
    """Turn D honesty: satisfy across package cuts lives on the catalog."""
    del memnet_temp
    root = tmp_path / "sat_model"
    root.mkdir()
    (root / "root.sysml").write_text(_ROOT, encoding="utf-8")
    (root / "req.sysml").write_text(_REQ, encoding="utf-8")
    (root / "part.sysml").write_text(_PRT_SATISFY, encoding="utf-8")
    result = snap_model(root, map_file=_MAP)
    assert len(result.cross_cuts) == 1
    cut = result.cross_cuts[0]
    assert cut.relation == "satisfies"
    assert cut.src_qname.endswith("PowerRail")
    assert cut.dst_qname.endswith("ReqAlpha")
    assert cut.dst_requirement_id == "MN-REQ-DEMO.A"
    assert cut.src_session != cut.dst_session
    assert result.cross_cut_misses == 0

    part_sid = next(row.session_id for row in result.interiors if row.qname == "PkgPart")
    req_sid = next(row.session_id for row in result.interiors if row.qname == "PkgReq")
    part_ss = get_session(part_sid)
    req_ss = get_session(req_sid)
    assert not part_ss.store.list_records("REQ")
    sat_interior = [
        r
        for r in part_ss.store._by_hid.values()
        if r.tag == "EDG" and r.fields.get("relation") == "satisfies"
    ]
    assert sat_interior == []
    assert {r.fields.get("requirementId") for r in req_ss.store.list_records("REQ")} == {
        "MN-REQ-DEMO.A",
        "MN-REQ-DEMO.B",
    }

    catalog = get_session(result.catalog_session_id)
    reqs = catalog.store.list_records("REQ")
    assert any(r.fields.get("qname") == cut.dst_qname for r in reqs)
    loc = next(r for r in reqs if r.fields.get("qname") == cut.dst_qname)
    assert loc.fields.get("session") == req_sid
    assert loc.fields.get("grain") == "cross_cut"
    assert loc.fields.get("requirementId") == "MN-REQ-DEMO.A"
    prts = catalog.store.list_records("PRT")
    src = next(r for r in prts if r.fields.get("qname") == cut.src_qname)
    assert src.fields.get("session") == part_sid
    sat_cat = [
        r
        for r in catalog.store._by_hid.values()
        if r.tag == "EDG" and r.fields.get("relation") == "satisfies"
    ]
    assert sat_cat

    look = PinMapComposer(catalog).compose(
        anchor=None,
        kind="REQ",
        locators=[("requirementId", "MN-REQ-DEMO.A")],
        depth=2,
    )[1]
    assert "MN-REQ-DEMO.A" in look
    assert "PowerRail" in look
    assert req_sid in look
    assert part_sid in look
    assert "_el" not in look

    snapped = runner.invoke(
        app,
        ["snap", "model", "--root", str(root), "--map-file", str(_MAP)],
    )
    assert snapped.exit_code == 0, snapped.stderr
    assert "@WRN: cross_cut|satisfies 1" in snapped.stderr


def test_cross_cut_over_m_keeps_package_pair_only(memnet_temp, tmp_path: Path):
    """When unique ends exceed goldfish M, catalog keeps PKG-PKG satisfies only."""
    del memnet_temp
    root = tmp_path / "sat_fat"
    root.mkdir()
    (root / "root.sysml").write_text(_ROOT, encoding="utf-8")
    (root / "req.sysml").write_text(
        """\
package PkgReq {
  requirement def ReqAlpha {
    attribute requirementId : String = "MN-REQ-DEMO.A";
  }
}
""",
        encoding="utf-8",
    )
    (root / "part.sysml").write_text(_PRT_SATISFY, encoding="utf-8")
    result = snap_model(root, map_file=_MAP, goldfish_m=1)
    assert len(result.cross_cuts) == 1
    catalog = get_session(result.catalog_session_id)
    assert not catalog.store.list_records("REQ")
    assert not catalog.store.list_records("PRT") or all(
        r.fields.get("grain") != "cross_cut" for r in catalog.store.list_records("PRT")
    )
    sat_cat = [
        r
        for r in catalog.store._by_hid.values()
        if r.tag == "EDG" and r.fields.get("relation") == "satisfies"
    ]
    assert sat_cat
    look = PinMapComposer(catalog).compose(
        anchor=None,
        kind="PKG",
        locators=[("qname", "PkgPart")],
        depth=2,
    )[1]
    assert "PkgPart" in look
    assert "PkgReq" in look
    assert "satisfies" in look
    assert "CueConflict" not in look


def test_snap_does_not_mint_session_per_req(memnet_temp, model_dir: Path):
    del memnet_temp
    result = snap_model(model_dir, map_file=_MAP)
    req_row = next(row for row in result.interiors if row.qname == "PkgReq")
    assert req_row.node_count >= 3
    assert len([row for row in result.interiors if row.qname == "PkgReq"]) == 1


def test_kind_band_when_package_over_two_m(memnet_temp, tmp_path: Path):
    del memnet_temp
    root = tmp_path / "fat"
    root.mkdir()
    (root / "fat.sysml").write_text(_FAT, encoding="utf-8")
    result = snap_model(root, map_file=_MAP, goldfish_m=2)
    bands = {row.kind_band for row in result.interiors}
    assert "REQ" in bands
    assert "PRT" in bands
    assert len(result.interiors) == 2
    req_ss = get_session(next(r.session_id for r in result.interiors if r.kind_band == "REQ"))
    assert len(req_ss.store.list_records("REQ")) == 3


def _midsize_sysml(root: Path, *, n_prt: int = 201, n_req: int = 125) -> Path:
    root.mkdir()
    parts = "\n".join(f"  part def Part{i} {{ }}" for i in range(n_prt))
    reqs = "\n".join(
        f'  requirement def Req{i} {{ attribute requirementId : String = "R{i}"; }}'
        for i in range(n_req)
    )
    (root / "root.sysml").write_text(
        "package FoamRoot {\n  private import FoamReq::*;\n  private import FoamPart::*;\n}\n",
        encoding="utf-8",
    )
    (root / "req.sysml").write_text(f"package FoamReq {{\n{reqs}\n}}\n", encoding="utf-8")
    (root / "part.sysml").write_text(f"package FoamPart {{\n{parts}\n}}\n", encoding="utf-8")
    return root


def test_midsize_model_stays_package_grain(memnet_temp, tmp_path: Path):
    """A few hundred parts and requirements: catalog + 2 packages, not per leaf."""
    del memnet_temp
    root = _midsize_sysml(tmp_path / "foam")
    result = snap_model(root, map_file=_MAP)
    assert len(result.interiors) == 2
    assert len(result.session_ids) == 3
    assert {row.qname for row in result.interiors} == {"FoamReq", "FoamPart"}
    assert all(row.grain == "package" for row in result.interiors)
    assert "child_package" not in {row.grain for row in result.interiors}
    for row in result.interiors:
        ss = get_session(row.session_id)
        prt = ss.store.list_records("PRT")
        req = ss.store.list_records("REQ")
        assert len(prt) != 1 or len(req) > 0
        assert len(req) != 1 or len(prt) > 0
        assert len(prt) + len(req) > 1
    assert len(list_sessions()) == 3


def test_same_kind_over_two_m_does_not_split_per_element(memnet_temp, tmp_path: Path):
    del memnet_temp
    root = tmp_path / "parts_only"
    root.mkdir()
    parts = "\n".join(f"  part def Part{i} {{ }}" for i in range(120))
    (root / "parts.sysml").write_text(f"package OnlyParts {{\n{parts}\n}}\n", encoding="utf-8")
    result = snap_model(root, map_file=_MAP)
    assert len(result.interiors) == 1
    assert result.interiors[0].grain == "package"
    assert result.interiors[0].node_count > 100


def test_nested_package_split_not_element_qname(memnet_temp, tmp_path: Path):
    del memnet_temp
    root = tmp_path / "nested"
    root.mkdir()
    child_a = "\n".join(f"    part def A{i} {{ }}" for i in range(5))
    child_b = "\n".join(f"    part def B{i} {{ }}" for i in range(5))
    (root / "nest.sysml").write_text(
        "package FatPkg {\n"
        f"  package ChildA {{\n{child_a}\n  }}\n"
        f"  package ChildB {{\n{child_b}\n  }}\n"
        "}\n",
        encoding="utf-8",
    )
    result = snap_model(root, map_file=_MAP, goldfish_m=2)
    assert {row.grain for row in result.interiors} == {"nested_package"}
    assert {row.qname for row in result.interiors} == {"FatPkg::ChildA", "FatPkg::ChildB"}
    for row in result.interiors:
        assert row.node_count > 1


def test_session_precheck_creates_nothing(memnet_temp, model_dir: Path, schema_file, monkeypatch):
    monkeypatch.setenv("MEMNET_MAX_SESSIONS", "2")
    filler = open_session(map_file=str(schema_file), caps=Caps())
    before = list_sessions(Caps())
    with pytest.raises(MemNetError) as ei:
        snap_model(model_dir, map_file=_MAP, caps=Caps())
    assert ei.value.code == "limit_exceeded"
    assert ei.value.message == "sessions|4/2"
    after = list_sessions(Caps())
    assert after == before
    assert filler.session_id in {row[0] for row in after}


def test_ingest_budget_precheck_creates_nothing(memnet_temp, model_dir: Path):
    del memnet_temp
    before = list_sessions()
    with pytest.raises(MemNetError) as ei:
        snap_model(model_dir, map_file=_MAP, max_nodes=2)
    assert ei.value.code == "ingest_budget"
    assert list_sessions() == before


def test_midway_failure_leaves_no_sessions(memnet_temp, model_dir: Path, monkeypatch):
    del memnet_temp
    before = list_sessions()
    real = open_session
    n = {"opens": 0}

    def boom(*args, **kwargs):
        n["opens"] += 1
        if n["opens"] >= 2:
            raise MemNetError("internal", "forced mid-way failure")
        return real(*args, **kwargs)

    monkeypatch.setattr("memnet.catalog_snap.open_session", boom)
    with pytest.raises(MemNetError) as ei:
        snap_model(model_dir, map_file=_MAP)
    assert ei.value.code == "internal"
    assert list_sessions() == before


def test_repeat_snap_replaces_same_root(memnet_temp, model_dir: Path):
    del memnet_temp
    first = snap_model(model_dir, map_file=_MAP)
    n1 = len(list_sessions())
    assert n1 == 3
    second = snap_model(model_dir, map_file=_MAP)
    assert len(list_sessions()) == n1
    assert second.catalog_session_id != first.catalog_session_id
    with pytest.raises(MemNetError) as ei:
        get_session(first.catalog_session_id)
    assert ei.value.code in {"session_not_found", "session_expired"}


def test_caller_gone_rolls_back_partial_mint(memnet_temp, model_dir: Path, monkeypatch):
    del memnet_temp
    before = list_sessions()
    minted = {"yes": False}
    real = open_session

    def wrap(*args, **kwargs):
        ss = real(*args, **kwargs)
        minted["yes"] = True
        return ss

    monkeypatch.setattr("memnet.catalog_snap.open_session", wrap)
    token = set_snap_cancel_check(lambda: minted["yes"])
    try:
        with pytest.raises(MemNetError) as ei:
            snap_model(model_dir, map_file=_MAP)
        assert ei.value.code == "caller_gone"
        assert list_sessions() == before
    finally:
        reset_snap_cancel_check(token)


def test_empty_catalog_skips(memnet_temp, tmp_path: Path):
    del memnet_temp
    empty = tmp_path / "empty"
    empty.mkdir()
    (empty / "note.sysml").write_text("/* no package */\n", encoding="utf-8")
    before = list_sessions()
    with pytest.raises(MemNetError) as ei:
        snap_model(empty, map_file=_MAP)
    assert ei.value.code == "empty_catalog"
    assert list_sessions() == before


def test_join_is_slice_absorb_not_whole_s(memnet_temp, model_dir: Path):
    del memnet_temp
    result = snap_model(model_dir, map_file=_MAP)
    req_sid = next(row.session_id for row in result.interiors if row.qname == "PkgReq")
    member = get_session(req_sid)
    reqs = member.store.list_records("REQ")
    one = next(r for r in reqs if r.fields.get("requirementId") == "MN-REQ-DEMO.A")
    with pytest.raises(MemNetError) as ei:
        export_working_memory_slice(member, anchors=[])
    assert ei.value.code == "no_anchor"
    lead = open_session(map_file=str(_MAP))
    slice_ = WorkingMemorySlice(
        source_session_id=req_sid,
        anchors=["requirementId=MN-REQ-DEMO.A"],
        depth=1,
        view=None,
        records=[one],
    )
    imported = absorb_working_memory_slice(lead, slice_, enable_guard=False)
    assert imported.imported_ids
    lead_ss = get_session(lead.session_id)
    ids = {r.fields.get("requirementId") for r in lead_ss.store.list_records("REQ")}
    assert "MN-REQ-DEMO.A" in ids
    assert "MN-REQ-DEMO.B" not in ids


def test_close_frees_slots_for_snap_model(memnet_temp, model_dir: Path, schema_file, monkeypatch):
    monkeypatch.setenv("MEMNET_MAX_SESSIONS", "3")

    filler = open_session(map_file=str(schema_file), caps=Caps())
    with pytest.raises(MemNetError) as ei:
        snap_model(model_dir, map_file=_MAP, caps=Caps())
    assert ei.value.code == "limit_exceeded"
    assert ei.value.message == "sessions|4/3"
    close_session(filler.session_id, Caps())
    result = snap_model(model_dir, map_file=_MAP, caps=Caps())
    assert result.catalog_session_id
    assert len(result.session_ids) == 3


def test_leftover_catalog_pkg_nick_stable_and_unique() -> None:
    used: set[str] = set()
    a = leftover_catalog_pkg_nick("PkgReq", used=used)
    b = leftover_catalog_pkg_nick("PkgReq", used=set())
    assert a == b == "pkg_PkgReq"
    validate_id(a)
    band = leftover_catalog_pkg_nick("FatPkg", kind_band="REQ", used=used)
    assert band == "pkg_FatPkg_REQ"
    collide = leftover_catalog_pkg_nick("PkgReq", used=used)
    assert collide != a
    assert collide.startswith("pkg_")
    validate_id(collide)
    long_q = "Q" * 80
    hashed = leftover_catalog_pkg_nick(long_q, used=set())
    assert hashed.startswith("pkg_")
    assert len(hashed) <= 64
    validate_id(hashed)


def test_catalog_session_save_load_roundtrip(memnet_temp, model_dir: Path, tmp_path: Path):
    del memnet_temp
    result = snap_model(model_dir, map_file=_MAP)
    catalog = get_session(result.catalog_session_id)
    text = snapshot_text(catalog)
    rec_lines = [
        ln for ln in text.splitlines() if ln.startswith("@") and not ln.startswith("@SNAP:")
    ]
    rec_lines = [ln for ln in rec_lines if ln.startswith("@PKG:")]
    assert rec_lines
    for line in rec_lines:
        nick = line.split(":", 1)[1].strip().split("|", 1)[0]
        assert nick, line
        validate_id(nick)

    snap_path = tmp_path / "catalog.snap"
    write_snapshot(catalog, snap_path)
    loaded = load_snapshot(snap_path)
    pkgs = [r for r in loaded.store.list_records("PKG") if r.fields.get("session")]
    assert {r.fields.get("qname") for r in pkgs} == {"PkgReq", "PkgPart"}
    assert all(r.id for r in pkgs)
    look = PinMapComposer(loaded).compose(anchor=None, kind="PKG", locators=[], depth=1)[1]
    assert "PkgReq" in look
    assert "pkg_PkgReq" not in look
    assert "_el" not in look

    save = runner.invoke(
        app,
        [
            "session",
            "save",
            "--file",
            str(snap_path),
            "--session",
            result.catalog_session_id,
        ],
    )
    assert save.exit_code == 0, save.stderr
    load = runner.invoke(app, ["session", "load", "--file", str(snap_path)])
    assert load.exit_code == 0, load.stderr
    assert "@ERR:" not in load.stdout
    assert "invalid_id" not in load.stderr


def test_cli_snap_model_and_session_list(memnet_temp, model_dir: Path):
    del memnet_temp
    snapped = runner.invoke(
        app,
        ["snap", "model", "--root", str(model_dir), "--map-file", str(_MAP)],
    )
    assert snapped.exit_code == 0, snapped.stderr
    assert "@SNAP: catalog|" in snapped.stdout
    assert "_el" not in snapped.stdout
    listed = runner.invoke(app, ["session", "list"])
    assert listed.exit_code == 0
    assert listed.stdout.splitlines()[0].startswith("@STAT: sessions|")
    assert listed.stdout.count("@SESSION:") >= 3
    cat = None
    for line in snapped.stdout.splitlines():
        if line.startswith("@SNAP:"):
            cat = line.split("|")[1]
    assert cat
    look = runner.invoke(
        app,
        ["query", "pin-map", "--kind", "PKG", "--session", cat],
    )
    assert look.exit_code == 0, look.stderr
    assert "PkgReq" in look.stdout or "session" in look.stdout
    assert "_el" not in look.stdout


def test_serve_timeout_named_and_rolls_back(memnet_temp, model_dir: Path, monkeypatch):
    """Client wait exceeded names serve_timeout; serve stops and rolls back."""
    import socket
    import threading
    import time

    from memnet.catalog_snap import raise_if_snap_cancelled
    from memnet.serve import probe, run_serve, send_command
    from memnet.session import open_session as real_open

    def slow_open(*args, **kwargs):
        for _ in range(40):
            time.sleep(0.05)
            raise_if_snap_cancelled()
        return real_open(*args, **kwargs)

    monkeypatch.setattr("memnet.catalog_snap.open_session", slow_open)
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.bind(("127.0.0.1", 0))
        port = int(sock.getsockname()[1])
    monkeypatch.setenv("MEMNET_SERVE_PORT", str(port))
    monkeypatch.setenv("MEMNET_SERVE_HOST", "127.0.0.1")
    thread = threading.Thread(
        target=run_serve,
        kwargs={"host": "127.0.0.1", "port": port},
        daemon=True,
    )
    thread.start()
    for _ in range(100):
        if probe(host="127.0.0.1", port=port):
            break
        time.sleep(0.05)
    else:
        pytest.fail("memnet serve did not start")
    before = len(list_sessions())
    raw = send_command(
        ["snap", "model", "--root", str(model_dir), "--map-file", str(_MAP)],
        host="127.0.0.1",
        port=port,
        timeout=0.25,
    )
    assert raw["exit_code"] == 1
    assert "@ERR: serve_timeout|wait exceeded" in (raw.get("stderr") or "")
    deadline = time.time() + 3.0
    while time.time() < deadline:
        if len(list_sessions()) == before:
            break
        time.sleep(0.05)
    assert len(list_sessions()) == before
