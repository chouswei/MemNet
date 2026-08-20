# SysML MemNet read policy — when to read `.sysml` vs `pin_map`

**Wire:** topology comes from shaped `pin_map` (GQL wire); `@PRT`/`@SYM` below mean label/id mnemonics, not pipe agent I/O.

**Problem:** Agents with MemNet still **re-read** `deploy*.sysml`, `requirements*.sysml`, and report sections every turn — duplicating work the graph already holds and burning context.

**Rule:** On the live **model root** (`sysml-v2-models/projects/<slug>/` **or** system-repo `sysml-models/`), **topology discovery = MemNet**; **syntax edit = narrow file window**; **full file read = last resort**.

Pair with [sysml-memnet-snap.md](sysml-memnet-snap.md) (6-step turn) and [sysml-memnet-pipeline.md](sysml-memnet-pipeline.md) (step wire).

---

## Three stores — who answers what

| Question | Ask first | Only if miss |
|----------|-----------|--------------|
| What parts exist? Who connects to whom? | `pin_map` → `@PRT` / `@CON` / `@EDG` | Grep `part ` in `deploy*.sysml` |
| Where is `linkFoo` / a named part? | `pin_map` → `@SYM_<name>` → `path` + `line` | `Grep` exact symbol in `models/` |
| What does requirement `REQ-*` satisfy? | `pin_map` → `@REQ_*` + `satisfies` EDGs | Read `root*.sysml` satisfy block (window) |
| What changed last session? | `pin_map(TSK_model_*)` + `<model-root>/.memnet/*.snap` load if session expired | Git diff (user asked or commit prep only) |
| Exact `connection` / `bind` / import syntax to patch? | Read **±15 lines** at `SYM.line` | Wider window only if the window misses |
| Load order / package imports broken? | `config.yaml` + validator errors | Read `root*.sysml` imports only |
| Human narrative for one report section? | Hub `index.md` + **one** `llm_toc[].file` | Other sections |

**MemNet is authoritative for structure between turns.** `.sysml` is authoritative for **syntax and satisfy links** at edit time. If MemNet MCP is missing: topology from `.sysml` / plain notes only (no TOON/TRON).

---

## Per-turn read budget (substantive modeling turn)

| Allowed | Typical limit |
|---------|----------------|
| Optional `serve_status` + `pin_map` | 1–2 calls (`TSK_model_*`, optional `@PRT_*` / `@CON_*`) |
| `Read` on `.sysml` | **≤2 files**, **≤40 lines each** (locator window around `@SYM.line`) |
| `Grep` on `models/` | **≤3** queries; scoped to one file when `@MOD` known |
| `Read` hub `index.md` | 1× (~80 lines) when touching reports |
| `Read` one report section | 1× the section file for the task topic only |

| **Forbidden** (unless user asks to audit whole file, or warm miss initial snap) |
|--------------------------------------------------------------------------------|
| `Read` entire `deploy*.sysml` (>80 lines) to “understand architecture” |
| Re-`Read` same deploy file every turn in a multi-turn thread |
| `Grep` whole project for names already in warm output |
| `Read` full `AGENT-CONTEXT.md` body for topology (header line only: session + anchor) |
| `Read` all report sections when one topic changed |
| Chat-summary / conversation memory instead of `pin_map` when MemNet is up |

---

## Decision tree (step 3 — locate before edit)

```
MemNet MCP in catalog?
  no → grep/read as needed; plain Markdown notes; skip MemNet write
serve_status (TCP / unsure only).running?
  false → grep/read as needed; note stale MemNet; skip step 6
  true / in-process → pin_map(TSK_model_<short>, depth=2)

Need symbol location?
  warm has @SYM_<name> with path+line?
    yes → Read(path, offset=line-12, limit=35)
    no  → Grep symbol in models/<file from @MOD_*>

Need connection endpoints?
  warm has @CON_<linkName>?
    yes → use ends from warm; open window on each @SYM if editing
    no  → Grep linkName in deploy + connections*.sysml

Need new part between existing parts?
  warm @PRT_* for neighbours → grep only the insertion region

Still ambiguous after warm + one grep?
  Grep scoped to the `:MOD` path (not full file read)
```

