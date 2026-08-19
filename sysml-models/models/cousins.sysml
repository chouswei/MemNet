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
      GraphLite-AI/GraphLite: embeddable ISO GQL store (SQLite-shaped,
      Sled, OpenGQL grammar). Cabinet/engine cousin — DurableStore-like
      alternative, NOT MemNet's agent API. INSERT (:Person {name: …})
      and MATCH by labels+properties (docs/Getting Started With GQL.md).
      Internal node identity exists for set ops
      (graphlite/tests/identity_based_set_ops_test.rs;
      insert_node_identifier_regression_test). SHALL NOT swap MemNet
      product for GraphLite. Cite: README.md; docs/Getting Started With
      GQL.md.
    */
    attribute storeKeyOnWire : Boolean = false;
    attribute requiredUniqueName : Boolean = false;
    attribute sessionVsVault : String = "durable_cabinet";
    attribute queryLanguage : String = "iso_gql";
    attribute productJob : String = "embedded_graph_store";
    attribute productSwapForbidden : Boolean = true;
    attribute mustNotCopyAsAgentApi : Boolean = true;
  }

  part def CousinTextToSqlGraphRag {
    doc /*
      kennethleungty/Text-to-SQL-with-KG-Neo4j-GraphRAG: GraphRAG + SQL
      over Neo4j. Warehouse RAG (embeddings + graph). Notebook keys
      Table nodes with elementId(t) AS node_id and WHERE elementId(t) =
      $node_id when writing embeddings
      (notebooks/graph_build_and_query_20250521.ipynb). Not a session
      goldfish. Embeddings SHALL NOT become the Recall operator.
      Cite: README.md; notebooks/graph_build_and_query_20250521.ipynb.
    */
    attribute storeKeyOnWire : Boolean = true;
    attribute requiredUniqueName : Boolean = false;
    attribute sessionVsVault : String = "warehouse";
    attribute queryLanguage : String = "cypher_plus_sql";
    attribute productJob : String = "warehouse_graphrag";
    attribute embeddingsAsRecallOperator : Boolean = true;
    attribute mustNotCopy : Boolean = true;
  }

  part def CousinGraphify {
    doc /*
      Graphify-Labs/graphify: corpus map you query instead of grepping.
      graph.json (NetworkX node-link) nodes carry id (stable identifier)
      and label (human-readable name); edges source/target are those ids
      (docs/how-it-works.md). Human CLI often points by label
      (README: graphify explain "APIRouter"). Not a session goldfish;
      not GQL-only pin_map emit. graph.json id SHALL NOT become MemNet
      agent store-key law. Cite: README.md; docs/how-it-works.md.
    */
    attribute storeKeyOnWire : Boolean = true;
    attribute requiredUniqueName : Boolean = false;
    attribute sessionVsVault : String = "corpus_map";
    attribute queryLanguage : String = "graphify_cli_json";
    attribute productJob : String = "corpus_map_query";
    attribute humanCueOftenLabel : Boolean = true;
    attribute mustNotCopyGraphJsonIdAsLaw : Boolean = true;
  }

  part def CousinUnderstandAnything {
    doc /*
      Egonex-AI/Understand-Anything: closest "understand a thing into a
      graph" cousin — partial overlap only. Ingest (tree-sitter + LLM) →
      JSON knowledge graph → dashboard / search / chat. Nodes addressed
      by minted locator ids such as file:src/index.ts; edges .source ==
      that id (agents/knowledge-graph-guide.md). Semantic/fuzzy search
      is a product query, not RelativeSeed. Split: no session goldfish,
      no GQL-only pin_map emit. Cite: README.md;
      understand-anything-plugin/agents/knowledge-graph-guide.md.
    */
    attribute storeKeyOnWire : Boolean = true;
    attribute requiredUniqueName : Boolean = false;
    attribute sessionVsVault : String = "project_understander";
    attribute queryLanguage : String = "json_dashboard_search";
    attribute productJob : String = "multimodal_understander";
    attribute ingestThenGraphThenQuery : Boolean = true;
    attribute goldfishPinMapEmit : Boolean = false;
    attribute gqlOnlyWire : Boolean = false;
    attribute mustNotCopyLocatorIdAsStoreKey : Boolean = true;
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
      TARGET pointing; places each cousin as an alternative. Pins what
      MemNet MUST NOT copy. Open hard part (no third operator): a cue may
      hit several relative roots; RelativeSeed stays bounded (LIMIT L)
      and honest when |Q| > 1; ShapeWalk unions under one M. Cousins
      confirm TARGET; they do not force a store-key back onto the wire.
      GraphLite is a cabinet, not the product. Logseq pages are the
      closest name-you-have cousin; SiYuan / NL2GQL are the leftover-id
      path.
    */
    attribute designOnly : Boolean = true;
    attribute mustNotNestUnderMemNetSystem : Boolean = true;
    attribute productSwitchForbidden : Boolean = true;
    attribute mustNotCopyMintedBlockId : Boolean = true;
    attribute mustNotCopyVidOnWire : Boolean = true;
    attribute mustNotCopyUniquePageNameLaw : Boolean = true;
    attribute mustNotCopyEmbeddingsAsRecall : Boolean = true;
    attribute mustNotCopyGraphLiteAsProduct : Boolean = true;
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
  }

  part cousinPointing : CousinPointingContrast;
}
