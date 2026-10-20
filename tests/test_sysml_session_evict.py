"""MN-REQ-05.5 model presence: the SysML cites runtime tests (proposed, not shipped).

Runtime behaviour lives in tests/test_session_evict.py. This file only checks
that the model points at those tests, that every cited test exists, that the
runtime module stays xfail until the engine ships, and that the READ-SURFACES,
NON-TOUCH-READS and MAINTENANCE-SAVES blocks match the shared surface lists in
tests/evict_surfaces.py and cover every registered MCP tool and every
session-scoped CLI command in cli.py. It makes no claim that a flag is true.
"""

from __future__ import annotations

import ast
import asyncio
import re
from pathlib import Path

import test_read_touch_regression as read_touch
from evict_surfaces import (
    CLI_ONLY_NON_READ,
    CLI_READ_ARGV,
    CLI_SURFACE_ALIAS,
    ENGINE_SAVES,
    MAINTENANCE_SAVES,
    MCP_NON_READ_TOOLS,
    NON_TOUCH_READS,
    READ_SURFACES,
)
from test_read_touch_regression import SURFACE_PARAMS

ROOT = Path(__file__).resolve().parents[1]
MODELS = ROOT / "sysml-models" / "models"
README = ROOT / "sysml-models" / "README.md"
DEPLOY = MODELS / "deploy.sysml"
REQ = MODELS / "requirements.sysml"
VERIFY = MODELS / "verify.sysml"
BEHAVIOUR = MODELS / "behaviour.sysml"
RUNTIME = ROOT / "tests" / "test_session_evict.py"
READ_TOUCH = ROOT / "tests" / "test_read_touch_regression.py"
# Runtime files a verify doc may cite a test from; the path itself is not a test name.
RUNTIME_FILES = ("tests/test_session_evict.py", "tests/test_read_touch_regression.py")
CLI = ROOT / "parts" / "common" / "memnet" / "memnet" / "cli.py"
VER_IDS = [f"MN-VER-05-S0{n}" for n in range(3, 10)]
SATISFY_LINE = (
    r"^\s*satisfy\s+MN_REQ_00_MissionBridge::MN_REQ_05_HardCaps::MN_REQ_05_5_SessionCapEvictLru\s*;"
)
# A session-scoped CLI parameter names a session by one of these names, or by a
# typer long option whose name is one of them (or contains "session"), e.g. --session.
SESSION_PARAM_NAMES = frozenset({"session", "session_id", "sid", "sess", "target"})


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
    """Test names cited in a doc, ignoring the runtime file paths themselves."""
    for path in RUNTIME_FILES:
        doc = doc.replace(path, "")
    return set(re.findall(r"\btest_\w+", doc))


def _runtime_test_names(path: Path = RUNTIME) -> set[str]:
    tree = ast.parse(_read(path))
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
    names = _runtime_test_names() | _runtime_test_names(READ_TOUCH)
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
    # Read-touch tests are cited too, but only the session-evict file must be fully cited here.
    assert _runtime_test_names() == cited - _runtime_test_names(READ_TOUCH)


def _deploy_flag(name: str) -> bool:
    found = re.findall(rf"attribute {name} : Boolean = (true|false);", _read(DEPLOY))
    assert len(found) == 1, f"deploy.sysml must declare {name} exactly once"
    return found[0] == "true"


def _evict_shipped() -> bool:
    return _deploy_flag("evictShipped")


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


def _get_session_xfail_marks() -> list:
    """The xfail marks on the get_session parameter of the read-touch regression test."""
    (param,) = [p for p in SURFACE_PARAMS if p.values[0] == "get_session"]
    return [m for m in param.marks if m.name == "xfail"]


def _open_stamps_xfail_marks() -> list:
    """The xfail marks on test_open_stamps_first_touch in the read-touch regression module."""
    test = read_touch.test_open_stamps_first_touch
    return [m for m in getattr(test, "pytestmark", []) if m.name == "xfail"]


