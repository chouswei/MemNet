# Application notes

Domain patterns for **using** MemNet (not engine internals). Index: [`../README.md`](../README.md).

**1.x dialect teach (ADR-001):** openCypher-shaped **GQL** + shaped `pin_map` — see [`examples/inverting-amplifier-gql-case-study.md`](examples/inverting-amplifier-gql-case-study.md).  
**Legacy (migration / most notes until M3):** **Layer** — `CST` + `ports=` + `law=` on NODE; port↔port `--bind-->`; bare-id relations. Doctrine: [`../grammar/memnet-multi-layer.md`](../grammar/memnet-multi-layer.md). Roadmap: [`../ROADMAP-0.5.md`](../ROADMAP-0.5.md).

Legacy `@TAG` pipe, paren `--(rel)-->`, and formula-on-EDGE (`derives`) appear only as **accept / pointer** notes — do not dual-teach Layer + GQL as peer 1.x surfaces.

| Note | Role |
|------|------|
| [`examples/inverting-amplifier-memnet.md`](examples/inverting-amplifier-memnet.md) | InvAmp derivation + Layer seed (legacy teach) |
| [`examples/inverting-amplifier-gql-case-study.md`](examples/inverting-amplifier-gql-case-study.md) | InvAmp through **GQL-wire** model (ADR-001) |
| [`llm-circuit-schematic.md`](llm-circuit-schematic.md) | Schematic / s-domain Layer |
| [`llm-nodal-analysis-formulas.md`](llm-nodal-analysis-formulas.md) | Node method ↔ NODE `law=` + binds |
| [`llm-sysml-v2-modeling.md`](llm-sysml-v2-modeling.md) | SysML v2 session memory |
| [`llm-system-dev-multitask.md`](llm-system-dev-multitask.md) | Multitask in `modelbasedPrj-*` |
| [`llm-software-development.md`](llm-software-development.md) | Multi-turn coding memory |
| [`llm-tech-docs-decomposition.md`](llm-tech-docs-decomposition.md) | Manual / SCPI atomisation |
| [`llm-daily-news.md`](llm-daily-news.md) | RSS digest pipeline |
| [`llm-mud.md`](llm-mud.md) | Multiplayer MUD |
| [`llm-build-on-memnet.md`](llm-build-on-memnet.md) | Custom MCP + skill pack |
