"""Original score + synthesised SFX for the Duro Ceramics spec film; ducks the music under the narration.
Score: 80 BPM, D minor -> D major at the end. Guitarra-portuguesa-like 12-string plucks (paired courses, tremolo on
long melody notes), classical-guitar bass and strums, soft string pad, frame drum and shaker.
Usage: python3 code/audio.py pt   -> audio/stems/mix_raw_pt.wav"""
import os, sys
import numpy as np, soundfile as sf
from scipy.signal import butter, sosfilt, fftconvolve, resample_poly
sys.path.insert(0, os.path.dirname(__file__))
from timing import DURATION, EV, BEAT, BAR, MUSIC_T0

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
LANG = sys.argv[1] if len(sys.argv) > 1 else "pt"
SR = 48000; N = int(DURATION * SR); T = np.arange(N) / SR
rng = np.random.default_rng(7)
midi = lambda m: 440 * 2 ** ((m - 69) / 12)
def env(n, a, d): t = np.arange(n) / SR; return np.minimum(1, t / max(a, 1e-4)) * np.exp(-t / d)
def lp(x, f): return sosfilt(butter(2, f, "low", fs=SR, output="sos"), x, axis=0)
def hp(x, f): return sosfilt(butter(2, f, "high", fs=SR, output="sos"), x, axis=0)
def bp(x, a, b): return sosfilt(butter(2, [a, b], "band", fs=SR, output="sos"), x, axis=0)
def place(buf, sig, t, g=1.0, pan=0.0):
    sig = np.asarray(sig, float)
    if sig.ndim == 1: sig = np.stack([sig * np.sqrt(.5 - pan / 2), sig * np.sqrt(.5 + pan / 2)], 1) * 1.414
    i = int(t * SR); j = min(N, i + len(sig))
    if i < 0: sig = sig[-i:]; j = min(N, len(sig)); i = 0
    if i < N: buf[i:j] += sig[:j - i] * g
def reverb(x, secs=1.8, mix=.2, seed=3):
    r = np.random.default_rng(seed); n = int(secs * SR); tt = np.arange(n) / SR
    ir = lp(r.standard_normal((n, 2)) * np.exp(-tt * 6.9 / secs)[:, None], 7000); ir /= np.sqrt((ir ** 2).sum(0))
    return x * (1 - mix) + np.stack([fftconvolve(x[:, c], ir[:, c])[:N] for c in range(2)], 1) * mix * 2.2

# ---------------- instruments ----------------
KS = {}
def ks(f, dur=1.6, damp=0.996, bright=6500, seed=0):
    key = (round(f, 2), dur, damp, bright)
    if key in KS: return KS[key]
    n = int(dur * SR); p = max(2, int(SR / f)); r = np.random.default_rng(seed + int(f))
    buf = r.uniform(-1, 1, p); buf = buf - buf.mean(); out = np.zeros(n)
    for i in range(n):
        j = i % p; out[i] = buf[j]; buf[j] = damp * 0.5 * (buf[j] + buf[(j + 1) % p])
    out = lp(out, bright); KS[key] = out; return out
def guitarra(m, dur=1.4, vel=1.0):
    """paired steel courses: unison slightly detuned (+ octave for the bass courses) -> shimmering 12-string tone"""
    f = midi(m); a = ks(f, dur, .9965, 9000); b = ks(f * 1.0035, dur, .9965, 9000, 5)
    s = a + 0.8 * b
    if m < 64: s = s + 0.45 * ks(f * 2, dur, .996, 9000, 9)
    return hp(s, 180) * vel
def viola(m, dur=1.6): return lp(ks(midi(m), dur, .995, 2600, 3), 3000)
def pad(ms, n):
    t = np.arange(n) / SR; s = np.zeros(n)
    for m in ms:
        for d in (-0.08, 0.0, 0.07):
            ph = rng.uniform(0, 1); s += ((t * midi(m + d) + ph) % 1.0 - 0.5)
    s = lp(lp(s, 1100), 1500) / (len(ms) * 3)
    a = np.minimum(1, t / .7) * np.minimum(1, (n / SR - t) / .6); return s * a

music = np.zeros((N, 2))
bar_t = lambda b: MUSIC_T0 + b * BAR
CHORDS = {0: [50, 53, 57], 1: [46, 50, 53], 2: [53, 57, 60], 3: [48, 52, 55], 4: [50, 53, 57], 5: [43, 46, 50], 5.5: [45, 49, 52], 6: [50, 54, 57]}
def chord_at(b, beat): return CHORDS[5.5] if (b == 5 and beat >= 2) else CHORDS[b]

