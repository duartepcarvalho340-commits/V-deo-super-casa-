"""Narration (Kokoro af_heart, en-US) for the Asia AI-chip Reel (2026-11-20). US close numbers come from numbers.json."""
import json, os, numpy as np, soundfile as sf
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
N = json.load(open(f"{ROOT}/numbers.json"))
def pct(x):
    a = abs(x); w = {0: "zero", 1: "one", 2: "two", 3: "three", 4: "four", 5: "five", 6: "six", 7: "seven", 8: "eight", 9: "nine"}
    i, d = int(a), round((a - int(a)) * 10)
    if d == 10: i, d = i + 1, 0
    s = w.get(i, str(i)) if i or not d else "zero"
    if d: s += f" point {w[d]}"
    return s + " percent"
def us_line():
    col = "green" if N["sp_day"] > 0 else "red"
    vd = "rose" if N["sp_day"] > 0 else "fell"; vw = "gained" if N["sp_week"] > 0 else "lost"
    return (f"Back in New York, this morning we asked: red or green? The answer: {col}. "
            f"The S&P 500 {vd} {pct(N['sp_day'])} today, and {vw} {pct(N['sp_week'])} this week.")
PHRASES = [
    (0.30, "Taiwan's stock market just had its worst week since 1991."),
    (0.40, "While America slept, yesterday's AI selloff hit Asia. And it hit harder."),
    (0.35, "Taiwan fell six percent today, and seventeen and a half percent this week."),
    (0.35, "South Korea and Japan both fell five percent. Samsung and SK Hynix, down six."),
    (0.40, "Why Taiwan? It is the world's AI chip factory. TSMC alone is about forty percent of the index, and it makes the chips for Nvidia, AMD and Apple."),
    (0.30, "So when investors doubt AI, Taiwan feels it first."),
    (0.45, us_line()),
    (0.40, "For long-term investors, one bad week is not the story. The real question is whether AI profits can grow into these prices."),
    (0.45, "Your call: AI bubble, or a bump on a long road? Comment BUBBLE or BUMP."),
]
VOICE, SPEED, DUR = "af_heart", 1.15, 80.0
if __name__ == "__main__":
    from kokoro_onnx import Kokoro
    k = Kokoro(f"{ROOT}/assets/voice/kokoro-v1.0.onnx", f"{ROOT}/assets/voice/voices-v1.0.bin")
    sr = 24000; track = np.zeros(int(DUR * sr), np.float32); timing = []; prev = 0
    for gap, text in PHRASES:
        t0 = round(prev + gap, 2)
        s, sr = k.create(text, voice=VOICE, speed=SPEED, lang="en-us")
        nz = np.nonzero(np.abs(s) > 0.01)[0]; s = s[max(0, nz[0] - 240): nz[-1] + 2400]
        i = int(t0 * sr); track[i:i + len(s)] += s[:len(track) - i]; t1 = t0 + len(s) / sr; prev = t1
        timing.append({"t0": t0, "t1": round(t1, 3), "text": text}); print(f"{t0:6.2f}-{t1:6.2f}  {text}")
    sf.write(f"{ROOT}/audio/voice.wav", track, sr); json.dump(timing, open(f"{ROOT}/audio/voice_timing.json", "w"), indent=1)
