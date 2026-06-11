# MemNet — Agent Playbook (for LLMs)

**You are a goldfish.** Your working memory is unreliable. Use MemNet as external structured scratch space so you do not have to hold state in your context.

**Core contract**
- Everything you need for the current task lives in the MemNet graph for this session.
- You **add** new facts, tasks, and relations once; you **update** them when something changes.
- You re-inject only the live slice on each turn via `query warm`.
- When a sub-task is done, you explicitly "settle" it so it disappears from future warm reads.
- You clean up when appropriate.
- You never rely on your own previous messages for durable state.

**One non-negotiable rule**
> **Always read with `query warm --anchor <something>` (or `read list --active-only`). Never use bare `query context` for normal turns.**

**MCP alternative (optional):** If your host supports MCP, install `memnet-llm[mcp]`, run `memnet serve`, then register `memnet-mcp` with `MEMNET_SESSION` set. Use the `query_warm`, `add`, and `update` tools instead of shelling `memnet` — same wire output, structured JSON envelope. Production use requires `memnet serve`; do not rely on `MEMNET_TEST_INLINE`.

---

## Add vs update — pick the right command

MemNet splits create and replace so mistakes fail loudly:

| Intent | Command | If you get it wrong |
|--------|---------|---------------------|
| **New** entity / edge | `add` | `id_exists` — id already taken; use `update` |
| **Change** existing row | `update` | `not_found` — typo or wrong id; fix id or use `add` |

**Rules**
- Copy ids from `query warm` output — never retype from memory.
- New NPC / task / edge → `add` with a **new** id.
- Status change, settlement, field edit → `update` with the **same** id from warm.
- Unsure? `read get --id N01` first.

There is no `write` command. Do not upsert implicitly.

---

## The Goldfish Loop (do this every turn)

1. **Think** what you need to remember or act on.
2. **Mutate** (batch preferred):
   ```powershell
   memnet add --stdin @"
   @TSK: T42|Clear the warehouse|2|in_progress|persistent
   @EDG: E77|N03|helps|T42|labour|persistent
   "@
   ```
   Or, if rows already exist from a prior turn:
   ```powershell
   memnet update --stdin @"
   @TSK: T42|Clear the warehouse|2|in_progress|persistent
   "@
   ```
3. **Read the live slice** (always anchored, always warm):
   ```powershell
   memnet query warm --anchor T42 --depth 2
   ```
   Paste the `@TAG:` lines (plus the `@LAW:` lines) into your prompt.
4. **Act / reason** using only the warm data + the current user request.
5. **Settle** finished work (see pattern below) — always via `update`.
6. (Occasionally) prune and continue.

Repeat. Each new turn starts by calling `query warm`.

---

## IDs — the most important discipline

- IDs are **global within a session** and **unique per tag**.
- **Reuse the same ID** for the same conceptual thing forever (e.g. the same person is always `N01`).
- **Never invent a new ID** for something that already exists in the graph.
- When in doubt, first do a `read get --id XXX` or a `query warm` to check.
- Bad: `add` with `N02` when `N01` already represents the same NPC.
- Good: `update` with the existing `N01` copied from warm output.

Law 02 (enforced): one row per (id + tag). `add` then `update` — never the reverse for the same id.

---

## The `recycle` field — how you control what the goldfish sees

Only tags that declare `recycle` in the current map have this column (see `memnet tagmap fields` or `memnet examples map`).

Valid values:
- `persistent` (or omit the field) → stays visible in warm reads.
- `delete_on_settle` → hidden from warm once you set it (finished mission / task).
- `delete_on_expire` → hidden from warm (temporary links, usually edges).

**Settlement pattern (do this when a mission or sub-task ends)**

Use **`update`** (these rows already exist):

```
@TSK: T01|Upgrade workshop|1|settled|delete_on_settle
@EDG: E01|N01|seeks_help|PLR01|unlock|delete_on_settle
@EDG: E02|PLR01|binds|TEC01|unlock|delete_on_settle
```

Then, on the **next** turn:
- Call `query warm --anchor <new focus>`.
- T01 and the settled edges will no longer appear (they are now recyclable).

Optionally follow up with:
```powershell
memnet housekeep prune recyclable --apply
```
to physically remove them and free cap space. Emit this after settlement when the graph is getting noisy.

