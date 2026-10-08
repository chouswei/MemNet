# Cap contract (product-gate integrator)

Developer-facing contract for a **product gate** that talks to `memnet-serve` or the generic MCP front (`memnet-mcp`). Every default, refuse, clip, and wire string below was read from the engine and re-hit by `tests/test_cap_contract.py` / `scripts/probe_cap_contract.py`. Do not treat this file as doctrine SSOT for goldfish; wire SSOT remains [`grammar/gql-wire-profile.md`](grammar/gql-wire-profile.md).

**This cut does not change any cap or behaviour.** If a probe finds a silent clip or a leftover gap, it is listed as a bug for a follow-up.

Never log a session id. MCP JSON may include one; redact it at the gate.

## How to read a reply

| Surface | Shape |
|---------|--------|
| Library | `MemNetError(code, message)` then CLI `format_err` |
| CLI / serve | stderr `@ERR: {code}\|{message}` (pipes inside *message* become spaces). Exit `1` or `2`. Mutate also prints `ok=0 fail=1` |
| MCP | JSON text: `exit_code`, `stdout`, `stderr`, `session_id`, `errors` (each `@ERR: …` line). Not a Python exception to the host |
| Product read (`pin_map`) | stdout may carry `## Truncation truncated=true M=… omitted=… reason=…` |
| Honesty (not a resource cap) | `## CueConflict`, `## CueMiss`, `## Peak_L`, `## outline`, `## Reserves` |
| Advisory | `@WRN:` (max **12** per call, then dropped) and `@STAT: key\|value\|cap` |

`format_err` lives in `memnet/output.py`. MCP wraps CLI via `memnet_mcp.client.MemNetResponse`.

## Commit gate (writes)

`MutateGate` (`memnet/mutate_gate.py`) applies a batch, then on `MemNetError` deletes added hids, restores replaced rows, restores deleted rows, and inverts renames. **A refused write is all-or-nothing for that batch.** Separate successful calls that already returned stay. Session row cap does **not** evict; it refuses the next new non-LAW row (nodes **and** edges).

Path-B ingest (`PinMapIngestBase.commit`) projects first; `ingest_budget` raises **before** commit. A projection that fits ingest caps can still hit `MEMNET_MAX_ROWS` at commit; that batch rolls back.

## Integrator checklist

1. Map `@ERR: {code}` to a typed error. Do not parse English prose as the stable key; `code` is the key, message is detail.
2. On **hard refuse**: do not retry the same payload unchanged. Split the batch, raise the cap, narrow the artefact, or grant ACL/RSV.
3. On **`## Truncation`**: the neighbourhood is incomplete. Narrow the cue, filter, or raise `max_rows` / lower `depth` / avoid `view=shell`. **Never treat a clipped read as complete.**
4. On leftover `query walk` / `query context`: those paths can clip **without** Truncation (bugs below). Prefer product `pin_map`. **Never retry a hard refuse unchanged.**
5. At session row cap: stop inserting; housekeep or open another session. Nothing is evicted.
6. On `session_expired\|snap_missing`: the graph is gone unless the operator saved. On `snap_available`: `session_load` with the known id (expire dir).
7. Never put a session id in logs, traces, or mapped errors.

---

## Ingest node budget

| | |
|--|--|
| Default | `2000` (`DEFAULT_INGEST_MAX_NODES`) |
| Knob | CLI `--max-nodes`, MCP `max_nodes`. Not an env var |
| Kind | Hard refuse (`ingest_budget`). No silent clip |
| Library | `ingest_budget` / `pin budget exceeded (max_nodes={N})` |
| Wire | `@ERR: ingest_budget\|pin budget exceeded (max_nodes={N})` |
| MCP | `errors` contains that line; `exit_code=1` |
| Write | Project refuses **before** commit. Session unchanged |
| Gate should | Split the artefact, Snap interiors, or raise `--max-nodes` |
| Gate must not | Retry the same path; dump the load tree into one session |

Source: `memnet/pin_map_ingest.py` `_budget_check` / SysML def loop; CLI `ingest sysml`; MCP `ingest_sysml`.

## Ingest edge budget

