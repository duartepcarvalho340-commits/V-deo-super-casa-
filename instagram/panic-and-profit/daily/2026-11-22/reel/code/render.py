"""Panic & Profit Reel renderer (VIX fear gauge, 2026-11-20). Skia 2D -> raw BGRA frames -> ffmpeg.
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



AMBER, ORANGE = "#D99A00", "#E0601A"
GC = (540, 1180); GR = 300; VMAX = 60.0
def ang(v): return math.radians(180 + 180 * clamp(v / VMAX))
def gauge(c, t, v, hl=None):
    cx, cy = GC; r = GR
    zones = [(0, 20, GREEN, "CALM"), (20, 30, AMBER, ""), (30, 40, ORANGE, "FEAR"), (40, 60, RED, "PANIC")]
    for i, (a0, a1, col, lab) in enumerate(zones):
        on = 1.0 if hl is None else (1.0 if hl == i else 0.25)
        p = paint(hexc(col, on), stroke=56, cap_round=False)
        c.drawArc(rect(cx - r, cy - r, 2 * r, 2 * r), 180 + 180 * a0 / VMAX + 0.6, 180 * (a1 - a0) / VMAX - 1.2, False, p)
    for tick in (0, 20, 30, 40, 60):
        a = ang(tick); x0, y0 = cx + (r + 40) * math.cos(a), cy + (r + 40) * math.sin(a)
        text(c, str(tick), x0, y0 + 10, 28, hexc(MUTE), IN[700], "c")
    a = ang(v); L = r - 50
    c.drawLine(cx, cy, cx + L * math.cos(a), cy + L * math.sin(a), paint(hexc(INK), stroke=12))
    c.drawCircle(cx, cy, 26, paint(hexc(INK)))

def needle_v(t):
    k = ease_io((t - 0.5) / 2.6); v = lerp(16.6, 35.89, k)
    if wtime('forty', 1) - 0.3 < t < P[2] - 0.3:
        u = clamp((t - (wtime('forty', 1) - 0.3)) / 1.4); v = 35.89 + 4.14 * math.sin(math.pi * u)
    if t > wtime('forty', 1) + 1.1: v = 35.89 + 0.6 * math.sin(t * 9) * (P[3] - 0.5 > t)
    return v

def scene_gauge(c, t):
    a = 1 - sstep(PE[3] + 0.1, PE[3] + 0.5, t)
    if a <= 0: return
    alpha_layer(c, a)
    hl = None
    if P[3] - 0.1 < t:
        hl = 0 if t < wtime("thirty", 3) else (2 if t < wtime("forty", 3) else 3)
    v = needle_v(t); gauge(c, t, v, hl)
    text(c, f"{v:.2f}" if t < P[2] else "35.89", GC[0], GC[1] + 110, 84, hexc(ORANGE if v < 40 else RED), FR[800], "c")
    intr = wtime("forty", 1) - 0.3 < t < P[2] - 0.3
    text(c, "VIX · FRIDAY, INTRADAY" if intr else "VIX · FRI CLOSE", GC[0], GC[1] + 160, 26, hexc(MUTE), IN[700], "c", track=4)
    # top text block per phrase
    if t < P[2] - 0.2:
        e = 1 - sstep(P[2] - 0.5, P[2] - 0.2, t)
        alpha_layer(c, e)
        text(c, "WALL STREET'S FEAR GAUGE", W / 2, 500, 30, hexc(MUTE), IN[700], "c", track=6)
        text(c, "Highest close", W / 2, 610, 84, hexc(INK), FR[800], "c")
        text(c, "since April 2025", W / 2, 710, 74, hexc(RED), FRI[800], "c")
        if t > wtime('forty', 1) - 0.3:
            s = clamp(back_out((t - (wtime('forty', 1) - 0.3)) / 0.4), 0, 1.15)
            c.save(); c.translate(W / 2, 790); c.rotate(-3); c.scale(s, s)
            lab = "INTRADAY HIGH: 40"; w = tw(lab, 32, IN[700]) + 3 * len(lab) + 60
            c.drawRRect(rrect(-w / 2, -36, w, 72, 36), paint(hexc(RED))); text(c, lab, 0, 12, 32, hexc("#FFFFFF"), IN[700], "c", track=3); c.restore()
        c.restore()
    elif t < P[3] - 0.2:
        e = ease_out((t - (P[2] - 0.2)) / 0.4) * (1 - sstep(P[3] - 0.5, P[3] - 0.2, t))
        alpha_layer(c, e)
        text(c, "WHAT IS THE VIX?", W / 2, 490, 30, hexc(MUTE), IN[700], "c", track=6)
        text(c, "The price of", W / 2, 600, 80, hexc(INK), FR[800], "c")
        text(c, "crash insurance.", W / 2, 700, 80, hexc(RED), FRI[800], "c")
        text(c, "Expected S&P 500 swings over 30 days, priced from options", W / 2, 770, 26, hexc(MUTE), IN[500], "c")
        c.restore()
    else:
        e = ease_out((t - (P[3] - 0.2)) / 0.4); alpha_layer(c, e)
        text(c, "HOW TO READ IT", W / 2, 490, 30, hexc(MUTE), IN[700], "c", track=6)
        labs = [("< 20", "CALM", GREEN, P[3]), ("> 30", "FEAR", ORANGE, wtime("thirty", 3)), ("> 40", "PANIC", RED, wtime("forty", 3))]
        for i, (n, l, col, tt) in enumerate(labs):
            if t < tt - 0.1: continue
            s = clamp(back_out((t - tt + 0.1) / 0.35), 0, 1.15); x = 220 + i * 320
            c.save(); c.translate(x, 650); c.scale(s, s)
            c.drawRRect(rrect(-140, -90, 280, 180, 24), paint(hexc(col)))
            text(c, n, 0, -10, 56, hexc("#FFFFFF"), FR[800], "c"); text(c, l, 0, 50, 34, hexc("#FFFFFF"), IN[700], "c", track=4); c.restore()
        c.restore()
    c.restore()

def scene_history(c, t):
    a = overlay(t, P[4] - 0.2, PE[5] + 0.3)
    if a <= 0: return
    alpha_layer(c, a)
    text(c, "THE TWIST · SINCE 1998", W / 2, 490, 30, hexc(GREEN), IN[700], "c", track=6)
    text(c, "VIX crosses 35 →", W / 2, 590, 64, hexc(INK), FR[800], "c") if False else text(c, "When the VIX crossed 35,", W / 2, 590, 58, hexc(INK), FR[800], "c")
    text(c, "the S&P 500 a year later:", W / 2, 670, 50, hexc(INK), FR[700], "c")
    k = ease_io((t - wtime("twenty-eight", 4)) / 1.2) if t > wtime("twenty-eight", 4) else 0
    text(c, f"+{28 * k:.0f}%", W / 2, 900, 220, hexc(GREEN), FR[800], "c")
    text(c, "on average (RBC study; Cboe: ~28% since 1990)", W / 2, 970, 28, hexc(MUTE), IN[600], "c")
    e = ease_out((t - P[5]) / 0.35)
    if e > 0:
        alpha_layer(c, e)
        y = 1040 + (1 - e) * 30
        c.drawRRect(rrect(110, y, 860, 230, 20), paint(hexc("#FFF1F3"))); c.drawRRect(rrect(110, y, 860, 230, 20), paint(hexc(RED), stroke=5))
        text(c, "THE EXCEPTION · 2008", 150, y + 55, 28, hexc(RED), IN[700], track=4)
        text(c, "Fear spiked, and stocks", 150, y + 118, 46, hexc(INK), FR[800])
        text(c, "kept falling for months.", 150, y + 172, 46, hexc(INK), FR[800])
        pth = skia.Path(); pth.moveTo(760, y + 70)
        for i in range(1, 30): pth.lineTo(760 + i * 6, y + 70 + i * 4 + 8 * math.sin(i))
        c.drawPath(pth, paint(hexc(RED), stroke=5))
        c.restore()
    c.restore()

def scene_bottom(c, t):
    a = overlay(t, P[6] - 0.2, PE[6] + 0.3)
    if a <= 0: return
    alpha_layer(c, a)
    text(c, "THE PATTERN", W / 2, 490, 30, hexc(INK), IN[700], "c", track=6)
    text(c, "Fear is loudest", W / 2, 590, 76, hexc(INK), FR[800], "c")
    text(c, "near the bottom.", W / 2, 680, 72, hexc(RED), FRI[800], "c")
    k = ease_io((t - (P[6] + 0.4)) / 2.4); x0, x1 = 120, 960; n = int(160 * k)
    pp = skia.Path(); pv = skia.Path()
    for i in range(n + 1):
        u = i / 160; x = lerp(x0, x1, u)
        yp = 820 + 260 * math.exp(-((u - 0.55) / 0.18) ** 2) - 120 * u + 12 * math.sin(u * 30)
        yv = 1300 - 220 * math.exp(-((u - 0.55) / 0.06) ** 2) - 8 * math.sin(u * 40)
        (pp.moveTo if i == 0 else pp.lineTo)(x, yp); (pv.moveTo if i == 0 else pv.lineTo)(x, yv)
    if n > 1:
        c.drawPath(pp, paint(hexc(INK), stroke=7)); c.drawPath(pv, paint(hexc(ORANGE), stroke=6))
    text(c, "STOCKS", x0, 800, 24, hexc(INK), IN[700], track=3); text(c, "FEAR (VIX)", x0, 1340, 24, hexc(ORANGE), IN[700], track=3)
    if k > 0.6:
        e = ease_out((k - 0.6) / 0.2); alpha_layer(c, e)
        xm = lerp(x0, x1, 0.55); c.drawLine(xm, 1110, xm, 1060, paint(hexc(RED), stroke=4))
        c.drawCircle(xm, 1080 - 0, 0, paint(hexc(RED)))
        text(c, "← Fear peaks here", xm + 40, 1100, 30, hexc(RED), IN[700], "l"); c.restore()
    text(c, "Illustration, not real data", x1, 1385, 22, hexc(SOFT), IN[500], "r")
    c.restore()

def vote(c, t):
    t0 = P[7] - 0.1
    if t < t0: return
    a = ease_out((t - t0) / 0.45)
    c.drawRect(rect(0, 400, W, 1100), paint(hexc(BG, .97 * a)))
    alpha_layer(c, a)
    text(c, "YOUR CALL", W / 2, 640, 32, hexc(RED), IN[700], "c", track=8)
    text(c, "Is this fear", W / 2, 790, 104, hexc(INK), FR[800], "c")
    text(c, "a warning, or an opportunity?", W / 2, 890, 54, hexc(INK), FRI[800], "c")
    for i, (lab, col, x) in enumerate((("WARNING", RED, 290), ("OPPORTUNITY", GREEN, 790))):
        k = back_out((t - (t0 + 1.0 + i * 0.25)) / 0.4)
        if k <= 0: continue
        pulse = 1 + 0.04 * math.sin((t - t0) * 7 + i * 1.6)
        c.save(); c.translate(x, 1070); c.scale(clamp(k, 0, 1.2) * pulse, clamp(k, 0, 1.2) * pulse)
        c.drawRRect(rrect(-225, -66, 450, 132, 66), paint(hexc(col))); text(c, lab, 0, 18, 44 if len(lab) > 8 else 58, hexc("#FFFFFF"), FR[800], "c", track=2)
        c.restore()
    b = ease_out((t - (t0 + 1.8)) / 0.4); alpha_layer(c, b)
    text(c, "Comment WARNING or OPPORTUNITY", W / 2, 1230, 42, hexc(INK), IN[700], "c"); c.restore()
    c.restore()

def crawl(c, t): pass

def cam(t):
    z = 1.0
    for t0 in P[:7]: z += 0.03 * ease_out((t - t0) / 0.6) * (1 - ease_out((t - (t0 + 1.2)) / 2.0))
    sh = 0.0
    for st in (3.1, P[1] + 2.4, P[5]):
        if st < t < st + 0.35: sh += 12 * math.exp(-(t - st) * 12) * math.sin((t - st) * 90)
    return z, sh

def scene_end(c, t):
    a = ease_out((t - (END + 0.15)) / 0.6)
    alpha_layer(c, a); logo(c, W / 2, 900, 118, line=True, tagline=True); c.restore()
    b = ease_out((t - (END + 0.6)) / 0.5); alpha_layer(c, b)
    pw = tw("Follow " + HANDLE, 44, IN[700]) + 90
    c.drawRRect(rrect(W / 2 - pw / 2, 1110 + (1 - b) * 20, pw, 96, 48), paint(hexc(GREEN)))
    text(c, "Follow " + HANDLE, W / 2, 1172 + (1 - b) * 20, 44, hexc("#FFFFFF"), IN[700], "c")
    text(c, "Save this for the next time fear spikes.", W / 2, 1280, 34, hexc(MUTE), IN[500], "c")
    text(c, "NOT FINANCIAL ADVICE", W / 2, 1390, 24, hexc(SOFT), IN[600], "c", track=4); c.restore()

SRC_TXT = "Sources: Cboe, Reuters, CEO Economy, Bloomberg, RBC via CNBC, Cboe Insights"

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
            scene_gauge(c, t); scene_history(c, t); scene_bottom(c, t)
            c.restore()
            vote(c, t)
            logo(c, 100, 285, 40, center=False)
            tg = "INVESTOR PSYCHOLOGY"; w = tw(tg, 24, IN[700]) + 3 * len(tg) + 40
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
