"""Original score + SFX for the Panic & Profit Reel (Asia AI chips). A minor, 100 BPM, tense pulse;
counter ticks, domino clacks on every fall, lifts to C major at the perspective scene. Music ducks under the narration."""
import os, sys
import numpy as np, soundfile as sf
from scipy.signal import butter, sosfilt, fftconvolve, resample_poly
sys.path.insert(0, os.path.dirname(__file__))
import sys as _sys; _sys.path.insert(0, os.path.dirname(__file__))
from timing import DURATION, P, END
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SR = 48000; N = int(DURATION * SR); T = np.arange(N) / SR; rng = np.random.default_rng(7)
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
def reverb(x, secs=1.4, mix=.18):
    n = int(secs * SR); tt = np.arange(n) / SR
    ir = lp(rng.standard_normal((n, 2)) * np.exp(-tt * 6.9 / secs)[:, None], 6000); ir /= np.sqrt((ir ** 2).sum(0))
    return x * (1 - mix) + np.stack([fftconvolve(x[:, c], ir[:, c])[:N] for c in range(2)], 1) * mix * 2.2

import json as _j
_UP = _j.load(open(os.path.join(ROOT, 'numbers.json')))['sp'] > 0
BPM = 100; BEAT = 60 / BPM; BAR = 4 * BEAT
CHP = [[57, 60, 64, 69], [53, 57, 60, 65], [55, 59, 62, 67], [52, 55, 59, 64]]  # Am - F - G - Em
CHG = [[48, 52, 55, 60], [55, 59, 62, 67], [57, 60, 64, 69], [53, 57, 60, 65]]  # C - G - Am - F
CH = CHP
BASSP = [45, 41, 43, 40]; BASSG = [36, 43, 45, 41]
BASS = BASSP
def chords(t): return CHG if (t >= P[6] or _UP) else CHP
def basses(t): return BASSG if (t >= P[6] or _UP) else BASSP
music = np.zeros((N, 2))
def pluck(f, n): t = np.arange(n) / SR; return (np.sin(2 * np.pi * f * t) + .3 * np.sin(4 * np.pi * f * t)) * np.exp(-t * 9)
t = 0.0; k = 0
while t < END:  # sixteenth-note pulse (tension)
    ch = chords(t)[int(t // BAR) % 4]; m = ch[[0, 2, 1, 3][k % 4]] + 12
    place(music, pluck(midi(m), int(.25 * SR)), t, .07 * (1.25 if k % 4 == 0 else 1), pan=.35 * np.sin(k * .9))
    t += BEAT / 4; k += 1
for b in range(int(END / BAR) + 1):  # dark pad
    n = int(BAR * SR * 1.05); tt = np.arange(n) / SR; ch = chords(b * BAR)[b % 4]
    s = sum(np.sin(2 * np.pi * midi(m) * tt + i) + .5 * np.sin(2 * np.pi * midi(m) * 1.003 * tt) for i, m in enumerate(ch))
    place(music, lp(s * np.minimum(1, tt / .4) * np.minimum(1, (n / SR - tt) / .3), 1400), b * BAR, .025)
t = 0.0
while t < END:  # bass + kick + hats
    n = int(BEAT * .95 * SR); tt = np.arange(n) / SR; f = midi(basses(t)[int(t // BAR) % 4])
    place(music, lp(np.sign(np.sin(2 * np.pi * f * tt)) * .6 + np.sin(2 * np.pi * f * tt), 600) * env(n, .005, .25), t, .16)
    kk = int(.3 * SR); kt = np.arange(kk) / SR
    place(music, np.sin(2 * np.pi * np.cumsum(48 + 110 * np.exp(-kt * 35)) / SR) * env(kk, .001, .13), t, .5)
    place(music, hp(rng.standard_normal(int(.04 * SR)), 8000) * env(int(.04 * SR), .0005, .01), t + BEAT / 2, .05)
    t += BEAT
# resolution: D major chord on the end card
n = int((DURATION - END) * SR); tt = np.arange(n) / SR
chord = sum(np.sin(2 * np.pi * midi(m) * tt) * (1 if m < 70 else .5) for m in (36, 48, 55, 60, 64, 67))
place(music, chord * np.minimum(1, tt / .04) * np.exp(-tt / 1.6) * .06, END)
music = reverb(music, 1.3, .14)

sfx = np.zeros((N, 2))
def blip(f, d=.06): n = int(.3 * SR); tt = np.arange(n) / SR; return np.sin(2 * np.pi * f * tt) * env(n, .001, d)
def thud(): n = int(.4 * SR); tt = np.arange(n) / SR; return np.sin(2 * np.pi * np.cumsum(70 + 160 * np.exp(-tt * 25)) / SR) * env(n, .001, .12)
def whoosh(dur=.5, f0=300, f1=4000):
    n = int(dur * SR); x = rng.standard_normal(n); out = np.zeros(n); seg = int(.01 * SR)
    for i in range(0, n, seg):
        f = f0 * (f1 / f0) ** (i / n); out[i:i + seg] = bp(x[max(0, i - 2048):i + seg], f * .7, min(f * 1.4, 20000))[-len(x[i:i + seg]):]
    return out * np.sin(np.pi * np.linspace(0, 1, n)) ** 2
def riser(dur): n = int(dur * SR); tt = np.arange(n) / SR; f = 200 * (6 ** (tt / dur)); return np.sin(2 * np.pi * np.cumsum(f) / SR) * (tt / dur) ** 2
import render as _r
for k_ in range(30): place(sfx, blip(900 + k_ * 30, .01), 0.4 + 3.0 * (k_ / 30) ** 0.7, .12)
place(sfx, riser(2.6), 0.6, .07); place(sfx, thud(), 3.4, .6); place(sfx, blip(midi(79), .3), _r.wtime("best", 1), .25)
place(sfx, blip(700, .08), _r.wtime("eleven", 2), .3)
for k in (3, 4, 6): place(sfx, blip(600, .08), P[k], .3)
place(sfx, thud(), P[5], .8)
for k in (2, 5, 7, 8): place(sfx, whoosh(.5, 600, 3000), P[k] - .15, .18)
place(sfx, blip(midi(72), .5) + .5 * blip(midi(79), .4), END + .2, .2)
sfx = reverb(sfx, .9, .1)

v, vsr = sf.read(f"{ROOT}/audio/voice.wav"); v = resample_poly(v, SR, vsr)[:N]; v = np.pad(v, (0, N - len(v)))
e = lp(np.abs(v), 6)[:, None]; e /= e.max() + 1e-9
duck = 1 - .6 * np.clip(e * 3, 0, 1); voice = np.stack([v, v], 1)
mix = music * duck + sfx + voice; mix *= np.clip((DURATION - T) / .5, 0, 1)[:, None]
os.makedirs(f"{ROOT}/audio/stems", exist_ok=True)
sf.write(f"{ROOT}/audio/stems/mix_raw.wav", (mix / np.abs(mix).max() * .7).astype(np.float32), SR); print("ok")
