from pathlib import Path
OUT = Path("/home/user/V-deo-super-casa-/instagram/panic-and-profit/carrossel_01_panico.html")

P="#1B7F4B"; PL="#4FB07A"; PD="#0F4D2D"; RED="#C8102E"; GREY="#8A8A8A"
LBG="#FAFAF7"; LBR="#E6E4DE"; DBG="#121413"; INK="#141414"
GRAD=f"linear-gradient(165deg,{PD} 0%,{P} 55%,{PL} 100%)"
TOTAL=7

def bar(i, light):
    pct=(i+1)/TOTAL*100
    tr,fi,lb=("rgba(0,0,0,0.08)",P,"rgba(0,0,0,0.3)") if light else ("rgba(255,255,255,0.12)","#fff","rgba(255,255,255,0.4)")
    return f'<div style="position:absolute;bottom:0;left:0;right:0;padding:16px 28px 20px;z-index:10;display:flex;align-items:center;gap:10px;"><div style="flex:1;height:3px;background:{tr};border-radius:2px;overflow:hidden;"><div style="height:100%;width:{pct:.2f}%;background:{fi};border-radius:2px;"></div></div><span class="sans" style="font-size:11px;color:{lb};font-weight:500;">{i+1}/{TOTAL}</span></div>'

def arrow(light):
    bg,st=("rgba(0,0,0,0.06)","rgba(0,0,0,0.25)") if light else ("rgba(255,255,255,0.08)","rgba(255,255,255,0.35)")
    return f'<div style="position:absolute;right:0;top:0;bottom:0;width:48px;z-index:9;display:flex;align-items:center;justify-content:center;background:linear-gradient(to right,transparent,{bg});"><svg width="24" height="24" viewBox="0 0 24 24" fill="none"><path d="M9 6l6 6-6 6" stroke="{st}" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round"/></svg></div>'

def logo(size=22, ink=INK, amp=GREY, line_w=150, tagline=True, tag_col=GREY):
    w=line_w; h=round(w*0.12)
    svg=(f'<svg width="{w}" height="{h+6}" viewBox="0 0 300 42" fill="none" style="display:block;margin-top:4px;">'
         f'<polyline points="4,10 62,15 104,35" stroke="{RED}" stroke-width="4" stroke-linecap="round" stroke-linejoin="round"/>'
         f'<polyline points="104,35 168,19 216,12 292,4" stroke="{P if ink==INK else "#fff"}" stroke-width="4" stroke-linecap="round" stroke-linejoin="round"/>'
         f'<circle cx="292" cy="4" r="4" fill="{P if ink==INK else "#fff"}"/></svg>')
    t=f'<div class="sans" style="font-size:7px;letter-spacing:2px;color:{tag_col};margin-top:6px;">MARKETS · MACRO · GEOPOLITICS</div>' if tagline else ''
    return f'<div style="display:inline-block;"><div class="serif" style="font-size:{size}px;font-weight:800;color:{ink};letter-spacing:-0.3px;line-height:1;">Panic <span style="font-style:italic;font-weight:500;color:{amp};">&amp;</span> Profit</div>{svg}{t}</div>'

def tag(t,c): return f'<span class="sans" style="display:inline-block;font-size:10px;font-weight:600;letter-spacing:2px;color:{c};margin-bottom:14px;">{t}</span>'

def slide(i, bg, body, light, last=False, justify="flex-end", extra=""):
    return f'''<div class="slide" style="background:{bg};">{extra}
<div style="position:absolute;inset:0;padding:0 36px 52px;display:flex;flex-direction:column;justify-content:{justify};z-index:2;">{body}</div>
{'' if last else arrow(light)}{bar(i, light)}</div>'''

slides=[]

