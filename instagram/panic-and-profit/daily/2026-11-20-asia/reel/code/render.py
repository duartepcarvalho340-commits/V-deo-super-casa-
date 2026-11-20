"""Panic & Profit Reel renderer (Asia AI-chip selloff, 2026-11-20). Skia 2D -> raw BGRA frames -> ffmpeg.
Concept: "while America slept" - a night map of Asia turns red market by market, a TSMC donut explains why Taiwan,
then the answer to the morning RED/GREEN vote and a BUBBLE / BUMP vote."""
import argparse, math, os, subprocess, sys
import numpy as np, skia
sys.path.insert(0, os.path.dirname(__file__))
from timing import FPS, DURATION, HANDLE, P, PE, END, _T, NUM

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
FD = f"{ROOT}/assets/fonts"
FR = {w: skia.Typeface.MakeFromFile(f"{FD}/Fraunces-{w}.ttf") for w in (300, 500, 700, 800)}
FRI = {w: skia.Typeface.MakeFromFile(f"{FD}/Fraunces-{w}-Italic.ttf") for w in (500, 700, 800)}
IN = {400: skia.Typeface.MakeFromFile(f"{FD}/Inter-Regular.otf"), 500: skia.Typeface.MakeFromFile(f"{FD}/Inter-Medium.otf"),
      600: skia.Typeface.MakeFromFile(f"{FD}/Inter-SemiBold.otf"), 700: skia.Typeface.MakeFromFile(f"{FD}/Inter-Bold.otf")}
W, H = 1080, 1920

def hexc(h, a=1.0):
    h = h.lstrip("#"); return skia.Color(int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16), int(max(0, min(1, a)) * 255))
BG, INK, RED, GREEN, GREY, BORDER, MUTE, SOFT = "#FAFAF7", "#141414", "#C8102E", "#1B7F4B", "#8A8A8A", "#E6E4DE", "#6B6B6B", "#A09B95"

clamp = lambda x, a=0.0, b=1.0: max(a, min(b, x))
lerp = lambda a, b, t: a + (b - a) * t
def sstep(a, b, x): t = clamp((x - a) / (b - a)); return t * t * (3 - 2 * t)
def ease_out(t): t = clamp(t); return 1 - (1 - t) ** 3
def ease_io(t): t = clamp(t); return 4 * t ** 3 if t < .5 else 1 - (-2 * t + 2) ** 3 / 2
def back_out(t, c=1.6): t = clamp(t); return 1 + (c + 1) * (t - 1) ** 3 + c * (t - 1) ** 2
def monotone(keys):
    xs = np.array([k[0] for k in keys], float); ys = np.array([k[1] for k in keys], float); n = len(xs)
    d = np.diff(ys) / np.diff(xs); m = np.zeros(n)
    for i in range(1, n - 1): m[i] = 0 if d[i - 1] * d[i] <= 0 else (d[i - 1] + d[i]) / 2
    for i in range(n - 1):
        if d[i] == 0: m[i] = m[i + 1] = 0; continue
        a, b = m[i] / d[i], m[i + 1] / d[i]; h = a * a + b * b
        if h > 9: s = 3 / math.sqrt(h); m[i], m[i + 1] = s * a * d[i], s * b * d[i]
    def f(x):
        if x <= xs[0]: return ys[0]
        if x >= xs[-1]: return ys[-1]
        i = int(np.searchsorted(xs, x) - 1); h = xs[i + 1] - xs[i]; t = (x - xs[i]) / h
        return ((2 * t**3 - 3 * t**2 + 1) * ys[i] + (t**3 - 2 * t**2 + t) * h * m[i] + (-2 * t**3 + 3 * t**2) * ys[i + 1] + (t**3 - t**2) * h * m[i + 1])
    return f

