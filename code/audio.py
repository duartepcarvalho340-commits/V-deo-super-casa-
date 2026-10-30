"""Original score + synthesised paper/pop-up SFX for the SUPERCASA spec film; ducks the music under the narration.
Usage: python3 code/audio.py en   -> audio/stems/mix_raw_en.wav"""
import json, os, sys
import numpy as np, soundfile as sf
from scipy.signal import butter, sosfilt, fftconvolve, resample_poly
sys.path.insert(0, os.path.dirname(__file__))
from timing import DURATION, EVENTS as EV, TURNS, COVER_OPEN, BOOK_CLOSE, END_OPEN

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
LANG = sys.argv[1] if len(sys.argv) > 1 else "en"
SR = 48000; N = int(DURATION * SR); T = np.arange(N) / SR
rng = np.random.default_rng(7)
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
def reverb(x, secs=1.8, mix=.2):
    n = int(secs * SR); tt = np.arange(n) / SR
    ir = lp(rng.standard_normal((n, 2)) * np.exp(-tt * 6.9 / secs)[:, None], 6000); ir /= np.sqrt((ir ** 2).sum(0))
    return x * (1 - mix) + np.stack([fftconvolve(x[:, c], ir[:, c])[:N] for c in range(2)], 1) * mix * 2.2

# ---------------- score: warm acoustic, 96 BPM in G major ----------------
BPM = 96; BEAT = 60 / BPM; BAR = 4 * BEAT
CH = [[55, 59, 62, 67], [54, 57, 62, 66], [52, 55, 59, 64], [48, 52, 55, 60]]  # G - D/F# - Em - C
BASS = [43, 42, 40, 36]
def pluck(f, dur=1.2):
    """Karplus-Strong string"""
    n = int(dur * SR); p = max(2, int(SR / f)); buf = rng.uniform(-1, 1, p); out = np.zeros(n)
    for i in range(n):
        out[i] = buf[i % p]; buf[i % p] = 0.996 * 0.5 * (buf[i % p] + buf[(i + 1) % p])
    return lp(out, 5000)
def piano(f, n):
    t = np.arange(n) / SR
    s = sum(a * np.sin(2 * np.pi * f * h * t) * np.exp(-t * (2.2 + h)) for h, a in ((1, 1), (2, .45), (3, .2), (4, .1)))
    return s * np.minimum(1, t / .004)
