# LLM Novel Writer — A MemNet Application Note

**Single-file document example.** This file is self-contained. It demonstrates how to drive a long-form, user-steered novel writing session where *every* piece of data lives in MemNet:

- Background and world bible (LORE)
- Style, tone, and mechanical constraints (RULE)
- Character bibles and backstories (CHR)
- High-level plot arcs and volume structure (PLT)
- User writing preferences for *this* project (USR)
- Current scenes, chapters, and in-flight choices (SCN, CHOICE)

No external lore files, no hidden system prompts, no "the model will remember." The graph is the single source of truth. The session can be snapshotted and resumed with `session save` / `session load`.

## The 6-Step Pipeline (the repeating loop)

This is the disciplined loop the orchestrator + LLM follow on every turn. The document's worked examples are structured strictly around these steps.

1. **Read the data if it needs** — selective `query warm --anchor <focus>` (current SCN/CHR/CHOICE, or direct anchors on LORE/RULE/CHR_BIBLE/PLT_MASTER/USR_PREF when background or configuration is required). Use `--depth` and EDG links to pull only what is relevant. Never rely on prior chat messages for facts.

2. **Generate context** — the warm result (LAW rows are *always* prepended, plus connected persistent reference rows + current transient state) becomes the deterministic context injected into the LLM prompt. This is external memory, not hallucinated lore.

3. **User prompt/selection** — the orchestrator surfaces any pending USRCHOICE or accepts free-form steering from the human. The user's input or selection is recorded as first-class data (usually by `add` or `update` of a choice/decision row).

4. **Analyse change to the data** — the LLM reasons over the injected context (explicitly referencing persistent background/configuration rows by id, e.g. "per RULE03", "as described in LORE01"). It decides what must be created or evolved and *must* copy ids from the warm output.

5. **Update the data** — execute `add` for brand-new entities and `update` for changes/settlements/resolutions. Transient creative work (scenes, choices, active beats) is settled with `recycle=delete_on_settle` (or `delete_on_expire`) once resolved. Persistent background/configuration rows are updated in place *only* when the story legitimately changes the canon.

6. **Loop** — return to step 1. The next turn begins with a fresh read. Settled transient rows disappear from `query warm` (unless still connected to the new anchor).

After heavy settlement, optionally run `housekeep prune recyclable --apply` to physically remove settled rows and free cap space. Reference material (LORE, RULE, full CHR bibles, master PLT, USR prefs) is never settled away.

**Persistent vs transient (quick legend)**

- Persistent (survives settlements, visible when anchored or connected via EDG): LORE, RULE, CHR (full bibles), PLT/ARC (master arcs), USR (prefs).
- Transient (created/updated during the current writing, settled with `delete_on_settle` once done): SCN (current/draft scenes), CHOICE (pending decisions), active chapter/beat work.

## Part A: Schema (the user tag map)

This is the map you feed to `memnet session open --map-file`. It defines only the *user* tags for this domain. Fixed tags (EDG and LAW) are always present and do not appear here.

```text
@LORE: id|name|kind|text|recycle
@RULE: id|name|scope|text|recycle
@CHR: id|name|role|traits|backstory|status|recycle
@PLT: id|title|phase|summary|status|recycle
@USR: id|key|value|recycle
@SCN: id|ch|title|summary|text|recycle
@CHOICE: id|scn|prompt|options|chosen|recycle
```

EDG relations used in this example (seed a few at start or use `--allow-new-relation` when genuinely new): `set_in`, `features`, `governs`, `continues`, `resolves`, `costs`, `influences`.

## Part B: Initial Seed (complete starting state)

Copy the block below (or extract it via heredoc) and feed it to `memnet add --stdin` after opening the session with the schema above. This populates the graph with *all* initial data: background, configuration, bibles, and the opening scene. Persistent rows use `persistent` (or omit the field); the opening scene is marked transient so it can be settled later.

