# MemNet

Mission working memory for LLMs. A named session graph (GQL **node**/vertex, **edge**/relationship, **property**) that agents **pin** and **mutate** — not a notepad in chat, and not the search library.

MemNet sits **between** LLM call pipelines and data search (MN-REQ-00). Corpus lookup stays on the host (grep, ingest, optional RAG); it may propose **locators**. In the session, kinds/tags are overlapping **cues**; recall is **serial** — cue, then a bounded `pin_map` neighbourhood. It is not GraphRAG, not a vector store, and not AgensGraph.

This repo ships the engine + generic MCP only. **Product shape:** [`docs/SHAPE.md`](docs/SHAPE.md). **Pinned role:** working set of **a few technical documents** (atoms and locators, not PDF bytes) plus live `TSK`/`USR`/`MOD`, re-read fast. Tens of MiB typical; **hundreds of MiB still in role**; gigabytes = RAG/cabinet.

Package **`memnet-llm`** (CLI **`memnet`**), version **0.20.2** on PyPI. Python ≥ 3.11. **1.0** is not claimed yet. What the version numbers mean (`a.b.c`): [`docs/ROADMAP.md`](docs/ROADMAP.md).

## What's shipped

- **Product gateway** — `memnet-mcp --transport gateway` routes each product, by credential, to the `memnet serve` that owns its sessions. GQL and `@ERR`/`@WRN`/`@STAT` replies pass through unchanged. See [`docs/operations/product-gateway-contract.md`](docs/operations/product-gateway-contract.md).
- **Safe upgrade** — `memnet admin upgrade-prepare` drains the serve (new sessions get `@ERR: serve_draining|retry_after_s=…`), saves every session, and the new version reloads them on start. See [`docs/operations/safe-upgrade.md`](docs/operations/safe-upgrade.md).
- **Checkpoints and backups** — `memnet admin checkpoint` saves every loaded session without stopping the serve; `memnet admin checkpoint-verify` checks a restored copy. The backup doc runs this hourly to R2 with restic, plus a weekly restore check. See [`docs/operations/backup.md`](docs/operations/backup.md).
- **Admin usage report** — `memnet admin usage-report` (admin token only, not an agent tool) lists active sessions by alias, with no graph content. See [`docs/operations/admin-usage-report.md`](docs/operations/admin-usage-report.md).
- **Request log** — optional, off by default: `--request-log` or `MEMNET_REQUEST_LOG` writes one JSON line per serve request (timings, op, sizes, outcome; no statement text), rotated by size. See [`docs/operations/request-log.md`](docs/operations/request-log.md).
- **Relation names in camelCase** — relation types are stored in lowerCamel form: `HAS_FACT` is stored as `hasFact`, and both spellings match the same edge. `mutate` warns when it renames one.

## Install + quick CLI

```bash
pip install memnet-llm
# or pin: pip install memnet-llm==0.20.2
# optional extras (drivers only — not an AgensGraph server):
# pip install 'memnet-llm[mcp]'
# pip install 'memnet-llm[agensgraph]'
# contributors: pip install -e ".[dev,mcp]"
```

Any host that runs `memnet-mcp` (stdio, streamable-http or the product gateway, for example a droplet) installs `pip install 'memnet-llm[mcp]'`. Without the extra, `memnet-mcp` exits 2 with one line: `@ERR: mcp_extra_missing|memnet-mcp needs the mcp extra (missing module: mcp); install with: pip install 'memnet-llm[mcp]'`.

CLI needs a serve process. Prefer local IPC; TCP is the fallback.

```bash
# Terminal 1
export MEMNET_IPC_SOCKET=/tmp/memnet.sock
memnet serve --ipc

# Terminal 2 (same MEMNET_IPC_SOCKET)
memnet session open --map-file parts/common/memnet/memnet/examples/schema.example.txt
# demo-world map for tests; warehouse GQL below is illustrative (not that world's field list)
# stderr prints MEMNET_SESSION=mn_… — pass it as --session (serve proxies argv, not your shell env)

memnet mutate --session mn_… --stdin <<'EOF'
CREATE (t:TSK {goal:'Clear warehouse', status:'in_progress'})
CREATE (n:NPC {role:'helper', status:'active'})
MATCH (n:NPC {role:'helper'}), (t:TSK {goal:'Clear warehouse'})
CREATE (n)-[:helps {note:'labour'}]->(t)
EOF

memnet query find --session mn_… --kind TSK --limit 8
# paging: a cursor is an opaque token; pass it back with the same cues
memnet query find --session mn_… --kind TSK --limit 8 --paged          # ends with @STAT: find_cursor|<token>|-
memnet query find --session mn_… --kind TSK --limit 8 --cursor <token>
memnet query typed-walk --session mn_… --from <id> --type partOf --limit 20 --cursor <token>
memnet query pin-map --session mn_… --kind TSK --locator 'goal=Clear warehouse' --depth 2
```

Shaped pin map (illustrative; nickname `id` only if set):

```cypher
(:TSK {goal: 'Clear warehouse', status: 'in_progress'})
(:NPC {role: 'helper', status: 'active'})
(:NPC {role: 'helper'})-[:helps {note: 'labour'}]->(:TSK {goal: 'Clear warehouse'})
```

