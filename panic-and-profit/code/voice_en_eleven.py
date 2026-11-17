"""Assemble the EN narration from the ElevenLabs takes (Higgsfield text2speech_v2, variant elevenlabs, preset voice
'Emily'). Raw takes live in audio/raw/: emily_p1 = "Markets slide. Oil spikes. Rates up again.", emily_rest = the
rest of the script read in one take. Each phrase is cut at its pause and placed on its beat (start s)."""
import json, os, numpy as np, soundfile as sf

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SR, DUR = 48000, 21.0
CUTS = [  # (take, cut start, cut end, place at, text)
    ("emily_p1",   0.00, 3.30, 0.25, "Markets slide. Oil spikes. Rates up again."),
    ("emily_rest", 0.00, 1.60, 3.75, "Every headline moves your money."),
    ("emily_rest", 1.80, 3.66, 6.30, "We explain what's really behind it."),
    ("emily_rest", 3.74, 5.07, 8.32, "Geopolitics."),
    ("emily_rest", 5.24, 6.10, 9.64, "Macro."),
    ("emily_rest", 6.44, 7.27, 10.56, "Markets."),
    ("emily_rest", 7.66, 8.63, 11.72, "No jargon."),
    ("emily_rest", 9.09, 10.01, 12.70, "No panic."),
    ("emily_rest", 10.44, 11.56, 13.66, "Understand the world."),
    ("emily_rest", 11.89, 12.82, 14.80, "Invest better."),
    ("emily_rest", 13.24, 14.60, 16.12, "Panic and Profit."),
    ("emily_rest", 14.96, 16.84, 17.50, "Follow at panic and profit."),
]
if __name__ == "__main__":
    takes = {k: sf.read(f"{ROOT}/audio/raw/{k}.wav")[0] for k in {c[0] for c in CUTS}}
    track = np.zeros(int(DUR * SR)); timing = []; prev = 0
    for k, a, b, t0, text in CUTS:
        s = takes[k][int(a * SR):int(b * SR)].copy(); f = int(.012 * SR)
        s[:f] *= np.linspace(0, 1, f); s[-f:] *= np.linspace(1, 0, f)   # click-free edges
        i = int(t0 * SR); track[i:i + len(s)] += s[:len(track) - i]
        t1 = t0 + len(s) / SR; flag = "  <-- OVERLAP" if t0 < prev else ""
        timing.append({"t0": t0, "t1": round(t1, 3), "text": text}); prev = t1
        print(f"{t0:6.2f}-{t1:6.2f}  {text}{flag}")
    sf.write(f"{ROOT}/audio/voice_en.wav", track.astype(np.float32), SR)
    json.dump(timing, open(f"{ROOT}/audio/voice_timing_en.json", "w"), indent=1)
