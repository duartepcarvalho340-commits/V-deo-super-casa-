"""Panic & Profit Reel renderer (Day 1 after the crash (ECG monitor), 2026-11-20). Skia 2D -> raw BGRA frames -> ffmpeg.
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




AMBER = "#D99A00"
RECORD = 7818.93
N = NUM
UP = N["sp"] > 0
FROM_REC = (1 - N["sp_close"] / RECORD) * 100
def sgn(x, d=1): return f"{'+' if x > 0 else '-'}{abs(x):.{d}f}%"
def col(x): return GREEN if x > 0 else RED

def ecg_y(u, beat):
    """heartbeat shape repeated; beat strength 0 = flat"""
    ph = (u * 4) % 1.0
    y = 0
    if 0.40 < ph < 0.46: y = -0.25 * math.sin((ph - 0.40) / 0.06 * math.pi)
    elif 0.48 < ph < 0.52: y = 1.0 * math.sin((ph - 0.48) / 0.04 * math.pi)
    elif 0.52 < ph < 0.56: y = -0.45 * math.sin((ph - 0.52) / 0.04 * math.pi)
    elif 0.62 < ph < 0.74: y = 0.22 * math.sin((ph - 0.62) / 0.12 * math.pi)
    return y * beat

def scene_monitor(c, t):
    a = 1 - sstep(PE[2] + 0.1, PE[2] + 0.5, t)
    if a <= 0: return
    alpha_layer(c, a)
    text(c, "MON, NOV 23 · DAY 1 AFTER THE CRASH", W / 2, 480, 28, hexc(MUTE), IN[700], "c", track=5)
    text(c, "Does the market", W / 2, 580, 78, hexc(INK), FR[800], "c")
    text(c, "still have a pulse?", W / 2, 670, 72, hexc(RED), FRI[800], "c")
    # monitor
    x0, x1, yc = 110, 970, 900
    c.drawRRect(rrect(x0 - 20, yc - 170, x1 - x0 + 40, 340, 24), paint(hexc("#FFFFFF")))
    c.drawRRect(rrect(x0 - 20, yc - 170, x1 - x0 + 40, 340, 24), paint(hexc(INK), stroke=4))
    for gx in range(x0, x1, 43): c.drawLine(gx, yc - 150, gx, yc + 150, paint(hexc("#EFEDE7"), stroke=1.5, cap_round=False))
    head_u = clamp((t - 0.3) / max(1.0, P[2] - 0.6))
    beat = 0.15 if t < P[1] else (1.0 if UP else 0.35)
    lc = INK if t < P[1] else col(N["sp"])
    pth = skia.Path(); n = 240
    for i in range(n + 1):
        u = i / n
        if u > head_u: break
        y = yc - 120 * ecg_y(u, beat if u > head_u - 0.25 else 0.15 if t < P[1] else beat)
        (pth.moveTo if i == 0 else pth.lineTo)(lerp(x0, x1, u), y)
    c.drawPath(pth, paint(hexc(lc), stroke=6))
    hx = lerp(x0, x1, head_u); c.drawCircle(hx, yc - 120 * ecg_y(head_u, beat), 10, paint(hexc(lc)))
    # readings
    rows = [("S&P 500", sgn(N["sp"]), N["sp"]), ("NASDAQ", sgn(N["ndq"]), N["ndq"]), ("DOW", f"{'+' if N['dow_pts'] > 0 else '-'}{abs(int(round(N['dow_pts']))):,} pts", N["dow_pts"])]
    for i, (nm, val, x) in enumerate(rows):
        tt = wtime(["500", "Nasdaq", "Dow"][i], 1) - 0.1
        if t < tt: continue
        s = clamp(back_out((t - tt) / 0.4), 0, 1.15); cx = 230 + i * 310
        c.save(); c.translate(cx, 1170); c.scale(s, s)
        c.drawRRect(rrect(-145, -70, 290, 140, 20), paint(hexc("#FFFFFF"))); c.drawRRect(rrect(-145, -70, 290, 140, 20), paint(hexc(col(x)), stroke=5))
        text(c, nm, 0, -20, 26, hexc(MUTE), IN[700], "c", track=3); text(c, val, 0, 40, 46 if len(val) < 8 else 38, hexc(col(x)), FR[800], "c"); c.restore()
    # verdict stamp
    if t > P[2] - 0.1:
        k = clamp(lerp(2.0, 1, ease_out((t - (P[2] - 0.1)) / 0.3)), 0.8, 2)
        word = "RELIEF RALLY" if UP else "NO RELIEF"; cc = GREEN if UP else RED
        c.save(); c.translate(W / 2, 900); c.rotate(-6); c.scale(k, k)
        w = tw(word, 92, FR[800]) + 80
        c.drawRRect(rrect(-w / 2, -80, w, 140, 20), paint(hexc("#FFFFFF", .92))); c.drawRRect(rrect(-w / 2, -80, w, 140, 20), paint(hexc(cc), stroke=9))
        text(c, word, 0, 30, 92, hexc(cc), FR[800], "c"); c.restore()
        e = ease_out((t - (P[2] + 1.4)) / 0.4)
        if e > 0:
            alpha_layer(c, e)
            sub = ("But one green day doesn't end a correction" if FROM_REC >= 10 else "Back above the correction line, for now") if UP else "8th straight loss for the S&P 500"
            text(c, sub, W / 2, 1310, 34, hexc(INK), IN[700], "c"); c.restore()
    c.restore()

def scene_nvda(c, t):
    a = overlay(t, P[3] - 0.2, PE[4] + 0.3)
    if a <= 0: return
    alpha_layer(c, a)
    text(c, "THE AI BELLWETHER", W / 2, 490, 30, hexc(MUTE), IN[700], "c", track=6)
    e = back_out((t - P[3]) / 0.45); s = clamp(e, 0, 1.12)
    c.save(); c.translate(W / 2, 680); c.scale(s, s)
    c.drawRRect(rrect(-400, -120, 800, 240, 30), paint(hexc("#FFFFFF"))); c.drawRRect(rrect(-400, -120, 800, 240, 30), paint(hexc(col(N["nvda"])), stroke=6))
    text(c, "NVIDIA · MONDAY", 0, -50, 30, hexc(MUTE), IN[700], "c", track=4)
    text(c, sgn(N["nvda"]), 0, 80, 140, hexc(col(N["nvda"])), FR[800], "c"); c.restore()
    text(c, "after Friday's -14% on an SEC report", W / 2, 860, 32, hexc(MUTE), IN[600], "c")
    # distance from record bar
    if t > P[4] - 0.2:
        f = ease_out((t - (P[4] - 0.2)) / 0.4); alpha_layer(c, f)
        text(c, "S&P 500 vs. OCT RECORD", W / 2, 965, 30, hexc(INK), IN[700], "c", track=4)
        k = ease_io((t - P[4]) / 1.4); x0, x1 = 140, 940
        c.drawRRect(rrect(x0, 1030, x1 - x0, 50, 25), paint(hexc(BORDER)))
        fill = (x1 - x0) * (1 - FROM_REC / 25 * k)
        c.drawRRect(rrect(x0, 1030, fill, 50, 25), paint(hexc(INK)))
        c.drawLine(x1, 1010, x1, 1100, paint(hexc(GREEN), stroke=5)); text(c, "RECORD", x1, 1130, 24, hexc(GREEN), IN[700], "c", track=2)
        xc = x0 + (x1 - x0) * (1 - 10 / 25); c.drawLine(xc, 1010, xc, 1100, paint(hexc(RED), stroke=3))
        text(c, "-10% = CORRECTION", xc, 1130, 22, hexc(RED), IN[700], "c", track=1)
        text(c, f"-{FROM_REC * k:.1f}%", x0 + fill, 1215, 48, hexc(RED if FROM_REC >= 10 else AMBER), FR[800], "c")
        c.restore()
    c.restore()

def scene_next(c, t):
    a = overlay(t, P[5] - 0.2, PE[6] + 0.3)
    if a <= 0: return
    alpha_layer(c, a)
    text(c, "NEXT UP", W / 2, 490, 30, hexc(RED), IN[700], "c", track=8)
    cards = [("TUE", "Dell earnings", "Is AI hardware demand holding?", wtime("Dell's", 5)), ("WED", "PCE inflation", "The Fed's favorite gauge, 8:30 ET", wtime("Wednesday's", 5))]
    for i, (d, ttl, sub, tt) in enumerate(cards):
        if t < tt - 0.1: continue
        s = clamp(back_out((t - tt + 0.1) / 0.4), 0, 1.12); y = 650 + i * 230
        c.save(); c.translate(W / 2, y); c.scale(s, s)
        c.drawRRect(rrect(-420, -90, 840, 180, 22), paint(hexc("#FFFFFF"))); c.drawRRect(rrect(-420, -90, 840, 180, 22), paint(hexc(INK), stroke=4))
        c.drawRRect(rrect(-400, -70, 140, 140, 18), paint(hexc(RED)))
        text(c, d, -330, 18, 50, hexc("#FFFFFF"), FR[800], "c")
        text(c, ttl, -230, -8, 48, hexc(INK), FR[800]); text(c, sub, -230, 44, 28, hexc(MUTE), IN[600])
        c.restore()
    e = ease_out((t - P[6]) / 0.4)
    if e > 0:
        alpha_layer(c, e)
        c.drawRect(rect(0, 420, W, 960), paint(hexc(BG)))
        text(c, "One day", W / 2, 760, 130, hexc(INK), FR[800], "c")
        text(c, "is not a trend.", W / 2, 890, 100, hexc(INK), FRI[800], "c")
        for i, (lab, cc, x) in enumerate((("DIRECTION", GREEN, 330), ("NOISE", RED, 750))):
            c.drawRRect(rrect(x - 180, 990, 360, 110, 55), paint(hexc(cc) if i == 0 else hexc("#FFFFFF")))
            if i: c.drawRRect(rrect(x - 180, 990, 360, 110, 55), paint(hexc(RED), stroke=5))
            text(c, lab, x, 1063, 50, hexc("#FFFFFF" if i == 0 else RED), FR[800], "c")
        c.restore()
    c.restore()

def vote(c, t):
    t0 = P[7] - 0.1
    if t < t0: return
    a = ease_out((t - t0) / 0.45)
    c.drawRect(rect(0, 400, W, 1100), paint(hexc(BG, .97 * a)))
    alpha_layer(c, a)
    text(c, "YOUR CALL", W / 2, 640, 32, hexc(RED), IN[700], "c", track=8)
    text(c, "Is the worst", W / 2, 790, 110, hexc(INK), FR[800], "c")
    text(c, "behind us, or still ahead?", W / 2, 890, 60, hexc(INK), FRI[800], "c")
    for i, (lab, cc, x) in enumerate((("BEHIND", GREEN, 290), ("AHEAD", RED, 790))):
        k = back_out((t - (t0 + 1.0 + i * 0.25)) / 0.4)
        if k <= 0: continue
        pulse = 1 + 0.04 * math.sin((t - t0) * 7 + i * 1.6)
        c.save(); c.translate(x, 1070); c.scale(clamp(k, 0, 1.2) * pulse, clamp(k, 0, 1.2) * pulse)
        c.drawRRect(rrect(-220, -66, 440, 132, 66), paint(hexc(cc))); text(c, lab, 0, 20, 60, hexc("#FFFFFF"), FR[800], "c", track=3)
        c.restore()
    b = ease_out((t - (t0 + 1.8)) / 0.4); alpha_layer(c, b)
    text(c, "Comment BEHIND or AHEAD", W / 2, 1230, 44, hexc(INK), IN[700], "c"); c.restore()
    c.restore()

def cam(t):
    z = 1.0
    for t0 in P[:7]: z += 0.03 * ease_out((t - t0) / 0.6) * (1 - ease_out((t - (t0 + 1.2)) / 2.0))
    sh = 0.0
    for st in (P[2] - 0.05, P[3] + 0.1):
        if st < t < st + 0.35: sh += 12 * math.exp(-(t - st) * 12) * math.sin((t - st) * 90)
    return z, sh

def scene_end(c, t):
    a = ease_out((t - (END + 0.15)) / 0.6)
    alpha_layer(c, a); logo(c, W / 2, 900, 118, line=True, tagline=True); c.restore()
    b = ease_out((t - (END + 0.6)) / 0.5); alpha_layer(c, b)
    pw = tw("Follow " + HANDLE, 44, IN[700]) + 90
    c.drawRRect(rrect(W / 2 - pw / 2, 1110 + (1 - b) * 20, pw, 96, 48), paint(hexc(GREEN)))
    text(c, "Follow " + HANDLE, W / 2, 1172 + (1 - b) * 20, 44, hexc("#FFFFFF"), IN[700], "c")
    text(c, "Daily market close, explained for long-term investors.", W / 2, 1280, 30, hexc(MUTE), IN[500], "c")
    text(c, "NOT FINANCIAL ADVICE", W / 2, 1390, 24, hexc(SOFT), IN[600], "c", track=4); c.restore()

SRC_TXT = "Sources: AP, CNBC, Reuters, Yahoo Finance; record close 7,818.93 (Oct 6)"

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
            scene_monitor(c, t); scene_nvda(c, t); scene_next(c, t)
            c.restore()
            vote(c, t)
            logo(c, 100, 285, 40, center=False)
            tg = "MARKET CLOSE"; w = tw(tg, 24, IN[700]) + 3 * len(tg) + 40
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
