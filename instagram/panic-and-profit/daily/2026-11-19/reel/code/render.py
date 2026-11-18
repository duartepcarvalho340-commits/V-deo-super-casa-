"""Panic & Profit Reel renderer (vertical 1080x1920). Skia 2D -> raw BGRA frames -> ffmpeg.
Concept: "the vertical feed" - each fact is a card-page; the camera scrolls down the feed like a thumb,
and the story turns into a seesaw (rates vs. value) and discounting bars.
Usage: python3 code/render.py --scale 1 --fps 60 --out exports/reel.mp4
       python3 code/render.py --scale 0.5 --out previews/s.png --still 1 5 8"""
import argparse, math, os, subprocess, sys
import numpy as np, skia
sys.path.insert(0, os.path.dirname(__file__))
from timing import FPS, DURATION, BOUNDS, EVENTS as EV, HANDLE

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

# ---------------- scenes (local coords 0..W, 0..H) ----------------
def scene_hook(c, t):
    k = back_out((t - EV["card_in"]) / 0.55); x = lerp(W + 40, 100, clamp(k, 0, 1.2)) if t > EV["card_in"] else W + 40
    cw, ch, cy = 880, 168, 560
    c.drawRect(rect(x + 8, cy + 8, cw, ch), paint(hexc("#000000", .06)))
    c.drawRect(rect(x, cy, cw, ch), paint(hexc("#FFFFFF"))); c.drawRect(rect(x, cy, cw, ch), paint(hexc(INK), stroke=4, cap_round=False))
    text(c, "BREAKING · FED", x + 34, cy + 52, 26, hexc(RED), IN[700], track=3)
    text(c, "DEC 9: ANOTHER HIKE?", x + 34, cy + 128, 54, hexc(INK), FR[800])
    c.drawRect(rect(x + cw - 128, cy + 42, 92, 92), paint(hexc(RED))); tri(c, x + cw - 82, cy + 88, 46, True, hexc("#FFFFFF"))
    for key, s, yb, col, tf in (("line1", "The Fed is", 940, INK, FR[800]), ("line2", "about to hike.", 1075, INK, FR[800]), ("line3", "Again.", 1230, RED, FRI[800])):
        a = ease_out((t - EV[key]) / 0.45)
        if a <= 0: continue
        alpha_layer(c, a); text(c, s, 100, yb + (1 - a) * 40, 132, hexc(col), tf); c.restore()
    a = ease_out((t - 2.2) / 0.5)
    alpha_layer(c, a); text(c, "What it means for your stocks, in 30 seconds.", 100, 1340, 36, hexc(MUTE), IN[500]); c.restore()

TL = [("tl_1", "JUL 2023", "The Fed's last hike", "before this new cycle", INK, False),
      ("tl_2", "SEP 16, 2026", "First hike since 2023", "+0.25 pt  →  3.75%–4.00%", RED, True),
      ("tl_3", "OCT 28", "Hold, but 2 voted to hike", "Cook and Hammack dissented (10–2)", INK, False),
      ("tl_4", "NOV 10", "October CPI came in hot", "+0.4% m/m · core +0.3% vs 0.2% expected", RED, True)]
def scene_timeline(c, t):
    a = ease_out((t - 3.45) / 0.4); alpha_layer(c, a)
    text(c, "How we got here", 100, 430, 72, hexc(INK), FR[700]); c.restore()
    x, y0, y1 = 150, 560, 1430; ys = [600, 830, 1060, 1290]
    prog = sstep(EV["tl_1"] - 0.1, EV["tl_4"] + 0.3, t)
    c.drawLine(x, y0, x, y1, paint(hexc(BORDER), stroke=6))
    c.drawLine(x, y0, x, lerp(y0, y1, prog), paint(hexc(INK), stroke=6))
    for (key, date, title, sub, col, up), y in zip(TL, ys):
        k = back_out((t - EV[key]) / 0.45)
        if t < EV[key]: c.drawCircle(x, y, 13, paint(hexc(BORDER))); continue
        c.drawCircle(x, y, 22 * clamp(k, 0, 1.3), paint(hexc(col))); c.drawCircle(x, y, 8 * clamp(k, 0, 1), paint(hexc(BG)))
        a = ease_out((t - EV[key]) / 0.4); alpha_layer(c, a); dx = (1 - a) * 40
        text(c, date, x + 60 + dx, y - 34, 26, hexc(col if col == RED else MUTE), IN[700], track=2.5)
        text(c, title, x + 60 + dx, y + 22, 50, hexc(INK), FR[700])
        text(c, sub, x + 60 + dx, y + 70, 30, hexc(MUTE), IN[500])
        if up: tri(c, W - 90 + dx, y + 6, 34, True, hexc(RED))
        c.restore()