def _status_guards(flag: str = "evictShipped") -> dict[str, list[bool]]:
    """Per MN-VER-05-S03..S09 def, the value of ``flag`` its status guard requires."""
    guards: dict[str, list[bool]] = {}
    for block in re.split(r"(?=verification def )", _read(VERIFY)):
        ver = re.search(r'attribute verificationId : String = "(MN-VER-05-S0\d)";', block)
        if ver and ver.group(1) in VER_IDS:
            found = re.findall(rf"\.{flag}\s*==\s*(true|false)", block)
            if found:
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
    get_marks = _get_session_xfail_marks()
    if shipped:
        assert not get_marks, "get_session read param must drop its xfail mark when the rule ships"
    else:
        assert len(get_marks) == 1 and get_marks[0].kwargs.get("strict") is True, (
            "get_session read param must stay xfail(strict=True) until the touch rule ships"
        )
    open_marks = _open_stamps_xfail_marks()
    if shipped:
        assert not open_marks, (
            "test_open_stamps_first_touch must drop its xfail mark when the rule ships"
        )
    else:
        assert len(open_marks) == 1 and open_marks[0].kwargs.get("strict") is True, (
            "test_open_stamps_first_touch must stay xfail(strict=True) until the touch rule ships"
        )
    assert _deploy_flag("commitRefusesLostLease") == shipped, (
        "commitRefusesLostLease must flip with evictShipped (both false now, both true at ship)"
    )
    guards = _status_guards()
    assert set(guards) == set(VER_IDS), "every MN-VER-05-S03..S09 def must carry a status guard"
    for ver_id, values in guards.items():
        assert values == [shipped], f"{ver_id} evictShipped guard must match the deploy value"
    lost_lease = _status_guards("commitRefusesLostLease")
    assert lost_lease == {"MN-VER-05-S09": [shipped]}, (
        "MN-VER-05-S09 must guard commitRefusesLostLease against the deploy value"
    )


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


def _block_names(text: str, name: str) -> list[str]:
    """Surface names between ``<name>-BEGIN`` and ``<name>-END``, one per line."""
    begin, end = f"{name}-BEGIN", f"{name}-END"
    assert text.count(begin) == 1, f"{begin} must appear exactly once in requirements.sysml"
    assert text.count(end) == 1, f"{end} must appear exactly once in requirements.sysml"
    body = text.split(begin, 1)[1].split(end, 1)[0]
    return [line.strip() for line in body.splitlines() if line.strip()]


def test_surface_blocks_match_shared_constants():
    text = _read(REQ)
    for block, names in (
        ("READ-SURFACES", READ_SURFACES),
        ("NON-TOUCH-READS", NON_TOUCH_READS),
        ("MAINTENANCE-SAVES", MAINTENANCE_SAVES),
    ):
        listed = _block_names(text, block)
        assert len(listed) == len(set(listed)), f"{block} must not repeat a surface"
        assert set(listed) == set(names), f"{block} must equal its tests/evict_surfaces.py list"


def test_surface_lists_are_disjoint():
    reads, nontouch, saves = set(READ_SURFACES), set(NON_TOUCH_READS), set(MAINTENANCE_SAVES)
    assert not (reads & nontouch), "a read cannot be both a touch and a non-touch read"
    assert not (saves & (reads | nontouch)), "a save is neither a read surface nor a read"


def test_every_caller_mcp_read_tool_is_listed():
    from memnet.cli import admin_app
    from memnet_mcp.server import mcp

    registered = {t.name for t in asyncio.run(mcp.list_tools())}
    reads = set(READ_SURFACES)
    nontouch = set(NON_TOUCH_READS)
    cli_only = set(CLI_READ_ARGV)
    assert MCP_NON_READ_TOOLS <= registered, "MCP_NON_READ_TOOLS names an unregistered tool"
    assert not (reads & MCP_NON_READ_TOOLS), "a READ_SURFACES entry must not be a non-read tool"
    assert not (nontouch & MCP_NON_READ_TOOLS), "a NON_TOUCH_READS entry must not be a non-read"
    unlisted = registered - MCP_NON_READ_TOOLS - reads - nontouch
    assert not unlisted, f"classify these MCP tools as read or non-read: {sorted(unlisted)}"
    # get_session is the in-process read; CLI_READ_ARGV names the CLI-only reads;
    # every other READ entry is an MCP tool.
    mcp_reads = reads - {"get_session"} - cli_only
    assert mcp_reads <= registered, "a READ_SURFACES MCP name is not registered"
    # Non-touch entries that are not MCP tools must be real `memnet admin` commands.
    admin_cmds = {"admin_" + c.name.replace("-", "_") for c in admin_app.registered_commands}
    assert (nontouch - registered) <= admin_cmds, "NON_TOUCH_READS names an absent command"
    # Maintenance saves that are not MCP tools or admin commands must be engine saves.
    saves_unknown = set(MAINTENANCE_SAVES) - registered - admin_cmds - ENGINE_SAVES
    assert not saves_unknown, (
        f"MAINTENANCE_SAVES names no tool, command or engine save: {saves_unknown}"
    )
    assert ENGINE_SAVES <= set(MAINTENANCE_SAVES), "ENGINE_SAVES must be maintenance saves"


