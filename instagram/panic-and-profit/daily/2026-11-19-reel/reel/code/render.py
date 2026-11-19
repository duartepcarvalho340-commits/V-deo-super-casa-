"""Panic & Profit Reel renderer (Anthropic IPO, 2026-11-19). Skia 2D -> raw BGRA frames -> ffmpeg.
Concept: "the trade confirmation" - a paper receipt prints out of a slot line by line with every number of the IPO,
then a rubber stamp lands on it.
Usage: python3 code/render.py --scale 1 --fps 60 --out exports/reel.mp4
       python3 code/render.py --scale 0.5 --out previews/s.png --still 1 5 8"""
import argparse, math, os, subprocess, sys
import numpy as np, skia
sys.path.insert(0, os.path.dirname(__file__))
from timing import FPS, DURATION, HANDLE, P, PE, END, FT, CLOSE, FT_IDX, LIVE

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


MONO = IN[600]
SLOT_Y = 380; RX, RW = 110, 860          # receipt x / width
ROW_H = 118
# rows: (time it prints, kind, data)
def rows():
    r = [(0.05, "head", None), (P[0] + 0.2, "big", ("THE BIGGEST IPO EVER", INK)),
         (P[1] + 1.2, "kv", ("PRICE / SHARE", "$83", GREEN, "range was $70–78")),
         (P[1] + 3.4, "kv", ("MONEY RAISED", "~$81.3B", INK, "largest IPO on record")),
         (P[2] + 0.6, "kv", ("VALUATION", "~$1.5T", INK, "fully diluted, at $83")),
         (P[3] + 0.5, "kv", ("REVENUE, H1", "$1.16B to $16.3B", GREEN, "2025 vs 2026, ~14x")),
         (P[4] + 0.9, "kv", ("PRICE / SALES", "~46x", RED, "valuation ÷ annualized H1 revenue")),
         (P[5] + 0.7, "kv", ("NET LOSS, H1 2026", "$80.7B", RED, "~$72.4B non-cash revaluation")),
         (P[5] + 2.4, "kv", ("OPERATING LOSS", "$693M", INK, "the core business, H1 2026")),
         (P[6] + 1.4, "kv", ("P/E (OFFICIAL)", "N/A", MUTE, "net loss = no P/E ratio")),
         (P[7] + 2.2, "kv", ("P/E, BEST QUARTER x4", "~385x", RED, "$1.5T ÷ ($974M Q2 profit × 4)")),
         (P[7] + 5.0, "kv", ("S&P 500 FORWARD P/E", "~18x", GREEN, "FactSet, Nov 2026"))]
    if FT:
        px, pc = FT.split("|"); col = GREEN if pc.strip().startswith("+") else RED
        r.append((P[FT_IDX] + 0.4, "kv", ("FIRST TRADE", f"${px}", col, f"{pc} vs the $83 IPO price, 11:50 a.m. ET")))
    else:
        r.append((P[FT_IDX] + 0.4, "kv", ("FIRST TRADE", "TODAY", INK, "Nasdaq · ticker ANT")))
    import json as _j, os as _o
    for k, e in enumerate(_j.loads(_o.environ.get("EXTRA", "[]"))):   # extra rows, one per extra voice line
        col = {"green": GREEN, "red": RED}.get(e.get("color", ""), INK)
        r.append((P[FT_IDX + 1 + k] + 0.4, "kv", (e["label"], e["value"], col, e.get("sub", ""))))
    return r
ROWS = rows()
HEAD_H = 230
def content_h(t):
    h = 0
    for i, (t0, kind, _) in enumerate(ROWS):
        if t < t0: break
        k = ease_out((t - t0) / 0.5); h += (HEAD_H if kind == "head" else (150 if kind == "big" else ROW_H)) * k
    return h
def offset(t):  # how far the receipt has scrolled up (keeps the newest line in view)
    vis = 1460 - SLOT_Y - 40
    return max(0.0, content_h(t) - vis)

def zig(c, y, col):
    p = skia.Path(); p.moveTo(RX, y); n = 30; w = RW / n
    for i in range(n): p.lineTo(RX + w * (i + .5), y + 18); p.lineTo(RX + w * (i + 1), y)
    p.lineTo(RX + RW, y - 2); p.lineTo(RX, y - 2); p.close(); c.drawPath(p, paint(col))

