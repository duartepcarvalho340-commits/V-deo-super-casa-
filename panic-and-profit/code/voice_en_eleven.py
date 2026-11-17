"""Assemble the EN narration from ElevenLabs takes (Higgsfield text2speech_v2, variant elevenlabs).
Raw takes live in audio/raw/<voice>_p1 ("Markets slide. Oil spikes. Rates up again.") and <voice>_rest (the rest of
the script read in one take). Each phrase is cut at its pause, optionally sped up without pitch change (ffmpeg atempo),
and placed on its beat. Usage: python3 code/voice_en_eleven.py [john|emily]   (default john, the current voice)"""
import json, os, subprocess, sys, tempfile, numpy as np, soundfile as sf

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SR, DUR = 48000, 21.0
VOICES = {
    # male, preset "John" — current version
    "john": [  # (take, cut start, cut end, place at, tempo, text)
        ("p1",   0.00, 1.32, 0.20, 1.2, "Markets slide."),
        ("p1",   1.47, 2.67, 1.36, 1.2, "Oil spikes."),
        ("p1",   2.83, 4.24, 2.40, 1.2, "Rates up again."),
        ("rest", 0.00, 1.71, 3.72, 1.0, "Every headline moves your money."),
        ("rest", 2.13, 3.99, 6.30, 1.0, "We explain what's really behind it."),
        ("rest", 4.47, 5.62, 8.30, 1.0, "Geopolitics."),
        ("rest", 5.99, 6.78, 9.60, 1.0, "Macro."),
        ("rest", 7.20, 8.02, 10.50, 1.0, "Markets."),
        ("rest", 8.32, 9.20, 11.70, 1.0, "No jargon."),
        ("rest", 9.47, 10.27, 12.65, 1.0, "No panic."),
        ("rest", 10.72, 12.00, 13.50, 1.0, "Understand the world."),
        ("rest", 12.27, 13.45, 14.78, 1.05, "Invest better."),
        ("rest", 13.91, 15.26, 16.25, 1.0, "Panic and Profit."),
        ("rest", 15.65, 17.68, 17.66, 1.08, "Follow at panic and profit."),
    ],
    # female, preset "Emily" — previous version
    "emily": [
        ("p1",   0.00, 3.30, 0.25, 1.0, "Markets slide. Oil spikes. Rates up again."),
        ("rest", 0.00, 1.60, 3.75, 1.0, "Every headline moves your money."),
        ("rest", 1.80, 3.66, 6.30, 1.0, "We explain what's really behind it."),
        ("rest", 3.74, 5.07, 8.32, 1.0, "Geopolitics."),
        ("rest", 5.24, 6.10, 9.64, 1.0, "Macro."),
        ("rest", 6.44, 7.27, 10.56, 1.0, "Markets."),
        ("rest", 7.66, 8.63, 11.72, 1.0, "No jargon."),
        ("rest", 9.09, 10.01, 12.70, 1.0, "No panic."),
        ("rest", 10.44, 11.56, 13.66, 1.0, "Understand the world."),
        ("rest", 11.89, 12.82, 14.80, 1.0, "Invest better."),
        ("rest", 13.24, 14.60, 16.12, 1.0, "Panic and Profit."),
        ("rest", 14.96, 16.84, 17.50, 1.0, "Follow at panic and profit."),
    ],
}
def tempo(x, f):
    if f == 1.0: return x
    with tempfile.TemporaryDirectory() as d:
        sf.write(f"{d}/a.wav", x, SR)
        subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-i", f"{d}/a.wav", "-af", f"atempo={f}", f"{d}/b.wav"], check=True)
        return sf.read(f"{d}/b.wav")[0]

if __name__ == "__main__":
    name = sys.argv[1] if len(sys.argv) > 1 else "john"
    takes = {k: sf.read(f"{ROOT}/audio/raw/{name}_{k}.wav")[0] for k in ("p1", "rest")}
    track = np.zeros(int(DUR * SR)); timing = []; prev = 0
    for k, a, b, t0, tf, text in VOICES[name]:
        s = tempo(takes[k][int(a * SR):int(b * SR)].copy(), tf); f = int(.012 * SR)
        s[:f] *= np.linspace(0, 1, f); s[-f:] *= np.linspace(1, 0, f)   # click-free edges
        i = int(t0 * SR); track[i:i + len(s)] += s[:len(track) - i]
        t1 = t0 + len(s) / SR; flag = "  <-- OVERLAP" if t0 < prev - 0.02 else ""
        timing.append({"t0": t0, "t1": round(t1, 3), "text": text}); prev = t1
        print(f"{t0:6.2f}-{t1:6.2f}  {text}{flag}")
    sf.write(f"{ROOT}/audio/voice_en.wav", track.astype(np.float32), SR)
    json.dump(timing, open(f"{ROOT}/audio/voice_timing_en.json", "w"), indent=1)
