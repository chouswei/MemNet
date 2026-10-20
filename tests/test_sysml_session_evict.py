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
SATISFY_LINE = (
    r"^\s*satisfy\s+MN_REQ_00_MissionBridge::MN_REQ_05_HardCaps::MN_REQ_05_5_SessionCapEvictLru\s*;"
)


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


def _evict_shipped() -> bool:
    found = re.findall(r"attribute evictShipped : Boolean = (true|false);", _read(DEPLOY))
    assert len(found) == 1, "deploy.sysml must declare evictShipped exactly once"
    return found[0] == "true"


def _satisfy_linked() -> bool:
    return re.search(SATISFY_LINE, _read(DEPLOY), re.M) is not None


def _xfail_mark() -> tuple[bool, bool | None]:
    """Whether the runtime module carries an xfail pytestmark, and its strict value."""
    for node in ast.parse(_read(RUNTIME)).body:
        if not (
            isinstance(node, ast.Assign)
            and any(isinstance(t, ast.Name) and t.id == "pytestmark" for t in node.targets)
        ):
            continue
        marks = node.value.elts if isinstance(node.value, ast.List) else [node.value]
        for mark in marks:
            if isinstance(mark, ast.Call) and ast.unparse(mark.func) == "pytest.mark.xfail":
                strict = next(
                    (ast.literal_eval(kw.value) for kw in mark.keywords if kw.arg == "strict"),
                    None,
                )
                return True, strict
    return False, None


def _status_guards() -> dict[str, list[bool]]:
    """Per MN-VER-05-S03..S09 def, the evictShipped value its status guard requires."""
    guards: dict[str, list[bool]] = {}
    for block in re.split(r"(?=verification def )", _read(VERIFY)):
        ver = re.search(r'attribute verificationId : String = "(MN-VER-05-S0\d)";', block)
        if ver and ver.group(1) in VER_IDS:
            found = re.findall(r"\.evictShipped\s*==\s*(true|false)", block)
            guards[ver.group(1)] = [v == "true" for v in found]
    return guards


def test_ship_flags_flip_together():
    shipped = _evict_shipped()
    linked = _satisfy_linked()
    has_xfail, strict = _xfail_mark()
    not_shipped = not shipped and not linked and has_xfail and strict is False
    shipped_ok = shipped and linked and (not has_xfail or strict is True)
    assert not_shipped or shipped_ok, (
        "evictShipped, the deploy satisfy link and the runtime xfail mark must flip together"
    )
    guards = _status_guards()
    assert set(guards) == set(VER_IDS), "every MN-VER-05-S03..S09 def must carry a status guard"
    for ver_id, values in guards.items():
        assert values == [shipped], f"{ver_id} evictShipped guard must match the deploy value"


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
