"""Static guides and example text."""

from __future__ import annotations

from memnet.config import examples_dir
from memnet.fixed_tags import FIXED_TAGS
from memnet.tag_map import example_ingest_line, load_map_from_file

# Legacy pipe field orders for tagmap/examples commands (not the agent dialect).
REFERENCE_FIELDS: dict[str, str] = {
    "CFG": "id|world|economy|identity|core_ability|crisis",
    "SYS": "id|round|time|deficit|revenue|chaos|exchange_rate",
    "PLR": "id|identity|wealth|cashflow|monopoly|reputation|inventory",
    "BIZ": "id|name|type|location|profit|cashflow|employees|recycle",
    "NPC": "id|name|traits|corruption|craft|funding_gap|status|recycle",
    "TSK": "id|goal|deadline|status|recycle",
    "TEC": "id|name|domain|status|effect",
    "PRD": "id|name|type|cost|price|status",
    "EDG": "id|src|relation|dist|at|attrs|recycle",
    "LAW": "id|name|cycle|mechanism|constraint",
}

ADD_SAMPLES: dict[str, str] = {
    "BIZ": "@BIZ: B01|Unfound|none|none|0|0|0|persistent",
    "NPC": "@NPC: N01|Shen Tiexin|female(12)|0|traditional|80|active|persistent",
    "PLR": "@PLR: PLR01|Vagrant beggar|3|-5|0|0|wheat cake",
    "EDG": "@EDG: E01|N01|seeks_help|PLR01|unlock|delete_on_expire",
}


def guide_text(*, loose: bool = False) -> str:
    if loose:
        bullets = [
            "MemNet (Net of Memory): in-memory NODE|EDGE working graph for agents.",
            "Agent dialect: Tier A NODE|EDGE shapes; mutate uses +/~/-; live pin map is bare present (no ops).",
            "Create with [NEW]; engine mints ids. Patch/settle: known ids only (no NEW).",
            "Live pin map: memnet query warm --anchor <id> (legacy name; bounded ego digest).",
            "Pin-map ingest: stable locators (path=, qname=, ...) - no client NEW for those pins.",
            "Transport: MCP in-process first; memnet serve / TCP is migration fallback.",
            "Legacy: @TAG pipe still accepted on add/update; snapshots and read may be pipe.",
            "MCP LawSeedHelper: Tier A LAW01–LAW05 by default (pipe only to match pipe seed_lines).",
            "Reuse ids; never invent new ids for the same entity.",
            "Forward docs: docs/grammar/. LLM-GUIDE.md is still partly pipe-era.",
        ]
        return "\n".join(f"- {b}" for b in bullets)
    return """MemNet - Net of Memory: in-memory NODE|EDGE working graph for LLM agents.

Doctrine:
  Tier A: mutate uses +/~/-; live pin map emits bare present lines (no ops)
  Live pin map = bounded ego digest (query warm is a legacy alias)
  Create with NEW; pin-map ingest uses locators, not client NEW
  Transport: in-process MCP first; serve/TCP as fallback

Quick start (CLI sessions still need serve today):
  memnet serve
  memnet session open --map-file schema.example.txt
  memnet add --file workflow.example.txt   # Tier A preferred; @TAG pipe still accepted
  memnet query warm --anchor ...           # live pin map (legacy command name)

Tier A sketch:
  + TSK [NEW] ; goal=Clear warehouse ; status=in_progress ; recycle=persistent
  + E77 [N03] --(helps)--> [T42] ; recycle=persistent
  # live pin map (emit): bare — no leading +
  TSK [T42] ; goal=Clear warehouse ; status=in_progress ; recycle=persistent
  E77 [N03] --(helps)--> [T42] ; recycle=persistent

TagMap maps (schema.*.example.txt) are pipe field defs for session_open — not agent dialect.
MCP LawSeedHelper defaults to Tier A; pipe only when seed_lines are @TAG.
See: docs/grammar/, examples/README.md, README.md, memnet guide --loose
"""


def agent_guide_text() -> str:
    return (
        "Agent playbook pointer (British English docs in-repo).\n"
        "Forward dialect: docs/grammar/ - Tier A, pin map, NEW vs locators.\n"
        "Operational loop: LLM-GUIDE.md (still partly pipe-era; prefer grammar when they conflict).\n"
        "Turn habit: query warm --anchor before inventing ids; mutate with Tier A; reuse ids.\n"
        "See also: memnet guide, memnet guide --loose, README.md."
    )


def examples_map_text() -> str:
    lines = [
        "# TagMap field maps for session_open --map-file (pipe @TAG: fields).",
        "# Not agent mutate — Tier A lives in workflow.*.example.txt and docs/grammar/.",
        "# Fixed tags (always present):",
    ]
    for tag, td in FIXED_TAGS.items():
        lines.append(f"@{tag}: {'|'.join(td.fields)}")
    lines.append("")
    lines.append("# Reference user tags (schema.example.txt)")
    schema = examples_dir() / "schema.example.txt"
    if schema.exists():
        lines.extend(schema.read_text(encoding="utf-8").splitlines())
    return "\n".join(lines)


def examples_workflow_text() -> str:
    wf = examples_dir() / "workflow.example.txt"
    if wf.exists():
        return wf.read_text(encoding="utf-8")
    return ""


def examples_path_text() -> str:
    d = examples_dir()
    paths = [str(p) for p in sorted(d.glob("*.txt"))]
    readme = d / "README.md"
    if readme.exists():
        paths.append(str(readme))
    paths.append(
        "(Tier A fixtures: docs/grammar/examples/; memnet examples agent-guide)"
    )
    return "\n".join(paths)


def fields_text(tag: str | None = None) -> str:
    if tag:
        t = tag.upper()
        if t in REFERENCE_FIELDS:
            return f"@{t}: {REFERENCE_FIELDS[t]}"
        return f"unknown reference tag {t}"
    lines = [f"@{t}: {fields}" for t, fields in sorted(REFERENCE_FIELDS.items())]
    return "\n".join(lines)


def add_example_text(tag: str) -> str:
    t = tag.upper()
    if t in ADD_SAMPLES:
        return ADD_SAMPLES[t]
    schema = examples_dir() / "schema.example.txt"
    if schema.exists():
        tm = load_map_from_file(str(schema))
        td = tm.get(t)
        if td:
            return example_ingest_line(td)
    return f"@TAG: no sample for {t}"
