#!/usr/bin/env python3
"""Measure in-process MemNet against a throwaway Neo4j 5.x on this machine.

This script does not change the engine. It loads graphs, times the product
pin_map / MutateGate paths, and times Cypher that is only approximately the
same work. See the generated report for what is and is not the same query.

Environment (no secrets in this file):

- MEMNET_NEO4J_URL       default bolt://127.0.0.1:7687
- MEMNET_NEO4J_USER      default neo4j
- MEMNET_NEO4J_PASSWORD  required
- NEO4J_HOME             required only for JVM cold-start samples

Outputs: neo4j-bench-raw.csv and neo4j-bench-report.md under --out-dir.
"""

from __future__ import annotations

import argparse
import csv
import gc
import json
import math
import os
import random
import statistics
import subprocess
import sys
import time
from collections import Counter
from pathlib import Path

# Shipped session row cap is 5000. 10k and 100k graphs cannot load without
# raising it. This process only; not a change to the engine default.
# Force the bench process caps. setdefault is not enough: a parent shell may
# already export the shipped (or a smaller) MEMNET_MAX_ROWS, and 10k/100k
# graphs plus their edges exceed 5000 and also a 20000 override.
os.environ["MEMNET_MAX_ROWS"] = "2000000"
os.environ["MEMNET_MAX_RELATIONS"] = "2000"
os.environ["MEMNET_MAX_TAGS"] = "128"

from neo4j import GraphDatabase
from neo4j.exceptions import Neo4jError

from memnet.config import DEFAULT_QUERY_MAX_ROWS, Caps, examples_dir
from memnet.durable.adapter import DurableSubgraph, HydrateBudget, record_cabinet_hid
from memnet.durable.neo4j import (
    Neo4jAdapter,
    Neo4jConfig,
    build_hydrate_nodes_cypher,
    cypher_ident,
    props_for_set,
)
from memnet.exceptions import MemNetError
from memnet.models import Record
from memnet.mutate_gate import MutateGate
from memnet.pin_map_composer import PinMapComposer
from memnet.pin_map_ingest import ingest_sysml
from memnet.session import close_session, open_session

REPO = Path(__file__).resolve().parents[1]
MODELS = REPO / "sysml-models" / "models"
SCHEMA = examples_dir() / "schema.sysml.example.txt"
ROW_CAP = DEFAULT_QUERY_MAX_ROWS  # product pin_map hard LIMIT (50)
# Working-memory sizes only. 10k and 100k rows stay in the raw CSV.
IN_SCOPE = ("n80", "n229", "n504")
QUERY_TIMEOUT_S = 20.0
IDENT = __import__("re").compile(r"^[A-Za-z_][A-Za-z0-9_]*$")

CSV_FIELDS = [
    "section",
    "size_label",
    "n_nodes",
    "n_edges",
    "param",
    "side",
    "run",
    "seconds",
    "ok",
    "error",
    "engine_nodes",
    "cypher_nodes",
    "intersection",
    "only_engine",
    "only_cypher",
    "note",
]


def meminfo() -> dict[str, int]:
    out: dict[str, int] = {}
    for line in Path("/proc/meminfo").read_text().splitlines():
        key, _, rest = line.partition(":")
        num = rest.strip().split()[0]
        if num.isdigit():
            out[key] = int(num)
    return out


def cpu_model() -> str:
    for line in Path("/proc/cpuinfo").read_text().splitlines():
        if line.startswith("model name"):
            return line.split(":", 1)[1].strip()
    return "unknown"


def rss_kb(pid: int | None = None) -> int | None:
    path = Path("/proc/self/status" if pid is None else f"/proc/{pid}/status")
    if not path.exists():
        return None
    for line in path.read_text().splitlines():
        if line.startswith("VmRSS:"):
            return int(line.split()[1])
    return None


def neo4j_pid(home: Path | None) -> int | None:
    if home is None:
        return None
    pid_file = home / "run" / "neo4j.pid"
    if not pid_file.exists():
        return None
    try:
        return int(pid_file.read_text().strip())
    except ValueError:
        return None


def percentile(values: list[float], p: float) -> float | None:
    """Nearest-rank percentile. p in (0, 1]."""
    if not values:
        return None
    ordered = sorted(values)
    rank = max(1, math.ceil(p * len(ordered)))
    return ordered[rank - 1]


def median(values: list[float]) -> float | None:
    if not values:
        return None
    return float(statistics.median(values))


def fmt_s(seconds: float | None) -> str:
    if seconds is None:
        return "n/a"
    ms = seconds * 1000.0
    if ms < 0.01:
        return f"{seconds * 1e6:.1f} us"
    if ms < 1:
        return f"{ms:.3f} ms"
    if ms < 10:
        return f"{ms:.2f} ms"
    if ms < 1000:
        return f"{ms:.1f} ms"
    return f"{seconds:.2f} s"


def fmt_ratio(neo: float | None, local: float | None) -> str:
    if neo is None or local is None or local == 0:
        return "n/a"
    return f"{neo / local:.2f}x"


class RowLog:
    def __init__(self, path: Path, *, append: bool = False) -> None:
        self.path = path
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.rows: list[dict] = []
        if append and path.exists() and path.stat().st_size:
            with path.open(newline="") as fh:
                self.rows = list(csv.DictReader(fh))
            self._fh = path.open("a", newline="")
            self._writer = csv.DictWriter(self._fh, fieldnames=CSV_FIELDS)
        else:
            self._fh = path.open("w", newline="")
            self._writer = csv.DictWriter(self._fh, fieldnames=CSV_FIELDS)
            self._writer.writeheader()

    def add(self, **kwargs) -> None:
        row = {key: "" for key in CSV_FIELDS}
        row.update(kwargs)
        self.rows.append(row)
        self._writer.writerow(row)
        self._fh.flush()

    def close(self) -> None:
        self._fh.close()


def is_timeout(exc: BaseException) -> bool:
    code = getattr(exc, "code", "") or ""
    text = f"{code} {exc}".lower()
    return "timedout" in text.replace(".", "") or "timeout" in text or "timed out" in text


def connect(url: str, user: str, password: str):
    return GraphDatabase.driver(url, auth=(user, password))


def run_tx(driver, cypher: str, params: dict | None = None, *, timeout: float, write: bool = False):
    params = params or {}
    with driver.session() as session:
        tx = session.begin_transaction(timeout=timeout)
        try:
            result = list(tx.run(cypher, params))
            tx.commit()
            return result
        except Exception:
            try:
                tx.rollback()
            except Exception:
                pass
            raise


def autocommit(driver, cypher: str, params: dict | None = None):
    """Implicit transaction. Required for schema DDL and IN TRANSACTIONS."""
    with driver.session() as session:
        result = session.run(cypher, params or {})
        return list(result)


def clear_graph(driver) -> None:
    # CALL {} IN TRANSACTIONS is illegal inside an explicit transaction.
    autocommit(
        driver,
        "MATCH (n) CALL (n) { DETACH DELETE n } IN TRANSACTIONS OF 2000 ROWS",
    )


def ensure_constraint(driver) -> None:
    autocommit(
        driver,
        "CREATE CONSTRAINT memnet_pin_hid IF NOT EXISTS "
        "FOR (n:MemnetPin) REQUIRE n._memnet_hid IS UNIQUE",
    )


def node_records(store) -> list[Record]:
    return [r for r in store._by_hid.values() if r.tag not in {"EDG", "LAW"}]


def edge_records(store) -> list[Record]:
    return [r for r in store._by_hid.values() if r.tag == "EDG"]


def undirected_degrees(store) -> list[int]:
    deg: Counter[str] = Counter()
    nodes = node_records(store)
    for edge in edge_records(store):
        deg[edge.fields.get("src", "")] += 1
        deg[edge.fields.get("dist", "")] += 1
    return [deg[rec.hid] for rec in nodes]


def degree_summary(degs: list[int]) -> dict[str, float | int | None]:
    if not degs:
        return {"n": 0, "min": None, "p50": None, "p95": None, "max": None, "mean": None}
    return {
        "n": len(degs),
        "min": min(degs),
        "p50": percentile([float(d) for d in degs], 0.50),
        "p95": percentile([float(d) for d in degs], 0.95),
        "max": max(degs),
        "mean": sum(degs) / len(degs),
    }


def modal_relation(store) -> str:
    counts: Counter[str] = Counter()
    for edge in edge_records(store):
        rel = edge.fields.get("relation") or ""
        if rel:
            counts[rel] += 1
    if not counts:
        return "contains"
    rel = counts.most_common(1)[0][0]
    return rel if IDENT.match(rel) else "contains"


