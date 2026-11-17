"""Generate the narration phrase by phrase (Kokoro, voice af_heart) and place each phrase on its beat."""
import json, numpy as np, soundfile as sf
from kokoro_onnx import Kokoro

PHRASES = [  # (start time in seconds, text)
    (0.35, "Start with a little curiosity."),
    (2.2, "Turn a lesson into a daily habit."),
    (5.05, "Keep your streak going,"),
    (7.30, "climb a little higher,"),
    (9.35, "and find the confidence to speak."),
    (11.60, "Explore languages, numbers, music and chess."),
    (15.10, "Small steps."),
    (16.25, "More possibilities."),
    (17.75, "Duolingo."),
]
VOICE, SPEED, DUR = "af_heart", 0.97, 21.0

if __name__ == "__main__":
    k = Kokoro("assets/voice/kokoro-v1.0.onnx", "assets/voice/voices-v1.0.bin")
    sr = 24000; track = np.zeros(int(DUR * sr), np.float32); timing = []
    for t0, text in PHRASES:
        s, sr = k.create(text, voice=VOICE, speed=SPEED, lang="en-us")
        nz = np.nonzero(np.abs(s) > 0.01)[0]; s = s[max(0, nz[0] - 240): nz[-1] + 2400]  # trim silence
        i = int(t0 * sr); track[i:i + len(s)] += s[:len(track) - i]
        timing.append({"t0": t0, "t1": round(t0 + len(s) / sr, 3), "text": text})
        print(f"{t0:6.2f}-{t0 + len(s) / sr:6.2f}  {text}")
    sf.write("audio/voice.wav", track, sr)
    json.dump(timing, open("audio/voice_timing.json", "w"), indent=1)
