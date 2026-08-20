---
name: memnet-nested-sessions
description: >-
  Nested MemNet sessions: catalog then one interior per generate; sub-unit
  in another session; already-built session= locator; look loop; parallel
  TSK when the parent shell is already clear. Triggers: nested session,
  session in session, look loop, sub-unit session, session stack, snap_model
  catalog, session strata, already-built interior, parallel interiors.
metadata:
  pattern: pipeline
  version: "1.1"
  domain: memnet
  product: "0.19.0"
---

# Nested sessions

How to **use** a session stack. Pair with [memnet-use](../memnet-use/SKILL.md). Doctrine: `docs/grammar/memnet-session-strata.md`. SysML loop: `docs/application-notes/llm-sysml-v2-modeling.md`. Evidence: `sysml-models/outputs/sysml-session-nest-cuts-case-study.md` (Turns A–I).

Chat is never SSOT. Goldfish is **one** \(S\) per generate. Do not revive Layer / `layer=`.

## Two laws

| # | Law |
|---|-----|
| 1 | **Relatives of one cue** — complete Shape of **this** parent, then one brace at `SYM.line`. |
| 2 | **Sub-unit in a separate session** — over \(M\), or **already built**, is cut away. Parent shell: **name** + `session=`. Do not walk that other \(S\) in this generate. |

Look = `pin_map(session=` that id`)`. Join = Absorb a **slice**, not a second Snap and not a paste of the nested tree.

## Look loop (session in session)

```text
pin_map(S_cat)     → pick session=
pin_map(S_i)       → child has session=?  yes → drop map, next generate pin_map(S_child)
                   → … until this brace fits M whole
edit SSOT of THAT cut → re-Snap THAT interior (reuse session= if qname= already has one)
```

Not \(N\) maps stacked in one prompt.

## Already built

If the nested type already presents in another minted session: **present** it. Shell = usage name + `typedBy` + existing `session=`. Configuration **delta** (`subsets`, extra nested pin) stays on the usage. Do not Snap a twin of the same `qname=`.

## Parallel sub-units

When the **parent shell is already clear** in SSOT (children named, `session=` assigned): parent mints one `TSK_*` per interior, passes that session id, **ends the turn**. Workers goldfish **only** their \(S_i\) — load [memnet-multitask](../memnet-multitask/SKILL.md) (TCP/HTTP). If the parent nest is still being invented: **serial** — write the shell first. Same interior / same brace: RSV or serialise.

## MUST NOT

- Kind zoo (`S_part`, `S_req`, `S_port`) — cuts are **fit**, not construct names.
- One session per leaf / exploded multiplicity.
- Clip `max_rows` and call it Shape — refuse; cut sessions.
- Absorb a whole \(S\) / merge interiors in chat.
- Two workers on the same interior before the shell is named.