def paint(color, stroke=None, blur=0, cap_round=True):
    p = skia.Paint(AntiAlias=True, Color=color)
    if stroke is not None:
        p.setStyle(skia.Paint.kStroke_Style); p.setStrokeWidth(stroke)
        if cap_round: p.setStrokeCap(skia.Paint.kRound_Cap); p.setStrokeJoin(skia.Paint.kRound_Join)
    if blur > 0: p.setMaskFilter(skia.MaskFilter.MakeBlur(skia.kNormal_BlurStyle, blur))
    return p
def tw(s, size, tf): return skia.Font(tf, size).measureText(s)
def text(c, s, x, y, size, color, tf, align="l", track=0.0):
    """y = baseline. track = letter spacing in px."""
    f = skia.Font(tf, size)
    if track == 0:
        w = f.measureText(s); dx = {"c": -w / 2, "l": 0, "r": -w}[align]
        c.drawString(s, x + dx, y, f, paint(color)); return w
    w = sum(f.measureText(ch) for ch in s) + track * (len(s) - 1); dx = {"c": -w / 2, "l": 0, "r": -w}[align]; xx = x + dx
    for ch in s: c.drawString(ch, xx, y, f, paint(color)); xx += f.measureText(ch) + track
    return w
def rect(x, y, w, h): return skia.Rect.MakeXYWH(x, y, w, h)
def rrect(x, y, w, h, r): return skia.RRect.MakeRectXY(rect(x, y, w, h), r, r)
def alpha_layer(c, a): c.saveLayerAlpha(None, int(clamp(a) * 255))
def tri(c, cx, cy, s, up, color):
    p = skia.Path()
    if up: p.moveTo(cx, cy - s * .55); p.lineTo(cx + s * .6, cy + s * .45); p.lineTo(cx - s * .6, cy + s * .45)
    else: p.moveTo(cx - s * .6, cy - s * .45); p.lineTo(cx + s * .6, cy - s * .45); p.lineTo(cx, cy + s * .55)
    p.close(); c.drawPath(p, paint(color))

def logo(c, x, y, size, a=1.0, center=True, line=True, tagline=False):
    """Panic & Profit wordmark; (x,y) = baseline start (or centre if center)."""
    w1, w2, w3 = tw("Panic ", size, FR[800]), tw("&", size, FRI[500]), tw(" Profit", size, FR[800]); w = w1 + w2 + w3
    x0 = x - w / 2 if center else x
    text(c, "Panic ", x0, y, size, hexc(INK, a), FR[800]); text(c, "&", x0 + w1, y, size, hexc(GREY, a), FRI[500])
    text(c, " Profit", x0 + w1 + w2, y, size, hexc(INK, a), FR[800])
    if line:
        sx = w / 300; oy = y + size * 0.28; sw = max(2.5, size * 0.06)
        def P(px, py): return (x0 + px * sx, oy + py * sx)
        red = skia.Path(); red.moveTo(*P(4, 10)); red.lineTo(*P(62, 15)); red.lineTo(*P(104, 35))
        grn = skia.Path(); grn.moveTo(*P(104, 35)); grn.lineTo(*P(168, 19)); grn.lineTo(*P(216, 12)); grn.lineTo(*P(292, 4))
        c.drawPath(red, paint(hexc(RED, a), stroke=sw)); c.drawPath(grn, paint(hexc(GREEN, a), stroke=sw))
        c.drawCircle(*P(292, 4), sw * 1.1, paint(hexc(GREEN, a)))
        if tagline: text(c, "MARKETS · MACRO · GEOPOLITICS", x0 + w / 2, oy + 42 * sx + size * 0.35, size * 0.2, hexc(GREY, a), IN[500], "c", track=size * 0.05)
    return w

def background(c):
    c.clear(hexc(BG))
    for yy in range(160, H, 120): c.drawLine(0, yy, W, yy, paint(hexc("#EFEDE7"), stroke=1.2, cap_round=False))


# ---- word-by-word captions (timings spread by word length inside each phrase) ----
WORDS = []
for ph in _T:
    ws = ph["text"].split(); L = sum(len(w) + 1 for w in ws); t = ph["t0"]; dur = ph["t1"] - ph["t0"] - 0.15
    for w in ws:
        d = dur * (len(w) + 1) / L; WORDS.append((t, t + d, w, ph["t0"])); t += d
