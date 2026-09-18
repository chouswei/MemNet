/*
  ARCHIVE shelf — leftover / retired fog. Honesty, not product nest.

  MUST NOT appear in sysml-models/config.yaml model_files.
  ProjectMemNet (root.sysml) MUST NOT import MemNetArchive.
  Teach path is GqlCodec + ProductGqlGate.rejectLayer. Do not sell
  Layer / Tier A / dashboard-as-API as product.

  Open this file when auditing leftovers. Do not delete history.
*/
package MemNetArchive {
  private import ScalarValues::*;

  attribute mustNotImportFromProjectMemNet : Boolean = true;
  attribute leftoverArchiveOffLoad : Boolean = true;
  attribute productTeach : Boolean = false;

  // =====================================================================
  // Retired Layer / Tier A / LegacyPipe item zoo (was connections.sysml)
  // =====================================================================

  item def LegacyLayerBatch {
    doc /*
      RETIRED archive — former Layer / Tier A NODE|EDGE ASCII (MemNetLayer.g4 /
      tier_a). Product accept REJECTED (M2 done; legacy_dialect_retired).
      MUST NOT be agent teach or nested on product path. Alias: TierABatch.
      Modules may remain for archive/tests only.
    */
  }

  item def LegacyPipeBatch {
    doc /*
      RETIRED archive — one-shot import of historical @TAG pipe session blobs.
      Not a standing store codec or agent dialect. MUST NOT nest on product path.
    */
  }

  port def TierAOutPort {
    doc /* RETIRED archive: former Tier A emit — MUST NOT nest on product path. */
    out item payload : LegacyLayerBatch;
  }
  port def TierAInPort {
    doc /* RETIRED archive: former Tier A consume — MUST NOT nest on product path. */
    in item payload : LegacyLayerBatch;
  }

  port def LegacyPipeOutPort {
    doc /* RETIRED archive: legacy pipe emit — MUST NOT nest on product path. */
    out item payload : LegacyPipeBatch;
  }
  port def LegacyPipeInPort {
    doc /* RETIRED archive: legacy pipe consume — MUST NOT nest on product path. */
    in item payload : LegacyPipeBatch;
  }

  connection def TierAFlow {
    doc /* RETIRED archive flow — MUST NOT nest on product path (M2 done). */
    end port source : TierAOutPort;
    end port sink : TierAInPort;
  }

  connection def LegacyPipeFlow {
    doc /* RETIRED archive: one-shot legacy pipe import — MUST NOT nest on product path. */
    end port source : LegacyPipeOutPort;
    end port sink : LegacyPipeInPort;
  }

  // =====================================================================
  // leftover_* invented-store honesty (was nested under Schema / GraphStore)
  // =====================================================================

  part def leftover_id_first {
    doc /* 0.9 leftover SCHEMA id_first. Archive shelf; not SchemaRegistry nest. */
    attribute leftoverAsIsEngine : Boolean = true;
    attribute leftoverIssue : String = "id_first";
    attribute productCommand : Boolean = false;
  }

  part def leftover_by_id {
    doc /* 0.9 leftover MemStore.by_id index. Archive shelf; not GraphStore nest. */
    attribute leftoverAsIsEngine : Boolean = true;
    attribute leftoverIssue : String = "by_id";
    attribute productCommand : Boolean = false;
    attribute targetImplemented : Boolean = false;
  }

  part def leftover_MERGE_by_id {
    doc /* 0.9 leftover MERGE-by-id as PK. Archive shelf; not GraphStore nest. */
    attribute leftoverAsIsEngine : Boolean = true;
    attribute leftoverIssue : String = "MERGE-by-id";
    attribute productCommand : Boolean = false;
    attribute targetImplemented : Boolean = false;
  }

  part def leftover_NEW_mint {
    doc /* 0.9 leftover NEW mint. Archive shelf; not IdAllocator nest. */
    attribute leftoverAsIsEngine : Boolean = true;
    attribute leftoverIssue : String = "NEW";
    attribute productCommand : Boolean = false;
    attribute targetImplemented : Boolean = false;
    attribute implemented : Boolean = true;
  }

  part def leftover_allocate_from_locator {
    doc /* 0.9 leftover PinMapIngest allocate_from_locator. Archive shelf. */
    attribute leftoverAsIsEngine : Boolean = true;
    attribute leftoverIssue : String = "locator-as-PK";
    attribute productCommand : Boolean = false;
    attribute targetImplemented : Boolean = false;
  }

  part def leftover_require_anchor {
    doc /*
      0.9 leftover pin_map require_anchor / by_id. Archive shelf.
      MUST NOT be the TARGET pin_map command.
    */
    attribute leftoverAsIsEngine : Boolean = true;
    attribute leftoverIssue : String = "require_anchor";
    attribute productCommand : Boolean = false;
    attribute targetImplemented : Boolean = false;
    attribute requireAnchorId : Boolean = true;
  }

  part def leftover_empty_seed_skip {
    doc /*
      leftover 0.10 empty Q skip ShapeWalk. Archive shelf.
      TARGET empty q is SessionOutline. MUST NOT be a product command.
    */
    attribute leftoverAsIsEngine : Boolean = true;
    attribute leftoverIssue : String = "empty-cue-skip";
    attribute productCommand : Boolean = false;
    attribute targetImplemented : Boolean = false;
  }

  part def leftover_ingestIsIdRule {
    doc /* 0.9 leftover ingestIsIdRule=true. TARGET Commit flag is false. */
    attribute leftoverAsIsEngine : Boolean = true;
    attribute leftoverIssue : String = "ingestIsIdRule";
    attribute productCommand : Boolean = false;
  }

  part def leftover_read_get {
    doc /*
      0.9 leftover MCP/CLI read_get(id) keyed on store-key. Archive shelf.
      MUST NOT nest under McpFacade / CliFacade as a product command.
    */
    attribute leftoverAsIsEngine : Boolean = true;
    attribute leftoverIssue : String = "read_get";
    attribute productCommand : Boolean = false;
    attribute implemented : Boolean = true;
    attribute targetImplemented : Boolean = false;
    attribute requiresStoreKeyId : Boolean = true;
  }

  part def leftover_AssignedIdMap {
    doc /*
      0.9 leftover required AssignedIdMap emit after NEW. Archive shelf.
      MUST NOT nest as a product command.
    */
    attribute leftoverAsIsEngine : Boolean = true;
    attribute leftoverIssue : String = "AssignedIdMap";
    attribute productCommand : Boolean = false;
    attribute implemented : Boolean = true;
    attribute targetImplemented : Boolean = false;
  }

  part def TierACodec {
    doc /*
      RETIRED / REJECTED on product path (ADR-001 M2 **done**): former Layer /
      Tier A NODE|EDGE ASCII (MemNetLayer.g4 / memnet.tier_a / memnet.layer).
      MutateGate rejects with legacy_dialect_retired. MUST NOT be nested as
      accept or 1.x teach. Hierarchical reconstruct (Recall k-hop) is NOT
      Layer dialect. Leftover retire-from-wheel: modules may remain on disk
      for archive/tests; MUST NOT silently delete. Primary wire is GqlCodec.
    */
    port tierAIn : TierAInPort;
    port tierAOut : TierAOutPort;
    attribute productPathRetired : Boolean = true;
    attribute mustNotNestOnProductPath : Boolean = true;
    attribute leftoverIssue : String = "retire-from-wheel";
    attribute deleteThisPr : Boolean = false;
  }

  part def LegacyPipeImport {
    doc /*
      RETIRED archive — MUST NOT nest on product path. One-shot import of
      historical @TAG pipe session blobs; convert then discard. Kept for
      as-is traceability only (not first-class product).
    */
    port legacyIn : LegacyPipeInPort;
    attribute implemented : Boolean = false;
  }

  part def LeftoverArchiveShelf {
    doc /*
      One shelf for leftover honesty. Not Schema. Not GraphStore.
      Not MemNetSystem. ProjectMemNet does not load this package.
    */
    part leftoverLayer : TierACodec;
    part leftoverPipe : LegacyPipeImport;
    part leftover_id_first : leftover_id_first;
    part leftover_by_id : leftover_by_id;
    part leftover_MERGE_by_id : leftover_MERGE_by_id;
    part leftover_NEW_mint : leftover_NEW_mint;
    part leftover_allocate_from_locator : leftover_allocate_from_locator;
    part leftover_require_anchor : leftover_require_anchor;
    part leftover_empty_seed_skip : leftover_empty_seed_skip;
    part leftover_ingestIsIdRule : leftover_ingestIsIdRule;
    part leftover_read_get : leftover_read_get;
    part leftover_AssignedIdMap : leftover_AssignedIdMap;
  }

  part leftoverArchiveShelf : LeftoverArchiveShelf;
}
