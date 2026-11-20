"""Narration (Kokoro af_heart, en-US). Each phrase placed at its start time; writes audio/voice.wav + timing json."""
import json, sys, numpy as np, soundfile as sf
from kokoro_onnx import Kokoro
PHRASES = [  # (gap before phrase in s, text) -> placed back to back
    (0.30, "Three retail giants reported this week. Same shopper. Three very different stock reactions."),
    (0.40, "Target: sales at stores open at least a year rose five point six percent, versus three point eight expected. The stock jumped about seven percent."),
    (0.40, "Walmart beat and raised its outlook. The stock still slipped: its sales forecast fell short of what Wall Street wanted."),
    (0.40, "Home Depot grew sales, but fewer customers came through the door, and it cut its profit outlook. Shares fell about three percent."),
    (0.40, "The lesson: stocks don't react to good or bad. They react to better or worse than expected."),
    (0.40, "And the shopper? Still spending on everyday basics. Big home projects, not so much."),
    (0.45, "Your call: which retailer looks strongest to you? Comment W M T, T G T, or H D."),
]
VOICE, SPEED, DUR = "af_heart", 1.15, 70.0
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
