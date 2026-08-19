---
name: sysml-modeling-session-checklist
description: >-
  Short preflight before substantive SysML v2 modeling: MemNet warm, project context, plan-with-user, validate,
  outputs sync. Triggers: start modeling session, new chat, new project folder, batch .sysml edits, preflight
  checklist before sysml, memnet sysml.
metadata:
  pattern: pipeline
  domain: sysml-v2
  version: "1.2"
  pairs_with: [sysml-memnet-documentation, sysml-memnet-cache, sysml-modeling-workflow, project-planner, mcp-sysml-v2, mcp-sysmledgraph, mcp-memnet, sysml-view-doc-sync]
token_guardrails: |
  - **Thin:** run the checklist mentally or as bullets; do not paste long repo trees.
  - **MemNet first:** steps 0–1 before any `.sysml` Read (see sysml-memnet-read-policy.md).
  - **Model SSOT:** plan edits to `.sysml` first; commissioning / power-cycle / setup flows → behaviour + requirements (refine/derive), then outputs diagrams.
  - **After edits:** mcp-sysml-v2 validate; step 6 MemNet delta when structure changed.
  - Use project-planner in a separate turn for full requirements interview + roadmap.
---

system_instruction: |
  Prefer plain Markdown tables or domain wire; do not use TOON/TRON. JSON only at tool boundaries.


# SysML modeling session checklist

**Alias in [SKILL-GRAPH](../SKILL-GRAPH.md):** **smsc** (routing / edges — not a second skill).

**Not** a replacement for **[project-planner](../project-planner/SKILL.md)**. Use when you are about to **edit `.sysml`**.

## Output contract

After the checklist, state briefly:

- **project** — model root + short name (from repo `AGENTS.md` if present)
- **anchor** — `TSK_model_<short>`
- **warm** — `warm_hit` | `warm_miss` (if miss → initial snap)
- **read plan** — symbols from warm only; no full deploy read unless warm_miss
- **pipe** — `TSK_turn_*` id if serve up; else `serve_down`
- **next** — target file from `@SYM` if known, else which `models/*.sysml`
- **plan status** — agreed roadmap / **skipped** + one-line why

## Pipeline

0. **MemNet (steps 1–2)** — `serve_status`. If running: `pin_map(anchor=TSK_model_<short>, depth=2, max_rows=50)`. Session from `MEMNET_SESSION` or read **only** the header line of `AGENT-CONTEXT.md` (session id + anchor). On **warm_miss** → [initial snap](../sysml-memnet-documentation/references/sysml-memnet-snap.md#initial-snap-warm-miss-only). If serve down → note stale graph; skip warm.

1. **Project context** — Confirm model root (`sysml-v2-models/projects/<name>/` **or** repo `AGENTS.md` path such as `sysml-models/`), `config.yaml`, files to touch. **Read policy:** [sysml-memnet-read-policy.md](../sysml-memnet-documentation/references/sysml-memnet-read-policy.md) — no full deploy/AGENT-CONTEXT when warm hit. Submodules: edit in canonical repo if applicable (open repo root `AGENTS.md`).

2. **Plan-with-user** — Non-trivial / ambiguous work without agreed plan: stop and plan—or **project-planner** for documented roadmap. If user skipped planning, state in one line.

3. **Cross-file scope** — Large setups: **mcp-sysmledgraph** **indexDbGraph** / **impact** before wide renames.

4. **Modeling sequence** — requirements (prefer **refine** / **derive** under parents) → deploy / connections → behaviour (incl. commissioning / power-cycle when in scope) → satisfy / allocate → outputs + **`outputs/diagrams/`** ([sysml-modeling-workflow](../sysml-modeling-workflow/SKILL.md) 6-step turn). Model first; do not author architecture only in Markdown.

5. **After changes** — **Validate** (step 4); **sysml-view-doc-sync** if outputs (step 5); **MemNet delta + `@CLM` pipe settle** (step 6) unless comment-only or serve down. Optional: `python sysml-v2-models/scripts/exam_model.py --project <name>`.

**Hub:** [AGENTS.md](../../../AGENTS.md#agent-workflow) · **MemNet:** [sysml-memnet-snap.md](../sysml-memnet-documentation/references/sysml-memnet-snap.md) · **Read policy:** [sysml-memnet-read-policy.md](../sysml-memnet-documentation/references/sysml-memnet-read-policy.md)
