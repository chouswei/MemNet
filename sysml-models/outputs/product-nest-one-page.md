# Product nest (one page)

Mission working memory: hand off by **session id**; GQL ask/commit; no graph dump in chat.

```text
MemNetSystem                          // SharedLlmMemory product
├── Core
│   ├── Session                       // session id = SSOT handle
│   ├── GQL                           // GqlCodec + ProductGqlGate (reject Layer)
│   └── RecallCommit                  // TWO operators only
│       ├── Recall                    // cue → pin_map (outline / Peak_L honesty)
│       └── Commit                    // mutate (+ RSV lease)
├── Multitask
│   ├── Path A                        // shared session → re-pin (no import nest)
│   └── Path B                        // slice → ImportGuard (optional soft)
│                                     //        → ImportAbsorb (hard)
└── DurableBuffer                     // ONE primary cabinet story (hydrate/flush)

APPLICATION LOOK   CousinPointingContrast, HostSearchBridge, …
ARCHIVE LOOK       MemNetArchive (models/archive.sysml) — leftover_* /
                   TierACodec / LegacyPipe* shelf; ProjectMemNet MUST NOT import
OPS LOOK           MemNetUsageDashboard — human look only; not agent wire
```

## Soft-pass kills (this cut)

- Leftovers nested under Schema / GraphStore on the product path
- Dashboard as manage / agent web API (`agentWire=false`, `httpImplemented=false`)
- Tip as face (`tipIsFace=false`)
- Unparking HTTP dashboard code
- SemVer `b` (honesty `c` only; goldfish loop unchanged)

Honesty that leftovers exist lives on the **ARCHIVE** shelf, not on `ProjectMemNet` load (`sysml-models/config.yaml` omits `archive.sysml`; `root.sysml` does not import `MemNetArchive`).
