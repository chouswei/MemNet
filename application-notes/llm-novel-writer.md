# LLM Novel-Style RPG — A MemNet Application Note

**Application example (documentation only).** This file is a self-contained *pattern* for one domain — interactive novel-style RPGs — not part of the MemNet engine. It shows how you might combine MemNet primitives (`query warm`, fixed **LAW** / **EDG**, user-defined tags, `add`/`update`, settlement) with an orchestrator and an LLM. Copy or adapt the schema; other projects may use different tags and outputs.

**MemNet (engine)** — always provides `@LAW:` and `@EDG:`, prepends all LAW rows on every warm read, and stores whatever tags you declare in your map.

**This example (application)** — declares `@LORE`, `@RULE`, `@CHR`, `@ITEM`, `@QUEST`, `@PLT`, `@USR`, `@SCN`, `@CHOICE`. In step 2 the orchestrator injects the warm data rows into the LLM prompt; the LLM converts those data rows into the novel section with selections (reader-facing narrative prose in novel style + the choice/selection description the player sees and picks from) and the orchestrator gives the converted text to the human to read. Structural outcomes (the rows that will feed future conversions — updated character attributes, consumed or gained items, quest progress, companion relationships, new scenes) are recorded in the graph in step 5.

The human experiences the game as reading (and choosing inside) a living novel. The prose is rich, immersive, and literary. Underneath, the graph is the single source of truth for the RPG state: your character's attributes and skills, inventory, active quests, companion bonds, and world facts are many small rows. Most state enters warm only when the current scene or choice reaches it via EDG or direct anchor. **All `@LAW:` rows are always prepended**, so the LLM cannot miss the pipeline discipline or project constraints.

No external character sheets, no hidden system prompts, no "the model will remember the numbers." The graph is the character sheet and the world model. The session can be snapshotted and resumed with `session save` / `session load`.

**At a glance (for skimming or partial LLM reads)**

