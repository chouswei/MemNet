"""Helpers for one-session-per-document serve probes. Never emit a session id."""

from __future__ import annotations

import json
import os
import re
import socket
import subprocess
import sys
import time
from collections.abc import Iterator
from contextlib import contextmanager
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from memnet.serve import send_command

SID_RE = re.compile(r"mn_[0-9a-fA-F]+")
ADMIN_TOKEN = "probe-admin-token"
TECHDOCS_MAP = (
    Path(__file__).resolve().parents[1]
    / "parts"
    / "common"
    / "memnet"
    / "memnet"
    / "examples"
    / "schema.techdocs.example.txt"
)
_ENGINE = Path(__file__).resolve().parents[1] / "parts" / "common" / "memnet" / "memnet"
SNAPSHOT_PY = _ENGINE / "snapshot.py"
MEM_STORE_PY = _ENGINE / "mem_store.py"
TAG_MAP_PY = _ENGINE / "tag_map.py"
GQL_PY = _ENGINE / "gql.py"
PIN_MAP_INGEST_PY = _ENGINE / "pin_map_ingest.py"
PIN_MAP_COMPOSER_PY = _ENGINE / "pin_map_composer.py"
CONFIG_PY = _ENGINE / "config.py"
OUTPUT_PY = _ENGINE / "output.py"
CLI_PY = _ENGINE / "cli.py"
WIRE_PY = _ENGINE / "wire.py"
CAP_CONTRACT = Path(__file__).resolve().parents[1] / "docs" / "cap-contract.md"
DEFAULT_BATCH_LINES = 1000
DEFAULT_BATCH_BYTES = 1_500_000
LOAD_PROBE_NODES = 3000
FAT_PROBE_NODES = 3000
FAT_TEXT_NODES = 1500
FULLDOC_NODES = 3000
FULLDOC_FAT = 1500
FULLDOC_EDGES = 4500
FULLDOC_EDGE_TYPES = ("inSection", "cites", "refersTo")
HUB_SEC = "SEC_0001"
E16_P95_BAR_MS = 300.0

# Needles that must remain in docs/cap-contract.md on 0.19.18.
CAP_CONTRACT_NEEDLES = (
    "CLI / serve",
    r"@ERR: {code}\|{message}",
    "exit_code`, `stdout`, `stderr`, `session_id`, `errors`",
    r"@ERR: ingest_budget\|pin budget exceeded (max_nodes={N})",
    "@ERR: limit_exceeded|rows",
    "## Truncation truncated=true M={max_rows} omitted={n} reason=max_rows",
    "snap_missing",
    "snap_available",
    r"@ERR: acl_who\|",
    r"@ERR: acl_denied\|",
    r"@ERR: acl_scope\|",
    "MEMNET_MAX_SESSIONS",
    "1024",
    "MEMNET_SESSION_TTL_MINUTES",
    "MEMNET_SAVE_ON_EXPIRE",
    "MEMNET_SERVE_INTERNAL=1",
    "DEFAULT_QUERY_MAX_ROWS",
    "MEMNET_MAX_FIELDS",
    "Never treat a clipped read as complete",
)

PROP32 = ["id"] + [f"p{i:02d}" for i in range(31)]
assert len(PROP32) == 32


def redact(text: str | None) -> str:
    return SID_RE.sub("<session>", text or "")


def assert_sid_free(*parts: str) -> None:
    blob = "\n".join(parts)
    if SID_RE.search(blob) or "mn_" in blob:
        raise AssertionError("session id leaked")


def redact_obj(obj: Any) -> Any:
    return json.loads(redact(json.dumps(obj)))


def gql_str(value: str) -> str:
    escaped = (
        value.replace("\\", "\\\\")
        .replace("'", "\\'")
        .replace("\n", "\\n")
        .replace("\r", "\\r")
        .replace("\t", "\\t")
    )
    return f"'{escaped}'"


def err_lines(stderr: str) -> list[str]:
    return [ln for ln in redact(stderr).splitlines() if ln.startswith("@ERR:")]


def stat_lines(text: str) -> list[str]:
    return [ln for ln in redact(text).splitlines() if ln.startswith("@STAT:")]


def wrn_lines(text: str) -> list[str]:
    return [ln for ln in redact(text).splitlines() if ln.startswith("@WRN:")]


def parse_session_stat(stdout: str) -> tuple[int, int] | None:
    for line in stdout.splitlines():
        if line.startswith("@STAT: sessions|"):
            body = line.split("|", 2)
            if len(body) >= 2 and "/" in body[1]:
                n_s, max_s = body[1].split("/", 1)
                return int(n_s), int(max_s)
    return None


def extract_sid(stdout: str) -> str:
    for line in stdout.splitlines():
        if line.startswith("@SESSION:"):
            return line.split("|", 1)[0].replace("@SESSION:", "").strip()
    raise RuntimeError("no session in reply")


def rss_bytes(pid: int) -> int | None:
    try:
        with open(f"/proc/{pid}/statm", encoding="ascii") as fh:
            pages = int(fh.read().split()[1])
        return pages * int(os.sysconf("SC_PAGE_SIZE"))
    except (OSError, IndexError, ValueError):
        return None


def free_port() -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.bind(("127.0.0.1", 0))
        return int(sock.getsockname()[1])


def schema_prop32() -> str:
    fields = " ".join(PROP32)
    return f"SCHEMA PRT ; fields={fields}\nSCHEMA TSK ; fields=id goal status recycle\n"


