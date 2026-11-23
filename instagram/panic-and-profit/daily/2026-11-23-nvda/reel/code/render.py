"""Panic & Profit Reel renderer (Nvidia comeback (rocket counter + timeline), 2026-11-20). Skia 2D -> raw BGRA frames -> ffmpeg.
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





def scene_hook(c, t):
    a = 1 - sstep(PE[1] + 0.1, PE[1] + 0.5, t)
    if a <= 0: return
    alpha_layer(c, a)
    text(c, "NVIDIA · TODAY, MON NOV 23", W / 2, 500, 30, hexc(MUTE), IN[700], "c", track=5)
    text(c, "The comeback", W / 2, 610, 86, hexc(INK), FR[800], "c")
    k = ease_io((t - 0.4) / 3.0)
    text(c, f"+{25 * k:.0f}%+", W / 2, 880, 230, hexc(GREEN), FR[800], "c")
    text(c, "in one morning", W / 2, 960, 50, hexc(INK), FR[700], "c")
    x0, x1 = 140, 940; pts = [(x0, 1300), (x0 + 200, 1320), (x0 + 330, 1335), (x0 + 450, 1290), (x0 + 560, 1180), (x0 + 680, 1100), (x1, 1040)]
    n = max(2, int(len(pts) * 25 * k)); pth = skia.Path(); pth.moveTo(*pts[0]); cnt = 0
    for (a_, b_), (c_, d_) in zip(pts, pts[1:]):
        for s_ in range(1, 26):
            cnt += 1
            if cnt > n: break
            pth.lineTo(lerp(a_, c_, s_ / 25), lerp(b_, d_, s_ / 25))
    c.drawPath(pth, paint(hexc(GREEN), stroke=9))
    tt = wtime("best", 1) - 0.2
    if t > tt:
        s = clamp(back_out((t - tt) / 0.4), 0, 1.15)
        c.save(); c.translate(W / 2, 1100); c.rotate(-4); c.scale(s, s)
        lab = "ONE OF ITS BEST DAYS EVER"; w = tw(lab, 32, IN[700]) + 3 * len(lab) + 60
        c.drawRRect(rrect(-w / 2, -40, w, 80, 40), paint(hexc(GREEN))); text(c, lab, 0, 12, 32, hexc("#FFFFFF"), IN[700], "c", track=3); c.restore()
    c.restore()

def scene_why(c, t):
    a = overlay(t, P[2] - 0.2, PE[4] + 0.3)
    if a <= 0: return
    alpha_layer(c, a)
    text(c, "WHY?", W / 2, 490, 34, hexc(RED), IN[700], "c", track=8)
    text(c, "The CEO is back.", W / 2, 600, 86, hexc(INK), FR[800], "c")
    # timeline
    x0, x1, y = 160, 920, 760
    k = ease_io((t - wtime("reinstated", 2)) / 1.2) if t > wtime("reinstated", 2) else 0
    c.drawLine(x0, y, x1, y, paint(hexc(BORDER), stroke=10))
    c.drawLine(x0, y, lerp(x0, x1, k), y, paint(hexc(INK), stroke=10))
    c.drawCircle(x0, y, 22, paint(hexc(RED))); text(c, "NOV 12", x0, y + 70, 32, hexc(RED), IN[700], "c"); text(c, "Steps down", x0, y + 110, 28, hexc(MUTE), IN[600], "c")
    if k > 0.95:
        c.drawCircle(x1, y, 22, paint(hexc(GREEN))); text(c, "NOV 23", x1, y + 70, 32, hexc(GREEN), IN[700], "c"); text(c, "Reinstated", x1, y + 110, 28, hexc(MUTE), IN[600], "c")
    tt = wtime("eleven", 2)
    if t > tt:
        e = ease_out((t - tt) / 0.35); alpha_layer(c, e)
        c.drawRRect(rrect(W / 2 - 130, y - 110, 260, 70, 35), paint(hexc(INK))); text(c, "11 DAYS", W / 2, y - 63, 34, hexc("#FFFFFF"), IN[700], "c", track=3); c.restore()
    cards = [(P[3], "WASHINGTON", "Trump urged the board to bring him back"), (P[4], "THE MARKET", "Nasdaq opened up more than 6%")]
    for j, (tt, hd, ln) in enumerate(cards):
        if t < tt - 0.1: continue
        s = clamp(back_out((t - tt + 0.1) / 0.4), 0, 1.12); yy = 1040 + j * 170
        c.save(); c.translate(W / 2, yy); c.scale(s, s)
        c.drawRRect(rrect(-420, -70, 840, 140, 20), paint(hexc("#FFFFFF"))); c.drawRRect(rrect(-420, -70, 840, 140, 20), paint(hexc(GREEN if j else INK), stroke=4))
        text(c, hd, -380, -18, 26, hexc(GREEN if j else RED), IN[700], track=4); text(c, ln, -380, 38, 34, hexc(INK), FR[800])
        c.restore()
    c.restore()

def scene_caution(c, t):
    a = overlay(t, P[5] - 0.2, PE[6] + 0.3)
    if a <= 0: return
    alpha_layer(c, a)
    text(c, "BUT REMEMBER", W / 2, 490, 34, hexc(RED), IN[700], "c", track=8)
    k = ease_out((t - P[5]) / 0.4)
    c.save(); c.translate(W / 2, 720); c.scale(clamp(back_out((t - P[5]) / 0.4), 0, 1.12), clamp(back_out((t - P[5]) / 0.4), 0, 1.12))
    c.drawRRect(rrect(-420, -150, 840, 300, 26), paint(hexc("#FFF1F3"))); c.drawRRect(rrect(-420, -150, 840, 300, 26), paint(hexc(RED), stroke=6))
    text(c, "FRIDAY, NOV 20", 0, -80, 30, hexc(MUTE), IN[700], "c", track=4); text(c, "-14%", 0, 70, 170, hexc(RED), FR[800], "c"); c.restore()
    text(c, "Huge swings, both ways", W / 2, 940, 40, hexc(INK), IN[700], "c")
    tt = P[6] - 0.1
    if t > tt:
        s = clamp(back_out((t - tt) / 0.4), 0, 1.12)
        c.save(); c.translate(W / 2, 1150); c.scale(s, s)
        c.drawRRect(rrect(-420, -100, 840, 200, 22), paint(hexc("#FFFFFF"))); c.drawRRect(rrect(-420, -100, 840, 200, 22), paint(hexc(INK), stroke=4))
        text(c, "STILL OPEN", -380, -40, 26, hexc(RED), IN[700], track=4)
        text(c, "SEC review of its accounting", -380, 15, 44, hexc(INK), FR[800]); text(c, "(reported by Reuters; no charges)", -380, 65, 28, hexc(MUTE), IN[600])
        c.restore()
    c.restore()

def scene_long(c, t):
    a = overlay(t, P[7] - 0.2, PE[7] + 0.3)
    if a <= 0: return
    alpha_layer(c, a)
    text(c, "THE LONG-TERM VIEW", W / 2, 490, 34, hexc(GREEN), IN[700], "c", track=8)
    text(c, "The CEO is back.", W / 2, 720, 100, hexc(GREEN), FR[800], "c")
    text(c, "The questions", W / 2, 880, 100, hexc(INK), FR[800], "c")
    text(c, "aren't gone.", W / 2, 1000, 100, hexc(RED), FRI[800], "c")
    c.restore()

def vote(c, t):
    t0 = P[8] - 0.1
    if t < t0: return
    a = ease_out((t - t0) / 0.45)
    c.drawRect(rect(0, 400, W, 1100), paint(hexc(BG, .97 * a)))
    alpha_layer(c, a)
    text(c, "YOUR CALL", W / 2, 640, 32, hexc(RED), IN[700], "c", track=8)
    text(c, "Nvidia: real comeback,", W / 2, 790, 82, hexc(INK), FR[800], "c")
    text(c, "or just a bounce?", W / 2, 890, 70, hexc(INK), FRI[800], "c")
    for i, (lab, cc, x) in enumerate((("COMEBACK", GREEN, 290), ("BOUNCE", RED, 790))):
        k = back_out((t - (t0 + 1.0 + i * 0.25)) / 0.4)
        if k <= 0: continue
        pulse = 1 + 0.04 * math.sin((t - t0) * 7 + i * 1.6)
        c.save(); c.translate(x, 1070); c.scale(clamp(k, 0, 1.2) * pulse, clamp(k, 0, 1.2) * pulse)
        c.drawRRect(rrect(-225, -66, 450, 132, 66), paint(hexc(cc))); text(c, lab, 0, 20, 54 if len(lab) > 6 else 60, hexc("#FFFFFF"), FR[800], "c", track=2)
        c.restore()
    b = ease_out((t - (t0 + 1.8)) / 0.4); alpha_layer(c, b)
    text(c, "Comment COMEBACK or BOUNCE", W / 2, 1230, 44, hexc(INK), IN[700], "c"); c.restore()
    c.restore()

def cam(t):
    z = 1.0
    for t0 in P[:8]: z += 0.03 * ease_out((t - t0) / 0.6) * (1 - ease_out((t - (t0 + 1.2)) / 2.0))
    sh = 0.0
    for st in (3.3, P[5]):
        if st < t < st + 0.35: sh += 12 * math.exp(-(t - st) * 12) * math.sin((t - st) * 90)
    return z, sh

def scene_end(c, t):
    a = ease_out((t - (END + 0.15)) / 0.6)
    alpha_layer(c, a); logo(c, W / 2, 900, 118, line=True, tagline=True); c.restore()
    b = ease_out((t - (END + 0.6)) / 0.5); alpha_layer(c, b)
    pw = tw("Follow " + HANDLE, 44, IN[700]) + 90
    c.drawRRect(rrect(W / 2 - pw / 2, 1110 + (1 - b) * 20, pw, 96, 48), paint(hexc(GREEN)))
    text(c, "Follow " + HANDLE, W / 2, 1172 + (1 - b) * 20, 44, hexc("#FFFFFF"), IN[700], "c")
    text(c, "Breaking market news, explained for long-term investors.", W / 2, 1280, 30, hexc(MUTE), IN[500], "c")
    text(c, "NOT FINANCIAL ADVICE", W / 2, 1390, 24, hexc(SOFT), IN[600], "c", track=4); c.restore()

SRC_TXT = "Sources: CNBC, Yahoo Finance, Investing.com, Seeking Alpha, Fast Company, Reuters"

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
            scene_hook(c, t); scene_why(c, t); scene_caution(c, t); scene_long(c, t)
            c.restore()
            vote(c, t)
            logo(c, 100, 285, 40, center=False)
            tg = "BREAKING"; w = tw(tg, 24, IN[700]) + 3 * len(tg) + 40
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
