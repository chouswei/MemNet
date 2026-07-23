# MemNet grammar × ANTLR4 — coherence notes

**Status:** R1 twin live (`docs/grammar/tools/tier_a.py` + package `memnet.tier_a`); `.g4` remains teaching / future codegen stub  
**Pair with:** `memnet-grammar-design.md`, `MemNet.g4`, `examples/`, `tools/`  
**Tooling pin:** `third_party/antlr4/` **4.13.2** (Python3 target docs: `doc/python-target.md`)  
**British English.**

---

## Verdict

Tier A is a **good fit for ANTLR4** as a line-oriented language. R1 has a **pure-Python twin** that parses fixtures, soft-lints semantic bad cases, and round-trips warm examples — without requiring `antlr4-python3-runtime` in the core package. Write=display means **one AST + one emit shape** for warm and mutate. Legacy `@TAG` pipe is **not** in this grammar and **not** a peer dialect.

---

## 1. Does the proposed syntax parse cleanly?

| Topic | Assessment |
|-------|------------|
| Left recursion | None. Fine for ANTLR4. |
| Ambiguity (parser) | Line forms distinguishable by first tokens (`+ KIND [id]`, `+ Eid [a] --(rel)--> [b]`, `~ Eid`, `- Eid`, `LAW…`). |
| Ambiguity (values) | **R1 locked atoms-only** — `;` joins fields only. List/map deferred to R2. |
| Lexer vs parser | One `IDENT` + `KW_NEW` + visitor/twin checks. |
| Keywords | Ops, `##` heads, mint **`KW_NEW`** (`NEW`). Kind tokens remain data. |
| `lawPin` | **`IDENT field (SEMI field)*`** — first field has **no** leading `;` (matches warm LAW lines). |
| Edge ids | Warm: `+ E77 [from] --(rel)--> [to]`. Create: `+ NEW [from] --(rel)--> [to]` or omit eid. |
| `key=value` | `IDENT ASSIGN value`. `+=` / `-=` longer match before `=`. |
| Arrows | `--(` + rel + `)-->` unambiguous. |
| STRING | Escapes `\\` `\"` `\n` `\r` `\t`; quote Windows paths. |

---

## 2. Is `MemNet.g4` adequate?

| Role | Judgement |
|------|-----------|
| Teaching shapes for R1 | Yes — lawPin, edge-id forms, `KW_NEW`, STRING escapes aligned with design. |
| Codegen-ready SSOT | Still a stub; **runtime twin** is `tier_a.py` until optional ANTLR generate. |
| Policy | R1 = atoms only; pipe **out** of this `.g4`; focus/caps **out** of body grammar. |

---

## 3. Write = display and ANTLR

1. **Parse** recovers AST (`Node` | `Edge`).  
2. **Emit** (`tier_a.emit`) pretty-prints with the same separators.  
3. Round-trip tests: parse → emit → parse on `01_` / `04_`.  
4. MN-REQ-08.7 / 08.9 / 09.3: warm emit and mutate input share one grammar.

---

## 4. Python runtime fit

| Item | Note |
|------|------|
| R1 twin | `memnet.tier_a` / `docs/grammar/tools/tier_a.py` — no antlr4 dependency |
| Golden | `python -m pytest tests/grammar -q` |
| Future | Optional `antlr4 -Dlanguage=Python3 -visitor MemNet.g4` under a generated tree |
| Host | Python ≥3.11 |
| Legacy pipe | Deprecated import-once only — not in `.g4`, not agent-facing |

---

## 5. Pipe is not a peer dialect

**Locked:** Tier A only for agent I/O. Do not add `@` lexer modes to Tier A. Bad fixtures `05_` / `09_` are **parse-reject** (pipe as agent surface). Historical compile sketches live under `examples/deprecated/` if kept.

---

## 6. Pin-map / warm / fixtures

| Need | Status |
|------|--------|
| Law pins without leading `;` | Fixed in `.g4` + twin |
| Edge ids on warm | `+ Eid [from] --(rel)--> [to]` in `01_` / `04_` |
| Multi-word / punctuated atoms | Bare atom or `STRING` |
| focus / caps | **Envelope only** — not in body grammar or fixtures |
| Headerless mutate | Legal (`02_`, `03_`, `14_`, `15_`) |
| Warm sections | **Required** on agent-facing warm fixtures |
| SET membership | R1: expand to many EDGE lines (`member_of` / `contains`) |
| Fixture labels | `examples/README.md` — `parse-reject` vs `lint-reject` |
| Soft prose/fat lint | parse OK; harness lint-reject (`06_`, `08_`) |

---

## 7. Locked defaults

1. Agent dialect → **Tier A only** (Write = display).  
2. Pipe → **deprecated import footnote**, not a standing tier.  
3. `##` on warm → **required** for agent-facing warm.  
4. Fat fields → **soft lint**.  
5. Compound values → **R1 atoms-only**; R2 deferred.  
6. Warm metadata → **envelope only**.

**Still open:** `NEW` as edge **endpoint** in the same mutate batch as node creates.

---

## 8. Engineering status

| Step | Status |
|------|--------|
| R1 value rule atoms-only | Done |
| Golden harness | Done — `tests/grammar/` |
| Parse / emit twin | Done — `tier_a.py` |
| Visitor from `.g4` | Optional later |
| Legacy pipe compile sketch | Deprecated (`examples/deprecated/`) |

---

## 9. Requirement hooks (thin)

| Leaf | ANTLR / twin angle |
|------|--------------------|
| MN-REQ-08.* | Tier A `.g4` + emit twin = sole LLM-facing dialect |
| MN-REQ-08.9 | Warm emit same grammar as mutate input |
| MN-REQ-09.1–09.2 | Canonical parse + reject invalid |
| MN-REQ-09.3–09.4 | Inspect via AST render; no ad-hoc splits |
| MN-REQ-03 / 10.4 | `KW_NEW` mint; engine-allocated ids; copy from warm |
