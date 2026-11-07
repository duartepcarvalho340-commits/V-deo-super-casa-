# Duro Ceramics — anúncio spec (PT-PT)

Conceito independente de Duarte Carvalho (@duartecarvalho) · **sem afiliação à Duro Ceramics / Duro Designers**.

**Conceito — "Da roda à mesa":** uma única forma redonda que se vai transformando, com a câmara sempre a pique.
O barro cai na roda e abre-se num prato → é moldado → o vidrado passa como o calor do forno → o prato é pintado à mão
na roda de bandas (friso azul-cobalto e uma roseta de sardinhas) → sobe da roda e pousa numa mesa posta, de onde
salta uma sardinha de cerâmica → chicote para uma parede caiada com azulejos, onde pousam três andorinhas → uma delas
voa contra a câmara e enche o ecrã de cobalto → pilha de pratos (salpicos, calçada portuguesa, andorinhas, sardinhas)
→ prato branco onde o logótipo é pintado a pincel → o prato vira-se e o cartão final é a marca do oleiro no verso.

Essência da marca usada: peças utilitárias decorativas feitas e pintadas à mão nas Caldas da Rainha, com símbolos da
cultura portuguesa (sardinhas, andorinhas, calçada) em cores garridas; nas palavras de António Duro, *"dar novas
leituras ao artesanato português"*. O logótipo e as peças são aproximações desenhadas em código.

## Ficheiros
- `code/timing.py` — tempos, eventos e todos os textos do ecrã (`TEXT["pt"]`) + guião da voz (`VOICE_PT`)
- `code/voice_pt.py` — monta a narração a partir de `audio/voice_raw/l1..l7.mp3` (voz ElevenLabs "Ines", via Higgsfield
  `text2speech_v2`): encurta pausas internas, acelera 7 % e coloca cada frase no seu tempo → `audio/voice_pt.wav`
- `code/audio.py` — banda sonora original (80 BPM, ré menor → ré maior; dedilhado tipo guitarra portuguesa com
  trémulo, viola, pad, adufe e shaker) + efeitos sintetizados + ducking da música sob a voz
- `code/render.py` — renderizador Skia, `--orient L|V`
- `exports/` — vídeos finais (1920×1080 e 1080×1920, 60 fps, H.264 + AAC, −14 LUFS / −1 dBTP)

## Re-renderizar
```bash
bash <skill>/scripts/setup.sh . pt          # Skia, ffmpeg, fontes base
python3 code/voice_pt.py
python3 code/audio.py pt
# loudnorm em duas passagens para -14 LUFS / -1 dBTP -> audio/mix_pt.wav
python3 code/render.py --orient L --out exports/duro_spec_PT_1920x1080.mp4
python3 code/render.py --orient V --out exports/duro_spec_PT_1080x1920.mp4
# stills: python3 code/render.py --orient V --scale 0.5 --out previews/s.png --still 1 4 8
```

## Licenças
- Fontes: Cormorant Garamond, Manrope e Caveat (SIL OFL 1.1, via @fontsource).
- Voz: ElevenLabs (voz predefinida "Ines") gerada através do Higgsfield — sujeita aos termos dessas plataformas.
- Música e efeitos: sintetizados em `code/audio.py` (originais).
- Logótipo, peças e marca "DC" desenhados em código; nada foi descarregado da marca.
