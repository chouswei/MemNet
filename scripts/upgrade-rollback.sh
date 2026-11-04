#!/usr/bin/env bash
# One-step rollback of a memnet-serve upgrade (docs/operations/safe-upgrade.md, "Rollback").
#
#   scripts/upgrade-rollback.sh --live-venv /opt/memnet/venv --old-venv /opt/memnet/venv-0.20.4 \
#     --state-dir /var/lib/memnet --saved /var/lib/memnet.pre-upgrade \
#     --stop 'systemctl stop memnet-serve' --start 'systemctl start memnet-serve'
#
# Stops the serve, sets the current state dir aside as <state-dir>.rolled-back-<UTC stamp>
# (nothing is deleted), copies the saved pre-upgrade state dir back with its upgrade
# manifest un-retired, points the live venv link at the old venv, starts the serve, and
# waits for its upgrade-restore.json: every saved session restored and none failed.
# Exit 0 ok, 2 refused before anything changed (or the stop command failed), 3 not restored.
set -euo pipefail

live="" old="" state="" saved="" stop_cmd="" start_cmd="" wait_s=60

die() { # code kind detail
  echo "@ERR: upgrade_rollback|$2|$3" >&2
  exit "$1"
}

while [ $# -gt 0 ]; do
  case "$1" in
    --live-venv) live="$2" ;;
    --old-venv) old="$2" ;;
    --state-dir) state="$2" ;;
    --saved) saved="$2" ;;
    --stop) stop_cmd="$2" ;;
    --start) start_cmd="$2" ;;
    --wait-s) wait_s="$2" ;;
    *) die 2 usage "unknown argument $1" ;;
  esac
  shift 2 || die 2 usage "missing value for $1"
done

for name in live old state saved stop_cmd start_cmd; do
  [ -n "${!name}" ] || die 2 usage "--${name//_/-} is required"
done
[ -L "$live" ] || die 2 live_venv "$live is not a symlink"
py="$old/bin/python"
[ -x "$py" ] || die 2 old_venv "$py is not executable"
[ -d "$state" ] || die 2 state_dir "$state is not a directory"
manifest="$saved/upgrade-manifest.json"
expected=$("$py" -I -c '
import json, sys
m = json.load(open(sys.argv[1], encoding="utf-8"))
assert m.get("ready_to_stop") is True
print(len(m["sessions"]))
' "$manifest" 2>/dev/null) || die 2 saved "$manifest is missing or not a ready-to-stop manifest"

sh -c "$stop_cmd" || die 2 stop "stop command failed; nothing changed"

aside="$state.rolled-back-$(date -u +%Y%m%dT%H%M%SZ)"
mv -- "$state" "$aside"
cp -a -- "$saved" "$state"
rm -f -- "$state/upgrade-restore.json"
"$py" -I -c '
import json, os, sys
path = sys.argv[1]
m = json.load(open(path, encoding="utf-8"))
m["retired"] = False
m.pop("retired_at", None)
tmp = path + ".tmp"
with open(tmp, "w", encoding="utf-8") as fh:
    fh.write(json.dumps(m, indent=2, sort_keys=True) + "\n")
os.replace(tmp, path)
' "$state/upgrade-manifest.json"
ln -sfn -- "$old" "$live.rollback-tmp"
mv -T -- "$live.rollback-tmp" "$live"
echo "@STAT: upgrade_rollback_moved|$aside"

sh -c "$start_cmd" || die 3 start "start command failed"

report="$state/upgrade-restore.json"
deadline=$((SECONDS + wait_s))
until [ -s "$report" ]; do
  [ "$SECONDS" -lt "$deadline" ] || die 3 timeout "no $report after ${wait_s}s"
  sleep 0.2
done
"$py" -I -c '
import json, sys
r = json.load(open(sys.argv[1], encoding="utf-8"))
sys.exit(0 if int(r.get("ok", -1)) == int(sys.argv[2]) and int(r.get("failed", 1)) == 0 else 1)
' "$report" "$expected" || die 3 restore "expected $expected sessions; see $report"
echo "@STAT: upgrade_rollback|ok|$expected"