# 1 HERO
chart=f'''<svg width="348" height="120" viewBox="0 0 348 120" fill="none" style="display:block;margin:18px 0 6px;">
<line x1="0" y1="118" x2="348" y2="118" stroke="{LBR}" stroke-width="1"/>
<polyline points="2,22 60,30 100,26 140,62 170,98" stroke="{RED}" stroke-width="3" stroke-linecap="round" stroke-linejoin="round"/>
<polyline points="170,98 200,70 240,58 290,40 340,14" stroke="{P}" stroke-width="3" stroke-linecap="round" stroke-linejoin="round"/>
<circle cx="170" cy="98" r="5" fill="{RED}"/><circle cx="340" cy="14" r="5" fill="{P}"/>
<text x="178" y="112" font-family="Inter" font-size="9" font-weight="600" fill="{RED}" letter-spacing="1">VENDESTE AQUI</text>
<text x="252" y="30" font-family="Inter" font-size="9" font-weight="600" fill="{P}" letter-spacing="1">E ISTO?</text>
</svg>'''
b1=f'''<div style="position:absolute;top:30px;left:36px;">{logo(17,line_w=110,tagline=False)}</div>
{tag("MERCADOS · PSICOLOGIA", RED)}
<h1 class="serif" style="font-size:34px;font-weight:700;line-height:1.08;letter-spacing:-0.6px;color:{INK};">Vender no pânico custa mais do que a própria queda.</h1>
{chart}
<p class="sans" style="font-size:13px;color:#6B6B6B;line-height:1.5;">O que os números de 20 anos de S&amp;P 500 dizem sobre sair do mercado na hora errada.</p>'''
slides.append(slide(0,LBG,b1,True,justify="center"))

# 2 PROBLEM - abril 2025
def card(date,title,val,up):
    c=P if up else RED
    tri="M6 2 L11 10 L1 10 Z" if up else "M1 2 L11 2 L6 10 Z"
    return f'''<div style="display:flex;align-items:center;justify-content:space-between;background:#fff;border-radius:6px;padding:10px 12px;margin-bottom:8px;">
<div><div class="sans" style="font-size:8px;font-weight:700;letter-spacing:1.5px;color:{c};">{date}</div>
<div class="serif" style="font-size:16px;font-weight:800;color:{INK};text-transform:uppercase;letter-spacing:0.2px;">{title}</div></div>
<div style="display:flex;align-items:center;gap:8px;"><span class="sans" style="font-size:15px;font-weight:700;color:{c};">{val}</span>
<div style="width:26px;height:26px;background:{c};border-radius:4px;display:flex;align-items:center;justify-content:center;"><svg width="12" height="12" viewBox="0 0 12 12"><path d="{tri}" fill="#fff"/></svg></div></div></div>'''
b2=f'''{tag("O PROBLEMA · ABRIL DE 2025", "#E8566C")}
<h2 class="serif" style="font-size:29px;font-weight:700;line-height:1.1;letter-spacing:-0.4px;color:#fff;margin-bottom:16px;">Em dois dias, o S&amp;P 500 caiu ~10,5%. Muitos venderam.</h2>
{card("3 ABR · TARIFAS","Mercados afundam","−4,8%",False)}
{card("4 ABR · PÂNICO","Investidores fogem","−6,0%",False)}
{card("9 ABR · PAUSA NAS TARIFAS","Mercado dispara","+9,5%",True)}
<p class="sans" style="font-size:13px;color:rgba(255,255,255,0.6);line-height:1.5;margin-top:8px;">Quem vendeu a 4 de abril ficou de fora, três sessões depois, do melhor dia do índice desde 2008.</p>'''
slides.append(slide(1,DBG,b2,False))

# 3 DATA - J.P. Morgan
def hbar(label,val,ret,pct,c,txtc):
    return f'''<div style="margin-bottom:14px;"><div style="display:flex;justify-content:space-between;align-items:baseline;margin-bottom:6px;">
<span class="sans" style="font-size:12px;font-weight:600;color:{INK};">{label}</span><span class="sans" style="font-size:11px;color:#8A8580;">{ret}</span></div>
<div style="height:34px;width:{pct}%;background:{c};border-radius:4px;display:flex;align-items:center;padding-left:12px;">
<span class="serif" style="font-size:18px;font-weight:700;color:{txtc};">{val}</span></div></div>'''
b3=f'''{tag("OS NÚMEROS", P)}
<h2 class="serif" style="font-size:29px;font-weight:700;line-height:1.1;letter-spacing:-0.4px;color:{INK};margin-bottom:8px;">Falhar 10 dias em 20 anos corta o resultado para menos de metade.</h2>
<p class="sans" style="font-size:13px;color:#6B6B6B;line-height:1.5;margin-bottom:18px;">10 000 US$ no S&amp;P 500, de 2005 a 2024.</p>
{hbar("Sempre investido","71 750 US$","≈10,4% ao ano",100,P,"#fff")}
{hbar("Fora dos 10 melhores dias","32 871 US$","≈6,1% ao ano",46,RED,"#fff")}
<p class="sans" style="font-size:12px;color:{INK};line-height:1.5;padding-top:4px;border-top:1px solid {LBR};">Fora dos 40 melhores dias, o retorno anual fica <b>negativo</b>.</p>
<p class="sans" style="font-size:9px;color:#A09B95;margin-top:8px;">Fonte: J.P. Morgan Asset Management, Guide to Retirement 2025 (via CNBC e Franklin Templeton).</p>'''
slides.append(slide(2,LBG,b3,True))

