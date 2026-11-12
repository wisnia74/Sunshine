"""testapp.py --schedule 'FPS:SECS,FPS:SECS,...' [--secs N] [--log FILE] [--detail X] [--marker freeze|flat]
              [--driver x11|wayland] [--button CODE] [--flicker] [--still]

Throwaway test scene for the stream's Sway session (source sway-env.sh first). Draws a panning, detailed
scene with its own frame cap, following the schedule in a loop. Reads Sunshine's virtual Xbox 360 pad
from its evdev node and, on each press of --button (default 304, A), makes the next frame a marker:
'freeze' repeats the previous frame (encodes to almost nothing), 'flat' fills the screen with one colour.
At exit it writes every frame time, press and marker to --log, in CLOCK_MONOTONIC ms.
Uses libSDL2 and libGL through ctypes, because the homelab has neither dev headers nor Python bindings."""
import argparse, ctypes as C, fcntl, gc, json, os, signal, struct, time

ap = argparse.ArgumentParser()
ap.add_argument("--schedule", default="120:10")
ap.add_argument("--secs", type=float, default=0, help="stop after this long (0: until SIGTERM)")
ap.add_argument("--log", default="/tmp/testapp.json")
ap.add_argument("--detail", type=float, default=1.0)
ap.add_argument("--marker", default="freeze", choices=["freeze", "flat"])
ap.add_argument("--driver", default="x11")
ap.add_argument("--button", type=int, default=304)
ap.add_argument("--rumble", type=float, default=0, help="play a rumble effect on the pad this many times a second")
ap.add_argument("--load", type=float, default=0, help="extra shader work per pixel (noise lookups), to load the GPU like a game")
ap.add_argument("--flicker", action="store_true", help="two squares lit on alternate frames, to see whether the display shows every frame")
ap.add_argument("--still", action="store_true", help="hold the background still, so that only the line and the disc move: a picture the encoder keeps refining")
a = ap.parse_args()
sched = [(float(f), float(s)) for f, s in (x.split(":") for x in a.schedule.split(","))]

os.environ["SDL_VIDEODRIVER"] = a.driver
sdl = C.CDLL("libSDL2-2.0.so.0"); gl = C.CDLL("libGL.so.1")
sdl.SDL_CreateWindow.restype = C.c_void_p
sdl.SDL_CreateWindow.argtypes = [C.c_char_p, C.c_int, C.c_int, C.c_int, C.c_int, C.c_uint32]
sdl.SDL_GL_CreateContext.restype = C.c_void_p; sdl.SDL_GL_CreateContext.argtypes = [C.c_void_p]
sdl.SDL_GL_SwapWindow.argtypes = [C.c_void_p]
sdl.SDL_GL_GetDrawableSize.argtypes = [C.c_void_p, C.POINTER(C.c_int), C.POINTER(C.c_int)]
sdl.SDL_GetError.restype = C.c_char_p
gl.glGetUniformLocation.argtypes = [C.c_uint, C.c_char_p]
gl.glUniform1f.argtypes = [C.c_int, C.c_float]; gl.glUniform2f.argtypes = [C.c_int, C.c_float, C.c_float]
gl.glVertex2f.argtypes = [C.c_float, C.c_float]

if sdl.SDL_Init(0x20) != 0: raise SystemExit("SDL_Init: " + sdl.SDL_GetError().decode())
win = sdl.SDL_CreateWindow(b"stream-testapp", 0, 0, 2560, 1440, 0x2 | 0x1000)  # OPENGL | FULLSCREEN_DESKTOP
if not win: raise SystemExit("SDL_CreateWindow: " + sdl.SDL_GetError().decode())
if not sdl.SDL_GL_CreateContext(win): raise SystemExit("SDL_GL_CreateContext: " + sdl.SDL_GetError().decode())
sdl.SDL_GL_SetSwapInterval(0)

