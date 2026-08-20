# MemNet layout adaptation

This repository follows [SYSTEM-REPO-LAYOUT.md](../SYSTEM-REPO-LAYOUT.md) for **model-based software project development**, with the adaptations below. MemNet is a software product (NODE|EDGE graph engine + generic MCP; in-process first), not a hardware deploy with PCBA.

## Mapping

| Spec concept | MemNet choice |
|--------------|---------------|
| `parts/common/<lib>/` | Core Python library `parts/common/memnet/` (shared by MCP hosts) |
| `parts/<part>/software/` | Product surface: `memnet-mcp` |
| `docs/` | Cross-part guides — index [`docs/README.md`](docs/README.md). Job folders: `grammar/` (wire), `cabinet/` (durable), `extras/` (numbered extras), `operations/` (Multitask), `application-notes/` (`system/` / `domains/` / `examples/`) |
| `sysml-models/` | System SysML (`models/`, design notes under `outputs/`); libs pin may still be local |
| `pcba-libs/` | **N/A** — no hardware boards |
| `project.toml` | System identity + SemVer; Python packaging remains in `pyproject.toml` |
| `scripts/`, `tests/`, `data/` | Kept at repo root (tooling, tests, sample data) |
| `refs/` | Local vendor grammar pins (`refs/README.md` tracked; extract trees gitignored) |

## Part roots

| Folder | Role |
|--------|------|
| `parts/common/memnet` | Shared `memnet` package (CLI + graph engine; Tier A, MutateGate, PinMapComposer) |
| `parts/memnet-mcp` | Generic MemNet MCP server (`memnet_mcp`) |

Novel-writer is **not** a part root. Removal record: [`DROP-NOVEL-WRITER.md`](DROP-NOVEL-WRITER.md).

## Intentionally not migrated

- GitHub / clone folder rename to `modelbasedPrj-memnet` (user decision)
- Pinning `sysml-models/libs` as a proper `sysml-libs` submodule (local OMG junction may be used until then)
- Rewriting historical `CHANGELOG.md` paths
