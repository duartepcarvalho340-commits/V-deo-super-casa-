"""Panic & Profit Reel renderer (Nvidia, 2026-11-18) (vertical 1080x1920). Skia 2D -> raw BGRA frames -> ffmpeg.
Concept: "split screen" - the frame is cut into PANIC (red tint, top) and PROFIT (green tint, bottom);
the divider slides as the story moves from the CEO exit to the record quarter, then dissolves into the lesson.
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


# ---------------- divider (screen y of the PANIC/PROFIT split) ----------------
DIV = monotone([(0, 960), (4.45, 960), (5.05, 1460), (11.6, 1460), (12.15, 470), (22.3, 470), (22.85, 960), (DURATION, 960)])
TINT = lambda t: 1 - sstep(22.35, 22.9, t)   # tints fade out for the lesson

def card(c, x, y, w, h, tag, title, col, up, k):
    if k <= 0: return
    xx = lerp(W + 30, x, clamp(k, 0, 1.15))
    c.drawRect(rect(xx + 8, y + 8, w, h), paint(hexc("#000000", .06)))
    c.drawRect(rect(xx, y, w, h), paint(hexc("#FFFFFF"))); c.drawRect(rect(xx, y, w, h), paint(hexc(INK), stroke=4, cap_round=False))
    text(c, tag, xx + 30, y + 46, 24, hexc(col), IN[700], track=3)
    text(c, title, xx + 30, y + h - 34, 44 if tw(title, 46, FR[800]) > w - 160 else 46, hexc(INK), FR[800])
    c.drawRect(rect(xx + w - 104, y + h / 2 - 38, 76, 76), paint(hexc(col))); tri(c, xx + w - 66, y + h / 2, 38, up, hexc("#FFFFFF"))

def scene_split(c, t):
    d = DIV(t); ti = TINT(t)
    if ti > 0:
        c.drawRect(rect(0, 0, W, d), paint(hexc("#F7E3E6", .75 * ti))); c.drawRect(rect(0, d, W, H - d), paint(hexc("#E2F0E7", .75 * ti)))
        c.drawLine(0, d, W, d, paint(hexc(INK, ti), stroke=5, cap_round=False))
        # side labels
        alpha_layer(c, ti * (1 - sstep(22.0, 22.4, t)))
        if d > 520: text(c, "PANIC", 100, d - 34, 30, hexc(RED), IN[700], track=6)
        if d < 1400: text(c, "PROFIT", 100, d + 64, 30, hexc(GREEN), IN[700], track=6)
        c.restore()
    # ---- hook ----
    if t < 5.2:
        a = 1 - sstep(4.45, 4.85, t)
        alpha_layer(c, a)
        k = ease_out((t - EV["ceo_out"]) / 0.45)
        if k > 0: alpha_layer(c, k); text(c, "CEO out.", 100, 760 + (1 - k) * 40, 150, hexc(RED), FRI[800]); c.restore()
        k = back_out((t - EV["chip"]) / 0.4)
        if t > EV["chip"]:
            cw = tw("5 DAYS LATER", 28, IN[700]) + 3 * 11 + 56; s = clamp(k, 0, 1.2)
            c.save(); c.translate(W / 2, 960); c.scale(s, s)
            c.drawRRect(rrect(-cw / 2, -34, cw, 68, 34), paint(hexc(INK))); text(c, "5 DAYS LATER", 0, 10, 28, hexc("#FFFFFF"), IN[700], "c", track=3); c.restore()
        k = ease_out((t - EV["record"]) / 0.45)
        if k > 0: alpha_layer(c, k); text(c, "Record", 100, 1210 + (1 - k) * 40, 150, hexc(GREEN), FR[800]); text(c, "quarter.", 100, 1360 + (1 - k) * 40, 150, hexc(GREEN), FR[800]); c.restore()
        c.restore()
    # ---- panic (top) ----
    if 4.6 < t < 12.4:
        a = sstep(4.7, 5.1, t) * (1 - sstep(11.6, 12.0, t)); alpha_layer(c, a)
        text(c, "Nov 12, 2026", 100, 430, 64, hexc(INK), FR[700])
        card(c, 100, 500, 880, 170, "BREAKING · NVIDIA", "JENSEN HUANG STEPS DOWN", RED, False, back_out((t - EV["card1"]) / 0.55))
        card(c, 100, 720, 880, 170, "SAME DAY · INTERIM CEO", "CFO COLETTE KRESS", INK, True, back_out((t - EV["card2"]) / 0.55))
        k = ease_out((t - EV["ticker"]) / 0.4)
        if k > 0:
            alpha_layer(c, k)
            text(c, "NVDA", 100, 1080, 56, hexc(INK), IN[700], track=4)
            text(c, "−4.3%", 100, 1290 + (1 - k) * 30, 200, hexc(RED), FR[800])
            text(c, "close on Nov 12", 100, 1360, 34, hexc(MUTE), IN[500]); c.restore()
        c.restore()
    # ---- profit (bottom) ----
    if 11.9 < t < 22.9:
        a = sstep(12.1, 12.5, t) * (1 - sstep(22.2, 22.6, t)); alpha_layer(c, a)
        text(c, "Nov 17: her first earnings", 100, 400, 50, hexc(INK), FR[700])
        k = ease_io((t - EV["rev_start"]) / (EV["rev_end"] - EV["rev_start"]))
        text(c, "Q3 REVENUE", 100, 580, 28, hexc(GREEN), IN[700], track=4)
        text(c, f"${115.8 * k:.1f}B", 100, 760, 190, hexc(INK), FR[800])
        k2 = back_out((t - EV["yoy"]) / 0.4)
        if t > EV["yoy"]:
            s = clamp(k2, 0, 1.2); c.save(); c.translate(100, 800); c.scale(s, s)
            c.drawRRect(rrect(0, 0, 330, 70, 35), paint(hexc(GREEN))); text(c, "+103% y/y", 165, 47, 36, hexc("#FFFFFF"), IN[700], "c"); c.restore()
        # bars: expected vs actual vs Q4 guide
        base, x0, bw, sc = 1395, 130, 230, 3.1
        for key, x, val, lab, col in (("bar_exp", x0, 108.9, "Expected", GREY), ("bar_act", x0 + 290, 115.8, "Actual", GREEN), ("guide", x0 + 580, 130.0, "Q4 guide", INK)):
            g = ease_out((t - EV[key]) / 0.6)
            if g <= 0: continue
            h = (val - 60) * sc * 1.6 * g
            c.drawRect(rect(x, base - h, bw, h), paint(hexc(col)))
            text(c, ("~" if key == "bar_exp" else "") + f"${val:.1f}B" if key != "guide" else "$130B", x + bw / 2, base - h - 20, 44, hexc(col if col != GREY else MUTE), FR[800], "c")
            text(c, lab, x + bw / 2, base + 46, 32, hexc(INK), IN[600], "c")
        c.drawLine(110, base, W - 110, base, paint(hexc(INK), stroke=5))
        c.restore()
    # ---- lesson ----
    if t > 22.5:
        a = ease_out((t - EV["lesson_title"]) / 0.45) * (1 - sstep(29.35, 29.7, t)); alpha_layer(c, a)
        text(c, "Key-person risk", W / 2, 430, 74, hexc(INK), FR[800], "c")
        text(c, "is not business risk.", W / 2, 515, 66, hexc(RED), FRI[700], "c")
        cols = (("col_left", 100, "THE BUSINESS", GREEN, ["Revenue +103% y/y", "Beat estimates", "Q4 guide: $130B"], "✓"),
                ("col_right", 560, "STILL OPEN", RED, ["Permanent CEO", "Who runs strategy", "Q4 guide: no China"], "?"))
        for key, x, hd, col, items, mark in cols:
            k = ease_out((t - EV[key]) / 0.45)
            if k <= 0: continue
            alpha_layer(c, k); y = 620 + (1 - k) * 30
            c.drawRect(rect(x, y, 420, 560), paint(hexc("#FFFFFF"))); c.drawRect(rect(x, y, 420, 560), paint(hexc(INK), stroke=4, cap_round=False))
            c.drawRect(rect(x, y, 420, 84), paint(hexc(col))); text(c, hd, x + 210, y + 54, 30, hexc("#FFFFFF"), IN[700], "c", track=3)
            for i, it in enumerate(items):
                yy = y + 190 + i * 140
                c.drawCircle(x + 52, yy - 14, 24, paint(hexc(col)))
                text(c, mark, x + 52, yy - 2, 30, hexc("#FFFFFF"), IN[700], "c")
                words = it.split(": ") if ": " in it else [it]
                if len(words) == 2: text(c, words[0] + ":", x + 92, yy - 22, 32, hexc(INK), IN[600]); text(c, words[1], x + 92, yy + 20, 32, hexc(INK), IN[600])
                elif tw(it, 32, IN[600]) > 300:
                    p = it.split(" "); m = len(p) // 2
                    text(c, " ".join(p[:m]), x + 92, yy - 22, 32, hexc(INK), IN[600]); text(c, " ".join(p[m:]), x + 92, yy + 20, 32, hexc(INK), IN[600])
                else: text(c, it, x + 92, yy, 32, hexc(INK), IN[600])
            c.restore()
        k = ease_out((t - EV["held"]) / 0.45)
        if k > 0:
            alpha_layer(c, k)
            text(c, "The numbers held.", W / 2, 1300, 52, hexc(GREEN), FR[800], "c")
            text(c, "Who leads next is the real test.", W / 2, 1370, 40, hexc(INK), FR[700], "c"); c.restore()
        c.restore()

def scene_end(c, t):
    a = ease_out((t - EV["end_logo"]) / 0.6)
    alpha_layer(c, a); logo(c, W / 2, 900, 118, line=True, tagline=True); c.restore()
    b = ease_out((t - (EV["end_logo"] + 0.5)) / 0.5); alpha_layer(c, b)
    pw = tw("Follow " + HANDLE, 44, IN[700]) + 90
    c.drawRRect(rrect(W / 2 - pw / 2, 1110 + (1 - b) * 20, pw, 96, 48), paint(hexc(GREEN)))
    text(c, "Follow " + HANDLE, W / 2, 1172 + (1 - b) * 20, 44, hexc("#FFFFFF"), IN[700], "c")
    text(c, "Save this for the next headline panic.", W / 2, 1280, 34, hexc(MUTE), IN[500], "c")
    text(c, "NOT FINANCIAL ADVICE", W / 2, 1390, 24, hexc(SOFT), IN[600], "c", track=4); c.restore()

SOURCES = ["", "Sources: Nvidia 8-K (SEC), CNBC, TechCrunch, Al Jazeera", "Sources: Nvidia Q3 FY2027 results, CNBC, Investing.com, IndMoney",
           "Sources: Nvidia, CNN, CNBC", ""]

class Renderer:
    def __init__(self, scale):
        self.scale = scale; self.surf = skia.Surface(int(W * scale), int(H * scale))
    def draw(self, t):
        c = self.surf.getCanvas(); c.save(); c.scale(self.scale, self.scale); background(c)
        si = int(np.searchsorted(BOUNDS, t, side="right") - 1)
        if t < BOUNDS[-1] + 0.3: scene_split(c, t)
        if t > BOUNDS[-1]: scene_end(c, t)
        ha = 1 - sstep(29.2, 29.6, t)
        if ha > 0:
            alpha_layer(c, ha); logo(c, 100, 285, 40, center=False)
            tg = "EARNINGS"; w = tw(tg, 24, IN[700]) + 3 * 7 + 40
            c.drawRRect(rrect(W - 100 - w, 250, w, 50, 25), paint(hexc(INK)))
            text(c, tg, W - 100 - w / 2, 284, 24, hexc("#FFFFFF"), IN[700], "c", track=3); c.restore()
        src = SOURCES[min(si, len(SOURCES) - 1)]
        if src:
            sa = sstep(BOUNDS[si] + 0.3, BOUNDS[si] + 0.7, t) * (1 - sstep(BOUNDS[si + 1] - 0.3, BOUNDS[si + 1], t))
            alpha_layer(c, sa); text(c, src, W / 2, 1535, 24, hexc(SOFT), IN[500], "c"); c.restore()
        c.restore(); return self.surf.makeImageSnapshot().toarray()
    def frame(self, t, fps):
        dt = 1 / fps; sp = abs(DIV(t + dt / 2) - DIV(t - dt / 2))
        n = 1 if sp < 6 else int(min(10, 3 + sp / 8))
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
