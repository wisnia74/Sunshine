#!/bin/bash
# setfps.sh N: change the test game's MangoHud frame cap (see varfps-game.sh)
printf 'fps_limit=%s\nno_display\n' "$1" > /tmp/mh-test.conf
