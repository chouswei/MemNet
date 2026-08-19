# Grammar archive — historical Layer / Tier A

**Status:** quarantine only. **Not** agent teach. **Not** a product accept path.

User / product direction (post ADR-001 supersession): **one dialect = GQL** ([`../gql-wire-profile.md`](../gql-wire-profile.md)). MemNet Layer / Tier A ASCII is **retired from doctrine**.

| Path | What it was |
|------|-------------|
| [`docs/`](docs/) | Former Layer ontology, GQL consideration narrative, Layer↔GQL crosswalk |
| [`antlr/`](antlr/) | `MemNetLayer.g4` + generated Python + smoke; unused `MemNet.g4` stub (never codegen) |
| [`examples-layer/`](examples-layer/) | Layer golden fixtures |
| [`tools/layer_soft_validate.py`](tools/layer_soft_validate.py) | Layer soft-validate harness |

**MUST NOT** cite these as product wire, legacy-accept teach, or peer dialect.  
**M2 done:** product accept rejects Layer/Tier A. Sources here stay quarantine-only.  
Default pytest **does not** collect [`../../../tests/grammar/archive/`](../../../tests/grammar/archive/).
