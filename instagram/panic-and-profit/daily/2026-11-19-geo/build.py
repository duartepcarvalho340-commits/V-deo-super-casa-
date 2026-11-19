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
H2=lambda t,c=None: f'<h2 class="serif" style="font-size:28px;font-weight:700;line-height:1.1;letter-spacing:-0.4px;color:{c or INK};margin-bottom:10px;">{t}</h2>'
SUB=lambda t: f'<p class="sans" style="font-size:13px;color:#6B6B6B;line-height:1.5;margin-bottom:14px;">{t}</p>'
SRC=lambda t: f'<p class="sans" style="font-size:9px;color:#A09B95;margin-top:10px;">{t}</p>'
def chip(t,c): return f'<span class="sans" style="display:inline-block;font-size:11px;font-weight:700;letter-spacing:1.5px;padding:7px 12px;border:1.5px solid {INK};border-radius:4px;background:#fff;color:{c};margin:0 6px 6px 0;">{t}</span>'

# 1 HOOK
b1=f'''<div style="position:absolute;top:30px;left:36px;">{logo(17,line_w=110,tagline=False)}</div>
{tag("GEOPOLITICS · BREAKING", RED)}
<h1 class="serif" style="font-size:33px;font-weight:700;line-height:1.08;letter-spacing:-0.6px;color:{INK};">Trump, Xi and Putin in one room. A first.</h1>
<div style="margin:16px 0 10px;">{chip("WASHINGTON",INK)}{chip("BEIJING",RED)}{chip("MOSCOW",INK)}</div>
<p class="sans" style="font-size:13px;color:#6B6B6B;line-height:1.5;">Skip the theater. Here are the 4 ways this summit can reach your portfolio.</p>'''
slides.append(slide(0,LBG,b1,True,justify="center"))

# 2 SETUP
def row(lbl,val):
    return f'''<div style="padding:10px 0;border-bottom:1px solid {LBR};"><div class="sans" style="font-size:9px;font-weight:700;letter-spacing:1.5px;color:#8A8580;">{lbl}</div>
<div class="sans" style="font-size:13px;color:{INK};font-weight:600;margin-top:3px;line-height:1.4;">{val}</div></div>'''
b2=f'''{tag("THE SETUP", RED)}
{H2("Shenzhen, Nov 19: the first-ever three-way meeting.")}
{row("WHERE","APEC summit sidelines, Shenzhen, China")}
{row("BEFORE IT","Separate Trump–Xi and Trump–Putin meetings. First Trump–Putin sit-down since Alaska, Aug 2025")}
{row("ON THE TABLE (PER US OFFICIALS)","Trade, chips, rare earths, nuclear arms, the Iran war")}
{SRC("Sources: Washington Post, UPI, ABC News, CNBC, AP.")}'''
slides.append(slide(1,LBG,b2,True))

# 3 THE TRADE NUMBERS
def stat(lbl,val,sub,col=INK):
    return f'''<div style="padding:11px 0;border-bottom:1px solid {LBR};display:flex;justify-content:space-between;align-items:center;gap:12px;">
<div><div class="sans" style="font-size:9px;font-weight:700;letter-spacing:1.5px;color:#8A8580;">{lbl}</div><div class="sans" style="font-size:11px;color:#6B6B6B;margin-top:2px;line-height:1.35;">{sub}</div></div>
<div class="serif" style="font-size:22px;font-weight:800;color:{col};white-space:nowrap;">{val}</div></div>'''
b3=f'''{tag("THE US–CHINA TRUCE, IN NUMBERS", P)}
{H2("A fragile truce with a deadline.")}
{stat("NEW TARIFF-CUT LISTS","~$30B","Of goods each way, released by the US and China",P)}
{stat("TRUCE DEADLINE","Jan 10, 2027","China's rare-earth control pause and extra 24% tariff pause",RED)}
{stat("STILL IN PLACE","10%","China's tariff on US goods")}
{SRC("Sources: PBS NewsHour, NBC News, The National, APA Engineering.")}'''
slides.append(slide(2,LBG,b3,True))

