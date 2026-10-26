# Research 195: Claude Code harness, with and without MemNet as SSOT

Research note for issue #195, with Claude Code in place of Cursor. Research only: no engine change, no `memnet-llm` SemVer, no harness patch. Nothing here implies 1.0.

## Verdict summary

| Q | Topic | Verdict | One line |
|---|-------|---------|----------|
| 1 | Honour 0.13 drop-prior-maps | **defer** (approximate only) | Claude Code keeps every tool result in the transcript; the agent can ignore a stale map, not drop it. |
| 2 | Tokens, rounds, wall-clock | **defer** | Tokens not measured; arm B used more rounds and more seconds on trivial read missions (n=1). |
| 3 | Factual accuracy | **defer** | 0 misses in both arms; the missions were too small to expose stale state. |
| 4 | Single agent vs shared session | **steal** the docs stance | In-process MCP is isolated; shared `S` needs serve or streamable-http. Remote id reuse across calls confirmed; subagent sharing not tested. |
| 5 | What belongs on `S` | **defer** | Not exercised beyond four read/edit missions. |
| 6 | Handoff | **steal** (sid only) | The only workable handoff is a session id plus cue; a pasted map is the failure. Not exercised end to end. |
| 7 | Eval tape | **steal** | Run outputs and Atelier rows were the scoring tape and never `S`. |

## MUST NOT for agent teach

- MUST NOT teach that Claude Code honours the drop-prior-maps rule. At best it ignores stale maps; the transcript still holds them.
- MUST NOT teach pasting a `pin_map` (or any graph) into a parent→worker prompt, chat, a task row or a PR; hand off a session id plus cue and write scope only.
- MUST NOT teach in-process MCP (or a per-process local serve) as shared Multitask state.
- MUST NOT put real session ids (`mn_...`) in rows, files, PRs or comments; refer to sessions by name.
- MUST NOT teach committing env blobs (test logs, shell dumps) to `S` and calling that Shape.
- MUST NOT restore harness-thesis docs as agent teach, ship a Claude-specific goldfish caller in `memnet-llm`, or cite this note as a 1.0 claim.

## Setup

- Clone of `chouswei/MemNet` at start commit `a374e1f` (0.19.26). Same model family in both arms (haiku ran the arms; sonnet planned and reviewed).
- Four missions, each with a fixed prompt and a shell checker that prints PASS/FAIL per fact:
  - m1: read five constants from `config.py` / `__init__.py`.
  - m2: edit a copy of `config.py` (two constants).
  - m3: settle `RESERVED_TAGS` and `ORPHAN_EXEMPT_TAGS` members and definition lines.
  - m4: same edit as m2 with at most two original lines changed.
- Arm A: no MemNet; chat, files and grep only.
- Arm B: a MemNet session as mission SSOT (cue then `pin_map`, sparse `mutate`), on a throwaway local `memnet serve --ipc`, closed after.

## Raw run table

All numbers are helper-reported, one run per mission. Seconds are whole seconds. Tokens: not measured.

| Mission | Arm | Checks | Misses | Secs | Tool rounds | MemNet calls | Stale maps left in context | Tokens |
|---------|-----|--------|--------|------|-------------|--------------|----------------------------|--------|
| m1 | A | PASS | 0 | 6 | 4 | 0 | n/a | not measured |
| m2 | A | PASS | 0 | 2 | 3 | 0 | n/a | not measured |
| m3 | A | PASS | 0 | 6 | 4 | 0 | n/a | not measured |
| m4 | A | PASS | 0 | 2 | 3 | 0 | n/a | not measured |
| m1 | B | PASS | 0 | 21 | 7 | 4 | 0 | not measured |
| m2 | B | PASS | 0 | 12 | 4 | 4 | 1 | not measured |
| m3 | B | PASS | 0 | 9 | 5 | 4 | 2 | not measured |
| m4 | B | PASS | 0 | 10 | 4 | 4 | 3 | not measured |

Source rows: Atelier `memnetor-work` r00001405 (arm A), r00001406 (arm B), r00001407 (review).

## Remote probe (coordinator, Q1 and Q4)

Run by the coordinator on `memnet.inkmirage.xyz` over MCP with a fresh session, closed afterwards (id not recorded here).

- `session_open` needs a map: no map is `no_map`, and a bare `@TSK` line is `invalid wire line`; a `SCHEMA` line works. Core LAW rows are auto-seeded.
- Sequence: `mutate` CREATE a `TSK` (status open), `pin_map` outline, `mutate` MERGE status settled, `pin_map` kind `TSK`, then `session_close` (returned closed).
- Q1: the first `pin_map` showed the `TSK` as open and the second as settled. Both results sit in the transcript; the harness offers no call to retract the first. Each `pin_map` is a full emit, so one live map per generate depends on the caller, not on the server.
- Q4: the session id worked across separate tool calls over the remote endpoint (`mutate`, `pin_map`, `close` all addressed by `session`). `session_list` on this host also lists other sessions (4 live at the time), so ids are not private to one caller. Not tested: a subagent using the same session (the `haiku-worker` helper has no MCP tools), so worker-side sharing is not measured.

## Per-question notes

1. **Honour 0.13?** Approximate only. Arm B left 0/1/2/3 stale `pin_map` outputs in context over m1..m4 (the CLI cannot drop them), and the probe shows the same in the MCP path. Options that exist: ignore the old map, a fresh subagent per cue, `/clear` or compaction. None is the "drop rows from the pack" the contract asks for. Verdict: defer; document as ignore-not-drop.
2. **Tokens and wall-clock.** Tokens not measured. Rounds A 4/3/4/3 vs B 7/4/5/4; seconds A 6/2/6/2 vs B 21/12/9/10. Arm B was about 2-4x slower on these trivial read missions. This says nothing about long missions where chat grows; do not read it as MemNet losing in general. Verdict: defer.
3. **Accuracy.** 0 misses in both arms. Stale `SYM.line`, renames and settled-but-open tasks were not provoked. Verdict: defer; needs a mission that changes state mid-run.
4. **Single agent vs Multitask.** Matches `docs/operations/multi-agent-sessions.md`: in-process is isolated; shared `S` needs serve or streamable-http. Arm B's local `serve --ipc` was an isolated throwaway, so this run does not show B collapsing to A or not. Verdict: steal the stance; the shared-worker case remains untested.
5. **`S` vs harness.** Only the mission facts and edit state were in play; test output and shell blobs stayed in the harness by construction of the missions. Verdict: defer.
6. **Handoff.** Helpers received task text only. A sid-plus-cue handoff was not run (the CLI could not name the session). Verdict: steal the rule, untested in practice.
7. **Eval tape.** Scoring came from checker output files and Atelier rows, never from `S`. Verdict: steal (dual tape).

## Caveats

- Single run per mission (n=1); no variance, no significance claim.
- Arm B used a local IPC serve, not the remote host; the remote host was probed separately by the coordinator.
- No token counts: not measured.
- Tool rounds and seconds are helper-reported; seconds are whole seconds.
- Helpers worked on main-clone paths, not their worktrees (reviewer note); results are unaffected as no repo edits were made.
- Arm B session could not be named via the CLI; its close call failed (wrong flag), and the server was killed so the in-memory session is gone.
- Four tiny missions; not representative of long coding campaigns.