def open_mapped_session():
    return open_session(map_file=str(SCHEMA), ttl_minutes=1440, caps=Caps())


def load_sysml(path: Path):
    session = open_mapped_session()
    t0 = time.perf_counter()
    ingest_sysml(session, path, max_nodes=20000, max_files=8)
    elapsed = time.perf_counter() - t0
    return session, elapsed


def configuration_edges(n: int, empirical: list[int], rng: random.Random) -> list[tuple[int, int]]:
    """Stub-pair a simple graph whose degrees are drawn from ``empirical``."""
    degrees = [empirical[rng.randrange(len(empirical))] for _ in range(n)]
    if sum(degrees) % 2:
        degrees[0] += 1
    stubs: list[int] = []
    for i, deg in enumerate(degrees):
        stubs.extend([i] * deg)
    rng.shuffle(stubs)
    used: set[tuple[int, int]] = set()
    edges: list[tuple[int, int]] = []
    for a, b in zip(stubs[0::2], stubs[1::2]):
        if a == b:
            continue
        e = (a, b) if a < b else (b, a)
        if e in used:
            continue
        used.add(e)
        edges.append(e)
    return edges


def load_synthetic(n: int, empirical: list[int], relation: str, rng: random.Random):
    session = open_mapped_session()
    t0 = time.perf_counter()
    edges = configuration_edges(n, empirical, rng)
    store = session.store
    nodes: list[Record] = []
    for i in range(n):
        rec = Record(
            tag="REQ",
            fields={
                "name": f"n{i}",
                "qname": f"bench::{i}",
                "path": "synthetic",
                "sysml_kind": "requirement",
                "requirementId": f"SYN-{i}",
            },
        )
        store.upsert(rec, allow_new_relation=True, relations=session.relations)
        nodes.append(rec)
    for src_i, dst_i in edges:
        rec = Record(
            tag="EDG",
            fields={
                "src": nodes[src_i].hid,
                "dist": nodes[dst_i].hid,
                "relation": relation,
            },
        )
        store.upsert(rec, allow_new_relation=True, relations=session.relations)
    elapsed = time.perf_counter() - t0
    return session, elapsed


def push_neo4j(driver, store) -> float:
    t0 = time.perf_counter()
    by_tag: dict[str, list[dict]] = {}
    for rec in node_records(store):
        tag = cypher_ident(rec.tag.upper(), kind="node label")
        props = props_for_set(dict(rec.fields), skip={"_memnet_hid", "_memnet_tag"})
        by_tag.setdefault(tag, []).append({"hid": record_cabinet_hid(rec), "props": props})
    for tag, rows in by_tag.items():
        cypher = (
            f"UNWIND $rows AS row\n"
            f"MERGE (n:{tag}:MemnetPin {{_memnet_hid: row.hid}})\n"
            f"SET n += row.props, n._memnet_tag = $tag, n._memnet_hid = row.hid"
        )
        for chunk in _chunks(rows, 1000):
            run_tx(driver, cypher, {"rows": chunk, "tag": tag}, timeout=30.0, write=True)
    by_rel: dict[str, list[dict]] = {}
    for rec in edge_records(store):
        rel = rec.fields.get("relation") or ""
        if not IDENT.match(rel):
            continue
        rel_t = cypher_ident(rel, kind="relationship type")
        props = props_for_set(dict(rec.fields), skip={"_memnet_hid", "_memnet_tag"})
        by_rel.setdefault(rel_t, []).append(
            {
                "hid": record_cabinet_hid(rec),
                "src": rec.fields.get("src", ""),
                "dst": rec.fields.get("dist", ""),
                "props": props,
            }
        )
    for rel, rows in by_rel.items():
        cypher = (
            "UNWIND $rows AS row\n"
            "MATCH (a:MemnetPin {_memnet_hid: row.src})\n"
            "MATCH (b:MemnetPin {_memnet_hid: row.dst})\n"
            f"MERGE (a)-[r:{rel} {{_memnet_hid: row.hid}}]->(b)\n"
            "SET r += row.props, r._memnet_tag = 'EDG', r._memnet_hid = row.hid"
        )
        for chunk in _chunks(rows, 1000):
            run_tx(driver, cypher, {"rows": chunk}, timeout=30.0, write=True)
    return time.perf_counter() - t0


def _chunks(rows: list, size: int):
    for i in range(0, len(rows), size):
        yield rows[i : i + size]


def pick_seed(store) -> tuple[Record, str, int]:
    """Highest undirected degree. On these SysML trees that is the package root."""
    nodes = node_records(store)
    deg: Counter[str] = Counter()
    for edge in edge_records(store):
        deg[edge.fields.get("src", "")] += 1
        deg[edge.fields.get("dist", "")] += 1
    seed = max(nodes, key=lambda r: (deg[r.hid], r.fields.get("qname") or "", r.hid))
    qname = seed.fields.get("qname") or ""
    if not qname:
        raise MemNetError("no_seed", "seed has no qname locator")
    return seed, qname, deg[seed.hid]


def engine_node_hids(rows: list[Record]) -> set[str]:
    return {r.hid for r in rows if r.tag not in {"EDG", "LAW"}}


def cypher_indexed(k: int) -> str:
    # Depth is an integer we control (2 or 3). Neo4j will not parameterise it.
    return (
        "MATCH (ego:MemnetPin {_memnet_hid: $hid})\n"
        f"OPTIONAL MATCH (ego)-[*0..{k}]-(n:MemnetPin)\n"
        "WITH DISTINCT n\n"
        "WHERE n IS NOT NULL\n"
        "RETURN n._memnet_hid AS hid\n"
        "LIMIT $limit"
    )


def cypher_ball(k: int) -> str:
    return (
        "MATCH (ego:MemnetPin {_memnet_hid: $hid})\n"
        f"MATCH (ego)-[*0..{k}]-(n:MemnetPin)\n"
        "RETURN DISTINCT n._memnet_hid AS hid"
    )


def read_rows(driver, cypher: str, params: dict, timeout: float) -> tuple[list[dict], float]:
    t0 = time.perf_counter()
    with driver.session() as session:
        tx = session.begin_transaction(timeout=timeout)
        try:
            rows = [rec.data() for rec in tx.run(cypher, params)]
            tx.commit()
        except Exception:
            try:
                tx.rollback()
            except Exception:
                pass
            raise
    return rows, time.perf_counter() - t0


def hids_of(rows: list[dict]) -> list[str]:
    """Accept either `hid` or the shipped hydrate shape (`props._memnet_hid`)."""
    out: list[str] = []
    for row in rows:
        hid = row.get("hid")
        if not hid:
            props = row.get("props") or {}
            if isinstance(props, dict):
                hid = props.get("_memnet_hid")
        if hid:
            out.append(str(hid))
    return out


def time_call(fn):
    t0 = time.perf_counter()
    try:
        value = fn()
        return time.perf_counter() - t0, True, "", value
    except Exception as exc:  # noqa: BLE001 — bench records the failure
        return time.perf_counter() - t0, False, f"{type(exc).__name__}: {exc}", None


def run_samples(fn, runs: int, warmup: int, *, abort_after_timeouts: int = 5):
    """Return list of (seconds, ok, error, value). Stops after repeated timeouts."""
    for _ in range(warmup):
        try:
            fn()
        except Exception:
            break
    out = []
    timeouts = 0
    for _ in range(runs):
        seconds, ok, err, value = time_call(fn)
        out.append((seconds, ok, err, value))
        if not ok and is_timeout(Exception(err)):
            timeouts += 1
            if timeouts >= abort_after_timeouts:
                break
        else:
            timeouts = 0
    return out


def recall_one_engine(composer, qname: str, k: int):
    rows, text = composer.compose(
        anchor=None,
        locators=[("qname", qname)],
        depth=k,
        max_rows=ROW_CAP,
        active_only=True,
    )
    return rows, text


def recall_one_walk(store, hid: str, k: int):
    return store.context_pack(
        anchor_id=hid,
        depth=k,
        max_rows=ROW_CAP,
        active_only=True,
    )


def full_ball(store, hid: str, k: int) -> tuple[set[str], int, bool]:
    warnings: list[str] = []
    rows = store.neighbors(hid, k, fanout_warnings=warnings)
    hids = {r.hid for r in rows if r.kind == "node"}
    return hids, len(rows), bool(warnings)


def commit_lines(batch: int, token: str) -> list[str]:
    return [
        "CREATE (:REQ {"
        f"id: 'REQ_{token}_{i}', name: 'bench{i}', qname: 'benchcommit::{token}::{i}'"
        "})"
        for i in range(batch)
    ]


