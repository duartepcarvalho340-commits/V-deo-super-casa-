"""Narration (Kokoro af_heart) for the VIX fear-gauge Reel (2026-11-22)."""
import json, os, numpy as np, soundfile as sf
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PHRASES = [
    (0.30, "Wall Street's fear gauge just hit its highest close since April 2025."),
    (0.40, "On Friday, the VIX closed near thirty-six, after touching forty during the day."),
    (0.35, "What is the VIX? Think of it as the price of crash insurance. When investors panic, they pay up to protect their portfolios, and the VIX jumps."),
    (0.35, "Below twenty is calm. Above thirty is fear. Above forty is panic."),
    (0.40, "Now the twist. Since 1998, when the VIX crossed thirty-five, the S&P 500 was up about twenty-eight percent a year later, on average."),
    (0.35, "Not every time. In 2008, fear spiked and stocks kept falling for months."),
    (0.40, "But fear is usually loudest near the bottom, not the top. That's when panic selling does the most damage."),
    (0.45, "Your call: is this fear a warning, or an opportunity? Comment WARNING or OPPORTUNITY."),
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