def canonical_snapshot(text: str) -> str:
    """Sid-free snapshot body: map + relations + records; drop @SNAP meta."""
    lines: list[str] = []
    skip_snap = False
    for raw in text.splitlines():
        line = raw.rstrip("\n")
        if line.startswith("@SNAP:"):
            skip_snap = True
            lines.append("@SNAP: <meta>")
            continue
        if skip_snap:
            skip_snap = False
        lines.append(redact(line))
    body = "\n".join(lines).strip() + "\n"
    assert_sid_free(body)
    return body


def snapshot_write_once_report() -> dict[str, Any]:
    """What exists today. Do not invent write-once in the engine."""
    src = SNAPSHOT_PY.read_text(encoding="utf-8")
    return {
        "write_snapshot_uses_path_write_text": "Path(path).write_text(" in src,
        "engine_o_excl": "O_EXCL" in src,
        "engine_chmod": "chmod" in src,
        "engine_immutable_flag": "immutable" in src.lower() or "chattr" in src,
        "caller_or_filesystem_only": True,
    }


def sec_create(i: int, *, status: str = "active") -> str:
    nid = f"SEC_{i:04d}"
    return (
        "CREATE (:SEC {"
        f"id: {gql_str(nid)}, art: 'ART_doc', heading: {gql_str(f'Part {i}')}, "
        f"numbering: {gql_str(str(i))}, parent: '', order: {gql_str(str(i))}, "
        f"status: {gql_str(status)}, recycle: ''"
        "})"
    )


def populate_batches(
    n_parts: int,
    *,
    text_nodes: int = 8,
    edges: int = 40,
    batch_lines: int = 900,
) -> list[str]:
    """Synthetic document graph: one ART, n SEC parts, USR text, contains edges."""
    lines: list[str] = [
        (
            "CREATE (:ART {id: 'ART_doc', title: 'Synthetic manual', "
            "source: 'synthetic.txt', kind: 'instrument_manual', "
            "status: 'active', recycle: ''})"
        )
    ]
    for i in range(1, n_parts + 1):
        lines.append(sec_create(i))
    sample = "unicode 测例 Ω | pipe and quotes \"double\" and 'single'"
    for t in range(text_nodes):
        lines.append(
            "CREATE (:USR {"
            f"id: {gql_str(f'USR_txt{t:02d}')}, key: {gql_str(f'blob{t}')}, "
            f"value: {gql_str(sample if t == 0 else f'text-{t}')}, recycle: ''"
            "})"
        )
    n_edges = min(edges, n_parts)
    for i in range(1, n_edges + 1):
        lines.append(
            f"MATCH (a {{id: 'ART_doc'}}), (b {{id: 'SEC_{i:04d}'}})\n"
            f"CREATE (a)-[:contains {{id: 'E_c{i:04d}'}}]->(b)"
        )
    batches: list[str] = []
    cur: list[str] = []
    cur_n = 0
    for stmt in lines:
        n = stmt.count("\n") + 1
        if cur and cur_n + n > batch_lines:
            batches.append("\n".join(cur) + "\n")
            cur = []
            cur_n = 0
        cur.append(stmt)
        cur_n += n
    if cur:
        batches.append("\n".join(cur) + "\n")
    return batches


def pack_batches(
    stmts: list[str],
    *,
    batch_lines: int = DEFAULT_BATCH_LINES,
    batch_bytes: int = DEFAULT_BATCH_BYTES,
) -> list[str]:
    """Split GQL statements so each mutate stdin stays under line and byte caps."""
    batches: list[str] = []
    cur: list[str] = []
    cur_n = 0
    cur_b = 0
    for stmt in stmts:
        n = stmt.count("\n") + 1
        b = len(stmt.encode("utf-8")) + 1
        if cur and (cur_n + n > batch_lines or cur_b + b > batch_bytes):
            batches.append("\n".join(cur) + "\n")
            cur = []
            cur_n = 0
            cur_b = 0
        cur.append(stmt)
        cur_n += n
        cur_b += b
    if cur:
        batches.append("\n".join(cur) + "\n")
    return batches


def populate_node_batches(
    n: int,
    *,
    batch_lines: int = DEFAULT_BATCH_LINES,
    batch_bytes: int = DEFAULT_BATCH_BYTES,
) -> list[str]:
    """n SEC nodes, no edges. Mutate batches stay at or under 1000 lines."""
    return pack_batches(
        [sec_create(i) for i in range(1, n + 1)],
        batch_lines=batch_lines,
        batch_bytes=batch_bytes,
    )


def fat_payload_bytes(index: int) -> int:
    """2 KiB, 3 KiB, or 4 KiB of UTF-8 (cycle)."""
    return 2048 + (index % 3) * 1024


def make_fat_blob(nbytes: int) -> str:
    """Single-line opaque text of exactly nbytes UTF-8 (CJK prefix, ASCII pad)."""
    prefix = "测例"
    prefix_b = prefix.encode("utf-8")
    if nbytes < len(prefix_b):
        return "A" * nbytes
    return prefix + ("B" * (nbytes - len(prefix_b)))


def populate_fat_batches(
    n_nodes: int = FAT_PROBE_NODES,
    n_fat: int = FAT_TEXT_NODES,
    *,
    batch_lines: int = DEFAULT_BATCH_LINES,
    batch_bytes: int = DEFAULT_BATCH_BYTES,
) -> list[str]:
    """n_nodes nodes, no edges; n_fat USR rows carry 2–4 KiB value text."""
    thin = n_nodes - n_fat
    stmts: list[str] = [sec_create(i) for i in range(1, thin + 1)]
    for j in range(n_fat):
        blob = make_fat_blob(fat_payload_bytes(j))
        stmts.append(
            "CREATE (:USR {"
            f"id: {gql_str(f'USR_fat{j:04d}')}, key: {gql_str(f'fat{j}')}, "
            f"value: {gql_str(blob)}, recycle: ''"
            "})"
        )
    return pack_batches(stmts, batch_lines=batch_lines, batch_bytes=batch_bytes)


