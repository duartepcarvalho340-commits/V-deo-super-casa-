"""Narration (Kokoro af_heart, en-US). Each phrase placed at its start time; writes audio/voice.wav + timing json."""
import json, sys, numpy as np, soundfile as sf
from kokoro_onnx import Kokoro
import os
MARKET_LINE = os.environ.get("MARKET_LINE", "By the close, the damage was clear: chip stocks were among the day's biggest losers.")
PHRASES = [  # (gap before phrase in s, text) -> placed back to back
    (0.30, "AMD lost up to nine percent in a single morning. The trigger? A short seller."),
    (0.40, "Hunterbrook, which is betting against the stock, published a report today."),
    (0.35, "It alleges that a Chinese server maker, blacklisted by the US since 2025, kept shipping updates with newer AMD firmware."),
    (0.40, "AMD has not responded. And the report itself says it does not prove AMD broke any export rules."),
    (0.40, "So why the drop? Export risk hits what investors pay for: future sales."),
    (0.35, MARKET_LINE),
    (0.40, "The lesson: a short report is a claim, not a verdict. Watch for the company's answer, and for regulators."),
    (0.45, "Your call: buying the dip, or catching a falling knife? Comment dip, or knife."),
]
VOICE, SPEED, DUR = "af_heart", 1.12, 60.0
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