def receipt(c, t):
    off = offset(t); h = content_h(t); top = SLOT_Y - off
    if h <= 0: return
    c.save(); c.clipRect(skia.Rect.MakeLTRB(0, SLOT_Y, W, H))
    c.drawRect(rect(RX + 10, top + 10, RW, h + 20), paint(hexc("#000000", .06), blur=8))
    c.drawRect(rect(RX, top, RW, h), paint(hexc("#FFFFFF")))
    zig(c, top + h, hexc("#FFFFFF"))
    y = top
    for t0, kind, d in ROWS:
        if t < t0: break
        a = ease_out((t - t0) / 0.35)
        alpha_layer(c, a)
        if kind == "head":
            text(c, "TRADE CONFIRMATION", W / 2, y + 70, 30, hexc(MUTE), IN[700], "c", track=6)
            text(c, "ANT", W / 2, y + 160, 84, hexc(INK), FR[800], "c")
            text(c, "NASDAQ · NOV 19, 2026", W / 2, y + 205, 26, hexc(SOFT), IN[600], "c", track=3)
            hh = HEAD_H
        elif kind == "big":
            s, col = d; text(c, s, W / 2, y + 95, 62, hexc(col), FR[800], "c"); hh = 150
        else:
            lbl, val, col, sub = d
            text(c, lbl, RX + 50, y + 52, 26, hexc(MUTE), IN[700], track=3)
            text(c, sub, RX + 50, y + 92, 26, hexc(SOFT), IN[500])
            vs = 58 if tw(val, 58, FR[800]) < 430 else 46
            text(c, val, RX + RW - 50, y + 72, vs, hexc(col), FR[800], "r")
            hh = ROW_H
        # dotted separator
        for xx in range(RX + 40, RX + RW - 40, 18): c.drawLine(xx, y + hh - 2, xx + 8, y + hh - 2, paint(hexc(BORDER), stroke=3, cap_round=False))
        c.restore(); y += hh * ease_out((t - t0) / 0.5)
    c.restore()
    # printer slot (drawn on top)
    c.drawRRect(rrect(RX - 50, SLOT_Y - 34, RW + 100, 50, 25), paint(hexc(INK)))
    c.drawRect(rect(RX - 10, SLOT_Y - 6, RW + 20, 10), paint(hexc("#3A3A3A")))

def stamp(c, t):
    t0 = P[CLOSE] + 0.15
    if t < t0: return
    k = clamp((t - t0) / 0.28); s = lerp(2.4, 1.0, ease_out(k)); a = clamp(k * 1.6)
    c.save(); c.translate(W / 2, 1050); c.rotate(-8); c.scale(s, s)
    alpha_layer(c, a * 0.93)
    c.drawRRect(rrect(-440, -150, 880, 300, 18), paint(hexc("#FFFFFF", .88)))
    c.drawRRect(rrect(-440, -150, 880, 300, 18), paint(hexc(RED), stroke=10))
    c.drawRRect(rrect(-422, -132, 844, 264, 12), paint(hexc(RED), stroke=3))
    text(c, "DAY ONE = HEADLINE", 0, -20, 56, hexc(RED), FR[800], "c")
    text(c, "NUMBERS = THE STORY", 0, 70, 56, hexc(GREEN), FR[800], "c")
    c.restore(); c.restore()

def plain(c, t):
    """'In plain English' card over the receipt: years of profit to earn back the price."""
    t0, t1 = P[8] - 0.15, PE[9] + 0.35
    if t < t0 or t > t1 + 0.4: return
    a = ease_out((t - t0) / 0.4) * (1 - sstep(t1, t1 + 0.4, t))
    c.drawRect(rect(0, 330, W, 1250), paint(hexc(BG, .95 * a)))
    alpha_layer(c, a)
    text(c, "IN PLAIN ENGLISH", W / 2, 520, 30, hexc(GREEN), IN[700], "c", track=6)
    text(c, "Years of today's profit", W / 2, 620, 62, hexc(INK), FR[800], "c")
    text(c, "to earn back the price", W / 2, 695, 62, hexc(INK), FR[800], "c")
    k = ease_io((t - (t0 + 0.5)) / 1.6); x0, wmax = 110, 860
    for i, (lab, yrs, col) in enumerate((("ANT at $83", 385, RED), ("S&P 500", 18, GREEN))):
        y = 800 + i * 200
        text(c, lab, x0, y, 34, hexc(INK), IN[700])
        wv = max(14, wmax * yrs / 385 * k)
        c.drawRRect(rrect(x0, y + 22, wv, 74, 8), paint(hexc(col)))
        lbl = f"~{int(round(yrs * k))} yrs"
        if wv > 260: text(c, lbl, x0 + wv - 24, y + 74, 44, hexc("#FFFFFF"), FR[800], "r")
        else: text(c, lbl, x0 + wv + 20, y + 74, 44, hexc(col), FR[800])
    b = ease_out((t - P[9]) / 0.45)
    if b > 0:
        alpha_layer(c, b)
        c.drawRRect(rrect(110, 1230, 860, 170, 16), paint(hexc("#FFFFFF"))); c.drawRRect(rrect(110, 1230, 860, 170, 16), paint(hexc(INK), stroke=4))
        text(c, "FAIR PRICE?", W / 2, 1282, 26, hexc(MUTE), IN[700], "c", track=5)
        text(c, "Only if profits grow 20x+", W / 2, 1360, 54, hexc(INK), FR[800], "c")
        c.restore()
    c.restore()