FRAG = b"""#version 120
uniform float t; uniform vec2 res; uniform float detail; uniform float flatc; uniform float parity; uniform float load; uniform float pan;
float hash(vec2 p) { return fract(sin(dot(p, vec2(127.1, 311.7))) * 43758.5453); }
float noise(vec2 p) { vec2 i = floor(p), f = fract(p); f = f * f * (3.0 - 2.0 * f);
  return mix(mix(hash(i), hash(i + vec2(1, 0)), f.x), mix(hash(i + vec2(0, 1)), hash(i + vec2(1, 1)), f.x), f.y); }
void main() {
  if (flatc > 0.5) { gl_FragColor = vec4(0.5, 0.5, 0.5, 1.0); return; }
  vec2 uv = gl_FragCoord.xy / res.y;
  vec2 p = uv * 5.0 + pan * vec2(t * 1.2, sin(t * 0.6) * 0.9);
  float n = 0.0, amp = 0.5; vec2 q = p;
  for (int i = 0; i < 7; i++) { n += amp * noise(q); q = q * 2.07 + 13.0; amp *= 0.5; }
  // --load: extra noise octaves that change nothing visible, to keep the GPU as busy as a real game does
  float burn = 0.0; for (int k = 0; k < 4000; k++) { if (float(k) >= load) break; burn += noise(q + float(k)); }
  n += burn * 1e-9;
  float fine = noise(p * 220.0) - 0.5;
  vec3 col = mix(vec3(0.08, 0.16, 0.30), vec3(0.95, 0.78, 0.45), smoothstep(0.25, 0.75, n));
  col += detail * 0.22 * fine;
  float x = fract(t * 0.25) * res.x / res.y;
  col = mix(col, vec3(1.0), step(abs(uv.x - x), 0.012));
  vec2 c = vec2(0.5 * res.x / res.y, 0.5) + 0.3 * vec2(cos(t * 2.0), sin(t * 2.0));
  col = mix(col, vec3(0.9, 0.15, 0.1), step(length(uv - c), 0.05));
  // --flicker: two squares lit on alternate frames. Shown at the full frame rate both look the same grey;
  // a display that shows every other frame leaves one white and one black.
  if (parity >= 0.0) {
    vec2 m = vec2(0.5 * res.x / res.y, 0.5);
    if (abs(uv.y - m.y) < 0.2 && abs(abs(uv.x - m.x) - 0.3) < 0.2) col = vec3(uv.x < m.x ? 1.0 - parity : parity);
  }
  gl_FragColor = vec4(col, 1.0);
}"""
def shader(kind, src):
    s = gl.glCreateShader(kind); p = C.c_char_p(src)
    gl.glShaderSource(s, 1, C.byref(p), None); gl.glCompileShader(s)
    ok = C.c_int(); gl.glGetShaderiv(s, 0x8B81, C.byref(ok))
    if not ok.value:
        buf = C.create_string_buffer(4096); gl.glGetShaderInfoLog(s, 4096, None, buf); raise SystemExit(buf.value.decode())
    return s
prog = gl.glCreateProgram()
gl.glAttachShader(prog, shader(0x8B31, b"#version 120\nvoid main() { gl_Position = gl_Vertex; }"))
gl.glAttachShader(prog, shader(0x8B30, FRAG)); gl.glLinkProgram(prog); gl.glUseProgram(prog)
u_t, u_res, u_detail, u_flat, u_par = (gl.glGetUniformLocation(prog, n) for n in (b"t", b"res", b"detail", b"flatc", b"parity"))
u_load = gl.glGetUniformLocation(prog, b"load"); u_pan = gl.glGetUniformLocation(prog, b"pan")

# ---- the pad, straight from evdev ----
EVENT = struct.Struct("llHHi"); EVIOCSCLOCKID = 0x400445A0
def find_pad():
    block = {}
    for line in open("/proc/bus/input/devices").read().split("\n") + [""]:
        if line.startswith("I:"): block = {"id": line}
        elif line.startswith("H:"): block["h"] = line.split("=", 1)[1].split()
        elif not line and block:
            if "Vendor=045e" in block.get("id", "") and any(h.startswith("js") for h in block.get("h", [])):
                return "/dev/input/" + next(h for h in block["h"] if h.startswith("event"))
            block = {}
    return None
