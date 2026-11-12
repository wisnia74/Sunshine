#!/bin/bash
# shot.sh [SCALE]: PNG of what the stream's Sway output shows right now, on stdout (default half size).
. "$(dirname "$0")/sway-env.sh"
exec grim -s "${1:-0.5}" -
