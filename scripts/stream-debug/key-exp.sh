#!/bin/bash
# key-exp.sh TAG SECS OPTS 'SCENE...' SETTINGS...: one m.py measurement per set of Sunshine settings and test scene.
# SETTINGS is key=value[,key=value...] for sunshine.conf, e.g. nvenc_vbv_increase=0,nvenc_keyframe_scale=3.
# OPTS are the player options for tv.py up ('' for the build's own). Scenes: s120 s60 swing lo60 still60.
# SUN is the Sunshine binary that runs the settings (default: the installed build, through the service).
# Saves $OUT/TAG-SETTINGS-SCENE.json (default $STREAM_DEBUG_OUT/key-exp), readable with m.py why and an-key.py.
# sunshine.conf is put back as it was at the end, and Sunshine restarts on it.
cd "$(dirname "$0")"
M=${MOONLIGHT_TOOLS:-../../../moonlight-tizen/tools/stream-debug}
TAG=$1; SECS=$2; OPTS=$3; SCENES=$4; shift 4
SUN=${SUN:-installed}; OUT=${OUT:-${STREAM_DEBUG_OUT:-/tmp/stream-debug}/key-exp}; mkdir -p $OUT
CONF=~/.config/sunshine/sunshine.conf; BEFORE=$OUT/sunshine.conf.before-$$
say() { echo "[$(date +%T)] $*"; }
die() { say "FAILED: $*"; python3 -I $M/m.py pad off; exit 2; }
age() { python3 -I $M/insp.py 'Math.round(performance.now())'; }
scene() { case $1 in
  s120) bash scene.sh ;;
  s60) bash scene.sh --schedule 60:10 ;;
  swing) bash scene.sh --schedule 120:3,60:3,90:3,45:3,120:3,75:3,60:3,100:3,40:3 ;;
  lo60) bash scene.sh --schedule 60:10 --detail 0 ;;
  still60) bash scene.sh --schedule 60:10 --still ;;
  *) die "unknown scene $1" ;; esac; }
up() { if [ -n "$OPTS" ]; then python3 -I $M/tv.py up Desktop --opts "$OPTS"; else python3 -I $M/tv.py up Desktop --fresh; fi; }
restart() { python3 -I $M/tv.py down | tail -1; bash sun-swap.sh "$SUN" || die "Sunshine did not come back"; sleep 3; }

cp $CONF $BEFORE
# An interrupted run must not leave an experiment's settings in the file that the installed Sunshine reads.
trap 'cmp -s $BEFORE $CONF || { cp $BEFORE $CONF; say "sunshine.conf put back; the running Sunshine still holds the last settings"; }; rm -f $BEFORE $OUT/conf.next' EXIT

for C in "$@"; do
  cp $BEFORE $OUT/conf.next
  for kv in ${C//,/ }; do
    k=${kv%%=*}; v=${kv#*=}
    if grep -q "^$k = " $OUT/conf.next; then sed -i "s/^$k = .*/$k = $v/" $OUT/conf.next; else echo "$k = $v" >> $OUT/conf.next; fi
  done
  if ! cmp -s $OUT/conf.next $CONF || [ "$(readlink /proc/$(pgrep -x sunshine | head -1)/exe)" != "$(readlink -f ${SUN/#installed//usr/bin/sunshine})" ]; then
    cp $OUT/conf.next $CONF; restart
    say "Sunshine runs with $C"
  fi
  slug=$(echo "$C" | sed 's/nvenc_//g; s/=//g; s/,/-/g')
  for S in $SCENES; do
    scene $S || die "scene $S"
    up | tail -2
    a=$(age) || die "the page does not answer"
    # tv.py up can relaunch Moonlight. A stream that starts before page age 63 s is swapped to new threads
    # inside the window, so its numbers do not compare with a stream that started later.
    if [ "$a" -lt 66000 ]; then say "the page is $a ms old; waiting for 67 s"; sleep $(( (67000 - a) / 1000 + 1 )); up | tail -2; fi
    python3 -I $M/m.py pad play | tail -1
    sleep 8
    say "measuring $C $S"
    python3 -I $M/m.py $SECS --full --label "$C $S" --out $OUT/$TAG-$slug-$S.json | grep -v '^RESULT '
  done
done
python3 -I $M/m.py pad off; bash scene.sh stop; python3 -I $M/tv.py down | tail -1
if ! cmp -s $BEFORE $CONF; then cp $BEFORE $CONF; bash sun-swap.sh "$SUN" || die "Sunshine did not come back on the restored sunshine.conf"; fi
say EXP-DONE