---

## Anti-patterns (do not repeat)

| Anti-pattern | Why wrong | Do instead |
|--------------|-----------|------------|
| Read `deploy*.sysml` at start of every user message | Graph already has `@PRT`/`@CON` | `pin_map` |
| Grep known part names across repo each turn | Redundant after delta push | Warm on the relevant `@PRT_*` / `@CON_*` |
| Read requirements + deploy + root before one link rename | Blast radius is in MemNet + sysmledgraph | Warm `@CON_*` + grep link name |
| Sync outputs by re-reading all of deploy | Report pipeline: warm + **one** section | [memnet-report-pipeline.md](../../system-design-report-generator/references/memnet-report-pipeline.md) M1–M3 |
| Skip MemNet write after multi-file session | Next turn forces full re-read | Step 6 delta + `session_save` / wire push |

---

## Multi-turn threads (conversation handoff)

When the user continues a design thread:

1. **Turn 2+:** `pin_map(TSK_model_*)` — **do not** re-ingest deploy from disk for facts already atomised.
2. If prior turn edited `.sysml` but **step 6 was skipped** → treat as **stale graph**: run **incremental delta** from git-diff symbols **before** warm, or grep changed ids only.
3. Store **settled decisions** as `@CLM` / `@DEC` so prose questions do not require re-read.

---

## `pin_map` prompts (copy patterns)

Use a **cue** (`kind` / `locators` / `keyword`), not leftover `anchor=` as law (`query_warm` is leftover alias):

| Task | Cue |
|------|-----|
| Project resume | `kind='TSK'`, locators `id=TSK_model_<short>` |
| Named subsystem | `PRT_*` / `CON_*` |
| Requirements | `REQ_*` |
| Named subsystem | rows for the relevant `PRT_*` / `CON_*` |
| Requirements touched | `REQ_*` + `satisfies` edges |
| Report section | `ART_<project>-design` + `@SEC` for section id |
| Locate edit | `@SYM_<linkOrPartName>` |

Increase `max_rows` (50→80) only when warm returns &lt;3 relevant rows **and** initial snap is known good.

---

## When full file read **is** allowed

| Case | Action |
|------|--------|
| **Initial snap** (warm miss, greenfield) | Grep-by-role per [sysml-memnet-snap.md](sysml-memnet-snap.md) §Initial snap — not blind `Read` entire file |
| **User:** “audit deploy file” / “review whole model” | Full read permitted |
| **Import-order diagnosis** | `sysml-import-order-helper` — targeted files from validate errors |
| **Refactor blast radius** | `mcp-sysmledgraph` first; full deploy only if graph unavailable |
| **Common lib edit** (`libs/common/` or pack equivalent) | No project `@TSK` — grep/read lib file; optional `MOD_*` in MemNet if seeded |

---

## After edit (mandatory — prevents next-turn re-read)

1. Validate the textual model
2. MemNet delta: new/changed PRT/POR/CON/REQ + SYM + rels
3. Re-grep touched MOD → `mutate` SET all `SYM.line` in that file
4. If ≥3 structural changes or end of session: `session_save` → `<model-root>/.memnet/<short>.snap` or wire push

**Stale graph is the main cause of repeated SysML reads.** Step 6 is not optional for structural edits.

---

## Specialist skills

Any `sysml-*` generator/refactorer/audit skill **MUST**:

1. Delegate **discovery** to `pin_map` (this policy) when MemNet MCP is available
2. Delegate **turn order** to [sysml-modeling-workflow](../../sysml-modeling-workflow/SKILL.md)
3. Run **step 6** before ending the turn when structure changed

---

## Quick self-check (before opening another `.sysml` file)

Answer **yes** to at least one, or stop and warm:

- [ ] MemNet MCP present (or explicitly skipped as down)?
- [ ] `pin_map` run for this task’s anchor when MemNet is up?
- [ ] I have `@SYM.line` for the symbol I will edit?
- [ ] This read is ≤40 lines or validate-error-targeted?
- [ ] I am not re-fetching facts already in warm output?
