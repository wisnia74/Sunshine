#!/bin/bash
# varfps-game.sh APPID GAME/EXECUTABLE [FPS]: starts a Steam game from $STEAM_DIR/steamapps/common inside the stream's
# Sway session, with a MangoHud frame cap (default 120) that setfps.sh changes while the game runs. MangoHud reads
# its config file again when the file changes. Steam must already run in the session, because the game's Steam API
# connects to it, and APPID tells the API which game this is.
. "$(dirname "$0")/sway-env.sh"
[ -f "$(dirname "$0")/.env" ] && . "$(dirname "$0")/.env"
: "${STEAM_DIR:?set STEAM_DIR in .env}"
[ $# -ge 2 ] || { echo "usage: varfps-game.sh APPID GAME/EXECUTABLE [FPS]"; exit 2; }
O=${STREAM_DEBUG_OUT:-/tmp/stream-debug}; mkdir -p "$O"
printf 'fps_limit=%s\nno_display\n' "${3:-120}" > /tmp/mh-test.conf
exe=$STEAM_DIR/steamapps/common/$2
cd "$(dirname "$exe")" || exit 1
env -u MANGOHUD_CONFIG MANGOHUD_CONFIGFILE=/tmp/mh-test.conf SteamAppId="$1" SteamGameId="$1" \
  setsid mangohud "./$(basename "$exe")" >"$O/game.log" 2>&1 </dev/null &