def edge_create(rel: str, eid: str, src: str, dst: str) -> str:
    """One-line MATCH…CREATE so each edge is one mutate stdin line."""
    return (
        f"MATCH (a {{id: {gql_str(src)}}}), (b {{id: {gql_str(dst)}}}) "
        f"CREATE (a)-[:{rel} {{id: {gql_str(eid)}}}]->(b)"
    )


def edge_delete(eid: str) -> str:
    """Product edge DROP that actually reaches EdgeRec on 0.19.18.

    Documented ``MATCH ()-[r {id}]-() DELETE r`` lowers as a node DROP with an
    empty id and refuses ``@ERR: not_found|DELETE matched no element``. A node
    WHERE filter makes ``_parse_node_patterns`` fail, so lowering takes the
    relationship-DELETE path. GraphGlot still accepts this form.
    """
    return f"MATCH (n WHERE true)-[r {{id: {gql_str(eid)}}}]->() DELETE r"


def fulldoc_edge_stmts(
    *,
    n_thin: int = FULLDOC_NODES - FULLDOC_FAT,
    n_fat: int = FULLDOC_FAT,
) -> list[str]:
    """4500 edges: inSection (hub), cites (SEC chain), refersTo (USR→SEC)."""
    stmts: list[str] = []
    for j in range(n_fat):
        stmts.append(edge_create("inSection", f"E_ins{j:04d}", f"USR_fat{j:04d}", HUB_SEC))
    for i in range(1, n_thin + 1):
        dst = (i % n_thin) + 1
        stmts.append(edge_create("cites", f"E_cit{i:04d}", f"SEC_{i:04d}", f"SEC_{dst:04d}"))
    for j in range(n_fat):
        dst = (j % n_thin) + 1
        stmts.append(
            edge_create(
                "refersTo",
                f"E_ref{j:04d}",
                f"USR_fat{j:04d}",
                f"SEC_{dst:04d}",
            )
        )
    return stmts


def populate_fulldoc_batches(
    n_nodes: int = FULLDOC_NODES,
    n_fat: int = FULLDOC_FAT,
    *,
    batch_lines: int = DEFAULT_BATCH_LINES,
    batch_bytes: int = DEFAULT_BATCH_BYTES,
    nodes_only: bool = False,
    max_edges: int | None = None,
) -> list[str]:
    """Fulldoc with edges: n_nodes (n_fat with 2–4 KiB text) + ~4500 typed edges.

    Order lives on SEC.order, not on an edge. Batches stay at or under 1000 lines.
    """
    node_batches = populate_fat_batches(
        n_nodes, n_fat, batch_lines=batch_lines, batch_bytes=batch_bytes
    )
    if nodes_only:
        return node_batches
    n_thin = n_nodes - n_fat
    edges = fulldoc_edge_stmts(n_thin=n_thin, n_fat=n_fat)
    if max_edges is not None:
        edges = edges[:max_edges]
    return node_batches + pack_batches(edges, batch_lines=batch_lines, batch_bytes=batch_bytes)


def percentile_ms(samples_s: list[float], p: float) -> float | None:
    if not samples_s:
        return None
    ordered = sorted(samples_s)
    rank = int((p / 100.0) * (len(ordered) - 1))
    return round(ordered[rank] * 1000.0, 3)


def latency_summary(samples_s: list[float]) -> dict[str, Any]:
    if not samples_s:
        return {"n": 0, "p50_ms": None, "p95_ms": None, "max_ms": None}
    return {
        "n": len(samples_s),
        "p50_ms": percentile_ms(samples_s, 50),
        "p95_ms": percentile_ms(samples_s, 95),
        "max_ms": round(max(samples_s) * 1000.0, 3),
        "mean_ms": round(1000.0 * sum(samples_s) / len(samples_s), 3),
    }


def cpu_model() -> str:
    try:
        text = Path("/proc/cpuinfo").read_text(encoding="utf-8")
    except OSError:
        return "unknown"
    for line in text.splitlines():
        if line.lower().startswith("model name"):
            return line.split(":", 1)[1].strip()
    return "unknown"


def make_special_blob(target_bytes: int, *, newlines: bool, pipes: bool) -> str:
    """UTF-8 blob of target_bytes with LaTeX / quotes / CJK; optional newline and |."""
    core = r"LaTeX $\frac{a}{b}$ braces {x_y} quotes \"double\" and 'single' 测例 Ω"
    if pipes:
        core += " | pipe"
    if newlines:
        core = "line1\n" + core + "\nline3"
    raw = core.encode("utf-8")
    if len(raw) > target_bytes:
        cut = core
        while len(cut.encode("utf-8")) > target_bytes:
            cut = cut[:-1]
        return cut
    return core + ("A" * (target_bytes - len(raw)))


def parse_stat_int(text: str, key: str) -> int | None:
    prefix = f"@STAT: {key}|"
    for line in text.splitlines():
        if line.startswith(prefix):
            body = line.split("|", 2)
            if len(body) >= 2:
                try:
                    return int(body[1])
                except ValueError:
                    return None
    return None


def shaped_node_props(stdout: str) -> dict[str, Any] | None:
    """First shaped (:Kind {…}) property map from pin_map / find emit."""
    from memnet.gql import parse_props

    for line in stdout.splitlines():
        s = line.strip()
        if not s.startswith("(:"):
            continue
        brace = s.find("{")
        end = s.rfind("}")
        if brace < 0 or end <= brace:
            continue
        return parse_props(s[brace : end + 1])
    return None


