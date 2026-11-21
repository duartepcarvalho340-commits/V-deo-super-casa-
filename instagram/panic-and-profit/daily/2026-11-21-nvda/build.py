from pathlib import Path
OUT = Path(__file__).resolve().parent/"carousel.html"

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
def TEASE(t): return f'<p class="sans" style="font-size:11.5px;font-weight:700;color:{RED};margin-top:10px;">{t} →</p>'
H2=lambda t,c=None: f'<h2 class="serif" style="font-size:28px;font-weight:700;line-height:1.1;letter-spacing:-0.4px;color:{c or INK};margin-bottom:10px;">{t}</h2>'
SUB=lambda t: f'<p class="sans" style="font-size:13px;color:#6B6B6B;line-height:1.5;margin-bottom:14px;">{t}</p>'
SRC=lambda t: f'<p class="sans" style="font-size:9px;color:#A09B95;margin-top:10px;">{t}</p>'
def chip(t,c): return f'<span class="sans" style="display:inline-block;font-size:11px;font-weight:700;letter-spacing:1.5px;padding:7px 12px;border:1.5px solid {INK};border-radius:4px;background:#fff;color:{c};margin:0 6px 6px 0;">{t}</span>'

# 1 HOOK
spark=f"""<svg width="348" height="90" viewBox="0 0 348 110" fill="none" style="display:block;margin:14px 0 4px;">
<line x1="0" y1="108" x2="348" y2="108" stroke="{LBR}" stroke-width="1"/>
<polyline points="2,70 40,52 80,38 120,20 150,8 180,26 210,44 240,60 270,74 300,88 340,96" stroke="{RED}" stroke-width="3" stroke-linecap="round" stroke-linejoin="round"/>
<circle cx="150" cy="8" r="4.5" fill="{INK}"/><circle cx="340" cy="96" r="5" fill="{RED}"/>
<text x="158" y="12" font-family="Inter" font-size="9" font-weight="700" fill="{INK}" letter-spacing="1">OCT 6 RECORD</text>
<text x="262" y="104" font-family="Inter" font-size="9" font-weight="700" fill="{RED}" letter-spacing="1">$125.53</text></svg>"""
b1=f"""<div style="position:absolute;top:30px;left:36px;">{logo(17,line_w=110,tagline=False)}</div>
<div style="height:30px"></div>{tag("IS NVIDIA CHEAP NOW?", RED)}
<h1 class="serif" style="font-size:33px;font-weight:700;line-height:1.05;letter-spacing:-0.6px;color:{INK};">Nvidia is now cheaper than the S&amp;P 500.</h1>
{spark}
<div style="display:flex;gap:8px;margin:6px 0 10px;">{chip("~-48% FROM ATH",RED)}{chip("P/E 11.7x vs. S&amp;P ~17x",INK)}</div>
<p class="sans" style="font-size:13px;color:#6B6B6B;line-height:1.5;">Earnings +111%. Stock -14% in a day on an SEC report. Gift, or trap? Swipe for both sides →</p>"""
slides.append(slide(0,LBG,b1,True,justify="center"))

# 2 THE DRAWDOWN
def stat(lbl,val,sub,col=INK):
    return f"""<div style="padding:10px 0;border-bottom:1px solid {LBR};display:flex;justify-content:space-between;align-items:center;gap:12px;">
<div><div class="sans" style="font-size:9px;font-weight:700;letter-spacing:1.5px;color:#8A8580;">{lbl}</div><div class="sans" style="font-size:11px;color:#6B6B6B;margin-top:2px;line-height:1.35;">{sub}</div></div>
<div class="serif" style="font-size:22px;font-weight:800;color:{col};white-space:nowrap;">{val}</div></div>"""
b2=f"""{tag("THE DRAWDOWN", RED)}
{H2("$2.7 trillion gone. 7 straight losing weeks.")}
{stat("CLOSE, FRI NOV 20","$125.53","-14% on the day. Worst day since Jan 2025",RED)}
{stat("FROM THE OCT 6 RECORD","~-48%","~$2.7T of market cap erased",RED)}
{stat("CATALYST 1","CEO exit","Huang out Nov 12; CFO Colette Kress interim CEO, search ongoing")}
{stat("CATALYST 2","SEC report","Reuters: SEC examining its accounting. No charges; SEC no comment",RED)}
{stat("CATALYST 3","Capex funding","Can hyperscalers keep spending as free cash flow thins?")}
{TEASE("But the numbers tell a different story")}
{SRC("Sources: Yahoo Finance, Global Banking &amp; Finance, Reuters, Bloomberg, CNBC, Nvidia 8-K (SEC), Barclays via BigGo.")}"""
slides.append(slide(1,LBG,b2,True))

