"""Panic & Profit Reel renderer (Friday crash, 3 blows, 2026-11-20). Skia 2D -> raw BGRA frames -> ffmpeg.
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
    a = overlay(t, P[1] - 0.2, P[7] - 0.3)
    if a <= 0: return
    alpha_layer(c, a)
    s = "BREAKING  ·  NASDAQ -5.3%  ·  S&P 500 -3.7%  ·  DOW -950  ·  NVIDIA -14%  ·  AMD -13%  ·  BROADCOM -12%  ·  SEC PROBE REPORT  ·  "
    c.drawRect(rect(0, 342, W, 46), paint(hexc(RED)))
    f = skia.Font(IN[700], 26); w = sum(f.measureText(ch) for ch in s) + 2 * len(s); off = -(t * 140) % w
    c.save(); c.clipRect(rect(0, 342, W, 46)); x = off - w
    while x < W: x += text(c, s, x, 374, 26, hexc("#FFFFFF"), IN[700], track=2) + 2
    c.restore(); c.restore()

def scene_hook(c, t):
    a = 1 - sstep(P[1] - 0.3, P[1] + 0.1, t)
    if a <= 0: return
    alpha_layer(c, a)
    text(c, "TODAY · FRI, NOV 20 · THE NASDAQ", W / 2, 540, 30, hexc(MUTE), IN[700], "c", track=5)
    k = ease_io((t - 0.4) / 2.2)
    text(c, f"-{5.3 * k:.1f}%", W / 2, 800, 250, hexc(RED), FR[800], "c")
    text(c, "in one day", W / 2, 890, 54, hexc(INK), FR[700], "c")
    x0, x1 = 140, 940; pts = [(x0, 1000), (x0 + 220, 1015), (x0 + 360, 1090), (x0 + 520, 1170), (x0 + 650, 1250), (x1, 1330)]
    n = max(2, int(len(pts) * 25 * k)); pth = skia.Path(); pth.moveTo(*pts[0]); cnt = 0
    for (a_, b_), (c_, d_) in zip(pts, pts[1:]):
        for s_ in range(1, 26):
            cnt += 1
            if cnt > n: break
            pth.lineTo(lerp(a_, c_, s_ / 25), lerp(b_, d_, s_ / 25))
    c.drawPath(pth, paint(hexc(RED), stroke=9))
    c.restore()

def scene_indexes(c, t):
    a = overlay(t, P[1] - 0.2, PE[1] + 0.2)
    if a <= 0: return
    alpha_layer(c, a)
    text(c, "TODAY'S CLOSE · FRI, NOV 20", W / 2, 470, 30, hexc(MUTE), IN[700], "c", track=5)
    rows = (("NASDAQ", "-5.3%"), ("S&P 500", "-3.7%"), ("DOW", "-950 pts"))
    for i, (nm, v) in enumerate(rows):
        tt = P[1] + i * 0.35
        if t < tt: continue
        y = 580 + i * 160; s = clamp(back_out((t - tt) / 0.4), 0, 1.15)
        c.save(); c.translate(W / 2, y); c.scale(s, s)
        hot = nm == "NASDAQ"
        c.drawRRect(rrect(-400, -66, 800, 132, 66), paint(hexc("#FFF1F3" if hot else "#FFFFFF"))); c.drawRRect(rrect(-400, -66, 800, 132, 66), paint(hexc(RED if hot else INK), stroke=6 if hot else 4))
        text(c, nm, -350, 18, 50, hexc(INK), FR[800]); tri(c, 60, 0, 32, False, hexc(RED)); text(c, v, 350, 22, 62, hexc(RED), FR[800], "r")
        c.restore()
    for i, (lab, tt) in enumerate((("7TH STRAIGHT LOSS", wtime("seventh", 1)), ("-8.6% THIS WEEK", wtime("eight", 1)))):
        if t < tt: continue
        s = clamp(back_out((t - tt) / 0.4), 0, 1.2); x = 300 + i * 480
        c.save(); c.translate(x, 1100); c.rotate(-4 + 8 * i); c.scale(s, s)
        w = tw(lab, 32, IN[700]) + 3 * len(lab) + 60
        c.drawRRect(rrect(-w / 2, -40, w, 80, 40), paint(hexc(RED))); text(c, lab, 0, 12, 32, hexc("#FFFFFF"), IN[700], "c", track=3); c.restore()
    c.restore()

BLOWS = [(3, "BLOW 1 · THE SEC REPORT", ["Reuters: SEC examining", "Nvidia's accounting"], [("NVIDIA", "-14%"), ("AMD", "-13%"), ("AVGO", "-12%")]),
         (4, "BLOW 2 · WASHINGTON", ["Trump threatens a tax on", "AI data centers built abroad"], []),
         (5, "BLOW 3 · AI DOUBTS", ["Not Nvidia's earnings,", "not Anthropic's IPO, helped"], [])]
def scene_blows(c, t):
    a = overlay(t, P[2] - 0.2, PE[5] + 0.3)
    if a <= 0: return
    alpha_layer(c, a)
    text(c, "3 BLOWS AT ONCE", W / 2, 470, 34, hexc(RED), IN[700], "c", track=8)
    # meter on the right: S&P falling as blows land
    for j, (ph, hd, lines, chips) in enumerate(BLOWS):
        tt = P[ph] - 0.1
        if t < tt: continue
        k = ease_out((t - tt) / 0.25); drop = (1 - k) * -500
        y = 540 + j * 250 + drop
        rot = [-2.5, 2, -1.5][j]
        c.save(); c.translate(W / 2, y + 110); c.rotate(rot * k); c.translate(-W / 2, -(y + 110))
        c.drawRRect(rrect(116, y + 8, 860, 220, 18), paint(hexc("#000000", .10), blur=10))
        c.drawRRect(rrect(110, y, 860, 220, 18), paint(hexc("#FFFFFF"))); c.drawRRect(rrect(110, y, 860, 220, 18), paint(hexc(INK), stroke=4))
        c.drawRect(rect(110, y, 18, 220), paint(hexc(RED)))
        text(c, hd, 160, y + 52, 26, hexc(RED), IN[700], track=4)
        for q, ln in enumerate(lines): text(c, ln, 160, y + 112 + q * 54, 44, hexc(INK), FR[800])
        c.restore()
        if chips and t > wtime("fourteen", 3) - 0.1:
            for q, (nm, v) in enumerate(chips):
                tq = wtime("fourteen", 3) - 0.1 + q * 0.3 if q == 0 else wtime("AMD", 3) + (q - 1) * 0.3
                if t < tq: continue
                s = clamp(back_out((t - tq) / 0.35), 0, 1.15); x = 250 + q * 290
                c.save(); c.translate(x, 1350); c.scale(s, s)
                c.drawRRect(rrect(-130, -50, 260, 100, 50), paint(hexc(RED))); text(c, f"{nm} {v}", 0, 12, 34, hexc("#FFFFFF"), IN[700], "c"); c.restore()
    c.restore()

def scene_now(c, t):
    a = overlay(t, P[6] - 0.2, PE[6] + 0.3)
    if a <= 0: return
    alpha_layer(c, a)
    text(c, "WHERE WE STAND", W / 2, 490, 34, hexc(INK), IN[700], "c", track=8)
    items = [("NASDAQ · 2026", "Negative YTD", wtime("negative", 6)), ("S&P 500 · FROM RECORD", "10%+ below", wtime("correction", 6) - 0.3)]
    for i, (lab, v, tt) in enumerate(items):
        if t < tt: continue
        s = clamp(back_out((t - tt) / 0.4), 0, 1.12); y = 700 + i * 260
        c.save(); c.translate(W / 2, y); c.scale(s, s)
        c.drawRRect(rrect(-420, -100, 840, 200, 26), paint(hexc("#FFFFFF"))); c.drawRRect(rrect(-420, -100, 840, 200, 26), paint(hexc(RED), stroke=6))
        text(c, lab, 0, -30, 32, hexc(MUTE), IN[700], "c", track=4); text(c, v, 0, 62, 92, hexc(RED), FR[800], "c"); c.restore()
    e = ease_out((t - (wtime("correction", 6) + 0.3)) / 0.4)
    if e > 0:
        alpha_layer(c, e); text(c, "Correction = 10%+ below the record", W / 2, 1250, 36, hexc(INK), IN[600], "c"); c.restore()
    c.restore()

def scene_long(c, t):
    a = overlay(t, P[7] - 0.2, PE[7] + 0.3)
    if a <= 0: return
    alpha_layer(c, a)
    text(c, "THE LONG-TERM VIEW", W / 2, 490, 34, hexc(GREEN), IN[700], "c", track=8)
    text(c, "A report", W / 2, 680, 120, hexc(INK), FR[800], "c")
    text(c, "is not a verdict.", W / 2, 810, 96, hexc(INK), FRI[800], "c")
    e = ease_out((t - wtime("charged", 7) + 0.6) / 0.4)
    if e > 0:
        alpha_layer(c, e)
        c.drawRRect(rrect(150, 900, 780, 90, 45), paint(hexc("#EAF5EE"))); text(c, "No charges have been filed.", W / 2, 960, 40, hexc(GREEN), IN[700], "c"); c.restore()
    f = ease_out((t - wtime("facts,", 7)) / 0.4) if wtime("facts,", 7) != P[7] else ease_out((t - (P[7] + 5)) / 0.4)
    if f > 0:
        alpha_layer(c, f)
        for i, (lab, col, x) in enumerate((("FACTS", GREEN, 330), ("FEAR", RED, 750))):
            c.drawRRect(rrect(x - 170, 1080, 340, 120, 60), paint(hexc(col) if i == 0 else hexc("#FFFFFF")))
            if i: c.drawRRect(rrect(x - 170, 1080, 340, 120, 60), paint(hexc(RED), stroke=5))
            text(c, lab, x, 1160, 60, hexc("#FFFFFF" if i == 0 else RED), FR[800], "c")
        c.drawLine(560, 1110, 520, 1170, paint(hexc(INK), stroke=6)); text(c, ">", 540, 1162, 60, hexc(INK), FR[800], "c") if False else None
        c.restore()
    c.restore()

def vote(c, t):
    t0 = P[8] - 0.1
    if t < t0: return
    a = ease_out((t - t0) / 0.45)
    c.drawRect(rect(0, 400, W, 1100), paint(hexc(BG, .97 * a)))
    alpha_layer(c, a)
    text(c, "YOUR CALL", W / 2, 640, 32, hexc(RED), IN[700], "c", track=8)
    text(c, "Is this panic,", W / 2, 790, 104, hexc(INK), FR[800], "c")
    text(c, "or profit?", W / 2, 910, 104, hexc(GREEN), FRI[800], "c")
    for i, (lab, col, x) in enumerate((("PANIC", RED, 290), ("PROFIT", GREEN, 790))):
        k = back_out((t - (t0 + 1.0 + i * 0.25)) / 0.4)
        if k <= 0: continue
        pulse = 1 + 0.04 * math.sin((t - t0) * 7 + i * 1.6)
        c.save(); c.translate(x, 1080); c.scale(clamp(k, 0, 1.2) * pulse, clamp(k, 0, 1.2) * pulse)
        c.drawRRect(rrect(-220, -70, 440, 140, 70), paint(hexc(col))); text(c, lab, 0, 22, 64, hexc("#FFFFFF"), FR[800], "c", track=3)
        c.restore()
    b = ease_out((t - (t0 + 1.8)) / 0.4); alpha_layer(c, b)
    text(c, "Comment PANIC or PROFIT", W / 2, 1240, 46, hexc(INK), IN[700], "c"); c.restore()
    c.restore()

def cam(t):
    z = 1.0
    for t0 in P[:8]: z += 0.03 * ease_out((t - t0) / 0.6) * (1 - ease_out((t - (t0 + 1.2)) / 2.0))
    sh = 0.0
    for st in (2.6, P[3] - 0.1 + 0.25, P[4] - 0.1 + 0.25, P[5] - 0.1 + 0.25):
        if st < t < st + 0.35: sh += 14 * math.exp(-(t - st) * 12) * math.sin((t - st) * 90)
    return z, sh

def scene_end(c, t):
    a = ease_out((t - (END + 0.15)) / 0.6)
    alpha_layer(c, a); logo(c, W / 2, 900, 118, line=True, tagline=True); c.restore()
    b = ease_out((t - (END + 0.6)) / 0.5); alpha_layer(c, b)
    pw = tw("Follow " + HANDLE, 44, IN[700]) + 90
    c.drawRRect(rrect(W / 2 - pw / 2, 1110 + (1 - b) * 20, pw, 96, 48), paint(hexc(GREEN)))
    text(c, "Follow " + HANDLE, W / 2, 1172 + (1 - b) * 20, 44, hexc("#FFFFFF"), IN[700], "c")
    text(c, "Save this for the next red day.", W / 2, 1280, 34, hexc(MUTE), IN[500], "c")
    text(c, "NOT FINANCIAL ADVICE", W / 2, 1390, 24, hexc(SOFT), IN[600], "c", track=4); c.restore()

SRC_TXT = "Sources: CNBC, Yahoo Finance, Reuters, Bloomberg, NBC News, Investing.com, Globe and Mail"

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
            scene_hook(c, t); scene_indexes(c, t); scene_blows(c, t); scene_now(c, t); scene_long(c, t)
            c.restore()
            vote(c, t); crawl(c, t)
            logo(c, 100, 285, 40, center=False)
            tg = "MARKET CRASH"; w = tw(tg, 24, IN[700]) + 3 * len(tg) + 40
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
