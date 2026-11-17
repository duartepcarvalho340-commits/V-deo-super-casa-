---
name: panic-profit-reel
description: Make a Panic & Profit Instagram Reel (vertical 1080x1920, US English, real verified market data) animated in code with Skia, Kokoro voice and an original score, then schedule it via Metricool after approval. Adapted from video-spec. Use for "reel", "vídeo Panic & Profit", or the Wednesday/Saturday slot of the daily task.
---

# panic-profit-reel: Reels educativos animados em código (Panic & Profit)

Adaptação da skill `video-spec` para a marca própria **Panic & Profit** (Instagram **@panic.and.profit**).
Fala com o utilizador em **português de Portugal**; tudo o que está no vídeo (voz, textos, legenda) é em **inglês americano**,
para investidores americanos intermédios e avançados. Foco: **bolsa americana** (S&P 500, Nasdaq, Dow, setores,
mega caps, Fed, resultados, macro dos EUA, geopolítica que mexe nas ações).

## Diferenças em relação ao video-spec
| video-spec | panic-profit-reel |
|---|---|
| Anúncio spec de marca alheia, aviso de não afiliação | Marca própria: sem aviso de não afiliação, sem logótipos de terceiros |
| Cartão final "DC · Duarte Carvalho" | Cartão final (2 s): logótipo Panic & Profit + "Follow @panic.and.profit" + "NOT FINANCIAL ADVICE" |
| Dados fictícios | **Dados reais**, cada número confirmado em 2 fontes independentes ou 1 fonte primária; fonte em letra pequena no ecrã |
| PT por omissão, Piper | **Só inglês (en-US)**, Kokoro `af_heart` (Apache-2.0, uso comercial OK) |
| Horizontal + vertical, ~21 s | **Só vertical 1080×1920**, 20–30 s, 60 fps, H.264 + AAC, −14 LUFS / −1 dBTP |
| Estilo livre por marca | Identidade fixa da marca (abaixo); a ideia visual muda em cada Reel |

## Identidade fixa
- Fundo claro `#FAFAF7` (papel branco, como o vídeo original da marca); tinta `#141414`; vermelho `#C8102E` = quedas/pânico;
  verde `#1B7F4B` = subidas/lucro; cinzento `#8A8A8A` = "&" itálico do logótipo; bordas `#E6E4DE`.
- Letras: **Fraunces** (títulos, 700–800; "&" em itálico 500) e **Inter** (texto). O setup instala ambas em `assets/fonts/`.
- Logótipo desenhado em código: "Panic & Profit" em Fraunces + linha que desce a vermelho e sobe a verde até um ponto verde,
  tagline "MARKETS · MACRO · GEOPOLITICS" (ver `logo()` em `../panic-profit-carousel/build.py`).
- Linguagem gráfica herdada do vídeo da marca: cartões de "breaking news" com contorno preto e seta vermelha/verde,
  tickers, gráficos de linha, barras, números grandes. Sem fundos escuros.

## Criatividade
Antes de escrever código: 3 conceitos (uma frase cada), escolher o mais forte e dizer porquê. Variar entre Reels
(registar em `instagram/panic-and-profit/daily/*/concept.txt` e não repetir os últimos 10): ticker que vira gráfico,
cartões de notícias que se empilham e viram, número gigante que se decompõe, mapa/geopolítica com setas de fluxo,
linha do tempo que faz zoom, ecrã dividido "panic vs profit", papel que se dobra, candlesticks que se constroem, etc.
**Não usar** o "fio contínuo de cena em cena" (gasto). Música original coerente (ex.: pulsação tensa → resolução).

## Passos
1. **Pesquisa** (WebSearch, várias fontes credíveis e atuais: Reuters, AP, Bloomberg, WSJ, CNBC, FT, FactSet, S&P DJI,
   Fed, BLS, BEA, SEC, comunicados de resultados). Um ângulo que ensine algo. Guardar `sources.md`.
2. **Briefing curto** no chat (PT-PT): 3 conceitos e o escolhido, guião (5–8 frases curtas), 6–9 momentos com tempos.
3. **Projeto** em `instagram/panic-and-profit/daily/YYYY-MM-DD/reel/`:
   `bash .claude/skills/panic-profit-reel/scripts/setup.sh <dir>` (Skia, Kokoro, Fraunces, Inter). Os ficheiros pesados
   (`assets/`, `audio/stems/`, `previews/` de trabalho) não vão para o git: adicionar um `.gitignore` local.
4. **Voz** `code/voice_en.py` (modelo em `examples/duolingo/voice_en.py`, `lang="en-us"`, `af_heart`, speed ~1.0):
   frases curtas com tempo de início, sem sobreposições; `audio/voice_timing.json`.
5. **Animação** `code/render.py` (infraestrutura dos `examples/`: helpers, câmara, `Renderer`, motion blur, pipe para ffmpeg
   com `-pix_fmt bgra`), só layout vertical 1080×1920. Margens seguras do Reels: nada importante nos 220 px de cima nem
   nos 380 px de baixo (interface do Instagram). Stills: `--scale 0.5 --still …` + folha de contacto (`ffmpeg tile`) e
   corrigir sobreposições.
6. **Áudio** `code/audio.py`: banda sonora sintetizada + efeitos nos eventos + ducking sob a voz; depois
   `ffmpeg -i audio/stems/mix_raw.wav -af loudnorm=I=-14:TP=-1:LRA=11 -ar 48000 audio/mix.wav`. Validar com espectrograma.
7. **Pré-visualização para aprovação**: `preview.mp4` (540×960, 30 fps) + `preview.png` (folha de contacto de 8 frames) +
   `caption.txt` (inglês: gancho, 2–4 linhas de valor, CTA seguir/guardar, "Not financial advice.", 8–12 hashtags).
   Enviar com SendUserFile e perguntar "Quais ajustes antes de exportar e publicar?". Não publicar sem aprovação.
8. **Depois de aprovado**: render final `reel.mp4` 1080×1920 60 fps (em segundo plano; máx. 2 renders em simultâneo),
   confirmar com ffprobe (resolução, fps, duração 20–30 s, áudio AAC) e tamanho < 100 MB; `cover.jpg` (frame forte do
   gancho, 1080×1920). Commit e push; URL pública
   `https://raw.githubusercontent.com/duartepcarvalho340-commits/V-deo-super-casa-/<branch>/<caminho>/reel.mp4` (curl → 200).
9. **Metricool** `createScheduledPost` (blogId 8179959, timezone Europe/Lisbon): providers `[{"network":"instagram"}]`,
   `instagramData {"type":"REEL","showReelOnFeed":true}`, media = [URL do mp4], `videoThumbnailUrl` = URL do cover.jpg,
   text = caption.txt, autoPublish true, draft false. Hora: a pedida; "publica já" → +10 min; senão 17:00 Lisboa (12:00 ET).
   Confirmar com hora de Lisboa e Nova Iorque e o plannerUrl; transmitir erros tal como vierem.

## Licenças
Fraunces e Inter (SIL OFL 1.1); Kokoro v1.0 (Apache-2.0); música e efeitos sintetizados no código (originais).