def scene_odds(c, t):
    a = ease_out((t - 9.85) / 0.4); alpha_layer(c, a)
    text(c, "What markets are pricing", W / 2, 430, 64, hexc(INK), FR[700], "c")
    text(c, "Odds of a Fed hike on Dec 9", W / 2, 505, 36, hexc(MUTE), IN[500], "c"); c.restore()
    cx, cy, r = W / 2, 960, 300; k = ease_io((t - EV["ring_start"]) / (EV["ring_end"] - EV["ring_start"]))
    c.drawCircle(cx, cy, r, paint(hexc(BORDER), stroke=48, cap_round=False))
    if k > 0:
        arc = skia.Path(); arc.addArc(skia.Rect.MakeLTRB(cx - r, cy - r, cx + r, cy + r), -90, 324 * k)
        c.drawPath(arc, paint(hexc(RED), stroke=48, cap_round=False))
    v = int(round(90 * k)); s = f"~{v}%" if k > 0.98 else f"{v}%"
    text(c, s, cx, cy + 62, 180, hexc(INK), FR[800], "c")
    a = ease_out((t - 12.6) / 0.5); alpha_layer(c, a)
    text(c, "Roughly 9 in 10", cx, cy + 420, 56, hexc(RED), FR[700], "c")
    text(c, "Next decision: Wednesday, Dec 9", cx, cy + 480, 34, hexc(MUTE), IN[500], "c"); c.restore()

def box(c, cx, cy, w, h, lines, col, arrow_up):
    c.drawRect(rect(cx - w / 2 + 6, cy - h / 2 + 6, w, h), paint(hexc("#000000", .06)))
    c.drawRect(rect(cx - w / 2, cy - h / 2, w, h), paint(hexc("#FFFFFF")))
    c.drawRect(rect(cx - w / 2, cy - h / 2, w, h), paint(hexc(INK), stroke=4, cap_round=False))
    n = len(lines); yy = cy - (n - 1) * 24 + 14
    for i, s in enumerate(lines): text(c, s, cx, yy + i * 48 - 18, 40, hexc(col), FR[800], "c")
    c.drawRect(rect(cx - 34, cy + h / 2 - 2, 68, 56), paint(hexc(RED))); tri(c, cx, cy + h / 2 + 26, 30, arrow_up, hexc("#FFFFFF"))
def scene_seesaw(c, t):
    a = ease_out((t - 14.3) / 0.4); alpha_layer(c, a)
    text(c, "Why stocks care", W / 2, 430, 72, hexc(INK), FR[700], "c")
    text(c, "Rates and valuations sit on a seesaw.", W / 2, 505, 36, hexc(MUTE), IN[500], "c"); c.restore()
    px, py = W / 2, 1180; ang = 13 * ease_io((t - EV["beam_tilt"]) / (EV["beam_tilt_end"] - EV["beam_tilt"]))
    pv = skia.Path(); pv.moveTo(px, py); pv.lineTo(px + 90, py + 150); pv.lineTo(px - 90, py + 150); pv.close(); c.drawPath(pv, paint(hexc(INK)))
    c.drawLine(120, py + 152, W - 120, py + 152, paint(hexc(INK), stroke=5))
    L = 430; th = math.radians(ang)
    ends = [(px + (-L) * math.cos(th), py + (-L) * math.sin(th)), (px + L * math.cos(th), py + L * math.sin(th))]
    c.save(); c.translate(px, py); c.rotate(ang); c.drawRRect(rrect(-L - 30, -14, 2 * L + 60, 28, 8), paint(hexc(INK))); c.restore()
    c.drawCircle(px, py, 16, paint(hexc(GREY)))
    ea = ease_out((t - 14.9) / 0.4); alpha_layer(c, ea)
    box(c, ends[0][0] + 90, ends[0][1] - 150, 280, 150, ["RATES"], RED, True)
    box(c, ends[1][0] - 120, ends[1][1] - 175, 330, 190, ["VALUE OF", "FUTURE", "PROFITS"], INK, False)
    c.restore()
    a = ease_out((t - 16.9) / 0.4); alpha_layer(c, a)
    text(c, "Rates up  →  what future profits are", W / 2, 1450, 36, hexc(INK), IN[600], "c")
    text(c, "worth today goes down.", W / 2, 1498, 36, hexc(INK), IN[600], "c"); c.restore()