OPEN_PX, OPEN_PC = 111.50, "+34.3%"
def live(c, t):
    """After the receipt: a live quote board with the opening price and the math re-done at $111.50."""
    t0 = P[FT_IDX] + 1.6; t1 = PE[LIVE + 3] + 0.4
    if t < t0 or t > t1 + 0.45: return
    a = ease_out((t - t0) / 0.45) * (1 - sstep(t1, t1 + 0.45, t))
    c.drawRect(rect(0, 330, W, 1250), paint(hexc(BG, .97 * a)))
    alpha_layer(c, a)
    # header: live dot + ticker
    blink = 0.55 + 0.45 * math.sin(t * 6)
    c.drawCircle(130, 470, 12, paint(hexc(RED, blink)))
    text(c, "LIVE · NASDAQ: ANT", 156, 481, 30, hexc(INK), IN[700], track=4)
    text(c, "OPENED 11:50 A.M. ET", W - 110, 481, 26, hexc(MUTE), IN[700], "r", track=3)
    k = ease_io((t - t0) / 1.6)
    text(c, f"${lerp(83, OPEN_PX, k):.2f}", 110, 680, 170, hexc(INK), FR[800])
    if k > 0.95:
        c.drawRRect(rrect(110, 712, 250, 70, 35), paint(hexc(GREEN))); text(c, OPEN_PC, 235, 760, 36, hexc("#FFFFFF"), IN[700], "c")
    # mini chart: IPO price line and the move up
    cx0, cx1, cy83, cyop = 400, 970, 790, 700
    for xx in range(cx0, cx1, 22): c.drawLine(xx, cy83, xx + 10, cy83, paint(hexc(SOFT), stroke=3, cap_round=False))
    text(c, "$83 IPO", cx1, cy83 + 36, 24, hexc(MUTE), IN[600], "r")
    pts = [(cx0, cy83), (cx0 + 120, cy83 - 6), (cx0 + 200, cyop + 30), (cx0 + 330, cyop + 8), (cx0 + 450, cyop - 6), (cx1, cyop)]
    n = int(len(pts) * 40 * k); path = skia.Path(); path.moveTo(*pts[0]); done = 0
    for (x0_, y0_), (x1_, y1_) in zip(pts, pts[1:]):
        for s_ in range(1, 41):
            done += 1
            if done > n: break
            path.lineTo(lerp(x0_, x1_, s_ / 40), lerp(y0_, y1_, s_ / 40))
    c.drawPath(path, paint(hexc(GREEN), stroke=7))
    # market value line
    b = ease_out((t - P[LIVE]) / 0.45)
    if b > 0:
        alpha_layer(c, b); text(c, "Market value at the open: ~$2.0T", 110, 880, 40, hexc(INK), FR[700]); c.restore()
    # the math, updated
    rows = (("VALUATION", "~$1.5T", "~$2.0T", INK, P[LIVE] + 0.4),
            ("PRICE / SALES", "~46x", "~62x", RED, P[LIVE + 1] + 0.6),
            ("P/E, BEST QUARTER x4", "~385x", "~517x", RED, P[LIVE + 2] + 0.8))
    hb = ease_out((t - (P[LIVE] + 0.2)) / 0.4)
    if hb > 0:
        alpha_layer(c, hb)
        c.drawRect(rect(110, 930, 860, 380), paint(hexc("#FFFFFF"))); c.drawRect(rect(110, 930, 860, 380), paint(hexc(INK), stroke=4, cap_round=False))
        text(c, "UPDATED MATH", 150, 985, 26, hexc(GREEN), IN[700], track=4)
        text(c, "AT $83", 690, 985, 22, hexc(SOFT), IN[700], "r", track=2); text(c, "AT $111.50", 930, 985, 22, hexc(INK), IN[700], "r", track=2)
        c.restore()
    for i, (lbl, old, new, col, tr) in enumerate(rows):
        e = ease_out((t - tr) / 0.4)
        if e <= 0: continue
        y = 1060 + i * 82; alpha_layer(c, e)
        text(c, lbl, 150, y + 10, 28, hexc(INK), IN[700], track=2)
        w_old = text(c, old, 690, y + 12, 40, hexc(SOFT), FR[700], "r")
        c.drawLine(690 - w_old, y - 2, 690, y - 2, paint(hexc(SOFT), stroke=3))
        text(c, new, 930, y + 14, 52, hexc(col), FR[800], "r")
        c.restore()
    f = ease_out((t - P[LIVE + 3]) / 0.45)
    if f > 0:
        alpha_layer(c, f)
        c.drawRRect(rrect(110, 1335, 860, 150, 16), paint(hexc(INK)))
        text(c, "FAIR PRICE NOW?", W / 2, 1385, 26, hexc("#FFFFFF", .7), IN[700], "c", track=5)
        text(c, "Only if profits grow ~29x", W / 2, 1455, 52, hexc("#FFFFFF"), FR[800], "c")
        c.restore()
    c.restore()

