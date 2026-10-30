"""Generate the English narration phrase by phrase (Kokoro, voice af_heart) and place each phrase on its beat."""
import json, numpy as np, soundfile as sf
from kokoro_onnx import Kokoro

PHRASES = [  # (start time in seconds, text)
    (0.45, "Every home starts with a story."),
    (3.35, "Search to buy or rent, anywhere in Portugal."),
    (7.05, "Explore the map, or what's right near you."),
    (10.5, "Save the ones you love."),
    (12.0, "And get alerts the moment a new home appears."),
    (15.4, "Super Casa."),
    (16.45, "Your next chapter starts here."),
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
    for a, b in zip(timing, timing[1:]):
        if a["t1"] > b["t0"] - 0.1: print("OVERLAP", a["text"], "->", b["text"])
    sf.write("audio/voice_en.wav", track, sr)
    json.dump(timing, open("audio/voice_timing_en.json", "w"), indent=1)
