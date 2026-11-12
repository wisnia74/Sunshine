#!/bin/bash
# scene.sh [testapp.py options] | scene.sh stop: (re)start the test scene in the stream's Sway session, detached.
# Fails at once when the scene does not come up. Default schedule 120:10; e.g. scene.sh --schedule 60:10 --load 800
cd "$(dirname "$0")"; . ./sway-env.sh
O=${STREAM_DEBUG_OUT:-/tmp/stream-debug}; mkdir -p "$O"
for p in $(pgrep -f 'testapp.py --log'); do kill $p; done
[ "$1" = stop ] && { echo "test scene stopped"; exit 0; }
sleep 0.4
nohup setsid python3 -I testapp.py --log "$O/scene.json" --secs 7200 --marker flat --button 999 "$@" >"$O/scene.out" 2>&1 </dev/null &
for n in 1 2 3 4 5 6 7 8; do sleep 0.4; swaymsg -t get_tree 2>/dev/null | grep -q stream-testapp && { echo "test scene up: $*"; exit 0; }; done
echo "FAILED: test scene did not open a window: $(tail -2 "$O/scene.out")"; exit 2