pad = None; pad_scan = 0.0; ff_id = None
def open_pad():
    global pad, ff_id
    path = find_pad()
    if not path: return
    try:
        pad = os.open(path, os.O_RDWR | os.O_NONBLOCK)
        fcntl.ioctl(pad, EVIOCSCLOCKID, struct.pack("i", 1))
        ff_id = None
        if a.rumble:
            # struct ff_effect, FF_RUMBLE: type, id, direction, trigger(2x u16), replay(length, delay), pad, rumble(strong, weak)
            eff = bytearray(struct.pack("HhHHHHHxx" "HH" "28x", 0x50, -1, 0, 0, 0, 120, 0, 0x6000, 0x6000))
            fcntl.ioctl(pad, 0x40304580, eff)  # EVIOCSFF
            ff_id = struct.unpack_from("h", eff, 2)[0]
    except OSError as e:
        print("pad:", e, flush=True); pad = None

run = True
def stop(*_):
    global run
    run = False
signal.signal(signal.SIGTERM, stop); signal.signal(signal.SIGINT, stop)

now = time.monotonic
frames = []; presses = []; markers = []; pad_events = 0; rumbles = 0
w, h = C.c_int(), C.c_int(); ev = C.create_string_buffer(64)
gc.disable()
start = now(); seg = 0; seg_end = start + sched[0][1]; target = start; scene_t = 0.0; last = start
pending = []; next_rumble = start + 1
while run:
    t = now()
    if a.secs and t - start >= a.secs: break
    if t >= seg_end:
        seg = (seg + 1) % len(sched); seg_end = t + sched[seg][1]
    target += 1.0 / sched[seg][0]
    if target < t - 0.05: target = t           # fell far behind: start the cadence over
    d = target - now()
    if d > 0.0004: time.sleep(d - 0.0003)
    while now() < target: pass
    while sdl.SDL_PollEvent(ev):
        if C.cast(ev, C.POINTER(C.c_uint32))[0] == 0x100: run = False
    if pad is None and now() - pad_scan > 1: pad_scan = now(); open_pad()
    if pad is not None:
        try:
            data = os.read(pad, EVENT.size * 64)
            rd = now() * 1000
            for i in range(0, len(data), EVENT.size):
                sec, usec, etype, code, value = EVENT.unpack_from(data, i)
                if etype in (1, 3): pad_events += 1
                if etype == 1 and code == a.button and value == 1: pending.append([sec * 1000 + usec / 1000, rd])
        except BlockingIOError: pass
        except OSError: os.close(pad); pad = None
        if ff_id is not None and now() >= next_rumble:
            next_rumble = now() + 1.0 / a.rumble
            try: os.write(pad, EVENT.pack(0, 0, 0x15, ff_id, 1)); rumbles += 1
            except OSError: pass
    mark = bool(pending)
    t = now()
    if not (mark and a.marker == "freeze"): scene_t += t - last
    last = t
    sdl.SDL_GL_GetDrawableSize(win, C.byref(w), C.byref(h)); gl.glViewport(0, 0, w, h)
    gl.glUniform1f(u_t, scene_t); gl.glUniform2f(u_res, float(w.value), float(h.value))
    gl.glUniform1f(u_detail, a.detail); gl.glUniform1f(u_flat, 1.0 if mark and a.marker == "flat" else 0.0)
    gl.glUniform1f(u_load, a.load); gl.glUniform1f(u_pan, 0.0 if a.still else 1.0)
    gl.glUniform1f(u_par, float(len(frames) % 2) if a.flicker else -1.0)
    gl.glBegin(4); gl.glVertex2f(-1, -1); gl.glVertex2f(3, -1); gl.glVertex2f(-1, 3); gl.glEnd()
    sdl.SDL_GL_SwapWindow(win)
    done = now() * 1000
    frames.append(done)
    if mark:
        for p in pending: presses.append(p + [done, len(frames) - 1])
        markers.append(len(frames) - 1); pending = []

json.dump({"start": start * 1000, "size": [w.value, h.value], "schedule": sched, "marker": a.marker, "frames": frames,
           "presses": presses, "padEvents": pad_events, "rumbles": rumbles}, open(a.log, "w"))
print(f"{len(frames)} frames in {now() - start:.1f}s, {len(presses)} presses, {pad_events} pad events, {rumbles} rumbles, {w.value}x{h.value}", flush=True)