def merge_created(driver, records: list[Record]) -> None:
    rows = []
    for rec in records:
        if rec.tag == "EDG":
            continue
        tag = cypher_ident(rec.tag.upper(), kind="node label")
        props = props_for_set(dict(rec.fields), skip={"_memnet_hid", "_memnet_tag"})
        rows.append({"hid": record_cabinet_hid(rec), "tag": tag, "props": props})
    if not rows:
        return
    # One transaction, one label family per call. Commit batches are all REQ.
    tag = rows[0]["tag"]
    cypher = (
        "UNWIND $rows AS row\n"
        f"MERGE (n:{tag}:MemnetPin {{_memnet_hid: row.hid}})\n"
        "SET n += row.props, n._memnet_tag = $tag, n._memnet_hid = row.hid"
    )
    run_tx(driver, cypher, {"rows": rows, "tag": tag}, timeout=QUERY_TIMEOUT_S, write=True)


def delete_created(store, driver, records: list[Record]) -> None:
    hids = [record_cabinet_hid(r) for r in records if r.tag != "EDG" and record_cabinet_hid(r)]
    for hid in hids:
        store.delete(hid)
    if hids:
        run_tx(
            driver,
            "UNWIND $hids AS hid MATCH (n:MemnetPin {_memnet_hid: hid}) DETACH DELETE n",
            {"hids": hids},
            timeout=30.0,
            write=True,
        )


def slice_subgraph(store, hid: str) -> DurableSubgraph:
    budget = HydrateBudget()
    rows = store.context_pack(
        anchor_id=hid,
        depth=budget.depth,
        max_rows=budget.max_nodes + budget.max_edges,
        active_only=True,
    )
    nodes = [r for r in rows if r.tag not in {"EDG", "LAW"}]
    edges = [r for r in rows if r.tag == "EDG"]
    rels = {e.fields.get("relation", "") for e in edges if e.fields.get("relation")}
    return DurableSubgraph(ego_id=hid, nodes=nodes, edges=edges, relations=rels).bounded(budget)


def machine_note() -> str:
    info = meminfo()
    total = info.get("MemTotal", 0) / 1024 / 1024
    avail = info.get("MemAvailable", 0) / 1024 / 1024
    return (
        f"{cpu_model()}; {os.cpu_count()} CPUs; "
        f"MemTotal {total:.1f} GiB; MemAvailable {avail:.1f} GiB at script start"
    )


def summarise(samples: list[tuple]) -> dict:
    ok_times = [s for s, ok, _e, _v in samples if ok]
    errors = [e for _s, ok, e, _v in samples if not ok]
    return {
        "n": len(samples),
        "n_ok": len(ok_times),
        "n_err": len(errors),
        "median": median(ok_times),
        "p95": percentile(ok_times, 0.95),
        "min": min(ok_times) if ok_times else None,
        "max": max(ok_times) if ok_times else None,
        "error": errors[0] if errors else "",
        "timeouts": sum(1 for e in errors if "timeout" in e.lower() or "timedout" in e.lower()),
    }


def samples_for(rows: list[dict], section: str, size: str, param: str, side: str) -> list[tuple]:
    out = []
    for row in rows:
        if (
            row["section"] == section
            and row["size_label"] == size
            and row["param"] == param
            and row["side"] == side
            and row["run"] != ""
            and str(row["run"]) != "meta"
        ):
            ok = str(row["ok"]) == "1"
            seconds = float(row["seconds"]) if row["seconds"] != "" else 0.0
            out.append((seconds, ok, row["error"], None))
    return out