# 4 FOUR CHANNELS
def ch(n,t,d,c):
    return f'''<div style="display:flex;gap:12px;align-items:flex-start;padding:9px 0;border-bottom:1px solid {LBR};">
<div class="serif" style="min-width:30px;height:30px;border-radius:50%;background:{c};color:#fff;display:flex;align-items:center;justify-content:center;font-size:14px;font-weight:700;">{n}</div>
<div><div class="sans" style="font-size:13px;font-weight:700;color:{INK};">{t}</div><div class="sans" style="font-size:11.5px;color:#6B6B6B;line-height:1.4;margin-top:2px;">{d}</div></div></div>'''
b4=f'''{tag("HOW IT REACHES YOUR PORTFOLIO", P)}
{H2("4 channels from summit to stocks")}
{ch(1,"Tariffs","Import costs hit retailers' and manufacturers' margins.",INK)}
{ch(2,"Rare earths","Magnets for chips, defense and EVs. Supply = production.",RED)}
{ch(3,"Chip exports","Nvidia's next-quarter guide already assumes zero China data-center sales.",INK)}
{ch(4,"Oil","Russia sanctions and the Iran war feed oil, then inflation, then the Fed.",RED)}
{SRC("Nvidia guidance: Q3 FY2027 results (Nov 17, 2026).")}'''
slides.append(slide(3,LBG,b4,True))

# 5 NUANCE
b5=f'''{tag("FOR ADVANCED INVESTORS", P)}
{H2("Headlines move prices for a day. Follow-through moves them for a year.")}
<p class="sans" style="font-size:13px;color:#555;line-height:1.55;margin-bottom:14px;">The last US–China deal (Busan, Oct 2025) looked big on paper. A year later, US officials say rare-earth shipments still fall short of what was promised, and Beijing disputes it.</p>
<div style="display:flex;gap:10px;">
<div style="flex:1;border:1px solid {LBR};border-radius:10px;padding:12px;background:#fff;"><div class="sans" style="font-size:9px;font-weight:700;letter-spacing:1.5px;color:{RED};">PRICE THE PHOTO</div><div class="serif" style="font-size:15px;font-weight:700;color:{INK};margin-top:4px;">Handshakes, statements</div></div>
<div style="flex:1;border:1px solid {LBR};border-radius:10px;padding:12px;background:#fff;"><div class="sans" style="font-size:9px;font-weight:700;letter-spacing:1.5px;color:{P};">PRICE THE PAPER</div><div class="serif" style="font-size:15px;font-weight:700;color:{INK};margin-top:4px;">Tariff lists, export licenses</div></div></div>
{SRC("Sources: CSIS, InvestingLive, The National.")}'''
slides.append(slide(4,LBG,b5,True))

# 6 WATCHLIST
def step(n,t,d):
    return f'''<div style="display:flex;align-items:flex-start;gap:14px;padding:10px 0;border-bottom:1px solid {LBR};">
<span class="serif" style="font-size:26px;font-weight:300;color:{P};min-width:34px;line-height:1;">{n}</span>
<div><div class="sans" style="font-size:14px;font-weight:600;color:{INK};">{t}</div><div class="sans" style="font-size:12px;color:#8A8580;line-height:1.45;margin-top:2px;">{d}</div></div></div>'''
b6=f'''{tag("YOUR WATCHLIST", P)}
{H2("What to track next")}
{step("01","The joint statement: out","A 4-point declaration on nuclear stability. No major breakthroughs.")}
{step("02","Jan 10, 2027","The truce deadline. Extension or cliff?")}
{step("03","Chip export rules","Any change hits semis first.")}
{step("04","Oil prices","The fastest link from geopolitics to inflation.")}'''
slides.append(slide(5,LBG,b6,True))

# 7 CTA
b7=f'''<div style="text-align:center;display:flex;flex-direction:column;align-items:center;">
<div style="padding:0 0 4px;margin-bottom:26px;">{logo(26,line_w=190)}</div>
<h2 class="serif" style="font-size:28px;font-weight:700;line-height:1.12;letter-spacing:-0.4px;color:{INK};margin-bottom:10px;">Watch the paper,<br>not the photo.</h2>
<p class="sans" style="font-size:13px;color:#6B6B6B;line-height:1.5;margin-bottom:22px;max-width:290px;">Markets, macro and geopolitics without the noise, for people who already invest.</p>
<div class="sans" style="display:inline-flex;align-items:center;gap:8px;padding:12px 26px;background:{P};color:#fff;font-weight:700;font-size:14px;border-radius:28px;">Follow @panic.and.profit</div>
<p class="sans" style="font-size:11px;color:#8A8580;margin-top:12px;">Save this for the next summit.</p>
<p class="sans" style="font-size:8px;letter-spacing:1.5px;color:#A09B95;margin-top:18px;">NOT FINANCIAL ADVICE</p></div>'''
slides.append(slide(6,LBG,b7,True,last=True,justify="center"))
html=f'''<!DOCTYPE html><html lang="en-US"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>Panic &amp; Profit — Trump, Xi, Putin</title>
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
<div class="ig-caption"><b>panic.and.profit</b> Trump, Xi and Putin in one room. What your portfolio should watch. <small>2 HOURS AGO</small></div>
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
