"""Original score + synthesised SFX for the Panic & Profit reel; ducks the music under the narration.
Panic: 120 BPM, D minor — pulsing sub bass, clock tick, staccato stabs, rising tension,
plus a chaos layer (two sirens, phone notifications and vibrations) that cuts dead when the headlines fall.
Explain: groove builds (kick, muted plucks). Recovery: opens to D major — clean piano, claps, warm pad.
Logo: pen-stroke + bell chord; end card sustains and fades.
Usage: python3 code/audio.py en  -> audio/stems/mix_raw_en.wav"""
import json, os, sys
import numpy as np, soundfile as sf
from scipy.signal import butter, sosfilt, fftconvolve, resample_poly
sys.path.insert(0, os.path.dirname(__file__))
from timing import DURATION, EVENTS as EV

LANG = sys.argv[1] if len(sys.argv) > 1 else "en"
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SR = 48000; N = int(DURATION * SR); T = np.arange(N) / SR
rng = np.random.default_rng(21)
midi = lambda m: 440 * 2 ** ((m - 69) / 12)
def env(n, a, d): t = np.arange(n) / SR; return np.minimum(1, t / max(a, 1e-4)) * np.exp(-t / d)
def lp(x, f): return sosfilt(butter(2, f, "low", fs=SR, output="sos"), x, axis=0)
def hp(x, f): return sosfilt(butter(2, f, "high", fs=SR, output="sos"), x, axis=0)
def bp(x, a, b): return sosfilt(butter(2, [a, b], "band", fs=SR, output="sos"), x, axis=0)
def place(buf, sig, t, g=1.0, pan=0.0):
    sig = np.asarray(sig, float)
    if sig.ndim == 1: sig = np.stack([sig * np.sqrt(.5 - pan / 2), sig * np.sqrt(.5 + pan / 2)], 1) * 1.414
    i = int(t * SR); j = min(N, i + len(sig))
    if 0 <= i < N: buf[i:j] += sig[:j - i] * g
def reverb(x, secs=1.6, mix=.2):
    n = int(secs * SR); tt = np.arange(n) / SR
    ir = lp(rng.standard_normal((n, 2)) * np.exp(-tt * 6.9 / secs)[:, None], 7000); ir /= np.sqrt((ir ** 2).sum(0))
    return x * (1 - mix) + np.stack([fftconvolve(x[:, c], ir[:, c])[:N] for c in range(2)], 1) * mix * 2.2
def saw(f, n, det=0.0):
    t = np.arange(n) / SR; out = 0
    for d in (-det, 0, det): out = out + 2 * ((t * f * (1 + d)) % 1) - 1
    return out / 3

BPM = 120; BEAT = 60 / BPM; S16 = BEAT / 4
PANIC_END, TURN_END, EXPL_END, REC_END = EV["fall"], EV["slip_back"], EV["grid_in"], EV["vline"]
music = np.zeros((N, 2))

# --- panic: sub-bass 8ths on D, stabs, rising drone ---
t = 0.0
while t < PANIC_END:
    n = int(BEAT / 2 * .9 * SR); prog = t / PANIC_END
    b = lp(saw(midi(38), n, .004), 180 + 900 * prog) * env(n, .004, .12)
    place(music, b, t, .30)
    t += BEAT / 2
n = int(PANIC_END * SR); tt = np.arange(n) / SR   # tension riser: detuned saw cluster sliding up
f = midi(50) * 2 ** (tt / PANIC_END * 0.6)
drone = sum(np.sin(2 * np.pi * np.cumsum(f * r) / SR) for r in (1, 1.006, 1.5, 2.0)) * (tt / PANIC_END) ** 1.5
place(music, lp(drone, 2500), 0.0, .05)
for e in EV["slips"]:  # staccato minor stab on each slip
    n = int(.22 * SR); s = sum(lp(saw(midi(m), n, .006), 2400) for m in (62, 65, 69)) * env(n, .003, .07)
    place(music, s, e, .07, pan=rng.uniform(-.4, .4))

# --- clock tick-tock: 16ths through panic, quarters through the turn and explain ---
t = 0.0
while t < EXPL_END + 0.3:
    if t < PANIC_END: step, g = S16, .05 + .05 * t / PANIC_END
    else: step, g = BEAT, .045
    n = int(.03 * SR); hi = int(round(t / step)) % 2 == 0
    click = hp(rng.standard_normal(n), 3500 if hi else 2200) * env(n, .0003, .006)
    place(music, click, t, g, pan=.25 if hi else -.25)
    t += step

# --- turn: low Dm pad, held under "Every headline moves your money" ---
n = int((TURN_END - PANIC_END + .6) * SR); tt = np.arange(n) / SR
pad = sum(np.sin(2 * np.pi * midi(m) * tt + i) for i, m in enumerate((38, 50, 57, 62, 65)))
place(music, lp(pad, 900) * np.minimum(1, tt / .6) * np.exp(-tt / 3.5), PANIC_END + .05, .045)

