# Serve concurrency under desk load (design note, no code)

Status: proposal for the owner and Elon. Nothing here is built. Origin: Atelier task
r00001830 (SysMLEdge desk reproject takes 70-94 s of engine time and a second
connection times out). Numbers are from `perf/reproject` on a dev box, not the Pi;
the shape of the result carries over, the absolute seconds do not.

## 1. Today's model (read from the code)

- `memnet serve` (TCP) is `socketserver.ThreadingTCPServer`: one thread per connection,
  one request per connection (`serve.py` `_Handler`, `_Server`). The IPC gateway shares
  the same `_handle_request`.
- Locks: one `RLock` per session (`registry.SessionEntry.lock`, taken in
  `Session.lock`; the `exclusive` flag is ignored, so a read and a write on the same
  session also queue), a process-wide `_registry_lock` held only for dict access, a
  `_cap_lock` for the session-cap and eviction pick, a `_checkpoint_lock` (one
  checkpoint at a time), and the upgrade `drain_gate`.
- `purge_expired` runs at the start of every request but only try-locks other
  sessions (`_expire_drop_if_overdue` is non-blocking), so one session's long upload
  does not block another session's request at the lock level. Side effect: an
  unrelated request pays for any overdue session's expire-save snapshot IO.
- CPython GIL: all request work is pure Python in one process, so threads on
  different sessions do not run in parallel; they interleave.
- The reply is written once, after the work finishes. There is no byte on the socket
  while a request runs. The client's 30 s socket idle timeout therefore fires on any
  request that takes longer than 30 s, however healthy the engine is.
- The "one heavy job at a time" in the desk analysis is the face's heavy gate (one
  worker, 60 s wait), not the engine.

## 2. What was measured (dev box, synthetic desk-shaped model, 8,230 lines in 1,000-line mutate batches)

| Case | Result |
|---|---|
| One upload, before the hotspot fixes | 81.5 s (nodes 4.3 s per batch, edges about 18 s per batch) |
| One upload, after (PR on `perf/reproject`) | 4.9 s |
| Two uploads at once on two sessions (after) | 10.5 s and 10.6 s each, against 4.9 s solo |
| Checkpoint serialise of one 8,230-row session | 0.13 s |
| Tiny read on another session during that serialise | 0.07 s median (0.03 s idle) |

Two overlapping heavy requests each take about twice as long: the work is shared, not
parallel. With the Pi's 70-94 s per reproject, a second heavy request waits 70-190 s
before it gets a reply, and the client gives up at 30 s of silence. That matches the
`memnet TCP timeout` failures in the desk logs, without any lock being involved.

## 3. Options

| Option | What it does | Fixes | Cost / risk |
|---|---|---|---|
| A. Fewer CPU seconds per request | The hotspot PR (parse-shape cache, `match_nodes` loop); next an id index so edge ends are O(1) | Everything, linearly; shrinks every window below 30 s | Smallest. Index needs every field-write path to keep it consistent |
| B. Per-session locks only (today) | Keep as is | Correctness | Does not help CPU-bound overlap under the GIL |
| C. Worker pool of processes, sessions pinned to a worker | Real parallelism across sessions | Throughput on 4 cores | Largest change: sessions live in RAM in one process; cross-session ops (cap, eviction, checkpoint, import_slice) need routing; snapshot/restore semantics must hold |
| D. Fair admission queue with a queued ack | Server reads the frame, replies at once with `@STAT: queued|pos|eta` (or writes a heartbeat byte), then the result | Silent timeouts; the client can tell busy from dead | Wire change: a new first frame or heartbeat, and the face client must accept it. Old clients must still work |
| E. Server-side busy reply with retry-after | Over a threshold of in-flight heavy requests, answer `@ERR: busy|retry_after_s=N` immediately (same shape as `serve_draining`) | Fast failure, no silent wait | Client must retry; needs a definition of "heavy" (batch lines, op) |
| F. Keepalive while working | A side thread writes a progress byte every few seconds on connections whose request is running | Client idle timeout | Needs a framing that tolerates leading progress bytes |

Suggested order: A (done in part), then E or D, which is a small, additive wire change
and removes the silent 30 s cliff; F only if D is too invasive for the face client. C
only if A through E are not enough on the Pi, because the memory model makes it
costly. This is an architecture call for the owner and Elon.

## 4. Does checkpoint block serving? (the 10-28 07:18 BACKEND_UNREACHABLE)

From the code, a checkpoint holds `_checkpoint_lock` (only other checkpoints wait on
it), refuses if the drain gate is not open, and takes each session's lock only while
`snapshot_text` copies that session; the file write happens outside the session
lock. The measurement above: 0.13 s for an 8,230-row session, and an unrelated tiny
read during it took 0.07 s. A request on the same session waits at most that long.
A checkpoint of a few such sessions on the Pi is likely well under a few seconds.

So checkpoint holding a lock long enough to cause BACKEND_UNREACHABLE is not
supported by the code or the measurement. It stays unverified for that event: there is
no Pi journal for 07:18 on 10-28 (journald is volatile, history starts at the 10-27
16:30 boot), and no per-request engine log yet (PR #229 adds one). Candidates to check
with the Pi's logs and the request log once it runs: a service restart or
`upgrade-prepare` drain at that time (draining answers `serve_draining`, a connect gap
during restart answers as unreachable), a long reproject occupying the CPU through the
GIL while the health probe waited, or a checkpoint running with a very large session.
