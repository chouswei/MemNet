# Per-request serve log

## Purpose

When two heavy requests overlapped, the serve engine left no trace, and clients hit the 30 s timeout without anyone seeing why. The per-request log records one line for each request, so overlap, queueing and slow commands can be found afterwards.

The log is off by default.

## Enable

```sh
memnet serve --request-log PATH
```

or set the environment variable:

```sh
MEMNET_REQUEST_LOG=PATH
```

On the Pi the journal is RAM-only, so the journal does not persist. Use a file under the user's state directory. Create the directory first:

```sh
mkdir -p "$HOME/.local/state/memnet"
MEMNET_REQUEST_LOG=$HOME/.local/state/memnet/request.jsonl
```

### Rotation

The file rotates by size.

- `MEMNET_REQUEST_LOG_MAX_BYTES`: rotate when the file reaches this size. Default `10485760` (10 MiB).
- `MEMNET_REQUEST_LOG_BACKUPS`: number of old files kept. Default `3`, giving `PATH.1` to `PATH.3`.

## Fields

Each line is one JSON object.

| Field | Meaning |
|---|---|
| `received_ms` | Epoch milliseconds when the request frame was received. |
| `finished_ms` | Epoch milliseconds when the reply was sent. |
| `queue_wait_ms` | Time from the frame being fully read until the command starts. Includes gate waits. |
| `server_ms` | Time from the command start until the reply is ready. |
| `op` | Command words only, for example `session open` or `mutate`. Never arguments. |
| `session` | One-way label: `s_` plus 8 hex digits of the session id. The engine has no session names, and the real `mn_` id is never written. |
| `bytes_in` | Bytes received in the request. |
| `bytes_out` | Bytes sent in the reply. |
| `lines_in` | Lines on stdin for the request. |
| `lines_out` | Lines on stdout for the reply. |
| `nodes_touched` | Currently always `null`. The dispatch layer does not know this. |
| `outcome` | `ok`, an `@ERR` code, `error`, `peer_gone` or `incomplete_frame`. |
| `conn_id` | Per-connection counter. |
| `seq` | Request number on that connection. Always `1` today, because the protocol is one request per connection. |

## Notes

- A line is written after the reply is sent.
- Sink errors are swallowed. One warning is logged.
- Bare connects, such as probes, are not logged.
- No payload text, tokens or ids are written.
- The log applies to TCP `serve` and to `serve --ipc`, which use the same handler.
- `memnet-mcp` over HTTP reaches the engine through this `serve` when it uses TCP, so those requests are logged. In-process MCP mode does not go through `serve` and is not logged.

## Sample line

```json
{"received_ms":1793000000123,"finished_ms":1793000031456,"queue_wait_ms":1204,"server_ms":30120,"op":"mutate","session":"s_3f9a1c2e","bytes_in":18342,"bytes_out":211,"lines_in":96,"lines_out":3,"nodes_touched":null,"outcome":"ok","conn_id":57,"seq":1}
```

## Finding overlaps

Requests that waited more than a second in the queue:

```sh
jq -c 'select(.queue_wait_ms>1000)' request.jsonl
```
