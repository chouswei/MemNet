"""0.15 catalog Snap + session strata + model Snap."""

from __future__ import annotations

from pathlib import Path

import pytest
from typer.testing import CliRunner

from memnet.catalog_snap import snap_model
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
