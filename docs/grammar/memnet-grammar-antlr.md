# MemNet grammar × ANTLR4 — coherence notes

**Status:** ANTLR codegen **cancelled**. `MemNet.g4` is quarantine-only under [`archive/antlr/MemNet.g4`](archive/antlr/MemNet.g4). Product wire is **GQL** ([`gql-wire-profile.md`](gql-wire-profile.md)). Line-dialect twin remains `memnet.tier_a` (rejected on product mutate).  
**Pair with:** `memnet-grammar-design.md`, `examples/`, `tools/`  
**Tooling pin:** `third_party/antlr4/` **4.13.2** is optional historical reference only.  
**British English.**

**Naming:** agent-facing name is **shared dialect** (Write = display). Code/harness names `tier_a` / “Tier A” denote the **same** dialect — keep them for continuity. This note preserves formal ANTLR fit, locked defaults, and golden coverage; it does not thin the grammar into slogans.

---

## Verdict

The retired line dialect was a **good fit for ANTLR4** as a line-oriented language. R1 shipped a **pure-Python twin** (`tier_a.py`) instead of generating from `.g4`. That stub was **never** compiled into the engine. **Do not** add `antlr4 -Dlanguage=Python3` as an accept path. Product teach/accept is GQL (`GqlCodec`). Legacy `@TAG` pipe is **not** preferred agent I/O.

---

## 1. Does the proposed syntax parse cleanly?

| Topic | Assessment |
|-------|------------|
| Left recursion | None. Fine for ANTLR4. |
| Ambiguity (parser) | Line forms distinguishable by first tokens (`+ KIND [id]`, `+ Eid [a] --(rel)--> [b]`, `~ Eid`, `- Eid`, `LAW…`, `SCHEMA KIND`, bare present). |
| Ambiguity (values) | **R1 locked atoms-only** — `;` joins fields only. List/map deferred to R2. |
| Lexer vs parser | One `IDENT` + `KW_NEW` + `KW_SCHEMA` + visitor/twin checks. |
| Keywords | Ops, `##` heads, mint **`KW_NEW`** (`NEW`), schema **`KW_SCHEMA`**. Kind tokens remain data. |
| `lawPin` | **`IDENT field (SEMI field)*`** — first field has **no** leading `;` (matches pin-map LAW lines). |
| `schemaDecl` | **`KW_SCHEMA IDENT (SEMI field)*`** — `fields=` space-separated names; `id` first. Session map only. |
| Edge ids | Pin map (bare present): `E77 [from] --(rel)--> [to]`. Create: `+ NEW [from] --(rel)--> [to]` or omit eid. |
| `key=value` | `IDENT ASSIGN value`. `+=` / `-=` longer match before `=`. |
| Arrows | `--(` + rel + `)-->` unambiguous. |
| STRING | Escapes `\\` `\"` `\n` `\r` `\t`; quote Windows paths. |

---

## 2. `MemNet.g4` — dropped from the live tree

| Role | Judgement |
|------|-----------|
| Product wire | **GQL** — not this `.g4`. |
| Engine parse | `memnet.tier_a` (line dialect, reject on mutate) and `memnet.gql_codec` (accept). |
| Stub | Archived; **MUST NOT** generate a visitor as a second dialect. |

---

## 3. Write = display and ANTLR

1. **Parse** recovers AST (`Node` | `Edge`).  
2. **Emit** (`tier_a.emit`) pretty-prints with the same separators.  
3. Round-trip tests: parse → emit → parse on `01_` / `04_`.  
4. MN-REQ-08.7 / 08.9 / 09.3: pin-map emit and mutate input share one grammar.

---

## 4. Python runtime fit

| Item | Note |
|------|------|
| R1 twin | `memnet.tier_a` / `docs/grammar/tools/tier_a.py` — no antlr4 dependency (**keep**) |
| Golden | `python -m pytest tests/grammar -q` (**keep**) |
| ANTLR generate | **Cancelled** — stub archived; do not codegen |
| Host | Python ≥3.11 |
| Legacy pipe | Deprecated import-once only — not in `.g4`, not preferred agent I/O |

---

## 5. Pipe is not preferred agent I/O

**Locked:** line-dialect agent I/O for those fixtures. Do not add `@` lexer modes. Bad fixtures `05_` / `09_` are **parse-reject** (pipe as agent surface) — **keep** those fixtures; they teach illegal shapes. Historical compile sketches live under `examples/deprecated/` if kept. Product mutate accept is GQL, not this dialect.

---

## 6. Pin-map / fixtures

| Need | Status |
|------|--------|
| Law pins without leading `;` | Fixed in `.g4` + twin |
| Edge ids on pin map | bare `Eid [from] --(rel)--> [to]` in `01_` / `04_` (no leading `+`) |
| Multi-word / punctuated atoms | Bare atom or `STRING` |
| focus / caps | **Envelope only** — not in body grammar or fixtures |
| Headerless mutate | Legal (`02_`, `03_`, `14_`, `15_`) |
| Pin-map sections | **Required** on agent-facing pin-map fixtures |
| SET membership | R1: expand to many EDGE lines (`member_of` / `contains`) |
| Fixture labels | `examples/README.md` — `parse-reject` vs `lint-reject` |
| Soft prose/fat lint | parse OK; harness lint-reject (`06_`, `08_`) |

---

## 7. Locked defaults

1. Agent dialect → **shared dialect only** (Write = display; aka Tier A in code names).  
2. Pipe → **deprecated import footnote**, not preferred agent I/O (keep import rules if present).  
3. `##` on pin map → **required** for agent-facing pin-map fixtures.  
4. Fat fields → **soft lint**.  
5. Compound values → **R1 atoms-only**; R2 deferred.  
6. Pin-map metadata → **envelope only**.

**Still open:** `NEW` as edge **endpoint** in the same mutate batch as node creates.

---

## 8. Engineering status

| Step | Status |
|------|--------|
| R1 value rule atoms-only | Done |
| Golden harness | Done — `tests/grammar/` (**preserve**) |
| Parse / emit twin | Done — `tier_a.py` (**preserve**) |
| Visitor from `.g4` | **Cancelled** |
| Legacy pipe compile sketch | Deprecated (`examples/deprecated/`) — retained for history |

---

## 9. Requirement hooks (thin)

| Leaf | ANTLR / twin angle |
|------|--------------------|
| MN-REQ-08.* | Product LLM-facing dialect = GQL; line twin is archive/tests only |
| MN-REQ-08.9 | Pin-map emit same grammar as mutate input |
| MN-REQ-09.1–09.2 | Canonical parse + reject invalid |
| MN-REQ-09.3–09.4 | Inspect via AST render; no ad-hoc splits |
| MN-REQ-03 / 10.4 | `KW_NEW` mint; engine-allocated ids; copy from pin map |
