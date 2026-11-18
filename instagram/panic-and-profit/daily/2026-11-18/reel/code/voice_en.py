"""Narration (Kokoro af_heart, en-US). Each phrase placed at its start time; writes audio/voice.wav + timing json."""
import json, sys, numpy as np, soundfile as sf
from kokoro_onnx import Kokoro
PHRASES = [  # (gap before phrase in s, text) -> placed back to back
    (0.30, "Nvidia lost its CEO. Five days later, it posted a record quarter."),
    (0.40, "On November twelfth, Jensen Huang stepped down. CFO Colette Kress took over."),
    (0.30, "The stock fell over four percent that day."),
    (0.40, "Her first earnings: one hundred fifteen point eight billion in revenue, up one hundred three percent."),
    (0.30, "Wall Street expected about one hundred nine. The next-quarter guide: one hundred thirty."),
    (0.40, "The lesson: key-person risk is not the same as business risk."),
    (0.30, "The numbers held. The open question is who leads next."),
]
VOICE, SPEED, DUR = "af_heart", 1.15, 32.0
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
