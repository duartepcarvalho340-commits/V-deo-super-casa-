"""Original score + synthesised SFX for the Meta Muse spec film; music ducks under the narration."""
import os, sys
import numpy as np, soundfile as sf
from scipy.signal import butter, sosfilt, fftconvolve, resample_poly
sys.path.insert(0, os.path.dirname(__file__))
from timing import DURATION, EVENTS as EV

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SR = 48000; N = int(DURATION * SR); T = np.arange(N) / SR
rng = np.random.default_rng(5)
midi = lambda m: 440 * 2 ** ((m - 69) / 12)
def env(n, a, d): t = np.arange(n) / SR; return np.minimum(1, t / max(a, 1e-4)) * np.exp(-t / d)
def lp(x, f): return sosfilt(butter(2, f, "low", fs=SR, output="sos"), x, axis=0)
def hp(x, f): return sosfilt(butter(2, f, "high", fs=SR, output="sos"), x, axis=0)
def bp(x, a, b): return sosfilt(butter(2, [a, b], "band", fs=SR, output="sos"), x, axis=0)
def place(buf, sig, t, g=1.0, pan=0.0):
    sig = np.asarray(sig)
    if sig.ndim == 1: sig = np.stack([sig * np.sqrt(.5 - pan / 2), sig * np.sqrt(.5 + pan / 2)], 1) * 1.414
    i = int(t * SR); j = min(N, i + len(sig))
    if 0 <= i < N: buf[i:j] += sig[:j - i] * g
def reverb(x, secs=2.2, mix=.25):
    n = int(secs * SR); tt = np.arange(n) / SR
    ir = lp(rng.standard_normal((n, 2)) * np.exp(-tt * 6.9 / secs)[:, None], 6500); ir /= np.sqrt((ir ** 2).sum(0))
    return x * (1 - mix) + np.stack([fftconvolve(x[:, c], ir[:, c])[:N] for c in range(2)], 1) * mix * 2.2
def saw(f, n, det=.006):
    t = np.arange(n) / SR; return sum(2 * ((t * f * (1 + d)) % 1) - 1 for d in (-det, 0, det)) / 3

# ---------------- score: airy, forward-moving, 116 BPM ----------------
BPM = 116; BEAT = 60 / BPM; BAR = 4 * BEAT
CH = [[62, 66, 69, 73], [59, 62, 66, 69], [55, 59, 62, 66], [57, 61, 64, 69]]  # Dmaj7 - Bm7 - Gmaj7 - A
BASS = [38, 35, 31, 33]
music = np.zeros((N, 2))
for b in range(int(DURATION / BAR) + 1):  # evolving pad
    n = int(BAR * SR * 1.15); s = sum(saw(midi(m), n) for m in CH[b % 4]) * np.minimum(1, np.arange(n) / SR / .6) * np.exp(-np.arange(n) / SR / 3.5)
    place(music, lp(s, 1200 + 600 * (b % 2)), b * BAR, .045)
