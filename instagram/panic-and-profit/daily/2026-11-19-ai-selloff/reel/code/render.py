"""Panic & Profit Reel renderer (AMD short report, 2026-11-19). Skia 2D -> raw BGRA frames -> ffmpeg.
Concept: "the case file" - a manila folder; exhibits A-D slide in as paper memos, a red ALLEGED stamp lands,
and the story closes on a VERDICT? card with the audience question.
Usage: python3 code/render.py --scale 1 --fps 60 --out exports/reel.mp4
       python3 code/render.py --scale 0.5 --out previews/s.png --still 1 5 8"""
import argparse, math, os, subprocess, sys
import numpy as np, skia
sys.path.insert(0, os.path.dirname(__file__))
from timing import FPS, DURATION, HANDLE, P, PE, END, AMD_CLOSE, SOX_CLOSE, NDX_CLOSE

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


KRAFT, KRAFT_D = "#EFE6D2", "#DCCFB2"
def folder(c, t):
    a = ease_out((t - 0.05) / 0.5)
    c.save(); c.translate(0, (1 - a) * 80)
    c.drawRRect(rrect(70, 410, 300, 90, 14), paint(hexc(KRAFT_D)))                 # tab
    text(c, "CASE FILE", 110, 458, 28, hexc(INK), IN[700], track=5)
    c.drawRRect(rrect(60, 470, 960, 1080, 18), paint(hexc(KRAFT)))
    c.drawRRect(rrect(60, 470, 960, 1080, 18), paint(hexc(KRAFT_D), stroke=4))
    text(c, "AMD  ·  NOV 19, 2026", 1000, 535, 26, hexc("#8A7A58"), IN[700], "r", track=3)
    c.restore()

def memo(c, k, y, h, rot, label, title, lines, accent, dim=0.0):
    """A paper exhibit sliding in from the right; k = 0..1 progress."""
    if k <= 0: return
    x = lerp(W + 80, 110, clamp(k, 0, 1.08)); r = lerp(9, rot, clamp(k))
    c.save(); c.translate(x + 430, y + h / 2); c.rotate(r); c.translate(-430, -h / 2)
    c.drawRect(rect(10, 12, 860, h), paint(hexc("#000000", .08), blur=10))
    c.drawRect(rect(0, 0, 860, h), paint(hexc("#FFFFFF")))
    c.drawRect(rect(0, 0, 12, h), paint(hexc(accent)))
    text(c, label, 50, 62, 26, hexc(accent), IN[700], track=4)
    text(c, title, 50, 128, 50, hexc(INK), FR[800])
    for i, ln in enumerate(lines): text(c, ln, 50, 196 + i * 50, 33, hexc(MUTE), IN[500])
    if dim > 0: c.drawRect(rect(0, 0, 860, h), paint(hexc(KRAFT, .55 * dim)))
    c.restore()

def stamp(c, t, t0, x, y, txt, col, ang=-12, size=78):
    if t < t0: return
    k = clamp((t - t0) / 0.25); s = lerp(2.2, 1.0, ease_out(k))
    c.save(); c.translate(x, y); c.rotate(ang); c.scale(s, s)
    alpha_layer(c, clamp(k * 1.5) * .9)
    w = tw(txt, size, FR[800]) + 70
    c.drawRRect(rrect(-w / 2, -size * .85, w, size * 1.5, 12), paint(hexc(col), stroke=8))
    text(c, txt, 0, size * .32, size, hexc(col), FR[800], "c", track=4)
    c.restore(); c.restore()

