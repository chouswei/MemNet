# Neo4j versus in-process bench

Measurement script only. It does not change the engine and it does not open a pull request.

`neo4j_vs_inprocess.py` loads real SysML projections (`implementation.sysml` ≈ 80 nodes, `requirements.sysml` 229, `deploy.sysml` 504) and two synthetic graphs (10_000 and 100_000 nodes) whose undirected degrees are drawn from the requirements degree sequence. It times:

- `PinMapComposer.compose` (cue `qname`, depth 2 and 3, `max_rows=50`) against an indexed Cypher ego and against the shipped `build_hydrate_nodes_cypher` text
- `MutateGate.apply` batches of 1, 10, and 100 pins against one Bolt `UNWIND`/`MERGE` of those same pins (MERGE only; the gate checks are not repeated on Neo4j)
- `Neo4jAdapter.flush` / `hydrate` of one `HydrateBudget` ego slice
- process cold start (engine interpreter vs Neo4j JVM) when `--cold-runs` is set and `NEO4J_HOME` is set

The uncapped k-hop node sets are compared once per cell. Limited recalls are not the same truncation: the engine clips a ranked mix of nodes and edges; Cypher `LIMIT`s distinct nodes.

## Run

Neo4j 5.x must already be listening. The server is not vendored here.

```bash
source .venv/bin/activate
pip install -e '.[neo4j]'
export MEMNET_NEO4J_URL=bolt://127.0.0.1:7687
export MEMNET_NEO4J_USER=neo4j
export MEMNET_NEO4J_PASSWORD=...   # operator password; do not commit it
export NEO4J_HOME=/path/to/neo4j   # only for JVM cold-start samples
python bench/neo4j_vs_inprocess.py --out-dir /tmp/neo4j-bench --runs 200 --warmup 20
```

This process sets `MEMNET_MAX_ROWS=2000000` so the 10k and 100k graphs can load. The shipped default is 5000.

Outputs: `neo4j-bench-raw.csv` (one row per measured run) and `neo4j-bench-report.md`.