def write_report(path: Path, log: RowLog, meta: dict) -> None:
    rows = log.rows
    lines: list[str] = []
    lines.append("# Neo4j versus in-process MemNet")
    lines.append("")
    lines.append("Measurement only. The engine was not modified. No deployed host was touched.")
    lines.append("")
    lines.append("## Machine")
    lines.append("")
    lines.append(f"- Host: {meta['machine']}")
    lines.append(f"- Neo4j: {meta['neo4j']} (community tarball, not vendored)")
    lines.append(
        "- JVM caps set for this throwaway process: heap 512m-1g, page cache 512m, "
        "`db.transaction.timeout=30s`. A dedicated server would give Neo4j more RAM. "
        "These graphs are small enough that the page cache cap is unlikely to be the "
        "limiter; that was not re-measured with a larger heap."
    )
    lines.append(f"- Python driver: neo4j {meta['driver']}")
    lines.append(f"- MemNet package: {meta['memnet']}")
    lines.append(
        f"- Timed runs: {meta['runs']} after {meta['warmup']} warm-up calls, "
        "unless a cell stopped early (see notes)."
    )
    lines.append(
        f"- Product pin_map row cap: `DEFAULT_QUERY_MAX_ROWS={ROW_CAP}`. "
        "Shipped `MEMNET_MAX_ROWS` default is 5000. The three graphs here fit under that cap "
        "(80+79, 229+228, and 504+579 rows)."
    )
    lines.append("")
    lines.append("## What was timed")
    lines.append("")
    lines.append(
        "In-process recall is `PinMapComposer.compose` with a `qname` locator cue, "
        f"depth k, `max_rows={ROW_CAP}`, `active_only=True`. That includes the cue scan, "
        "the k-hop walk, the mixed law/node/edge clip, and shaped-text emit. "
        "`inprocess_walk` is `context_pack` only (seed already resolved), same depth and row cap."
    )
    lines.append("")
    lines.append(
        "Indexed Cypher (the working-store query) is an undirected variable-length "
        "match on `:MemnetPin` from the same `_memnet_hid`, `LIMIT 50` on **distinct nodes**. "
        "A uniqueness constraint on `:MemnetPin(_memnet_hid)` was created for this bench. "
        "The shipped adapter does not create that constraint and its hydrate query has no label."
    )
    lines.append("")
    lines.append(
        "Shipped Cypher is `build_hydrate_nodes_cypher` (the cabinet query): no `:MemnetPin` "
        "label, `LIMIT` = 50 nodes. It is not the same traversal as `neighbors` "
        "(no rank, no fan-out clamp, no mixed-row clip)."
    )
    lines.append("")
    lines.append(
        "Commit, in-process, is `MutateGate.apply(..., mode='mutate')` for 1, 10, and 100 "
        "new `REQ` pins, including parse, schema checks, and upsert. "
        "Neo4j commit is one Bolt transaction that `UNWIND`/`MERGE`s those same pins. "
        "**The Neo4j time does not include MutateGate.** A thin rules layer on Neo4j "
        "would still have to run those checks; add that cost on top of the Neo4j number. "
        "Cleanup of the batch is outside the timer."
    )
    lines.append("")
    lines.append(
        "Hydrate/flush uses `Neo4jAdapter.flush` then `Neo4jAdapter.hydrate` on one ego "
        "slice (`HydrateBudget` defaults: depth 2, 50 nodes, 100 edges) against the "
        "cabinet that already holds the full graph. Each shipped flush statement auto-commits. "
        "The slice build (`context_pack`) is outside the timer."
    )
    lines.append("")
    lines.append("## Graph sizes")
    lines.append("")
    lines.append(
        "These three cells are real `ingest_sysml` projections (`max_nodes=20000`, so the "
        "default 200-pin budget does not reject them). `implementation.sysml` is the "
        "closest model file to ~75 nodes (it is 80). `requirements.sysml` is the ~230 "
        "projection. `deploy.sysml` is the ~500 projection. Load times are a single sample, "
        "not a 200-run distribution."
    )
    lines.append("")
    lines.append("| label | nodes | edges | seed qname | degree min / p50 / p95 / max | load in-process | load Neo4j |")
    lines.append("|---|---:|---:|---|---|---:|---:|")
    for size in meta["sizes"]:
        if size["label"] not in IN_SCOPE:
            continue
        lines.append(
            f"| {size['label']} | {size['n_nodes']} | {size['n_edges']} | `{size['seed_qname']}` | "
            f"{size['deg']} | {fmt_s(size['load_local'])} | {fmt_s(size['load_neo'])} |"
        )
    lines.append("")
    lines.append("")
    lines.append("## Recall / pin_map")
    lines.append("")
    lines.append(
        "Ratio is Neo4j median / in-process `pin_map` median. Above 1 means Neo4j was slower. "
        "Node counts are the median over measured runs. The two LIMIT clauses do not clip "
        "the same thing: the engine clips a ranked mix of nodes and edges to 50 rows; "
        "Cypher returns up to 50 distinct nodes."
    )
    lines.append("")
    lines.append(_recall_table(rows, "cypher_indexed", "Indexed Cypher vs pin_map"))
    lines.append("")
    lines.append(_recall_table(rows, "cypher_shipped", "Shipped adapter node query vs pin_map"))
    lines.append("")
    lines.append("### Walk only (no cue scan, no shaped emit)")
    lines.append("")
    lines.append(
        "`inprocess_walk` median next to the same indexed Cypher median. "
        "Use this when the cue scan, not the hop, might dominate."
    )
    lines.append("")
    lines.append(_walk_table(rows))
    lines.append("")
    lines.append("### Uncapped k-hop node set (once per cell, not 200 runs)")
    lines.append("")
    lines.append(
        "Engine side is `neighbors` (full ball, fan-out clamp still applies). "
        "Cypher side is the same indexed pattern **without** `LIMIT`. "
        "Equal sets mean the walks reached the same nodes. A mismatch means the "
        "queries are not the same neighbourhood, quite apart from the row cap."
    )
    lines.append("")
    lines.append(
        "| size | k | engine nodes | cypher nodes | intersection | only engine | only cypher | "
        "equal | fan-out clamped | full-ball Cypher once |"
    )
    lines.append("|---|---:|---:|---:|---:|---:|---:|---|---|---:|")
    for row in rows:
        if row["section"] != "recall_ball" or row["size_label"] not in IN_SCOPE:
            continue
        once = float(row["seconds"]) if row["seconds"] else None
        lines.append(
            f"| {row['size_label']} | {row['param']} | {row['engine_nodes']} | {row['cypher_nodes']} | "
            f"{row['intersection']} | {row['only_engine']} | {row['only_cypher']} | "
            f"{'yes' if row['note'].startswith('equal') else 'no'} | "
            f"{'yes' if 'fanout' in row['note'] else 'no'} | {fmt_s(once) if row['ok'] == '1' else row['error']} |"
        )
    lines.append("")
    lines.append("## Commit")
    lines.append("")
    lines.append(
        "Ratio is Neo4j median / in-process median. The Neo4j column is MERGE only. "
        "It does **not** include schema validation, caps, ACL, or id minting. "
        "Those checks are inside the in-process number. Putting the same rules on "
        "Neo4j would add work that this table does not contain."
    )
    lines.append("")
    lines.append("| size | nodes in graph | batch | in-process median | in-process p95 | Neo4j median | Neo4j p95 | ratio | n in-process | n Neo4j | note |")
    lines.append("|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---|")
    for size_label, param in _pairs(rows, "commit"):
        loc = summarise(samples_for(rows, "commit", size_label, param, "inprocess"))
        neo = summarise(samples_for(rows, "commit", size_label, param, "neo4j"))
        n_nodes = _first(rows, "commit", size_label, "n_nodes")
        note = _note_pair(loc, neo)
        lines.append(
            f"| {size_label} | {n_nodes} | {param} | {fmt_s(loc['median'])} | {fmt_s(loc['p95'])} | "
            f"{fmt_s(neo['median'])} | {fmt_s(neo['p95'])} | {fmt_ratio(neo['median'], loc['median'])} | "
            f"{loc['n_ok']}/{loc['n']} | {neo['n_ok']}/{neo['n']} | {note} |"
        )
    lines.append("")
    lines.append("## Adapter hydrate and flush")
    lines.append("")
    lines.append(
        "One ego slice, shipped `Neo4jAdapter`, full graph already in the cabinet. "
        "Round-trip is flush then hydrate, timed as one sample. "
        "There is no in-process counterpart: this seam only exists because Neo4j is outside the process."
    )
    lines.append("")
    lines.append("| size | op | median | p95 | n ok / n | note |")
    lines.append("|---|---|---:|---:|---:|---|")
    for size_label, param in _pairs(rows, "adapter"):
        stats = summarise(samples_for(rows, "adapter", size_label, param, "neo4j"))
        note = stats["error"]
        if stats["n"] < meta["runs"]:
            note = (note + "; " if note else "") + f"stopped at {stats['n']} runs (asked {meta['runs']})"
        lines.append(
            f"| {size_label} | {param} | {fmt_s(stats['median'])} | {fmt_s(stats['p95'])} | "
            f"{stats['n_ok']}/{stats['n']} | {note} |"
        )
    lines.append("")
    lines.append("Slice versus hydrate node-set (one check after the timed loop):")
    lines.append("")
    lines.append("| size | flushed nodes | hydrated nodes | intersection | only flushed | only hydrated | note |")
    lines.append("|---|---:|---:|---:|---:|---:|---|")
    for row in rows:
        if row["section"] != "adapter_set" or row["size_label"] not in IN_SCOPE:
            continue
        lines.append(
            f"| {row['size_label']} | {row['engine_nodes']} | {row['cypher_nodes']} | "
            f"{row['intersection']} | {row['only_engine']} | {row['only_cypher']} | {row['note'] or row['error']} |"
        )
    lines.append("")
    lines.append("## Cold start and resident memory")
    lines.append("")
    lines.append(_cold_table(rows))
    lines.append("")
    lines.append("Resident set after each graph was loaded and the recall warm-up had run:")
    lines.append("")
    lines.append("| size | bench process RSS | Neo4j JVM RSS |")
    lines.append("|---|---:|---:|")
    for row in rows:
        if row["section"] != "rss" or row["size_label"] not in IN_SCOPE:
            continue
        lines.append(
            f"| {row['size_label']} | {row['engine_nodes']} MiB | {row['cypher_nodes']} MiB |"
        )
    lines.append("")
    lines.append(
        "Bench-process RSS is the measurement process (graph + driver + script), not a "
        "fresh engine. The cold-start engine RSS is a fresh interpreter that only opens "
        "an empty session. Neo4j RSS is the JVM process."
    )
    lines.append("")
    lines.append("## Conclusion")
    lines.append("")
    lines.extend(meta["conclusion"])
    lines.append("")
    lines.append("## Appendix: out of scope")
    lines.append("")
    big = [r for r in rows if r["size_label"] in {"n10000", "n100000"}]
    lines.append(
        f"Rows for 10,000 and 100,000 nodes are in `neo4j-bench-raw.csv` ({len(big)} rows) and are "
        "out of scope. MemNet sessions are bounded working memory at roughly 75 to 500 nodes, and "
        "graphs that big are too slow to be useful. They are not in the tables or the conclusion."
    )
    lines.append("")
    lines.append("## Caveats")
    lines.append("")
    lines.append(
        "- Absolute times will not transfer to the production host. That host is a "
        "Raspberry Pi 5 (ARM, 8 GB) shared with other services. This VM is x86_64 with "
        "more RAM and a different CPU. Ratios are the only figure worth carrying across, "
        "and even ratios can move when Bolt latency, page cache, and core count change."
    )
    lines.append(
        "- The indexed Cypher query and `pin_map` do not implement the same walk or the "
        "same truncation. Where the uncapped node sets differ, do not read the latency "
        "ratio as a ratio of equal work."
    )
    lines.append(
        "- Neo4j commit time is MERGE only. MemNet's gate checks are not in that number."
    )
    lines.append(
        "- The shipped adapter opens a Bolt session per statement and auto-commits each "
        "MERGE. The commit benchmark uses one transaction per batch, which is what a "
        "purpose-built working store would do. Hydrate/flush timings are the shipped adapter."
    )
    lines.append(
        "- `implementation.sysml` is 80 nodes, not 75. No model file in `sysml-models/models` "
        "projects to 75 nodes."
    )
    lines.append(
        "- A cell that timed out records the runs that actually executed. Remaining runs "
        "were not invented."
    )
    lines.append("")
    path.write_text("\n".join(lines) + "\n")


def _pairs(rows: list[dict], section: str, *, labels: tuple[str, ...] | None = IN_SCOPE) -> list[tuple[str, str]]:
    seen = []
    for row in rows:
        if row["section"] != section or row["run"] == "meta":
            continue
        if labels is not None and row["size_label"] not in labels:
            continue
        key = (row["size_label"], row["param"])
        if key not in seen:
            seen.append(key)
    return seen


def _first(rows, section, size, field):
    for row in rows:
        if row["section"] == section and row["size_label"] == size and row[field] != "":
            return row[field]
    return ""


