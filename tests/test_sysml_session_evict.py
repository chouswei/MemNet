"""MN-REQ-05.5 model presence: the SysML cites runtime tests (proposed, not shipped).

Runtime behaviour lives in tests/test_session_evict.py. This file only checks
that the model points at those tests, that every cited test exists, and that
the runtime module stays xfail until the engine ships. It makes no claim that a
flag is true.
"""

from __future__ import annotations

import ast
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
MODELS = ROOT / "sysml-models" / "models"
README = ROOT / "sysml-models" / "README.md"
DEPLOY = MODELS / "deploy.sysml"
REQ = MODELS / "requirements.sysml"
VERIFY = MODELS / "verify.sysml"
BEHAVIOUR = MODELS / "behaviour.sysml"
RUNTIME = ROOT / "tests" / "test_session_evict.py"
VER_IDS = [f"MN-VER-05-S0{n}" for n in range(3, 10)]


def _read(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def _verify_docs(text: str) -> dict[str, str]:
    """Map MN-VER-05-S0x id to its verification def doc, one def block at a time."""
    docs: dict[str, str] = {}
    for block in re.split(r"(?=verification def )", text):
        ver = re.search(r'attribute verificationId : String = "(MN-VER-05-S0\d)";', block)
        doc = re.search(r"doc /\*(.*?)\*/", block, re.S)
        if ver and doc:
            docs[ver.group(1)] = doc.group(1)
    return docs


def _cited_tests(doc: str) -> set[str]:
    """Test names cited in a doc, ignoring the runtime file path itself."""
    return set(re.findall(r"\btest_\w+", doc.replace("tests/test_session_evict.py", "")))


def _runtime_test_names() -> set[str]:
    tree = ast.parse(_read(RUNTIME))
    return {
        n.name for n in tree.body if isinstance(n, ast.FunctionDef) and n.name.startswith("test_")
    }


def test_requirement_def_and_derivation_present():
    text = _read(REQ)
    assert "requirement def MN_REQ_05_5_SessionCapEvictLru {" in text
    assert 'attribute requirementId : String = "MN-REQ-05.5";' in text
    assert "requirement sessionCapEvictLruReq" in text
    assert "end #derive ::> sessionCapEvictLruReq;" in text


def test_verify_defs_s03_to_s09_present():
    text = _read(VERIFY)
    docs = _verify_docs(text)
    assert set(VER_IDS) <= set(docs)
    for n in range(3, 10):
        assert f"verification def MN_VER_05_S0{n}_" in text


def test_each_verify_doc_names_runtime_pytests_that_exist():
    docs = _verify_docs(_read(VERIFY))
    names = _runtime_test_names()
    for ver_id in VER_IDS:
        doc = docs[ver_id]
        assert "tests/test_session_evict.py" in doc, f"{ver_id} must name its runtime file"
        cited = _cited_tests(doc)
        assert cited, f"{ver_id} must cite at least one runtime test"
        assert cited <= names, f"{ver_id} cites a test that does not exist"


def test_every_runtime_test_is_cited_by_a_verify_doc():
    docs = _verify_docs(_read(VERIFY))
    cited = set()
    for ver_id in VER_IDS:
        doc = docs[ver_id]
        cited |= _cited_tests(doc)
    assert _runtime_test_names() == cited


def test_runtime_module_is_xfail_until_shipped():
    text = _read(RUNTIME)
    assert "pytestmark = pytest.mark.xfail(" in text
    assert 'reason="MN-REQ-05.5 not shipped; engine pending"' in text
    assert "strict=False" in text


def test_deploy_satisfy_not_linked_while_not_shipped():
    text = _read(DEPLOY)
    satisfy = "satisfy MN_REQ_00_MissionBridge::MN_REQ_05_HardCaps::MN_REQ_05_5_SessionCapEvictLru"
    assert satisfy not in text
    assert "attribute evictShipped : Boolean = false;" in text


def test_evict_saving_closes_only_on_evict_saved():
    text = _read(BEHAVIOUR)
    assert "attribute def EvEvictSaved" in text
    closed = r"transition evict_saving_to_closed\s+first evictSaving\s+accept EvEvictSaved\s"
    assert re.search(closed + r"+then closed;", text)
    active = (
        r"transition evict_saving_to_active\s+first evictSaving\s+accept EvError\s+then active;"
    )
    assert re.search(active, text)


def test_readme_points_at_runtime_file():
    assert "tests/test_session_evict.py" in _read(README)


def test_no_lease_carried_wording_anywhere_in_models():
    everything = "\n".join(_read(p) for p in MODELS.glob("*.sysml")) + _read(README)
    assert "evictKeepsAclLease" not in everything
    assert "same ACL and lease" not in everything
