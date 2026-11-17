"""Original score + synthesised SFX for the Duolingo spec film; ducks the music under the narration."""
import json, os, sys
import numpy as np, soundfile as sf
from scipy.signal import butter, sosfilt, fftconvolve, resample_poly
sys.path.insert(0, os.path.dirname(__file__))
from timing import DURATION, EVENTS as EV

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SR = 48000; N = int(DURATION * SR); T = np.arange(N) / SR
rng = np.random.default_rng(11)
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
def reverb(x, secs=1.6, mix=.2):
    n = int(secs * SR); tt = np.arange(n) / SR
    ir = lp(rng.standard_normal((n, 2)) * np.exp(-tt * 6.9 / secs)[:, None], 7000); ir /= np.sqrt((ir ** 2).sum(0))
    return x * (1 - mix) + np.stack([fftconvolve(x[:, c], ir[:, c])[:N] for c in range(2)], 1) * mix * 2.2

# ---------------- score: bright, bouncy, 128 BPM in F major ----------------
BPM = 128; BEAT = 60 / BPM; BAR = 4 * BEAT
CH = [[65, 69, 72, 76], [62, 65, 69, 72], [70, 74, 77, 81], [60, 64, 67, 72]]  # F - Dm - Bb - C
BASS = [41, 38, 46, 36]
def marimba(f, n):
    t = np.arange(n) / SR
    return (np.sin(2 * np.pi * f * t) + .35 * np.sin(2 * np.pi * f * 4 * t) * np.exp(-t * 30)) * np.exp(-t * 7)