# guitarra arpeggio (8ths), lighter in the first bar
ARP = [0, 2, 1 + 12 * 0, 2, 0, 2, 1, 2]
for b in range(6):
    for k in range(8):
        ch = chord_at(b, k / 2); m = ch[[0, 2, 1, 2, 0, 2, 1, 2][k]] + (24 if k in (2, 6) else 12) + (12 if k == 4 else 0)
        place(music, guitarra(m, 1.1, 1.0), bar_t(b) + k * BEAT / 2 + rng.normal(0, .004), .09 * (0.55 if b == 0 else 1), pan=.35 * np.sin(k * 1.3))
# viola: bass on 1 and 3, soft strum on 2 and 4 (from bar 1)
for b in range(1, 6):
    for beat in range(4):
        ch = chord_at(b, beat); t0 = bar_t(b) + beat * BEAT
        if beat in (0, 2): place(music, viola(ch[0] - 12 + (0 if beat == 0 else 7), 1.4), t0, .30, pan=-.15)
        else:
            for i, m in enumerate(ch): place(music, viola(m, 1.0), t0 + i * 0.012, .10, pan=-.2 + .2 * i)
# melody with tremolo on long notes (the guitarra portuguesa signature)
MEL = [(1, 0, 77, 1.5, 1), (1, 1.5, 76, .5, 0), (1, 2, 74, 2, 1), (2, 0, 72, 1.5, 1), (2, 1.5, 74, .5, 0), (2, 2, 76, 2, 1),
       (3, 0, 77, 1, 0), (3, 1, 76, 1, 0), (3, 2, 74, 2, 1), (4, 0, 74, 1.5, 1), (4, 1.5, 77, .5, 0), (4, 2, 81, 2, 1),
       (5, 0, 79, 2, 1), (5, 2, 76, 2, 1), (6, 0, 78, 3, 1), (6, 3, 74, 1.5, 0)]
for b, bt, m, d, trem in MEL:
    t0 = bar_t(b) + bt * BEAT; dur = d * BEAT; g = .10 if b < 6 else .12
    if trem:
        n = int(dur / 0.062)
        for i in range(n): place(music, guitarra(m, .5, 0.6 + 0.4 * (i == 0)), t0 + i * 0.062, g * (0.85 if i else 1.1) * (1 - 0.4 * i / max(1, n)), pan=.15)
        place(music, guitarra(m, 1.6), t0 + n * 0.062, g * .8, pan=.15)
    else: place(music, guitarra(m, 1.4), t0, g * 1.1, pan=.15)
# pad under everything (bar 1 onward)
for b in range(1, 7):
    for half in (0, 1):
        ch = chord_at(b, half * 2); n = int(BAR / 2 * SR * 1.15) if b < 6 else int((DURATION - bar_t(6)) * SR / 2)
        place(music, pad([m + 12 for m in ch], n), bar_t(b) + half * BAR / 2, .14)
# percussion from bar 2: frame drum + shaker; a little more in bars 4-5
def drum(n=int(.45 * SR)):
    t = np.arange(n) / SR; return np.sin(2 * np.pi * np.cumsum(70 + 50 * np.exp(-t * 25)) / SR) * env(n, .003, .14) + lp(rng.standard_normal(n), 700) * env(n, .001, .03) * .5
def shaker(): n = int(.09 * SR); return hp(rng.standard_normal(n), 5000) * env(n, .015, .03)
DR = drum()
for b in range(2, 6):
    for beat in range(4):
        t0 = bar_t(b) + beat * BEAT
        if beat == 0 or (b >= 4 and beat == 2): place(music, DR, t0, .32)
        if beat == 1: place(music, DR, t0 + BEAT / 2, .2)
        for h in (0, .5): place(music, shaker(), t0 + h * BEAT, .045 if h else .03, pan=.35)
# final bar: D major strum that rings into the end card
for i, m in enumerate([38, 45, 50, 54, 57, 62, 66]): place(music, viola(m, 3.2) if m < 55 else guitarra(m, 3.2), bar_t(6) + i * 0.018, .18, pan=-.3 + .1 * i)
music = reverb(music, 2.2, .22)

# ---------------- SFX ----------------
sfx = np.zeros((N, 2))
def add(*xs):
    n = max(len(x) for x in xs); return sum(np.pad(x, (0, n - len(x))) for x in xs)