```text
@LAW: LAW01|edge_recycle|on_context|hide|delete_on_expire and delete_on_settle EDG unless anchor touches src or dist
@LAW: LAW02|node_id|on_add|unique|one row per global id use add then update same tag only
@LAW: LAW03|edge_endpoints|on_add|validate|prefer src and dist to reference existing node ids before settle
@LAW: LAW04|field_escape|on_add|use_backslash|pipe inside one field value is backslash pipe not bare pipe

@LORE: LORE01|The Ashen Marches|region|A blasted frontier where the Ashblight creeps nightly. Ash is both dust and hunger. Villages survive by flame-runes and hard bargains.|persistent
@LORE: LORE02|Ashblight|malady|Living dust that devours crops, breath, and memory. Only certain relics and prices can turn it.|persistent

@RULE: RULE01|Grim tone|voice|Close third, spare prose, no heroic fanfare. Hope is earned and usually costs.|persistent
@RULE: RULE02|Power costs|magic|Every working of power demands a personal, lasting price. No clean victories.|persistent
@RULE: RULE03|Scene economy|pacing|One clear change of state or knowledge per scene. End on consequence or decision.|persistent
@RULE: RULE04|User prefs|project|Keep scenes concise. Favour internal cost over spectacle. When in doubt, tighten.|persistent

@CHR: CHR01|Kael Voss|protagonist|stoic|scarred ex-warder|Once broke an oath to save a town; the guilt still governs him. Fears becoming the thing he fought.|haunted|persistent
@CHR: CHR02|Elder Sira|mentor|pragmatic|village elder|Will sacrifice anything to keep the last families alive. Sees Kael as the last usable weapon.|persistent

@PLT: PLT01|The Ash Crown|volume-1|Kael must decide what (and who) he is willing to burn to stop the blight from reaching the last safe valley.|active|persistent

@USR: USR01|scene_length|concise|persistent
@USR: USR02|voice|close-third-cost|persistent

@SCN: SCN01|01|The Last Hearth|Kael arrives at the last unblighted village as the Ash wind rises. Elder Sira waits with a relic and a price.|The hearth is the only light for miles. Sira offers the Crown-ash relic: it can turn the blight, but using it will mark the bearer with an ever-hungrier hunger. Three paths are possible: burn the relic and the village with it, bargain with the Ash directly, or flee with the sick and abandon the rest. The choice will change Kael and the land.|delete_on_settle

@EDG: E01|SCN01|set_in|LORE01||persistent
@EDG: E02|SCN01|features|CHR01||persistent
@EDG: E03|SCN01|features|CHR02||persistent
@EDG: E04|CHR01|governs|RULE02||persistent
```

## The 6-Step Pipeline (command-level view)

**Orchestrator responsibilities (the harness around the LLM):**
- Always begin the turn with a read (step 1).
- Inject exactly the warm output (plus any directly read background) as the context (step 2).
- Surface choices or steering to the human and turn the response into data rows (step 3).
- Execute only the `add`/`update` commands the LLM emits in step 5 (after validation / dry-run if nervous).
- After settlement, optionally prune; always start the next turn with a fresh read.

The LLM never "remembers" ids or facts across turns. It only ever sees what step 1 + 2 put in front of it.

## Part D: Worked Turns (the pipeline in action)

Three compact turns. Each is shown strictly as the six numbered steps. Warm output excerpts include the prepended `@LAW:` rows. All ids are copied from the warm/context output. Transient rows are settled with `delete_on_settle` when their work is done. One turn demonstrates a legitimate update to a persistent RULE when the story changes the world's "canon."

### Turn 1 — The First Hard Choice

**User prompt/steering:** "Kael reaches the village. The elder offers the relic. Give the player a real, costly choice. Do not resolve it yet."

**Step 1 — Read the data if it needs**
```
memnet query warm --anchor SCN01 --depth 2 --max-rows 30
```

**Step 2 — Generate context (warm output excerpt)**
```
@LAW: LAW01 edge_recycle on_context hide delete_on_expire and delete_on_settle EDG unless anchor touches src or dist
@LAW: LAW02 node_id on_add unique one row per global id use add then update same tag only
@LAW: LAW03 edge_endpoints on_add validate prefer src and dist to reference existing node ids before settle
@LAW: LAW04 field_escape on_add use_backslash pipe inside one field value is backslash pipe not bare pipe
@LORE: LORE01|The Ashen Marches|region|...
@LORE: LORE02|Ashblight|malady|...
@RULE: RULE01|Grim tone|voice|...
@RULE: RULE02|Power costs|magic|Every working of power demands a personal, lasting price...
@RULE: RULE03|Scene economy|pacing|...
@CHR: CHR01|Kael Voss|protagonist|stoic|...|haunted|persistent
@CHR: CHR02|Elder Sira|mentor|pragmatic|...|persistent
@SCN: SCN01|01|The Last Hearth|Kael arrives...|...|delete_on_settle
@EDG: E01|SCN01|set_in|LORE01||persistent
@EDG: E02|SCN01|features|CHR01||persistent
@EDG: E03|SCN01|features|CHR02||persistent
```

