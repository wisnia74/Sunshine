#!/bin/bash
# sun-swap.sh BINARY | installed: stop the running Sunshine and run BINARY in its place, with the same
# environment and working directory, or go back to the installed build. Ends any stream.
LOG=~/.config/sunshine/sunshine.log; OUT=${STREAM_DEBUG_OUT:-/tmp/stream-debug}/sun-swap.out
say() { echo "[$(date +%T)] $*"; }
die() { say "FAILED: $*"; exit 2; }
BIN=$1
[ "$BIN" = installed ] || [ -x "$BIN" ] || die "usage: sun-swap.sh BINARY | installed"
mkdir -p "$(dirname "$OUT")"

old=$(pgrep -x sunshine | head -1)
if [ "$BIN" != installed ]; then
  [ -n "$old" ] || die "no Sunshine is running to copy the environment from"
  mapfile -d '' -t ENVIRON < /proc/$old/environ
  cwd=$(readlink /proc/$old/cwd)
fi
if [ -n "$old" ]; then
  kill $old
  for n in $(seq 40); do kill -0 $old 2>/dev/null || break; sleep 0.25; done
  kill -0 $old 2>/dev/null && die "Sunshine $old did not exit within 10 s"
  say "stopped Sunshine $old"
fi

since=$(date '+%F %T')
if [ "$BIN" = installed ]; then
  # A Sunshine that this script started runs outside the service, so a restart of the service does not
  # stop it, and it keeps the ports that the installed one needs. That is why it is stopped first.
  systemctl --user restart sway-sunshine || die "sway-sunshine did not restart"
else
  cd "$cwd" || die "cannot enter $cwd"
  nohup setsid env -i "${ENVIRON[@]}" "$BIN" >$OUT 2>&1 </dev/null &
fi
up=
for n in $(seq 60); do
  sleep 0.5
  curl -s -m 1 http://127.0.0.1:47989/serverinfo | grep -q hostname && { up=1; break; }
done
[ -n "$up" ] || die "Sunshine did not answer within 30 s: $(tail -2 $OUT 2>/dev/null)"
new=$(pgrep -x sunshine | head -1)
ver=$(grep -a 'Sunshine version' $LOG | tail -1)
[[ "${ver:1:19}" < "$since" ]] && die "sunshine.log holds no version line from this start"
say "Sunshine $new is $(readlink /proc/$new/exe): ${ver#*Info: }"