| | |
|--|--|
| Default | `2000` (`DEFAULT_INGEST_MAX_EDGES`) |
| Knob | CLI `--max-edges`, MCP `max_edges` |
| Kind | Hard refuse |
| Library | `ingest_budget` / `edge budget exceeded (max_edges={N})` |
| Wire | `@ERR: ingest_budget\|edge budget exceeded (max_edges={N})` |
| Write | Before commit |
| Gate should | Raise `--max-edges` or cut the artefact |
| Gate must not | Retry unchanged |

Source: `_edge_budget_check` / `_budget_over`.

## Ingest file budget

| | |
|--|--|
| Default | `64` files (argument default, not env) |
| Knob | `--max-files` / MCP `max_files` |
| Kind | Hard refuse |
| Wire (SysML dir) | `@ERR: ingest_budget\|too many .sysml files ({n} > max_files={N})` |
| Also | `too many source files (…)` / `too many .ato files (…)` / `too many skill/rule files (…)` |
| Gate should | Point at one file or raise `max_files` |

Source: `_collect_sysml_files` and cousins.

## Per-session row cap (`maxRows`)

| | |
|--|--|
| Default | `5000` non-LAW records (nodes **and** edges) |
| Knob | `MEMNET_MAX_ROWS` (baked into `Caps` at session open) |
| Kind | Hard refuse of the **next new** non-LAW row. Updates of existing rows still apply. **No eviction** |
| Library | `limit_exceeded` / `rows\|{n}/{max}` |
| Wire | `@ERR: limit_exceeded\|rows {n}/{max}` (pipe in the message becomes a space) |
| Mutate extra | `ok=0 fail=1` on stderr |
| MCP | `errors: ["@ERR: limit_exceeded\|rows {n}/{max}"]` |
| Batch | All-or-nothing rollback (probe: 3 CREATEs with cap 2 → 0 rows left) |
| In memory at cap | Further CREATE refuses; existing graph stays |
| Gate should | Housekeep, split sessions, or raise `MEMNET_MAX_ROWS` **before** open |
| Gate must not | Retry the same CREATE; assume old rows were dropped |

Source: `MemStore.upsert` in `memnet/mem_store.py`. LAW rows use `max_law` instead.

Near-cap advisories on session load: `@WRN: near_cap` at 80%, `@WRN: near_cap_critical` at 95% (`memnet/warnings.py`).

## Relation-type cap (`maxRelations`)

| | |
|--|--|
| Default | **`200`** (`MEMNET_MAX_RELATIONS`). Not 5000 |
| Knob | `MEMNET_MAX_RELATIONS` |
| Kind | Hard refuse when adding a **new** type with `allow_new_relation=True` |
| Library | `limit_exceeded` / `relations\|{n}/{max}` |
| Wire | `@ERR: limit_exceeded\|relations {n}/{max}` |
| Seed | `relations.seed.txt` is loaded **without** this cap (41 types in-tree). Setting the env **below** seed size blocks *new* types only; seed types still work |
| Without `--allow-new-relation` | `unknown_relation` instead (see below) |
| Gate should | Reuse a seeded type, pass `allow_new_relation`, or raise the cap |
| Gate must not | Retry the same new type unchanged |

Source: `MemStore.upsert` relation branch; `session._seed_relations`.

## Unknown relation (not a size cap)

| | |
|--|--|
| Default | Product `mutate` / leftover `add` default `allow_new_relation=False` |
| Kind | Hard refuse |
| Wire | `@ERR: unknown_relation\|{rel} known: {comma-list}` |
| Gate should | Use a known type or pass `allow_new_relation=true` |

Path-B ingest commits with `allow_new_relation=True`.

## LAW cap

| | |
|--|--|
| Default | `100` |
| Knob | `MEMNET_MAX_LAW` |
| Kind | Hard refuse of a **new** LAW row |
| Wire | `@ERR: limit_exceeded\|law {n}/{max}` |

## Tag-map caps

| Limit | Default | Knob | Wire |
|-------|---------|------|------|
| User tags | 64 | `MEMNET_MAX_TAGS` | `@ERR: limit_exceeded\|tags {n}/{max}` |
| Fields per tag | 32 | `MEMNET_MAX_FIELDS` | `@ERR: limit_exceeded\|fields {n}/{max}` |

Raised at map load (`memnet/tag_map.py`). Session open fails; nothing is stored.

## Pipe value / line bytes