**Step 3 — User prompt/selection**
The user prompt above is the steering. The agent will surface the dilemma as a pending choice row rather than resolving it in prose. (The human will pick later.)

**Step 4 — Analyse change to the data**
"Context gives me LORE01/02, RULE02 (power costs), CHR01 (Kael's guilt), and the current SCN01. Per RULE03 we end on a decision. I will not write the choice in the scene text; instead I add a CHOICE row so the human decides. I will copy ids exactly: SCN01, CHR01, RULE02, LORE01. New id for the choice: CHOICE01. Relation `resolves` is new here; I will use `--allow-new-relation` once."

**Step 5 — Update the data**
```
memnet add --allow-new-relation --stdin @"
@CHOICE: CHOICE01|SCN01|The elder offers the Crown-ash relic. Using it will mark the bearer with an ever-hungrier hunger. Three paths: burn the relic and the village with it; bargain with the Ash directly through the relic; flee with the sick and abandon the rest. What does Kael do?|Burn the relic / Bargain with the Ash / Flee with the sick||delete_on_settle
"@
```

**Step 6 — Loop**
Next turn will start with a fresh `query warm --anchor CHOICE01` (or SCN01). The choice row is now the live focus. SCN01 remains visible while the choice is unresolved.

(After this turn the orchestrator might optionally prune if other settled rows existed, but here the graph is still small.)

### Turn 2 — The Human Chooses; Consequence Is Written

**User prompt/selection:** "I choose 'Bargain with the Ash'. Kael accepts the mark to save the village. Show the immediate cost and move to the next scene."

**Step 1 — Read the data if it needs**
```
memnet query warm --anchor CHOICE01 --depth 2 --max-rows 30
```

**Step 2 — Generate context**
Warm now surfaces the pending CHOICE01, the still-active SCN01, linked LORE/RULE/CHR, and the prepended LAW rows (not repeated here for brevity).

**Step 3 — User prompt/selection**
The human's choice text is captured. The orchestrator will turn it into an update of CHOICE01 and a new scene.

**Step 4 — Analyse change to the data**
"CHOICE01 is still open. Per RULE02 the bargain must cost Kael something permanent. I will:
- update CHOICE01 with chosen and a short consequence note
- update CHR01 status to reflect the new hunger/mark (canon change to character)
- add SCN02 for the immediate aftermath
- settle CHOICE01 and SCN01 with delete_on_settle
- add one EDG from SCN02 to CHR01 (features) and one to LORE02 (set_in)
I will copy every id from the current warm output. No new ids for existing people."

**Step 5 — Update the data**
```
memnet update --stdin @"
@CHOICE: CHOICE01|SCN01|The elder offers the Crown-ash relic...|Burn the relic / Bargain with the Ash / Flee with the sick|Bargain with the Ash|Kael accepts the Ash mark to spare the village. The hunger now lives in him.|delete_on_settle
@CHR: CHR01|Kael Voss|protagonist|stoic|scarred ex-warder|Once broke an oath... Now carries the Ash hunger as a living brand. The mark answers when he is weak.|marked|persistent
@SCN: SCN02|02|The Mark Settles|The bargain is struck at the hearth. Ash coils into Kael's scar and does not leave. The village is spared for now; the debt has a name.|Kael's breath frosts black at the edges. He can feel the blight listening. Sira watches with relief and horror. The relic is quiet, but something else is awake inside the man.|delete_on_settle
@EDG: E05|SCN02|set_in|LORE02||persistent
@EDG: E06|SCN02|features|CHR01||persistent
"@
```

**Step 6 — Loop**
Next read (e.g. `query warm --anchor SCN02`) will not show the settled CHOICE01 or SCN01 unless they remain directly connected to the new anchor. CHR01 (persistent) and the LORE/RULE rows remain available.

### Turn 3 — A Canon Change to a Persistent Rule

**User prompt/steering:** "The hunger is worse than we said. Update the world's rule about power costs to make the price steeper and more personal. Then show Kael feeling the new cost in the next quiet moment."