# 4 WHY - clustering
def pair(year,d1,v1,d2,v2):
    return f'''<div style="display:flex;gap:8px;margin-bottom:10px;">
<div style="flex:0 0 46px;" class="serif"><span style="font-size:22px;font-weight:300;color:{PL};">{year}</span></div>
<div style="flex:1;background:rgba(200,16,46,0.14);border:1px solid rgba(200,16,46,0.35);border-radius:8px;padding:8px 10px;"><div class="sans" style="font-size:9px;letter-spacing:1px;color:rgba(255,255,255,0.5);">{d1}</div><div class="serif" style="font-size:19px;font-weight:700;color:#FF6B7F;">{v1}</div></div>
<div style="flex:1;background:rgba(27,127,75,0.18);border:1px solid rgba(79,176,122,0.4);border-radius:8px;padding:8px 10px;"><div class="sans" style="font-size:9px;letter-spacing:1px;color:rgba(255,255,255,0.5);">{d2}</div><div class="serif" style="font-size:19px;font-weight:700;color:{PL};">{v2}</div></div></div>'''
b4=f'''{tag("PORQUÊ", PL)}
<h2 class="serif" style="font-size:29px;font-weight:700;line-height:1.1;letter-spacing:-0.4px;color:#fff;margin-bottom:10px;">Os melhores dias escondem-se no meio dos piores.</h2>
<p class="sans" style="font-size:13px;color:rgba(255,255,255,0.6);line-height:1.5;margin-bottom:16px;"><b style="color:#fff;">7 dos 10 melhores dias</b> dos últimos 20 anos aconteceram a menos de duas semanas dos 10 piores.</p>
{pair("2008","15 OUT","−9,0%","13 OUT","+11,6%")}
{pair("2020","16 MAR","−12,0%","24 MAR","+9,4%")}
{pair("2025","4 ABR","−6,0%","9 ABR","+9,5%")}
<p class="sans" style="font-size:12px;color:rgba(255,255,255,0.45);line-height:1.5;margin-top:4px;">Para apanhar o ressalto, tens de estar dentro quando tudo parece pior.</p>'''
slides.append(slide(3,DBG,b4,False))

# 5 NUANCE (advanced)
b5=f'''{tag("PARA QUEM JÁ SABE", P)}
<h2 class="serif" style="font-size:28px;font-weight:700;line-height:1.1;letter-spacing:-0.4px;color:{INK};margin-bottom:12px;">"Mas quem sai também evita os piores dias." Verdade.</h2>
<p class="sans" style="font-size:13px;color:#555;line-height:1.55;margin-bottom:14px;">Ninguém falha <i>só</i> os melhores dias: o estudo é um cenário extremo. O problema real do <i>market timing</i> é outro: tens de acertar <b>duas vezes</b>.</p>
<div style="display:flex;gap:10px;margin-bottom:14px;">
<div style="flex:1;border:1px solid {LBR};border-radius:10px;padding:12px;background:#fff;"><div class="sans" style="font-size:9px;font-weight:700;letter-spacing:1.5px;color:{RED};">DECISÃO 1</div><div class="serif" style="font-size:16px;font-weight:700;color:{INK};margin-top:4px;">Quando sair</div></div>
<div style="flex:1;border:1px solid {LBR};border-radius:10px;padding:12px;background:#fff;"><div class="sans" style="font-size:9px;font-weight:700;letter-spacing:1.5px;color:{P};">DECISÃO 2</div><div class="serif" style="font-size:16px;font-weight:700;color:{INK};margin-top:4px;">Quando voltar</div></div></div>
<p class="sans" style="font-size:13px;color:#555;line-height:1.55;">Em abril de 2025, o sinal para voltar chegou numa publicação nas redes sociais, a meio de uma sessão. Quase ninguém que vendeu estava pronto.</p>'''
slides.append(slide(4,LBG,b5,True))

