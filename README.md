# SUPERCASA — spec ad (EN + PT)

Independent concept by Duarte Carvalho (@duartecarvalho) · **not affiliated with SUPERCASA / Janela Digital**.

**Concept — "Your next chapter":** the home search is shown as a pop-up book. Each page turn is a feature
(search buy/rent → map + near me → favourites + alerts), and the houses, cards and pins pop up from the paper.
At the end the book closes on the cover (logo + tagline) and opens once more onto the end card.
Colours: SUPERCASA blue + white only (blue table, white pages and cover, blue logo; approximate shades drawn in code, logo approximated).

## Files
- `code/timing.py` — page turns, events and all on-screen text (`TEXT["en"]`, `TEXT["pt"]`)
- `code/voice_en.py` — EN narration (Kokoro `af_heart`) → `audio/voice_en.wav`
- `code/voice_pt.py` — PT-PT narration (Piper `pt_PT-dii-high`) → `audio/voice_pt.wav`
- `code/audio.py` — original score (96 BPM, G major, plucked strings + piano) + paper SFX + ducking
- `code/render.py` — Skia renderer, `--orient L|V`, `--lang en|pt`
- `exports/` — final videos (1920×1080 and 1080×1920, 60 fps, H.264 + AAC, −14 LUFS / −1 dBTP)

## Re-render
```bash
bash <skill>/scripts/setup.sh . en          # Skia, fonts, Kokoro voice
python3 code/voice_en.py
python3 code/audio.py en
ffmpeg -i audio/stems/mix_raw_en.wav -af loudnorm=I=-14:TP=-1:LRA=11 -ar 48000 audio/mix_en.wav
python3 code/render.py --orient L --lang en --out exports/supercasa_spec_EN_1920x1080.mp4
python3 code/render.py --orient V --lang en --out exports/supercasa_spec_EN_1080x1920.mp4
# PT: python3 code/voice_pt.py && python3 code/audio.py pt && loudnorm -> audio/mix_pt.wav, then --lang pt (_PT_ files)
# stills: python3 code/render.py --orient V --scale 0.5 --out previews/s.png --still 1 4 8
```

## Licences
- Fonts: Inter (SIL OFL 1.1), Fraunces (SIL OFL 1.1, via @fontsource).
- Voices: Kokoro v1.0 (Apache-2.0); Piper pt_PT-dii-high (CC BY-NC-SA 4.0 — non-commercial use only).
- Music and SFX: synthesised in `code/audio.py` (original).
- Names, prices and listings on screen are fictional.

## PT voice v2 (ElevenLabs via Higgsfield, voice "Ines")
The Piper PT voice was too flat, so the PT narration was regenerated with ElevenLabs (Higgsfield `text2speech_v2`,
preset voice "Ines"). The Higgsfield file host is blocked from this cloud session, so the re-voicing was mixed in
the Higgsfield sandbox from `audio/bed/music.wav` + `audio/bed/sfx.wav` (music ducked under the voice, −14.8 LUFS / −1 dBTP)
and muxed onto the PT exports. Line placement (start s · filter):
0.45 "Cada casa começa com uma história." · 3.2 "Compre ou arrende... de norte a sul do país!" (atempo 1.08) ·
7.0 "Explore o mapa, ou o que está mesmo perto de si." (atempo 1.12) · 10.45 "Guarde as que mais gosta." ·
12.5 "E receba alertas, mal surja uma casa nova!" (atempo 1.08) · 15.35 "SUPERCASA." (trim 1.4 s) ·
16.75 "O seu próximo capítulo... começa aqui." (pause shortened 0.3 s, atempo 1.05).
