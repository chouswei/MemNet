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
            "Agent dialect: gated openCypher-shaped GQL only (docs/grammar/gql-wire-profile.md).",
            "Mutate: CREATE / MATCH…SET / MERGE / DELETE; live pin map emits shaped subgraph.",
            "Create with id: 'NEW'; engine mints ids. Patch/settle: known ids only (no NEW).",
            "Live pin map: memnet query pin-map --anchor <id> (query warm is legacy alias).",
            "Pin-map ingest: locators (path=, qname=, refdes=, skill_id=); no client NEW.",
            "Transport: MCP in-process first; serve --ipc (MEMNET_IPC_SOCKET); TCP fallback.",
            "Legacy @TAG pipe still accepted as import-once; Layer/Tier A retired from accept.",
            "MCP LawSeedHelper: GQL LAW01–LAW05 by default (pipe only to match pipe seed_lines).",
            "Reuse ids; never invent new ids for the same entity.",
            "Forward docs: docs/grammar/gql-wire-profile.md; ADR-001.",
        ]
        return "\n".join(f"- {b}" for b in bullets)
    return """MemNet - Net of Memory: in-memory NODE|EDGE working graph for LLM agents.

Doctrine:
  Agent wire = gated openCypher-shaped GQL only (gql-wire-profile.md)
  Live pin map = bounded shaped subgraph (query pin-map; query warm is legacy)
  Create with id: 'NEW'; pin-map ingest uses locators, not client NEW
  Transport: in-process MCP first; LocalIpc (MEMNET_IPC_SOCKET) or serve/TCP

Quick start (CLI sessions still need serve today):
  memnet serve                    # TCP :18765
  # or: export MEMNET_IPC_SOCKET=/tmp/memnet.sock && memnet serve --ipc
  memnet session open --map-file schema.example.txt
  memnet add --file workflow.example.txt   # GQL preferred; @TAG pipe import-once
  memnet query pin-map --anchor ...        # shaped GQL subgraph

GQL sketch:
  CREATE (:TSK {id: 'NEW', goal: 'Clear warehouse', status: 'in_progress'})
  MATCH (a {id: 'N03'}), (b {id: 'T42'})
  CREATE (a)-[:helps {id: 'NEW'}]->(b)
  # live pin map (emit): shaped present — no CREATE
  (:TSK {id: 'T42', goal: 'Clear warehouse', status: 'in_progress'})
  (:NPC {id: 'N03'})-[:helps {id: 'E77'}]->(:TSK {id: 'T42'})

TagMap maps (schema.*.example.txt) use shared-dialect SCHEMA lines for session_open.
Legacy @TAG: id|field pipe maps remain accepted on load. Not agent mutate dialect.
MCP LawSeedHelper defaults to GQL; pipe only when seed_lines are @TAG.
See: docs/grammar/gql-wire-profile.md, examples/README.md, README.md, memnet guide --loose
"""


def agent_guide_text() -> str:
    return (
        "Agent playbook pointer (British English docs in-repo).\n"
        "Forward dialect: docs/grammar/gql-wire-profile.md - GQL only, pin map, NEW vs locators.\n"
        "Operational loop: LLM-GUIDE.md "
        "(M3 body rewrite pending; prefer grammar when they conflict).\n"
        "Turn habit: query pin-map --anchor before inventing ids; mutate with GQL; reuse ids.\n"
        "See also: memnet guide, memnet guide --loose, README.md."
    )


def examples_map_text() -> str:
    lines = [
        "# Session maps for session_open --map-file (SCHEMA preferred; @TAG pipe accepted).",
        "# Not agent mutate — NODE|EDGE lives in workflow.*.example.txt and docs/grammar/.",
        "# Fixed tags (always present):",
    ]
    for tag, td in FIXED_TAGS.items():
        lines.append(f"SCHEMA {tag} ; fields={' '.join(td.fields)}")
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
    paths.append("(GQL wire: docs/grammar/gql-wire-profile.md; memnet examples agent-guide)")
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
