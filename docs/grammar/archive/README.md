# Grammar archive — historical Layer / Tier A

**Status:** quarantine only. **Not** agent teach. **Not** a product accept path.

User / product direction (post ADR-001 supersession): **one dialect = GQL** ([`../gql-wire-profile.md`](../gql-wire-profile.md)). MemNet Layer / Tier A ASCII is **retired from doctrine**.

| Path | What it was |
|------|-------------|
| [`docs/`](docs/) | Former Layer ontology, GQL consideration narrative, Layer↔GQL crosswalk |
| [`antlr/`](antlr/) | `MemNetLayer.g4` + generated Python + smoke |
| [`examples-layer/`](examples-layer/) | Layer golden fixtures |
| [`tools/layer_soft_validate.py`](tools/layer_soft_validate.py) | Layer soft-validate harness |

**MUST NOT** cite these as 1.x wire, legacy-accept teach, or peer dialect.  
**M2** removes as-is engine codecs that still parse Layer lines from the product path.  
Default pytest **does not** collect [`../../../tests/grammar/archive/`](../../../tests/grammar/archive/).