# 3 THE PRINT
b3=f"""{tag("THE FUNDAMENTALS: Q3 FY27", P)}
{H2("The print didn't break. The multiple did.")}
{stat("REVENUE","$115.8B","+103% y/y, +20% q/q",P)}
{stat("DATA CENTER","$107.6B","+110% y/y. 93% of revenue",P)}
{stat("NON-GAAP EPS","$2.68","+111% y/y vs. $2.47 consensus",P)}
{stat("GROSS MARGIN","74.9%","Non-GAAP. Q4 guide: 71-72%",INK)}
{stat("Q4 GUIDE","$130B ±3%","Assumes $0 China data-center compute",INK)}
{TEASE("So how cheap is it, really?")}
{SRC("Source: Nvidia Q3 FY2027 release & CFO commentary (Nov 17, 2026); TradingKey, StockTitan.")}"""
slides.append(slide(2,LBG,b3,True))

# 4 THE MULTIPLE
def bar_row(lbl,val,w,col,sub):
    return f"""<div style="margin:6px 0;"><div style="display:flex;justify-content:space-between;align-items:baseline;"><span class="sans" style="font-size:11px;font-weight:700;letter-spacing:1px;color:{INK};">{lbl}</span><span class="serif" style="font-size:20px;font-weight:800;color:{col};">{val}</span></div>
<div style="height:14px;background:{LBR};border-radius:7px;margin-top:5px;overflow:hidden;"><div style="height:100%;width:{w}%;background:{col};border-radius:7px;"></div></div>
<div class="sans" style="font-size:10px;color:#8A8580;margin-top:3px;">{sub}</div></div>"""
b4=f"""{tag("THE MULTIPLE", P)}
{H2("Below-market multiple. +111% EPS.")}
<p class="sans" style="font-size:12px;color:#555;line-height:1.5;margin-bottom:6px;"><b>P/E in plain English:</b> how many years of today's profit it takes to earn back the price you pay.</p>
{bar_row("NVIDIA · RUN-RATE","11.7x",11.7/20*100,P,"$125.53 / ($2.68 × 4 = $10.72 annualized EPS)")}
{bar_row("S&amp;P 500 · FORWARD 12M","~17x",16.7/20*100,INK,"FactSet 18.3x (Nov 13), adjusted for this week's -8.6%")}
<div style="display:flex;gap:10px;margin-top:8px;"><div style="flex:1;border:1px solid {LBR};border-radius:10px;padding:10px;background:#fff;"><div class="sans" style="font-size:9px;font-weight:700;letter-spacing:1.5px;color:{P};">IMPLIED PEG</div><div class="serif" style="font-size:20px;font-weight:800;color:{INK};">~0.11</div><div class="sans" style="font-size:9.5px;color:#8A8580;">11.7x / 111% EPS growth</div></div>
<div style="flex:1;border:1px solid {LBR};border-radius:10px;padding:10px;background:#fff;"><div class="sans" style="font-size:9px;font-weight:700;letter-spacing:1.5px;color:{RED};">EARNINGS YIELD</div><div class="serif" style="font-size:20px;font-weight:800;color:{INK};">~8.5%</div><div class="sans" style="font-size:9.5px;color:#8A8580;">vs. ~5% on 10-year Treasuries</div></div></div>
{TEASE("Too good to be true? The bear case")}
{SRC("Our math from Nvidia's reported EPS. Sources: Benzinga, Crypto Briefing, Motley Fool, FactSet.")}"""
slides.append(slide(3,LBG,b4,True))

# 5 BULL vs BEAR
def case(title,col,items):
    li="".join(f'<li style="margin:0 0 6px 0;">{x}</li>' for x in items)
    return f"""<div style="flex:1;border:1.5px solid {col};border-radius:10px;padding:11px 11px 6px;background:#fff;">
<div class="sans" style="font-size:10px;font-weight:800;letter-spacing:2px;color:{col};margin-bottom:6px;">{title}</div>
<ul class="sans" style="font-size:10.5px;color:{INK};line-height:1.38;padding-left:13px;">{li}</ul></div>"""
b5=f"""{tag("BULL CASE vs. BEAR CASE", INK)}
{H2("Cheap multiple, or peak earnings?")}
<div style="display:flex;gap:8px;">
{case("CHEAP",P,["Hypergrowth at a value multiple: PEG ~0.11","Guide implies +12% q/q on Rubin ramp","Moat: CUDA + full-stack systems","Below-market P/E with ~75% margins"])}
{case("TRAP",RED,["Cyclical math: low P/E at <b>peak</b> E is the classic semis trap","GM guide down ~340 bps to 71-72%","<b>SEC reportedly examining the accounting:</b> if the E is in doubt, the P/E means nothing","Capex funded by thinning FCF + key-person risk"])}
</div>
<p class="sans" style="font-size:12px;color:#555;line-height:1.5;margin-top:10px;">The debate isn't the P. It's the <b>durability of the E</b>: is FY27 a plateau or a peak?</p>
{SRC("Sources: Nvidia guidance, Barclays, Fortune, CNBC, Yahoo Finance.")}"""
slides.append(slide(4,LBG,b5,True))

