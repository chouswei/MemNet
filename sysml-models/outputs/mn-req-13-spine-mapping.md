# MN-REQ-13 spine mapping

Reparent of agent-facing requirements under **Recall(q)** or **Commit(Δ)**.
Requirement ids are unchanged. Organisational nesting of groups
MN-REQ-01…12 under MN-REQ-00 is unchanged this cut (importers, ops,
cousins, and archive stay put). Spine parentage is `#derivation`
to `MN-REQ-13.Recall` or `MN-REQ-13.Commit`. Session open / save /
close stay on MN-REQ-01 as the other agent-surface verbs.

Source of the table: `agentSurface` on each requirement def in
`models/requirements.sysml`.

## Later PRs (not this cut)

- Split deploy/ops out of MN-REQ-06 / `deploy.sysml` ops parts.
- Move Path-B importers (MN-REQ-11.6…11.16) to a dedicated ingest nest.
- Move `cousins.sysml` / `archive.sysml` (or rename leftover coinages).
- Merge-and-report as a Commit rule (owner decision; 03.1–03.3 stay strict).

## Spine tree

```text
MN-REQ-00 Mission
├── MN-REQ-13 RecallCommit                         SPINE
│   ├── MN-REQ-13.1 TwoOperators
│   ├── MN-REQ-13.Recall   Recall(q) = pin_map
│   │   └── agent-facing read leaves via #derivation
│   │       (04.* minus housekeep, 02.4, 05.2, 08.7/08.9,
│   │        10.2/10.3/10.6, find/export options, 12.4 pin_map)
│   └── MN-REQ-13.Commit   Commit(Δ) = mutate
│       ├── MN-REQ-13.2 SameThingAbsorb            nested
│       └── agent-facing write leaves via #derivation
│           (03.* strict mutate unchanged, ingest/snap options,
│            Absorb / RSV options)
├── MN-REQ-01 SessionLifecycle   open / save / close
├── MN-REQ-02, 05, 07–12         organisational groups (importers stay)
└── MN-REQ-06 ProcessBoundary    ops (later PR may split)
```

Agent surface verbs: **recall**, **commit**, **session open**, **save**, **close**.

## Counts

- Requirement defs / usages: **132** (130 at ab0d2db plus spine arms `MN-REQ-13.Recall` and `MN-REQ-13.Commit`).
- Under Recall (`Recall` + `option:Recall`): **26**
- Under Commit (`Commit` + `option:Commit`): **30**
- Session surface (`session` + `option:session`): **10**
- Internal: **44**
- Ops: **17**
- Other (mission / spine / surface listing): **5**
- Named by some `verify`: **52**; still unverified: **80** (the previous 78 plus the two new arms).
- `agentSurface` breakdown: mission 1, session 7, option:session 3, Recall 19, option:Recall 7, Commit 8, option:Commit 22, internal 44, ops 17, surface 2, spine 2.

## Mapping (old organisational parent → new spine parent)

