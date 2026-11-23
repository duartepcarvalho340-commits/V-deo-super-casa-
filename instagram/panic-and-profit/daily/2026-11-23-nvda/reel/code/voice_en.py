"""Narration (Kokoro af_heart) for the Nvidia comeback Reel (Mon 2026-11-23, intraday)."""
import json, os, numpy as np, soundfile as sf
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PHRASES = [
    (0.30, "Nvidia just staged one of the biggest comebacks in its history."),
    (0.35, "The stock jumped more than twenty-five percent this morning, one of its best days ever."),
    (0.35, "Why? Nvidia's board reinstated Jensen Huang as CEO, just eleven days after he stepped down."),
    (0.30, "President Trump had urged the board to bring him back."),
    (0.35, "The whole market followed. The Nasdaq opened more than six percent higher."),
    (0.35, "But remember: on Friday, Nvidia lost fourteen percent in a single day."),
    (0.30, "And the SEC review of its accounting, reported by Reuters, is still out there."),
    (0.35, "For long-term investors: the CEO is back. The questions are not gone."),
    (0.45, "Your call: Nvidia, real comeback or just a bounce? Comment COMEBACK or BOUNCE."),
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