def noise(d): return rng.standard_normal(int(d * SR))
def whoosh(d=.5, f0=400, f1=3000, shape=2):
    n = int(d * SR); x = rng.standard_normal(n); out = np.zeros(n); seg = int(.01 * SR)
    for i in range(0, n, seg):
        f = f0 * (f1 / f0) ** (i / n); lo, hi = max(40, f * .6), min(f * 1.6, 20000)
        out[i:i + seg] = bp(x[max(0, i - 2048):i + seg], lo, hi)[-len(x[i:i + seg]):]
    return out * np.sin(np.pi * np.linspace(0, 1, n)) ** shape
def thud(f=60, d=.5, a=.6):
    n = int(d * SR); t = np.arange(n) / SR
    return np.sin(2 * np.pi * np.cumsum(f + 60 * np.exp(-t * 20)) / SR) * env(n, .002, .12) + lp(rng.standard_normal(n), 900) * env(n, .001, .05) * a
def clink(f=2200, d=.35, g=1.0):
    n = int(d * SR); t = np.arange(n) / SR; s = np.zeros(n)
    for k, (r, a, dec) in enumerate(((1, 1, .18), (2.32, .6, .10), (4.25, .4, .06), (6.63, .25, .04))):
        s += a * np.sin(2 * np.pi * f * r * t + k) * np.exp(-t / dec)
    s += hp(rng.standard_normal(n), 3000) * env(n, .0003, .004) * .8
    return s * g
def clack(): return add(clink(rng.uniform(1300, 1700), .3) * .7, thud(90, .3, .9) * .6)
def swish(d=.25, lo=2500, hi=9000): n = int(d * SR); return bp(rng.standard_normal(n), lo, hi) * np.sin(np.pi * np.linspace(0, 1, n)) ** 1.5
def flutter(d=.5, rate=17):
    n = int(d * SR); t = np.arange(n) / SR; am = 0.5 + 0.5 * np.sign(np.sin(2 * np.pi * rate * t)) * np.abs(np.sin(2 * np.pi * rate * t)) ** .3
    return bp(rng.standard_normal(n), 300, 2500) * am * np.sin(np.pi * np.linspace(0, 1, n))
def chime(ms, d=.8, gap=.06):
    n = int(2.0 * SR); t = np.arange(n) / SR; out = np.zeros(n)
    for k, m in enumerate(ms):
        o = int(k * gap * SR); s = np.sin(2 * np.pi * midi(m) * t + .6 * np.sin(2 * np.pi * midi(m) * 3.0 * t) * np.exp(-t * 8)) * env(n, .002, d); out[o:] += s[:n - o]
    return out

# 1 · wheel
place(sfx, whoosh(.26, 1500, 300, 1), EV["clay_drop"], .12)
place(sfx, add(thud(55, .6, 1.0), lp(noise(.6), 1800) * env(int(.6 * SR), .001, .06) * .9), EV["clay_land"], .75)
# motor hum + wet clay, following the wheel speed
W_KEYS = [(0, 0), (0.30, 0), (0.75, 8.5), (4.2, 8.5), (4.9, 2.8), (5.22, 2.8), (5.42, 11.5), (5.88, 11.5), (6.03, 3.49), (7.62, 3.49), (7.85, 1.0), (8.18, 0), (99, 0)]
om = np.interp(T, [k[0] for k in W_KEYS], [k[1] for k in W_KEYS]) / 11.5
hum = (np.sin(2 * np.pi * 50 * T) * .5 + np.sin(2 * np.pi * 100 * T) * .3 + lp(rng.standard_normal(N), 260) * 2.0) * om
hum += bp(rng.standard_normal(N), 800, 2600) * om * (0.4 + 0.3 * np.sin(2 * np.pi * 1.3 * T)) * ((T > 0.5) & (T < 3.5))
place(sfx, hum * .05, 0)
sc = int(.5 * SR); place(sfx, bp(noise(.5), 2000, 6000) * np.sin(np.pi * np.linspace(0, 1, sc)) * (0.6 + 0.4 * np.sin(np.linspace(0, 40, sc))), EV["groove"], .10, pan=.2)
# kiln + glaze wipe
gd = EV["glaze_end"] - EV["glaze"]; gn = int((gd + .4) * SR)
roar = lp(rng.standard_normal(gn), 900) * np.sin(np.pi * np.linspace(0, 1, gn)) ** 1.2
crackle = np.zeros(gn); idx = rng.integers(0, gn - 400, 90); crackle[idx] = rng.uniform(.3, 1, 90); crackle = hp(crackle, 2500)
place(sfx, add(roar * .5, crackle * .5, whoosh(gd + .4, 300, 5000) * .6), EV["glaze"] - .1, .25)
place(sfx, chime([86, 93], .6), EV["glaze_end"], .05)
# 2 · brush
place(sfx, whoosh(.3, 2000, 600), EV["brush_in"], .06, pan=.4)
place(sfx, swish(EV["ring_end"] - EV["ring"], 3000, 9000), EV["ring"], .13, pan=.3)
for k in range(6): place(sfx, swish(.24), EV["fish0"] + k * EV["fish_dur"], .11, pan=.25)
for i in range(25): place(sfx, bp(noise(.03), 2500, 7000) * env(int(.03 * SR), .001, .006), EV["dots"] + i * 0.016, .12, pan=.2)
place(sfx, whoosh(.3, 600, 2500), EV["brush_out"], .06, pan=.4)
# 3 · table
place(sfx, whoosh(.35, 300, 1500), EV["lift"], .10)
place(sfx, add(thud(110, .3, .6) * .6, clink(2600, .25) * .25), EV["set"] + .26, .55)
for i in range(8):
    tl = EV["items"] + i * 0.11
    place(sfx, swish(.45, 600, 3500), tl, .06, pan=-.6 + .17 * i); place(sfx, add(thud(120 + 15 * i, .2, .7) * .4, clink(1900 + 140 * i, .2) * .14), tl + .45, .4, pan=-.6 + .17 * i)