---

## Reading strategy

Background, rules, world facts, configs and character data are stored as many small rows, not monolithic blobs. Only the pieces the current anchor can reach (directly or via EDG links) appear in `query warm`. This keeps every turn's context small and precise even on long-running tasks.

- **Normal agent turn**: `query warm --anchor <current focus>` (or a PLR / mission id).
  - Always includes all `@LAW:` rows.
  - Excludes everything with `recycle` = `delete_on_settle` or `delete_on_expire`.
- Use `--depth 2` (or 1–3) and `--max-rows 50` (or less) to keep the injection small.
- `query context` (without `--active-only`) is for **audit only**. It will flood you with settled missions and emit `stale_in_context` warnings on stderr. Do not use it as your default read.
- `read list --active-only` or `read list --tag TSK --active-only` for simple filtered lists without graph traversal.
- `read list --where field=value` to match a specific field (exact). Repeat `--where` for AND. Wildcards: `--where name=*Tiexin*`.
- `housekeep stats` includes `@STAT: modified|…` — compare across turns to skip re-injecting warm output when the graph is unchanged.

---

## Relations (EDG)

EDG rows are first-class directed links (`@EDG: E99|src|relation|dist||recycle`). They are the explicit wiring the agent maintains so that `query warm --anchor <focus>` can pull in only the connected background, rules and entities needed for the current state (instead of the whole graph or nothing). Background itself is deliberately granular — many small rows (one fact, one rule, one character facet, etc.) — so only the relevant fragments are brought in. LAW01 hides transient edges from warm once settled unless the anchor touches an endpoint.

- Relations are declared at session open (seeded from `relations.seed.txt`).
- By default you may only use known relations.
- To introduce a new one: `add ... --allow-new-relation` or `update ... --allow-new-relation`.
- Do not spam new relations. Prefer the existing vocabulary (`seeks_help`, `binds`, `produces`, `links`, etc.).
- Check current vocabulary with `memnet relations list`.

See `application-notes/llm-novel-writer.md` for a long-form example where EDGs wire every scene to its LORE/CHR/RULE dependencies and transient links are settled away cleanly.

---

## Housekeeping rhythm (what a disciplined agent does)

After you settle one or more missions:
```powershell
memnet housekeep stale
memnet housekeep prune stale --apply
```

Or be more precise:
- `housekeep recyclable` + prune (settled missions)
- `housekeep dangling` + prune (broken edges you accidentally created)
- `housekeep orphans --tag NPC` (lonely characters you can safely forget)

`housekeep stats` gives you the numbers vs your caps (`@STAT: rows|142|5000` etc.).

You will also receive warnings on stderr:
- `near_cap*` → you are close to a limit; prune or close missions.
- `stale_graph` / `stale_in_store` → there is dirt; consider `housekeep stale`.
- `ttl_expiring` → session is about to die; save a snapshot if you need it later (`session save --file ...`).

---

## Warnings live on stderr — you must read them

Every stateful command can emit `@WRN:` lines before the data on stdout.

Common ones you care about:
- `stale_in_store|...|query warm or housekeep prune ...`
- `mission_settled|T01|next read use query warm --anchor <focus>`
- `near_cap_critical|rows|...|housekeep required`
- `ttl_expiring|7`

Treat these as first-class signals. Adjust behaviour (switch anchor, prune, settle, save snapshot, etc.).

---

## Session lifecycle (for the agent)

- One task → one session id.
- `session open --map-file ...` (or `--map` lines) at the very beginning of a big job.
- `session resume $env:MEMNET_SESSION` on every subsequent turn (or rely on the env var).
- `session current` and `session list` to inspect.
- When the whole job is finished: `session close`.
- Optional durability: `session save --file my-job.snap` before risky steps or at major milestones. Restore later with `session load --file my-job.snap [--ttl 120]`.

Default TTL is 60 minutes. Override with `--ttl` on open/load or the `MEMNET_SESSION_TTL_MINUTES` env var.

---

## Schema discovery (you must do this)

At the start of a session, or when you see an unfamiliar tag:

```powershell
memnet examples map          # full fixed + user tags for the bundled schema
memnet tagmap fields         # or --tag NPC
memnet tagmap show           # what this session actually loaded
memnet examples workflow     # realistic example of a world + missions + edges
```

