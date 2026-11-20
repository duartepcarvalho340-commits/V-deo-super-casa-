"""Panic & Profit Reel renderer (market selloff dominoes, 2026-11-20). Skia 2D -> raw BGRA frames -> ffmpeg.
Concept: "dominoes" - index counters fall, then three cause tiles (rates, AI doubts, IPO fade) topple into
the S&P 500 tile; a perspective chart; PANIC / PROFIT vote.
Usage: python3 code/render.py --scale 1 --fps 60 --out exports/reel.mp4
       python3 code/render.py --scale 0.5 --out previews/s.png --still 1 5 8"""
import argparse, math, os, subprocess, sys
import numpy as np, skia
sys.path.insert(0, os.path.dirname(__file__))
from timing import FPS, DURATION, HANDLE, P, PE, END, _T

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

def crawl(c, t):
    s = "BREAKING  ·  SHORT REPORT  ·  AMD  ·  EXPORT CONTROLS  ·  ENTITY LIST  ·  CHIP STOCKS  ·  "
    c.drawRect(rect(0, 342, W, 46), paint(hexc(RED)))
    f = skia.Font(IN[700], 26); w = sum(f.measureText(ch) for ch in s) + 2 * (len(s) - 1) + 90; off = -(t * 140) % w
    c.save(); c.clipRect(rect(0, 342, W, 46))
    x = off - w
    while x < W: text(c, s, x, 374, 26, hexc("#FFFFFF"), IN[700], track=2); x += w
    c.restore()

def hook_chart(c, t):
    k = ease_io((t - 0.6) / 2.6)
    if k <= 0: return
    x0, x1, ytop, ybot = 130, 950, 1180, 1440
    pts = [(x0, ytop), (x0 + 160, ytop + 12), (x0 + 260, ytop + 70), (x0 + 380, ytop + 150), (x0 + 520, ytop + 200), (x0 + 680, ytop + 235), (x1, ybot - 10)]
    n = max(2, int(len(pts) * k * 30)); path = skia.Path(); path.moveTo(*pts[0]); cnt = 0
    for (a_, b_), (c_, d_) in zip(pts, pts[1:]):
        for s_ in range(1, 31):
            cnt += 1
            if cnt > n: break
            path.lineTo(lerp(a_, c_, s_ / 30), lerp(b_, d_, s_ / 30))
    c.drawPath(path, paint(hexc(RED), stroke=9))
    for xx in range(x0, x1, 24): c.drawLine(xx, ytop, xx + 12, ytop, paint(hexc("#B9AE92"), stroke=3, cap_round=False))
    text(c, "prior close", x1, ytop - 16, 24, hexc("#8A7A58"), IN[600], "r")

def vote_unused(c, t):
    t0 = P[7] + 1.2
    if t < t0: return
    for i, (lab, col, x) in enumerate((("DIP", GREEN, 290), ("KNIFE", RED, 790))):
        k = back_out((t - (t0 + i * 0.25)) / 0.4)
        if k <= 0: continue
        pulse = 1 + 0.04 * math.sin((t - t0) * 7 + i * 1.6)
        c.save(); c.translate(x, 1170); c.scale(clamp(k, 0, 1.2) * pulse, clamp(k, 0, 1.2) * pulse)
        c.drawRRect(rrect(-210, -70, 420, 140, 70), paint(hexc(col)))
        text(c, lab, 0, 22, 66, hexc("#FFFFFF"), FR[800], "c", track=3)
        c.restore()
    a = ease_out((t - (t0 + 0.7)) / 0.4); alpha_layer(c, a)
    text(c, "Comment DIP or KNIFE 👇" if False else "Comment DIP or KNIFE", W / 2, 1330, 46, hexc(INK), IN[700], "c"); c.restore()

def cam(t):
    """punch-in zoom per phrase + shake on the stamp"""
    z = 1.0
    for i, t0 in enumerate(P[:7]):
        z += 0.035 * ease_out((t - t0) / 0.6) * (1 - ease_out((t - (t0 + 1.2)) / 2.0))
    sh = 0.0; st = P[2] + 3.35
    if st < t < st + 0.35: sh = 14 * math.exp(-(t - st) * 12) * math.sin((t - st) * 90)
    return z, sh



def ease_in(t): t = clamp(t); return t ** 3
def overlay(c, t, t0, t1):
    a = ease_out((t - t0) / 0.4) * (1 - sstep(t1, t1 + 0.4, t)); return a

