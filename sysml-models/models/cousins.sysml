/*
  Cousin pointing / identity contrast — not a product switch.

  APPLICATION nest (like HostSearchBridge): MUST NOT instantiate under
  MemNetSystem. Chosen design stays TARGET: cue q → RelativeSeed →
  ShapeWalk → pin_map emit. Cousins are alternative pointing, cabinet,
  or understander designs. Reviewed via GitHub remote files only
  (no clone). Cite paths in part docs.

  Load: after requirements.sysml, before deploy.sysml (config.yaml).
  Root last. Recall/Commit operatorCount stays 2; liveNeo4jClaimed stays
  false. Python engine and leftover 0.9 store drop are out of this cut.
*/
package MemNetCousinContrast {
  private import ScalarValues::*;
  private import MemNetRequirements::*;

  // =====================================================================
  // Chosen TARGET pointing (identity / Recall story — not a third operator)
  // =====================================================================

  part def MemNetTargetPointing {
    doc /*
      Chosen MemNet TARGET pointing. Cue q is a codebook token (kind /
      labels, properties the node actually has, keyword; nickname id only
      if already set). name is NOT required. RelativeSeed MATCH_L yields
      walk-root graph elements Q; ShapeWalk walks k hops from Q under one
      M; pin_map emits that bounded neighbourhood. Commit is pattern MERGE
      by labels+properties. Re-cue to point again. GraphElement is
      identity; optional id is a nickname only. HiddenStoreHandle stays
      off the wire. SHALL NOT require --anchor <store-key> as product law.
    */
    attribute storeKeyOnWire : Boolean = false;
    attribute requiredUniqueName : Boolean = false;
    attribute sessionVsVault : String = "session_goldfish";
    attribute queryLanguage : String = "gql_opencypher_shaped";
    attribute productJob : String = "session_working_memory";
    attribute cueThenRelativeSeedThenShapeWalk : Boolean = true;
    attribute cueMayHitSeveralRoots : Boolean = true;
    attribute relativeSeedHardLimitHolds : Boolean = true;
    attribute unionWalkUnderOneM : Boolean = true;
    attribute inventThirdOperatorOnAmbiguity : Boolean = false;
    attribute graphElementIsIdentity : Boolean = true;
    attribute nameRequired : Boolean = false;
  }

  // =====================================================================
  // Seven cousins (pointing / identity only — not a clone of each product)
  // =====================================================================

  part def CousinNl2Gql {
    doc /*
      zhiqix/NL2GQL (R³-NL2GQL): English → nGQL translator over a warehouse.
      Gold queries use WHERE id(n) == "Tim Duncan" / LOOKUP … YIELD
      id(vertex). Schema classes carry vid (player.__init__(self, vid,
      name, age)). System.py FAISS rewriter aligns NL to store keys
      (faiss=FAISS(new_emb_list, node_csv)). Store-key on the query wire.
      Cite: README.md (train/test JSON); System.py.
    */
    attribute storeKeyOnWire : Boolean = true;
    attribute requiredUniqueName : Boolean = false;
    attribute sessionVsVault : String = "warehouse";
    attribute queryLanguage : String = "ngql";
    attribute productJob : String = "nl2gql_translator";
    attribute faissRewriterAlignsToVid : Boolean = true;
    attribute mustNotCopy : Boolean = true;
  }

  part def CousinGraphLite {
    doc /*
      GraphLite-AI/GraphLite (default main): embeddable ISO-GQL store,
      not a memory product. Pointing is GQL pattern cue by label+properties.
      docs/Getting Started With GQL.md: INSERT (:Person {name: 'Alice
      Johnson'}) then MATCH the same pattern. Grammar has no MERGE; CREATE
      is catalog-only (SCHEMA/GRAPH). Data verb is INSERT. Optional ID()
      exists in graphlite/src/functions/graph_functions.rs but docs never
      point with it. Engine mints content-hash ids
      (generate_node_content_id → node_{:x} from sorted labels+all props)
      in graphlite/src/exec/write_engine/operations/insert.rs. Storage key
      node:{node_id} in Architecture.md. Session is auth + SESSION SET
      GRAPH, not the graph. Cabinet/store cousin only. MUST NOT copy: GQL
      engine, content-hash-of-entire-property-map as identity, SQLite-clone
      product job.
    */
    attribute storeKeyOnWire : Boolean = false;
    attribute requiredUniqueName : Boolean = false;
    attribute sessionVsVault : String = "durable_cabinet";
    attribute queryLanguage : String = "iso_gql";
    attribute productJob : String = "embedded_graph_store";
    attribute patternCueByLabelAndProps : Boolean = true;
    attribute dataVerbIsInsert : Boolean = true;
    attribute grammarHasMerge : Boolean = false;
    attribute createIsCatalogOnly : Boolean = true;
    attribute docsPointWithIdFunction : Boolean = false;
    attribute contentHashNodeId : Boolean = true;
    attribute sessionIsAuthPlusGraphContext : Boolean = true;
    attribute productSwapForbidden : Boolean = true;
    attribute mustNotCopyGqlEngine : Boolean = true;
    attribute mustNotCopyContentHashIdentity : Boolean = true;
    attribute mustNotCopySqliteCloneJob : Boolean = true;
    attribute mustNotCopyAsAgentApi : Boolean = true;
  }

  part def CousinTextToSqlGraphRag {
    doc /*
      kennethleungty/Text-to-SQL-with-KG-Neo4j-GraphRAG (main): schema KG
      for Text-to-SQL. MERGE by unique name (MERGE (t:Table {name: $name})).
      elementId only to write embeddings back
      (notebooks/graph_build_and_query_20250521.ipynb). Retriever returns
      node.name, never elementId. Required unique name for Table/Concept.
      Persistent Neo4j. Not session goldfish. MUST NOT copy: unique-name
      MERGE as universal identity, vector/fulltext as pointing, elementId
      writeback. Cite: README.md; notebooks/graph_build_and_query_20250521.ipynb.
    */
    attribute storeKeyOnWire : Boolean = false;
    attribute requiredUniqueName : Boolean = true;
    attribute sessionVsVault : String = "warehouse";
    attribute queryLanguage : String = "cypher_plus_sql";
    attribute productJob : String = "warehouse_graphrag";
    attribute mergeByUniqueName : Boolean = true;
    attribute retrieverReturnsName : Boolean = true;
    attribute elementIdWritebackOnly : Boolean = true;
    attribute embeddingsAsRecallOperator : Boolean = true;
    attribute mustNotCopyUniqueNameMergeAsIdentity : Boolean = true;
    attribute mustNotCopyVectorFulltextAsPointing : Boolean = true;
    attribute mustNotCopyElementIdWriteback : Boolean = true;
    attribute mustNotCopy : Boolean = true;
  }

  part def CousinGraphify {
    doc /*
      Graphify-Labs/graphify (default v8): code/docs → graphify-out/graph.json.
      Agent points by human label (graphify explain "APIRouter"). Query:
      match G.nodes[n].label by case-folded substring + IDF, start 1-3
      nodes, BFS depth-3 / DFS neighbourhood
      (graphify/skills/claude/references/query.md). Store id is a slug
      (graphify/ids.py). No GQL on the agent path (NetworkX). Persistent
      vault. Agent loop is cue-by-label then emit neighbourhood — same
      shape as pin_map. MUST NOT copy: Unicode id-normalization,
      substring/IDF as identity, Leiden, Cypher export as the query API.
      Cite: README.md; docs/how-it-works.md; query.md; ids.py.
    */
    attribute storeKeyOnWire : Boolean = false;
    attribute requiredUniqueName : Boolean = false;
    attribute sessionVsVault : String = "persistent_vault";
    attribute queryLanguage : String = "networkx_label_neighbourhood";
    attribute productJob : String = "corpus_map_query";
    attribute humanCueByLabel : Boolean = true;
    attribute neighbourhoodEmitLikePinMap : Boolean = true;
    attribute storeIdIsSlug : Boolean = true;
    attribute gqlOnAgentPath : Boolean = false;
    attribute mustNotCopyUnicodeIdNormalization : Boolean = true;
    attribute mustNotCopySubstringIdfAsIdentity : Boolean = true;
    attribute mustNotCopyLeiden : Boolean = true;
    attribute mustNotCopyCypherExportAsQueryApi : Boolean = true;
  }

  part def CousinUnderstandAnything {
    doc /*
      Egonex-AI/Understand-Anything (main): multimodal understander +
      persistent .ua/knowledge-graph.json. Schema requires both id and
      name. Ids are typed composites (file:path, function:path:name) in
      graph-builder.ts. Chat: grep name/summary/tags, note ids, then
      1-hop edges (skills/understand-chat/SKILL.md). Query cue is
      name/text; ids are file-format keys. Not session goldfish. Partial
      overlap: ingest → graph → query. Split: no goldfish, no GQL-only
      pin_map emit. MUST NOT copy: type:path:name as agent language,
      Fuse+embeddings as TARGET, commit-the-JSON as the memory product.
      Cite: README.md; graph-builder.ts; skills/understand-chat/SKILL.md.
    */
    attribute storeKeyOnWire : Boolean = false;
    attribute requiredUniqueName : Boolean = false;
    attribute sessionVsVault : String = "persistent_json_vault";
    attribute queryLanguage : String = "json_dashboard_search";
    attribute productJob : String = "multimodal_understander";
    attribute schemaRequiresIdAndName : Boolean = true;
    attribute cueIsNameText : Boolean = true;
    attribute idsAreFileFormatKeys : Boolean = true;
    attribute typedCompositeStoreId : Boolean = true;
    attribute ingestThenGraphThenQuery : Boolean = true;
    attribute goldfishPinMapEmit : Boolean = false;
    attribute gqlOnlyWire : Boolean = false;
    attribute mustNotCopyTypedPathIdAsAgentLanguage : Boolean = true;
    attribute mustNotCopyFuseEmbeddingsAsTarget : Boolean = true;
    attribute mustNotCopyCommitJsonAsMemoryProduct : Boolean = true;
  }

  part def CousinLogseq {
    doc /*
      logseq/logseq: persistent notes vault (DataScript). Pages identified
      by unique :block/name; blocks by :block/uuid
      (src/main/frontend/worker/render_affected_keys.cljs
      page-identity-attrs #{:block/name :block/uuid}). Human points at a
      page by title [[Rin]]. Closest human-facing "point with a name you
      have" cousin. Unique page-name SHALL NOT become MemNet identity law
      (name is not required). Block UUID is the store-key path MemNet
      dropped. Cite: README.md;
      src/main/frontend/worker/render_affected_keys.cljs.
    */
    attribute storeKeyOnWire : Boolean = true;
    attribute requiredUniqueName : Boolean = true;
    attribute sessionVsVault : String = "notes_vault";
    attribute queryLanguage : String = "datascript";
    attribute productJob : String = "notes_vault";
    attribute pageNameHumanPointing : Boolean = true;
    attribute blockUuidStoreKey : Boolean = true;
    attribute closestHumanNameCousin : Boolean = true;
    attribute mustNotCopyUniquePageNameLaw : Boolean = true;
  }

  part def CousinSiyuan {
    doc /*
      siyuan-note/siyuan: leftover MemNet 0.9 (--anchor TSK1) path. Every
      block (including the document) gets a minted id YYYYMMDDHHmmss-xxxxxxx
      (docs/API.md example 20210917220056-yxtyl7i). API and refs are by
      that id; title/path are lookup FROM the id (/api/filetree/getHPathByID).
      Cite: README.md; docs/API.md (Get human-readable path based on ID).
    */
    attribute storeKeyOnWire : Boolean = true;
    attribute requiredUniqueName : Boolean = false;
    attribute sessionVsVault : String = "notes_vault";
    attribute queryLanguage : String = "http_api";
    attribute productJob : String = "notes_vault";
    attribute mintedBlockIdOnWire : Boolean = true;
    attribute leftoverZeroNineAnchorPath : Boolean = true;
    attribute mustNotCopy : Boolean = true;
  }

  // =====================================================================
  // Contrast nest root — outside MemNetSystem
  // =====================================================================

  part def CousinPointingContrast {
    doc /*
      Thin contrast nest on the identity / Recall story. States chosen
      TARGET pointing; places each cousin as an alternative. TARGET
      impact: copy cue-without-store-key and neighbourhood emit. SHALL
      NOT copy engines, unique-name MERGE as identity, silent LLM merge
      of same-name nodes into the store, content-hash ids,
      typed path-ids, or vector indexes as identity. Open hard part (no
      third operator): a cue may hit several relative roots; RelativeSeed
      stays bounded (LIMIT L) and honest when |Q| > 1. Cousins confirm
      TARGET; they do not force a store-key back onto the wire. GraphLite
      is a cabinet, not the product. Logseq pages are the closest
      name-you-have cousin; SiYuan / NL2GQL are the leftover-id path.
    */
    attribute designOnly : Boolean = true;
    attribute mustNotNestUnderMemNetSystem : Boolean = true;
    attribute productSwitchForbidden : Boolean = true;
    attribute copyCueWithoutStoreKey : Boolean = true;
    attribute copyNeighbourhoodEmit : Boolean = true;
    attribute mustNotCopyMintedBlockId : Boolean = true;
    attribute mustNotCopyVidOnWire : Boolean = true;
    attribute mustNotCopyUniquePageNameLaw : Boolean = true;
    attribute mustNotCopyEmbeddingsAsRecall : Boolean = true;
    attribute mustNotCopyGraphLiteAsProduct : Boolean = true;
    attribute mustNotCopyGqlEngine : Boolean = true;
    attribute mustNotCopyContentHashIdentity : Boolean = true;
    attribute mustNotCopyUniqueNameMergeAsIdentity : Boolean = true;
    attribute mustNotCopySilentLlmSameNameMerge : Boolean = true;
    attribute mustNotCopyTypedPathIdsAsAgentLanguage : Boolean = true;
    attribute mustNotCopyVectorIndexAsIdentity : Boolean = true;
    attribute operatorCountUnchanged : Integer = 2;
    attribute liveNeo4jClaimed : Boolean = false;
    attribute inventThirdOperatorOnAmbiguity : Boolean = false;
    part chosen : MemNetTargetPointing;
    part nl2gql : CousinNl2Gql;
    part graphlite : CousinGraphLite;
    part textToSqlGraphRag : CousinTextToSqlGraphRag;
    part graphify : CousinGraphify;
    part understandAnything : CousinUnderstandAnything;
    part logseq : CousinLogseq;
    part siyuan : CousinSiyuan;

    satisfy MN_REQ_00_MissionBridge::MN_REQ_02_MemoryNetGraph::MN_REQ_02_8_IdNotRequiredOnWire;
    satisfy MN_REQ_00_MissionBridge::MN_REQ_02_MemoryNetGraph::MN_REQ_02_9_MustNotCopyCousinStoreKey;
    satisfy MN_REQ_00_MissionBridge::MN_REQ_04_SliceEconomy::MN_REQ_04_7_RelativeSeedThenShapeWalk;
    satisfy MN_REQ_00_MissionBridge::MN_REQ_04_SliceEconomy::MN_REQ_04_8_CueMultiRootHonest;
    satisfy MN_REQ_00_MissionBridge::MN_REQ_13_RecallCommit::MN_REQ_13_1_TwoOperators;
    satisfy MN_REQ_00_MissionBridge::MN_REQ_13_RecallCommit::MN_REQ_13_2_SameThingAbsorb;
  }

  part cousinPointing : CousinPointingContrast;
}
