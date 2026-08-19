# NOTICE — vendored official grammar BNF

MemNet vendors **one file** from the openCypher project as the spelling /
identity SSOT for node, relationship, and property patterns.

| Item | Value |
|------|--------|
| Vendored file | [`openCypher.bnf`](openCypher.bnf) |
| Upstream path | `grammar/openCypher.bnf` |
| Source repository | https://github.com/opencypher/openCypher |
| Upstream `main` at fetch | `677cbafabb8c` (2026-03-20) |
| Raw URL | https://raw.githubusercontent.com/opencypher/openCypher/main/grammar/openCypher.bnf |
| Licence of this file | Apache License 2.0 |

Do **not** rewrite productions in `openCypher.bnf`. Refresh by re-fetching the official file.

## Copyright (upstream NOTICE)

Copyright (c) "Neo4j"  
Neo4j Sweden AB [https://neo4j.com]

Licensed under the Apache License, Version 2.0 (the "License"); you may not
use this file except in compliance with the License. You may obtain a copy of
the License at http://www.apache.org/licenses/LICENSE-2.0

A full copy of the Apache License 2.0, taken from the upstream `LICENSE`
file, is [`LICENSE-Apache-2.0.txt`](LICENSE-Apache-2.0.txt).

Attribution notice under the terms of the Apache License 2.0 (from the
upstream project NOTICE):

> This work was created by the collective efforts of the openCypher community.
> Without limiting the terms of Section 6, any Derivative Work that is not
> approved by the public consensus process of the openCypher Implementers Group
> should not be described as “Cypher” (and Cypher® is a registered trademark of
> Neo4j Inc.) or as "openCypher". Extensions by implementers or prototypes or
> proposals for change that have been documented or implemented should only be
> described as "implementation extensions to Cypher" or as "proposed changes to
> Cypher that are not yet approved by the openCypher community".

The upstream README also records © Copyright Neo4j, Inc.

## MemNet product licence

The MemNet product remains **MIT** (repository root [`LICENSE`](../../LICENSE)).
This vendored BNF, this NOTICE, and [`LICENSE-Apache-2.0.txt`](LICENSE-Apache-2.0.txt)
are Apache-2.0 third-party material. They do not re-licence the rest of MemNet.

## What this is / is not

| Is | Is not |
|----|--------|
| Spelling / identity SSOT for node / relationship / property patterns | A promise to accept the whole language |
| Cite for “no store-key production” on CREATE / MERGE | A MemNet-invented `id` law |
| Apache-2.0 attribution for one official file | TCK compliance; a vendored TCK / CIP tree / ANTLR tools |
| | A second Python accept path; do not generate a parser/visitor from this BNF |

MemNet agent API stays gated (`pin_map` + mutate; no free WITH / UNWIND / CALL /
unbounded MATCH…RETURN). See [`gql-wire-profile.md`](gql-wire-profile.md).

## Behaviour cite (not vendored)

openCypher TCK `tck/features/clauses/create/Create1.feature` scenario
`[1] Create a single node` (`CREATE ()`) shows a node with empty filler —
no required property `id`. That feature is **not** copied into this repo and
is **not** a compliance claim.

## Trademark

Do **not** describe MemNet as “Cypher” or “openCypher”. Cypher® is a registered
trademark of Neo4j Inc. MemNet is a gated agent wire in the GQL family
(openCypher-shaped). Apache License §6 does not grant trademark rights.