def scene_hook(c, t):
    a = 1 - sstep(P[1] - 0.3, P[1] + 0.1, t)
    if a <= 0: return
    alpha_layer(c, a)
    k = ease_io((t - 0.3) / 2.2)
    text(c, "THE DOW", W / 2, 560, 34, hexc(MUTE), IN[700], "c", track=8)
    text(c, f"-{int(1101 * k):,}", W / 2, 790, 230, hexc(RED), FR[800], "c")
    text(c, "points in one day", W / 2, 880, 50, hexc(INK), FR[700], "c")
    # falling line
    x0, x1 = 140, 940; pts = [(x0, 980), (x0 + 200, 1000), (x0 + 330, 1080), (x0 + 470, 1110), (x0 + 600, 1200), (x1, 1260)]
    n = max(2, int(len(pts) * 25 * k)); pth = skia.Path(); pth.moveTo(*pts[0]); cnt = 0
    for (a_, b_), (c_, d_) in zip(pts, pts[1:]):
        for s_ in range(1, 26):
            cnt += 1
            if cnt > n: break
            pth.lineTo(lerp(a_, c_, s_ / 25), lerp(b_, d_, s_ / 25))
    c.drawPath(pth, paint(hexc(RED), stroke=9))
    e = ease_out((t - 2.8) / 0.4)
    if e > 0:
        alpha_layer(c, e); text(c, "Closed at 49,097: first close below 50,000 since June", W / 2, 1340, 30, hexc(MUTE), IN[600], "c"); c.restore()
    c.restore()

def scene_indexes(c, t):
    a = overlay(c, t, P[1] - 0.2, PE[1] + 0.2)
    if a <= 0: return
    alpha_layer(c, a)
    for i, (nm, v) in enumerate((("DOW", "-2.2%"), ("S&P 500", "-2.0%"), ("NASDAQ", "-2.3%"))):
        k = back_out((t - (P[1] + i * 0.35)) / 0.4)
        if t < P[1] + i * 0.35: continue
        y = 560 + i * 170; s = clamp(k, 0, 1.15)
        c.save(); c.translate(W / 2, y); c.scale(s, s)
        c.drawRRect(rrect(-400, -70, 800, 140, 70), paint(hexc("#FFFFFF"))); c.drawRRect(rrect(-400, -70, 800, 140, 70), paint(hexc(INK), stroke=4))
        text(c, nm, -350, 18, 50, hexc(INK), FR[800]); tri(c, 100, 0, 34, False, hexc(RED)); text(c, v, 350, 22, 66, hexc(RED), FR[800], "r")
        c.restore()
    for i, (lab, tt) in enumerate((("6TH STRAIGHT LOSS", P[1] + 2.2), ("-8.2% FROM RECORD", P[1] + 3.6))):
        k = back_out((t - tt) / 0.4)
        if t < tt: continue
        s = clamp(k, 0, 1.2); x = 300 + i * 480
        c.save(); c.translate(x, 1100); c.rotate(-4 + 8 * i); c.scale(s, s)
        w = tw(lab, 32, IN[700]) + 3 * len(lab) + 60
        c.drawRRect(rrect(-w / 2, -40, w, 80, 40), paint(hexc(RED))); text(c, lab, 0, 12, 32, hexc("#FFFFFF"), IN[700], "c", track=3); c.restore()
    c.restore()

TILES = [("FED", 190), ("AI", 410), ("IPO", 630), ("S&P", 870)]
FLOOR = 1300; TW, TH = 120, 330
def fall_times():
    f1 = P[4] - 0.55; f2 = P[5] - 0.55; f3 = PE[5] - 1.6; f4 = f3 + 0.45
    return [f1, f2, f3, f4]
def tile_angle(i, t):
    ft = fall_times()[i]; maxa = 62 if i < 3 else 84
    return maxa * ease_in((t - ft) / 0.5) if t > ft else 0.0