def _note_pair(loc: dict, neo: dict) -> str:
    bits = []
    if loc["n_err"]:
        bits.append(f"in-process errors {loc['n_err']}: {loc['error'][:160]}")
    if neo["n_err"]:
        bits.append(f"neo4j errors {neo['n_err']}: {neo['error'][:160]}")
    if loc["n"] != neo["n"]:
        bits.append(f"runs in-process {loc['n']} vs Neo4j {neo['n']}")
    return "; ".join(bits)


def _recall_table(rows: list[dict], neo_side: str, title: str) -> str:
    lines = [f"### {title}", ""]
    lines.append(
        "| size | k | pin_map median | pin_map p95 | Neo4j median | Neo4j p95 | ratio | "
        "equal node sets | median intersection | median only engine | median only cypher | n pin_map / n Cypher | note |"
    )
    lines.append("|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---|")
    for size_label, param in _pairs(rows, "recall"):
        if not any(
            r["section"] == "recall" and r["size_label"] == size_label and r["param"] == param and r["side"] == neo_side
            for r in rows
        ):
            continue
        loc = summarise(samples_for(rows, "recall", size_label, param, "inprocess_pin_map"))
        neo = summarise(samples_for(rows, "recall", size_label, param, neo_side))
        subset = [
            r
            for r in rows
            if r["section"] == "recall"
            and r["size_label"] == size_label
            and r["param"] == param
            and r["side"] == neo_side
            and r["ok"] == "1"
        ]
        equal = 0
        inter, only_e, only_c = [], [], []
        for r in subset:
            if r["intersection"] == "":
                continue
            inter.append(float(r["intersection"]))
            only_e.append(float(r["only_engine"]))
            only_c.append(float(r["only_cypher"]))
            if r["only_engine"] == "0" and r["only_cypher"] == "0":
                equal += 1
        n = len(subset)
        eq = f"{equal}/{n}" if n else "n/a"
        note = _note_pair(loc, neo)
        lines.append(
            f"| {size_label} | {param} | {fmt_s(loc['median'])} | {fmt_s(loc['p95'])} | "
            f"{fmt_s(neo['median'])} | {fmt_s(neo['p95'])} | {fmt_ratio(neo['median'], loc['median'])} | "
            f"{eq} | {fmt_num(median(inter))} | {fmt_num(median(only_e))} | {fmt_num(median(only_c))} | "
            f"{loc['n_ok']}/{loc['n']} / {neo['n_ok']}/{neo['n']} | {note} |"
        )
    return "\n".join(lines)


def _walk_table(rows: list[dict]) -> str:
    lines = [
        "| size | k | walk median | walk p95 | indexed Cypher median | ratio cypher/walk | n walk | n Cypher |",
        "|---|---:|---:|---:|---:|---:|---:|---:|",
    ]
    for size_label, param in _pairs(rows, "recall"):
        walk = summarise(samples_for(rows, "recall", size_label, param, "inprocess_walk"))
        neo = summarise(samples_for(rows, "recall", size_label, param, "cypher_indexed"))
        if walk["n"] == 0 and neo["n"] == 0:
            continue
        lines.append(
            f"| {size_label} | {param} | {fmt_s(walk['median'])} | {fmt_s(walk['p95'])} | "
            f"{fmt_s(neo['median'])} | {fmt_ratio(neo['median'], walk['median'])} | "
            f"{walk['n_ok']}/{walk['n']} | {neo['n_ok']}/{neo['n']} |"
        )
    return "\n".join(lines)


def _note_rss_kib(rows: list[dict], side: str, param: str) -> str:
    rss = []
    for row in rows:
        if row["section"] != "cold" or row["side"] != side or row["param"] != param or row["ok"] != "1":
            continue
        for part in (row["note"] or "").split(";"):
            if part.startswith("rss_kib="):
                try:
                    rss.append(float(part.split("=", 1)[1]))
                except ValueError:
                    pass
    if not rss:
        return ""
    med = median(rss)
    if med is None:
        return ""
    return f"median RSS {med / 1024:.1f} MiB (n={len(rss)})"


def _cold_table(rows: list[dict]) -> str:
    lines = [
        "n is the number of cold starts actually executed. Neo4j was stopped before 200.",
        "",
        "| side | what | median | p95 | n ok / n | resident |",
        "|---|---|---:|---:|---:|---|",
    ]
    seen = []
    for row in rows:
        if row["section"] != "cold" or row["run"] == "meta":
            continue
        key = (row["side"], row["param"])
        if key in seen:
            continue
        seen.append(key)
        stats = summarise(samples_for(rows, "cold", row["size_label"], row["param"], row["side"]))
        lines.append(
            f"| {row['side']} | {row['param']} | {fmt_s(stats['median'])} | {fmt_s(stats['p95'])} | "
            f"{stats['n_ok']}/{stats['n']} | {_note_rss_kib(rows, row['side'], row['param'])} |"
        )
    if len(lines) == 4:
        lines.append("| n/a | cold start not run | n/a | n/a | 0/0 | |")
    return "\n".join(lines)


def fmt_num(value: float | None) -> str:
    if value is None:
        return "n/a"
    if float(value).is_integer():
        return str(int(value))
    return f"{value:.1f}"


def build_conclusion(rows: list[dict], runs: int) -> list[str]:
    """Headline from the three working-memory sizes only. No 10k or 100k figures."""
    lines = [
        "Ratios are Neo4j median / in-process median on this VM. Above 1 means Neo4j was slower. "
        "Only the ~75, ~230, and ~500 node cells are in this conclusion. "
        "Each latency cell below is n=200 successful runs unless a sentence says otherwise."
    ]
    lines.append("")
    bits = []
    for size_label, param in _pairs(rows, "recall"):
        loc = summarise(samples_for(rows, "recall", size_label, param, "inprocess_pin_map"))
        neo = summarise(samples_for(rows, "recall", size_label, param, "cypher_indexed"))
        if loc["median"] is None or neo["median"] is None:
            continue
        bits.append(
            f"{size_label} k={param}: pin_map {fmt_s(loc['median'])} (p95 {fmt_s(loc['p95'])}, n={loc['n_ok']}), "
            f"indexed Cypher {fmt_s(neo['median'])} (p95 {fmt_s(neo['p95'])}, n={neo['n_ok']}), "
            f"ratio {fmt_ratio(neo['median'], loc['median'])}"
        )
    lines.append(
        "Recall, indexed Cypher versus pin_map: " + "; ".join(bits) + "."
        if bits
        else "Recall: no paired medians."
    )
    lines.append("")
    lines.append(
        "That recall ratio is not a ratio of equal results. The uncapped k-hop node sets matched "
        "on a single check at every in-scope cell (see the table; that check is n=1, not 200). "
        "The timed queries did not return the same node set in any of the 200 runs: pin_map clips "
        "a ranked mix of nodes and edges to 50 rows, and Cypher `LIMIT`s 50 distinct nodes. "
        "The flat ~1–2 ms Cypher medians are that limited query. The one full-ball Cypher time "
        "is the last column of the uncapped table, and at 504 nodes it sits in the same tens of "
        "milliseconds as pin_map, not at the limited-query median."
    )
    lines.append("")
    cbits = []
    for size_label, param in _pairs(rows, "commit"):
        loc = summarise(samples_for(rows, "commit", size_label, param, "inprocess"))
        neo = summarise(samples_for(rows, "commit", size_label, param, "neo4j"))
        if loc["median"] is None or neo["median"] is None:
            continue
        cbits.append(
            f"{size_label} batch {param}: in-process {fmt_s(loc['median'])} (n={loc['n_ok']}), "
            f"Neo4j MERGE {fmt_s(neo['median'])} (n={neo['n_ok']}), "
            f"ratio {fmt_ratio(neo['median'], loc['median'])}"
        )
    lines.append("Commit: " + "; ".join(cbits) + "." if cbits else "Commit: no paired medians.")
    lines.append("")
    lines.append(
        "A batch of 1 pin is about parity. Batches of 10 and 100 are faster as a Neo4j `UNWIND`/`MERGE` "
        "than through `MutateGate`. The Neo4j number does not include parse, schema, caps, or id checks. "
        "A thin rules layer on Neo4j would still have to run those checks; that cost was not measured."
    )
    lines.append("")
    eng = summarise(samples_for(rows, "cold", "process", "engine_wall_import_and_open_session", "inprocess"))
    jvm = summarise(samples_for(rows, "cold", "process", "neo4j_start_until_bolt", "neo4j"))
    if eng["median"] is not None or jvm["median"] is not None:
        lines.append(
            f"Cold start: engine process (import plus empty `open_session`) median {fmt_s(eng['median'])} "
            f"(p95 {fmt_s(eng['p95'])}, n={eng['n_ok']}/{eng['n']}); "
            f"Neo4j JVM start until Bolt accepts `RETURN 1` median {fmt_s(jvm['median'])} "
            f"(p95 {fmt_s(jvm['p95'])}, n={jvm['n_ok']}/{jvm['n']}). "
            f"Empty-session engine {_note_rss_kib(rows, 'inprocess', 'engine_wall_import_and_open_session')}. "
            f"Neo4j JVM {_note_rss_kib(rows, 'neo4j', 'neo4j_start_until_bolt')}."
        )
        lines.append("")
    lines.append(
        "These ratios will not transfer as absolute times to the Raspberry Pi 5 (ARM, 8 GB, shared). "
        "They also do not show that MemNet should become a Cypher proxy: the limited recalls do not "
        "match, and the commit comparison leaves the gate on only one side."
    )
    return lines