# --- explain: kick + muted plucks, Dm - Bb - F - C ---
CH_MIN = [[62, 65, 69], [58, 62, 65], [65, 69, 72], [60, 64, 67]]; BASS_MIN = [38, 34, 41, 36]
def pluck(f, n):
    t = np.arange(n) / SR
    return lp(saw(f, n, .002), 1800) * np.exp(-t * 14) + .3 * np.sin(2 * np.pi * f * 2 * t) * np.exp(-t * 20)
def kick(g=1.0):
    k = int(.3 * SR); kt = np.arange(k) / SR
    return np.sin(2 * np.pi * np.cumsum(48 + 110 * np.exp(-kt * 35)) / SR) * env(k, .001, .14) * g
t = TURN_END; k = 0
while t < EXPL_END:
    bar = int((t - TURN_END) // (4 * BEAT)) % 4; ch = CH_MIN[bar]
    place(music, pluck(midi(ch[[0, 1, 2, 1][k % 4]]), int(.3 * SR)), t, .11, pan=.35 * np.sin(k))
    if k % 2 == 0:
        place(music, kick(), t, .42)
        n = int(BEAT * .9 * SR); place(music, np.sin(2 * np.pi * midi(BASS_MIN[bar]) * np.arange(n) / SR) * env(n, .005, .25), t, .25)
    t += BEAT / 2; k += 1

# --- recovery: D major opens — piano chords, claps, warm pad: D - A - Bm - G ---
CH_MAJ = [[62, 66, 69, 74], [61, 64, 69, 73], [59, 62, 66, 71], [59, 62, 67, 71]]; BASS_MAJ = [38, 33, 35, 31]
def piano(f, n):
    t = np.arange(n) / SR
    s = sum(np.sin(2 * np.pi * f * h * t) * a * np.exp(-t * (2.2 + h)) for h, a in ((1, 1), (2, .45), (3, .2), (4, .1)))
    return s * np.minimum(1, t / .004)
t = EXPL_END; k = 0
place(music, lp(hp(rng.standard_normal(int(.8 * SR)), 3000), 9000) * np.linspace(0, 1, int(.8 * SR)) ** 2, EXPL_END - .8, .022)  # lift into it
while t < REC_END - 0.05:
    bar = int((t - EXPL_END) // (4 * BEAT)) % 4; ch = CH_MAJ[bar]
    if k % 8 == 0:
        for j, m in enumerate(ch): place(music, piano(midi(m), int(2.2 * SR)), t + j * .012, .07)
        n = int(2.0 * SR); place(music, np.sin(2 * np.pi * midi(BASS_MAJ[bar]) * np.arange(n) / SR) * env(n, .01, .9), t, .25)
    place(music, piano(midi(ch[[3, 1, 2, 1][k % 4]] + 12), int(.6 * SR)), t + BEAT / 2 * 0, .035, pan=.3 * np.sin(k * 1.3))
    if k % 2 == 0: place(music, kick(.8), t, .33)
    if k % 4 == 2: place(music, bp(rng.standard_normal(int(.12 * SR)), 900, 5000) * env(int(.12 * SR), .001, .035), t, .12)
    place(music, hp(rng.standard_normal(int(.04 * SR)), 8000) * env(int(.04 * SR), .0005, .01), t + BEAT / 4, .05)
    t += BEAT / 2; k += 1
n = int((REC_END - EXPL_END + 1) * SR); tt = np.arange(n) / SR
pad = sum(np.sin(2 * np.pi * midi(m) * tt + i) for i, m in enumerate((50, 57, 62, 66, 69)))
place(music, lp(pad, 1500) * np.minimum(1, tt / .8) * np.exp(-tt / 6), EXPL_END, .03)

# --- logo + end card: resolved D major chord with bells ---
n = int((DURATION - REC_END) * SR); tt = np.arange(n) / SR
chord = sum(np.sin(2 * np.pi * midi(m) * tt) * (1 if m < 70 else .5) for m in (38, 50, 57, 62, 66, 69, 74, 78))
place(music, lp(chord, 3000) * np.minimum(1, tt / .5) * np.exp(-tt / 4.0) * .05, REC_END)
music = reverb(music, 1.6, .16)

# ---------------- SFX ----------------
sfx = np.zeros((N, 2))
def whoosh(dur=.5, f0=300, f1=4000):
    n = int(dur * SR); x = rng.standard_normal(n); out = np.zeros(n); seg = int(.01 * SR)
    for i in range(0, n, seg):
        f = f0 * (f1 / f0) ** (i / n); out[i:i + seg] = bp(x[max(0, i - 2048):i + seg], f * .7, min(f * 1.4, 20000))[-len(x[i:i + seg]):]
    return out * np.sin(np.pi * np.linspace(0, 1, n)) ** 2
def slam():  # paper slap on a desk: low thump + papery noise burst + snap
    n = int(.35 * SR); tt = np.arange(n) / SR
    thump = np.sin(2 * np.pi * np.cumsum(70 + 160 * np.exp(-tt * 40)) / SR) * env(n, .001, .07)
    paper = bp(rng.standard_normal(n), 1200, 7000) * env(n, .0008, .035)
    snap = hp(rng.standard_normal(n), 5000) * env(n, .0002, .006)
    return thump * .9 + paper * .7 + snap * .5
def flip_snd(dur=.25):
    n = int(dur * SR); x = bp(rng.standard_normal(n), 1500, 9000); return x * np.sin(np.pi * np.linspace(0, 1, n)) ** 3
def blip(f, d=.08): n = int(.4 * SR); tt = np.arange(n) / SR; return np.sin(2 * np.pi * f * tt) * env(n, .001, d)
def bell(ms, d=1.2, gap=.06):
    n = int(2.5 * SR); tt = np.arange(n) / SR; out = np.zeros(n)
    for k, m in enumerate(ms):
        o = int(k * gap * SR); f = midi(m)
        s = (np.sin(2 * np.pi * f * tt) + .4 * np.sin(2 * np.pi * f * 2.76 * tt) * np.exp(-tt * 6)) * env(n, .002, d); out[o:] += s[:n - o]
    return out
def boom():
    n = int(1.4 * SR); tt = np.arange(n) / SR
    return np.sin(2 * np.pi * np.cumsum(40 + 60 * np.exp(-tt * 8)) / SR) * env(n, .002, .45) + lp(rng.standard_normal(n), 300) * env(n, .001, .2) * .6

for i, e in enumerate(EV["slips"]): place(sfx, slam(), e, .55 + .04 * i, pan=rng.uniform(-.35, .35))

# ---------------- chaos layer (panic only): sirens + phone notifications, cut dead at the fall ----------------
chaos = np.zeros((N, 2)); END = EV["fall"] + 0.02
def siren_wail(dur, f_lo=620, f_hi=1350, rate=0.55):
    """US-style wail: slow up/down sweep, square-ish tone, band-limited like a distant speaker."""
    n = int(dur * SR); t = np.arange(n) / SR
    f = f_lo + (f_hi - f_lo) * (0.5 - 0.5 * np.cos(2 * np.pi * rate * t))
    ph = 2 * np.pi * np.cumsum(f) / SR
    tone = np.tanh(2.5 * np.sin(ph)) + .3 * np.sin(2 * ph)
    return bp(tone, 450, 3200)
def siren_twotone(dur, f1=740, f2=988, period=1.1):
    """European hi-lo siren with a slight Doppler rise as it approaches."""
    n = int(dur * SR); t = np.arange(n) / SR
    f = np.where((t % period) < period / 2, f1, f2) * (1 + 0.025 * t / dur)
    f = lp(f, 40)  # soften the steps
    ph = 2 * np.pi * np.cumsum(f) / SR
    return bp(np.tanh(2 * np.sin(ph)) + .25 * np.sin(3 * ph), 500, 4000)
def ping(kind):
    n = int(.5 * SR); t = np.arange(n) / SR
    if kind == 0:   # two-note "ding-ding" message
        out = np.zeros(n)
        for k, m in enumerate((88, 93)):
            o = int(k * .09 * SR); out[o:] += (np.sin(2 * np.pi * midi(m) * t) * env(n, .001, .12))[:n - o]
        return out
    if kind == 1:   # news-alert tri-tone
        out = np.zeros(n)
        for k, m in enumerate((84, 88, 91)):
            o = int(k * .07 * SR); out[o:] += (np.sin(2 * np.pi * midi(m) * t) * env(n, .001, .09))[:n - o]
        return out
    if kind == 2:   # glassy single pop
        return (np.sin(2 * np.pi * 1760 * t) + .5 * np.sin(2 * np.pi * 2640 * t)) * env(n, .0005, .07)
    # phone vibration buzz on a desk
    m = int(.35 * SR); tb = np.arange(m) / SR
    buzz = np.sign(np.sin(2 * np.pi * 165 * tb)) * (0.6 + .4 * np.sin(2 * np.pi * 28 * tb)) * np.minimum(1, tb / .01) * np.exp(-tb * 3)
    out = np.zeros(n); out[:m] = lp(buzz, 900); return out
w = siren_wail(END - 0.0); w *= np.linspace(0.35, 1.0, len(w)) ** 1.5
place(chaos, np.stack([w * np.linspace(.9, .4, len(w)), w * np.linspace(.4, .9, len(w))], 1), 0.0, .10)   # drifts left -> right
tt_ = siren_twotone(END - 1.3); tt_ *= np.linspace(0.15, 1.0, len(tt_)) ** 2                              # approaching
place(chaos, tt_, 1.3, .09, pan=.45)
times = 0.12 + (END - .25) * np.sort(rng.random(22)) ** 0.75   # 22 notifications, denser towards the fall
for k, tn in enumerate(times):
    kind = [0, 1, 2, 3, 0, 2, 1, 3][k % 8]
    place(chaos, ping(kind), tn, (.07 if kind < 3 else .12) * (0.7 + .6 * tn / END), pan=rng.uniform(-.8, .8))
for e in EV["slips"][2:]:  # a news-alert tone stacked on some slams
    place(chaos, ping(1), e + .03, .06, pan=rng.uniform(-.5, .5))
cut = np.clip((END - T) / .03, 0, 1)[:, None]; chaos *= cut   # everything stops dead at the fall
chaos = reverb(chaos, 0.9, .12) * 2.8
place(sfx, whoosh(.55, 3000, 200), EV["fall"] - .05, .35); place(sfx, boom(), EV["fall"] + .12, .55)
for kw, f in (("w_every", 0), ("w_moves", 0)): place(sfx, hp(rng.standard_normal(int(.03 * SR)), 2500) * env(int(.03 * SR), .0003, .008), EV[kw], .1)
place(sfx, bell([86, 93], .5, .05), EV["w_money"] + .05, .05)               # a light 'ka-ching' on "money"
place(sfx, whoosh(.45, 400, 3500), EV["slip_back"] - .1, .2); place(sfx, slam(), EV["slip_back"] + .3, .35)
place(sfx, flip_snd(.3), EV["flip"] + .1, .45); place(sfx, whoosh(.7, 250, 2500), EV["expand"], .18)
for i in range(3):
    e = EV[f"tile_{i + 1}"]
    if i: place(sfx, blip(1600, .02), e - .3, .12)
    place(sfx, blip(midi([69, 74, 78][i]), .12) + .3 * blip(midi([81, 86, 90][i]), .05), e, .16, pan=-.3 + .3 * i)
place(sfx, whoosh(.5, 2500, 400), EV["card_out"], .2)
for i in range(8): place(sfx, flip_snd(.12), EV["grid_in"] + i * .06 + .45, .2, pan=-.4 + .1 * i)
for i in range(8):  # each marker flips red -> green, a rising D major scale
    e = EV["flip_green"] + i * .1; place(sfx, flip_snd(.12), e, .22, pan=-.35 + .1 * i)
    place(sfx, blip(midi([62, 64, 66, 67, 69, 71, 73, 74][i] + 12), .09), e + .14, .1, pan=-.35 + .1 * i)
place(sfx, whoosh(.5, 300, 2500), EV["statement_out"], .18)
# logo: pen stroke along the V, pop on the dot, bell chord on the wordmark
n = int(.75 * SR); pen = bp(rng.standard_normal(n), 2500, 8000) * (0.5 + .5 * np.sin(np.linspace(0, 40, n)) ** 2) * np.sin(np.pi * np.linspace(0, 1, n))
place(sfx, pen, EV["vline"], .08); place(sfx, blip(midi(86), .06), EV["vline"] + .74, .2)
place(sfx, bell([62, 69, 74, 78, 81], 1.4, .05), EV["wordmark"], .1)
place(sfx, blip(900, .03) + .5 * blip(1800, .015), EV["cta"], .2)
place(sfx, whoosh(.5, 500, 3000), EV["to_endcard"] - .05, .14); place(sfx, bell([74, 81], 1.2), EV["endcard"], .06)
sfx = reverb(sfx, 1.0, .1)

# ---------------- mix: duck music under the voice ----------------
v, vsr = sf.read(f"{ROOT}/audio/voice_{LANG}.wav"); v = resample_poly(v, SR, vsr)[:N]; v = np.pad(v, (0, N - len(v)))
e = lp(np.abs(v), 6)[:, None]; e = e / (e.max() + 1e-9)
duck = 1 - .5 * np.clip(e * 3, 0, 1)
voice = np.stack([v, v], 1) * 1.6
chaos_duck = 1 - .45 * np.clip(e * 3, 0, 1)
mix = music * duck + sfx + chaos * chaos_duck + voice
mix *= np.clip((DURATION - T) / .8, 0, 1)[:, None]
os.makedirs(f"{ROOT}/audio/stems", exist_ok=True)
pk = max(1e-9, np.abs(mix).max())
for name, x in (("music", music * duck), ("sfx", sfx), ("chaos", chaos * chaos_duck), ("voice", voice), (f"mix_raw_{LANG}", mix)):
    sf.write(f"{ROOT}/audio/stems/{name}.wav", (x / pk * .7).astype(np.float32), SR)
print("ok")