Never guess field order or required columns. Use the map.

---

## Ingest discipline

- Prefer `--stdin` or `--file` with many lines in one call (atomic, fewer round-trips).
- New rows → `add`. Changes to existing rows → `update`.
- Always escape pipes inside values: `note\|extra`.
- Dry-run when you are unsure: `add --dry-run ...` or `update --dry-run ...`
- After any update that settles work, the very next read must be `query warm`.

---

## Common failure modes (and the correct behaviour)

- Using `query context` every turn → prompt pollution, settled missions reappear, you get confused.
  → Fix: only `query warm --anchor ...`
- `add` with a new id for something that already exists (`N02` when `N01` is the same NPC).
  → Fix: read warm first, `update` with `N01`.
- `update` with a typo (`N0l` instead of `N01`) → `not_found`.
  → Fix: copy id from warm output; do not retype.
- `add` when id already exists → `id_exists`.
  → Fix: use `update` instead.
- Leaving settled missions with `recycle=persistent`.
  → Fix: on completion, `update` with both `status=settled` **and** the appropriate `delete_on_*` value.
- Forgetting to prune after many settlements.
  → Fix: after settlement batch, run `housekeep prune stale --apply`.
- Introducing random new relations on every edge.
  → Fix: use the existing list; only `--allow-new-relation` when genuinely needed.
- Ignoring `@WRN:` lines on stderr.
  → Fix: read them. They tell you about caps, staleness, and mission state changes.

---

## Minimal complete turn (copy-paste shape)

```powershell
# 1. Add new state (batch) — first time only
memnet add --stdin @"
@TSK: T07|Negotiate with the guild|3|in_progress|persistent
@EDG: E19|B01|seeks_help|T07|terms|persistent
"@

# 2. Read only the live relevant slice
memnet query warm --anchor T07 --depth 2 --max-rows 30

# (paste the returned @LAW: + @TAG: lines into your reasoning)

# 3. Later, when done — update existing rows
memnet update --stdin @"
@TSK: T07|Negotiate with the guild|3|settled|delete_on_settle
@EDG: E19|B01|seeks_help|T07|terms|delete_on_settle
"@

# 4. Next turn starts with warm again (T07 will be absent)
memnet query warm --anchor PLR01
```

---

## Quick reference for agents

- `memnet serve` — must be running (one terminal).
- `memnet session open --map-file ... [--ttl 90]`
- `memnet add --stdin ...` — new rows only
- `memnet update --stdin ...` — existing rows only
- `memnet query warm --anchor <id> [--depth 2]`
- `memnet housekeep stale`
- `memnet housekeep prune stale --apply`
- `memnet relations list`
- `memnet tagmap fields --tag <TAG>`
- `memnet guide --loose` — short cheat sheet.
- `memnet examples map|workflow`

**Application note:** see `application-notes/llm-novel-writer.md` for a long-running creative writing example that follows the explicit 6-step pipeline (read → context → user input as data → analyse citing rows → add/update with correct recycle → loop) where background, configurations, bibles, rules and user preferences are kept as persistent rows inside the graph.

See `application-notes/llm-sysml-v2-modeling.md` for LLM-assisted SysML v2 textual modeling (PDU controller on a 6U CubeSat) using the same pipeline, a prominent SysML v2 syntax reference table, a deployable "complete model as rows" block, explicit demonstration that models whose definitions live in different .sysml files are easily referred to together via lightweight @PKG rows + declaredIn / cross-package EDG, and worked examples of using the graph to help build the system (allocations, ports and connections driving implementation tasks, wiring and deployment), write the official system model documentation (interconnection, behaviour and traceability artefacts generated from the rows), and evaluate runtime behaviour (BEHD + timing/power + allocations for analysis and budgeting). `query warm --anchor` + EDG + settlement still keeps every turn's injected slice small, granular and on-demand.

**Read this file (`LLM-GUIDE.md`) at the beginning of any non-trivial task.**

When the current schema or examples change, re-run `memnet examples map` and `memnet tagmap show`.

Stay disciplined with ids, `add` vs `update`, the `recycle` label on settlement, and `query warm`. Everything else follows from that.
