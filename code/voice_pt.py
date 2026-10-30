"""PT-PT narration (Piper voice pt_PT-dii-high), phrase by phrase on its beat -> audio/voice_pt.wav"""
import json, numpy as np, soundfile as sf
from piper import PiperVoice, SynthesisConfig

PHRASES = [  # (start, text)
    (0.45, "Cada casa começa com uma história."),
    (3.3, "Compre ou arrende, de norte a sul do país."),
    (7.0, "Explore o mapa, ou o que está perto de si."),
    (10.45, "Guarde as que mais gosta."),
    (12.1, "E receba alertas mal surja uma casa nova."),
    (15.3, "Super Casa."),
    (16.45, "O seu próximo capítulo começa aqui."),
]
VOICE = "pt_PT-dii-high"; DUR = 21.0; LENGTH_SCALE = 0.93

if __name__ == "__main__":
    d = f"assets/voice/vits-piper-{VOICE}"; v = PiperVoice.load(f"{d}/{VOICE}.onnx", config_path=f"{d}/{VOICE}.onnx.json")
    sr = v.config.sample_rate; track = np.zeros(int(DUR * sr), np.float32); timing = []
    for t0, text in PHRASES:
        s = np.concatenate([c.audio_float_array for c in v.synthesize(text, syn_config=SynthesisConfig(length_scale=LENGTH_SCALE))])
        nz = np.nonzero(np.abs(s) > 0.01)[0]; s = s[max(0, nz[0] - 200): nz[-1] + 2000]
        i = int(t0 * sr); track[i:i + len(s)] += s[:len(track) - i]
        timing.append({"t0": t0, "t1": round(t0 + len(s) / sr, 3), "text": text}); print(f"{t0:6.2f}-{t0 + len(s) / sr:6.2f}  {text}")
    for a, b in zip(timing, timing[1:]):
        if a["t1"] > b["t0"]: print("OVERLAP", a["text"], "->", b["text"])
    sf.write("audio/voice_pt.wav", track, sr); json.dump(timing, open("audio/voice_timing_pt.json", "w"), indent=1, ensure_ascii=False)
