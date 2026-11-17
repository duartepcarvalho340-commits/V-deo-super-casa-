"""Narration for the Panic & Profit launch reel (Kokoro, voice af_heart), phrase by phrase on its beat."""
import json, os, numpy as np, soundfile as sf
from kokoro_onnx import Kokoro

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PHRASES = [  # (start s, text)
    (0.30, "Markets slide. Oil spikes. Rates up again."),
    (3.75, "Every headline moves your money."),
    (6.30, "We explain what's really behind it."),
    (8.55, "Geopolitics."),
    (9.55, "Macro."),
    (10.45, "Markets."),
    (11.75, "No jargon. No panic."),
    (13.55, "Understand the world. Invest better."),
    (16.15, "Panic and Profit."),
    (17.55, "Follow at panic and profit."),
]
VOICE, SPEED, DUR = "af_heart", 1.02, 21.0

if __name__ == "__main__":
    k = Kokoro(f"{ROOT}/assets/voice/kokoro-v1.0.onnx", f"{ROOT}/assets/voice/voices-v1.0.bin")
    sr = 24000; track = np.zeros(int(DUR * sr), np.float32); timing = []; prev = 0
    for t0, text in PHRASES:
        s, sr = k.create(text, voice=VOICE, speed=SPEED, lang="en-us")
        nz = np.nonzero(np.abs(s) > 0.01)[0]; s = s[max(0, nz[0] - 240): nz[-1] + 1800]
        i = int(t0 * sr); track[i:i + len(s)] += s[:len(track) - i]
        t1 = t0 + len(s) / sr; flag = "  <-- OVERLAP" if t0 < prev else ""
        timing.append({"t0": t0, "t1": round(t1, 3), "text": text}); prev = t1
        print(f"{t0:6.2f}-{t1:6.2f}  {text}{flag}")
    sf.write(f"{ROOT}/audio/voice_en.wav", track, sr)
    json.dump(timing, open(f"{ROOT}/audio/voice_timing_en.json", "w"), indent=1)
