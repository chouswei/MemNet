# MemNet documentation

Two classes only. **Developers** — engine, MCP, shared dialect, and agent operating doctrine for this product. **Applications** — how to apply MemNet in downstream work (system repos, domains, custom MCP).

Hub: [`AGENTS.md`](../AGENTS.md) · layout: [`LAYOUT.md`](../LAYOUT.md) · doctrine entry: [`README.md`](../README.md).

---

## For developers

MemNet engine / generic MCP / shared dialect / operating the product as an agent.

| Doc | Role |
|-----|------|
| [`LLM-GUIDE.md`](LLM-GUIDE.md) | Agent playbook (0.4.x goldfish loop, shared dialect, MCP primary) |
| [`ROADMAP-0.5.md`](ROADMAP-0.5.md) | One-path / 0.5.0 gap-closure plan (remote entry, dialect teach, Pi graph owner) |
| [`multi-agent-sessions.md`](multi-agent-sessions.md) | Multitask operating model (as-is 0.4.x): shared session, parent/worker MUST/MUSTNOT, transport |
| [`grammar/memnet-grammar-design.md`](grammar/memnet-grammar-design.md) | Shared dialect SSOT (Write = display, pin map, `NEW` vs locators) |
| [`grammar/memnet-field-formulas.md`](grammar/memnet-field-formulas.md) | Generic formula EDGE relations (any domain) |
| [`grammar/memnet-multi-layer.md`](grammar/memnet-multi-layer.md) | Stratified pin maps (design) |
| [`grammar/gql-consideration.md`](grammar/gql-consideration.md) | ISO GQL vs Layer: map, not teach as wire |
| [`grammar/memnet-neighbourhood-reserve.md`](grammar/memnet-neighbourhood-reserve.md) | Neighbourhood reserve (design) |
| [`grammar/memnet-security-multi-agent.md`](grammar/memnet-security-multi-agent.md) | Session ACL / multi-agent (design) |
| [`grammar/memnet-grammar-antlr.md`](grammar/memnet-grammar-antlr.md) | ANTLR grammar notes |
| [`grammar/examples/`](grammar/examples/) | Golden fixtures (shared dialect + layer) |
| [`grammar/antlr/`](grammar/antlr/) | Layer grammar sources and smoke parse |

**Multitask (developer):** enforceable doctrine lives in [`multi-agent-sessions.md`](multi-agent-sessions.md). Product development skill: [`.cursor/skills/memnet-reference/`](../.cursor/skills/memnet-reference/). SysML trail: MN-REQ-12 → MN-VER-12-G00 + S01…S09 → [`sysml-models/outputs/multitask-case-study.md`](../sysml-models/outputs/multitask-case-study.md).

---

## For applications

Downstream system development and domain patterns — MemNet as working memory in a product or pipeline.

| Doc | Role |
|-----|------|
| [`application-notes/llm-system-dev-multitask.md`](application-notes/llm-system-dev-multitask.md) | Multitask in `modelbasedPrj-*` repos (mission SSOT + product SysML structural SSOT) |
| [`application-notes/llm-software-development.md`](application-notes/llm-software-development.md) | Multi-turn coding in Cursor |
| [`application-notes/llm-sysml-v2-modeling.md`](application-notes/llm-sysml-v2-modeling.md) | SysML v2 modeling (single-agent) |
| [`application-notes/llm-build-on-memnet.md`](application-notes/llm-build-on-memnet.md) | Custom MCP + Cursor skill pack on MemNet |
| [`application-notes/llm-tech-docs-decomposition.md`](application-notes/llm-tech-docs-decomposition.md) | Manual / SCPI decomposition |
| [`application-notes/llm-circuit-schematic.md`](application-notes/llm-circuit-schematic.md) | Circuit schematic / s-domain (**Layer** ports / law / bind) |
| [`application-notes/llm-nodal-analysis-formulas.md`](application-notes/llm-nodal-analysis-formulas.md) | Nodal method ↔ NODE `law=` + binds |
| [`application-notes/llm-daily-news.md`](application-notes/llm-daily-news.md) | Batch RSS digest |
| [`application-notes/llm-mud.md`](application-notes/llm-mud.md) | Multiplayer MUD (shared serve) |
| [`application-notes/`](application-notes/) | Application-notes index (**Layer** teach) |
| [`application-notes/examples/`](application-notes/examples/) | Worked Layer examples (e.g. inverting amplifier) |

**Multitask (application):** user-pack skill `~/.cursor/skills/memnet-multitask/`; adopt MN-REQ-12 in a system repo via [`application-notes/llm-system-dev-multitask.md`](application-notes/llm-system-dev-multitask.md); operational MUST/MUSTNOT still comes from developer doc [`multi-agent-sessions.md`](multi-agent-sessions.md).

Application notes teach **Layer** as the primary agent surface (`ports=` / `law=` / `--bind-->` where electrical; bare-id relations for chart rows). Legacy `@TAG` pipe, paren `--(rel)-->`, and formula-on-EDGE are accept-only pointers — do not dual-teach.
