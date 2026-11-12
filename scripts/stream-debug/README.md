# Stream debugging scripts

Tools for measuring and testing the stream from the host's side: a scripted test scene, sweeps of encoder settings, test builds, and the timing of frames as they leave the network card. They were written for Sunshine running in a headless Sway session and streaming to Moonlight on a Samsung Tizen TV. The TV-side tools are in the moonlight-tizen fork under `tools/stream-debug/`, and `key-exp.sh` calls them.

## Setup

Copy `.env.example` to `.env` and set `STEAM_DIR`. Git ignores `.env`.

Two environment variables override defaults:

- `STREAM_DEBUG_OUT`: where the scripts write their output. Default `/tmp/stream-debug`.
- `MOONLIGHT_TOOLS`: the moonlight-tizen fork's `tools/stream-debug` folder. Default: the sibling clone, `../../../moonlight-tizen/tools/stream-debug` from here.

Run the Python scripts with `python3 -I`.

## Scripts

| Script | What it does |
|---|---|
| `testapp.py` | A test scene for the stream's Sway session. It pans a detailed picture at a scripted frame rate, can add GPU load, and marks a frame when a button is pressed, so a measurement can be repeated. |
| `scene.sh` | Starts `testapp.py` detached in the Sway session; `scene.sh stop` stops it. `--still` holds the picture still, which is where keyframes show most. |
| `sway-env.sh` | Sourced by the other scripts. Exports the Sway session's environment, taken from the running Sunshine. |
| `shot.sh` | Writes a PNG of what the stream shows to stdout. |
| `varfps-game.sh` | Starts a Steam game in the Sway session with a MangoHud frame cap that can change while the game runs. |
| `setfps.sh` | Changes that cap. |
| `swing.sh` | Steps the cap through a fixed pattern, to test a game whose frame rate keeps changing. |
| `sunshine-test-build.sh` | Builds the checked-out branch as the image `wisnia74/sunshine:TAG` and copies out its `.deb`. It leaves `artifacts/` and the installed build's image alone. |
| `sun-swap.sh` | Stops the running Sunshine and runs another binary in its place with the same environment, such as one unpacked from a test `.deb`. `sun-swap.sh installed` goes back. |
| `key-exp.sh` | Restarts Sunshine with each set of `sunshine.conf` settings in turn and measures each test scene on the TV. It puts `sunshine.conf` back when it finishes or is interrupted. |
| `burstdur.py` | Times how long each video frame takes to leave the network card and prints the qdisc's backlog and drop counters, to check the pacing toward the TV. |