def scene_bars(c, t):
    a = ease_out((t - 18.75) / 0.4); alpha_layer(c, a)
    text(c, "$100, ten years from now", W / 2, 430, 66, hexc(INK), FR[700], "c")
    text(c, "What it's worth today:", W / 2, 505, 36, hexc(MUTE), IN[500], "c"); c.restore()
    base, full, bw = 1320, 640, 250
    k3 = ease_io((t - EV["bar3_start"]) / (EV["bar3_end"] - EV["bar3_start"])); k5 = ease_io((t - EV["bar5_start"]) / (EV["bar5_end"] - EV["bar5_start"]))
    vals = [(310, "at 3%", lerp(100, 74.41, k3), INK, k3), (770, "at 5%", lerp(100, 61.39, k5), RED, k5)]
    gin = ease_out((t - EV["bars_in"]) / 0.5)
    for x, lab, v, col, k in vals:
        h = full * v / 100 * gin
        c.drawRect(rect(x - bw / 2, base - full * gin, bw, full * gin), paint(hexc(BORDER), stroke=3, cap_round=False))
        c.drawRect(rect(x - bw / 2, base - h, bw, h), paint(hexc(col if k > 0 else "#CFCBC2")))
        if gin > 0.3:
            text(c, f"${v:.0f}", x, base - h - 26, 76, hexc(col if k > 0 else INK), FR[800], "c")
            text(c, lab, x, base + 64, 44, hexc(INK), FR[700], "c")
    c.drawLine(120, base, W - 120, base, paint(hexc(INK), stroke=5))
    a = ease_out((t - 24.2) / 0.4); alpha_layer(c, a)
    text(c, "Same $100. Higher rate, lower value.", W / 2, 1470, 38, hexc(RED), IN[600], "c"); c.restore()

def scene_duration(c, t):
    a = ease_out((t - 25.15) / 0.4); alpha_layer(c, a)
    text(c, "The further out the profits,", W / 2, 430, 58, hexc(INK), FR[700], "c")
    text(c, "the bigger the hit.", W / 2, 505, 58, hexc(RED), FRI[700], "c"); c.restore()
    k = ease_io((t - EV["dur_start"]) / (EV["dur_end"] - EV["dur_start"]))
    base, x0, x1 = 1250, 130, 950; n = 10; step = (x1 - x0) / n; bw = step * 0.62; full = 560
    gin = ease_out((t - 25.2) / 0.5)
    for i in range(1, n + 1):
        x = x0 + step * (i - 0.5); h3 = full / 1.03 ** i * gin; h5 = full / 1.05 ** i * gin; h = lerp(h3, h5, k)
        c.drawRect(rect(x - bw / 2, base - h3, bw, h3 - h), paint(hexc(RED, .85)))
        c.drawRect(rect(x - bw / 2, base - h, bw, h), paint(hexc(INK)))
        if i in (1, 10): text(c, f"Yr {i}", x, base + 48, 30, hexc(MUTE), IN[600], "c")
    c.drawLine(110, base, W - 110, base, paint(hexc(INK), stroke=5))
    a = ease_out((t - 26.4) / 0.4); alpha_layer(c, a)
    c.drawRect(rect(150, 1350, 34, 34), paint(hexc(RED, .85)))
    text(c, "value lost when rates go from 3% to 5%", 200, 1378, 32, hexc(INK), IN[500])
    text(c, "Long-duration growth stocks feel it first.", W / 2, 1470, 38, hexc(INK), IN[600], "c"); c.restore()

