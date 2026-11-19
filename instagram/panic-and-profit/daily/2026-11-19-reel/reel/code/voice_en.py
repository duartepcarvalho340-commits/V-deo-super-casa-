"""Narration (Kokoro af_heart, en-US). Each phrase placed at its start time; writes audio/voice.wav + timing json."""
import json, sys, numpy as np, soundfile as sf
from kokoro_onnx import Kokoro
import os
OPEN_LINE = os.environ.get("OPEN_LINE", "Shares start trading on the Nasdaq today.")
PHRASES = [  # (gap before phrase in s, text) -> placed back to back
    (0.30, "The biggest IPO in history just priced."),
    (0.35, "Anthropic sold shares at eighty-three dollars, above its range, raising about eighty-one billion."),
    (0.30, "That values it near one point five trillion."),
    (0.35, "Revenue grew about fourteen times in a year."),
    (0.30, "But the price is roughly forty-six times sales. You're paying for years of growth."),
    (0.35, "And the eighty billion dollar loss? Mostly a non-cash revaluation."),
    (0.35, OPEN_LINE),
    (0.35, "Day one is the headline. The numbers are the story."),
]
VOICE, SPEED, DUR = "af_heart", 1.15, 34.0
if __name__ == "__main__":
    k = Kokoro("assets/voice/kokoro-v1.0.onnx", "assets/voice/voices-v1.0.bin")
    sr = 24000; track = np.zeros(int(DUR * sr), np.float32); timing = []; prev = 0
    for gap, text in PHRASES:
        t0 = round(prev + gap, 2)
        s, sr = k.create(text, voice=VOICE, speed=SPEED, lang="en-us")
        nz = np.nonzero(np.abs(s) > 0.01)[0]; s = s[max(0, nz[0] - 240): nz[-1] + 2400]
        i = int(t0 * sr); track[i:i + len(s)] += s[:len(track) - i]; t1 = t0 + len(s) / sr
        flag = "  <-- OVERLAP" if t0 < prev else ""; prev = t1
        timing.append({"t0": t0, "t1": round(t1, 3), "text": text}); print(f"{t0:6.2f}-{t1:6.2f}  {text}{flag}")
    sf.write("audio/voice.wav", track, sr); json.dump(timing, open("audio/voice_timing.json", "w"), indent=1)
