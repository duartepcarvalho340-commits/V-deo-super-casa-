"""Narration (Kokoro af_heart, en-US). Each phrase placed at its start time; writes audio/voice.wav + timing json."""
import json, sys, numpy as np, soundfile as sf
from kokoro_onnx import Kokoro
PHRASES = [  # (gap before phrase in s, text) -> placed back to back
    (0.30, "Wall Street just had a brutal day. The Dow lost more than eleven hundred points."),
    (0.40, "The S&P 500 fell two percent, its sixth straight loss. And the tech-heavy Nasdaq, home of the AI giants, fell even more."),
    (0.40, "Why? Follow the AI dominoes."),
    (0.35, "Domino one: AI leadership. Nvidia, the face of the boom, lost its CEO, and a short seller hit AMD."),
    (0.35, "Domino two: the AI IPO test. Anthropic opened up thirty-four percent, then gave back half. It could not revive confidence in AI."),
    (0.35, "Domino three: rates. Markets expect another Fed hike, and higher rates hit the priciest growth stocks first."),
    (0.40, "Now, perspective. Since 1980, the S&P 500 has dropped about fourteen percent at some point in an average year. And still finished higher in roughly three out of four years."),
    (0.40, "Eight percent off the top hurts. It is not unusual."),
    (0.45, "Your call: is the AI bubble popping, or is this just a bump on a long road? Comment BUBBLE or BUMP."),
]
VOICE, SPEED, DUR = "af_heart", 1.15, 80.0
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