**Step 1 — Read the data if it needs**
```
memnet query warm --anchor RULE02 --depth 1
# (direct anchor on the persistent rule; also read current SCN for context)
memnet query warm --anchor SCN02 --depth 1 --max-rows 20
```

**Step 2 — Generate context**
Warm on RULE02 surfaces the current (old) text plus linked LORE/CHR. Warm on SCN02 surfaces the recent scene + its connections. LAW rows are prepended in both.

**Step 3 — User prompt/selection**
The steering is a direct request to change a persistent world rule. The orchestrator treats this as an update to RULE02 (canon revision) plus a follow-on scene.

**Step 4 — Analyse change to the data**
"User wants a steeper, more personal cost in RULE02. I must read the current text first (done), then update the row in place because this is a legitimate canon change. I will also add a short follow-on beat (SCN03) showing Kael experiencing the harsher price, settle SCN02, and link the new scene. Copy ids: RULE02, SCN02, CHR01, LORE02."

**Step 5 — Update the data**
```
memnet update --stdin @"
@RULE: RULE02|Power costs|magic|Every working of power demands a personal, lasting price — and the price now grows with use. The Ash remembers what you gave and asks for more next time. There is no ceiling.|persistent
@SCN: SCN03|03|The Hunger Answers|A quiet hour after the bargain. Kael tries to warm a dying child with a spark of will. The Ash answers — and takes a memory he did not mean to offer.|Kael's spark saves the child, but when he wakes the next morning he cannot remember the name of his first dog. The hunger is not satisfied; it is awake and counting.|delete_on_settle
@EDG: E07|SCN03|set_in|LORE02||persistent
@EDG: E08|SCN03|costs|CHR01||persistent
"@
```

**Step 6 — Loop**
Next turn begins with `query warm --anchor SCN03`. RULE02 (updated) remains visible when needed because it is persistent and connected. SCN02 is now absent from warm unless explicitly reached.

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

The resulting session contains the complete novel project. Warm reads will surface whatever the current anchor can reach, including the persistent reference rows.

## Pipeline-Aware Pitfalls (and how the design helps)

- **Skipping the read (step 1)** and "remembering" that Kael has trait X from earlier chat → you invent a new CHR id or use the wrong status. Fix: every turn starts with `query warm --anchor ...`; copy ids from the output you actually received.
- **Treating background as external notes or "the model knows"** → LORE/RULE/CHR bibles live only in the graph. If you do not read them this turn, they are not in context. Fix: anchor on them or ensure EDG links when you need them.
- **Using `add` for something that already exists** → `id_exists` (good). Fix: read first, then `update` with the exact id from warm.
- **Forgetting to settle transient work** → `query warm` keeps showing old scenes and choices. Fix: when a scene or choice is done, `update` it with the appropriate `delete_on_settle` (and usually a status change).
- **Mutating a RULE or CHR bible without reading it first in the turn** → you may contradict the current text or use a stale version. Fix: read the row (direct warm anchor or via links), then update.
- **Anchoring only on a settled transient id** → warm returns mostly LAW and feels "empty." Fix: move the anchor to the new live SCN/CHR/CHOICE after settlement.
- **Generating "new context" in prose instead of reading rows** → the story drifts from the recorded canon. Fix: the only context that matters is what step 1 + 2 put in the prompt.

## Quick-Start (copy-paste these commands)

