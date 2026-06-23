#!/usr/bin/env python3
"""Regenerate workflow.memnet-codebase.snap.txt from src/**/*.py (grep-verified symbols)."""

from __future__ import annotations

import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
OUT = ROOT / "src" / "memnet" / "examples" / "workflow.memnet-codebase.snap.txt"

KEY_PATTERNS: list[tuple[str, str]] = [
    (r"^def main\b", "fn"),
    (r"^async def serve_status\b", "fn"),
    (r"^async def session_open\b", "fn"),
    (r"^async def session_load\b", "fn"),
    (r"^async def session_save\b", "fn"),
    (r"^async def query_warm\b", "fn"),
    (r"^async def add\b", "fn"),
    (r"^async def update\b", "fn"),
    (r"^def run_memnet\b", "fn"),
    (r"^def open_session\b", "fn"),
    (r"^def get_session\b", "fn"),
    (r"^def close_session\b", "fn"),
    (r"^def resolve_session_id\b", "fn"),
    (r"^def run_serve\b", "fn"),
    (r"^def send_command\b", "fn"),
    (r"^def probe\b", "fn"),
    (r"^def parse_line\b", "fn"),
    (r"^def load_map_from_lines\b", "fn"),
    (r"^def parse_tag_line\b", "fn"),
    (r"^def split_payload\b", "fn"),
    (r"^def write_snapshot\b", "fn"),
    (r"^def load_snapshot\b", "fn"),
    (r"^def snapshot_text\b", "fn"),
    (r"^def supplement_seed_lines\b", "fn"),
    (r"^def emit_record\b", "fn"),
    (r"^def emit_wrn\b", "fn"),
    (r"^def emit_session\b", "fn"),
    (r"^def emit_err\b", "fn"),
    (r"^def format_err\b", "fn"),
    (r"^def stats\b", "fn"),
    (r"^def prune_stale\b", "fn"),
    (r"^def stale_rows\b", "fn"),
    (r"^def recyclable_rows\b", "fn"),
    (r"^def register\b", "fn"),
    (r"^def get\b", "fn"),
    (r"^def remove\b", "fn"),
    (r"^def purge_before\b", "fn"),
    (r"^def purge_expired\b", "fn"),
    (r"^def emit_cap_warnings\b", "fn"),
    (r"^def emit_session_warnings\b", "fn"),
    (r"^def record_matches\b", "fn"),
    (r"^def sanitise_batch\b", "fn"),
    (r"^def dispatch\b", "fn"),
    (r"^def extract_session_id\b", "fn"),
    (r"^def extract_errors\b", "fn"),
    (r"^def fixed_tag_map\b", "fn"),
    (r"^def guide_text\b", "fn"),
    (r"^class MemStore\b", "class"),
    (r"^class SessionStore\b", "class"),
    (r"^class SessionEntry\b", "class"),
    (r"^class Caps\b", "class"),
    (r"^class TagDef\b", "class"),
    (r"^class TagMap\b", "class"),
    (r"^class Record\b", "class"),
    (r"^class SessionMeta\b", "class"),
    (r"^class MemNetError\b", "class"),
    (r"^class MemNetResponse\b", "class"),
    (r"^async def prose_metrics\b", "fn"),
    (r"^async def chapter_prose_gate\b", "fn"),
    (r"^async def chapter_prose_append\b", "fn"),
    (r"^def query_warm\b", "fn"),
    (r"^def session_save\b", "fn"),
    (r"^def session_load\b", "fn"),
    (r"^def session_open\b", "fn"),
    (r"^def add_cmd\b", "fn"),
    (r"^def update_cmd\b", "fn"),
    (r"^def housekeep_stats\b", "fn"),
    (r"^def chapter_prose_gate\b", "fn"),
    (r"^def chapter_prose_append\b", "fn"),
    (r"^def count_zh_chars\b", "fn"),
    (r"^def prose_status\b", "fn"),
]


def mod_id(path: Path) -> str:
    rel = path.relative_to(ROOT).as_posix()
    return "MOD_" + rel.replace("/", "_").replace(".", "_")


def main() -> None:
    lines = [
        "@LAW: LAW-SNAP01|SYM|on_add|verify_first|grep_before_sym_row",
        "@LAW: LAW-SNAP02|MOD|on_add|one_per_file|one_mod_per_source_file",
        "@CFG: CFG01|MemNet|MOD_repo_root|0.2.16|memnet_codebase_snap",
        "@MOD: MOD_repo_root|.|MemNet repo root|active|persistent",
        "@TSK: TSK_codebase_snap_memnet|Full MemNet src index|MOD_repo_root|in_progress|persistent",
        "@USR: USR_snap_scope|scope|src key entrypoints light snap|active|persistent",
    ]
    mods: list[str] = []
    syms: list[str] = []
    edges: list[str] = [
        "@EDG: E_tsk_root|TSK_codebase_snap_memnet|owns|MOD_repo_root|scope|persistent",
        "@EDG: E_tsk_usr|TSK_codebase_snap_memnet|constrained_by|USR_snap_scope|light_snap|persistent",
    ]
    n = 1
    for path in sorted(SRC.rglob("*.py")):
        rel = path.relative_to(ROOT).as_posix()
        mid = mod_id(path)
        role = "mcp" if "mcp" in rel else "engine"
        mods.append(f"@MOD: {mid}|{rel}|{path.name} {role}|active|persistent")
        edges.append(f"@EDG: E_own_{n}|TSK_codebase_snap_memnet|owns|{mid}|scope|persistent")
        n += 1
        seen: set[tuple[str, str]] = set()
        for i, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
            for pat, kind in KEY_PATTERNS:
                if not re.match(pat, line):
                    continue
                m = re.search(r"(?:async def|def|class)\s+(\w+)", line)
                if not m:
                    break
                name = m.group(1)
                key = (mid, name)
                if key in seen:
                    break
                seen.add(key)
                sid = f"SYM_{mid[4:]}_{name}"[:60]
                sig = line.strip()[:40].replace("|", " ")
                syms.append(f"@SYM: {sid}|{name}|{kind}|{rel}|{i}|{sig}|active|persistent")
                edges.append(f"@EDG: E_def_{n}|{mid}|defines|{sid}|entry|persistent")
                n += 1
                break
    OUT.write_text("\n".join(lines + mods + syms + edges) + "\n", encoding="utf-8")
    print(f"{OUT}: {len(mods)} MOD, {len(syms)} SYM, {len(edges)} EDG")


if __name__ == "__main__":
    main()