def snapshot_load_cap_report() -> dict[str, Any]:
    """What session_load is bound by. Do not change the engine."""
    snap = SNAPSHOT_PY.read_text(encoding="utf-8")
    ingest = PIN_MAP_INGEST_PY.read_text(encoding="utf-8")
    store = MEM_STORE_PY.read_text(encoding="utf-8")
    load_fn = "def load_snapshot_text"
    load_body = snap[snap.find(load_fn) : snap.find("\ndef ", snap.find(load_fn) + 1)]
    return {
        "load_calls_parse_line": "parse_line(" in load_body,
        "load_calls_upsert": "store.upsert(" in load_body,
        "load_mentions_ingest_budget": "ingest_budget" in snap,
        "ingest_budget_in_pin_map_ingest": "ingest_budget" in ingest,
        "upsert_checks_row_count_non_law": "row_count_non_law()" in store
        and "limit_exceeded" in store,
        "code_path": (
            "cli.session_load -> snapshot.load_snapshot -> load_snapshot_text "
            "(parse_line + MemStore.upsert). ingest_budget is Path-B only "
            "(pin_map_ingest / catalog_snap), not this path."
        ),
    }


def max_rows_count_report() -> dict[str, Any]:
    """MEMNET_MAX_ROWS counts every non-LAW tag, including EDG."""
    store = MEM_STORE_PY.read_text(encoding="utf-8")
    cfg = CONFIG_PY.read_text(encoding="utf-8")
    return {
        "default_env": "MEMNET_MAX_ROWS",
        "default_value": 5000,
        "config_default_5000": 'self.max_rows = _env_int("MEMNET_MAX_ROWS", 5000)' in cfg,
        "row_count_sums_non_law_tags": (
            'return sum(len(s) for t, s in self._by_tag.items() if t != "LAW")' in store
        ),
        "upsert_edg_counts": (
            'elif record.tag != "LAW" and not existing:' in store and "row_count_non_law()" in store
        ),
        "counts_nodes_plus_edges": True,
    }


def snapshot_value_cap_report() -> dict[str, Any]:
    """value_bytes is on the decoded field; line_bytes is the raw snapshot line."""
    tag = TAG_MAP_PY.read_text(encoding="utf-8")
    wire = WIRE_PY.read_text(encoding="utf-8")
    cfg = CONFIG_PY.read_text(encoding="utf-8")
    snap = SNAPSHOT_PY.read_text(encoding="utf-8")
    out_src = OUTPUT_PY.read_text(encoding="utf-8")
    join_at = wire.find("def join_payload")
    join_end = wire.find("\ndef ", join_at + 1)
    join_src = wire[join_at:join_end] if join_at >= 0 else ""
    val_at = tag.find("def validate_values")
    val_end = tag.find("\ndef ", val_at + 1)
    val_src = tag[val_at:val_end] if val_at >= 0 else ""
    parse_at = tag.find("def parse_line")
    parse_end = tag.find("\ndef ", parse_at + 1)
    parse_src = tag[parse_at:parse_end] if parse_at >= 0 else ""
    return {
        "value_bytes_default": 4096,
        "line_bytes_default": 32768,
        "max_fields_default": 32,
        "value_bytes_on_decoded_field": "len(val.encode(" in val_src
        and "max_value_bytes" in val_src
        and ">" in val_src,
        "value_bytes_gt_not_ge": 'len(val.encode("utf-8")) > caps.max_value_bytes' in val_src,
        "decoded_after_split_payload": (
            "values = split_payload(payload)" in parse_src and "validate_values(" in parse_src
        ),
        "line_bytes_on_raw_snapshot_line": "max_line_bytes" in parse_src
        and "len(line.encode(" in parse_src,
        "join_escapes_backslash_and_pipe": (
            "def join_payload" in join_src
            and 'replace("\\\\"' in join_src
            and 'replace("|",' in join_src
        ),
        "split_unescapes_before_validate": "split_payload(payload)" in parse_src,
        "cr_or_nl_is_newline_in_value": '"\\n" in val or "\\r" in val' in val_src,
        "tab_not_in_newline_check": '"\\t" in val' not in val_src,
        "max_fields_on_schema_register": "len(field_names) > caps.max_fields" in tag,
        "emit_record_schema_columns_only": "values = [record.fields.get(f, " in out_src,
        "save_write_text_no_value_check": "Path(path).write_text" in snap,
        "config_value": '_env_int("MEMNET_MAX_VALUE_BYTES", 4096)' in cfg,
        "config_line": '_env_int("MEMNET_MAX_LINE_BYTES", 32768)' in cfg,
        "config_fields": '_env_int("MEMNET_MAX_FIELDS", 32)' in cfg,
        "code_path": (
            "session_save -> snapshot_text -> emit_record -> join_payload "
            "(escapes \\\\ and | only). session_load -> parse_line: raw line "
            "vs max_line_bytes, then split_payload unescape, then "
            "validate_values decoded utf-8 vs max_value_bytes (`>` not `>=`); "
            "CR/LF -> newline_in_value. SCHEMA register vs max_fields."
        ),
    }


E18_HAN = "测"
E18_HAN_ORD = 0x6D4B
E18_RT_KEEP = (
    "nid",
    "kind",
    "chars",
    "utf8",
    "escaped_field_utf8",
    "uniq_ord",
    "open_exit",
    "open_err",
    "create_exit",
    "save_exit",
    "load_exit",
    "exact",
    "ram_exact",
    "fields_exact",
    "ram_utf8",
    "loaded_utf8",
    "create_err",
    "save_err",
    "load_err",
    "snap_line_utf8",
    "loaded_key_n",
    "ram_key_n",
    "wire_shape",
)