| Id | Old parent | New parent | agentSurface | Note |
|----|------------|------------|--------------|------|
| `MN-REQ-00` | `—` | `—` | `mission` | mission root; not an operator |
| `MN-REQ-01` | `MN-REQ-00` | `MN-REQ-01 (session surface; not Recall/Commit)` | `session` | session open / save / close (agent surface beside Recall and Commit) |
| `MN-REQ-01.1` | `MN-REQ-01` | `MN-REQ-01 (session surface; not Recall/Commit)` | `session` | named sessions; session id is the mission handle |
| `MN-REQ-01.2` | `MN-REQ-01` | `MN-REQ-01 (session surface; not Recall/Commit)` | `session` | open, resume, and close |
| `MN-REQ-01.3` | `MN-REQ-01` | `internal (stays under organisational group)` | `internal` | TTL and concurrent-session caps; not an agent verb |
| `MN-REQ-01.4` | `MN-REQ-01` | `MN-REQ-01 (session surface; not Recall/Commit)` | `session` | session_save |
| `MN-REQ-01.5` | `MN-REQ-01` | `MN-REQ-01 (session surface; not Recall/Commit)` | `option:session` | session_load — option of save |
| `MN-REQ-01.6` | `MN-REQ-01` | `MN-REQ-01 (session surface; not Recall/Commit)` | `option:session` | keep_id on load — option of save |
| `MN-REQ-01.7` | `MN-REQ-01` | `MN-REQ-01 (session surface; not Recall/Commit)` | `session` | session id is the handoff capability and secret; keep unchanged |
| `MN-REQ-01.8` | `MN-REQ-01` | `MN-REQ-01 (session surface; not Recall/Commit)` | `session` | no graph dump on handoff; keep unchanged |
| `MN-REQ-01.9` | `MN-REQ-01` | `internal (stays under organisational group)` | `internal` | snapshot lossless round-trip; save integrity |
| `MN-REQ-01.10` | `MN-REQ-01` | `internal (stays under organisational group)` | `internal` | ACL who-check on save / load / close |
| `MN-REQ-02` | `MN-REQ-00` | `internal (stays under organisational group)` | `internal` | graph identity / grammar; organisational |
| `MN-REQ-02.1` | `MN-REQ-02` | `internal (stays under organisational group)` | `internal` | exactly node and edge |
| `MN-REQ-02.2` | `MN-REQ-02` | `internal (stays under organisational group)` | `internal` | nodes hold atomised facts |
| `MN-REQ-02.3` | `MN-REQ-02` | `internal (stays under organisational group)` | `internal` | edges are first class |
| `MN-REQ-02.4` | `MN-REQ-02` | `MN-REQ-13.Recall` | `Recall` | query over the node/edge graph is Recall |
| `MN-REQ-02.5` | `MN-REQ-02` | `internal (stays under organisational group)` | `internal` | grammar expresses node and edge |
| `MN-REQ-02.6` | `MN-REQ-02` | `internal (stays under organisational group)` | `internal` | parser recovers node and edge; parser is SSOT |
| `MN-REQ-02.7` | `MN-REQ-02` | `MN-REQ-13.Commit` | `option:Commit` | schema-validated ingest — option of Commit |
| `MN-REQ-02.8` | `MN-REQ-02` | `internal (stays under organisational group)` | `internal` | id not required on the wire |
| `MN-REQ-02.9` | `MN-REQ-02` | `internal (stays under organisational group)` | `internal` | MUST NOT copy cousin store-key / embedding Recall |
| `MN-REQ-03` | `MN-REQ-00` | `MN-REQ-13.Commit` | `Commit` | strict mutate group; spine parent Commit |
| `MN-REQ-03.1` | `MN-REQ-03` | `MN-REQ-13.Commit` | `Commit` | AddFailsIfExists; unchanged; merge-and-report pending |
| `MN-REQ-03.2` | `MN-REQ-03` | `MN-REQ-13.Commit` | `Commit` | UpdateFailsIfAbsent; unchanged |
| `MN-REQ-03.3` | `MN-REQ-03` | `MN-REQ-13.Commit` | `Commit` | no silent upsert; unchanged; merge-and-report is owner-pending |
| `MN-REQ-03.4` | `MN-REQ-03` | `MN-REQ-13.Commit` | `Commit` | honour WHERE or refuse |
| `MN-REQ-04` | `MN-REQ-00` | `MN-REQ-13.Recall` | `Recall` | slice economy / pin_map group; spine parent Recall |
| `MN-REQ-04.1` | `MN-REQ-04` | `MN-REQ-13.Recall` | `Recall` | bounded live pin_map |
| `MN-REQ-04.2` | `MN-REQ-04` | `MN-REQ-13.Recall` | `Recall` | hide recycled rows from pin_map |
| `MN-REQ-04.3` | `MN-REQ-04` | `MN-REQ-13.Recall` | `Recall` | hard depth/row caps; truncation flagged on the wire |
| `MN-REQ-04.4` | `MN-REQ-04` | `MN-REQ-13.Recall` | `Recall` | prepend engine-law rows on pin_map |
| `MN-REQ-04.5` | `MN-REQ-04` | `MN-REQ-13.Recall` | `option:Recall` | query_walk / anchored walk — leftover option of Recall |
| `MN-REQ-04.6` | `MN-REQ-04` | `MN-REQ-13.Recall` | `option:Recall` | find — bounded MATCH seed; option of Recall |
| `MN-REQ-04.7` | `MN-REQ-04` | `MN-REQ-13.Recall` | `Recall` | RelativeSeed then ShapeWalk |
| `MN-REQ-04.8` | `MN-REQ-04` | `MN-REQ-13.Recall` | `Recall` | CueConflict when |Q|>1; no absorb in Recall |
| `MN-REQ-04.9` | `MN-REQ-04` | `MN-REQ-13.Recall` | `Recall` | empty cue returns the session outline; keep unchanged |
| `MN-REQ-04.10` | `MN-REQ-04` | `MN-REQ-13.Recall` | `Recall` | Peak_L last-resort cue |
| `MN-REQ-04.11` | `MN-REQ-04` | `MN-REQ-13.Recall` | `Recall` | pin_map order from Shape observables |
| `MN-REQ-04.12` | `MN-REQ-04` | `internal (stays under organisational group)` | `internal` | housekeep endpoint identity; not an agent verb |
| `MN-REQ-05` | `MN-REQ-00` | `internal (stays under organisational group)` | `internal` | hard caps group; leaves split across Recall / Commit / internal |
| `MN-REQ-05.1` | `MN-REQ-05` | `internal (stays under organisational group)` | `internal` | store resource caps |
| `MN-REQ-05.2` | `MN-REQ-05` | `MN-REQ-13.Recall` | `Recall` | query fan-out caps; truncation flagged on the wire |
| `MN-REQ-05.3` | `MN-REQ-05` | `MN-REQ-13.Commit` | `Commit` | one value-byte cap on mutate and snapshot load |
| `MN-REQ-06` | `MN-REQ-00` | `MN-REQ-06 (ops; later PR may split)` | `ops` | process / transport / fleet; later PR may split deploy/ops |
| `MN-REQ-06.1` | `MN-REQ-06` | `MN-REQ-06 (ops; later PR may split)` | `ops` | in-process primary binding |
| `MN-REQ-06.2` | `MN-REQ-06` | `MN-REQ-06 (ops; later PR may split)` | `ops` | local IPC share |
| `MN-REQ-06.3` | `MN-REQ-06` | `MN-REQ-06 (ops; later PR may split)` | `ops` | TCP serve migration |
| `MN-REQ-06.4` | `MN-REQ-06` | `MN-REQ-06 (ops; later PR may split)` | `ops` | durable store behind MemNet |
| `MN-REQ-06.5` | `MN-REQ-06` | `MN-REQ-06 (ops; later PR may split)` | `ops` | human usage look; not agent wire |
| `MN-REQ-06.6` | `MN-REQ-06` | `MN-REQ-06 (ops; later PR may split)` | `ops` | device services / one droplet MemNet MCP |
| `MN-REQ-06.7` | `MN-REQ-06` | `MN-REQ-06 (ops; later PR may split)` | `ops` | SSOT → code allocate |
| `MN-REQ-06.8` | `MN-REQ-06` | `MN-REQ-06 (ops; later PR may split)` | `ops` | tip MemNet access portal |
| `MN-REQ-06.9` | `MN-REQ-06` | `MN-REQ-06 (ops; later PR may split)` | `ops` | LAN MCP front; inventOnly |
| `MN-REQ-06.10` | `MN-REQ-06` | `MN-REQ-06 (ops; later PR may split)` | `ops` | SliceHandCarry; inventOnly |
| `MN-REQ-06.11` | `MN-REQ-06` | `MN-REQ-06 (ops; later PR may split)` | `ops` | admin serve usage report |
| `MN-REQ-06.12` | `MN-REQ-06` | `MN-REQ-06 (ops; later PR may split)` | `ops` | product gateway |
| `MN-REQ-06.13` | `MN-REQ-06` | `MN-REQ-06 (ops; later PR may split)` | `ops` | serve request isolation |
| `MN-REQ-06.14` | `MN-REQ-06` | `MN-REQ-06 (ops; later PR may split)` | `ops` | safe serve upgrade |
| `MN-REQ-06.15` | `MN-REQ-06` | `MN-REQ-06 (ops; later PR may split)` | `ops` | admin checkpoint |
| `MN-REQ-07` | `MN-REQ-00` | `MN-REQ-13 (names the five verbs)` | `surface` | MCP/CLI boundary group; names the agent surface |
| `MN-REQ-07.1` | `MN-REQ-07` | `MN-REQ-13 (names the five verbs)` | `surface` | agent surface is exactly recall, commit, session open, save, and close |
| `MN-REQ-07.2` | `MN-REQ-07` | `internal (stays under organisational group)` | `internal` | structured tool envelope |
| `MN-REQ-07.3` | `MN-REQ-07` | `internal (stays under organisational group)` | `internal` | no domain-product tools on generic MCP |
| `MN-REQ-07.4` | `MN-REQ-07` | `MN-REQ-01 (session surface; not Recall/Commit)` | `option:session` | law-seed on session_open — option of open |
| `MN-REQ-07.5` | `MN-REQ-07` | `internal (stays under organisational group)` | `internal` | no store-key tool surface |
| `MN-REQ-08` | `MN-REQ-00` | `internal (stays under organisational group)` | `internal` | agent I/O grammar; applies to both operators |
| `MN-REQ-08.1` | `MN-REQ-08` | `internal (stays under organisational group)` | `internal` | LLM-friendly stdio |
| `MN-REQ-08.2` | `MN-REQ-08` | `internal (stays under organisational group)` | `internal` | LLM-friendly MCP |
| `MN-REQ-08.3` | `MN-REQ-08` | `internal (stays under organisational group)` | `internal` | no hostile positional dump |
| `MN-REQ-08.4` | `MN-REQ-08` | `internal (stays under organisational group)` | `internal` | boundary-friendly if internal differs |
| `MN-REQ-08.5` | `MN-REQ-08` | `internal (stays under organisational group)` | `internal` | I/O actor is the LLM |
| `MN-REQ-08.6` | `MN-REQ-08` | `internal (stays under organisational group)` | `internal` | follow prompt rules |
| `MN-REQ-08.7` | `MN-REQ-08` | `MN-REQ-13.Recall` | `Recall` | Write = display = shaped pin_map emit |
| `MN-REQ-08.8` | `MN-REQ-08` | `internal (stays under organisational group)` | `internal` | template-copyable shapes |
| `MN-REQ-08.9` | `MN-REQ-08` | `MN-REQ-13.Recall` | `Recall` | pin_map emit same family as mutate; Commit shares the grammar |
| `MN-REQ-09` | `MN-REQ-00` | `internal (stays under organisational group)` | `internal` | human inspect; parser is SSOT |
| `MN-REQ-09.1` | `MN-REQ-09` | `internal (stays under organisational group)` | `internal` | canonical parser SSOT; keep unchanged |
| `MN-REQ-09.2` | `MN-REQ-09` | `internal (stays under organisational group)` | `internal` | reject invalid wire |
| `MN-REQ-09.3` | `MN-REQ-09` | `internal (stays under organisational group)` | `internal` | parse-faithful inspect |
| `MN-REQ-09.4` | `MN-REQ-09` | `internal (stays under organisational group)` | `internal` | no ad-hoc consumer splits |
| `MN-REQ-09.5` | `MN-REQ-09` | `internal (stays under organisational group)` | `internal` | GraphGlot parse then product gate |
| `MN-REQ-10` | `MN-REQ-00` | `internal (stays under organisational group)` | `internal` | LLM assumed properties and limits |
| `MN-REQ-10.1` | `MN-REQ-10` | `internal (stays under organisational group)` | `internal` | chat is not durable store |
| `MN-REQ-10.2` | `MN-REQ-10` | `MN-REQ-13.Recall` | `Recall` | pin_map must fit context |
| `MN-REQ-10.3` | `MN-REQ-10` | `MN-REQ-13.Recall` | `Recall` | minimise token round-trips |
| `MN-REQ-10.4` | `MN-REQ-10` | `internal (stays under organisational group)` | `internal` | external ground truth required |
| `MN-REQ-10.5` | `MN-REQ-10` | `internal (stays under organisational group)` | `internal` | grammar must be LLM-learnable |
| `MN-REQ-10.6` | `MN-REQ-10` | `MN-REQ-13.Recall` | `Recall` | prefer template-friendly pins |
| `MN-REQ-10.7` | `MN-REQ-10` | `internal (stays under organisational group)` | `internal` | human verify via parser |
| `MN-REQ-11` | `MN-REQ-00` | `MN-REQ-13.Commit` | `option:Commit` | snapshot / ingest interop; importers stay here this cut |
| `MN-REQ-11.1` | `MN-REQ-11` | `MN-REQ-13.Recall` | `option:Recall` | export_pin_map is a GQL write-out of a cue pin_map (option of Recall); SysML v2 reverse is not claimed |
| `MN-REQ-11.2` | `MN-REQ-11` | `MN-REQ-13.Recall` | `option:Recall` | SysML node mapping of export; live code is GQL pin_map write-out, not .sysml reverse |
| `MN-REQ-11.3` | `MN-REQ-11` | `MN-REQ-13.Recall` | `option:Recall` | SysML edge mapping of export; live code is GQL pin_map write-out, not .sysml reverse |
| `MN-REQ-11.4` | `MN-REQ-11` | `internal (stays under organisational group)` | `internal` | pin-map export/ingest distinct from session snapshot |
| `MN-REQ-11.5` | `MN-REQ-11` | `MN-REQ-13.Recall` | `option:Recall` | SysML round-trip SHOULD; not claimed from ingest or export_pin_map |
| `MN-REQ-11.6` | `MN-REQ-11` | `MN-REQ-13.Commit` | `option:Commit` | ingest_codebase — option of Commit |
| `MN-REQ-11.7` | `MN-REQ-11` | `MN-REQ-13.Commit` | `option:Commit` | codebase nodes; option of Commit |
| `MN-REQ-11.8` | `MN-REQ-11` | `MN-REQ-13.Commit` | `option:Commit` | codebase edges; option of Commit |
| `MN-REQ-11.9` | `MN-REQ-11` | `MN-REQ-13.Commit` | `option:Commit` | ingest_pcba / .ato — option of Commit |
| `MN-REQ-11.10` | `MN-REQ-11` | `MN-REQ-13.Commit` | `option:Commit` | ingest_skills — option of Commit |
| `MN-REQ-11.11` | `MN-REQ-11` | `MN-REQ-13.Commit` | `option:Commit` | skills/rules nodes; option of Commit |
| `MN-REQ-11.12` | `MN-REQ-11` | `MN-REQ-13.Commit` | `option:Commit` | skills/rules edges; option of Commit |
| `MN-REQ-11.13` | `MN-REQ-11` | `MN-REQ-13.Recall` | `option:Recall` | map of pins; emit economy shared with Recall |
| `MN-REQ-11.14` | `MN-REQ-11` | `MN-REQ-13.Commit` | `option:Commit` | PCBA nodes; option of Commit |
| `MN-REQ-11.15` | `MN-REQ-11` | `MN-REQ-13.Commit` | `option:Commit` | PCBA edges; option of Commit |
| `MN-REQ-11.16` | `MN-REQ-11` | `MN-REQ-13.Commit` | `option:Commit` | Path-B ingest locators; option of Commit |
| `MN-REQ-11.17` | `MN-REQ-11` | `MN-REQ-13.Commit` | `option:Commit` | snap_model — option of Commit (locator mint, not a third operator) |
| `MN-REQ-11.17.1` | `MN-REQ-11.17` | `MN-REQ-13.Commit` | `option:Commit` | cross-cut satisfy locators on catalog Snap |
| `MN-REQ-11.17.2` | `MN-REQ-11.17` | `MN-REQ-13.Commit` | `option:Commit` | Snap session grain |
| `MN-REQ-11.17.3` | `MN-REQ-11.17` | `MN-REQ-13.Commit` | `option:Commit` | Snap budget pre-check |
| `MN-REQ-11.17.4` | `MN-REQ-11.17` | `MN-REQ-13.Commit` | `option:Commit` | Snap caller-gone rollback |
| `MN-REQ-11.17.5` | `MN-REQ-11.17` | `MN-REQ-13.Commit` | `option:Commit` | Snap replace by model identity |
| `MN-REQ-12` | `MN-REQ-00` | `internal (stays under organisational group)` | `internal` | Multitask protocol; workers use Recall then Commit; not one operator |
| `MN-REQ-12.1` | `MN-REQ-12` | `MN-REQ-01 (session surface; not Recall/Commit)` | `session` | shared session id is mission SSOT handle |
| `MN-REQ-12.2` | `MN-REQ-12` | `MN-REQ-06 (ops; later PR may split)` | `ops` | shared store transport (TCP / streamable-http) |
| `MN-REQ-12.3` | `MN-REQ-12` | `internal (stays under organisational group)` | `internal` | parent owns task lifecycle |
| `MN-REQ-12.4` | `MN-REQ-12` | `MN-REQ-13.Recall` | `Recall` | worker pin_map first; scoped write is Commit under the same mission |
| `MN-REQ-12.5` | `MN-REQ-12` | `internal (stays under organisational group)` | `internal` | prefer one worker or disjoint scopes |
| `MN-REQ-12.6` | `MN-REQ-12` | `internal (stays under organisational group)` | `internal` | parent ends turn; no poll |
| `MN-REQ-12.7` | `MN-REQ-12` | `internal (stays under organisational group)` | `internal` | MUST NOT assume full ACL / reserve / ingest |
| `MN-REQ-12.8` | `MN-REQ-12` | `internal (stays under organisational group)` | `internal` | applies to relevant tasks |
| `MN-REQ-12.9` | `MN-REQ-12` | `MN-REQ-13.Commit` | `option:Commit` | lead-owned import_slice / Absorb — option of Commit |
| `MN-REQ-12.10` | `MN-REQ-12` | `MN-REQ-13.Commit` | `option:Commit` | no chat or whole-store import |
| `MN-REQ-12.11` | `MN-REQ-12` | `MN-REQ-13.Commit` | `option:Commit` | optional ImportGuard on Absorb |
| `MN-REQ-12.12` | `MN-REQ-12` | `internal (stays under organisational group)` | `internal` | host-driven async parallel |
| `MN-REQ-12.13` | `MN-REQ-12` | `MN-REQ-13.Commit` | `option:Commit` | RSV lease — option of Commit, not a third operator |
| `MN-REQ-13` | `MN-REQ-00` | `MN-REQ-00 (spine)` | `spine` | spine group: Recall(q) and Commit(Δ) |
| `MN-REQ-13.1` | `MN-REQ-13` | `MN-REQ-13` | `spine` | exactly two product operators; RSV is a Commit lease |
| `MN-REQ-13.2` | `MN-REQ-13` | `MN-REQ-13.Commit` | `Commit` | SameThingAbsorb is a Commit rule, not Recall |
| `MN-REQ-13.Recall` | `MN-REQ-13` | `MN-REQ-13` | `Recall` | spine arm Recall(q) |
| `MN-REQ-13.Commit` | `MN-REQ-13` | `MN-REQ-13` | `Commit` | spine arm Commit(Δ) |

## Did not fit cleanly under Recall or Commit

- **MN-REQ-01** session open / save / close — agent surface beside the two operators, not inside them.
- **MN-REQ-05** hard caps — 05.1 internal store, 05.2 Recall, 05.3 Commit (and snapshot).
- **MN-REQ-07.1** names all five verbs; not a sub-rule of one operator.
- **MN-REQ-08** I/O grammar applies to both; 08.7 / 08.9 hang on Recall (emit) with Commit sharing the family.
- **MN-REQ-11.1–11.5** SysML v2 export / round-trip text vs live `export_pin_map` GQL write-out (option of Recall); `.sysml` reverse still unclaimed.
- **MN-REQ-11** Path-B importers stay nested here; marked option of Commit (move importers = later PR).
- **MN-REQ-12** Multitask is host protocol: workers Recall then Commit; 12.4 is dual; 12.2 is ops transport.
- **MN-REQ-04.12** housekeep sits in the slice-economy group but is internal, not Recall.
- **MN-REQ-13.1** is the two-operator law itself (spine, not a leaf of one arm).