# 6 WATCHLIST
def step(n,t,d):
    return f"""<div style="display:flex;align-items:flex-start;gap:14px;padding:9px 0;border-bottom:1px solid {LBR};">
<span class="serif" style="font-size:26px;font-weight:300;color:{P};min-width:34px;line-height:1;">{n}</span>
<div><div class="sans" style="font-size:14px;font-weight:600;color:{INK};">{t}</div><div class="sans" style="font-size:12px;color:#8A8580;line-height:1.45;margin-top:2px;">{d}</div></div></div>"""
b6=f"""{tag("📌 SAVE THIS CHECKLIST", P)}
{H2("4 signals that settle the debate")}
{step("01","Hyperscaler 2027 capex guides","The demand side of Nvidia's E. Cuts = estimate cuts.")}
{step("02","The SEC review","Any formal action, or Nvidia's response. A report is not a verdict.")}
{step("03","A permanent CEO","Removes the key-person discount, or deepens it.")}
{step("04","Q4 print vs. $130B + margins","Beat with 71-72% margins keeps the cheap case alive.")}"""
slides.append(slide(5,LBG,b6,True))

# 7 VOTE + CTA
b7=f"""<div style="text-align:center;display:flex;flex-direction:column;align-items:center;">
<div style="padding:0 0 4px;margin-bottom:18px;">{logo(24,line_w=170)}</div>
<div class="sans" style="font-size:10px;font-weight:700;letter-spacing:2px;color:{RED};margin-bottom:8px;">YOUR CALL</div>
<h2 class="serif" style="font-size:30px;font-weight:700;line-height:1.1;letter-spacing:-0.4px;color:{INK};margin-bottom:14px;">Is Nvidia cheap,<br>or a value trap?</h2>
<div style="display:flex;gap:10px;margin-bottom:10px;"><span class="serif" style="padding:10px 22px;border-radius:26px;background:{P};color:#fff;font-weight:800;font-size:17px;letter-spacing:1px;">CHEAP</span><span class="serif" style="padding:10px 22px;border-radius:26px;background:{RED};color:#fff;font-weight:800;font-size:17px;letter-spacing:1px;">TRAP</span></div>
<p class="sans" style="font-size:12px;color:#6B6B6B;margin-bottom:18px;">Comment CHEAP or TRAP 👇</p>
<div class="sans" style="display:inline-flex;align-items:center;gap:8px;padding:11px 24px;background:{INK};color:#fff;font-weight:700;font-size:13px;border-radius:28px;">Follow @panic.and.profit</div>
<p class="sans" style="font-size:11px;color:#8A8580;margin-top:10px;">Save this for Nvidia's Q4 print.</p>
<p class="sans" style="font-size:8px;letter-spacing:1.5px;color:#A09B95;margin-top:14px;">NOT FINANCIAL ADVICE</p></div>"""
slides.append(slide(6,LBG,b7,True,last=True,justify="center"))
html=f'''<!DOCTYPE html><html lang="en-US"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>Panic &amp; Profit — Is Nvidia cheap now?</title>
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
<div class="ig-header"><div class="ig-avatar">P<i>&amp;</i>P</div><div><div style="font-size:13px;font-weight:600;">panic.and.profit</div><div style="font-size:11px;color:#888;">Markets · Macro · Geopolitics</div></div></div>
<div class="carousel-viewport"><div class="carousel-track">{"".join(slides)}</div></div>
<div class="ig-dots">{"".join('<span class="on"></span>' if k==0 else '<span></span>' for k in range(TOTAL))}</div>
<div class="ig-actions"><div>
<svg width="24" height="24" fill="none" stroke="#111" stroke-width="2" viewBox="0 0 24 24"><path d="M12 21s-7-4.5-9.5-9A5.5 5.5 0 0 1 12 6a5.5 5.5 0 0 1 9.5 6c-2.5 4.5-9.5 9-9.5 9z"/></svg>
<svg width="24" height="24" fill="none" stroke="#111" stroke-width="2" viewBox="0 0 24 24"><path d="M21 12a8.5 8.5 0 0 1-12.6 7.4L3 21l1.6-5.4A8.5 8.5 0 1 1 21 12z"/></svg>
<svg width="24" height="24" fill="none" stroke="#111" stroke-width="2" viewBox="0 0 24 24"><path d="M22 3L9.2 13.5M22 3l-7 18-3.5-7.5L3 10z"/></svg></div>
<svg width="24" height="24" fill="none" stroke="#111" stroke-width="2" viewBox="0 0 24 24"><path d="M19 21l-7-5-7 5V4a1 1 0 0 1 1-1h12a1 1 0 0 1 1 1z"/></svg></div>
<div class="ig-caption"><b>panic.and.profit</b> Is Nvidia cheap now? The bull and bear case. <small>2 HOURS AGO</small></div>
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
