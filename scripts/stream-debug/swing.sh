#!/bin/bash
# swing.sh SECS: step the test game's frame cap through a fixed pattern, one step every 3 s
end=$((SECONDS + $1))
while :; do for f in 120 60 90 45 120 75 60 100 40 120; do
  [ $SECONDS -ge $end ] && { "$(dirname "$0")/setfps.sh" 120; exit; }
  "$(dirname "$0")/setfps.sh" $f; sleep 3
done; done
