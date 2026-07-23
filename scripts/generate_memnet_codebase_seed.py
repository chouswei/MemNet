#!/usr/bin/env python3
"""Regenerate workflow.memnet-codebase.snap.txt from published packages via AST walk.

Top-level FunctionDef / AsyncFunctionDef / ClassDef nodes become @SYM rows; one
@MOD row per file. Private names (leading underscore) and dunder modules are
skipped to keep the snap focused on public surface.
"""

from __future__ import annotations

import ast
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCAN_ROOTS = (
    ROOT / "parts" / "common" / "memnet" / "memnet",
    ROOT / "parts" / "memnet-mcp" / "software" / "memnet_mcp",
)
OUT = ROOT / "parts" / "common" / "memnet" / "memnet" / "examples" / "workflow.memnet-codebase.snap.txt"


def mod_id(path: Path) -> str:
    rel = path.relative_to(ROOT).as_posix()
    return "MOD_" + rel.replace("/", "_").replace(".", "_")


def role_for(rel: str) -> str:
    if "memnet_mcp" in rel:
        return "mcp"
    return "engine"


def iter_python_files() -> list[Path]:
    seen: set[Path] = set()
    out: list[Path] = []
    for root in SCAN_ROOTS:
        if not root.is_dir():
            continue
        for path in sorted(root.rglob("*.py")):
            resolved = path.resolve()
            if resolved in seen:
                continue
            seen.add(resolved)
            out.append(path)
    return out


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
        elif isinstance(node, (ast.ClassDef)):
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
    ]
    mods: list[str] = []
    syms: list[str] = []
    edges: list[str] = []
    ei = 1
    for path in iter_python_files():
        mid = mod_id(path)
        rel = path.relative_to(ROOT).as_posix()
        role = role_for(rel)
        mods.append(f"@MOD: {mid}|{rel}|{path.name}|{role}|active|persistent")
        for name, kind, lineno, sig in collect_symbols(path):
            sid = f"SYM_{mid}_{name}"
            syms.append(f"@SYM: {sid}|{name}|{kind}|{lineno}|{sig}|active|persistent")
            edges.append(f"@EDG: E{ei:04d}|{mid}|defines|{sid}|ast|persistent")
            ei += 1
    lines = head + mods + syms + edges
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"wrote {OUT} ({len(mods)} mods, {len(syms)} syms)")


if __name__ == "__main__":
    main()