music = np.zeros((N, 2))
pat = [0, 2, 1, 3, 2, 1, 3, 1]
t = 0.0; k = 0
while t < 18.6:
    ch = CH[int(t // BAR) % 4]; m = ch[pat[k % 8]] + (12 if t > 11.5 else 0)
    place(music, marimba(midi(m), int(.5 * SR)), t, .16 * (0.5 if t < 1.5 else 1), pan=.4 * np.sin(k * 1.3))
    t += BEAT / 2; k += 1
for b in range(int(DURATION / BAR) + 1):  # warm pad
    n = int(BAR * SR * 1.1); tt = np.arange(n) / SR
    s = sum(np.sin(2 * np.pi * midi(m) * tt + i) for i, m in enumerate(CH[b % 4])) * np.minimum(1, tt / .3) * np.exp(-tt / 3)
    place(music, lp(s, 2000), b * BAR, .035)
t = 0.0
while t < 18.6:  # bass + soft kick + claps
    n = int(BEAT * .9 * SR); tt = np.arange(n) / SR
    if t >= 1.5:
        f = midi(BASS[int(t // BAR) % 4]); place(music, np.sin(2 * np.pi * f * tt) * env(n, .005, .2), t, .3)
        kk = int(.25 * SR); kt = np.arange(kk) / SR; place(music, np.sin(2 * np.pi * np.cumsum(55 + 90 * np.exp(-kt * 40)) / SR) * env(kk, .001, .1), t, .45)
        if int(round(t / BEAT)) % 2 == 1: place(music, bp(rng.standard_normal(int(.12 * SR)), 900, 5000) * env(int(.12 * SR), .001, .03), t, .12)
        place(music, hp(rng.standard_normal(int(.05 * SR)), 7000) * env(int(.05 * SR), .0005, .012), t + BEAT / 2, .07)
    t += BEAT
# final airy chord for the logo and end card
n = int((DURATION - 17.45) * SR); tt = np.arange(n) / SR
chord = sum(np.sin(2 * np.pi * midi(m) * tt) * (1 if m < 72 else .5) for m in (53, 60, 65, 69, 72, 76, 79))
place(music, chord * np.minimum(1, tt / .05) * np.exp(-tt / 2.5) * .05, 17.45)
music = reverb(music, 1.4, .15)

# ---------------- SFX ----------------
sfx = np.zeros((N, 2))
def blip(f, d=.08, g=1.0): n = int(.3 * SR); tt = np.arange(n) / SR; return np.sin(2 * np.pi * f * tt) * env(n, .001, d) * g
def pop(): n = int(.25 * SR); tt = np.arange(n) / SR; return np.sin(2 * np.pi * np.cumsum(180 + 600 * np.exp(-tt * 30)) / SR) * env(n, .001, .06)
def whoosh(dur=.5, f0=300, f1=4000):
    n = int(dur * SR); x = rng.standard_normal(n); out = np.zeros(n); seg = int(.01 * SR)
    for i in range(0, n, seg):
        f = f0 * (f1 / f0) ** (i / n); out[i:i + seg] = bp(x[max(0, i - 2048):i + seg], f * .7, min(f * 1.4, 20000))[-len(x[i:i + seg]):]
    return out * np.sin(np.pi * np.linspace(0, 1, n)) ** 2
def chime(ms, d=.5, gap=.07):
    n = int(1.2 * SR); tt = np.arange(n) / SR; out = np.zeros(n)
    for k, m in enumerate(ms):
        o = int(k * gap * SR); s = np.sin(2 * np.pi * midi(m) * tt + 1.5 * np.sin(2 * np.pi * midi(m) * 2 * tt) * np.exp(-tt * 8)) * env(n, .002, d); out[o:] += s[:n - o]
    return out
place(sfx, whoosh(.45, 3000, 400), 0.05, .25); place(sfx, pop(), 0.5, .7); place(sfx, blip(1400, .05), 0.62, .2)
place(sfx, whoosh(.6, 600, 6000), 0.65, .12)
for i in range(3): place(sfx, chime([79 + 2 * i]), EV[f"lesson_node_{i + 1}"], .12, pan=-.3 + .3 * i)
place(sfx, whoosh(.5, 400, 3000), 2.55, .15)
for i in range(3): place(sfx, blip(900 + 120 * i, .03) + .4 * blip(2600, .01), EV[f"tile_{i + 1}"] + .28, .35)
place(sfx, blip(500, .04), EV["check"], .35); place(sfx, chime([84, 88, 91], .6), EV["correct"], .2)
place(sfx, whoosh(.7, 200, 2500), EV["flame"] - .2, .25)
fl = lp(rng.standard_normal(int(1.6 * SR)), 900) * np.minimum(1, np.arange(int(1.6 * SR)) / SR / .2) * np.exp(-np.arange(int(1.6 * SR)) / SR / .9)
place(sfx, fl, EV["flame"], .15)
ticks = np.linspace(0, 1, 26) ** 1.8 * (EV["counter_end"] - EV["counter_start"]) + EV["counter_start"]
for j, tk in enumerate(ticks): place(sfx, blip(1800 + j * 20, .012), tk, .12)
place(sfx, chime([84, 91], .5), EV["counter_end"], .14)
place(sfx, whoosh(1.0, 300, 3500), EV["climb_start"], .2); place(sfx, chime([84, 88, 91, 96], .6, .06), EV["climb_end"], .17)
place(sfx, whoosh(.5, 2500, 500), 9.25, .15); place(sfx, blip(700, .05), 9.5, .25)
for i, k in enumerate(["station_languages", "station_numbers", "station_music", "station_chess"]):
    place(sfx, pop(), EV[k], .4, pan=-.3 + .2 * i); place(sfx, chime([72 + [0, 4, 7, 12][i]], .4), EV[k] + .02, .14)
place(sfx, whoosh(1.0, 200, 5000), EV["converge"], .2)
place(sfx, blip(300, .15) * 1.0, EV["msg_1"], .25); place(sfx, blip(450, .15), EV["msg_2"], .25)
place(sfx, whoosh(.4, 3000, 400), EV["duo_land"] - .4, .22); place(sfx, pop(), EV["duo_land"], .7)
place(sfx, whoosh(.6, 500, 6000), EV["wordmark"], .12)
place(sfx, whoosh(.5, 400, 4000), EV["to_endcard"], .2); place(sfx, chime([84, 91], .8), 19.05, .1)
sfx = reverb(sfx, 1.0, .12)

# ---------------- mix: duck music under the voice ----------------
v, vsr = sf.read(f"{ROOT}/audio/voice.wav"); v = resample_poly(v, 320, 147)[:N] if vsr == 22050 else resample_poly(v, SR, vsr)[:N]; v = np.pad(v, (0, N - len(v)))
e = lp(np.abs(v), 6)[:, None]; e = e / (e.max() + 1e-9)
duck = 1 - .55 * np.clip(e * 3, 0, 1)
voice = np.stack([v, v], 1) * 1.0
mix = music * duck + sfx + voice
fade = np.clip((DURATION - T) / .6, 0, 1)[:, None]; mix *= fade
os.makedirs(f"{ROOT}/audio/stems", exist_ok=True)
for name, x in (("music", music * duck), ("sfx", sfx), ("voice", voice), ("mix_raw", mix)):
    sf.write(f"{ROOT}/audio/stems/{name}.wav", (x / max(1e-9, np.abs(mix).max()) * .7).astype(np.float32), SR)
print("ok")