Create nodes by labels and properties (`CREATE ()` is legal); you don't mint ids yourself. The old `id:'NEW'` placeholder and `@ID:` id map are legacy and not part of the product. Each turn, call `pin_map(q)` (or skip it) and **drop** earlier maps from the prompt. The old `--anchor` flag still works, but only as a nickname cue. Agents speak **GQL only** (openCypher-shaped); no other input format is accepted. The wire format is defined in [`docs/grammar/gql-wire-profile.md`](docs/grammar/gql-wire-profile.md).

MCP in-process (`memnet-mcp`) does not need serve — that's the usual single-agent path.

## Session pipe

Handoff between modules/agents is the **`sessionId`** (treat it as a secret capability). The peer **re-`pin_map`s** — don't dump the graph into chat. Keep working/mission memory distinct from other product handles (e.g. a company store id); mixing those is an app concern, not MemNet's job.

## Import absorb vs shared session

- **Path A** — same `sessionId`; peers just re-`pin_map`. No import.
- **Path B** — separate member session; lead absorbs a bounded slice via `memnet import-slice` (pattern match, not MERGE-by-id). The old `keep`/`reject`/`remint` `id_policy` options are legacy and not part of the product. The slice is merged into the lead session (the single source of truth), not appended. **ImportGuard** / **CheapLlmImportGuard** is a **user-selectable** optional soft LLM (feature stays; not deprecated). Absorb works with the key unset. Set `MEMNET_IMPORT_GUARD_API_KEY` on serve to activate (optional `MEMNET_IMPORT_GUARD_BASE_URL` / `MEMNET_IMPORT_GUARD_MODEL`). `--no-guard` skips the soft pass for one call. Hard ImportAbsorb always runs. Teach: [`docs/LLM-GUIDE.md`](docs/LLM-GUIDE.md).

## ACL + transport

**CapsPolicy ACL** (shipped; off by default until `session acl-enable`): who (`caller`) / `pin_map` vs mutate / `WorkerWriteScope` hard reject / optional `missionId`+`lease` bind.

**RSV** neighbourhood reserve exists (`memnet reserve` / `extend` / `release`; `llm_id` + TTL; pin map may show `## Reserves`).

**Transport:** in-process MCP default (one graph per process). Shared graph: `memnet serve --ipc` (`MEMNET_IPC_SOCKET`) or TCP `memnet serve` (`127.0.0.1:18765`). Multitask / parallel workers need a shared serve — not default in-process.

**Durable:** optional client `memnet-llm[agensgraph]`; the cabinet is external and not vendored. Since **0.7** the adapter and an operator-run round trip exist, but nothing calls the cabinet at runtime yet, so a live cabinet is not claimed. Its CI tests skip unless `MEMNET_AGENSGRAPH_URL` is set. Neo4j is retired (#187). `MEMNET_NEO4J_*` is ignored (one log warning); the engine still starts.

## Not done yet

- Hosted AgensGraph as a product service (operator runs the server; this repo does not vendor it)
- N-server session pipe ([#47](https://github.com/chouswei/MemNet/issues/47))
- Reading SysML files or edited pin maps back in (MN-REQ-11.5 SHOULD / [#66](https://github.com/chouswei/MemNet/issues/66)) — `pin_map` GQL can be written out today; matching identities on the way back comes later
- Host search / RAG as a MemNet tool — application nest only ([`docs/extras/memnet-host-search-nest.md`](docs/extras/memnet-host-search-nest.md))

## Links

| Doc | Role |
|-----|------|
| [`docs/LLM-GUIDE.md`](docs/LLM-GUIDE.md) | Agent playbook (GQL only) |
| [`docs/SHAPE.md`](docs/SHAPE.md) | Product shape from the problem |
| [`docs/grammar/gql-wire-profile.md`](docs/grammar/gql-wire-profile.md) | GQL wire SSOT |
| [`docs/ROADMAP.md`](docs/ROADMAP.md) | Version map SSOT |
| [`sysml-models/`](sysml-models/) | Requirements / verify |
| [`docs/operations/multi-agent-sessions.md`](docs/operations/multi-agent-sessions.md) | Multitask ops |
| [`docs/operations/safe-upgrade.md`](docs/operations/safe-upgrade.md) | Upgrade a serve without losing sessions |
| [`docs/operations/backup.md`](docs/operations/backup.md) | Checkpoints, R2 backup, restore check |
| [`docs/operations/admin-usage-report.md`](docs/operations/admin-usage-report.md) | Admin view of active sessions |
| [`docs/operations/request-log.md`](docs/operations/request-log.md) | Optional per-request serve log |
| [`docs/operations/product-gateway-contract.md`](docs/operations/product-gateway-contract.md) | Product gateway wire contract |
| [`docs/README.md`](docs/README.md) | Full docs index |
| [`docs/cap-contract.md`](docs/cap-contract.md) | Caps a product gate can hit (refuse vs clip, exact wire) |

Layout: [`LAYOUT.md`](LAYOUT.md) · [`AGENTS.md`](AGENTS.md). Novel-writer is out: [`DROP-NOVEL-WRITER.md`](DROP-NOVEL-WRITER.md).

## Licence

MIT
