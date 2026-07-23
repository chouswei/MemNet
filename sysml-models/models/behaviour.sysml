/*
  Session lifecycle behaviour for MemNet (clarify open -> warm -> mutate -> save).
*/
package MemNetBehaviour {
  private import ScalarValues::*;

  attribute def EvOpenSession {
    doc /* session_open / CLI session open with TagMap. */
  }
  attribute def EvLoadSnapshot {
    doc /* session_load from SnapshotBlob. */
  }
  attribute def EvWarmRead {
    doc /* query_warm (or walk) against active session. */
  }
  attribute def EvMutateGraph {
    doc /* add or update wire batch (or delete/housekeep mutate). */
  }
  attribute def EvSaveSnapshot {
    doc /* session_save to file. */
  }
  attribute def EvCloseOrExpire {
    doc /* session_close or TTL purge. */
  }
  attribute def EvError {
    doc /* Hard error (@ERR) that aborts the current command without changing lifecycle state. */
  }

  state def SessionLifecycle {
    doc /*
      Logical lifecycle of one SessionStore entry in the serve registry.
      Hosted conceptually by MemNetServeDaemon / SessionRegistryService.
      Aligns with goldfish loop: warm -> act -> mutate -> settle -> warm.
    */
    entry;
    then closed;

    state closed {
      doc /* No session id; open or load required. */
    }
    transition closed_to_opening
      first closed
      accept EvOpenSession
      then opening;
    transition closed_to_loading
      first closed
      accept EvLoadSnapshot
      then loading;

    state opening {
      doc /* TagMap merge, SessionStore create, optional LAW seed. */
    }
    transition opening_to_active
      first opening
      accept EvWarmRead
      then active;
    transition opening_to_active_after_seed
      first opening
      accept EvMutateGraph
      then active;
    transition opening_to_closed_fail
      first opening
      accept EvError
      then closed;

    state loading {
      doc /* Parse snapshot sections into TagMap + records. */
    }
    transition loading_to_active
      first loading
      accept EvWarmRead
      then active;
    transition loading_to_closed_fail
      first loading
      accept EvError
      then closed;

    state active {
      doc /* Session usable: warm/walk, add/update, read_get, housekeep, save. */
    }
    transition active_warm
      first active
      accept EvWarmRead
      then active;
    transition active_mutate
      first active
      accept EvMutateGraph
      then active;
    transition active_to_saving
      first active
      accept EvSaveSnapshot
      then saving;
    transition active_to_closed
      first active
      accept EvCloseOrExpire
      then closed;
    transition active_error_stay
      first active
      accept EvError
      then active;

    state saving {
      doc /* Write SnapshotBlob; session remains open. */
    }
    transition saving_to_active
      first saving
      accept EvWarmRead
      then active;
    transition saving_to_active_done
      first saving
      accept EvMutateGraph
      then active;
    transition saving_to_closed
      first saving
      accept EvCloseOrExpire
      then closed;
  }
}
