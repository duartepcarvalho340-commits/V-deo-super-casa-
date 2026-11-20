---
name: panic-profit-carousel
description: Make a Panic & Profit Instagram carousel (7 slides, US English, real verified US-market data, light brand design) from build.py/export.js, then schedule it via Metricool after approval. Use for "carrossel Panic & Profit" or the carousel days of the daily task (alternating with Reels).
---

# panic-profit-carousel

Fala com o utilizador em **português de Portugal**; slides e legenda em **inglês americano** (formatos dos EUA: $71,750, +9.5%, Apr 9)
para investidores americanos intermédios e avançados. Instagram **@panic.and.profit**. Modelo aprovado: `build.py`
(gerador; copiar componentes, paleta, Fraunces + Inter, logótipo, barra de progresso, seta em todos menos no último,
moldura IG 420 px, slides 420×525) e `export.js` (`node export.js <html> <outdir> <scale>`).

**Todos os slides em fundo claro `#FAFAF7`**: nada de slides escuros, alternância ou degradê. Vermelho `#C8102E` = quedas,
verde `#1B7F4B` = subidas, cinzento `#8A8A8A` = "&".

## Passos
1. Ver `instagram/panic-and-profit/daily/` para não repetir temas dos últimos 30 dias.
2. Pesquisar (Reuters, AP, Bloomberg, WSJ, CNBC, FT, FactSet, S&P DJI, Fed, BLS, BEA, Treasury, SEC, resultados). Cada número
   confirmado em 2 fontes independentes ou 1 primária; o resto sai.
3. 7 slides: gancho, contexto/problema, dados (gráfico/barras), porquê/mecanismo, nuance para avançados, plano prático,
   CTA ("Follow @panic.and.profit", frase para guardar, "NOT FINANCIAL ADVICE"). Linha de fonte pequena nos slides com dados.
   Direto, sem hype, sem recomendações de compra/venda de títulos concretos. HTML gerado com Python.
4. Guardar em `instagram/panic-and-profit/daily/YYYY-MM-DD/`: script, `carousel.html`, `sources.md`, `caption.txt`
   (gancho, 2–4 linhas, CTA, "Not financial advice.", 8–12 hashtags), `preview.png` (7 slides a escala 1, em mosaico).
   Ver a imagem e corrigir sobreposições.
5. Commit, push, SendUserFile (proactive, render) e perguntar "Quais slides precisam de ajuste antes de exportar e publicar?".
6. **Só depois de aprovado**: exportar a escala 2.5714285714 → JPEG qualidade 92 `slide_1.jpg`…`slide_7.jpg` (1080×1350),
   commit/push, URLs `https://raw.githubusercontent.com/duartepcarvalho340-commits/V-deo-super-casa-/<branch>/<caminho>/slide_N.jpg`
   (curl → 200), Metricool `createScheduledPost` (blogId 8179959, Europe/Lisbon, providers instagram, instagramData
   `{"type":"POST"}`, media = 7 URLs em ordem, text = caption, autoPublish true). Hora: a pedida; "publica já" → +10 min;
   senão 17:00 Lisboa (12:00 ET). Confirmar com hora de Lisboa e Nova Iorque e plannerUrl.

## Pergunta final + primeiro comentário (regra do utilizador)
Todos os posts terminam com uma pergunta curta e neutra ao público ("Your call: ...?"): última cena do Reel / último slide de conteúdo do carrossel, repetida na legenda e **sempre** definida como `firstCommentText` no Metricool (ex.: "Your call: is $111.50 a share too much? What is Anthropic really worth? 👇"). O primeiro comentário só pode ser definido antes de o post sair. Explicações "em português simples" de métricas (ex.: P/E = anos de lucro para recuperar o preço) são bem-vindas.

## Story 5 minutos depois (regra do utilizador)
Cada post novo (Reel ou carrossel) leva um **Story** 1080×1920 publicado **5 minutos depois** do post. Reel: frame mais forte (ex.: a capa) + faixa vermelha "NEW REEL ▶ WATCH IT ON OUR PROFILE" + a pergunta final. Carrossel: slide 1 em cartão + "NEW POST ▶ SWIPE IT ON OUR PROFILE" + a pergunta final. Texto fora dos 250 px de cima e de baixo (zonas da interface). Metricool: `instagramData {"type":"STORY"}`, sem texto. Autocolantes (sondagem, link) não são possíveis por API: lembrar o utilizador de os pôr à mão ou de partilhar o post no story.

## URLs públicas sem cache
O raw.githubusercontent.com guarda cache ~5 min por caminho. Para ficheiros atualizados, usar sempre o URL fixo ao commit: `https://raw.githubusercontent.com/duartepcarvalho340-commits/V-deo-super-casa-/<sha do commit>/<caminho>` e confirmar com curl o tamanho igual ao ficheiro local.

## Investimento a LONGO PRAZO (regra do utilizador)
A Panic & Profit é uma página de investimento a longo prazo. NUNCA usar linguagem de trading/curto prazo: "trade", "the AI trade", "trader(s)", "trading" (no sentido especulativo), "buy the dip", "dip", "swing", "scalp", "entry/exit", "price target" para timing, etc. Preferir: investors, long-term, fundamentals, valuation, "a bump on a long road", "stay invested", "time in the market". Perguntas finais com opções de longo prazo (ex.: BUBBLE / BUMP). Antes de exportar, procurar no guião, ecrã e legenda por trad|dip e reescrever.