def e18_cjk_blob(nbytes: int, *, han: str = E18_HAN) -> str:
    """nbytes UTF-8 from 3-byte CJK plus ASCII pad."""
    hb = han.encode("utf-8")
    if len(hb) != 3:
        raise ValueError("han must be 3-byte UTF-8")
    n_han, rem = divmod(nbytes, 3)
    return han * n_han + ("X" * rem)


def e18_cjk_composition(nbytes: int, *, han: str = E18_HAN) -> str:
    hb = han.encode("utf-8")
    n_han, rem = divmod(nbytes, 3)
    pad = f" + {rem} ASCII X" if rem else ""
    return f"{n_han} × U+{ord(han):04X} ({han}, {len(hb)}-byte UTF-8){pad}"


def e18_blob_meta(blob: str) -> dict[str, Any]:
    from memnet.wire import join_payload

    raw = blob.encode("utf-8")
    return {
        "chars": len(blob),
        "utf8": len(raw),
        "escaped_field_utf8": len(join_payload([blob]).encode("utf-8")),
        "uniq_ord": sorted({ord(c) for c in blob})[:8],
    }


def e18_wire_shape(stmt: str, replacements: list[str]) -> str:
    out = stmt.strip()
    for blob in replacements:
        if not blob:
            continue
        token = f"<blob utf8={len(blob.encode('utf-8'))} chars={len(blob)}>"
        g = gql_str(blob)
        if g in out:
            out = out.replace(g, token)
        elif len(blob) >= 16 and blob in out:
            out = out.replace(blob, token)
    if len(out) > 240:
        return out[:120] + f"…({len(out)} chars)"
    return out


def e18_usr_create(nid: str, blob: str, *, extra: dict[str, str] | None = None) -> str:
    bits = [
        f"id: {gql_str(nid)}",
        "key: 'e18'",
        f"value: {gql_str(blob)}",
        "recycle: ''",
    ]
    for k, v in (extra or {}).items():
        bits.append(f"{k}: {gql_str(v)}")
    return "CREATE (:USR {" + ", ".join(bits) + "})"


def e18_schema_fields(n: int, *, tag: str = "WIDE") -> list[str]:
    names = ["id"] + [f"p{i:03d}" for i in range(n - 1)]
    return [f"SCHEMA {tag} ; fields={' '.join(names)}"]


def e18_fat_schema(n_props: int = 8, *, tag: str = "FAT") -> list[str]:
    names = ["id"] + [f"p{i:03d}" for i in range(n_props)]
    return [f"SCHEMA {tag} ; fields={' '.join(names)}"]


def e18_fat_create(nid: str, blobs: dict[str, str], *, tag: str = "FAT") -> str:
    bits = [f"id: {gql_str(nid)}"]
    for k, v in blobs.items():
        bits.append(f"{k}: {gql_str(v)}")
    return f"CREATE (:{tag} {{" + ", ".join(bits) + "})"


def e18_public_rt(row: dict[str, Any]) -> dict[str, Any]:
    return {k: row[k] for k in E18_RT_KEEP if k in row}


def _e18_snap_line_bytes(snap: Path, nid: str, kind: str) -> int | None:
    if not snap.is_file():
        return None
    needle = nid.encode("utf-8")
    prefix = f"@{kind}:".encode("ascii")
    for ln in snap.read_bytes().split(b"\n"):
        if ln.startswith(prefix) and needle in ln[:120]:
            return len(ln)
    return None


def e18_roundtrip(
    svc: ServeProc,
    tmp: Path,
    *,
    blob: str,
    nid: str,
    kind: str = "USR",
    value_key: str = "value",
    map_lines: list[str] | None = None,
    extra_props: dict[str, str] | None = None,
    create_stmt: str | None = None,
    expect: dict[str, str] | None = None,
) -> dict[str, Any]:
    """CREATE via mutate, save, load into a new session, compare value bytes."""
    snap = tmp / f"{nid}.snap"
    wanted = dict(expect or {})
    wanted.setdefault(value_key, blob)
    stmt = create_stmt or e18_usr_create(nid, blob, extra=extra_props)
    out: dict[str, Any] = {
        "nid": nid,
        "kind": kind,
        "value_key": value_key,
        **e18_blob_meta(blob),
        "wire_shape": e18_wire_shape(stmt, [blob, *wanted.values()]),
        "create_exit": None,
        "save_exit": None,
        "load_exit": None,
        "exact": False,
        "ram_utf8": None,
        "loaded_utf8": None,
        "create_err": [],
        "save_err": [],
        "load_err": [],
        "snap_line_utf8": None,
    }
    sid, open_r = svc.try_open_session(map_lines=map_lines)
    out["open_exit"] = open_r.exit_code
    out["open_err"] = err_lines(open_r.stderr)
    if sid is None:
        return out
    created = svc.mutate(sid, stmt if stmt.endswith("\n") else stmt + "\n")
    out["create_exit"] = created.exit_code
    out["create_err"] = err_lines(created.stderr)
    ram_props: dict[str, Any] = {}
    if created.exit_code == 0:
        ram_props = shaped_node_props(svc.pin_map(sid, cue=nid).stdout) or {}
        ram = ram_props.get(value_key)
        out["ram_utf8"] = len(ram.encode("utf-8")) if isinstance(ram, str) else None
        out["ram_exact"] = ram == blob
        out["ram_key_n"] = len(ram_props)
        out["ram_has_extras"] = any(str(k).startswith("x") for k in ram_props)
    saved = svc.save(sid, snap)
    out["save_exit"] = saved.exit_code
    out["save_err"] = err_lines(saved.stderr)
    out["snap_line_utf8"] = _e18_snap_line_bytes(snap, nid, kind)
    svc.close(sid)
    if saved.exit_code != 0:
        return out
    loaded = svc.load_file(snap)
    out["load_exit"] = loaded.exit_code
    out["load_err"] = err_lines(loaded.stderr)
    if loaded.exit_code != 0:
        return out
    new = None
    for line in loaded.stdout.splitlines():
        if line.startswith("@SESSION:"):
            new = line.split("|", 1)[0].replace("@SESSION:", "").strip()
            break
    if not new:
        return out
    props2 = shaped_node_props(svc.pin_map(new, cue=nid).stdout) or {}
    got = props2.get(value_key)
    out["loaded_utf8"] = len(got.encode("utf-8")) if isinstance(got, str) else None
    field_ok = {k: props2.get(k) == v for k, v in wanted.items()}
    out["fields_exact"] = field_ok
    out["exact"] = bool(field_ok) and all(field_ok.values())
    out["loaded_keys"] = sorted(props2)
    out["loaded_key_n"] = len(props2)
    out["loaded_has_extras"] = any(str(k).startswith("x") for k in props2)
    svc.close(new)
    return out