- The 6-step pipeline used by the orchestrator + LLM in *this* example, plus the role of LAW rows as the always-prepended machine-readable contract.
- Schema you declare in your map (Part A) and the LAW vs RULE vs USR distinction (do not confuse them).
- Complete starting seed block (Part B) — copy this after `session open`.
- What the orchestrator must do (command-level view).
- Three worked turns showing the full cycle: in step 2 the orchestrator injects the warm data rows; the LLM converts those data rows into the novel section with selections and gives it to the human to read → human responds (selection or steering) → orchestrator records the outcome in the graph (step 5) so future warm reads have the memory. (Harry Potter / Philosopher's Stone era, novel-style RPG.)
- Snapshot / resume, pipeline-aware pitfalls, copy-paste quick-start, and a Mermaid diagram of the loop.

## The 6-Step Pipeline (this example's repeating loop)

This is the orchestrator + LLM loop **used in this application note**. The worked turns below follow these steps. Other application notes (e.g. SysML modeling) reuse the same MemNet mechanics with different tags and deliverables.

1. **Read the state** — selective `query warm --anchor <focus>` (in this example: current SCN/CHR/CHOICE/QUEST, or direct anchors on LORE/RULE/CHR/ITEM/PLT/USR when background, inventory or quest state is required). Use `--depth` and EDG links to pull only connected reference material. Never rely on prior chat messages for facts or numbers.

2. **Write the novel section** — the orchestrator takes the `query warm` output (the data rows: always-prepended LAW rows + whatever the anchor and EDGs reach: LORE, RULE, CHR with its current attr and status, ITEMs, QUEST progress, SCN, CHOICE, EDG, etc.) and **injects those data rows into the LLM prompt** together with user steering. In this example, **in step 2 the LLM converts the data rows into the novel section with selections** that is given to the human to read: reader-facing narrative prose in novel style (immersive, literary, describing the situation, your attempted action, the narrated outcome, the emotional and mechanical cost, and the new situation) plus, when the beat reaches a decision point, the choice/selection description (the prompt text and the list of numbered options the player sees and can pick from). The warm data rows are the source of truth (your current Courage 3, Charms 2, the Wiggenweld potion still in your pocket, Hermione's relationship at "wary"); the LLM turns them into the readable novel page the human consumes right now. The orchestrator records the structural outcome of the turn (updated @CHR attr or status, @ITEM count reduced, @QUEST progress advanced, new/updated @SCN and @CHOICE rows, settlements, wiring) later in step 5 so the next warm read carries the updated character sheet and world. MemNet itself does not generate prose or selections; the orchestrator + LLM do the conversion using the warm data rows as input.

3. **Capture the response** — the human has just read the novel section (narrative prose + choice/selection description) produced in step 2. The orchestrator surfaces any pending **CHOICE** or accepts free-form steering from the human in response to what they read. The user's input or selection is recorded as first-class data (usually by `add` or `update` of a choice/decision row).

4. **Analyse the turn** — after the human's selection or steering has been captured as first-class data in step 3 (e.g. a chosen option on a CHOICE row, or free-form prompt), the orchestrator performs **additional targeted reads** from the memStore. Typical reads in this phase: re-anchor on the now-resolved CHOICE (to see the exact player words), anchor on the primary CHR that will be affected, on the RULEs that govern costs or behaviour, on the QUEST, on any ITEMs or other state the choice touches. The LLM uses these reads (plus the original context) to determine precisely **how the player's specific input interacts with the current rows** — what state changes are licensed, what mechanical costs or relationship shifts occur, what new transient records (new SCN, updated status, settlements) are required, and what must be left untouched. Only after this read-heavy analysis does it emit a precise plan of *row mutations*. The analysis phase itself does not write; it is the determination step. Step 5 is where the memStore is actually updated.

5. **Persist the outcome** — this is the phase that actually mutates the graph. The orchestrator emits the node and edge operations determined in step 4, using MemNet's graph language (the wire format of `@TAG:` rows for nodes and `@EDG:` rows for directed named edges). New nodes are created with `add`; existing nodes and edges are changed with `update`. Transient nodes/edges (SCN, CHOICE, most active wiring) are settled with `recycle=delete_on_settle`. Persistent nodes (CHR with its attr, ITEM counts, QUEST progress, RULE, LORE) are only mutated when the player's actions legitimately change the world model. Step 5 speaks the graph language to the memStore.

6. **Loop** — return to step 1. The next turn begins with a fresh read. Settled transient rows disappear from `query warm` (unless still connected to the new anchor).

### LAW as the pipeline contract (for the LLM)

The six steps above describe the **orchestrator loop** (CLI calls, user I/O, ingest). **LAW rows** are the complementary piece: the **always-on reasoning contract** the LLM sees in every warm read — procedure and graph discipline encoded in the graph itself, not buried in chat history or a hidden system prompt.

| Role | Who runs it | What it does |
|------|-------------|--------------|
| **Orchestrator** | Your script or agent | Executes steps 1–6: `query warm`, surfaces user input, runs `add`/`update`, optional prune |
| **LAW rows** | MemNet prepends them | Tells the LLM **how** to reason and which wire-line rules to obey when emitting changes |
| **Warm slice** | MemNet + anchor/EDG | Supplies **what** is true this turn (SCN, LORE, RULE, …) |

**How the core LAWs map to the pipeline:**

| Step | LAW support |
|------|-------------|
| 1 Read | **LAW02** — ids in warm output are authoritative; never invent ids from chat |
| 2 Write | Engine prepends **all** LAW rows; orchestrator injects the data rows (warm output) into the LLM prompt. In this example, **in step 2 the LLM converts those data rows into the novel section with selections** and gives it to the human to read. |
| 3 Respond | Orchestrator records steering as rows (e.g. CHOICE); optional domain LAW can require "record human choice as data, not prose only" |
| 4 Analyse | Additional targeted reads on the captured player input (the chosen CHOICE, affected CHR, relevant RULEs, QUEST, etc.) to determine exactly how the selection interacts with the graph; produce the mutation plan; domain LAWs still apply |
| 5 Persist | Emit the actual graph mutations (nodes + edges) in wire format; **LAW02** (add vs update), **LAW03** (edge endpoints), **LAW04** (escaping); **LAW-ATOM01** (no sentence in fields — break the sentence into nodes and edges; only ids/keys/codes/phases in row fields); domain LAWs still constrain what is legal to write |
| 6 Loop | **LAW01** — settled transient EDGs/rows drop from warm unless anchor touches an endpoint |

**Domain LAW rows** extend the same pattern. The **`name` field = governed tag** (`CHR`, `SCN`, `*`, …); put the rule in `cycle|mechanism|constraint` as short codes only — e.g. `LAW-HP01|CHR|…|cite_chr_attr_step2` and `LAW-ATOM01|*|…|break_to_nodes_edges`. Optional turn-discipline row:

```text
@LAW: LAW-PIPE01|SCN|on_turn|read_warm|anchor_scn_or_choice_cite_warm_ids
@LAW: LAW-ATOM01|*|on_add|no_sentences|break_to_nodes_edges
```

Keep LAW rows **short and procedural**. Story voice belongs in **RULE**; operator knobs in **USR**. This note's markdown pipeline is documentation for humans; **LAW is the machine-readable contract the LLM actually receives every turn.**

After heavy settlement, optionally run `housekeep prune recyclable --apply` to physically remove settled rows and free cap space. Reference material (LORE facts, RULE constraints, focused CHR bibles/facets, master PLT, USR prefs) is never settled away.

**Persistent vs transient (quick legend)**

- **Persistent** (survives settlements): LORE, RULE, CHR, PLT, USR, domain LAW rows. Most appear in warm **only when the anchor or EDG reaches them** — except **LAW (all rows), which are always prepended with no EDG required**. Other persistent types typically need EDG (or a direct anchor) to enter warm.
- **Transient** (settle with `delete_on_settle` when done): SCN, CHOICE, active beat work, and most transient EDGs.

## Part A: Schema (the user tag map)

This is the map you feed to `memnet session open --map-file`. It defines only the *user* tags for this domain. Fixed tags **EDG** and **LAW** are always present and do not appear here. See **LAW vs RULE vs USR** below for how LAW (fixed) differs from RULE (your schema).

```text
@LORE: id|name|kind|code|recycle
@RULE: id|name|scope|code|recycle
@CHR: id|name|role|attr|facet|status|recycle
@ITEM: id|name|kind|uses|effect|recycle
@QUEST: id|key|stage|goal|progress|status|recycle
@PLT: id|key|phase|arc|status|recycle
@USR: id|key|value|recycle
@SCN: id|key|phase|recycle
@CHOICE: id|resolves|chosen|recycle
@EVT: id|type|actor|focus|code|recycle
@COST: id|subject|kind|site|recycle
@BOND: id|left|right|delta|code|recycle
```

**Important for token efficiency (this pattern):** Enforced by `LAW-ATOM01` (always prepended): **no sentence in any field, on any tag** — break meaning into more nodes and edges. Every field on every row (`@LAW` constraint codes included) holds only ids, keys, phases, short codes, or numeric attr values. No `text`, `backstory`, or prose blobs. If a fact needs several ideas, split it into multiple `@LORE` / `@RULE` / `@EVT` rows and wire them with `@EDG`. Reader-facing novel text is generated only in step 2 from this skeleton + the prepended LAW codes.

## LAW vs RULE vs USR (do not confuse them)

Both LAW and RULE are “rules” in plain English. In this note they are **different tags with different jobs**.

| | **LAW** (fixed tag) | **RULE** (your schema) | **USR** (your schema) |
|--|---------------------|------------------------|------------------------|
| **Governs** | The **graph** and **how rows may exist** (ids, edges, wire format) + **hard project structure** (e.g. "when resolving a challenge, cite the acting skill value from the CHR row") | The **story**: voice, magic, pacing, world logic | **Your preferences** as the operator: length, POV style |
| **In every `query warm`?** | **Yes** — engine prepends **all** LAW rows | **No** — only if EDG-linked or you anchor on it | **No** — same as RULE |
| **Needs EDG to appear in warm?** | **No** — engine prepends all LAW rows | **Yes** — EDG-linked or direct anchor | **Yes** — same as RULE |
| **Optional EDG (bookkeeping)** | `@EDG: LAW-HP01\|governs\|SCN01` (audit which scenes obeyed the stat-cite rule) | `@EDG: CHR01\|governs\|RULE02` | `@EDG: SCN01\|influences\|USR01` |
| **Engine enforcement** | Partly (e.g. LAW02 duplicate id on `add`) | Prompt discipline only | Prompt discipline only |
| **Example** | LAW02 (`*|on_add`): one id per row; LAW-HP01 (`CHR|on_turn`): cite acting attr from CHR in step 2 | RULE01: `cite_choices_not_ability` | USR01: `scene_length=spare` |

**Decision guide — which tag?**

1. If breaking it would corrupt **ids, EDGs, or ingest** → **LAW** (and consider a domain LAW if the model must see it **every turn** before `add`).
2. If it is **how the story should read or how the world (or magic) works in fiction** → **RULE**, wire with EDG from scenes/characters that need it.
3. If it is **your steering preference** (not in-universe canon) → **USR**, not RULE.

**Why not put story craft in LAW?** You could, but every LAW row lands in **every** warm read forever — token cost adds up. RULE stays out of context until a linked scene or character needs it.

**Why LAW-HP01 is not a RULE:** the "cite acting skill/attr from CHR on every year-1 challenge resolution" rule must be visible **before every skill test or spell** in year 1; the engine does not enforce it. LAW guarantees the constraint is never skipped — **no EDG required**.

**LAW rows need no EDG.** The `@LAW:` row alone is enough; every `query warm` prepends it. Optional `constrains` (or similar) EDGs are for **graph bookkeeping** — listing which nodes were minted under a domain LAW, auditing, or traversing from LAW → instances. They do **not** control whether the LAW text appears in context.

EDG relations used in this example (seed a few at start or use `--allow-new-relation` when genuinely new): `set_in`, `features`, `governs`, `constrains`, `continues`, `resolves`, `costs`, `influences`, `risk_if`, `seeks`, `targets`, `caused`, `suffered_by`, `imposed`, `carries`, `changed`, `between`, `applies_to`, `potential_for`.

**EDG rows — the explicit wiring for selective context**

EDG is a *fixed, built-in tag* (always available; never declared in your map). It models directed, named links between any rows:

```
@EDG: E99|SRC_ID|relation|DST_ID|optional_attrs|recycle
```

**Core function in the pipeline:**
- They are how you declare "this scene is *set_in* this lore", "this character *features* here", "this rule *governs* that character", "this beat *costs* this person". Optionally, "this domain LAW *constrains* this NPC" — for audit and traversal only; the LAW row is already in every warm read without that link.
- `query warm --anchor <focus> --depth N` traverses EDG links to pull in *only* the connected persistent background, bibles and rules the current focus needs. Without the right EDGs, anchoring on a SCN or CHOICE would return almost nothing but the prepended LAW rows (core invariants plus any domain constraints such as id rules) + the anchor itself.
- LAW01 (`EDG|on_context|hide`) keeps the warm slice clean: most transient EDGs (and the rows they point to) are hidden from context unless the anchor is at src or dist.
- You manage them with the same `add`/`update` discipline as nodes (copy ids from warm; use `--allow-new-relation` only for genuinely new relation verbs). They are first-class data, not implicit "the LLM will remember the connection".

In short: EDG is the mechanism that makes "read only what the anchor can reach" reliable and deterministic for long-running work.

**LAW rows — protocol and structural constraints (always on)**

LAW is a *fixed, built-in tag* (not in your map). **Every** `query warm` prepends **all** LAW rows before the anchored slice. They are not optional background.

```
@LAW: id|name|cycle|mechanism|constraint
```

MemNet names the second field `name` in the wire format; in this note we treat it as the **governed tag** — which `@TAG:` (or `EDG`, or `*` for all node tags) the law applies to. The last three fields are short codes only (`cycle`, `mechanism`, `constraint`); never sentences. LAW has no `recycle` field — LAW rows are always prepended and are not settled away.

| Field (wire) | Role in this note |
|--------------|-------------------|
| `id` | LAW row id (`LAW01`, `LAW-ATOM01`, …) |
| `name` | **Governed tag** — `EDG`, `CHR`, `LORE`, `SCN`, `*` (all node tags), etc. |
| `cycle` | When it applies (`on_context`, `on_add`, `on_turn`, …) |
| `mechanism` | How (`hide`, `unique`, `no_sentences`, …) |
| `constraint` | What (`settled_edg_unless_anchor`, `break_to_nodes_edges`, …) |

The four **core** LAWs (MemNet engine — seed in every project):

```text
@LAW: LAW01|EDG|on_context|hide|settled_edg_unless_anchor
@LAW: LAW02|*|on_add|unique|one_id_add_then_update
@LAW: LAW03|EDG|on_add|validate|src_dist_exist_first
@LAW: LAW04|*|on_add|use_backslash|backslash_pipe_not_bare
```

**Core function in the pipeline:**

See **LAW as the pipeline contract (for the LLM)** above for the orchestrator vs LAW split and step mapping. In brief:

- LAW02 (`*|on_add|unique`) is the reason you must read first, copy the exact id, and use `add` only for truly new things (or `update` for existing). It is enforced at ingest.
- LAW01 (`EDG|on_context|hide`) and LAW03 (`EDG|on_add|validate`) work with EDG to keep warm slices clean and wiring sound.
- LAW04 (`*|on_add|use_backslash`) protects the wire format itself.

**Domain LAW rows (project-specific, still always prepended)**

Beyond LAW01–04, add **domain** LAW rows. Put the **governed tag** in the `name` field (`CHR`, `SCN`, `*`, …) and the rule in the three code fields. They appear in **every** warm read, same as the core four.

Example in this note: `LAW-HP01|CHR|on_turn|stat_cite|cite_chr_attr_step2` — when step 2 generates year-1 challenge prose, cite the acting attr/skill from the warm CHR row (e.g. Charms 2). SCN and CHOICE rows stay minimal; the LAW names `CHR` as the tag whose values must be cited. Optional audit EDG:

```
@EDG: E06|LAW-HP01|governs|SCN01||persistent
```

(The src is the LAW-HP01 row; dist is the scene that obeys it; the edge is persistent so the link survives settlement.)

If you add these links, they help with:
- `query warm --anchor LAW-HP01 --depth 1` surfacing the scenes that obeyed the rule
- Traversing from a scene back to the governing LAW for audit
- Keeping "this constraint applied here" as first-class graph data rather than only in the LLM's head

Skip the EDG entirely if you only need the rule text every turn and do not care about traversable instance lists.

In short: **LAW** = “how nodes are allowed to exist in the graph” (always visible, no EDG needed). **Optional EDG** = which specific scenes or characters were created under a domain LAW.

**RULE rows — story craft (on demand only)**

RULE is a *user tag* from your map. Each row is one **narrative** constraint: voice, magic rules, pacing, tone. RULE rows are **not** prepended globally — they enter warm only when:

- an **EDG** links them from the current anchor (e.g. `CHR01|governs|RULE02`), or
- you **anchor directly** on the RULE (as Turn 3 does on `RULE02`).

```
@RULE: id|name|scope|code|recycle
```

Examples from the seed: `cite_choices_not_ability` (theme), `low_skill_visible_cost` (risk), `one_state_delta_per_beat` (structure). Each is a single short code — not a sentence. **Do not** put operator prefs here — use **USR** (`USR01|scene_length|spare`). **Do not** put id format or graph mechanics here — use **LAW**.

When canon changes (Turn 3), **update** the existing RULE row's `code` field in place (e.g. `low_skill_visible_cost` → `low_skill_lingering_cost`); cite its id from warm output.

**Background is many small pieces, referred only when needed**

Because persistent material is many small rows, the warm slice for each turn contains only what the focus needs — **plus all LAW rows**. SCN and CHOICE are deliberately tiny (key/phase or resolves+chosen); per-turn outcomes are recorded as atomic @EVT / @COST / @BOND nodes (fields are only ids + short codes) wired by many EDG relations. In the seed you see LORE01/LORE02, initial EVT00 + COST00 for the door risk, three RULE rows, four core LAWs + LAW-HP01, the player CHR with its current attr, a starting ITEM, the active QUEST (short progress key), etc. RULE01 appears in Turn 1 because `CHR01|governs|RULE01` is wired; RULE03 may stay out until a scene links it. Anchor directly on a RULE (Turn 3) when you need to edit canon without traversing from a scene. This keeps every warm read token-efficient.

## Part B: Initial Seed (complete starting state)

Copy the block below (or extract it via heredoc) and feed it to `memnet add --stdin` after opening the session with the schema above. This populates the graph with *all* initial data as many small pieces: LORE facts, RULE codes, core LAWs plus domain LAWs (`LAW-ATOM01|*|…`, `LAW-HP01|CHR|…`), player and companion CHRs, ITEM, QUEST, PLT, USR, opening SCN, and EDG wiring. Persistent rows use `persistent` (or omit recycle); opening SCN and its transient links use `delete_on_settle`.

```text
@LAW: LAW01|EDG|on_context|hide|settled_edg_unless_anchor
@LAW: LAW02|*|on_add|unique|one_id_add_then_update
@LAW: LAW03|EDG|on_add|validate|src_dist_exist_first
@LAW: LAW04|*|on_add|use_backslash|backslash_pipe_not_bare
@LAW: LAW-ATOM01|*|on_add|no_sentences|break_to_nodes_edges
@LAW: LAW-HP01|CHR|on_turn|stat_cite|cite_chr_attr_step2

@LORE: LORE01|philosophers_stone|artifact|elixir_source|persistent
@LORE: LORE02|philosophers_stone|artifact|voldemort_power_y1|persistent
@LORE: LORE03|quirrell|threat|possessed|persistent
@LORE: LORE04|quirrell|threat|closing_stone|persistent

@RULE: RULE01|choices_wizard|theme|cite_choices_not_ability|persistent
@RULE: RULE02|magic_toll|risk|low_skill_visible_cost|persistent
@RULE: RULE03|one_change|structure|one_state_delta_per_beat|persistent

@CHR: CHR01|You|protagonist|Courage:3|Wit:4|Charms:2|Stealth:3|firstyear_belong|unhurt|persistent
@CHR: CHR02|Harry|ally|brave|scarred|boy_who_lived|persistent
@CHR: CHR03|Hermione|ally|brilliant|loyal|rules_first_help_wary|persistent

@ITEM: ITM01|wiggenweld|consumable|1|steady_spell|persistent

@QUEST: QST01|stone_y1|1|stop_quirrell|final_door_ward|active|persistent

@PLT: PLT01|stone_y1|year-1|stone_not_voldemort|active|persistent

@USR: USR01|scene_length|spare|persistent
@USR: USR02|voice|close-second-wonder|persistent

@SCN: SCN01|final_door|warded|delete_on_settle

@EVT: EVT00|risk|door|charms|bite|persistent
@COST: CST00|CHR01|potential_mark|hand|persistent

@EDG: E01|SCN01|set_in|LORE01||persistent
@EDG: L01|LORE01|risk_if|LORE02||persistent
@EDG: L02|LORE03|seeks|LORE01||persistent
@EDG: L03|LORE04|targets|LORE01||persistent
@EDG: E02|SCN01|features|CHR01||persistent
@EDG: E03|SCN01|features|CHR02||persistent
@EDG: E04|SCN01|features|CHR03||persistent
@EDG: E05|CHR01|governs|RULE01||persistent
@EDG: E06|SCN01|features|ITM01||persistent
@EDG: E07|SCN01|features|EVT00||persistent
@EDG: E08|SCN01|features|CST00||persistent
@EDG: E09|EVT00|applies_to|CHR01||persistent
@EDG: E10|CST00|potential_for|CHR01||persistent
```

## The 6-Step Pipeline (command-level view, this example)

**Orchestrator responsibilities (the harness around the LLM in this novel-style RPG pattern):**
- Always begin the turn with a read (step 1).
- Inject exactly the warm data rows (plus user steering) as the LLM context (step 2). In this example, **in step 2 the LLM converts the data rows into the novel section with selections** (narrative prose in novel style + choice/selection description) and gives that text to the human to read.
- Step 5 is where the graph is mutated in graph language: the orchestrator sends the exact node rows (`@CHR:`, `@SCN:`, `@RULE:`, `@ITEM:`, `@QUEST:`, etc.) and edge rows (`@EDG:`) that step 4 decided must exist or change. This is the only place the in-memory graph (nodes + directed named edges) is written to.
- Capture the human's response after they read the novel section (step 3).
- In step 4 (analyse), after capture, issue further targeted reads on the player's input (the chosen CHOICE row, the CHR(s) it affects, the RULEs that govern the interaction, QUEST progress, etc.). Use these reads to let the LLM determine exactly how this specific selection/prompt should affect the graph (which nodes change, which edges must be added or settled).
- In step 5, emit the graph operations (node and edge mutations) in MemNet's wire language. The commands sent (`memnet add --stdin`, `memnet update --stdin`) are statements that create or modify nodes (`@CHR:`, `@SCN:`, `@RULE:`, etc.) and edges (`@EDG:`). Step 5 is where the graph itself is updated.
- After settlement, optionally prune; always start the next turn with a fresh read.

The LLM never "remembers" ids or facts across turns. It only ever sees what step 1 + 2 put in front of it.

## Part D: Worked Turns (the pipeline in action)

Three compact turns. Each is shown strictly as the six numbered steps. Warm output excerpts include the prepended `@LAW:` rows (core invariants plus any domain constraints). All ids are copied from the warm/context output. Transient rows are settled with `delete_on_settle` when their work is done. One turn demonstrates a legitimate update to a persistent RULE when the story changes the world's "canon." Turn 1 also demonstrates obeying domain LAWs: `LAW-HP01|CHR|…` (cite acting attr in step 2 prose) and `LAW-ATOM01|*|…` (no sentence in any row field — atomic nodes + EDGs). The example is a novel-style RPG: the human reads immersive prose that feels like a book page; the graph holds the character sheet, inventory, quests and relationships as first-class rows.

### Turn 1 — The First Hard Choice

**Human steering (feeds step 2 + 3):** "You, Harry and Hermione are at the final warded door. Quirrell is close on the other side. Give the player a real, costly choice that respects the current Charms 2 and the Wiggenweld in inventory. Do not resolve it yet."

**Step 1 — Read the state**
```
memnet query warm --anchor SCN01 --depth 2 --max-rows 30
```

**Step 2 — Write the novel section**
```
@LAW: LAW01|EDG|on_context|hide|settled_edg_unless_anchor
@LAW: LAW02|*|on_add|unique|one_id_add_then_update
@LAW: LAW03|EDG|on_add|validate|src_dist_exist_first
@LAW: LAW04|*|on_add|use_backslash|backslash_pipe_not_bare
@LAW: LAW-ATOM01|*|on_add|no_sentences|break_to_nodes_edges...
@LAW: LAW-HP01|CHR|on_turn|stat_cite|cite_chr_attr_step2...
@LORE: LORE01|philosophers_stone|artifact|elixir_source|persistent
@LORE: LORE02|philosophers_stone|artifact|voldemort_power_y1|persistent
@LORE: LORE03|quirrell|threat|possessed|persistent
@LORE: LORE04|quirrell|threat|closing_stone|persistent
@RULE: RULE01|choices_wizard|theme|cite_choices_not_ability|persistent
@RULE: RULE02|magic_toll|risk|low_skill_visible_cost|persistent
@RULE: RULE03|one_change|structure|one_state_delta_per_beat|persistent
@CHR: CHR01|You|protagonist|Courage:3|Wit:4|Charms:2|Stealth:3|firstyear_belong|unhurt|persistent
@CHR: CHR02|Harry|ally|brave|scarred|boy_who_lived|persistent
@CHR: CHR03|Hermione|ally|brilliant|loyal|rules_first_help_wary|persistent
@ITEM: ITM01|wiggenweld|consumable|1|steady_spell|persistent
@QUEST: QST01|stone_y1|1|stop_quirrell|final_door_ward|active|persistent
@SCN: SCN01|final_door|warded|delete_on_settle
@EVT: EVT00|risk|door|charms|bite|persistent
@COST: CST00|CHR01|potential_mark|hand|persistent
@EDG: E01|SCN01|set_in|LORE01||persistent
@EDG: E02|SCN01|features|CHR01||persistent
@EDG: E03|SCN01|features|CHR02||persistent
@EDG: E04|SCN01|features|CHR03||persistent
@EDG: E05|CHR01|governs|RULE01||persistent
@EDG: E06|SCN01|features|ITM01||persistent
@EDG: E07|SCN01|features|EVT00||persistent
@EDG: E08|SCN01|features|CST00||persistent
@EDG: E09|EVT00|applies_to|CHR01||persistent
@EDG: E10|CST00|potential_for|CHR01||persistent
```

**Novel section given to the human (what the reader/player reads right now)**

> You stand with Harry and Hermione before the warded door. The silver tracery pulses like a slow heartbeat. On the other side Quirrell's voice is a cold thread of sound. Your wand feels too light in your hand. You know your Charms is only 2 — under pressure the charm can sputter, the ward can bite, the noise can bring the servant running before you are ready.
>
> Hermione's fingers hover near her own wand. Harry's eyes flick to the small vial in your pocket and back to your face. He gives the smallest of nods.
>
> What do you do?
>
> 1. Attempt the unlocking charm yourself (your Charms is 2; the prose will show the risk and any backlash or shaky partial success).
> 2. Ask Hermione to cast it (she will almost certainly succeed cleanly, but it will cost trust — she will remember that you asked her to take the risk for you).
> 3. Drink the Wiggenweld first to steady your hand and nerves (consume the item; the prose will show the brief steadiness it lends your Charms 2 attempt).

**Remark:** In step 2 the LLM converts the warm data rows shown above (plus the steering) into this novel section with selections. The blockquoted text is what the human is given to read. The data rows are the input (your current Charms 2, the single Wiggenweld, Hermione's relationship state, the active quest, the warded door + its initial EVT/COST risk facts); the readable novel page + choice description is the output the human consumes at this point in the turn. No graph update has happened yet.

**Human selects (step 3 — concrete example)**

"I choose 1."  (or "1. Attempt the unlocking charm yourself..." or the full text)

The orchestrator captures the human's exact words ("I choose 1.") as the user input. In this turn's step 5 the selection is resolved against the numbered options and stored on the CHOICE node as a minimal record (resolves + chosen index/short label only — no sentences). The mechanical outcome (bite, yield, personal cost, companion note) is recorded as atomic @EVT / @COST / @BOND nodes + many EDGs. The graph mutations (CHR status code, new minimal SCN02, atomic nodes, edges, settlements) are applied in this turn's Step 5 using node and edge rows in the wire format. The consequence novel section the human reads is produced by a step 2 that uses the recorded choice + the new atomic nodes as steering.

**Step 3 — Capture the response (detailed)**
The human has just read the novel section above. That section was produced in step 2 by the LLM converting the preceding warm data rows into reader-facing novel prose plus the three numbered selection options that respect the RPG state (your Charms 2, the item, the companion relationship).

The orchestrator records the human's exact selection (the number "1", resolved to a short label) as first-class data on the CHOICE node (minimal: resolves SCN + chosen key). No worded prompt or consequence text is stored on the row. The downstream graph mutations (minimal SCN02 + atomic @EVT / @COST / @BOND nodes for the bite/cost/shift + many EDGs + settlements) are applied in this same turn's Step 5. The human's words steer the step 2 that generates the reader-facing consequence prose from the updated structural rows.

**Step 4 — Analyse the turn**
" Warm (ids + current values copied exactly):
- CHR01: Courage:3|Wit:4|Charms:2|Stealth:3|...|unhurt
- ITM01: uses=1 (Wiggenweld)
- QST01: stage=1, status=active , progress=final_door_ward
- SCN01 (minimal key/phase), RULE02 (toll on low skill), LAW-HP01 (must cite acting value in generated prose)
- EVT00 / CST00 (door risk facts) via EDGs from SCN01
- Companions CHR02/03 present via features EDGs.

Row mutations (pure atomic nodes + edges only; no sentences or phrases in any row):
- CHOICE01: add, resolves=SCN01, chosen=1|self , recycle=delete_on_settle
- SCN02: add, key=threshold , phase=breach , recycle=delete_on_settle
- EVT01: add, type=yield , actor=CHR01 , focus=door , code=charms2_self
- COST01: add, subject=CHR01 , kind=mark , site=hand
- BOND01: add, left=CHR03 , right=CHR01 , delta=up , code=self_risk
- EDG E10: LAW-HP01 governs SCN01 (audit)
- Multiple EDG from SCN02 / EVT01 / COST01 / BOND01 to CHR01, LORE02, each other (caused, suffered, changed, records, applies_to, etc.)
- Settle prior transient pair SCN01 + CHOICE01

All ids and short codes copied from warm or generated under LAW discipline (including LAW-ATOM01: no sentence in fields). The rich wording lives only in the generated novel section. Ready for step 5 (graph update in wire format)."

**Step 5 — Persist the outcome (graph update in graph language)**

The human has selected "1. Attempt the unlocking charm yourself (your Charms is 2...)".

Step 4 (additional targeted reads on CHOICE01, CHR01, RULE02, LAW-HP01, the initial EVT/COST, etc.) has determined the exact row mutations licensed by that choice under the current state and LAW-HP01.

Step 5 is where the graph is mutated using node + edge wire format. Per LAW-ATOM01 (always prepended), no sentences or phrases are written into any row. The outcome is expressed purely as typed atomic nodes (EVT/COST/BOND with only short codes) plus many named EDG relations that connect actor, scene, skill reference, bearer, etc.

```
memnet update --stdin @"
@CHOICE: CHOICE01|SCN01|1|self|delete_on_settle
@CHR: CHR01|You|protagonist|Courage:3|Wit:4|Charms:2|Stealth:3|...|shaken_hand|persistent
@SCN: SCN02|threshold|breach|delete_on_settle
@EVT: EVT01|yield|CHR01|door|charms2_self|delete_on_settle
@COST: COST01|CHR01|mark|hand|persistent
@BOND: BOND01|CHR03|CHR01|up|self_risk|persistent
@EDG: E10|SCN02|set_in|LORE02||persistent
@EDG: E11|SCN02|features|CHR01||persistent
@EDG: E12|SCN02|costs|CHR01||persistent
@EDG: E13|SCN02|caused|EVT01||persistent
@EDG: E14|EVT01|suffered_by|CHR01||persistent
@EDG: E15|SCN02|imposed|COST01||persistent
@EDG: E16|CHR01|carries|COST01||persistent
@EDG: E17|SCN02|changed|BOND01||persistent
@EDG: E18|BOND01|between|CHR03|CHR01
@EDG: E19|EVT01|used|charms2||persistent
"@
```

This Step 5 update (in graph language):
- CHOICE01: minimal selection record (short code only).
- CHR01: status updated to a pure code (the linked COST01 carries the "what" via relations).
- SCN02: tiny phase marker (key + phase).
- EVT01, COST01, BOND01: three new atomic nodes. Their fields are only type codes, actor/focus/subject ids, and short reason codes. No English.
- A larger number of EDG rows explicitly wire the semantics (caused, suffered_by, imposed, carries, changed, between, used, etc.).
- Prior transients settled.

The rich literary wording ("shaky blue spark", "thin line of red", "Hermione's mouth tightened", the sting, the earned price) lives only in the novel section the LLM generated in step 2 for the human. Future warm reads see the atomic nodes + the web of EDG names + updated CHR status code; the LLM converts that pure structure back into consistent prose under the governing RULEs and LAW-HP01. This keeps token usage low each round.

**Step 6 — Loop**
Next turn will start with a fresh `query warm --anchor SCN02 --depth 2`. The new scene is now the live focus. The settled choice and prior door scene are gone (or pruned). CHR01 carries the updated status forward. Future challenges will still be governed by LAW-HP01 (always prepended) and will continue to cite the acting attr/skill value in prose and options.

The optional EDG from LAW-HP01 to SCN01 (or the new SCN) is only needed if you want to audit which scenes obeyed the "cite the acting value" rule.

(After this turn the orchestrator may run a settlement/prune pass if other settled rows existed, but here the graph remains small.)

### Follow-on cycle — Consequence prose given to the human

**Context:** The human selected "I choose 1." in the prior turn. The selection was recorded as a minimal chosen key on CHOICE01, and the full graph mutations (CHR status, minimal SCN02 phase marker, small atomic fact LORE rows for the event/cost/shift, EDGs, settlements) were applied in that turn's Step 5 using wire-format nodes and edges. No sentences were stored on any SCN or CHOICE row.

This cycle illustrates the reader-facing consequence prose (generated in its own step 2 from the now-updated small structural rows). The prose the human reads is rich; the graph stays tiny for cheap warm reads.

**Step 1 — Read the state**
```
memnet query warm --anchor CHOICE01 --depth 2 --max-rows 30
```

**Step 2 — Write the novel section**
Warm now includes the pending CHOICE01 (with the human's prior selection), the still-live SCN01, your CHR01 (Charms 2), the companions, the active QUEST, relevant LORE/RULE, and the prepended LAW rows.

**Novel section given to the human (what the reader/player reads right now)**

> The charm left your wand in a shaky blue spark. The silver tracery on the door flared, bit back, and then — with a sound like a breath held too long — the lock yielded. A thin line of red opened across the back of your wand hand where the ward had kissed you. The door moved a handspan, enough to slip through.
>
> Harry slid through first, wand up, and gave you a quick, fierce look. Hermione followed without a word, but her eyes flicked to your hand and away. The chamber on the other side is colder; the air tastes of old stone and something sweeter, like rotting lilies. Your hand stings. The quest has moved one room closer to the Stone, and you carry a small, personal price for having insisted on doing it yourself.

**Remark:** In this turn's step 2 the LLM converts the warm data rows (minimal CHOICE01 with chosen key, CHR01 status code, the EVT/COST/BOND nodes reached via the new SCN02 EDGs, RULE02, LAW-HP01, companions, QUEST progress key, etc.) into the above novel section. The blockquoted text is the human's lived experience. The structural record (minimal SCN + atomic nodes + wires + CHR status code) was already written in the prior turn's Step 5 so that this and future warm reads see only the small skeleton. The LLM turns that skeleton into consistent prose.

**Step 3 — Capture the response**
The human has just read the consequence page above. That page was the output of step 2. The selection itself was already captured in the previous turn (when the CHOICE01 row was first created). This turn the human may add further steering ("make the cost sting more next time", "Hermione is a bit cross", etc.) or simply continue. Any new steering becomes part of the context for step 4/5.

**Step 4 — Analyse the turn (row-mutation focused)**

To determine how the player's concrete selection ("1. Attempt the unlocking charm yourself (your Charms is 2...)") interacts with the live graph, the orchestrator issues additional targeted reads now that the choice is known:

```
memnet query warm --anchor CHOICE01 --depth 1
memnet query warm --anchor CHR01 --depth 1
memnet query warm --anchor RULE02 --depth 1
memnet query warm --anchor QST01 --depth 1
# (these reads surface the exact chosen text, your current attr/status, the toll rule that must be honoured because skill is low, and the quest that may advance or gain a consequence tag)
```

From these reads the interaction is modelled:

"Warm values (from the extra reads + prior context, ids and live fields copied exactly):
- CHOICE01 carries chosen key '1|self'; transient.
- CHR01: Charms:2 , status=shaken_hand per RULE02 + self-cast choice.
- RULE02 (toll), LAW-HP01, QST01 progress key, new minimal SCN02 + its EVT01 / COST01 / BOND01 (and the web of EDG) reachable via anchor/EDG.
- No ITEM consumed.

Row mutations (already executed in the selection turn's Step 5; this cycle is verification + settle):
- CHOICE01 and prior SCN01: settle via recycle.
- (The minimal SCN02, the atomic EVT/COST/BOND nodes, CHR status code, and all the EDG wires were created earlier in graph language.)

The graph holds only the cheap skeleton. The prose the human read came from converting that skeleton in step 2. Ready for settlement or loop."

**Step 5 — Persist the outcome (or verify)**
The mutations (minimal CHOICE01 record, CHR01 status code, minimal SCN02, the atomic EVT/COST/BOND nodes, EDGs, settlements of prior transients) were already sent in graph language in the selection turn's Step 5. This cycle's step 5 can be a settlement pass or no-op. The human experiences the generated consequence prose from step 2.

**Step 6 — Loop**
Next read (e.g. `query warm --anchor SCN02 --depth 2`) surfaces the tiny SCN02 + its linked EVT/COST/BOND nodes + updated CHR01 status code + active QUEST key + LORE/RULEs (prepended LAWs always) + companion links. Settled transients are absent. Future step 2 converts this small skeleton into the next novel page the human reads. Token cost per round stays low because no sentences live in the graph rows.

### Turn 3 — A Canon Touch and a Quiet Cost

**User prompt/steering:** "The toll when a low skill is pushed should be steeper in the rule, and show the PC feeling both the sting and a small, earned pride in the quiet after. Hermione softens a fraction."

**Step 1 — Read the state**
```
memnet query warm --anchor RULE02 --depth 1
# (direct anchor on the persistent rule; also read current SCN for context)
memnet query warm --anchor SCN02 --depth 1 --max-rows 20
```

**Step 2 — Write the novel section**
Warm on RULE02 surfaces the current (old) text plus linked LORE/CHR. Warm on SCN02 surfaces the recent scene + its connections. LAW rows are prepended in both.

**Novel section given to the human (what the reader/player reads right now)**

> A few minutes inside the colder chamber. Your hand still throbs where the ward kissed it. You flex the fingers and the sting answers at once — a reminder that Charms 2 is not a number on a page but a live edge you just pressed against. Harry is already moving toward the next arch, eyes on the dark. Hermione lingers a half-step. She looks at your hand, then at your face.
>
> "You didn't have to do that alone," she says, very low. It is not quite forgiveness, but it is not the closed look she wore at the door. The choice you made — to risk your own shaky skill rather than spend hers — has landed on both of you.
>
> The quest has not changed. The Stone is still ahead. But something small and real has shifted between the three of you, and the toll of pushing a low skill under pressure is no longer just a line in a book.

**Remark:** In step 2 the LLM converts the warm data rows (updated RULE02 + minimal SCN02 + its linked EVT/COST/BOND nodes + CHR status code + companions + prepended LAWs) into this novel section. The blockquoted text is what the human reads. The RULE canon change and the quiet beat's memory (sting, pride, softening) are recorded as atomic nodes + relations so future warm reads (and conversions) stay consistent and cheap. The rich wording is generated, not stored.

**Step 3 — Capture the response**
The human has just read the new beat. The steering revises a persistent RULE (canon) and asks for a quiet progression beat. The orchestrator will persist the RULE update and, for the beat, a minimal SCN phase marker + atomic EVT/COST/BOND nodes (sting memory, earned pride, softening) wired via many EDGs; no sentences in any row.

**Step 4 — Analyse the turn**

After the previous consequence, the user gives new steering that affects canon (the toll rule) and asks for a quiet follow-on beat showing the sting + earned pride + Hermione softening. To decide the exact row interaction, additional reads are performed:

```
memnet query warm --anchor RULE02 --depth 1
memnet query warm --anchor SCN02 --depth 1
memnet query warm --anchor CHR01 --depth 1
memnet query warm --anchor CHR03 --depth 1
# (these let us see the current wording of the rule we are about to tighten, the scene that will be settled or continued from, the player's current status after the door, and Hermione's current regard so we can model the small positive shift)
```

"Warm (ids + live values copied from the reads above):
- RULE02 current text (previous toll rule)
- SCN02 (minimal), CHR01 (shaken_hand, Charms 2), CHR03, QST01, LORE02 + prior EVT/COST/BOND.

Row mutations (structural only):
- RULE02: update code `low_skill_visible_cost` → `low_skill_lingering_cost`
- SCN03: add minimal key=quiet_after , phase=sting_pride_softening , recycle=delete_on_settle
- EVT02: add, type=quiet_sting , actor=CHR01 , focus=self , code=pride
- COST02: add, subject=CHR01 , kind=lingering , site=hand
- BOND02: add, left=CHR03 , right=CHR01 , delta=up , code=soften
- EDGs: SCN03 set_in LORE02, costs CHR01, features CHR03; EVT02/COST02/BOND02 wired to SCN03 + CHR01/03 (caused, suffered, changed, between, etc.)

Copy ids + current RULE text from warm. Step 5 writes the nodes/edges.

**Step 5 — Persist the outcome**
Step 5 sends the node rows and edge rows (graph language). RULE update + minimal SCN phase marker + atomic EVT/COST/BOND for the quiet beat (no sentences anywhere).

```
memnet update --stdin @"
@RULE: RULE02|magic_toll|risk|low_skill_lingering_cost|persistent
@SCN: SCN03|quiet_after|sting_pride_softening|delete_on_settle
@EVT: EVT02|quiet_sting|CHR01|self|pride|delete_on_settle
@COST: COST02|CHR01|lingering|hand|persistent
@BOND: BOND02|CHR03|CHR01|up|soften|persistent
@EDG: E10|SCN03|set_in|LORE02||persistent
@EDG: E11|SCN03|costs|CHR01||persistent
@EDG: E12|SCN03|features|CHR03||persistent
@EDG: E13|SCN03|caused|EVT02||persistent
@EDG: E14|SCN03|imposed|COST02||persistent
@EDG: E15|SCN03|changed|BOND02||persistent
@EDG: E16|CHR01|carries|COST02||persistent
@EDG: E17|BOND02|between|CHR03|CHR01
@EDG: E18|EVT02|suffered_by|CHR01||persistent
"@
```

**Step 6 — Loop**
Next turn begins with `query warm --anchor SCN03`. RULE02 (updated) is reachable when needed. The new minimal SCN03 + its EVT/COST/BOND nodes surface the sting, the small pride, and the softening via the EDG names + CHR status code. Prior SCN02 is absent unless re-anchored. Future step 2 converts the small skeleton into the next prose the human reads.

## Snapshot (full project state)

At any point you can capture *everything* — current story plus all background, configs, bibles, rules, and user prefs:

```powershell
memnet session save --file my-novel.snap
```

Later (new machine, new terminal, after a break):

```powershell
memnet session load --file my-novel.snap
# or --keep-id if you want the old session id
```

The resulting session contains the complete novel project as many small rows. Warm reads prepend **all LAW rows**, then surface fragments the current anchor (plus EDG links) can reach.

## Pipeline-Aware Pitfalls (and how the design helps)

- **Skipping the read (step 1)** and "remembering" that the PC has a trait, attr value or memory from earlier chat → you invent a new fact, a higher skill, or the wrong cost. Fix: every turn starts with `query warm --anchor ...`; copy ids, attr values and facts from the output you actually received.
- **Treating background as external notes or "the model knows"** → LORE/RULE/CHR live only in the graph. If warm does not reach them this turn, they are not in context (**LAW rows are the exception** — always prepended). Fix: anchor or EDG when you need a row; never skip step 1.
- **Using `add` for something that already exists** → `id_exists` (good). Fix: read first, then `update` with the exact id from warm.
- **Forgetting to settle transient work** → `query warm` keeps showing old scenes and choices. Fix: when a scene or choice is done, `update` it with the appropriate `delete_on_settle` (and usually a status change).
- **Mutating a RULE or CHR bible without reading it first in the turn** → you may contradict the current text or use a stale version. Fix: read the row (direct warm anchor or via links), then update.
- **Putting story craft or prefs in LAW** → every warm read bloats; use **RULE** (craft) or **USR** (prefs) with EDG instead.
- **Putting a required stat-cite or challenge rule in RULE** → model may miss it when writing the scene; use a **domain LAW** (e.g. LAW-HP01).
- **Confusing LAW and RULE** → both say “rule” in English; check the tag: `@LAW:` = always on + graph/structure, `@RULE:` = story + on demand.
- **Thinking LAW needs an EDG to appear** → it does not; only RULE/LORE/CHR/etc. need wiring. Optional `constrains` from LAW is for instance bookkeeping, not visibility.
- **Anchoring only on a settled transient id** → warm returns mostly LAW and feels "empty." Fix: move the anchor to the new live SCN/CHR/CHOICE after settlement.
- **Generating "new context" in prose instead of reading rows** → the story drifts from the recorded canon. Fix: the only context that matters is what step 1 + 2 put in the prompt.
- **Putting sentences in any row field** → warm bloats every round. Fix: `LAW-ATOM01|*|on_add|no_sentences|break_to_nodes_edges` applies to every tag. Fields = ids/keys/codes only. Split multi-idea facts into more nodes + `@EDG`. Prose lives only in step 2 output for the human.
- **Using a prose label in LAW `name`** → `name` must be the **governed tag** (`CHR`, `EDG`, `*`, …), not a topic phrase like `year1_challenges` or `atomic_fields`.

## Quick-Start (copy-paste these commands)

```powershell
# Terminal 1
memnet serve
# note the MEMNET_SERVE address if it is not the default

# Terminal 2 (client)
# 1. Extract the schema block (Part A above, the @LORE: ... lines only) to a temp map file.
# PowerShell example:
@'
@LORE: id|name|kind|code|recycle
@RULE: id|name|scope|code|recycle
@CHR: id|name|role|attr|facet|status|recycle
@ITEM: id|name|kind|uses|effect|recycle
@QUEST: id|key|stage|goal|progress|status|recycle
@PLT: id|key|phase|arc|status|recycle
@USR: id|key|value|recycle
@SCN: id|key|phase|recycle
@CHOICE: id|resolves|chosen|recycle
@EVT: id|type|actor|focus|code|recycle
@COST: id|subject|kind|site|recycle
@BOND: id|left|right|delta|code|recycle
'@ | Out-File -Encoding utf8 $env:TEMP\novel.map.txt

memnet session open --map-file $env:TEMP\novel.map.txt
# stderr will print something like: MEMNET_SESSION=mn_3f8a2c1d
$env:MEMNET_SESSION = "mn_3f8a2c1d"

# 2. Add the initial seed (Part B block, the @LAW: ... through the final @EDG: wiring lines). Domain LAWs use the governed tag in the `name` field (`LAW-ATOM01|*|…`, `LAW-HP01|CHR|…`).
# Again using a heredoc for clarity; in practice you can also use --file.
memnet add --stdin @"
@LAW: LAW01|EDG|on_context|hide|settled_edg_unless_anchor
@LAW: LAW02|*|on_add|unique|one_id_add_then_update
@LAW: LAW03|EDG|on_add|validate|src_dist_exist_first
@LAW: LAW04|*|on_add|use_backslash|backslash_pipe_not_bare
@LAW: LAW-ATOM01|*|on_add|no_sentences|break_to_nodes_edges
@LAW: LAW-HP01|CHR|on_turn|stat_cite|cite_chr_attr_step2
@LORE: LORE01|philosophers_stone|artifact|elixir_source|persistent
@LORE: LORE02|philosophers_stone|artifact|voldemort_power_y1|persistent
@LORE: LORE03|quirrell|threat|possessed|persistent
@LORE: LORE04|quirrell|threat|closing_stone|persistent
@RULE: RULE01|choices_wizard|theme|cite_choices_not_ability|persistent
@RULE: RULE02|magic_toll|risk|low_skill_visible_cost|persistent
@RULE: RULE03|one_change|structure|one_state_delta_per_beat|persistent
@CHR: CHR01|You|protagonist|Courage:3|Wit:4|Charms:2|Stealth:3|firstyear_belong|unhurt|persistent
@CHR: CHR02|Harry|ally|brave|scarred|boy_who_lived|persistent
@CHR: CHR03|Hermione|ally|brilliant|loyal|rules_first_help_wary|persistent
@ITEM: ITM01|wiggenweld|consumable|1|steady_spell|persistent
@QUEST: QST01|stone_y1|1|stop_quirrell|final_door_ward|active|persistent
@PLT: PLT01|stone_y1|year-1|stone_not_voldemort|active|persistent
@USR: USR01|scene_length|spare|persistent
@USR: USR02|voice|close-second-wonder|persistent
@SCN: SCN01|final_door|warded|delete_on_settle
@EVT: EVT00|risk|door|charms|bite|persistent
@COST: CST00|CHR01|potential_mark|hand|persistent
@EDG: E01|SCN01|set_in|LORE01||persistent
@EDG: L01|LORE01|risk_if|LORE02||persistent
@EDG: L02|LORE03|seeks|LORE01||persistent
@EDG: L03|LORE04|targets|LORE01||persistent
@EDG: E02|SCN01|features|CHR01||persistent
@EDG: E03|SCN01|features|CHR02||persistent
@EDG: E04|SCN01|features|CHR03||persistent
@EDG: E05|CHR01|governs|RULE01||persistent
@EDG: E06|SCN01|features|ITM01||persistent
@EDG: E07|SCN01|features|EVT00||persistent
@EDG: E08|SCN01|features|CST00||persistent
@EDG: E09|EVT00|applies_to|CHR01||persistent
@EDG: E10|CST00|potential_for|CHR01||persistent
"@

# 3. First read (start of your first pipeline cycle)
memnet query warm --anchor SCN01 --depth 2 --max-rows 30

# 4. Now follow the 6 steps for real. Example first read of Turn 1:
# memnet query warm --anchor SCN01 --depth 2 --max-rows 30
# ... think ...
# memnet add --allow-new-relation --stdin @" ... @CHOICE ... "@
# (then wait for user choice, then continue the loop)
```

Bash users: use `cat <<'EOF' > /tmp/novel.map.txt` and `memnet add --stdin <<'EOF' ... EOF`.

## Diagram — The 6-Step Pipeline as a Loop

```mermaid
flowchart TD
  Start([Loop start]) --> Step1["1. Read the state<br/>query warm --anchor focus<br/>(+ direct reads on LORE/RULE/CHR/PLT/USR when background/config required)"]
  Step1 --> Step2["2. Write the novel section<br/>Warm data rows injected into LLM prompt<br/>LLM converts the data rows into the novel section with selections<br/>and gives the converted text to the human to read"]
  Step2 --> Step3["3. Capture the response<br/>Orchestrator surfaces pending CHOICE or accepts free-form steering<br/>User response captured as data (add/update)"]
  Step3 --> Step4["4. Analyse the turn<br/>LLM reasons over context (incl. background/config rows)<br/>Decides creates vs evolves; must copy ids from warm"]
  Step4 --> Step5["5. Persist the outcome<br/>add (new) / update (changes + settlements)<br/>Transient work gets recycle=delete_on_settle<br/>Persistent background/config updated in place when canon changes"]
  Step5 --> Step6["6. Loop back to 1<br/>Fresh read on next turn; settled transient rows absent from warm<br/>unless still reachable from new anchor"]
  Step6 --> Step1

  subgraph Persistent["Persistent data in MemNet (LAW always prepended; rest via EDG)"]
    LAW_TAG[LAW protocol + domain]
    LORE
    RULE
    CHR_BIBLE
    PLT_MASTER
    USR_PREF
    SCN
    CHOICE
  end
```

**Persistent vs transient (legend for the diagram above)**

- **Persistent:** LORE, RULE, CHR, PLT, USR, domain LAW — survive settlement. **LAW (all rows): always prepended.** Other persistent rows: only when anchor/EDG reaches them.
- **Transient:** SCN, CHOICE, active beat work — settle with `delete_on_settle`.

---

**This file is one documented application example.** Use it as a template for novel-style RPG projects on MemNet: schema, seed, loop, and id/recycle discipline. Voice, plot, theme, and the RPG systems (attributes, items, quests, relationships) are whatever you put into the rows. For engine behaviour see `LLM-GUIDE.md`; for another domain see `application-notes/llm-sysml-v2-modeling.md`.