def scene_dominoes(c, t):
    a = overlay(c, t, P[2] - 0.2, PE[5] + 0.6)
    if a <= 0: return
    alpha_layer(c, a)
    text(c, "THINK DOMINOES", W / 2, 560, 34, hexc(RED), IN[700], "c", track=8)
    c.drawLine(80, FLOOR, W - 80, FLOOR, paint(hexc(INK), stroke=6))
    active = 0 if t < P[4] else (1 if t < P[5] else 2)
    for i, (lab, cx) in enumerate(TILES):
        ang = tile_angle(i, t)
        c.save(); c.translate(cx + TW / 2, FLOOR); c.rotate(ang); c.translate(-(cx + TW / 2), -FLOOR)
        hot = (i == active and t > P[3] - 0.2) or i == 3
        fill = RED if (i == 3) else ("#FFFFFF")
        c.drawRRect(rrect(cx - TW / 2 + 6, FLOOR - TH + 8, TW, TH, 14), paint(hexc("#000000", .08), blur=8))
        c.drawRRect(rrect(cx - TW / 2, FLOOR - TH, TW, TH, 14), paint(hexc(fill)))
        c.drawRRect(rrect(cx - TW / 2, FLOOR - TH, TW, TH, 14), paint(hexc(RED if hot else INK), stroke=6))
        for d in range(3): c.drawCircle(cx, FLOOR - TH + 70 + d * 70, 12, paint(hexc("#FFFFFF" if i == 3 else INK)))
        c.save(); c.translate(cx, FLOOR - 40); text(c, lab, 0, 0, 34 if len(lab) > 3 else 40, hexc("#FFFFFF" if i == 3 else INK), IN[700], "c"); c.restore()
        c.restore()
    # detail card for the active domino
    cards = [(P[3], "DOMINO 1 · RATES", ["Markets expect another", "Fed hike on Dec 9"]),
             (P[4], "DOMINO 2 · AI DOUBTS", ["Nvidia CEO exit +", "AMD short report (alleged)"]),
             (P[5], "DOMINO 3 · IPO FADE", ["Anthropic: +34% at the open", "+17% at the close ($97.17)"])]
    for j, (tt, hd, lines) in enumerate(cards):
        nxt = cards[j + 1][0] if j + 1 < len(cards) else PE[5] + 0.5
        e = ease_out((t - (tt - 0.1)) / 0.35) * (1 - sstep(nxt - 0.3, nxt, t))
        if e <= 0: continue
        alpha_layer(c, e); y = 640 + (1 - e) * 20
        c.drawRRect(rrect(110, y, 860, 250, 18), paint(hexc("#FFFFFF"))); c.drawRRect(rrect(110, y, 860, 250, 18), paint(hexc(INK), stroke=4))
        text(c, hd, 150, y + 60, 28, hexc(RED), IN[700], track=4)
        for k_, ln in enumerate(lines): text(c, ln, 150, y + 130 + k_ * 64, 50, hexc(INK), FR[800])
        c.restore()
    c.restore()

def scene_perspective(c, t):
    a = overlay(c, t, P[6] - 0.2, PE[7] + 0.3)
    if a <= 0: return
    alpha_layer(c, a)
    text(c, "PERSPECTIVE", W / 2, 560, 34, hexc(GREEN), IN[700], "c", track=8)
    text(c, "S&P 500, since 1980", W / 2, 640, 50, hexc(INK), FR[700], "c")
    k = ease_io((t - (P[6] + 1.0)) / 1.6); top = 720; scale = 24
    for i, (lab, v, col) in enumerate((("Average drop at some\\npoint in a year", 14, MUTE), ("Now, from the record", 8.2, RED))):
        x = 270 + i * 520; h = v * scale * k
        c.drawRect(rect(x - 110, top, 220, h), paint(hexc(col)))
        text(c, f"-{v * k:.0f}%" if i == 0 else f"-{v * k:.1f}%", x, top + h + 70, 64, hexc(col), FR[800], "c")
        for li, ln in enumerate(lab.split("\\n")): text(c, ln, x, top - 60 + li * 0 if False else top + h + 120 + li * 40, 30, hexc(INK), IN[600], "c")
    c.drawLine(120, top, W - 120, top, paint(hexc(INK), stroke=5))
    e = ease_out((t - (P[6] + 6.4)) / 0.4) if False else ease_out((t - (P[6] + 6.4)) / 0.4)
    if e > 0:
        alpha_layer(c, e)
        text(c, "Still finished higher in ~3 of 4 years", W / 2, 1275, 40, hexc(INK), IN[700], "c")
        for q in range(4):
            col = GREEN if q < 3 else RED
            c.drawRRect(rrect(W / 2 - 230 + q * 120, 1300, 100, 60, 14), paint(hexc(col)))
        c.restore()
    f = ease_out((t - P[7]) / 0.4)
    if f > 0:
        alpha_layer(c, f)
        c.drawRect(rect(0, 400, W, 1100), paint(hexc(BG, .95)))
        text(c, "-8% hurts.", W / 2, 860, 110, hexc(RED), FR[800], "c")
        text(c, "It's not unusual.", W / 2, 990, 96, hexc(INK), FRI[800], "c")
        c.restore()
    c.restore()