# 6 HOW-TO (dark)
def step(n,t,d):
    return f'''<div style="display:flex;align-items:flex-start;gap:14px;padding:11px 0;border-bottom:1px solid rgba(255,255,255,0.08);">
<span class="serif" style="font-size:26px;font-weight:300;color:{PL};min-width:34px;line-height:1;">{n}</span>
<div><div class="sans" style="font-size:14px;font-weight:600;color:#fff;">{t}</div><div class="sans" style="font-size:12px;color:rgba(255,255,255,0.5);line-height:1.45;margin-top:2px;">{d}</div></div></div>'''
b6=f'''{tag("O PLANO ANTI-PÂNICO", PL)}
<h2 class="serif" style="font-size:29px;font-weight:700;line-height:1.1;letter-spacing:-0.4px;color:#fff;margin-bottom:8px;">Decide antes da queda, não durante.</h2>
{step("01","Liquidez fora da bolsa","3 a 6 meses de despesas. Ninguém te obriga a vender no fundo.")}
{step("02","Alocação definida","Ex.: 80% ações / 20% obrigações, escrita antes de precisares dela.")}
{step("03","Rebalancear por regra","Só quando o peso se desvia mais de 5 p.p. Nunca por manchete.")}
{step("04","Investir todos os meses","Nas quedas, o mesmo valor compra mais unidades.")}'''
slides.append(slide(5,DBG,b6,False))

# 7 CTA
b7=f'''<div style="text-align:center;display:flex;flex-direction:column;align-items:center;">
<div style="background:#fff;border-radius:14px;padding:18px 22px 14px;margin-bottom:26px;">{logo(26,line_w=190)}</div>
<h2 class="serif" style="font-size:28px;font-weight:700;line-height:1.12;letter-spacing:-0.4px;color:#fff;margin-bottom:10px;">O pânico é deles.<br>O plano é teu.</h2>
<p class="sans" style="font-size:13px;color:rgba(255,255,255,0.75);line-height:1.5;margin-bottom:22px;max-width:290px;">Mercados, macro e geopolítica explicados sem ruído. Para quem já investe e quer fazê-lo melhor.</p>
<div class="sans" style="display:inline-flex;align-items:center;gap:8px;padding:12px 26px;background:{LBG};color:{PD};font-weight:700;font-size:14px;border-radius:28px;">Segue @panicandprofit</div>
<p class="sans" style="font-size:11px;color:rgba(255,255,255,0.6);margin-top:12px;">Guarda este post para a próxima queda.</p>
<p class="sans" style="font-size:8px;letter-spacing:1.5px;color:rgba(255,255,255,0.4);margin-top:18px;">NÃO É ACONSELHAMENTO FINANCEIRO</p></div>'''
slides.append(slide(6,GRAD,b7,False,last=True,justify="center"))

