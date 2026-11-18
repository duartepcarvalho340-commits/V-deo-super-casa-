"""Original score + SFX for the Panic & Profit Reel (Nvidia CEO exit vs record quarter). E minor, 112 BPM:
nervous pulse in the PANIC half, lifts to G major in the PROFIT half, resolves on the end card. Music ducks under the narration."""
import os, sys
import numpy as np, soundfile as sf
from scipy.signal import butter, sosfilt, fftconvolve, resample_poly
sys.path.insert(0, os.path.dirname(__file__))
from timing import DURATION, BOUNDS, EVENTS as EV
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

BPM = 112; BEAT = 60 / BPM; BAR = 4 * BEAT; END = BOUNDS[-1]
CHP = [[52, 55, 59, 64], [48, 52, 55, 60], [50, 54, 57, 62], [47, 50, 54, 59]]  # Em - C - D - Bm (panic)
CHG = [[55, 59, 62, 67], [50, 54, 57, 62], [52, 55, 59, 64], [48, 52, 55, 60]]  # G - D - Em - C (profit)
CH = CHP
BASSP = [40, 36, 38, 35]; BASSG = [43, 38, 40, 36]
BASS = BASSP
def chords(t): return CHG if t >= 11.75 else CHP
def basses(t): return BASSG if t >= 11.75 else BASSP
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
chord = sum(np.sin(2 * np.pi * midi(m) * tt) * (1 if m < 70 else .5) for m in (43, 55, 62, 67, 71, 74))
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
place(sfx, thud(), EV["ceo_out"], .7); place(sfx, blip(220, .2), EV["ceo_out"], .2)
place(sfx, blip(1200, .05), EV["chip"], .3); place(sfx, blip(midi(79), .3), EV["record"], .25)
for tt0 in (4.45, 11.6, 22.3): place(sfx, whoosh(.6, 400, 4500), tt0, .22)
for k in ("card1", "card2"): place(sfx, whoosh(.45, 4000, 600), EV[k], .25); place(sfx, thud(), EV[k] + .35, .45)
place(sfx, whoosh(.8, 3000, 200), EV["ticker"], .25); place(sfx, thud(), EV["ticker"] + .3, .7)
place(sfx, riser(EV["rev_end"] - EV["rev_start"]), EV["rev_start"], .08); place(sfx, blip(midi(83), .3), EV["rev_end"], .25)
place(sfx, blip(1500, .06), EV["yoy"], .3)
for k in ("bar_exp", "bar_act", "guide"): place(sfx, blip(600 + 200 * ("bar_exp", "bar_act", "guide").index(k), .08), EV[k], .3)
place(sfx, thud(), EV["lesson_title"], .5)
for k in ("col_left", "col_right"): place(sfx, blip(900, .05), EV[k], .3)
place(sfx, blip(midi(79), .5) + .5 * blip(midi(86), .4), EV["end_logo"], .2)
sfx = reverb(sfx, .9, .1)

v, vsr = sf.read(f"{ROOT}/audio/voice.wav"); v = resample_poly(v, SR, vsr)[:N]; v = np.pad(v, (0, N - len(v)))
e = lp(np.abs(v), 6)[:, None]; e /= e.max() + 1e-9
duck = 1 - .6 * np.clip(e * 3, 0, 1); voice = np.stack([v, v], 1)
mix = music * duck + sfx + voice; mix *= np.clip((DURATION - T) / .5, 0, 1)[:, None]
os.makedirs(f"{ROOT}/audio/stems", exist_ok=True)
sf.write(f"{ROOT}/audio/stems/mix_raw.wav", (mix / np.abs(mix).max() * .7).astype(np.float32), SR); print("ok")
