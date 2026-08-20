# Bundled examples

Agent wire is **GQL only** ([`docs/grammar/gql-wire-profile.md`](../../../../../docs/grammar/gql-wire-profile.md)).
These files are session maps and seeds for `session_open` / tests — not a second dialect.

CLI: `memnet examples path | map | workflow | agent-guide`.

## Session maps (`session_open --map-file`)

SCHEMA lines list kinds and property names. Built-in `LAW` / `EDG` are merged automatically — do not redefine them here. leftover `@TAG` pipe maps still load; do not teach pipe as mutate.

| File | Role |
|------|------|
| `schema.example.txt` | Demo world for CLI tests and `memnet examples map` (CFG/SYS/PLR/NPC/TSK/…) |
| `schema.coding.example.txt` | Coding session (MOD/SYM/TSK/USR/DEC) |
| `schema.sysml.example.txt` | Path-B SysML ingest (PKG/PRT/REQ/POR) |
| `schema.codebase.example.txt` | Path-B codebase ingest (MOD/SYM) |
| `schema.pcba.example.txt` | Path-B PCBA `.ato` ingest (CMP/NET/PIN) |
| `schema.skills.example.txt` | Path-B skills/rules ingest (SKL/RUL) |
| `schema.techdocs.example.txt` | Tech-docs / SCPI kinds (pair with the machine RTO seed) |

The README warehouse sketch (`:TSK` / `:NPC` / `:helps`) is **illustrative GQL**. It is not a dump of `schema.example.txt`. Open a map that `SCHEMA`s every label you mutate.

## Relation vocabulary

| File | Role |
|------|------|
| `relations.seed.txt` | Default relationship types loaded on `session_open` |

## Agent-facing GQL seeds (`memnet mutate --file`)

Optional nickname property `id` is leftover identity, kept here so CLI/MCP tests can `get("CFG01")`. Product create is labels+properties (`CREATE ()` is legal).

| File | Role |
|------|------|
| `workflow.example.txt` | Demo-world seed for `schema.example.txt` (stable nicknames for tests) |
| `workflow.coding.example.txt` | Coding tutorial seed for `schema.coding.example.txt` |

## Machine / leftover pipe seeds (import-once, not goldfish)

Regenerate; do not hand-edit bodies. leftover `add` still imports `@TAG` pipe. Product Commit is `mutate`.

| File | Role |
|------|------|
| `workflow.memnet-codebase.snap.txt` | `scripts/generate_memnet_codebase_seed.py` |
| `workflow.rto-remote.example.txt` | RTO SCPI dictionary; `scripts/extract_rto_scpi.py` |

## Not this folder

As-is line-codec **harness** fixtures (parse/emit only; rejected on product mutate): [`docs/grammar/examples/`](../../../../../docs/grammar/examples/).
Historical Layer ASCII: [`docs/grammar/archive/`](../../../../../docs/grammar/archive/).
Worked GQL circuit: [`docs/application-notes/examples/inverting-amplifier-gql-case-study.md`](../../../../../docs/application-notes/examples/inverting-amplifier-gql-case-study.md).