def ticker(c, t, t0):
    """Exhibit D: the market card."""
    k = ease_out((t - t0) / 0.5)
    if k <= 0: return
    y = 1080; x = lerp(W + 80, 110, clamp(k, 0, 1.05))
    c.save(); c.translate(x, y)
    c.drawRect(rect(10, 12, 860, 400, ), paint(hexc("#000000", .08), blur=10))
    c.drawRect(rect(0, 0, 860, 400), paint(hexc("#FFFFFF"))); c.drawRect(rect(0, 0, 12, 400), paint(hexc(RED)))
    text(c, "EXHIBIT D · THE MARKET", 50, 62, 26, hexc(RED), IN[700], track=4)
    rows = [("AMD", AMD_CLOSE or "down up to ~9%", "close" if AMD_CLOSE else "intraday")]
    if SOX_CLOSE: rows.append(("CHIP INDEX (SOX)", SOX_CLOSE, "close"))
    if NDX_CLOSE: rows.append(("NASDAQ", NDX_CLOSE, "close"))
    for i, (n, v, s) in enumerate(rows):
        e = ease_out((t - (t0 + 0.4 + i * 0.5)) / 0.4)
        if e <= 0: continue
        alpha_layer(c, e); yy = 140 + i * 90
        text(c, n, 50, yy, 34, hexc(INK), IN[700], track=2); text(c, s, 50, yy + 34, 24, hexc(SOFT), IN[500])
        text(c, v, 810, yy + 14, 58 if len(v) < 9 else 40, hexc(RED if v.startswith(("-", "−", "down")) else GREEN), FR[800], "r")
        c.restore()
    c.restore()

def verdict(c, t):
    t0 = P[7] - 0.1
    if t < t0: return
    a = ease_out((t - t0) / 0.45)
    c.drawRect(rect(0, 330, W, 1250), paint(hexc(BG, .95 * a)))
    alpha_layer(c, a); dy = (1 - a) * 30
    text(c, "THE VERDICT IS YOURS", W / 2, 700 + dy, 30, hexc(RED), IN[700], "c", track=6)
    text(c, "Buying the dip", W / 2, 840 + dy, 96, hexc(INK), FR[800], "c")
    text(c, "or catching a", W / 2, 950 + dy, 80, hexc(MUTE), FR[700], "c")
    text(c, "falling knife?", W / 2, 1060 + dy, 96, hexc(RED), FRI[800], "c")
    b = ease_out((t - (t0 + 1.4)) / 0.4); alpha_layer(c, b)
    pw = tw("Tell us in the comments", 38, IN[700]) + 80
    c.drawRRect(rrect(W / 2 - pw / 2, 1160, pw, 84, 42), paint(hexc(INK)))
    text(c, "Tell us in the comments", W / 2, 1215, 38, hexc("#FFFFFF"), IN[700], "c")
    c.restore(); c.restore()

def lesson(c, t):
    t0 = P[6] - 0.1; t1 = PE[6] + 0.3
    if t < t0 or t > t1 + 0.4: return
    a = ease_out((t - t0) / 0.4) * (1 - sstep(t1, t1 + 0.4, t))
    c.drawRect(rect(0, 330, W, 1250), paint(hexc(BG, .95 * a)))
    alpha_layer(c, a)
    text(c, "THE LESSON", W / 2, 640, 30, hexc(GREEN), IN[700], "c", track=6)
    text(c, "A short report is", W / 2, 780, 84, hexc(INK), FR[800], "c")
    text(c, "a claim,", W / 2, 890, 96, hexc(RED), FRI[800], "c")
    text(c, "not a verdict.", W / 2, 1000, 96, hexc(INK), FR[800], "c")
    b = ease_out((t - (P[6] + 2.6)) / 0.4)
    if b > 0:
        alpha_layer(c, b)
        for i, s in enumerate(("Watch for the company's answer", "and for the regulators.")): text(c, s, W / 2, 1120 + i * 56, 40, hexc(MUTE), IN[600], "c")
        c.restore()
    c.restore()

