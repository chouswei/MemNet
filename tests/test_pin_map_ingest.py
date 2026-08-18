"""Path-B PinMapIngest engines (MN-REQ-11.16 / #31 / #64)."""

from __future__ import annotations

from pathlib import Path

import pytest

from memnet.exceptions import MemNetError
from memnet.pin_map_composer import PinMapComposer
from memnet.pin_map_ingest import (
    IMPLEMENTED_CODEBASE,
    IMPLEMENTED_PCBA,
    IMPLEMENTED_SKILLS,
    IMPLEMENTED_SYSML,
    PinMapIngest_Codebase,
    PinMapIngest_PcbaAto,
    PinMapIngest_SkillsRules,
    PinMapIngest_Sysml,
    get_engine,
    ingest_codebase,
    ingest_pcba,
    ingest_skills,
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

_CODE_FIXTURE = '''\
"""Golden codebase fixture for PinMapIngest_Codebase."""

def helper(x):
    return x + 1


def entry(n):
    return helper(n)


class Greeter:
    def hello(self, name):
        return helper(len(name))

    @property
    def label(self):
        return "hi"

    @label.setter
    def label(self, value):
        return value
'''

_ATO_FIXTURE = """\
# Golden Atopile fixture for PinMapIngest_PcbaAto (bounded LED blink slice).
module LedBlink:
    signal vcc
    signal gnd

    component Led:
        pin anode
        pin cathode

    component Resistor:
        pin 1
        pin 2

    led = new Led
    r1 = new Resistor

    vcc ~ r1.1
    r1.2 ~ led.anode
    led.cathode ~ gnd
"""

_SKILL_FIXTURE = """\
---
name: demo-ingest
description: Short anchor phrase for Path-B skills ingest golden test
related:
  - companion-rule
triggers:
  - ingest skills
---
# Demo ingest skill

Long body that MUST NOT become a free prose blob in the pin map.
"""

_RULE_FIXTURE = """\
---
name: companion-rule
description: Companion rule paired with demo-ingest
governs:
  - demo-ingest
---
# Companion rule body (not ingested as blob)
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
def codebase_schema(tmp_path: Path) -> Path:
    src = Path(__file__).resolve().parents[1] / (
        "parts/common/memnet/memnet/examples/schema.codebase.example.txt"
    )
    dest = tmp_path / "schema.codebase.example.txt"
    dest.write_text(src.read_text(encoding="utf-8"), encoding="utf-8")
    return dest


@pytest.fixture
def pcba_schema(tmp_path: Path) -> Path:
    src = Path(__file__).resolve().parents[1] / (
        "parts/common/memnet/memnet/examples/schema.pcba.example.txt"
    )
    dest = tmp_path / "schema.pcba.example.txt"
    dest.write_text(src.read_text(encoding="utf-8"), encoding="utf-8")
    return dest


@pytest.fixture
def skills_schema(tmp_path: Path) -> Path:
    src = Path(__file__).resolve().parents[1] / (
        "parts/common/memnet/memnet/examples/schema.skills.example.txt"
    )
    dest = tmp_path / "schema.skills.example.txt"
    dest.write_text(src.read_text(encoding="utf-8"), encoding="utf-8")
    return dest


@pytest.fixture
def sysml_file(tmp_path: Path) -> Path:
    p = tmp_path / "demo.sysml"
    p.write_text(_FIXTURE, encoding="utf-8")
    return p


@pytest.fixture
def code_file(tmp_path: Path) -> Path:
    p = tmp_path / "demo_mod.py"
    p.write_text(_CODE_FIXTURE, encoding="utf-8")
    return p


@pytest.fixture
def ato_file(tmp_path: Path) -> Path:
    p = tmp_path / "led_blink.ato"
    p.write_text(_ATO_FIXTURE, encoding="utf-8")
    return p


@pytest.fixture
def skills_dir(tmp_path: Path) -> Path:
    skill = tmp_path / "demo-ingest"
    skill.mkdir()
    (skill / "SKILL.md").write_text(_SKILL_FIXTURE, encoding="utf-8")
    rules = tmp_path / "rules"
    rules.mkdir()
    (rules / "companion.mdc").write_text(_RULE_FIXTURE, encoding="utf-8")
    return tmp_path


def test_engine_flags():
    assert IMPLEMENTED_SYSML is True
    assert IMPLEMENTED_CODEBASE is True
    assert IMPLEMENTED_PCBA is True
    assert IMPLEMENTED_SKILLS is True
    assert PinMapIngest_Sysml().implemented is True
    assert PinMapIngest_Codebase().implemented is True
    assert PinMapIngest_PcbaAto().implemented is True
    assert PinMapIngest_SkillsRules().implemented is True


def test_reject_client_new():
    with pytest.raises(MemNetError) as ei:
        reject_client_new(["MERGE (:PRT {id: 'NEW'})"])
    assert ei.value.code == "new_illegal"


def test_get_engine_domains():
    assert isinstance(get_engine("sysml"), PinMapIngest_Sysml)
    assert isinstance(get_engine("codebase"), PinMapIngest_Codebase)
    assert isinstance(get_engine("pcba"), PinMapIngest_PcbaAto)
    assert isinstance(get_engine("skills"), PinMapIngest_SkillsRules)


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


def test_ingest_sysml_budget(memnet_temp, sysml_schema: Path, sysml_file: Path):
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


# ----- Codebase -----


def test_project_codebase_deterministic_locators(code_file: Path):
    result = PinMapIngest_Codebase().project(code_file, max_nodes=50)
    assert any(i.startswith("MOD_") for i in result.node_ids)
    assert any(i.startswith("SYM_") for i in result.node_ids)
    label_pins = [i for i in result.node_ids if i.endswith("_Greeter_label") or "Greeter_label" in i]
    assert len(label_pins) == 1
    gql = "\n".join(result.gql_lines)
    assert "path:" in gql
    assert "line:" in gql
    assert "signature:" in gql
    assert "NEW" not in gql
    again = PinMapIngest_Codebase().project(code_file, max_nodes=50)
    assert again.node_ids == result.node_ids
    assert again.edge_ids == result.edge_ids


def test_codebase_reject_new_in_commit(memnet_temp, codebase_schema: Path, code_file: Path):
    ss = open_session(map_file=str(codebase_schema))
    result = PinMapIngest_Codebase().project(code_file)
    bad = list(result.gql_lines) + ["MERGE (n:SYM {id: 'NEW'}) SET n += {name: 'x'}"]
    result.gql_lines = bad
    with pytest.raises(MemNetError) as ei:
        PinMapIngest_Codebase().commit(ss, result)
    assert ei.value.code == "new_illegal"


def test_ingest_codebase_commit_and_pin_map(memnet_temp, codebase_schema: Path, code_file: Path):
    ss = open_session(map_file=str(codebase_schema))
    result = ingest_codebase(ss, code_file, max_nodes=50)
    assert result.committed
    mods = [r for r in ss.store.by_id.values() if r.tag == "MOD"]
    syms = [r for r in ss.store.by_id.values() if r.tag == "SYM"]
    assert mods
    assert syms
    assert any(s.fields.get("name") == "helper" for s in syms)
    assert any(s.fields.get("signature", "").startswith("def helper") for s in syms)
    defines = [
        r
        for r in ss.store.by_id.values()
        if r.tag == "EDG" and r.fields.get("relation") == "defines"
    ]
    calls = [
        r for r in ss.store.by_id.values() if r.tag == "EDG" and r.fields.get("relation") == "calls"
    ]
    assert defines
    assert calls
    anchor = mods[0].id
    text = PinMapComposer(ss).compose(anchor=anchor, depth=2)[1]
    assert "MOD" in text or mods[0].id in text


def test_ingest_codebase_idempotent(memnet_temp, codebase_schema: Path, code_file: Path):
    ss = open_session(map_file=str(codebase_schema))
    ingest_codebase(ss, code_file)
    n1 = len(ss.store.by_id)
    ingest_codebase(ss, code_file)
    assert len(ss.store.by_id) == n1


def test_ingest_codebase_budget(code_file: Path):
    with pytest.raises(MemNetError) as ei:
        PinMapIngest_Codebase().project(code_file, max_nodes=1)
    assert ei.value.code == "ingest_budget"


# ----- PCBA Atopile -----


def test_project_pcba_deterministic_locators(ato_file: Path):
    result = PinMapIngest_PcbaAto().project(ato_file, max_nodes=50)
    assert any(i.startswith("CMP_") for i in result.node_ids)
    assert any(i.startswith("NET_") for i in result.node_ids)
    assert any(i.startswith("PIN_") for i in result.node_ids)
    gql = "\n".join(result.gql_lines)
    assert "refdes:" in gql
    assert "net:" in gql or "pin:" in gql
    assert "path:" in gql
    assert "NEW" not in gql
    again = PinMapIngest_PcbaAto().project(ato_file, max_nodes=50)
    assert again.node_ids == result.node_ids


def test_pcba_reject_new_in_commit(memnet_temp, pcba_schema: Path, ato_file: Path):
    ss = open_session(map_file=str(pcba_schema))
    result = PinMapIngest_PcbaAto().project(ato_file)
    result.gql_lines = list(result.gql_lines) + ["MERGE (n:CMP {id: 'NEW'}) SET n += {refdes: 'x'}"]
    with pytest.raises(MemNetError) as ei:
        PinMapIngest_PcbaAto().commit(ss, result)
    assert ei.value.code == "new_illegal"


def test_ingest_pcba_commit_and_pin_map(memnet_temp, pcba_schema: Path, ato_file: Path):
    ss = open_session(map_file=str(pcba_schema))
    result = ingest_pcba(ss, ato_file, max_nodes=50)
    assert result.committed
    cmps = [r for r in ss.store.by_id.values() if r.tag == "CMP"]
    nets = [r for r in ss.store.by_id.values() if r.tag == "NET"]
    pins = [r for r in ss.store.by_id.values() if r.tag == "PIN"]
    assert any(c.fields.get("refdes") == "led" for c in cmps)
    assert any(c.fields.get("refdes") == "r1" for c in cmps)
    assert any(n.fields.get("net") == "vcc" for n in nets)
    assert pins
    owns = [
        r for r in ss.store.by_id.values() if r.tag == "EDG" and r.fields.get("relation") == "owns"
    ]
    on_net = [
        r
        for r in ss.store.by_id.values()
        if r.tag == "EDG" and r.fields.get("relation") == "on_net"
    ]
    assert owns
    assert on_net
    # Bounded: fixture is a tiny slice, not a whole board dump
    assert result.node_count < 40


def test_ingest_pcba_idempotent(memnet_temp, pcba_schema: Path, ato_file: Path):
    ss = open_session(map_file=str(pcba_schema))
    ingest_pcba(ss, ato_file)
    n1 = len(ss.store.by_id)
    ingest_pcba(ss, ato_file)
    assert len(ss.store.by_id) == n1


def test_ingest_pcba_budget(ato_file: Path):
    with pytest.raises(MemNetError) as ei:
        PinMapIngest_PcbaAto().project(ato_file, max_nodes=1)
    assert ei.value.code == "ingest_budget"


# ----- Skills / rules -----


def test_project_skills_deterministic_locators(skills_dir: Path):
    result = PinMapIngest_SkillsRules().project(skills_dir, max_nodes=50)
    assert any(i.startswith("SKL_") for i in result.node_ids)
    assert any(i.startswith("RUL_") for i in result.node_ids)
    gql = "\n".join(result.gql_lines)
    assert "skill_id:" in gql
    assert "phrase:" in gql
    assert "NEW" not in gql
    # Body blob must not appear
    assert "Long body that MUST NOT" not in gql
    again = PinMapIngest_SkillsRules().project(skills_dir, max_nodes=50)
    assert again.node_ids == result.node_ids


def test_skills_reject_new_in_commit(memnet_temp, skills_schema: Path, skills_dir: Path):
    ss = open_session(map_file=str(skills_schema))
    result = PinMapIngest_SkillsRules().project(skills_dir)
    result.gql_lines = list(result.gql_lines) + [
        "MERGE (n:SKL {id: 'NEW'}) SET n += {skill_id: 'x'}"
    ]
    with pytest.raises(MemNetError) as ei:
        PinMapIngest_SkillsRules().commit(ss, result)
    assert ei.value.code == "new_illegal"


def test_ingest_skills_commit_and_pin_map(memnet_temp, skills_schema: Path, skills_dir: Path):
    ss = open_session(map_file=str(skills_schema))
    result = ingest_skills(ss, skills_dir, max_nodes=50)
    assert result.committed
    assert ss.store.get("SKL_demo_ingest") is not None
    skl = ss.store.get("SKL_demo_ingest")
    assert skl.fields.get("skill_id") == "demo-ingest"
    assert "phrase" in skl.fields
    assert "Long body" not in skl.fields.get("phrase", "")
    rul = ss.store.get("RUL_companion_rule")
    assert rul is not None
    paired = [
        r
        for r in ss.store.by_id.values()
        if r.tag == "EDG" and r.fields.get("relation") == "paired_with"
    ]
    governs = [
        r
        for r in ss.store.by_id.values()
        if r.tag == "EDG" and r.fields.get("relation") == "governs"
    ]
    assert paired or governs


def test_ingest_skills_idempotent(memnet_temp, skills_schema: Path, skills_dir: Path):
    ss = open_session(map_file=str(skills_schema))
    ingest_skills(ss, skills_dir)
    n1 = len(ss.store.by_id)
    ingest_skills(ss, skills_dir)
    assert len(ss.store.by_id) == n1


def test_ingest_skills_budget(skills_dir: Path):
    with pytest.raises(MemNetError) as ei:
        PinMapIngest_SkillsRules().project(skills_dir, max_nodes=1)
    assert ei.value.code == "ingest_budget"
