"""Builds report/panic_and_profit_report.pdf from posts.json + plan.json + daily/<folder>/ files.
Usage: python3 build_report.py  (then: node render_pdf.js)"""
import base64, html, json, re
from pathlib import Path
HERE = Path(__file__).resolve().parent; DAILY = HERE.parent / "daily"
posts = json.loads((HERE / "posts.json").read_text()); plan = json.loads((HERE / "plan.json").read_text())
def b64(p): return "data:image/png;base64," + base64.b64encode(p.read_bytes()).decode()
def md_links(p):
    if not p.exists(): return ""
    urls = re.findall(r"https?://[^\s|)]+", p.read_text())
    seen = []; [seen.append(u) for u in urls if u not in seen]
    return "".join(f'<li>{html.escape(u)}</li>' for u in seen)
cards = []
for i, p in enumerate(posts, 1):
    d = DAILY / p["folder"]; cap = (d / "caption.txt").read_text().strip() if (d / "caption.txt").exists() else ""
    cap = re.sub(r"[\U0001F300-\U0001FAFF\u2600-\u27BF]", "", cap).replace("  \n", "\n")
    pillar = (d / "pillar.txt").read_text().strip() if (d / "pillar.txt").exists() else ""
    img = f'<img src="{b64(d / "preview.png")}">' if (d / "preview.png").exists() else ""
    st = {"Published": "Publicado", "Scheduled": "Agendado"}.get(p["status"], p["status"]); stc = {"Publicado": "pub", "Agendado": "sch"}.get(st, "pl")
    link = f'<a href="{p["url"]}">{p["url"]}</a>' if p["url"] else "—"
    cards.append(f'''<section class="post"><div class="hd"><span class="n">#{i}</span><h2>{html.escape(p["title"])}</h2><span class="st {stc}">{st}</span></div>
<table class="meta"><tr><td>Data</td><td>{p["date"]} · {p["time"]}</td></tr><tr><td>Formato</td><td>{p["format"]}</td></tr>
<tr><td>Área</td><td>{html.escape(pillar)}</td></tr><tr><td>Instagram</td><td>{link}</td></tr></table>
{img}<h3>Legenda (publicada em inglês)</h3><pre>{html.escape(cap)}</pre><h3>Fontes</h3><ul class="src">{md_links(d / "sources.md")}</ul></section>''')
rows = "".join(f"<tr><td>{a}</td><td>{b}</td><td>{html.escape(c)}</td><td>{d}</td></tr>" for a, b, c, d in plan)
npub = sum(p["status"] == "Published" for p in posts); nsch = sum(p["status"] == "Scheduled" for p in posts)
doc = f'''<!doctype html><html><head><meta charset="utf-8"><title>Panic & Profit — Relatório de conteúdos</title>
<link href="https://fonts.googleapis.com/css2?family=Fraunces:ital,opsz,wght@0,9..144,700;0,9..144,800;1,9..144,500&family=Inter:wght@400;500;600;700&display=swap" rel="stylesheet">
<style>
@page{{size:A4;margin:16mm 14mm}} *{{box-sizing:border-box}} body{{font-family:Inter,sans-serif;color:#141414;font-size:10.5pt;margin:0}}
.cover{{height:250mm;display:flex;flex-direction:column;justify-content:center;page-break-after:always}}
.logo{{font-family:Fraunces,serif;font-weight:800;font-size:42pt}} .logo i{{font-weight:500;color:#8A8A8A}}
.tag{{letter-spacing:3px;font-size:8pt;color:#8A8A8A;margin-top:4px}} h1{{font-family:Fraunces,serif;font-size:26pt;margin:28px 0 6px}}
.sub{{color:#6B6B6B}} .kpi{{display:flex;gap:12px;margin-top:22px}} .kpi div{{border:1.5px solid #141414;padding:12px 16px;min-width:120px}}
.kpi b{{font-family:Fraunces,serif;font-size:22pt;display:block}}
h2{{font-family:Fraunces,serif;font-size:17pt;margin:0;flex:1}} h3{{font-size:9pt;letter-spacing:2px;text-transform:uppercase;color:#1B7F4B;margin:14px 0 6px}}
.post{{page-break-before:always}} .hd{{display:flex;align-items:center;gap:10px;border-bottom:2px solid #141414;padding-bottom:8px;margin-bottom:10px}}
.n{{font-family:Fraunces,serif;font-size:17pt;color:#8A8A8A}} .st{{font-size:8pt;font-weight:700;letter-spacing:1.5px;text-transform:uppercase;padding:4px 10px;border-radius:12px;color:#fff}}
.pub{{background:#1B7F4B}} .sch{{background:#C8102E}} .pl{{background:#8A8A8A}}
.meta td{{padding:2px 12px 2px 0;vertical-align:top}} .meta td:first-child{{color:#8A8A8A;width:80px}}
img{{width:100%;border:1px solid #E6E4DE;margin-top:10px}} pre{{white-space:pre-wrap;font-family:Inter,sans-serif;font-size:9.5pt;background:#FAFAF7;border:1px solid #E6E4DE;padding:10px;margin:0}}
.src{{font-size:7.5pt;color:#555;padding-left:16px;margin:0;word-break:break-all}} a{{color:#1B7F4B}}
table.plan{{width:100%;border-collapse:collapse;margin-top:10px}} .plan th,.plan td{{border-bottom:1px solid #E6E4DE;padding:7px 6px;text-align:left}} .plan th{{font-size:8pt;letter-spacing:1.5px;text-transform:uppercase;color:#8A8A8A}}
.note{{font-size:8.5pt;color:#6B6B6B;margin-top:12px}}
</style></head><body>
<div class="cover"><div class="logo">Panic <i>&amp;</i> Profit</div><div class="tag">MARKETS · MACRO · GEOPOLITICS · @panic.and.profit</div>
<h1>Relatório de conteúdos</h1><div class="sub">Publicações de quarta, 18 de novembro, a quarta, 25 de novembro de 2026</div>
<div class="kpi"><div><b>{npub}</b>publicados</div><div><b>{len(posts) - npub}</b>por publicar</div><div><b>{len(plan)}</b>dias</div></div>
<div class="note">Público: investidores dos EUA · conteúdos em inglês americano · publicação via Metricool · não é aconselhamento financeiro.</div></div>
{"".join(cards)}
<section class="post"><div class="hd"><h2>O que saiu em cada dia</h2></div>
<table class="plan"><tr><th>Dia</th><th>Formato</th><th>Tema</th><th>Estado</th></tr>{rows}</table>
<div class="note">Cada publicação leva um Story 5 minutos depois e a pergunta final como primeiro comentário. Desde segunda, 23 de novembro, o Metricool recusa publicações (limite da conta): os posts seguintes estão prontos para publicação manual ou depois de resolvido o limite.</div></section>
</body></html>'''
(HERE / "report.html").write_text(doc, encoding="utf-8"); print("html ok")
