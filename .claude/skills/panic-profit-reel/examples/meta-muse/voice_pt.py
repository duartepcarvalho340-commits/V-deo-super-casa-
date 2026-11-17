"""PT-PT narration (Piper voice pt_PT-dii-high), phrase by phrase on its beat -> audio/voice.wav"""
import json, numpy as np, soundfile as sf
from piper import PiperVoice, SynthesisConfig

PHRASES = [  # (start, text)
    (0.20, "Pede uma vez."),
    (1.45, "A Muse trata do resto."),
    (3.10, "Marca a viagem,"),
    (5.10, "envia o email,"),
    (7.30, "faz a compra."),
    (9.30, "Continua a trabalhar quando fechas a app,"),
    (11.55, "e lembra-se do que gostas."),
    (13.30, "No telemóvel, no Mac, no WhatsApp."),
    (16.00, "Menos tarefas."),
    (17.25, "Mais tempo."),
    (18.30, "Muse, da Meta."),
]
VOICE = "pt_PT-dii-high"; DUR = 21.75; LENGTH_SCALE = 0.95

if __name__ == "__main__":
    d = f"assets/voice/vits-piper-{VOICE}"; v = PiperVoice.load(f"{d}/{VOICE}.onnx", config_path=f"{d}/{VOICE}.onnx.json")
    sr = v.config.sample_rate; track = np.zeros(int(DUR * sr), np.float32); timing = []
    for t0, text in PHRASES:
        s = np.concatenate([c.audio_float_array for c in v.synthesize(text, syn_config=SynthesisConfig(length_scale=LENGTH_SCALE))])
        nz = np.nonzero(np.abs(s) > 0.01)[0]; s = s[max(0, nz[0] - 200): nz[-1] + 2000]
        i = int(t0 * sr); track[i:i + len(s)] += s[:len(track) - i]
        timing.append({"t0": t0, "t1": round(t0 + len(s) / sr, 3), "text": text}); print(f"{t0:6.2f}-{t0 + len(s) / sr:6.2f}  {text}")
    sf.write("audio/voice.wav", track, sr); json.dump(timing, open("audio/voice_timing.json", "w"), indent=1, ensure_ascii=False)