def _session_named(name: str) -> bool:
    return name in SESSION_PARAM_NAMES or "session" in name


def _session_param(arg: ast.arg, default: ast.expr | None) -> bool:
    """A typer parameter that names a session: by its own name, or by a long option."""
    if _session_named(arg.arg):
        return True
    for expr in (arg.annotation, default):
        if expr is None:
            continue
        for node in ast.walk(expr):
            if (
                isinstance(node, ast.Constant)
                and isinstance(node.value, str)
                and node.value.startswith("--")
                and _session_named(node.value[2:].replace("-", "_"))
            ):
                return True
    return False


def _signature_params(fn: ast.FunctionDef) -> list[tuple[ast.arg, ast.expr | None]]:
    """Positional and keyword-only parameters, each with its default (or None)."""
    pos = fn.args.args
    pos_defaults = [None] * (len(pos) - len(fn.args.defaults)) + list(fn.args.defaults)
    kw_defaults = fn.args.kw_defaults
    return list(zip(pos, pos_defaults, strict=True)) + list(
        zip(fn.args.kwonlyargs, kw_defaults, strict=True)
    )


def _session_commands_in(source: str) -> dict[str, str]:
    """CLI function name -> surface name, for each session-scoped typer command in source.

    cli.py registers commands with typer (``@<app>.command(...)``), not argparse.
    A command is session-scoped when one of its parameters names a session.
    """
    found: dict[str, str] = {}
    for node in ast.parse(source).body:
        if not isinstance(node, ast.FunctionDef):
            continue
        is_command = any(
            isinstance(d, ast.Call)
            and isinstance(d.func, ast.Attribute)
            and d.func.attr == "command"
            for d in node.decorator_list
        )
        if is_command and any(_session_param(a, d) for a, d in _signature_params(node)):
            found[node.name] = CLI_SURFACE_ALIAS.get(node.name, node.name)
    return found


def _cli_session_commands() -> dict[str, str]:
    return _session_commands_in(_read(CLI))


_CLASSIFIER_SNIPPET = """
@app.command()
def by_keyword(*, sid: Annotated[str, typer.Option("--ident")] = ""): ...

@app.command()
def by_option(name: Annotated[str, typer.Option("--session")] = ""): ...

@app.command()
def by_target(*, target: str): ...

@app.command()
def unrelated(*, count: int = 0): ...

def helper(session: str): ...
"""


def test_session_classifier_sees_keyword_only_and_aliased_params():
    found = _session_commands_in(_CLASSIFIER_SNIPPET)
    assert set(found) == {"by_keyword", "by_option", "by_target"}, (
        "keyword-only sid, a --session option under another name, and target must all count; "
        "a non-command helper and an unrelated keyword must not"
    )


def test_every_cli_session_command_is_classified():
    from memnet_mcp.server import mcp

    registered = {t.name for t in asyncio.run(mcp.list_tools())}
    reads = set(READ_SURFACES)
    nontouch = set(NON_TOUCH_READS)
    saves = set(MAINTENANCE_SAVES)
    cli_only = set(CLI_READ_ARGV)
    commands = _cli_session_commands()
    assert commands, "no session-scoped CLI command found in cli.py; the parser has moved"
    classified = reads | nontouch | saves | MCP_NON_READ_TOOLS | CLI_ONLY_NON_READ
    unclassified = sorted(f for f, surface in commands.items() if surface not in classified)
    assert not unclassified, (
        f"classify these session-scoped CLI commands as read, non-touch read, save or non-read: "
        f"{unclassified}"
    )
    # Every CLI-only read must be a real session-scoped command, and every read
    # that is not an MCP tool must be a CLI-only read with its argv.
    surfaces = set(commands.values())
    assert cli_only <= surfaces, "CLI_READ_ARGV names a command absent from cli.py"
    assert (reads - {"get_session"} - registered) == cli_only, (
        "a READ_SURFACES entry that is not an MCP tool must be in CLI_READ_ARGV"
    )


def test_no_lease_carried_wording_anywhere_in_models():
    everything = "\n".join(_read(p) for p in MODELS.glob("*.sysml")) + _read(README)
    assert "evictKeepsAclLease" not in everything
    assert "same ACL and lease" not in everything
