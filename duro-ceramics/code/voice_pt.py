"""PT-PT narration: ElevenLabs voice "Ines" (via Higgsfield text2speech_v2), one file per line in audio/voice_raw/.
Shortens long internal pauses, speeds each line up slightly and places it on its beat -> audio/voice_pt.wav
Usage: python3 code/voice_pt.py"""
import json, os, subprocess, sys
import numpy as np, soundfile as sf
from scipy.ndimage import uniform_filter1d
sys.path.insert(0, os.path.dirname(__file__))
from timing import DURATION, VOICE_PT

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SR = 48000; TEMPO = 1.07; MAX_PAUSE = 0.24

def load(i):
    src = f"{ROOT}/audio/voice_raw/l{i}.mp3"; tmp = f"{ROOT}/audio/voice_raw/l{i}_48k.wav"
    subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-i", src, "-ac", "1", "-ar", str(SR), tmp], check=True)
    x, _ = sf.read(tmp); return x

def tighten(x):
    """shorten internal silences longer than MAX_PAUSE (keeps a short crossfade)"""
    e = uniform_filter1d(np.abs(x), int(.02 * SR)); quiet = e < 0.006
    nz = np.nonzero(~quiet)[0]; x = x[max(0, nz[0] - 240): nz[-1] + 2400]; quiet = quiet[max(0, nz[0] - 240): nz[-1] + 2400]
    out = []; i = 0; n = len(x)
    while i < n:
        if quiet[i]:
            j = i
            while j < n and quiet[j]: j += 1
            if (j - i) / SR > MAX_PAUSE and i > 0 and j < n:
                keep = int(MAX_PAUSE * SR); h = keep // 2
                out.append(x[i:i + h]); out.append(x[j - h:j])
            else: out.append(x[i:j])
            i = j
        else:
            j = i
            while j < n and not quiet[j]: j += 1
            out.append(x[i:j]); i = j
    return np.concatenate(out)

def speed(x, tempo):
    a, b = f"{ROOT}/audio/voice_raw/_in.wav", f"{ROOT}/audio/voice_raw/_out.wav"
    sf.write(a, x, SR)
    subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-i", a, "-af", f"atempo={tempo}", b], check=True)
    y, _ = sf.read(b); return y

if __name__ == "__main__":
    track = np.zeros(int(DURATION * SR)); timing = []
    for i, (t0, text, tempo) in enumerate(VOICE_PT, 1):
        s = speed(tighten(load(i)), tempo or TEMPO)
        s = s * np.minimum(1, np.arange(len(s)) / 240)  # tiny fade-in
        k = int(t0 * SR); track[k:k + len(s)] += s[:len(track) - k]
        timing.append({"t0": t0, "t1": round(t0 + len(s) / SR, 3), "text": text}); print(f"{t0:6.2f}-{t0 + len(s) / SR:6.2f}  {text}")
    for a, b in zip(timing, timing[1:]):
        if a["t1"] > b["t0"] - 0.12: print("TOO CLOSE / OVERLAP:", a["text"], "->", b["text"])
    sf.write(f"{ROOT}/audio/voice_pt.wav", track.astype(np.float32), SR)
    json.dump(timing, open(f"{ROOT}/audio/voice_timing_pt.json", "w"), indent=1, ensure_ascii=False)