music = np.zeros((N, 2))
cache = {}
pat = [0, 2, 1, 3, 2, 1, 3, 2]
t = 0.0; k = 0
while t < 18.3:
    ch = CH[int(t // BAR) % 4]; m = ch[pat[k % 8]] + 12
    if m not in cache: cache[m] = pluck(midi(m))
    place(music, cache[m], t, .13 * (0.6 if t < 3.0 else 1), pan=.35 * np.sin(k * 1.1))
    t += BEAT / 2; k += 1
for b in range(int(DURATION / BAR) + 1):  # soft piano chords on each bar
    if b * BAR > 18.3: break
    n = int(BAR * SR); ch = CH[b % 4]
    s = sum(piano(midi(m), n) for m in ch) * .25
    place(music, s, b * BAR, .22)
t = 3.0
while t < 18.0:  # bass, brushed kick and shaker from the first page turn
    n = int(BEAT * .95 * SR); tt = np.arange(n) / SR
    f = midi(BASS[int(t // BAR) % 4]); place(music, np.sin(2 * np.pi * f * tt) * env(n, .01, .35), t, .28)
    beat = int(round(t / BEAT)) % 4
    if beat in (0, 2):
        kk = int(.3 * SR); kt = np.arange(kk) / SR
        place(music, np.sin(2 * np.pi * np.cumsum(50 + 70 * np.exp(-kt * 35)) / SR) * env(kk, .002, .12), t, .38)
    else:
        place(music, bp(rng.standard_normal(int(.2 * SR)), 1500, 6000) * env(int(.2 * SR), .01, .06), t, .08)
    for h in (0, .5):
        place(music, hp(rng.standard_normal(int(.06 * SR)), 6000) * env(int(.06 * SR), .008, .02), t + BEAT * h + BEAT / 4, .05, pan=.3)
    t += BEAT
# resolving chord for the cover and end card
n = int((DURATION - 15.35) * SR); tt = np.arange(n) / SR
chord = sum(piano(midi(m), n) for m in (43, 55, 59, 62, 67, 71, 74)) * .18
place(music, chord, 15.35, .5)
place(music, sum(piano(midi(m), int(2.4 * SR)) for m in (67, 71, 74, 79)) * .14, 18.85, .5)
music = reverb(music, 2.0, .2)

# ---------------- SFX ----------------
sfx = np.zeros((N, 2))
def page_turn(d=.7):
    n = int(d * SR); x = rng.standard_normal(n); tt = np.linspace(0, 1, n)
    flutter = 0.6 + 0.4 * np.abs(np.sin(2 * np.pi * 9 * tt * (1 + tt)))
    shape = np.sin(np.pi * tt) ** 1.5 * flutter
    return lp(bp(x, 700, 5000) * shape * .6 + bp(x, 2500, 8000) * shape * .12, 8000)
def paper_pop(f=220):
    n = int(.25 * SR); tt = np.arange(n) / SR
    return np.sin(2 * np.pi * np.cumsum(f + 500 * np.exp(-tt * 40)) / SR) * env(n, .001, .05) + bp(rng.standard_normal(n), 1500, 6000) * env(n, .001, .02) * .5
def tick(f=2500): n = int(.04 * SR); return bp(rng.standard_normal(n), f * .6, f * 1.5) * env(n, .0005, .008)
def chime(ms, d=.6, gap=.07):
    n = int(1.6 * SR); tt = np.arange(n) / SR; out = np.zeros(n)
    for k, m in enumerate(ms):
        o = int(k * gap * SR); s = np.sin(2 * np.pi * midi(m) * tt + .8 * np.sin(2 * np.pi * midi(m) * 3.5 * tt) * np.exp(-tt * 9)) * env(n, .002, d); out[o:] += s[:n - o]
    return out
def thud():
    n = int(.5 * SR); tt = np.arange(n) / SR
    return np.sin(2 * np.pi * np.cumsum(70 + 60 * np.exp(-tt * 20)) / SR) * env(n, .002, .12) + lp(rng.standard_normal(n), 900) * env(n, .001, .05) * .6
def whoosh(d=.5, f0=500, f1=4000):
    n = int(d * SR); x = rng.standard_normal(n); out = np.zeros(n); seg = int(.01 * SR)
    for i in range(0, n, seg):
        f = f0 * (f1 / f0) ** (i / n); out[i:i + seg] = bp(x[max(0, i - 2048):i + seg], f * .7, min(f * 1.4, 20000))[-len(x[i:i + seg]):]
    return out * np.sin(np.pi * np.linspace(0, 1, n)) ** 2

place(sfx, page_turn(COVER_OPEN[1]), COVER_OPEN[0], .35, pan=.2)
place(sfx, thud(), COVER_OPEN[0] + COVER_OPEN[1] - .05, .3, pan=-.2)
for t0, d in TURNS: place(sfx, page_turn(d), t0, .4, pan=.25)
for i, dt in enumerate((-.25, -.15, -.1, 0, .15, .25)): place(sfx, paper_pop(200 + 40 * i), EV["house_pop"] + dt + .05, .3, pan=-.4 + .15 * i)
place(sfx, chime([79, 83], .5), EV["house_lights"], .08)
# search
place(sfx, paper_pop(260), TURNS[0][0] + TURNS[0][1] + .1, .35); place(sfx, paper_pop(240), TURNS[0][0] + TURNS[0][1] + .15, .3)
n_chars = 6
for i in range(n_chars): place(sfx, tick(2200 + 300 * (i % 3)), EV["type_start"] + i * (EV["type_end"] - EV["type_start"]) / n_chars, .35)
place(sfx, tick(1200) * 2, EV["toggle_rent"], .35); place(sfx, chime([74], .2), EV["toggle_rent"] + .05, .08)
for i in range(3): place(sfx, paper_pop(400 + 60 * i), EV[f"chip_{i + 1}"] - .1, .25, pan=-.2 + .2 * i)
place(sfx, chime([79, 83, 86], .5), EV["results"], .1)
for i in range(3): place(sfx, paper_pop(220 + 30 * i), EV["results"] + .08 * i + .02, .3, pan=-.3 + .3 * i)
# map
for i in range(5): place(sfx, paper_pop(300 + 50 * i), EV[f"pin_{i + 1}"], .3, pan=-.3 + .15 * i)
for r in range(3): place(sfx, chime([86], .3), EV["near_me"] + r * 1.1, .07 / (r + 1))
place(sfx, whoosh(.6, 300, 2000), 8.75, .1)
# save + alerts
place(sfx, paper_pop(230), TURNS[2][0] + TURNS[2][1] + .1, .35)
place(sfx, paper_pop(500), EV["heart"], .3); place(sfx, chime([84, 88], .5), EV["heart"] + .03, .12)
bn = int(1.2 * SR); bt = np.arange(bn) / SR
bellsig = sum(np.sin(2 * np.pi * f * bt) * a for f, a in ((1320, 1), (1320 * 2.76, .4), (1320 * 5.4, .2))) * env(bn, .001, .35)
place(sfx, bellsig * .5, EV["bell"], .18)
for ev in ("alert_1", "alert_2"): place(sfx, whoosh(.4, 2500, 800), EV[ev], .15, pan=.4); place(sfx, chime([81, 88], .4), EV[ev] + .3, .1)
# close + logo + end card
place(sfx, page_turn(BOOK_CLOSE[1]), BOOK_CLOSE[0], .4, pan=-.25); place(sfx, thud(), BOOK_CLOSE[0] + BOOK_CLOSE[1] - .05, .55)
place(sfx, whoosh(.9, 1500, 9000), EV["logo_gleam"], .08)
place(sfx, page_turn(END_OPEN[1]), END_OPEN[0], .35, pan=.2); place(sfx, paper_pop(200), EV["card"], .4)
sfx = reverb(sfx, 1.0, .12)

# ---------------- mix: duck music under the voice ----------------
v, vsr = sf.read(f"{ROOT}/audio/voice_{LANG}.wav"); v = resample_poly(v, SR, vsr)[:N]; v = np.pad(v, (0, N - len(v)))
e = lp(np.abs(v), 6)[:, None]; e = e / (e.max() + 1e-9)
duck = 1 - .5 * np.clip(e * 3, 0, 1)
voice = np.stack([v, v], 1) * 1.1
mix = music * duck + sfx + voice
fade = np.clip((DURATION - T) / .5, 0, 1)[:, None]; mix *= fade
os.makedirs(f"{ROOT}/audio/stems", exist_ok=True)
pk = max(1e-9, np.abs(mix).max())
for name, x in (("music", music * duck), ("sfx", sfx), ("voice", voice), (f"mix_raw_{LANG}", mix)):
    sf.write(f"{ROOT}/audio/stems/{name}.wav", (x / pk * .7).astype(np.float32), SR)
print("ok")