def e18_largest_roundtrip(
    svc: ServeProc,
    tmp: Path,
    *,
    fill: str,
    hi: int,
    prefix: str,
) -> dict[str, Any]:
    """Binary search largest raw byte size of `fill` that save/load round-trips."""
    lo = 0
    best = 0
    last: dict[str, Any] = {}
    while lo <= hi:
        mid = (lo + hi) // 2
        blob = fill * mid
        row = e18_roundtrip(svc, tmp, blob=blob, nid=f"{prefix}{mid}")
        last = e18_public_rt(row)
        if row.get("exact"):
            best = mid
            lo = mid + 1
        else:
            hi = mid - 1
    return {"largest_raw": best, "last": last}


def e18_instance_width(svc: ServeProc, tmp: Path, n_props: int) -> dict[str, Any]:
    """n_props keys on 4-field USR SCHEMA. Extras live in RAM; save drops them."""
    nid = f"USR_w{n_props}"
    extra_n = max(0, n_props - 4)
    extras = {f"x{i:03d}": "v" for i in range(extra_n)}
    row = e18_roundtrip(
        svc,
        tmp,
        blob="w",
        nid=nid,
        extra_props=extras,
        expect={"value": "w", "key": "e18"},
    )
    public = e18_public_rt(row)
    public["n_requested"] = n_props
    public["extra_n"] = extra_n
    public["ram_has_extras"] = row.get("ram_has_extras")
    public["loaded_has_extras"] = row.get("loaded_has_extras")
    return public


def mutate_byte_cap_report() -> dict[str, Any]:
    """Pipe leftover caps vs GQL mutate (cap-contract bug 4)."""
    tag = TAG_MAP_PY.read_text(encoding="utf-8")
    gql = GQL_PY.read_text(encoding="utf-8")
    cfg = CONFIG_PY.read_text(encoding="utf-8")
    cli = CLI_PY.read_text(encoding="utf-8")
    out = OUTPUT_PY.read_text(encoding="utf-8")
    composer = PIN_MAP_COMPOSER_PY.read_text(encoding="utf-8")
    return {
        "gql_escapes": r"""\\ \' \" \n \r \t""",
        "gql_unknown_escape": "unknown string escape" in gql,
        "pipe_value_bytes_default": 4096,
        "pipe_line_bytes_default": 32768,
        "pipe_batch_lines_default": 1000,
        "pipe_value_code": "limit_exceeded|value_bytes {n}/{max} (inner | -> space on wire)",
        "pipe_line_code": "limit_exceeded|line_bytes {n}/{max}",
        "pipe_newline_code": "newline_in_value",
        "pipe_field_count_code": "FIELD_COUNT",
        "pipe_enforces_in_parse_line": "max_value_bytes" in tag and "max_line_bytes" in tag,
        "gql_mutate_checks_value_bytes": "max_value_bytes" in gql,
        "gql_mutate_checks_line_bytes": "max_line_bytes" in gql,
        "cli_batch_lines": "max_batch_lines" in cli and "batch_lines|" in cli,
        "wire_pipes_become_spaces": 'message.replace("|", " ")' in out,
        "locator_equality_only": 'if str(rec.fields.get(key, "")) != val:' in composer,
        "keyword_is_casefold_substring": (
            "return any(needle in str(v).lower() for v in rec.fields.values())" in composer
        ),
        "config_value_bytes": '_env_int("MEMNET_MAX_VALUE_BYTES", 4096)' in cfg,
        "config_line_bytes": '_env_int("MEMNET_MAX_LINE_BYTES", 32768)' in cfg,
        "bug4_gql_skips_pipe_caps": True,
    }


def citekeys_schema() -> str:
    return (
        "SCHEMA USR ; fields=id key value citeKeys recycle\n"
        "SCHEMA SEC ; fields=id art heading numbering parent order status recycle\n"
        "SCHEMA TSK ; fields=id goal status recycle\n"
        "SCHEMA ART ; fields=id title source kind status recycle\n"
    )


@dataclass
class ServeReply:
    exit_code: int
    stdout: str
    stderr: str
    keys: tuple[str, ...]
    request: dict[str, Any]

    @property
    def errors(self) -> list[str]:
        return err_lines(self.stderr)