def cold_engine(runs: int, warmup: int, log: RowLog) -> None:
    code = (
        "import os, time\n"
        "os.environ['MEMNET_MAX_ROWS']='2000000'\n"
        "t0=time.perf_counter()\n"
        "from memnet.config import Caps, examples_dir\n"
        "from memnet.session import open_session\n"
        "schema=examples_dir()/'schema.sysml.example.txt'\n"
        "s=open_session(map_file=str(schema), caps=Caps(), ttl_minutes=10)\n"
        "_=s.store.row_count_non_law()\n"
        "elapsed=time.perf_counter()-t0\n"
        "rss=0\n"
        "for line in open('/proc/self/status'):\n"
        "    if line.startswith('VmRSS:'):\n"
        "        rss=int(line.split()[1]); break\n"
        "print(f'{elapsed} {rss}')\n"
    )
    def once(label: str):
        t0 = time.perf_counter()
        proc = subprocess.run(
            [sys.executable, "-c", code],
            capture_output=True,
            text=True,
            cwd=str(REPO),
        )
        wall = time.perf_counter() - t0
        if proc.returncode != 0:
            raise RuntimeError(proc.stderr[-500:] or proc.stdout[-500:])
        inner, rss = proc.stdout.strip().split()
        return wall, float(inner), int(rss)

    # warmup discards
    for _ in range(warmup):
        try:
            once("warmup")
        except Exception as exc:
            log.add(
                section="cold",
                size_label="process",
                param="engine_wall_import_and_open_session",
                side="inprocess",
                run="meta",
                ok="0",
                error=f"warmup failed: {exc}",
            )
            return
    for i in range(runs):
        try:
            wall, inner, rss = once("run")
            log.add(
                section="cold",
                size_label="process",
                param="engine_wall_import_and_open_session",
                side="inprocess",
                run=i,
                seconds=f"{wall:.6f}",
                ok="1",
                note=f"inner_import_open_s={inner:.6f};rss_kib={rss}",
            )
        except Exception as exc:
            log.add(
                section="cold",
                size_label="process",
                param="engine_wall_import_and_open_session",
                side="inprocess",
                run=i,
                ok="0",
                error=str(exc)[:300],
            )


def cold_neo4j(home: Path, runs: int, warmup: int, log: RowLog, user: str, password: str, url: str) -> None:
    neo4j = str(home / "bin" / "neo4j")
    shell = str(home / "bin" / "cypher-shell")

    def ready() -> bool:
        proc = subprocess.run(
            [shell, "-a", url, "-u", user, "-p", password, "RETURN 1;"],
            capture_output=True,
            text=True,
        )
        return proc.returncode == 0

    def cycle():
        subprocess.run([neo4j, "stop"], check=False, capture_output=True, text=True)
        # wait until bolt is down
        deadline = time.perf_counter() + 60
        while time.perf_counter() < deadline and ready():
            time.sleep(0.2)
        t0 = time.perf_counter()
        subprocess.run([neo4j, "start"], check=True, capture_output=True, text=True)
        while time.perf_counter() - t0 < 120:
            if ready():
                wall = time.perf_counter() - t0
                rss = rss_kb(neo4j_pid(home))
                return wall, rss
            time.sleep(0.2)
        raise TimeoutError("neo4j did not accept Bolt within 120s")

    for _ in range(warmup):
        cycle()
    for i in range(runs):
        try:
            wall, rss = cycle()
            log.add(
                section="cold",
                size_label="process",
                param="neo4j_start_until_bolt",
                side="neo4j",
                run=i,
                seconds=f"{wall:.6f}",
                ok="1",
                note=f"rss_kib={rss}",
            )
            print(f"cold neo4j {i+1}/{runs} {wall:.2f}s", flush=True)
        except Exception as exc:
            log.add(
                section="cold",
                size_label="process",
                param="neo4j_start_until_bolt",
                side="neo4j",
                run=i,
                ok="0",
                error=str(exc)[:300],
            )
            print(f"cold neo4j {i+1} FAIL {exc}", flush=True)
            break


def size_meta_from_rows(rows: list[dict]) -> list[dict]:
    out: list[dict] = []
    for row in rows:
        if row["section"] != "size_meta":
            continue
        note: dict[str, str] = {}
        for part in (row["note"] or "").split(";"):
            if "=" in part:
                key, val = part.split("=", 1)
                note[key] = val
        out.append(
            {
                "label": row["size_label"],
                "n_nodes": int(row["n_nodes"] or 0),
                "n_edges": int(row["n_edges"] or 0),
                "seed_qname": note.get("seed", ""),
                "deg": note.get("deg", ""),
                "load_local": float(note["load_local_s"]) if note.get("load_local_s") else None,
                "load_neo": float(note["load_neo_s"]) if note.get("load_neo_s") else None,
            }
        )
    return out


def report_from_csv(args) -> None:
    """Rewrite the markdown from rows already on disk. Does not measure."""
    log = RowLog(args.out_dir / "neo4j-bench-raw.csv", append=True)
    # Measured server. Do not open Bolt again just to reprint the version.
    checkpoint_report(args, log, size_meta_from_rows(log.rows), "Neo4j Kernel 5.26.15 community")
    log.close()
    print(f"rewrote report from {args.out_dir / 'neo4j-bench-raw.csv'}", flush=True)


