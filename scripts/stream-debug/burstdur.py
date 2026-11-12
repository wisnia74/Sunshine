"""burstdur.py SECS: how long each video frame takes to leave eno1 (first to last byte), from the tx byte
counter. Lists every frame that took over 12 ms and the qdisc backlog/drop counters before and after."""
import sys, time, subprocess
dur = float(sys.argv[1]); GAP = 1.2e-3
def tc(): return subprocess.run(["tc", "-s", "qdisc", "show", "dev", "eno1"], capture_output=True, text=True).stdout
before = tc()
f = open('/sys/class/net/eno1/statistics/tx_bytes')
def rd():
    f.seek(0); return int(f.read())
ev = []; last = rd(); t0 = time.perf_counter(); end = t0 + dur
while True:
    t = time.perf_counter()
    if t > end: break
    b = rd()
    if b != last: ev.append((t, b - last)); last = b
bur = []
for t, d in ev:
    if bur and t - bur[-1][1] < GAP: bur[-1][1] = t; bur[-1][2] += d
    else: bur.append([t, t, d])
fr = [b for b in bur if b[2] >= 5000]
ds = sorted((b[1] - b[0]) * 1000 for b in fr)
print(f"frames {len(fr)}; send duration ms p50 {ds[len(ds)//2]:.1f} p90 {ds[len(ds)*9//10]:.1f} p99 {ds[len(ds)*99//100]:.1f} max {ds[-1]:.1f}")
long = [(round((b[0]-t0)*1000), round((b[1]-b[0])*1000, 1), b[2]) for b in fr if (b[1]-b[0]) > 0.012]
print(f"frames taking >12 ms to send: {len(long)} [at ms, ms, bytes]:", long[:40])
print("\n".join(l for l in (before + "---after\n" + tc()).splitlines() if "Sent" in l or "backlog" in l or "---" in l or "qdisc" in l))
