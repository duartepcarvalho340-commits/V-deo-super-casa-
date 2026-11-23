"""Narration (Kokoro af_heart) for the Day-1-after-the-crash Reel (Mon 2026-11-23). Lines built from numbers.json."""
import json, os, numpy as np, soundfile as sf
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
N = json.load(open(f"{ROOT}/numbers.json"))
W = {0: "zero", 1: "one", 2: "two", 3: "three", 4: "four", 5: "five", 6: "six", 7: "seven", 8: "eight", 9: "nine", 10: "ten",
     11: "eleven", 12: "twelve", 13: "thirteen", 14: "fourteen", 15: "fifteen", 16: "sixteen", 17: "seventeen", 18: "eighteen", 19: "nineteen", 20: "twenty"}
def pct(x):
    a = round(abs(x), 1); i = int(a); d = int(round((a - i) * 10))
    s = W.get(i, str(i))
    if d: s += f" point {W[d]}"
    return s + " percent"
def pts(x):
    a = int(round(abs(x), -1)) if abs(x) >= 100 else int(round(abs(x)))
    return f"{a:,}".replace(",", " thousand ") if False else f"{a}"
RECORD = 7818.93
def lines():
    up = N["sp"] > 0
    v = lambda x: "rose" if x > 0 else "fell"
    dow = "gained" if N["dow_pts"] > 0 else "lost"
    from_rec = (1 - N["sp_close"] / RECORD) * 100
    L = [
        "Monday was the first real test after Wall Street's brutal week.",
        f"The S&P 500 {v(N['sp'])} {pct(N['sp'])}. The Nasdaq {v(N['ndq'])} {pct(N['ndq'])}. And the Dow {dow} {abs(int(round(N['dow_pts'])))} points.",
        (("A relief rally. But one green day does not end a correction." if from_rec >= 10 else
          "The best day since April 2025. Strong enough to lift the S&P 500 out of correction territory, for now.") if up else
         "No relief. The S&P 500 just logged its eighth straight loss."),
        f"The spark: Nvidia {v(N['nvda'])} {pct(N['nvda'])}, after its board brought back Jensen Huang as CEO.",
        f"Zoom out: the S&P 500 is still about {pct(round(from_rec))} below its October record.",
        "Next up: Dell's earnings tomorrow, and Wednesday's inflation data.",
        "One day is not a trend. Long-term investors watch the direction, not the noise.",
        "Your call: is the worst behind us, or still ahead? Comment BEHIND or AHEAD.",
    ]
    return L
GAPS = [0.3, 0.4, 0.35, 0.4, 0.35, 0.35, 0.4, 0.45]
VOICE, SPEED, DUR = "af_heart", 1.15, 80.0
if __name__ == "__main__":
    from kokoro_onnx import Kokoro
    k = Kokoro(f"{ROOT}/assets/voice/kokoro-v1.0.onnx", f"{ROOT}/assets/voice/voices-v1.0.bin")
    sr = 24000; track = np.zeros(int(DUR * sr), np.float32); timing = []; prev = 0
    for gap, text in zip(GAPS, lines()):
        t0 = round(prev + gap, 2)
        s, sr = k.create(text, voice=VOICE, speed=SPEED, lang="en-us")
        nz = np.nonzero(np.abs(s) > 0.01)[0]; s = s[max(0, nz[0] - 240): nz[-1] + 2400]
        i = int(t0 * sr); track[i:i + len(s)] += s[:len(track) - i]; t1 = t0 + len(s) / sr; prev = t1
        timing.append({"t0": t0, "t1": round(t1, 3), "text": text}); print(f"{t0:6.2f}-{t1:6.2f}  {text}")
    sf.write(f"{ROOT}/audio/voice.wav", track, sr); json.dump(timing, open(f"{ROOT}/audio/voice_timing.json", "w"), indent=1)
