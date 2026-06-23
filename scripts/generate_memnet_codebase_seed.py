#!/usr/bin/env python3
"""Regenerate workflow.memnet-codebase.snap.txt from src/**/*.py via AST walk.

Top-level FunctionDef / AsyncFunctionDef / ClassDef nodes become @SYM rows; one
@MOD row per file. Private names (leading underscore) and dunder modules are
skipped to keep the snap focused on public surface.
"""

from __future__ import annotations

import ast
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
OUT = ROOT / "src" / "memnet" / "examples" / "workflow.memnet-codebase.snap.txt"


def mod_id(path: Path) -> str:
    rel = path.relative_to(ROOT).as_posix()
    return "MOD_" + rel.replace("/", "_").replace(".", "_")


def role_for(rel: str) -> str:
    return "mcp" if "_mcp" in rel else "engine"


def collect_symbols(path: Path) -> list[tuple[str, str, int, str]]:
    """Return (name, kind, lineno, signature) for top-level public defs/classes."""
    try:
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    except SyntaxError:
        return []
    out: list[tuple[str, str, int, str]] = []
    src_lines = path.read_text(encoding="utf-8").splitlines()
    for node in tree.body:
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            kind = "fn"
            name = node.name
        elif isinstance(node, ast.ClassDef):
            kind = "class"
            name = node.name
        else:
            continue
        if name.startswith("_"):
            continue
        sig_line = src_lines[node.lineno - 1] if node.lineno - 1 < len(src_lines) else ""
        sig = sig_line.strip().split(":", 1)[0][:40].replace("|", " ")
        out.append((name, kind, node.lineno, sig))
    return out


def main() -> None:
    head = [
        "@LAW: LAW-SNAP01|SYM|on_add|ast_first|ast_walk_top_level_def_class",
        "@LAW: LAW-SNAP02|MOD|on_add|one_per_file|one_mod_per_source_file",
        "@CFG: CFG01|MemNet|MOD_repo_root|0.2.16|memnet_codebase_snap",
        "@MOD: MOD_repo_root|.|MemNet repo root|active|persistent",
        "@TSK: TSK_codebase_snap_memnet|Full MemNet src index|MOD_repo_root|in_progress|persistent",
        "@USR: USR_snap_scope|scope|src public top-level defs only|active|persistent",
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
        role = role_for(rel)
        mods.append(f"@MOD: {mid}|{rel}|{path.name} {role}|active|persistent")
        edges.append(f"@EDG: E_own_{n}|TSK_codebase_snap_memnet|owns|{mid}|scope|persistent")
        n += 1
        for name, kind, lineno, sig in collect_symbols(path):
            sid = f"SYM_{mid[4:]}_{name}"[:60]
            syms.append(f"@SYM: {sid}|{name}|{kind}|{rel}|{lineno}|{sig}|active|persistent")
            edges.append(f"@EDG: E_def_{n}|{mid}|defines|{sid}|entry|persistent")
            n += 1
    OUT.write_text("\n".join(head + mods + syms + edges) + "\n", encoding="utf-8")
    print(f"{OUT}: {len(mods)} MOD, {len(syms)} SYM, {len(edges)} EDG")


if __name__ == "__main__":
    main()
