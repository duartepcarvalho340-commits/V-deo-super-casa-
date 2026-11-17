# Panic & Profit — Instagram launch reel (EN)

Launch / intro reel for **@panicandprofit**, a page about markets, macro and geopolitics explained without jargon:
*"Today's news is tomorrow's money."*

**Concept: "Front page → explainer".** Generic headline slips slam onto the screen, stack up and tremble while
a red chart falls. They drop away for *"Every headline moves your money."* One slip comes back, flips over like a page
and opens into the explainer on its back (01 Geopolitics → 02 Macro → 03 Markets). Then the slips return as a calm
bento grid, and every red ▼ flips to a green ▲ (*"Understand the world. Invest better."*). The logo's V chart line
draws itself, the wordmark rises out of a mask, and the reel ends on the end card.

There is no continuous thread between scenes. Each transition is physical paper: slam, fall, flip, re-order.

## Identity (from the logo)
- Background `#FFFFFF`, ink `#151515`, panic red `#C8102E`, profit green `#1B7F4B`, grey `#6B6B6B`. No gradients, no neon.
- Wordmark: "Panic & Profit" in Fraunces 600, with the "&" in Fraunces Italic 400. V chart line beneath it (red drop,
  green recovery, green end dot). Subtitle "MARKETS · MACRO · GEOPOLITICS" in Inter 500, caps, tracked, grey.
- The logo is redrawn in code from that spec (`logo()` in `code/render.py`), because the SVG wasn't available
  in this session. To use the exact SVG, replace the V-line points `VPTS` with the SVG's path coordinates.
- All headlines are generic and fictional. There is no real data, and no real people or companies.

## Files
- `code/timing.py`: scene boundaries, narration-locked events, motion-blur windows and all on-screen text (`TEXT["en"]`)
- `code/voice_en_eleven.py`: **current narration**. It cuts the ElevenLabs takes in `audio/raw/` (Higgsfield `text2speech_v2`,
  variant `elevenlabs`, preset voice **John**, male) at their pauses, speeds up a few lines slightly without changing pitch, and places each phrase on its beat, writing
  `audio/voice_en.wav` and `audio/voice_timing_en.json`.
- `code/voice_en.py`: the first version (Kokoro `af_heart`), replaced because it sounded robotic. Kept for reference.
  `python3 code/voice_en_eleven.py emily` rebuilds the second version (female ElevenLabs voice "Emily").
- `audio/raw/voz_alternativa_sloane.m4a`: an audition of an alternative voice (Sloane) on two lines
- `code/audio.py`: original score at 120 BPM. D minor during the panic (sub-bass pulse, clock tick, stabs, riser),
  then D major for the recovery (piano, claps, pad), then a bell chord on the logo. SFX on every headline, on the
  flips, and on the pen stroke and dot of the logo. In the panic there is also a chaos layer: a wailing siren,
  an approaching two-tone siren, 22 phone notifications (pings, news-alert tri-tones, vibrations), all of which
  cut dead when the headlines fall. Music and chaos are ducked under the voice.
- `code/render.py`: Skia renderer. `--orient V|L`; the vertical layout is built from scratch, not cropped.
- `exports/`: `panicandprofit_EN_1080x1920.mp4` (Reels) and `panicandprofit_EN_1920x1080.mp4`
  (60 fps, H.264 + AAC 192k, −14 LUFS integrated, −3 dBTP peak)
- `contact_sheet_V.png` / `contact_sheet_L.png`: one frame per second

## Re-render
```bash
bash <video-spec skill>/scripts/setup.sh . en       # Skia, Kokoro voice
# fonts (Google Fonts is blocked, so @fontsource from npm, converted to TTF into assets/fonts/):
#   npm pack @fontsource/fraunces@5.1.0 @fontsource/inter@5.1.0  -> Fraunces-{400,400i,600,700,900}.ttf, Inter-{400..800}.ttf
python3 code/voice_en_eleven.py john   # needs audio/raw/john_*.wav (ffmpeg -i x.mp3 -ac 1 -ar 48000 x.wav)
python3 code/audio.py en
ffmpeg -i audio/stems/mix_raw_en.wav -af "volume=2.55dB,aresample=192000,alimiter=limit=0.70:attack=0.5:release=50:level=false,aresample=48000" -c:a pcm_s16le audio/mix_en.wav
python3 code/render.py --orient V --out exports/panicandprofit_EN_1080x1920.mp4
python3 code/render.py --orient L --out exports/panicandprofit_EN_1920x1080.mp4
# stills: python3 code/render.py --orient V --scale 0.5 --out previews/s.png --still 1 4 8
```
If you change the voice or the text, recheck loudness with `ffmpeg -i audio/mix_en.wav -af ebur128=peak=true -f null -`
and adjust the `volume=` gain until you are at −14 LUFS.

## Licences
- Fonts: Fraunces and Inter, both SIL Open Font License 1.1 (via @fontsource; licence files are in `assets/fonts/`).
- Voice: ElevenLabs (preset "John") generated through Higgsfield. Check commercial use against the terms of the
  Higgsfield plan in use (the account is currently on the free plan). The old Kokoro voice is Apache-2.0.
- Music and SFX: synthesised in `code/audio.py` (original, no samples).