html=f'''<!DOCTYPE html><html lang="pt-PT"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>Panic &amp; Profit — Carrossel</title>
<link rel="preconnect" href="https://fonts.googleapis.com"><link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link href="https://fonts.googleapis.com/css2?family=Fraunces:ital,opsz,wght@0,9..144,300;0,9..144,500;0,9..144,700;0,9..144,800;1,9..144,500&family=Inter:wght@400;500;600;700&display=swap" rel="stylesheet">
<style>
*{{margin:0;padding:0;box-sizing:border-box}}
body{{background:#ECEBE6;font-family:'Inter',sans-serif;display:flex;justify-content:center;padding:32px 16px;min-height:100vh}}
.serif{{font-family:'Fraunces',serif}} .sans{{font-family:'Inter',sans-serif}}
.ig-frame{{width:420px;max-width:100%;background:#fff;border-radius:10px;box-shadow:0 6px 30px rgba(0,0,0,.12);overflow:hidden}}
.ig-header{{display:flex;align-items:center;gap:10px;padding:12px 14px}}
.ig-avatar{{width:34px;height:34px;border-radius:50%;background:#fff;border:1px solid #ddd;display:flex;align-items:center;justify-content:center;font-family:'Fraunces',serif;font-weight:800;font-size:12px;color:{INK}}}
.ig-avatar i{{color:{GREY};font-weight:500}}
.carousel-viewport{{width:420px;height:525px;overflow:hidden;position:relative;cursor:grab;touch-action:pan-y}}
.carousel-track{{display:flex;height:100%;transition:transform .35s ease}}
.slide{{width:420px;height:525px;flex:0 0 420px;position:relative;overflow:hidden}}
.ig-dots{{display:flex;justify-content:center;gap:4px;padding:10px 0 4px}}
.ig-dots span{{width:6px;height:6px;border-radius:50%;background:#ccc}} .ig-dots span.on{{background:#0095f6}}
.ig-actions{{display:flex;justify-content:space-between;padding:6px 14px}}
.ig-actions div{{display:flex;gap:14px}}
.ig-caption{{padding:4px 14px 16px;font-size:13px;line-height:1.45;color:#111}}
.ig-caption small{{display:block;color:#999;font-size:10px;margin-top:6px;letter-spacing:.5px}}
</style></head><body>
<div class="ig-frame">
<div class="ig-header"><div class="ig-avatar">P<i>&amp;</i>P</div><div><div style="font-size:13px;font-weight:600;">panicandprofit</div><div style="font-size:11px;color:#888;">Markets · Macro · Geopolitics</div></div></div>
<div class="carousel-viewport"><div class="carousel-track">{"".join(slides)}</div></div>
<div class="ig-dots">{"".join('<span class="on"></span>' if k==0 else '<span></span>' for k in range(TOTAL))}</div>
<div class="ig-actions"><div>
<svg width="24" height="24" fill="none" stroke="#111" stroke-width="2" viewBox="0 0 24 24"><path d="M12 21s-7-4.5-9.5-9A5.5 5.5 0 0 1 12 6a5.5 5.5 0 0 1 9.5 6c-2.5 4.5-9.5 9-9.5 9z"/></svg>
<svg width="24" height="24" fill="none" stroke="#111" stroke-width="2" viewBox="0 0 24 24"><path d="M21 12a8.5 8.5 0 0 1-12.6 7.4L3 21l1.6-5.4A8.5 8.5 0 1 1 21 12z"/></svg>
<svg width="24" height="24" fill="none" stroke="#111" stroke-width="2" viewBox="0 0 24 24"><path d="M22 3L9.2 13.5M22 3l-7 18-3.5-7.5L3 10z"/></svg></div>
<svg width="24" height="24" fill="none" stroke="#111" stroke-width="2" viewBox="0 0 24 24"><path d="M19 21l-7-5-7 5V4a1 1 0 0 1 1-1h12a1 1 0 0 1 1 1z"/></svg></div>
<div class="ig-caption"><b>panicandprofit</b> Vender no pânico parece proteção. Os números dizem outra coisa. Guarda para a próxima queda. 📉📈<small>HÁ 2 HORAS</small></div>
</div>
<script>
const track=document.querySelector('.carousel-track'),vp=document.querySelector('.carousel-viewport'),dots=[...document.querySelectorAll('.ig-dots span')];
let idx=0,sx=0,dx=0,drag=false;const N={TOTAL};
function go(i){{idx=Math.max(0,Math.min(N-1,i));track.style.transition='transform .35s ease';track.style.transform='translateX('+(-idx*420)+'px)';dots.forEach((d,k)=>d.classList.toggle('on',k===idx));}}
vp.addEventListener('pointerdown',e=>{{drag=true;sx=e.clientX;dx=0;track.style.transition='none';vp.setPointerCapture(e.pointerId);}});
vp.addEventListener('pointermove',e=>{{if(!drag)return;dx=e.clientX-sx;track.style.transform='translateX('+(-idx*420+dx)+'px)';}});
vp.addEventListener('pointerup',()=>{{if(!drag)return;drag=false;if(dx<-50)go(idx+1);else if(dx>50)go(idx-1);else go(idx);}});
document.addEventListener('keydown',e=>{{if(e.key==='ArrowRight')go(idx+1);if(e.key==='ArrowLeft')go(idx-1);}});
</script></body></html>'''
OUT.write_text(html,encoding="utf-8"); print("ok",OUT)