@dataclass
class ServeProc:
    host: str
    port: int
    pid: int
    proc: subprocess.Popen[str]
    snap_dir: Path
    map_file: Path
    timeout_s: float = 180.0

    def send(
        self,
        args: list[str],
        *,
        stdin: str | None = None,
        admin_token: str | None = None,
        admin_usage: bool = False,
        timeout: float | None = None,
    ) -> ServeReply:
        payload: dict[str, Any] = {"args": args}
        if stdin is not None:
            payload["stdin"] = stdin
        if admin_token is not None:
            payload["admin_token"] = admin_token
        if admin_usage:
            payload["admin_usage"] = True
        raw = send_command(
            args,
            stdin=stdin,
            host=self.host,
            port=self.port,
            admin_token=admin_token,
            admin_usage=admin_usage,
            timeout=self.timeout_s if timeout is None else timeout,
        )
        return ServeReply(
            exit_code=int(raw.get("exit_code") or 0),
            stdout=raw.get("stdout") or "",
            stderr=raw.get("stderr") or "",
            keys=tuple(sorted(raw.keys())),
            request=payload,
        )

    def open_session(
        self,
        *,
        map_file: Path | None = None,
        ttl: int | None = None,
        product: str | None = None,
        map_lines: list[str] | None = None,
    ) -> str:
        args = ["session", "open"]
        if map_lines:
            for line in map_lines:
                args.extend(["--map", line])
        else:
            args.extend(["--map-file", str(map_file or self.map_file)])
        if ttl is not None:
            args.extend(["--ttl", str(ttl)])
        if product:
            args.extend(["--product", product])
        reply = self.send(args)
        if reply.exit_code != 0:
            raise RuntimeError(redact(reply.stderr) or "session open failed")
        return extract_sid(reply.stdout)

    def try_open_session(self, **kwargs: Any) -> tuple[str | None, ServeReply]:
        args = ["session", "open"]
        map_lines = kwargs.get("map_lines")
        map_file = kwargs.get("map_file")
        if map_lines:
            for line in map_lines:
                args.extend(["--map", line])
        else:
            args.extend(["--map-file", str(map_file or self.map_file)])
        if kwargs.get("ttl") is not None:
            args.extend(["--ttl", str(kwargs["ttl"])])
        if kwargs.get("product"):
            args.extend(["--product", str(kwargs["product"])])
        reply = self.send(args)
        if reply.exit_code != 0:
            return None, reply
        return extract_sid(reply.stdout), reply

    def close(self, sid: str) -> ServeReply:
        return self.send(["session", "close", sid])

    def live_count(self) -> tuple[int, int]:
        reply = self.send(["session", "list"])
        parsed = parse_session_stat(reply.stdout)
        if parsed is None:
            raise RuntimeError("no @STAT: sessions on list")
        return parsed

    def mutate(
        self,
        sid: str,
        gql: str,
        *,
        caller: str | None = None,
        allow_new_relation: bool = False,
    ) -> ServeReply:
        args = ["mutate", "--stdin", "--session", sid]
        if allow_new_relation:
            args.append("--allow-new-relation")
        if caller:
            args.extend(["--caller", caller])
        return self.send(args, stdin=gql if gql.endswith("\n") else gql + "\n")

    def populate(self, sid: str, n_parts: int, **kwargs: Any) -> list[ServeReply]:
        return self.populate_stmts(sid, populate_batches(n_parts, **kwargs))

    def populate_stmts(
        self,
        sid: str,
        batches: list[str],
        *,
        allow_new_relation: bool = False,
    ) -> list[ServeReply]:
        out: list[ServeReply] = []
        for batch in batches:
            reply = self.mutate(sid, batch, allow_new_relation=allow_new_relation)
            out.append(reply)
            if reply.exit_code != 0:
                break
        return out

    def pin_map(
        self,
        sid: str,
        *,
        cue: str | None = None,
        kind: str | None = None,
        depth: int | None = None,
        max_rows: int | None = None,
        caller: str | None = None,
        locator: str | None = None,
        keyword: str | None = None,
    ) -> ServeReply:
        args = ["query", "pin-map", "--session", sid]
        if cue:
            args.extend(["--cue", cue])
        if kind:
            args.extend(["--kind", kind])
        if locator:
            args.extend(["--locator", locator])
        if keyword:
            args.extend(["--keyword", keyword])
        if depth is not None:
            args.extend(["--depth", str(depth)])
        if max_rows is not None:
            args.extend(["--max-rows", str(max_rows)])
        if caller:
            args.extend(["--caller", caller])
        try:
            return self.send(args)
        except (ConnectionError, OSError, TimeoutError) as exc:
            # Hub neighbourhood of fat USR values can exceed the 4 MiB serve frame.
            return ServeReply(
                exit_code=2,
                stdout="",
                stderr=f"@ERR: probe_client|{type(exc).__name__} {redact(str(exc))}\n",
                keys=(),
                request={"args": args, "stdin": None},
            )

    def find(
        self,
        sid: str,
        *,
        kind: str | None = None,
        locator: str | None = None,
        keyword: str | None = None,
        limit: int = 50,
    ) -> ServeReply:
        args = ["query", "find", "--session", sid, "--limit", str(limit)]
        if kind:
            args.extend(["--kind", kind])
        if locator:
            args.extend(["--locator", locator])
        if keyword:
            args.extend(["--keyword", keyword])
        return self.send(args)

    def read_list(
        self,
        sid: str,
        *,
        tag: str | None = None,
        where: str | None = None,
    ) -> ServeReply:
        args = ["read", "list", "--session", sid]
        if tag:
            args.extend(["--tag", tag])
        if where:
            args.extend(["--where", where])
        return self.send(args)

    def housekeep_stats(self, sid: str, *, caller: str | None = None) -> ServeReply:
        args = ["housekeep", "stats", "--session", sid]
        if caller:
            args.extend(["--caller", caller])
        return self.send(args)

    def expire_status(self) -> ServeReply:
        return self.send(["session", "expire-status"])

    def save(self, sid: str, path: Path, *, caller: str | None = None) -> ServeReply:
        args = ["session", "save", "--file", str(path), "--session", sid]
        if caller:
            args.extend(["--caller", caller])
        return self.send(args)

    def load_file(self, path: Path, *, caller: str | None = None) -> ServeReply:
        args = ["session", "load", "--file", str(path)]
        if caller:
            args.extend(["--caller", caller])
        return self.send(args)

    def load_sid(self, sid: str, *, caller: str | None = None) -> ServeReply:
        args = ["session", "load", "--session", sid]
        if caller:
            args.extend(["--caller", caller])
        return self.send(args)

    def export_pin_map(
        self,
        sid: str,
        *,
        cue: str | None = None,
        caller: str | None = None,
    ) -> ServeReply:
        args = ["export", "pin-map", "--session", sid]
        if cue:
            args.extend(["--cue", cue])
        if caller:
            args.extend(["--caller", caller])
        return self.send(args)

    def grant(self, sid: str, caller: str, *, write_scope: str | None = None) -> ServeReply:
        args = ["session", "acl-grant", "--caller", caller, "--session", sid]
        if write_scope:
            args.extend(["--write-scope", write_scope])
        return self.send(args)

    def acl_bind(self, sid: str, mission_id: str, lease: str) -> ServeReply:
        return self.send(
            [
                "session",
                "acl-bind",
                "--mission-id",
                mission_id,
                "--lease",
                lease,
                "--session",
                sid,
            ]
        )

    def snap_count(self) -> int:
        return len(list(self.snap_dir.glob("*.snap")))

    def usage_report(self) -> ServeReply:
        return self.send(
            ["admin", "usage-report"],
            admin_token=ADMIN_TOKEN,
            admin_usage=True,
        )

    def rss(self) -> int | None:
        return rss_bytes(self.pid)

    def stop(self) -> None:
        if self.proc.poll() is None:
            self.proc.terminate()
            try:
                self.proc.wait(timeout=8)
            except subprocess.TimeoutExpired:
                self.proc.kill()
                self.proc.wait(timeout=4)