def vote(c, t):
    t0 = P[8] - 0.1
    if t < t0: return
    a = ease_out((t - t0) / 0.45)
    c.drawRect(rect(0, 400, W, 1100), paint(hexc(BG, .97 * a)))
    alpha_layer(c, a)
    text(c, "YOUR CALL", W / 2, 640, 30, hexc(RED), IN[700], "c", track=6)
    text(c, "Is this panic", W / 2, 780, 100, hexc(INK), FR[800], "c")
    text(c, "or profit?", W / 2, 900, 100, hexc(GREEN), FRI[800], "c")
    for i, (lab, col, x) in enumerate((("PANIC", RED, 290), ("PROFIT", GREEN, 790))):
        k = back_out((t - (t0 + 1.0 + i * 0.25)) / 0.4)
        if k <= 0: continue
        pulse = 1 + 0.04 * math.sin((t - t0) * 7 + i * 1.6)
        c.save(); c.translate(x, 1080); c.scale(clamp(k, 0, 1.2) * pulse, clamp(k, 0, 1.2) * pulse)
        c.drawRRect(rrect(-220, -70, 440, 140, 70), paint(hexc(col))); text(c, lab, 0, 22, 66, hexc("#FFFFFF"), FR[800], "c", track=3)
        c.restore()
    b = ease_out((t - (t0 + 1.8)) / 0.4); alpha_layer(c, b)
    text(c, "Comment PANIC or PROFIT", W / 2, 1240, 46, hexc(INK), IN[700], "c"); c.restore()
    c.restore()

def scene_end(c, t):
    a = ease_out((t - (END + 0.15)) / 0.6)
    alpha_layer(c, a); logo(c, W / 2, 900, 118, line=True, tagline=True); c.restore()
    b = ease_out((t - (END + 0.6)) / 0.5); alpha_layer(c, b)
    pw = tw("Follow " + HANDLE, 44, IN[700]) + 90
    c.drawRRect(rrect(W / 2 - pw / 2, 1110 + (1 - b) * 20, pw, 96, 48), paint(hexc(GREEN)))
    text(c, "Follow " + HANDLE, W / 2, 1172 + (1 - b) * 20, 44, hexc("#FFFFFF"), IN[700], "c")
    text(c, "Save this for the next red day.", W / 2, 1280, 34, hexc(MUTE), IN[500], "c")
    text(c, "NOT FINANCIAL ADVICE", W / 2, 1390, 24, hexc(SOFT), IN[600], "c", track=4); c.restore()

SRC_TXT = "Sources: AP (ABC, Washington Post), CNBC, Fortune, Forbes, J.P. Morgan Guide to the Markets"

class Renderer:
    def __init__(self, scale):
        self.scale = scale; self.surf = skia.Surface(int(W * scale), int(H * scale))
    def draw(self, t):
        c = self.surf.getCanvas(); c.save(); c.scale(self.scale, self.scale); background(c)
        fade = 1 - sstep(END - 0.1, END + 0.25, t)
        if fade > 0:
            alpha_layer(c, fade)
            z, sh = cam(t)
            ft = fall_times()
            for f_ in ft:
                hit = f_ + 0.5
                if hit < t < hit + 0.3: sh += 10 * math.exp(-(t - hit) * 14) * math.sin((t - hit) * 90)
            c.save(); c.translate(W / 2 + sh, 980); c.scale(z, z); c.translate(-W / 2, -980)
            scene_hook(c, t); scene_indexes(c, t); scene_dominoes(c, t); scene_perspective(c, t)
            c.restore()
            vote(c, t)
            logo(c, 100, 285, 40, center=False)
            tg = "SELLOFF"; w = tw(tg, 24, IN[700]) + 3 * 6 + 40
            c.drawRRect(rrect(W - 100 - w, 250, w, 50, 25), paint(hexc(RED)))
            text(c, tg, W - 100 - w / 2, 284, 24, hexc("#FFFFFF"), IN[700], "c", track=3)
            captions(c, t)
            sa = sstep(5.0, 5.5, t); alpha_layer(c, sa); text(c, SRC_TXT, W / 2, 1565, 22, hexc(SOFT), IN[500], "c"); c.restore()
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