```powershell
# Terminal 1
memnet serve
# note the MEMNET_SERVE address if it is not the default

# Terminal 2 (client)
# 1. Extract the schema block (Part A above, the @LORE: ... lines only) to a temp map file.
# PowerShell example:
@'
@LORE: id|name|kind|text|recycle
@RULE: id|name|scope|text|recycle
@CHR: id|name|role|traits|backstory|status|recycle
@PLT: id|title|phase|summary|status|recycle
@USR: id|key|value|recycle
@SCN: id|ch|title|summary|text|recycle
@CHOICE: id|scn|prompt|options|chosen|recycle
'@ | Out-File -Encoding utf8 $env:TEMP\novel.map.txt

memnet session open --map-file $env:TEMP\novel.map.txt
# stderr will print something like: MEMNET_SESSION=mn_3f8a2c1d
$env:MEMNET_SESSION = "mn_3f8a2c1d"

# 2. Add the initial seed (Part B block, the @LAW: ... through @EDG: lines).
# Again using a heredoc for clarity; in practice you can also use --file.
memnet add --stdin @"
@LAW: LAW01|edge_recycle|on_context|hide|delete_on_expire and delete_on_settle EDG unless anchor touches src or dist
@LAW: LAW02|node_id|on_add|unique|one row per global id use add then update same tag only
@LAW: LAW03|edge_endpoints|on_add|validate|prefer src and dist to reference existing node ids before settle
@LAW: LAW04|field_escape|on_add|use_backslash|pipe inside one field value is backslash pipe not bare pipe
@LORE: LORE01|The Ashen Marches|region|A blasted frontier where the Ashblight creeps nightly. Ash is both dust and hunger. Villages survive by flame-runes and hard bargains.|persistent
@LORE: LORE02|Ashblight|malady|Living dust that devours crops, breath, and memory. Only certain relics and prices can turn it.|persistent
@RULE: RULE01|Grim tone|voice|Close third, spare prose, no heroic fanfare. Hope is earned and usually costs.|persistent
@RULE: RULE02|Power costs|magic|Every working of power demands a personal, lasting price. No clean victories.|persistent
@RULE: RULE03|Scene economy|pacing|One clear change of state or knowledge per scene. End on consequence or decision.|persistent
@RULE: RULE04|User prefs|project|Keep scenes concise. Favour internal cost over spectacle. When in doubt, tighten.|persistent
@CHR: CHR01|Kael Voss|protagonist|stoic|scarred ex-warder|Once broke an oath to save a town; the guilt still governs him. Fears becoming the thing he fought.|haunted|persistent
@CHR: CHR02|Elder Sira|mentor|pragmatic|village elder|Will sacrifice anything to keep the last families alive. Sees Kael as the last usable weapon.|persistent
@PLT: PLT01|The Ash Crown|volume-1|Kael must decide what (and who) he is willing to burn to stop the blight from reaching the last safe valley.|active|persistent
@USR: USR01|scene_length|concise|persistent
@USR: USR02|voice|close-third-cost|persistent
@SCN: SCN01|01|The Last Hearth|Kael arrives at the last unblighted village as the Ash wind rises. Elder Sira waits with a relic and a price.|The hearth is the only light for miles. Sira offers the Crown-ash relic: it can turn the blight, but using it will mark the bearer with an ever-hungrier hunger. Three paths are possible: burn the relic and the village with it, bargain with the Ash directly, or flee with the sick and abandon the rest. The choice will change Kael and the land.|delete_on_settle
@EDG: E01|SCN01|set_in|LORE01||persistent
@EDG: E02|SCN01|features|CHR01||persistent
@EDG: E03|SCN01|features|CHR02||persistent
@EDG: E04|CHR01|governs|RULE02||persistent
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
  Start([Loop start]) --> Step1["1. Read the data if it needs<br/>query warm --anchor focus<br/>(+ direct reads on LORE/RULE/CHR/PLT/USR when background/config required)"]
  Step1 --> Step2["2. Generate context<br/>Warm slice (LAW rows always prepended + connected persistent rows + transient state)<br/>becomes the deterministic injected context"]
  Step2 --> Step3["3. User prompt/selection<br/>Orchestrator surfaces pending USRCHOICE or accepts steering<br/>User response captured as data (add/update)"]
  Step3 --> Step4["4. Analyse change to the data<br/>LLM reasons over context (incl. background/config rows)<br/>Decides creates vs evolves; must copy ids from warm"]
  Step4 --> Step5["5. Update the data<br/>add (new) / update (changes + settlements)<br/>Transient work gets recycle=delete_on_settle<br/>Persistent background/config updated in place when canon changes"]
  Step5 --> Step6["6. Loop back to 1<br/>Fresh read on next turn; settled transient rows absent from warm<br/>unless still reachable from new anchor"]
  Step6 --> Step1

  subgraph Persistent["All data (background + config + bibles + rules + prefs + current story) lives in MemNet"]
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

- Persistent (stays across settlements, visible when anchored or connected): LORE, RULE, CHR (full bibles), PLT/ARC (master), USR (prefs).
- Transient (created/updated during writing, settled with `delete_on_settle` once done): SCN (current scenes), CHOICE (pending decisions), active chapter/beat work.

---

**Read this file at the start of any novel-writing project that uses MemNet.** The schema, the seed pattern, the 6-step loop, and the id + recycle discipline are the whole game. Everything else (voice, plot, theme) is just what you put into the rows.