| Limit | Default | Knob | Wire |
|-------|---------|------|------|
| Field value | 4096 | `MEMNET_MAX_VALUE_BYTES` | `@ERR: limit_exceeded\|value_bytes {n}/{max}` |
| Whole pipe line | 32768 | `MEMNET_MAX_LINE_BYTES` | `@ERR: limit_exceeded\|line_bytes {n}/{max}` |

Enforced on leftover `@TAG` `parse_line` only. **GQL `mutate` does not check these** (bug list).

## Mutate batch line cap

| | |
|--|--|
| Default | `1000` raw lines |
| Knob | `MEMNET_MAX_BATCH_LINES` |
| Kind | Hard refuse **before** sanitise / commit |
| Wire | `@ERR: limit_exceeded\|batch_lines {n}/{max}` |
| Gate should | Split the stdin batch |

Source: `cli._read_ingest_input`.

## `pin_map` row clip (`M`)

| | |
|--|--|
| Default | `50` (`DEFAULT_QUERY_MAX_ROWS`) |
| Knob | CLI `--max-rows`, MCP `max_rows`. **Not** `MEMNET_MAX_ROWS` |
| Kind | Signalled clip |
| Wire | `## Truncation truncated=true M={max_rows} omitted={n} reason=max_rows` |
| Fit | Mark omitted when the offer fits |
| Gate should | Narrow cue / filter / raise `max_rows` |
| Gate must not | Treat the emit as complete |

Source: `MemStore.context_pack` + `PinMapComposer.emit_truncation`.

Empty cue is session outline (`OUTLINE_EXEMPLAR_LIMIT=3` per kind, still one `max_rows`). Clip uses the same Truncation mark (`reason=max_rows`).

## `pin_map` hop depth

| | |
|--|--|
| Request default | `2` (`DEFAULT_QUERY_DEPTH`, `--depth`) |
| Hard ceiling | `4` (`MEMNET_MAX_DEPTH`) |
| Kind | Signalled clip: `depth = min(requested, max_depth)` plus Truncation `reason=depth` |
| Wire example | `## Truncation truncated=true M=50 omitted=0 reason=depth` |
| Gate should | Stay within 4 or raise `MEMNET_MAX_DEPTH` on the process |

## `pin_map` fan-out

| | |
|--|--|
| Default | `256` (`MEMNET_MAX_FANOUT`) |
| Kind | Signalled clip (`reason=fanout`) plus `@WRN: fanout_clamped` on the store path |
| Wire | Truncation `reason=fanout` (may combine with `max_rows` as `reason=max_rows,fanout`) |
| Gap | Clamp applies to **outgoing** `_edges_from` only, not inbound `_edges_to` (bug list) |

## `view=shell` grain

| | |
|--|--|
| Default | Off. Soft caps `SHELL_MAX_NODES=8`, `SHELL_MAX_EDGES=12` |
| Kind | Signalled clip `reason=shell` |
| `view=interior` | No extra soft cap |
| Unknown view | Hard refuse `@ERR: bad_view\|unknown view=…` |

## leftover `query walk`

| | |
|--|--|
| Default | `--max-rows=50`, `--depth=2`, then `min(depth, max_depth)` |
| Kind | **Silent clip** of hop list (bug). No Truncation, no `@ERR` |
| Wire | `@WALK: src -[rel]-> dst` lines only, truncated to `max_rows` |
| Fan-out | Also silent in `context_walk_hops` |
| Gate must | Not use this as product read. Use `pin_map` |

## leftover `query context`

| | |
|--|--|
| Kind | **Silent clip**: `context_pack(..., clip_notes=None)` slices `[:max_rows]` with no Truncation |
| Gate must | Use `query pin-map` / MCP `pin_map` |

## leftover `query neighbors` / `query path`

| | |
|--|--|
| Neighbors | Depth silently `min`'d to `max_depth`. Fan-out may `@WRN: fanout_clamped` without Truncation |
| Path | `find_path` walks at `max_depth` and may return empty with no mark |

## `find` LIMIT

| | |
|--|--|
| Default | No default — `--limit` required (`no_limit`) |
| Kind | Honesty, not a resource cap. `total > 1` → `## CueConflict \|Q\|={total}` |
| Listed seeds | `hits[:limit]`; cardinality is the true hit count |
| Gate must not | Pick one root. Tighten locators |

`bad_limit` when `--limit < 1`.

## Concurrent sessions

