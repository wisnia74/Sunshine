# source this: exports the stream's Sway session environment, taken from the running Sunshine
p=$(pgrep -x sunshine | head -1)
for v in WAYLAND_DISPLAY DISPLAY XDG_RUNTIME_DIR SWAYSOCK DBUS_SESSION_BUS_ADDRESS; do
  val=$(tr '\0' '\n' < /proc/$p/environ | sed -n "s/^$v=//p"); [ -n "$val" ] && export $v="$val"
done
