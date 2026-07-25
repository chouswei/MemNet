# MemNet grammar × ANTLR4 — coherence notes

**Status:** R1 twin live (`docs/grammar/tools/tier_a.py` + package `memnet.tier_a`); `.g4` remains teaching / future codegen stub  
**Pair with:** `memnet-grammar-design.md`, `MemNet.g4`, `examples/`, `tools/`  
**Tooling pin:** `third_party/antlr4/` **4.13.2** (Python3 target docs: `doc/python-target.md`)  
**British English.**

**Naming:** agent-facing name is **shared dialect** (Write = display). Code/harness names `tier_a` / “Tier A” denote the **same** dialect — keep them for continuity. This note preserves formal ANTLR fit, locked defaults, and golden coverage; it does not thin the grammar into slogans.

---

## Verdict

The shared dialect is a **good fit for ANTLR4** as a line-oriented language. R1 has a **pure-Python twin** that parses fixtures, soft-lints semantic bad cases, and round-trips pin-map examples — without requiring `antlr4-python3-runtime` in the core package. Write=display means **one AST + one emit shape** for pin map and mutate. Legacy `@TAG` pipe is **not** in this grammar and **not** a preferred agent dialect (import-once footnote only; keep import paths if present).

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

## 2. Is `MemNet.g4` adequate?

| Role | Judgement |
|------|-----------|
| Teaching shapes for R1 | Yes — lawPin, edge-id forms, `KW_NEW`, STRING escapes aligned with design. **Keep.** |
| Codegen-ready SSOT | Still a stub; **runtime twin** is `tier_a.py` until optional ANTLR generate. **Keep twin.** |
| Policy | R1 = atoms only; pipe **out** of this `.g4` (pipe remains import/store footnote); focus/caps **out** of body grammar. |

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
| Future | Optional `antlr4 -Dlanguage=Python3 -visitor MemNet.g4` under a generated tree |
| Host | Python ≥3.11 |
| Legacy pipe | Deprecated import-once only — not in `.g4`, not preferred agent I/O |

---

## 5. Pipe is not preferred agent I/O

**Locked:** shared dialect only for agent I/O. Do not add `@` lexer modes to the shared-dialect `.g4`. Bad fixtures `05_` / `09_` are **parse-reject** (pipe as agent surface) — **keep** those fixtures; they teach illegal shapes. Historical compile sketches live under `examples/deprecated/` if kept.

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
| Visitor from `.g4` | Optional later |
| Legacy pipe compile sketch | Deprecated (`examples/deprecated/`) — retained for history |

---

## 9. Requirement hooks (thin)

| Leaf | ANTLR / twin angle |
|------|--------------------|
| MN-REQ-08.* | Shared-dialect `.g4` + emit twin = sole LLM-facing dialect |
| MN-REQ-08.9 | Pin-map emit same grammar as mutate input |
| MN-REQ-09.1–09.2 | Canonical parse + reject invalid |
| MN-REQ-09.3–09.4 | Inspect via AST render; no ad-hoc splits |
| MN-REQ-03 / 10.4 | `KW_NEW` mint; engine-allocated ids; copy from pin map |