| | |
|--|--|
| Default | `1024` |
| Knob | `MEMNET_MAX_SESSIONS` |
| Kind | Hard refuse of `session open` |
| Wire | `@ERR: limit_exceeded\|sessions {n}/{max}` |
| List | `@STAT: sessions\|{n}/{max}` |
| Gate should | Close unused sessions |

## Session TTL and expiry

| | |
|--|--|
| Default TTL | `60` minutes (`MEMNET_SESSION_TTL_MINUTES`). Open `--ttl` / MCP `ttl` |
| Legal range | `1..1440` else `@ERR: bad_ttl\|ttl must be 1..1440` |
| Live access | Sliding TTL: each `get_session` extends `expires_at` by the original minutes |
| Expire, save off (default) | Session dropped from memory. First access of the still-registered expired id: `@ERR: session_expired\|snap_missing` (exit 2). After purge already ran: `@ERR: session_not_found\|unknown session` |
| Expire, `MEMNET_SAVE_ON_EXPIRE` truthy + `MEMNET_EXPIRE_SNAPSHOT_DIR` set | Snapshot `{dir}/{sid}.snap` (filename only; do not log it). Next use: `@ERR: session_expired\|snap_available`. Restore: `session_load` with that id |
| Save-on-expire on, dir unset | `@WRN: save_on_expire_no_dir\|dir unset`, then drop; `snap_missing` |
| `session save` after TTL with save-on-expire | Allowed; `@WRN: session_expired_saved`. Id then gone |
| `session save` after TTL with save off | `@ERR: session_expired` / `snap_missing`; no file |
| Status (no paths, no ids) | `@STAT: save_on_expire\|0\|` / `1`; `@STAT: expire_snapshot_dir_set\|0\|` / `1` |

Source: `memnet/session.py`, `memnet/config.py` `save_on_expire` / `expire_snapshot_dir`.

**Unsaved expiry:** the in-memory graph is gone. There is no recycle of rows into another session.

## CapsPolicy ACL

Off until `session acl-enable`, a grant/bind (which enables), or `MEMNET_ACL=1` on newly opened sessions.

| Code | When | Wire |
|------|------|------|
| `acl_who` | ACL on, no `--caller` / `MEMNET_CALLER` | `@ERR: acl_who\|caller id required when session ACL is enabled\|pass --caller or MEMNET_CALLER` |
| `acl_denied` | Unknown caller | `@ERR: acl_denied\|unknown caller for this session\|grant caller via session acl-grant` |
| `acl_forbidden` | Caller lacks `pin_map` or `mutate` | `@ERR: acl_forbidden\|caller lacks pin_map (TRAVERSE/MATCH read) permission` or `… lacks mutate (WRITE) permission` |
| `acl_bind` | Bind set, mission/lease mismatch, `require_bind=True` | `@ERR: acl_bind\|mission_id and lease must match session bind\|pass --mission-id and --lease matching session acl-bind` |
| `acl_scope` | WorkerWriteScope miss | `@ERR: acl_scope\|id/label outside WorkerWriteScope (GRANT)` or `edge outside …` |
| `acl_bad_caller` / `acl_bad_bind` / `acl_bad_scope` | Malformed grant/bind/scope | matching `@ERR:` |

Bind is **skipped** when `require_bind=False` and the trusted path is on (`MEMNET_SERVE_INTERNAL` or `MEMNET_TEST_INLINE` or `MEMNET_ACL_SKIP_BIND`). **`memnet serve` sets `MEMNET_SERVE_INTERNAL=1`**, so CLI/MCP through serve does **not** enforce bind today (who and scope still do). Library `MutateGate.apply(..., require_bind=True)` still refuses. Listed as a bug; not fixed in this run.

In-scope writes from earlier batches stay; a later out-of-scope batch is refused (not a partial of that batch).

## Neighbourhood reserve (RSV)

| Code | Wire / meaning |
|------|----------------|
| `reserve_conflict` | `@ERR: reserve_conflict\|neighbourhood already held by llm_id=… anchor=…` |
| `reserved` | Mutate touching another holder's ids |
| `no_llm_id` | Reserve/extend/release/mutate-under-lease without `llm_id` |
| `reserve_mismatch` | extend/release holder mismatch |
| `reserve_expired` | Lease gone; treat as free |
| `bad_ttl` | RSV `ttl_s` must be `1..86400` (default 120) |