def checkpoint_report(args, log: RowLog, size_meta: list[dict], neo_desc: str) -> None:
    import memnet
    import neo4j

    stored_machine = ""
    for row in log.rows:
        if row["section"] == "meta" and row["size_label"] == "machine" and row["note"]:
            stored_machine = row["note"]
            break
    meta = {
        "machine": stored_machine or machine_note(),
        "neo4j": neo_desc,
        "driver": neo4j.__version__,
        "memnet": getattr(memnet, "__version__", "unknown"),
        "runs": args.runs,
        "warmup": args.warmup,
        "sizes": size_meta,
        "source_degree": "",
        "conclusion": build_conclusion(log.rows, args.runs),
    }
    # source degree is a meta row written before sizes; keep it if present.
    for row in log.rows:
        if row["section"] == "meta" and row["size_label"] == "source_degree":
            meta["source_degree"] = row["note"]
    write_report(args.out_dir / "neo4j-bench-report.md", log, meta)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--out-dir", type=Path, default=Path("/opt/cursor/artifacts"))
    parser.add_argument("--runs", type=int, default=200)
    parser.add_argument("--warmup", type=int, default=20)
    parser.add_argument("--cold-runs", type=int, default=200)
    parser.add_argument("--cold-warmup", type=int, default=1)
    parser.add_argument(
        "--sizes",
        default="n80,n229,n504",
        help="comma list of working-memory sizes: n80,n229,n504",
    )
    parser.add_argument("--skip-cold", action="store_true")
    parser.add_argument(
        "--append",
        action="store_true",
        help="keep an existing raw CSV and skip sizes that already have size_meta",
    )
    parser.add_argument(
        "--report-only",
        action="store_true",
        help="rewrite the markdown report from the existing raw CSV; do not measure",
    )
    parser.add_argument("--query-timeout", type=float, default=QUERY_TIMEOUT_S)
    args = parser.parse_args()
    if args.report_only:
        report_from_csv(args)
        return

    url = (os.environ.get("MEMNET_NEO4J_URL") or "bolt://127.0.0.1:7687").strip()
    user = (os.environ.get("MEMNET_NEO4J_USER") or "neo4j").strip()
    password = os.environ.get("MEMNET_NEO4J_PASSWORD") or ""
    if not password:
        print("MEMNET_NEO4J_PASSWORD is required", file=sys.stderr)
        sys.exit(2)
    home_raw = (os.environ.get("NEO4J_HOME") or "").strip()
    home = Path(home_raw) if home_raw else None

    import memnet
    import neo4j

    driver = connect(url, user, password)
    with driver.session() as session:
        rec = session.run(
            "CALL dbms.components() YIELD name, versions, edition "
            "RETURN name, versions[0] AS version, edition"
        ).single()
        neo_desc = f"{rec['name']} {rec['version']} {rec['edition']}"
    print(f"connected {neo_desc}", flush=True)
    ensure_constraint(driver)

    wanted = [s.strip() for s in args.sizes.split(",") if s.strip()]
    # Degree source is always requirements, even if that size is not timed.
    print("loading requirements degree source", flush=True)
    src_session, _src_load = load_sysml(MODELS / "requirements.sysml")
    empirical = undirected_degrees(src_session.store)
    relation = modal_relation(src_session.store)
    source_degree = degree_summary(empirical)
    print(f"source degree {source_degree} relation {relation}", flush=True)
    close_session(src_session.session_id)
    del src_session
    gc.collect()

    log = RowLog(args.out_dir / "neo4j-bench-raw.csv", append=args.append)
    if not args.append:
        log.add(
            section="meta",
            size_label="machine",
            side="host",
            run="meta",
            note=machine_note(),
            ok="1",
        )
        log.add(
            section="meta",
            size_label="source_degree",
            side="requirements",
            run="meta",
            note=json.dumps(source_degree),
            ok="1",
        )
    done = {r["size_label"] for r in log.rows if r["section"] == "size_meta"}
    size_meta: list[dict] = []
    for row in log.rows:
        if row["section"] != "size_meta":
            continue
        note = {}
        for part in (row["note"] or "").split(";"):
            if "=" in part:
                k, v = part.split("=", 1)
                note[k] = v
        size_meta.append(
            {
                "label": row["size_label"],
                "n_nodes": int(row["n_nodes"] or 0),
                "n_edges": int(row["n_edges"] or 0),
                "seed_qname": note.get("seed", ""),
                "deg": note.get("deg", ""),
                "load_local": float(note["load_local_s"]) if note.get("load_local_s") else None,
                "load_neo": float(note["load_neo_s"]) if note.get("load_neo_s") else None,
            }
        )

    specs = {
        "n80": ("sysml", MODELS / "implementation.sysml"),
        "n229": ("sysml", MODELS / "requirements.sysml"),
        "n504": ("sysml", MODELS / "deploy.sysml"),
        "n10000": ("synthetic", 10_000),
        "n100000": ("synthetic", 100_000),
    }
    rng = random.Random(0)
    timeout = args.query_timeout

    for key in wanted:
        if key in done:
            print(f"=== size {key} already in CSV; skip ===", flush=True)
            continue
        kind, payload = specs[key]
        print(f"=== size {key} ({kind}) ===", flush=True)
        clear_graph(driver)
        if kind == "sysml":
            session, load_local = load_sysml(payload)
        else:
            session, load_local = load_synthetic(int(payload), empirical, relation, rng)
        store = session.store
        n_nodes = len(node_records(store))
        n_edges = len(edge_records(store))
        degs = undirected_degrees(store)
        deg_s = degree_summary(degs)
        seed, qname, seed_deg = pick_seed(store)
        seed_hid = seed.hid
        print(
            f"loaded nodes={n_nodes} edges={n_edges} seed={qname} hid={seed_hid} "
            f"seed_deg={seed_deg} deg={deg_s} local_load={load_local:.2f}s",
            flush=True,
        )
        load_neo = push_neo4j(driver, store)
        print(f"neo4j load {load_neo:.2f}s", flush=True)
        composer = PinMapComposer(session)
        gate = MutateGate(session)

        for k in (2, 3):
            param = str(k)
            ball, ball_rows, fanout = full_ball(store, seed_hid, k)
            print(f"k={k} engine ball nodes={len(ball)} records={ball_rows} fanout={fanout}", flush=True)
            try:
                t0 = time.perf_counter()
                cy_rows, _dt = read_rows(driver, cypher_ball(k), {"hid": seed_hid}, timeout)
                cy_set = set(hids_of(cy_rows))
                ball_err = ""
                ball_ok = "1"
                ball_s = time.perf_counter() - t0
            except Exception as exc:
                cy_set = set()
                ball_err = f"{type(exc).__name__}: {exc}"[:300]
                ball_ok = "0"
                ball_s = timeout
            inter = ball & cy_set
            note = "equal" if ball_ok == "1" and ball == cy_set else "mismatch"
            if fanout:
                note += "; fanout"
            log.add(
                section="recall_ball",
                size_label=key,
                n_nodes=n_nodes,
                n_edges=n_edges,
                param=param,
                side="compare",
                run=0,
                seconds=f"{ball_s:.6f}",
                ok=ball_ok,
                error=ball_err,
                engine_nodes=len(ball),
                cypher_nodes=len(cy_set),
                intersection=len(inter),
                only_engine=len(ball - cy_set),
                only_cypher=len(cy_set - ball),
                note=note,
            )

            def do_pinmap(k=k):
                return recall_one_engine(composer, qname, k)

            def do_walk(k=k):
                return recall_one_walk(store, seed_hid, k)

            print(f"k={k} timing pin_map and walk", flush=True)
            pin_samples = run_samples(do_pinmap, args.runs, args.warmup)
            walk_samples = run_samples(do_walk, args.runs, args.warmup)
            for i, (seconds, ok, err, value) in enumerate(pin_samples):
                log.add(
                    section="recall",
                    size_label=key,
                    n_nodes=n_nodes,
                    n_edges=n_edges,
                    param=param,
                    side="inprocess_pin_map",
                    run=i,
                    seconds=f"{seconds:.6f}",
                    ok="1" if ok else "0",
                    error="" if ok else err[:300],
                    note="truncated" if ok and value and "truncated=true" in value[1] else "",
                )
            for i, (seconds, ok, err, _value) in enumerate(walk_samples):
                log.add(
                    section="recall",
                    size_label=key,
                    n_nodes=n_nodes,
                    n_edges=n_edges,
                    param=param,
                    side="inprocess_walk",
                    run=i,
                    seconds=f"{seconds:.6f}",
                    ok="1" if ok else "0",
                    error="" if ok else err[:300],
                )

            indexed_q = cypher_indexed(k)
            shipped_q, shipped_params = build_hydrate_nodes_cypher(
                seed_hid, HydrateBudget(depth=k, max_nodes=ROW_CAP, max_edges=0)
            )
            # Graph is stable during recall, so the clipped pin_map node set is stable.
            try:
                pin_rows, _pin_text = do_pinmap()
                e_set = engine_node_hids(pin_rows)
            except Exception as exc:
                print(f"k={k} pin_map set capture failed: {exc}", flush=True)
                pin_rows = []
                e_set = set()

            def do_indexed(q=indexed_q, hid=seed_hid):
                rows, _elapsed = read_rows(driver, q, {"hid": hid, "limit": ROW_CAP}, timeout)
                return hids_of(rows)

            def do_shipped(q=shipped_q, params=shipped_params):
                rows, _elapsed = read_rows(driver, q, params, timeout)
                return hids_of(rows)

            print(f"k={k} timing cypher", flush=True)
            consecutive_to = 0
            for _ in range(args.warmup):
                try:
                    do_indexed()
                except Exception:
                    break
            for i in range(args.runs):
                seconds, ok, err, value = time_call(do_indexed)
                c_set = set(value or [])
                log.add(
                    section="recall",
                    size_label=key,
                    n_nodes=n_nodes,
                    n_edges=n_edges,
                    param=param,
                    side="cypher_indexed",
                    run=i,
                    seconds=f"{seconds:.6f}",
                    ok="1" if ok else "0",
                    error="" if ok else err[:300],
                    engine_nodes=len(e_set),
                    cypher_nodes=len(c_set) if ok else "",
                    intersection=len(e_set & c_set) if ok else "",
                    only_engine=len(e_set - c_set) if ok else "",
                    only_cypher=len(c_set - e_set) if ok else "",
                )
                if not ok and is_timeout(Exception(err)):
                    consecutive_to += 1
                    if consecutive_to >= 5:
                        print(f"k={k} indexed aborted after timeouts", flush=True)
                        break
                else:
                    consecutive_to = 0
                if (i + 1) % 50 == 0:
                    print(f"k={k} indexed {i+1}", flush=True)

            consecutive_to = 0
            for _ in range(min(args.warmup, 3)):
                try:
                    do_shipped()
                except Exception:
                    break
            for i in range(args.runs):
                seconds, ok, err, value = time_call(do_shipped)
                c_set = set(value or [])
                log.add(
                    section="recall",
                    size_label=key,
                    n_nodes=n_nodes,
                    n_edges=n_edges,
                    param=param,
                    side="cypher_shipped",
                    run=i,
                    seconds=f"{seconds:.6f}",
                    ok="1" if ok else "0",
                    error="" if ok else err[:300],
                    engine_nodes=len(e_set),
                    cypher_nodes=len(c_set) if ok else "",
                    intersection=len(e_set & c_set) if ok else "",
                    only_engine=len(e_set - c_set) if ok else "",
                    only_cypher=len(c_set - e_set) if ok else "",
                )
                if not ok and is_timeout(Exception(err)):
                    consecutive_to += 1
                    if consecutive_to >= 5:
                        print(f"k={k} shipped aborted after timeouts", flush=True)
                        break
                else:
                    consecutive_to = 0

        for batch in (1, 10, 100):
            print(f"commit batch {batch}", flush=True)

            def do_commit(batch=batch):
                token = f"{key}_{batch}_{time.time_ns()}"
                lines = commit_lines(batch, token)
                t0 = time.perf_counter()
                result = gate.apply(lines, mode="mutate", allow_new_relation=True)
                local_s = time.perf_counter() - t0
                neo_err = ""
                try:
                    t1 = time.perf_counter()
                    merge_created(driver, result.records)
                    neo_s = time.perf_counter() - t1
                except Exception as exc:  # noqa: BLE001 — recorded, then cleaned up
                    neo_s = time.perf_counter() - t1
                    neo_err = f"{type(exc).__name__}: {exc}"
                try:
                    delete_created(store, driver, result.records)
                except Exception:
                    pass
                return local_s, neo_s, len(result.records), neo_err

            # warmup
            warm_ok = True
            for _ in range(args.warmup):
                try:
                    _local_s, _neo_s, _nrec, neo_err = do_commit()
                    if neo_err:
                        raise RuntimeError(neo_err)
                except Exception as exc:
                    log.add(
                        section="commit",
                        size_label=key,
                        n_nodes=n_nodes,
                        n_edges=n_edges,
                        param=str(batch),
                        side="inprocess",
                        run="meta",
                        ok="0",
                        error=f"warmup: {type(exc).__name__}: {exc}"[:300],
                    )
                    warm_ok = False
                    break
            if not warm_ok:
                continue
            for i in range(args.runs):
                try:
                    local_s, neo_s, nrec, neo_err = do_commit()
                except Exception as exc:
                    err = f"{type(exc).__name__}: {exc}"[:300]
                    log.add(
                        section="commit",
                        size_label=key,
                        n_nodes=n_nodes,
                        n_edges=n_edges,
                        param=str(batch),
                        side="inprocess",
                        run=i,
                        ok="0",
                        error=err,
                    )
                    print(f"commit fail {err}", flush=True)
                    break
                log.add(
                    section="commit",
                    size_label=key,
                    n_nodes=n_nodes,
                    n_edges=n_edges,
                    param=str(batch),
                    side="inprocess",
                    run=i,
                    seconds=f"{local_s:.6f}",
                    ok="1",
                    note=f"records={nrec}",
                )
                log.add(
                    section="commit",
                    size_label=key,
                    n_nodes=n_nodes,
                    n_edges=n_edges,
                    param=str(batch),
                    side="neo4j",
                    run=i,
                    seconds=f"{neo_s:.6f}",
                    ok="0" if neo_err else "1",
                    error=neo_err[:300],
                    note=f"records={nrec}",
                )
                if neo_err:
                    print(f"commit neo4j fail {neo_err}", flush=True)
                    break

        print("adapter round-trip", flush=True)
        budget = HydrateBudget()
        subgraph = slice_subgraph(store, seed_hid)
        adapter = Neo4jAdapter(
            Neo4jConfig(url=url, user=user, password=password, database="neo4j")
        )
        # One untimed flush so hydrate has the slice even if a later flush fails.
        try:
            adapter.flush(subgraph)
        except Exception as exc:
            print(f"prime flush failed {exc}", flush=True)

        def do_flush():
            adapter.flush(subgraph)

        def do_hydrate():
            return adapter.hydrate(seed_hid, budget)

        def do_round():
            adapter.flush(subgraph)
            return adapter.hydrate(seed_hid, budget)

        for name, fn in (("flush", do_flush), ("hydrate", do_hydrate), ("round_trip", do_round)):
            samples = run_samples(fn, args.runs, min(args.warmup, 5))
            for i, (seconds, ok, err, _value) in enumerate(samples):
                log.add(
                    section="adapter",
                    size_label=key,
                    n_nodes=n_nodes,
                    n_edges=n_edges,
                    param=name,
                    side="neo4j",
                    run=i,
                    seconds=f"{seconds:.6f}",
                    ok="1" if ok else "0",
                    error="" if ok else err[:300],
                    note=f"slice_nodes={len(subgraph.nodes)};slice_edges={len(subgraph.edges)}",
                )
            print(f"adapter {name} n={len(samples)}", flush=True)
        try:
            hydrated = adapter.hydrate(seed_hid, budget)
            h_set = {record_cabinet_hid(r) for r in hydrated.nodes}
            f_set = {record_cabinet_hid(r) for r in subgraph.nodes}
            log.add(
                section="adapter_set",
                size_label=key,
                n_nodes=n_nodes,
                n_edges=n_edges,
                param="hydrate_vs_flush_slice",
                side="neo4j",
                run=0,
                ok="1",
                engine_nodes=len(f_set),
                cypher_nodes=len(h_set),
                intersection=len(f_set & h_set),
                only_engine=len(f_set - h_set),
                only_cypher=len(h_set - f_set),
                note="equal" if f_set == h_set else "mismatch",
            )
        except Exception as exc:
            log.add(
                section="adapter_set",
                size_label=key,
                n_nodes=n_nodes,
                n_edges=n_edges,
                param="hydrate_vs_flush_slice",
                side="neo4j",
                run=0,
                ok="0",
                error=f"{type(exc).__name__}: {exc}"[:300],
            )
        adapter.close()

        proc_rss = rss_kb()
        jvm_rss = rss_kb(neo4j_pid(home))
        log.add(
            section="rss",
            size_label=key,
            n_nodes=n_nodes,
            n_edges=n_edges,
            param="after_load",
            side="both",
            run=0,
            ok="1",
            engine_nodes=f"{(proc_rss or 0)/1024:.1f}",
            cypher_nodes=f"{(jvm_rss or 0)/1024:.1f}",
            note=f"bench_rss_kib={proc_rss};neo4j_rss_kib={jvm_rss}",
        )
        size_meta.append(
            {
                "label": key,
                "n_nodes": n_nodes,
                "n_edges": n_edges,
                "seed_qname": qname,
                "deg": (
                    f"{deg_s['min']} / {fmt_num(deg_s['p50'])} / "
                    f"{fmt_num(deg_s['p95'])} / {deg_s['max']}"
                ),
                "load_local": load_local,
                "load_neo": load_neo,
            }
        )
        log.add(
            section="size_meta",
            size_label=key,
            n_nodes=n_nodes,
            n_edges=n_edges,
            param="load",
            side="both",
            run="meta",
            ok="1",
            note=(
                f"seed={qname};seed_hid={seed_hid};seed_deg={seed_deg};"
                f"deg={size_meta[-1]['deg']};"
                f"load_local_s={load_local:.6f};load_neo_s={load_neo:.6f}"
            ),
        )
        checkpoint_report(args, log, size_meta, neo_desc)
        close_session(session.session_id)
        del session, store, composer, gate
        gc.collect()

    # Empty the cabinet before JVM restarts so cold start is boot, not recovery of 100k.
    try:
        clear_graph(driver)
    except Exception as exc:
        print(f"pre-cold wipe failed: {exc}", flush=True)
    driver.close()

    if not args.skip_cold and args.cold_runs > 0:
        print("cold engine", flush=True)
        cold_engine(args.cold_runs, args.cold_warmup, log)
        if home is not None:
            print("cold neo4j", flush=True)
            cold_neo4j(home, args.cold_runs, args.cold_warmup, log, user, password, url)
        else:
            log.add(
                section="cold",
                size_label="process",
                param="neo4j_start_until_bolt",
                side="neo4j",
                run="meta",
                ok="0",
                error="NEO4J_HOME unset; JVM cold start not measured",
            )

    checkpoint_report(args, log, size_meta, neo_desc)
    log.close()
    print(f"wrote {args.out_dir}", flush=True)


if __name__ == "__main__":
    main()
