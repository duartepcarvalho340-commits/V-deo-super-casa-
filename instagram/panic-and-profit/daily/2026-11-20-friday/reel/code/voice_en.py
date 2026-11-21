"""Narration (Kokoro af_heart) for the Friday crash Reel (2026-11-20, 6pm ET)."""
import json, os, numpy as np, soundfile as sf
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PHRASES = [
    (0.30, "Yesterday, Wall Street had the worst day of this selloff. The Nasdaq crashed more than five percent."),
    (0.40, "The S&P 500 fell three point seven percent, its seventh straight loss. Over the whole week, it lost more than eight percent."),
    (0.35, "Three blows hit at once."),
    (0.35, "Blow one: Reuters reported that the SEC is examining Nvidia's accounting. Nvidia fell fourteen percent. AMD and Broadcom, down twelve or more."),
    (0.35, "Blow two: President Trump threatened a tremendous tax on companies that build AI data centers overseas."),
    (0.35, "Blow three: the AI doubts never left. Not Nvidia's earnings, not Anthropic's IPO could stop the selling."),
    (0.40, "Now the Nasdaq is negative for 2026, and the S&P 500 is in a correction."),
    (0.40, "Remember: a report is not a verdict. Nvidia has not been charged with anything. Long-term investors follow the facts, not the fear."),
    (0.45, "Your call: is this panic, or profit? Comment PANIC or PROFIT."),
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