def captions(c, t):
    cur = [w for w in WORDS if w[3] <= t and t <= _phrase_end(w[3])]
    if not cur: return
    # show a window of up to 5 words around the current one
    idx = max([i for i, w in enumerate(cur) if w[0] <= t] or [0]); start = (idx // 4) * 4; win = cur[start:start + 4]
    line = " ".join(w[2] for w in win); fs = 64 if tw(line, 64, IN[700]) < 940 else 52
    x = W / 2 - tw(line, fs, IN[700]) / 2; y = 1478
    c.drawRRect(rrect(x - 26, y - fs - 6, tw(line, fs, IN[700]) + 52, fs + 40, 18), paint(hexc(INK, .88)))
    for i, w in enumerate(win):
        on = w[0] <= t; ww = tw(w[2] + " ", fs, IN[700])
        col = "#FFD84D" if (on and (i + start == idx)) else ("#FFFFFF" if on else "#9A9A9A")
        k = ease_out((t - w[0]) / 0.12) if i + start == idx else 1
        c.save(); c.translate(x + tw(w[2], fs, IN[700]) / 2, y); c.scale(lerp(1.12, 1, k), lerp(1.12, 1, k)); c.translate(-(x + tw(w[2], fs, IN[700]) / 2), -y)
        text(c, w[2], x, y, fs, hexc(col), IN[700]); c.restore(); x += ww
def _phrase_end(t0):
    for ph in _T:
        if ph["t0"] == t0: return ph["t1"] + 0.25
    return t0

def ease_in(t): t = clamp(t); return t ** 3
def overlay(t, t0, t1): return ease_out((t - t0) / 0.4) * (1 - sstep(t1, t1 + 0.4, t))
def wtime(word, ph):
    for w in WORDS:
        if w[3] == P[ph] and w[2].strip(",.?:").lower() == word.lower(): return w[0]
    return P[ph]
def fmt(x): return f"{'+' if x > 0 else '-'}{abs(x):.1f}%"
def sigcol(x): return GREEN if x > 0 else RED

def crawl(c, t):
    a = overlay(t, P[1] - 0.2, P[6] - 0.3)
    if a <= 0: return
    alpha_layer(c, a)
    s = "OVERNIGHT IN ASIA  ·  TAIWAN: WORST WEEK SINCE 1991  ·  KOSPI -5.2%  ·  NIKKEI -5.1%  ·  TSMC -4.8%  ·  SAMSUNG -6.9%  ·  "
    c.drawRect(rect(0, 342, W, 46), paint(hexc(RED)))
    f = skia.Font(IN[700], 26); w = sum(f.measureText(ch) for ch in s) + 2 * len(s); off = -(t * 140) % w
    c.save(); c.clipRect(rect(0, 342, W, 46)); x = off - w
    while x < W: x += text(c, s, x, 374, 26, hexc("#FFFFFF"), IN[700], track=2) + 2
    c.restore(); c.restore()

def scene_hook(c, t):
    a = 1 - sstep(P[1] - 0.3, P[1] + 0.1, t)
    if a <= 0: return
    alpha_layer(c, a)
    text(c, "TAIWAN'S STOCK MARKET", W / 2, 520, 32, hexc(MUTE), IN[700], "c", track=6)
    e = ease_out((t - 0.4) / 0.4); alpha_layer(c, e)
    text(c, "Worst week since", W / 2, 640, 78, hexc(INK), FR[800], "c"); c.restore()
    k = ease_io((t - 0.6) / 2.4); yr = int(round(2026 - 35 * k))
    s = 1 + 0.08 * math.exp(-max(0, t - 3.0) * 6) * (t > 3.0)
    c.save(); c.translate(W / 2, 880); c.scale(s, s)
    text(c, str(yr), 0, 0, 260, hexc(RED if k >= 1 else INK), FR[800], "c"); c.restore()
    # week bars falling
    b = ease_out((t - 2.9) / 0.5)
    if b > 0:
        sc = clamp(back_out((t - 2.9) / 0.45), 0, 1.15)
        c.save(); c.translate(W / 2, 1060); c.rotate(-3); c.scale(sc, sc)
        lab = "TAIEX  -17.5%  THIS WEEK"; w = tw(lab, 44, IN[700]) + 3 * len(lab) + 80
        c.drawRRect(rrect(-w / 2, -50, w, 100, 50), paint(hexc(RED)))
        text(c, lab, 0, 16, 44, hexc("#FFFFFF"), IN[700], "c", track=3); c.restore()
    c.restore()

# --- night map of Asia (schematic) ---
NODES = {"JAPAN": (815, 735, "NIKKEI 225", -5.1), "S. KOREA": (628, 705, "KOSPI", -5.2), "TAIWAN": (470, 1050, "TAIEX", -6.2)}
LAND = [[(80,560),(400,540),(560,600),(590,660),(560,720),(545,800),(530,880),(500,960),(430,1040),(350,1110),(250,1170),(80,1200)],
        [(590,660),(640,650),(665,720),(660,800),(615,815),(600,740)],
        [(770,560),(820,590),(860,660),(850,740),(800,800),(740,860),(700,880),(720,820),(780,760),(800,680),(780,620)],
        [(452,1000),(486,1005),(492,1080),(466,1098),(448,1050)]]
_DOTS = []
for poly in LAND:
    pth = skia.Path(); pth.moveTo(*poly[0])
    for q in poly[1:]: pth.lineTo(*q)
    pth.close()
    for yy in range(520, 1220, 16):
        for xx in range(60, 900, 16):
            if pth.contains(xx, yy): _DOTS.append((xx, yy))
def draw_land(c):
    pt = paint(hexc("#D9D3C6"))
    for x, y in _DOTS: c.drawCircle(x, y, 4.2, pt)
def blob(c, pts, col):
    p = skia.Path(); p.moveTo(*pts[0])
    for i in range(1, len(pts)):
        x0, y0 = pts[i - 1]; x1, y1 = pts[i]; p.quadTo(x0, y0, (x0 + x1) / 2, (y0 + y1) / 2)
    p.close(); c.drawPath(p, paint(hexc(col)))
def scene_map(c, t):
    a = overlay(t, P[1] - 0.2, PE[3] + 0.3)
    if a <= 0: return
    alpha_layer(c, a)
    text(c, "WHILE AMERICA SLEPT", W / 2, 470, 34, hexc(INK), IN[700], "c", track=8)
    # moon
    c.drawCircle(150, 455, 26, paint(hexc("#F2C94C"))); c.drawCircle(163, 446, 23, paint(hexc(BG)))
    draw_land(c)
    # wave from Wall Street (right edge)
    k = ease_io((t - P[1]) / 1.6)
    if k > 0:
        c.save(); c.clipRect(rect(W - k * (W - 300), 520, W, 760))
        for i in range(3):
            pth = skia.Path(); y0 = 900 + i * 40
            pth.moveTo(W + 40, y0)
            for xx in range(W + 40, 250, -20): pth.lineTo(xx, y0 + 18 * math.sin(xx / 45 + t * 6 + i))
            c.drawPath(pth, paint(hexc(RED, .35 - i * .08), stroke=5))
        c.restore()
        text(c, "WALL ST ▶", W - 60, 1270, 26, hexc(RED), IN[700], "r", track=3) if False else text(c, "FROM WALL ST", W - 70, 1270, 26, hexc(RED), IN[700], "r", track=3)
    order = [("TAIWAN", P[2] - 0.1), ("S. KOREA", P[3] - 0.1), ("JAPAN", wtime("Japan", 3) - 0.1)]
    for name, t0 in order:
        x, y, idx, v = NODES[name]
        e = ease_out((t - t0) / 0.35); on = t >= t0
        r = 18 + 6 * math.sin((t - t0) * 6) * on
        if on:
            c.drawCircle(x, y, 18 + 60 * ((t - t0) % 1.2) / 1.2, paint(hexc(RED, .45 * (1 - ((t - t0) % 1.2) / 1.2)), stroke=4))
        c.drawCircle(x, y, r, paint(hexc(RED if on else GREY)))
        if e > 0:
            alpha_layer(c, e); cw = 300; ch = 140
            cx = x - cw - 40 if name != "TAIWAN" else x + 50; cy = y - ch / 2 if name != "JAPAN" else y - ch - 30
            if name == "S. KOREA": cx, cy = x - cw - 40, y - 20
            if name == "JAPAN": cx, cy = x - cw / 2 - 20, y - ch - 60
            c.drawRRect(rrect(cx, cy, cw, ch, 16), paint(hexc("#FFFFFF"))); c.drawRRect(rrect(cx, cy, cw, ch, 16), paint(hexc(RED), stroke=4))
            text(c, f"{name} · {idx}", cx + 24, cy + 44, 22, hexc(MUTE), IN[700], track=2)
            tri(c, cx + 46, cy + 98, 30, False, hexc(RED)); text(c, fmt(v), cx + 80, cy + 114, 64, hexc(RED), FR[800])
            c.restore()
    e = ease_out((t - (P[2] + 2.0)) / 0.4)
    if e > 0 and t < P[3] + 0.6:
        alpha_layer(c, e)
        lab = "-17.5% THIS WEEK"; w = tw(lab, 34, IN[700]) + 3 * len(lab) + 50
        c.drawRRect(rrect(520, 1150, w, 72, 36), paint(hexc(INK))); text(c, lab, 520 + w / 2, 1198, 34, hexc("#FFFFFF"), IN[700], "c", track=3); c.restore()
    e = ease_out((t - wtime("Samsung", 3)) / 0.35)
    if e > 0:
        alpha_layer(c, e)
        for i, (lab, v) in enumerate((("SAMSUNG", "-6.9%"), ("SK HYNIX", "-6.1%"))):
            x = 560 + i * 250; y = 1235
            c.drawRRect(rrect(x, y, 230, 110, 18), paint(hexc("#FFF1F3"))); c.drawRRect(rrect(x, y, 230, 110, 18), paint(hexc(RED), stroke=3))
            text(c, lab, x + 115, y + 40, 22, hexc(MUTE), IN[700], "c", track=2); text(c, v, x + 115, y + 92, 48, hexc(RED), FR[800], "c")
        c.restore()
    c.restore()

def scene_why(c, t):
    a = overlay(t, P[4] - 0.2, PE[5] + 0.3)
    if a <= 0: return
    alpha_layer(c, a)
    text(c, "WHY TAIWAN?", W / 2, 490, 34, hexc(RED), IN[700], "c", track=8)
    text(c, "The world's AI chip factory", W / 2, 570, 54, hexc(INK), FR[800], "c")
    cx, cy, r = W / 2, 850, 210
    c.drawCircle(cx, cy, r, paint(hexc(BORDER), stroke=70, cap_round=False))
    k = ease_io((t - wtime("TSMC", 4)) / 1.2)
    if k > 0:
        c.drawArc(rect(cx - r, cy - r, 2 * r, 2 * r), -90, 360 * 0.40 * k, False, paint(hexc(RED), stroke=70, cap_round=False))
    text(c, f"~{int(40 * k)}%", cx, cy + 20, 120, hexc(RED if k > 0 else GREY), FR[800], "c")
    text(c, "of Taiwan's index", cx, cy + 82, 26, hexc(INK), IN[600], "c"); text(c, "is TSMC", cx, cy + 116, 26, hexc(INK), IN[600], "c")
    for i, nm in enumerate(("NVIDIA", "AMD", "APPLE")):
        t0 = wtime(nm.capitalize() if nm != "AMD" else "AMD", 4); e = back_out((t - t0) / 0.4)
        if t < t0: continue
        x = W / 2 + (i - 1) * 300; y = 1200; s = clamp(e, 0, 1.15)
        c.drawLine(cx, cy + r + 35, x, y - 45, paint(hexc(INK, .5), stroke=3))
        c.save(); c.translate(x, y); c.scale(s, s)
        c.drawRRect(rrect(-125, -45, 250, 90, 45), paint(hexc("#FFFFFF"))); c.drawRRect(rrect(-125, -45, 250, 90, 45), paint(hexc(INK), stroke=4))
        text(c, nm, 0, 14, 38, hexc(INK), IN[700], "c", track=2); c.restore()
    f = ease_out((t - P[5]) / 0.35)
    if f > 0:
        alpha_layer(c, f)
        c.drawRect(rect(0, 420, W, 960), paint(hexc(BG)))
        text(c, "Doubt AI?", W / 2, 800, 120, hexc(INK), FR[800], "c")
        text(c, "Taiwan feels it first.", W / 2, 940, 84, hexc(RED), FRI[800], "c")
        pth = skia.Path(); pth.moveTo(120, 1110)
        for xx in range(120, 961, 6):
            amp = 8 + 90 * math.exp(-((xx - 540) / 110) ** 2)
            pth.lineTo(xx, 1110 + amp * math.sin(xx / 9 + t * 8) * clamp((t - P[5]) / 0.8))
        c.drawPath(pth, paint(hexc(RED), stroke=5))
        c.restore()
    c.restore()

def scene_answer(c, t):
    a = overlay(t, P[6] - 0.2, PE[6] + 0.3)
    if a <= 0: return
    alpha_layer(c, a)
    text(c, "THIS MORNING WE ASKED", W / 2, 490, 32, hexc(MUTE), IN[700], "c", track=6)
    text(c, "Red or green?", W / 2, 600, 92, hexc(INK), FR[800], "c")
    up = NUM["sp_day"] > 0; word = "GREEN" if up else "RED"; col = GREEN if up else RED
    t0 = wtime(word.lower(), 6) if wtime(word.lower(), 6) != P[6] else wtime("answer", 6) + 0.4
    # the answer word is the 2nd occurrence; pick the time after 'answer:'
    t0 = max(t0, wtime("answer", 6) + 0.35)
    k = back_out((t - t0) / 0.45)
    if t > t0:
        s = clamp(lerp(2.2, 1, ease_out((t - t0) / 0.3)), 0.8, 2.2)
        c.save(); c.translate(W / 2, 800); c.rotate(-6); c.scale(s, s)
        w = tw(word, 150, FR[800]) + 90
        c.drawRRect(rrect(-w / 2, -110, w, 190, 24), paint(hexc(col), stroke=10))
        text(c, word, 0, 50, 150, hexc(col), FR[800], "c"); c.restore()
    rows = [("S&P 500 · LOSING STREAK", "7 DAYS", wtime("seventh", 6) - 0.1, "Longest since 2020"),
            ("S&P 500 · FROM RECORD", "<-10%", wtime("correction", 6) - 0.1, "Officially a correction")]
    for i, (lab, v, tt, sub) in enumerate(rows):
        e = back_out((t - tt) / 0.4)
        if t < tt: continue
        y = 1020 + i * 150; s = clamp(e, 0, 1.12)
        c.save(); c.translate(W / 2, y); c.scale(s, s)
        c.drawRRect(rrect(-400, -62, 800, 124, 62), paint(hexc("#FFFFFF"))); c.drawRRect(rrect(-400, -62, 800, 124, 62), paint(hexc(RED), stroke=5))
        text(c, lab, -350, 0, 30, hexc(INK), IN[700], track=2); text(c, sub, -350, 38, 24, hexc(MUTE), IN[500])
        text(c, v, 350, 22, 62, hexc(RED), FR[800], "r")
        c.restore()
    if NUM.get("draft"):
        text(c, "DRAFT · US NUMBERS FILLED AFTER THE CLOSE", W / 2, 1345, 24, hexc(GREY), IN[700], "c", track=3)
    c.restore()

def scene_long(c, t):
    a = overlay(t, P[7] - 0.2, PE[7] + 0.3)
    if a <= 0: return
    alpha_layer(c, a)
    text(c, "THE LONG-TERM VIEW", W / 2, 490, 34, hexc(GREEN), IN[700], "c", track=8)
    text(c, "One bad week", W / 2, 630, 96, hexc(INK), FR[800], "c")
    text(c, "is not the story.", W / 2, 740, 90, hexc(INK), FRI[800], "c")
    # schematic long road with a bump
    k = ease_io((t - (P[7] + 0.6)) / 2.6); x0, x1 = 120, 960
    pth = skia.Path(); n = int(140 * k)
    for i in range(n + 1):
        u = i / 140; x = lerp(x0, x1, u)
        y = 1180 - 230 * u - 16 * math.sin(u * 19) - (-70 * math.exp(-((u - 0.84) / 0.03) ** 2))
        pth.moveTo(x, y) if i == 0 else pth.lineTo(x, y)
    if n > 1: c.drawPath(pth, paint(hexc(GREEN), stroke=8))
    if k > 0.86:
        e = ease_out((k - 0.86) / 0.14); alpha_layer(c, e)
        c.drawCircle(lerp(x0, x1, .84), 1180 - 230 * .84 - 16 * math.sin(.84 * 19) + 70, 30, paint(hexc(RED), stroke=5))
        text(c, "a bad week", lerp(x0, x1, .84), 1080 + 120, 28, hexc(RED), IN[700], "c"); c.restore()
    text(c, "Illustration, not real data", x1, 1260, 22, hexc(SOFT), IN[500], "r")
    e = ease_out((t - wtime("question", 7)) / 0.4)
    if e > 0:
        alpha_layer(c, e)
        c.drawRRect(rrect(110, 1290 - 10, 860, 80, 40), paint(hexc(INK)))
        text(c, "Can AI profits grow into the prices?", W / 2, 1333, 36, hexc("#FFFFFF"), IN[700], "c"); c.restore()
    c.restore()

def vote(c, t):
    t0 = P[8] - 0.1
    if t < t0: return
    a = ease_out((t - t0) / 0.45)
    c.drawRect(rect(0, 400, W, 1100), paint(hexc(BG, .97 * a)))
    alpha_layer(c, a)
    text(c, "YOUR CALL", W / 2, 640, 32, hexc(RED), IN[700], "c", track=8)
    text(c, "AI bubble,", W / 2, 790, 110, hexc(INK), FR[800], "c")
    text(c, "or a bump on a long road?", W / 2, 900, 62, hexc(INK), FRI[800], "c")
    for i, (lab, col, x) in enumerate((("BUBBLE", RED, 290), ("BUMP", GREEN, 790))):
        k = back_out((t - (t0 + 1.0 + i * 0.25)) / 0.4)
        if k <= 0: continue
        pulse = 1 + 0.04 * math.sin((t - t0) * 7 + i * 1.6)
        c.save(); c.translate(x, 1080); c.scale(clamp(k, 0, 1.2) * pulse, clamp(k, 0, 1.2) * pulse)
        c.drawRRect(rrect(-220, -70, 440, 140, 70), paint(hexc(col))); text(c, lab, 0, 22, 62, hexc("#FFFFFF"), FR[800], "c", track=3)
        c.restore()
    b = ease_out((t - (t0 + 1.8)) / 0.4); alpha_layer(c, b)
    text(c, "Comment BUBBLE or BUMP", W / 2, 1240, 46, hexc(INK), IN[700], "c"); c.restore()
    c.restore()

def cam(t):
    z = 1.0
    for t0 in P[:8]: z += 0.03 * ease_out((t - t0) / 0.6) * (1 - ease_out((t - (t0 + 1.2)) / 2.0))
    sh = 0.0
    for st in (3.0, P[2] - 0.1, P[3] - 0.1, P[5]):
        if st < t < st + 0.35: sh += 12 * math.exp(-(t - st) * 12) * math.sin((t - st) * 90)
    return z, sh

def scene_end(c, t):
    a = ease_out((t - (END + 0.15)) / 0.6)
    alpha_layer(c, a); logo(c, W / 2, 900, 118, line=True, tagline=True); c.restore()
    b = ease_out((t - (END + 0.6)) / 0.5); alpha_layer(c, b)
    pw = tw("Follow " + HANDLE, 44, IN[700]) + 90
    c.drawRRect(rrect(W / 2 - pw / 2, 1110 + (1 - b) * 20, pw, 96, 48), paint(hexc(GREEN)))
    text(c, "Follow " + HANDLE, W / 2, 1172 + (1 - b) * 20, 44, hexc("#FFFFFF"), IN[700], "c")
    text(c, "Save this for the next red week.", W / 2, 1280, 34, hexc(MUTE), IN[500], "c")
    text(c, "NOT FINANCIAL ADVICE", W / 2, 1390, 24, hexc(SOFT), IN[600], "c", track=4); c.restore()

SRC_TXT = "Sources: Bloomberg, CNBC, Digitimes, 24/7 Wall St., TradingKey, AP"

class Renderer:
    def __init__(self, scale):
        self.scale = scale; self.surf = skia.Surface(int(W * scale), int(H * scale))
    def draw(self, t):
        c = self.surf.getCanvas(); c.save(); c.scale(self.scale, self.scale); background(c)
        fade = 1 - sstep(END - 0.1, END + 0.25, t)
        if fade > 0:
            alpha_layer(c, fade)
            z, sh = cam(t)
            c.save(); c.translate(W / 2 + sh, 900); c.scale(z, z); c.translate(-W / 2, -900)
            scene_hook(c, t); scene_map(c, t); scene_why(c, t); scene_answer(c, t); scene_long(c, t)
            c.restore()
            vote(c, t); crawl(c, t)
            logo(c, 100, 285, 40, center=False)
            tg = "AI CHIPS · ASIA"; w = tw(tg, 24, IN[700]) + 3 * len(tg) + 40
            c.drawRRect(rrect(W - 100 - w, 250, w, 50, 25), paint(hexc(RED)))
            text(c, tg, W - 100 - w / 2, 284, 24, hexc("#FFFFFF"), IN[700], "c", track=3)
            captions(c, t)
            sa = sstep(4.0, 4.5, t); alpha_layer(c, sa); text(c, SRC_TXT, W / 2, 1565, 22, hexc(SOFT), IN[500], "c"); c.restore()
            c.restore()
        if t > END: scene_end(c, t)
        c.restore(); return self.surf.makeImageSnapshot().toarray()
    def frame(self, t, fps): return self.draw(t)

if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--scale", type=float, default=1.0); ap.add_argument("--fps", type=int, default=FPS)
    ap.add_argument("--out", required=True); ap.add_argument("--audio", default=f"{ROOT}/audio/mix.wav"); ap.add_argument("--still", type=float, nargs="*")
    a = ap.parse_args(); R = Renderer(a.scale)
    if a.still:
        import cv2
        for t in a.still: cv2.imwrite(a.out.replace(".png", f"_{t:05.2f}.png"), R.draw(t)[:, :, :3])
        sys.exit()
    w, h = R.surf.width(), R.surf.height()
    cmd = ["ffmpeg", "-y", "-loglevel", "error", "-f", "rawvideo", "-pix_fmt", "bgra", "-s", f"{w}x{h}", "-r", str(a.fps), "-i", "-"]
    if os.path.exists(a.audio): cmd += ["-i", a.audio, "-c:a", "aac", "-b:a", "192k", "-shortest"]
    cmd += ["-c:v", "libx264", "-preset", "medium", "-crf", "18", "-pix_fmt", "yuv420p", "-movflags", "+faststart", a.out]
    ff = subprocess.Popen(cmd, stdin=subprocess.PIPE); N = int(DURATION * a.fps)
    for f in range(N):
        ff.stdin.write(R.frame(f / a.fps, a.fps).tobytes())
        if f % (a.fps * 3) == 0: print(f"{f / a.fps:5.1f}s", flush=True)
    ff.stdin.close(); ff.wait(); print("done", a.out)