def scene_end(c, t):
    a = ease_out((t - EV["end_logo"]) / 0.6)
    alpha_layer(c, a); logo(c, W / 2, 900, 118, line=True, tagline=True); c.restore()
    b = ease_out((t - 28.7) / 0.5); alpha_layer(c, b)
    pw = tw("Follow " + HANDLE, 44, IN[700]) + 90
    c.drawRRect(rrect(W / 2 - pw / 2, 1110 + (1 - b) * 20, pw, 96, 48), paint(hexc(GREEN)))
    text(c, "Follow " + HANDLE, W / 2, 1172 + (1 - b) * 20, 44, hexc("#FFFFFF"), IN[700], "c")
    text(c, "Save this for the next Fed day.", W / 2, 1280, 34, hexc(MUTE), IN[500], "c")
    text(c, "NOT FINANCIAL ADVICE", W / 2, 1390, 24, hexc(SOFT), IN[600], "c", track=4); c.restore()

SCENES = [scene_hook, scene_timeline, scene_odds, scene_seesaw, scene_bars, scene_duration, scene_end]
SOURCES = ["", "Sources: Federal Reserve, BLS, CNN, CNBC, Schwab", "Sources: CME FedWatch via CNBC, Kalshi · mid-Nov 2026",
           "", "Illustrative math: $100 ÷ (1 + r)¹⁰", "Illustrative math: $100 a year, discounted at 3% vs 5%", ""]

class Renderer:
    def __init__(self, scale):
        self.scale = scale; self.surf = skia.Surface(int(W * scale), int(H * scale))
        keys = [(0, 0.0)]
        for i, b in enumerate(BOUNDS[1:], 1): keys += [(b - 0.22, (i - 1) * H), (b + 0.28, i * H)]
        keys.append((DURATION, (len(BOUNDS) - 1) * H)); self.camy = monotone(keys)
    def draw(self, t):
        c = self.surf.getCanvas(); c.save(); c.scale(self.scale, self.scale); background(c)
        cy = self.camy(t); si = int(np.searchsorted(BOUNDS, t, side="right") - 1)
        for i, fn in enumerate(SCENES):
            off = i * H - cy
            if -H < off < H: c.save(); c.translate(0, off); fn(c, t); c.restore()
        # fixed header + source footer (screen space; inside Reels safe area)
        ha = 1 - sstep(27.6, 28.0, t)
        if ha > 0:
            alpha_layer(c, ha); logo(c, 100, 285, 40, center=False)
            tg = "FED WATCH"; w = tw(tg, 24, IN[700]) + 3 * 8 + 40
            c.drawRRect(rrect(W - 100 - w, 250, w, 50, 25), paint(hexc(RED)))
            text(c, tg, W - 100 - w / 2, 284, 24, hexc("#FFFFFF"), IN[700], "c", track=3); c.restore()
        src = SOURCES[min(si, len(SOURCES) - 1)]
        if src:
            sa = sstep(BOUNDS[si] + 0.3, BOUNDS[si] + 0.7, t) * (1 - sstep(BOUNDS[si + 1] - 0.3, BOUNDS[si + 1], t) if si + 1 < len(BOUNDS) else 1)
            alpha_layer(c, sa); text(c, src, W / 2, 1535, 24, hexc(SOFT), IN[500], "c"); c.restore()
        c.restore(); return self.surf.makeImageSnapshot().toarray()
    def frame(self, t, fps):
        dt = 1 / fps; sp = abs(self.camy(t + dt / 2) - self.camy(t - dt / 2))
        n = 1 if sp < 6 else int(min(12, 3 + sp / 8))
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