def question(c, t):
    t0 = P[-1] - 0.1
    if t < t0: return
    a = ease_out((t - t0) / 0.45)
    c.drawRect(rect(0, 330, W, 1250), paint(hexc(BG, .93 * a)))
    alpha_layer(c, a); dy = (1 - a) * 30
    text(c, "YOUR CALL", W / 2, 700 + dy, 30, hexc(RED), IN[700], "c", track=6)
    text(c, "Is $111.50 a share", W / 2, 840 + dy, 88, hexc(INK), FR[800], "c")
    text(c, "too much?", W / 2, 950 + dy, 92, hexc(RED), FRI[800], "c")
    b = ease_out((t - (t0 + 1.3)) / 0.45)
    alpha_layer(c, b)
    text(c, "What's Anthropic really worth?", W / 2, 1090 + dy, 50, hexc(INK), FR[700], "c")
    pw = tw("Tell us in the comments", 38, IN[700]) + 80
    c.drawRRect(rrect(W / 2 - pw / 2, 1170, pw, 84, 42), paint(hexc(INK)))
    text(c, "Tell us in the comments", W / 2, 1225, 38, hexc("#FFFFFF"), IN[700], "c")
    c.restore(); c.restore()

def scene_end(c, t):
    a = ease_out((t - (END + 0.15)) / 0.6)
    alpha_layer(c, a); logo(c, W / 2, 900, 118, line=True, tagline=True); c.restore()
    b = ease_out((t - (END + 0.6)) / 0.5); alpha_layer(c, b)
    pw = tw("Follow " + HANDLE, 44, IN[700]) + 90
    c.drawRRect(rrect(W / 2 - pw / 2, 1110 + (1 - b) * 20, pw, 96, 48), paint(hexc(GREEN)))
    text(c, "Follow " + HANDLE, W / 2, 1172 + (1 - b) * 20, 44, hexc("#FFFFFF"), IN[700], "c")
    text(c, "Save this for the next big IPO.", W / 2, 1280, 34, hexc(MUTE), IN[500], "c")
    text(c, "NOT FINANCIAL ADVICE · NOT AFFILIATED WITH ANTHROPIC", W / 2, 1390, 22, hexc(SOFT), IN[600], "c", track=3); c.restore()

SRC_TXT = "Sources: CNN, Yahoo Finance, NBC, CNBC, Anthropic S-1, FactSet · P/S and P/E are illustrative math"

class Renderer:
    def __init__(self, scale):
        self.scale = scale; self.surf = skia.Surface(int(W * scale), int(H * scale))
    def draw(self, t):
        c = self.surf.getCanvas(); c.save(); c.scale(self.scale, self.scale); background(c)
        fade = 1 - sstep(END - 0.1, END + 0.25, t)
        if fade > 0:
            alpha_layer(c, fade); receipt(c, t); plain(c, t); live(c, t); stamp(c, t); question(c, t)
            logo(c, 100, 285, 40, center=False)
            tg = "IPO DAY"; w = tw(tg, 24, IN[700]) + 3 * 6 + 40
            c.drawRRect(rrect(W - 100 - w, 250, w, 50, 25), paint(hexc(RED)))
            text(c, tg, W - 100 - w / 2, 284, 24, hexc("#FFFFFF"), IN[700], "c", track=3)
            sa = sstep(2.8, 3.3, t); alpha_layer(c, sa); text(c, SRC_TXT, W / 2, 1535, 22, hexc(SOFT), IN[500], "c"); c.restore()
            c.restore()
        if t > END: scene_end(c, t)
        c.restore(); return self.surf.makeImageSnapshot().toarray()
    def frame(self, t, fps):
        dt = 1 / fps; sp = abs(offset(t + dt / 2) - offset(t - dt / 2))
        n = 1 if sp < 6 else int(min(8, 3 + sp / 8))
        if n == 1: return self.draw(t)
        acc = sum(self.draw(t + dt * (k / n - 0.5)).astype(np.float32) for k in range(n)); return (acc / n).astype(np.uint8)

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