def scene_end(c, t):
    a = ease_out((t - (END + 0.15)) / 0.6)
    alpha_layer(c, a); logo(c, W / 2, 900, 118, line=True, tagline=True); c.restore()
    b = ease_out((t - (END + 0.6)) / 0.5); alpha_layer(c, b)
    pw = tw("Follow " + HANDLE, 44, IN[700]) + 90
    c.drawRRect(rrect(W / 2 - pw / 2, 1110 + (1 - b) * 20, pw, 96, 48), paint(hexc(GREEN)))
    text(c, "Follow " + HANDLE, W / 2, 1172 + (1 - b) * 20, 44, hexc("#FFFFFF"), IN[700], "c")
    text(c, "Save this for the next short report.", W / 2, 1280, 34, hexc(MUTE), IN[500], "c")
    text(c, "NOT FINANCIAL ADVICE", W / 2, 1390, 24, hexc(SOFT), IN[600], "c", track=4); c.restore()

SRC_TXT = "Sources: Hunterbrook, Investing.com, TradingKey, Wccftech, OfficeChai · allegations are unproven"

class Renderer:
    def __init__(self, scale):
        self.scale = scale; self.surf = skia.Surface(int(W * scale), int(H * scale))
    def draw(self, t):
        c = self.surf.getCanvas(); c.save(); c.scale(self.scale, self.scale); background(c)
        fade = 1 - sstep(END - 0.1, END + 0.25, t)
        if fade > 0:
            alpha_layer(c, fade); folder(c, t)
            # hook on the folder (scene 0)
            hk = ease_out((t - 0.3) / 0.45) * (1 - sstep(P[1] - 0.3, P[1] + 0.1, t))
            if hk > 0:
                alpha_layer(c, hk)
                text(c, "AMD", 130, 760, 200, hexc(INK), FR[800])
                text(c, "down up to ~9%", 130, 870, 72, hexc(RED), FRI[800])
                text(c, "in one morning.", 130, 950, 60, hexc(INK), FR[700])
                text(c, "The trigger: a short seller.", 130, 1080, 44, hexc(MUTE), IN[600])
                c.restore()
            kA = ease_out((t - (P[1] - 0.1)) / 0.55); kB = ease_out((t - (P[2] - 0.1)) / 0.55)
            kC = ease_out((t - (P[3] - 0.1)) / 0.55)
            memo(c, kA, 600, 330, -2.5, "EXHIBIT A · WHO", "Hunterbrook", ["Published a report today and", "disclosed a bet against AMD stock."], INK, dim=sstep(P[2], P[2] + 0.5, t))
            memo(c, kB, 700, 400, 1.8, "EXHIBIT B · THE CLAIM", "A blacklisted buyer?", ["Alleges Chinese server maker IEIT,", "on the US Entity List since 2025,", "kept shipping newer AMD firmware."], RED, dim=sstep(P[3], P[3] + 0.5, t))
            stamp(c, t, P[2] + 3.2, 790, 1020, "ALLEGED", RED)
            memo(c, kC, 820, 380, -1.5, "EXHIBIT C · WHAT IT DOESN'T PROVE", "No violation shown", ["The report says it does not prove", "AMD broke export rules.", "AMD has not responded."], GREEN, dim=sstep(P[4], P[4] + 0.5, t))
            # why: export risk -> future sales
            wk = ease_out((t - (P[4] + 0.2)) / 0.45) * (1 - sstep(P[5] - 0.2, P[5] + 0.2, t))
            if wk > 0:
                alpha_layer(c, wk)
                c.drawRRect(rrect(110, 640, 860, 150, 16), paint(hexc(INK)))
                text(c, "Export risk  →  future sales  →  price", W / 2, 735, 46, hexc("#FFFFFF"), IN[700], "c")
                c.restore()
            ticker(c, t, P[5] - 0.1)
            lesson(c, t); verdict(c, t)
            logo(c, 100, 285, 40, center=False)
            tg = "SHORT REPORT"; w = tw(tg, 24, IN[700]) + 3 * 11 + 40
            c.drawRRect(rrect(W - 100 - w, 250, w, 50, 25), paint(hexc(RED)))
            text(c, tg, W - 100 - w / 2, 284, 24, hexc("#FFFFFF"), IN[700], "c", track=3)
            sa = sstep(4.5, 5.0, t); alpha_layer(c, sa); text(c, SRC_TXT, W / 2, 1600, 22, hexc(SOFT), IN[500], "c"); c.restore()
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
