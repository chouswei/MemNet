"""Path-B PinMapIngest_Sysml (MN-REQ-11.16 / #31)."""

from __future__ import annotations

from pathlib import Path

import pytest

from memnet.exceptions import MemNetError
from memnet.pin_map_composer import PinMapComposer
from memnet.pin_map_ingest import (
    IMPLEMENTED_SYSML,
    PinMapIngest_Codebase,
    PinMapIngest_Sysml,
    get_engine,
    ingest_sysml,
    reject_client_new,
)
from memnet.session import open_session

_FIXTURE = """\
package DemoPkg {
  requirement def ReqAlpha {
    doc /* alpha */
    attribute requirementId : String = "MN-REQ-DEMO.1";
  }
  part def PowerRail {
    satisfy ReqAlpha;
  }
}
"""


@pytest.fixture
def sysml_schema(tmp_path: Path) -> Path:
    src = Path(__file__).resolve().parents[1] / (
        "parts/common/memnet/memnet/examples/schema.sysml.example.txt"
    )
    dest = tmp_path / "schema.sysml.example.txt"
    dest.write_text(src.read_text(encoding="utf-8"), encoding="utf-8")
    return dest


@pytest.fixture
def sysml_file(tmp_path: Path) -> Path:
    p = tmp_path / "demo.sysml"
    p.write_text(_FIXTURE, encoding="utf-8")
    return p


def test_sysml_engine_flag():
    assert IMPLEMENTED_SYSML is True
    assert PinMapIngest_Sysml().implemented is True
    assert PinMapIngest_Codebase().implemented is False


def test_reject_client_new():
    with pytest.raises(MemNetError) as ei:
        reject_client_new(["MERGE (:PRT {id: 'NEW'})"])
    assert ei.value.code == "new_illegal"


def test_codebase_not_implemented():
    with pytest.raises(MemNetError) as ei:
        PinMapIngest_Codebase().project("/tmp")
    assert ei.value.code == "not_implemented"


def test_get_engine_sysml():
    eng = get_engine("sysml")
    assert isinstance(eng, PinMapIngest_Sysml)


def test_project_sysml_deterministic_locators(sysml_file: Path):
    result = PinMapIngest_Sysml().project(sysml_file, max_nodes=50)
    assert result.node_count >= 3
    assert any(i.startswith("PKG_") for i in result.node_ids)
    assert any(i.startswith("REQ_") for i in result.node_ids)
    assert any(i.startswith("PRT_") for i in result.node_ids)
    # requirementId drives REQ ground id
    assert "REQ_MN_REQ_DEMO_1" in result.node_ids
    gql = "\n".join(result.gql_lines)
    assert "qname:" in gql or "qname: '" in gql
    assert "path:" in gql
    assert "NEW" not in gql
    # stable across re-project
    again = PinMapIngest_Sysml().project(sysml_file, max_nodes=50)
    assert again.node_ids == result.node_ids


def test_ingest_sysml_commit_and_pin_map(memnet_temp, sysml_schema: Path, sysml_file: Path):
    ss = open_session(map_file=str(sysml_schema))
    result = ingest_sysml(ss, sysml_file, max_nodes=50)
    assert result.committed is True
    assert ss.store.get("REQ_MN_REQ_DEMO_1") is not None
    req = ss.store.get("REQ_MN_REQ_DEMO_1")
    assert req.fields.get("requirementId") == "MN-REQ-DEMO.1"
    assert req.fields.get("path") == "demo.sysml"
    assert "qname" in req.fields

    # contains edge package → req
    contains = [
        r
        for r in ss.store.by_id.values()
        if r.tag == "EDG" and r.fields.get("relation") == "contains"
    ]
    assert contains

    # satisfies PowerRail → ReqAlpha
    sats = [
        r
        for r in ss.store.by_id.values()
        if r.tag == "EDG" and r.fields.get("relation") == "satisfies"
    ]
    assert sats

    text = PinMapComposer(ss).compose(anchor="REQ_MN_REQ_DEMO_1", depth=2)[1]
    assert "REQ_MN_REQ_DEMO_1" in text or "REQ [" in text or "REQ_MN" in text


def test_ingest_sysml_idempotent(memnet_temp, sysml_schema: Path, sysml_file: Path):
    ss = open_session(map_file=str(sysml_schema))
    ingest_sysml(ss, sysml_file)
    n1 = len(ss.store.by_id)
    ingest_sysml(ss, sysml_file)
    n2 = len(ss.store.by_id)
    assert n2 == n1


def test_ingest_budget(memnet_temp, sysml_schema: Path, sysml_file: Path):
    ss = open_session(map_file=str(sysml_schema))
    with pytest.raises(MemNetError) as ei:
        ingest_sysml(ss, sysml_file, max_nodes=1)
    assert ei.value.code == "ingest_budget"


def test_ingest_real_requirements_leaf(memnet_temp, sysml_schema: Path):
    """Bounded slice of in-repo requirements.sysml (MN-REQ-11.16 ground ids)."""
    req_path = Path(__file__).resolve().parents[1] / "sysml-models/models/requirements.sysml"
    if not req_path.is_file():
        pytest.skip("sysml-models not present")
    ss = open_session(map_file=str(sysml_schema))
    result = ingest_sysml(ss, req_path, max_nodes=400, max_files=1)
    assert result.committed
    assert ss.store.get("REQ_MN_REQ_11_16") is not None
    row = ss.store.get("REQ_MN_REQ_11_16")
    assert row.fields.get("requirementId") == "MN-REQ-11.16"
    assert "requirements.sysml" in row.fields.get("path", "")
