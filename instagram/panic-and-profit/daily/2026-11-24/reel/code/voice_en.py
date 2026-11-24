"""Narration (Kokoro af_heart) for the bonds-vs-stocks Reel (2026-11-24)."""
import json, os, numpy as np, soundfile as sf
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PHRASES = [
    (0.30, "A ten-year US Treasury now pays almost five percent, backed by the US government."),
    (0.35, "So why take the risk of owning stocks?"),
    (0.35, "Here's the math. Flip the P/E, and you get the earnings yield: the profit you buy with every hundred dollars."),
    (0.35, "The S&P 500 trades at about seventeen and a half times next year's profits. That's an earnings yield near five point seven percent."),
    (0.35, "Bonds pay about four point nine. So the extra pay for owning stocks is less than one percentage point. That's thin."),
    (0.40, "But a bond's payment is fixed. Company profits can grow. That's the long-term edge."),
    (0.40, "Since 1928, stocks returned about ten percent a year on average. Ten-year Treasuries, about four and a half."),
    (0.35, "Stocks pay more over time, because they can hurt more along the way. Like last week."),
    (0.45, "Your call: at five percent, are bonds the smarter buy, or do stocks still win? Comment BONDS or STOCKS."),
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
