"""Static guides and example text."""

from __future__ import annotations

from pathlib import Path

from memnet.config import examples_dir
from memnet.fixed_tags import FIXED_TAGS
from memnet.tag_map import example_ingest_line, load_map_from_file

REFERENCE_FIELDS: dict[str, str] = {
    "CFG": "id|world|economy|identity|core_ability|crisis",
    "SYS": "id|round|time|deficit|revenue|chaos|exchange_rate",
    "PLR": "id|identity|wealth|cashflow|monopoly|reputation|inventory",
    "BIZ": "id|name|type|location|profit|cashflow|employees|recycle",
    "NPC": "id|name|traits|corruption|craft|funding_gap|status|recycle",
    "TSK": "id|goal|deadline|status|recycle",
    "TEC": "id|name|domain|status|effect",
    "PRD": "id|name|type|cost|price|status",
    "EDG": "id|src|relation|dist|attrs|recycle",
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
            "Wire line: @TAG: field|field|... — quote the whole line in shell.",
            "Pipe inside a value: use backslash pipe \\| not bare |.",
            "Start server: memnet serve (one terminal).",
            "Open once: memnet session open --map-file schema.txt; export MEMNET_SESSION.",
            "Resume: memnet session resume <id> — never re-open for same task.",
            "New rows: memnet add --stdin or --file. Changes: memnet update --stdin or --file.",
            "Read turn: memnet query warm --anchor PLR01 (not query context).",
            "Structure: memnet query walk --anchor PLR01 → @WALK: src -[rel]-> dst hops.",
            "Optional: memnet session save --file snap.txt / session load --file snap.txt.",
            "Reuse ids; never invent new ids for the same entity.",
            "Read LLM-GUIDE.md (in the repo) for the full agent playbook and settlement rules.",
            "Example: @PLR: PLR01|Beggar|3|-5|0|0|cake",
        ]
        return "\n".join(f"- {b}" for b in bullets)
    return """MemNet — in-memory working-memory graph for LLM agents (goldfish brain).

Quick start:
  memnet serve
  memnet examples map
  memnet session open --map-file schema.example.txt
  memnet add --file workflow.example.txt
  memnet query warm --anchor PLR01
  memnet query walk --anchor PLR01

Wire format: @TAG: field|field|...
  Pipe in value: a\\|b
  Errors: @ERR: code|message|example on stderr

Shell (PowerShell): memnet add \"@NPC: N01|Alice|...\"
Shell (bash):       memnet add '@NPC: N01|Alice|...'
  Update existing:  memnet update '@NPC: N01|Alice|...'

See: memnet tagmap fields --tag NPC
     memnet guide --loose
     LLM-GUIDE.md (repo root) for the complete LLM/agent instructions
"""


def examples_map_text() -> str:
    lines = ["# Fixed tags (always present)"]
    for tag, td in FIXED_TAGS.items():
        lines.append(f"@{tag}: {'|'.join(td.fields)}")
    lines.append("")
    lines.append("# Reference user tags")
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
    paths.append("(LLM-GUIDE.md lives at repository root — run 'memnet examples agent-guide' for the pointer)")
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