Pin-map may add `## Reserves` (not a clip). Gate should wait or use the holder `llm_id`. Do not retry a `reserve_conflict` unchanged.

## Import slice budget

| | |
|--|--|
| Default | `max_rows × anchors` with `max_rows` default 50 |
| Kind | Hard refuse `slice_budget` **if** `len(records) > budget` |
| Reachability | Product `pin_map` already clips each anchor to `max_rows`, so the union cannot exceed the budget. Probe: export succeeds; the refuse is retained in code |

## Serve / IPC frame

| | |
|--|--|
| Default | 4 MiB (`MEMNET_SERVE_MAX_FRAME_BYTES`) |
| Client request over cap | `@ERR: frame_too_large\|request payload {n} bytes exceeds cap {max}` (no TCP connect) |
| Server request over cap | `@ERR: frame_too_large\|request frame {n} bytes exceeds cap {max}` |
| Response over cap | Python `ConnectionError` (not `@ERR`) |
| Bind | Non-loopback without `MEMNET_SERVE_ALLOW_REMOTE` raises `ServeBindError` (process start, not session wire) |

MCP TCP with serve down: `@ERR: serve_required\|run memnet serve in another terminal first` (`exit_code=2`). Default MCP is in-process and does not need serve.

## Warning budget

| | |
|--|--|
| Default | 12 `@WRN` lines per call (`MAX_WRN_PER_CALL`) |
| Kind | Further warnings dropped with no mark (bug-class silent clip of diagnostics) |

## Lock timeout

| | |
|--|--|
| Default | `2000` ms (`MEMNET_LOCK_TIMEOUT_MS`) |
| Kind | **Configured, not enforced.** `SessionStore.lock` is `threading.RLock()` with no timeout |

## Durable hydrate / flush (cabinet, not the live gate)

`SessionLifecycle.hydrate_from_durable` / `flush_to_durable` default `max_nodes=50`, `max_edges=100` and the adapter **slices** the payload (`nodes[:max_nodes]`). That is a silent cabinet clip, not `pin_map` Truncation. A product gate using only serve/MCP ingest + `pin_map` does not hit it.

---

## Session already at the row cap

After many mutates, `row_count_non_law() == max_rows`:

- Next **new** node or edge → `@ERR: limit_exceeded|rows {max+1}/{max}`
- Existing rows remain; **nothing is evicted or recycled automatically**
- `SET` / replace of an existing hid still works
- Housekeep prune is an explicit operator action

## Session expires unsaved

Default `MEMNET_SAVE_ON_EXPIRE` is off. At TTL:

1. `purge_expired` / next access drops the registry entry
2. Memory graph is gone
3. Caller sees `@ERR: session_expired|snap_missing` (or `session_not_found` if the id was never known)
4. No snapshot file unless save-on-expire **and** a dir were armed **before** expiry

## Bugs found this run (do not fix here)

1. **leftover `query walk`** (`WalkQuery` / `context_walk_hops`): clips hops at `max_rows` and fan-out **without** Truncation/`@ERR`.
2. **leftover `query context`**: `context_pack` without `clip_notes` slices `max_rows` silently.
3. **leftover `query neighbors` / `query path`**: depth `min` without Truncation; path may return empty.
4. **GQL `mutate`** does not enforce `MEMNET_MAX_VALUE_BYTES` / `MEMNET_MAX_LINE_BYTES` (pipe leftover does).
5. **`MEMNET_LOCK_TIMEOUT_MS`** is stored on `Caps` and never applied.
6. **`@WRN` budget**: lines after 12 vanish with no mark.
7. **Serve bind skip:** `memnet serve` sets `MEMNET_SERVE_INTERNAL=1`, so session **bind** is not enforced on the TCP/IPC product path (who/scope are). Library `require_bind=True` still refuses.
8. **Serve response frame** over cap raises `ConnectionError` rather than `@ERR: frame_too_large`.
9. **`max_fanout`** clamps only outgoing `_edges_from`, not inbound `_edges_to`, so a high in-degree hub is not Truncation-marked for fan-out.

Product `pin_map` Truncation for `max_rows` / `depth` / `fanout` / `shell` **is** signalled. Mutate/ingest row-cap batches **do** roll back.

## Proof

Live output: `scripts/probe_cap_contract.py` (sid-free log) and `tests/test_cap_contract.py`. The test file asserts the strings in the tables above so this document cannot drift without CI failing.