sq = int(.25 * SR); st = np.arange(sq) / SR
place(sfx, np.sin(2 * np.pi * np.cumsum(500 + 1400 * st / .25) / SR) * env(sq, .002, .08), EV["jump"], .12)
place(sfx, whoosh(.6, 500, 3000, 1.5), EV["jump"], .1, pan=.3)
place(sfx, add(clink(2300, .4) * .7, thud(140, .25, .5) * .4), EV["jump_end"], .45, pan=.35)
place(sfx, flutter(.55), EV["shadow_pass"], .12, pan=-.3)
place(sfx, whoosh(.5, 200, 6000, 1.2), EV["whip"] - .1, .32)
# 4 · wall
for i in range(3):
    tl = EV[f"sw{i}"]; place(sfx, flutter(.6, 15 + 2 * i), tl - .65, .10, pan=-.4 + .3 * i)
    place(sfx, add(clink(1500 + 220 * i, .22) * .6, thud(160, .15, .8) * .3), tl, .38, pan=-.2 + .3 * i)
place(sfx, flutter(.6, 19), EV["takeoff"], .14, pan=.3)
place(sfx, whoosh(.45, 150, 4000, 1.0), EV["takeover"], .35)
place(sfx, thud(48, .9, .4), EV["takeover_end"], .55)
# 5 · stack + logo + end card
for td in EV["drops"] + [EV["white"]]: place(sfx, clack(), td + .32, .5, pan=rng.uniform(-.2, .2)); place(sfx, whoosh(.3, 3000, 800), td, .04)
place(sfx, swish(EV["logo_end"] - EV["logo"] - .2, 2500, 8000), EV["logo"], .12, pan=-.2)
place(sfx, chime([81, 86, 90, 93], .9, .08), EV["ring_text"], .05)
place(sfx, whoosh(.5, 400, 3000), EV["flip"], .14)
place(sfx, clink(2900, .5) * .4, EV["flip_end"], .3)
place(sfx, chime([74, 78, 81, 86], 1.4, .07), EV["card"] + .05, .07)
sfx = reverb(sfx, 1.2, .14, seed=5)

# ---------------- mix: duck music under the voice ----------------
v, vsr = sf.read(f"{ROOT}/audio/voice_{LANG}.wav")
if v.ndim > 1: v = v.mean(1)
if vsr != SR: v = resample_poly(v, SR, vsr)
v = np.pad(v[:N], (0, max(0, N - len(v))))
v = hp(v, 80); v = v / (np.abs(v).max() + 1e-9) * 0.9
e = lp(np.abs(v), 5)[:, None]; e = e / (e.max() + 1e-9)
duck = 1 - .45 * np.clip(e * 3.5, 0, 1)
voice = np.stack([v, v], 1) * 1.0
mix = music * 0.95 * duck + sfx * 0.5 + voice * 0.95
fade = np.clip((DURATION - T) / .6, 0, 1)[:, None]; mix *= fade
os.makedirs(f"{ROOT}/audio/stems", exist_ok=True)
pk = max(1e-9, np.abs(mix).max())
for name, x in (("music", music * duck * .95), ("sfx", sfx * .5), ("voice", voice * .95), (f"mix_raw_{LANG}", mix)):
    sf.write(f"{ROOT}/audio/stems/{name}.wav", (x / pk * .7).astype(np.float32), SR)
print("ok", round(float(np.abs(mix).max()), 3))