def start_serve(
    tmp: Path,
    *,
    ttl_minutes: int = 60,
    max_sessions: int = 1024,
    extra_env: dict[str, str] | None = None,
    timeout_s: float = 180.0,
) -> ServeProc:
    host = "127.0.0.1"
    port = free_port()
    snap_dir = tmp / "expire-snaps"
    snap_dir.mkdir(parents=True, exist_ok=True)
    env = os.environ.copy()
    env.pop("MEMNET_TEST_INLINE", None)
    env.pop("MEMNET_SESSION", None)
    env.pop("MEMNET_CALLER", None)
    env["MEMNET_SERVE_HOST"] = host
    env["MEMNET_SERVE_PORT"] = str(port)
    env["MEMNET_MAX_SESSIONS"] = str(max_sessions)
    env["MEMNET_SESSION_TTL_MINUTES"] = str(ttl_minutes)
    env["MEMNET_SAVE_ON_EXPIRE"] = "1"
    env["MEMNET_EXPIRE_SNAPSHOT_DIR"] = str(snap_dir)
    env["MEMNET_ADMIN_TOKEN"] = ADMIN_TOKEN
    env["PYTHONUNBUFFERED"] = "1"
    if extra_env:
        env.update(extra_env)
    proc = subprocess.Popen(
        [
            sys.executable,
            "-m",
            "memnet",
            "serve",
            "--host",
            host,
            "--port",
            str(port),
        ],
        env=env,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )
    deadline = time.time() + 10
    while time.time() < deadline:
        if proc.poll() is not None:
            err = proc.stderr.read() if proc.stderr else ""
            raise RuntimeError(f"serve exited: {redact(err)}")
        try:
            with socket.create_connection((host, port), timeout=0.2):
                break
        except OSError:
            time.sleep(0.05)
    else:
        proc.kill()
        raise RuntimeError("memnet serve did not start")
    if proc.pid is None:
        raise RuntimeError("serve pid missing")
    return ServeProc(
        host=host,
        port=port,
        pid=int(proc.pid),
        proc=proc,
        snap_dir=snap_dir,
        map_file=TECHDOCS_MAP,
        timeout_s=timeout_s,
    )


@contextmanager
def running_serve(tmp: Path, **kwargs: Any) -> Iterator[ServeProc]:
    svc = start_serve(tmp, **kwargs)
    try:
        yield svc
    finally:
        svc.stop()


@dataclass
class ItemResult:
    item: str
    verdict: str
    notes: list[str] = field(default_factory=list)
    numbers: dict[str, Any] = field(default_factory=dict)
    wires: list[str] = field(default_factory=list)
    gaps: list[str] = field(default_factory=list)

    def render(self) -> str:
        lines = [f"## {self.item}", f"verdict: {self.verdict}"]
        if self.numbers:
            lines.append("numbers: " + json.dumps(self.numbers, sort_keys=True))
        for w in self.wires:
            lines.append("wire: " + redact(w))
        for n in self.notes:
            lines.append("note: " + redact(n))
        for g in self.gaps:
            lines.append("gap: " + redact(g))
        return "\n".join(lines) + "\n"