t, k = 1.4, 0
arp = [0, 1, 2, 3, 2, 1, 3, 2]
while t < 19.3:  # glassy 16th arpeggio
    ch = CH[int(t // BAR) % 4]; m = ch[arp[k % 8]] + 12 + (12 if t > 13.2 else 0)
    n = int(.35 * SR); tt = np.arange(n) / SR
    s = (np.sin(2 * np.pi * midi(m) * tt) + .3 * np.sin(2 * np.pi * midi(m) * 3 * tt) * np.exp(-tt * 20)) * env(n, .002, .12)
    place(music, s, t, .1, pan=.5 * np.sin(k * .9)); t += BEAT / 4 * 2; k += 1
t = 3.0
while t < 19.3:  # sub pulse + soft kick + hats
    n = int(BEAT * .95 * SR); tt = np.arange(n) / SR
    place(music, np.sin(2 * np.pi * midi(BASS[int(t // BAR) % 4]) * tt) * env(n, .01, .3), t, .28)
    kk = int(.3 * SR); kt = np.arange(kk) / SR; place(music, np.sin(2 * np.pi * np.cumsum(50 + 80 * np.exp(-kt * 35)) / SR) * env(kk, .001, .12), t, .4)
    place(music, hp(rng.standard_normal(int(.04 * SR)), 8000) * env(int(.04 * SR), .0005, .01), t + BEAT / 2, .06)
    t += BEAT
n = int((DURATION - EV["brand"]) * SR); tt = np.arange(n) / SR
place(music, sum(np.sin(2 * np.pi * midi(m) * tt) * (1 if m < 70 else .5) for m in (50, 57, 62, 66, 69, 73, 76)) * np.minimum(1, tt / .08) * np.exp(-tt / 2.8) * .05, EV["brand"])
music = reverb(music, 2.4, .25)

# ---------------- SFX ----------------
sfx = np.zeros((N, 2))
def blip(f, d=.06): n = int(.3 * SR); tt = np.arange(n) / SR; return np.sin(2 * np.pi * f * tt) * env(n, .001, d)
def whoosh(dur=.5, f0=300, f1=4000):
    n = int(dur * SR); x = rng.standard_normal(n); out = np.zeros(n); seg = int(.01 * SR)
    for i in range(0, n, seg):
        f = f0 * (f1 / f0) ** (i / n); out[i:i + seg] = bp(x[max(0, i - 2048):i + seg], f * .7, min(f * 1.4, 20000))[-len(x[i:i + seg]):]
    return out * np.sin(np.pi * np.linspace(0, 1, n)) ** 2
def shimmer(ms, d=.7, gap=.06):
    n = int(1.4 * SR); tt = np.arange(n) / SR; out = np.zeros(n)
    for k, m in enumerate(ms):
        o = int(k * gap * SR); out[o:] += (np.sin(2 * np.pi * midi(m) * tt) * env(n, .003, d))[:n - o]
    return out
def key(): n = int(.05 * SR); return bp(rng.standard_normal(n), 2000, 7000) * env(n, .0005, .008)
# orb ignition
n = int(1.2 * SR); tt = np.arange(n) / SR; rise = np.sin(2 * np.pi * np.cumsum(120 + 500 * tt) / SR) * np.minimum(1, tt / .4) * np.exp(-tt / .5)
place(sfx, rise, 0.0, .12); place(sfx, shimmer([74, 81, 86], .9), .35, .1); place(sfx, whoosh(.7, 500, 6000), .45, .12)
for i in range(18): place(sfx, key(), EV["type_start"] + i * (EV["type_end"] - EV["type_start"]) / 18, .25, pan=rng.uniform(-.3, .3))
place(sfx, blip(900, .05) + .5 * blip(1350, .04), EV["send"], .25); place(sfx, whoosh(.5, 600, 5000), EV["send"], .12)
for k in ("flight_ok", "hotel_ok"): place(sfx, shimmer([81, 88], .4), EV[k], .12)
place(sfx, blip(700, .04), EV["email_send"], .25); place(sfx, whoosh(.7, 400, 7000), EV["email_send"] + .05, .2); place(sfx, shimmer([86], .4), EV["email_sent"], .1)
place(sfx, blip(600, .04), EV["pay_press"], .25); place(sfx, shimmer([78, 83, 90], .5, .05), EV["paid"], .14)
place(sfx, blip(300, .12), EV["lock"], .25)
for k in ("task_1", "task_2", "task_3"): place(sfx, shimmer([86 + 2 * int(k[-1])], .3), EV[k], .09)
for k in ("mem_1", "mem_2", "mem_3"): place(sfx, blip(1200 + 150 * int(k[-1]), .08), EV[k], .14)
place(sfx, shimmer([79, 83, 86, 90], .6), EV["suggest"], .1)
for i, k in enumerate(("st_app", "st_mac", "st_whatsapp", "st_glasses")):
    place(sfx, whoosh(.4, 300, 3000), EV[k] - .35, .1); place(sfx, shimmer([74 + [0, 4, 7, 12][i]], .5), EV[k], .14, pan=-.3 + .2 * i)
place(sfx, whoosh(1.0, 200, 5000), EV["converge"], .18); place(sfx, blip(330, .2), EV["msg_1"], .2); place(sfx, blip(440, .2), EV["msg_2"], .2)
place(sfx, rise, EV["brand"] - .3, .1); place(sfx, whoosh(.5, 400, 4500), EV["to_endcard"], .18); place(sfx, shimmer([86, 93], .9), EV["endcard"] + .05, .08)
sfx = reverb(sfx, 1.2, .15)

# ---------------- mix ----------------
v, vsr = sf.read(f"{ROOT}/audio/voice.wav"); v = resample_poly(v, 320, 147) if vsr == 22050 else resample_poly(v, SR, vsr)
v = np.pad(v[:N], (0, max(0, N - len(v[:N]))))
e = lp(np.abs(v), 6)[:, None]; e = e / (e.max() + 1e-9); duck = 1 - .55 * np.clip(e * 3, 0, 1)
voice = np.stack([v, v], 1)
mix = (music * duck + sfx + voice) * np.clip((DURATION - T) / .6, 0, 1)[:, None]
os.makedirs(f"{ROOT}/audio/stems", exist_ok=True); pk = max(1e-9, np.abs(mix).max())
for name, x in (("music", music * duck), ("sfx", sfx), ("voice", voice), ("mix_raw", mix)):
    sf.write(f"{ROOT}/audio/stems/{name}.wav", (x / pk * .7).astype(np.float32), SR)
print("ok")
