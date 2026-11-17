"""Duolingo spec film renderer (independent educational concept, not affiliated with Duolingo).

Draws every frame with Skia (vector 2D) and pipes raw frames to FFmpeg.
Usage:
  python3 code/render.py --orient L --scale 1 --fps 60 --out exports/video_L.mp4
  python3 code/render.py --orient V --scale 0.5 --fps 30 --out previews/rough_V.mp4
"""
import argparse, json, math, os, subprocess, sys
import numpy as np, skia
sys.path.insert(0, os.path.dirname(__file__))
from timing import FPS, DURATION, SCENES, EVENTS as EV, NAME, HANDLE, AVATAR_INITIALS

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
FONT = {w: skia.Typeface.MakeFromFile(f"{ROOT}/assets/fonts/Nunito-{w}.ttf") for w in (700, 800, 900)}
SYMB = skia.Typeface.MakeFromFile("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf")

# ---------------- palette (Duolingo public brand colours) ----------------
def hexc(h, a=1.0):
    h = h.lstrip("#"); return skia.Color(int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16), int(max(0, min(1, a)) * 255))
GREEN, GREEN_LIP, MASK = "#58CC02", "#58A700", "#89E219"
FOX, BEE, MACAW, BEETLE, CARDINAL = "#FF9600", "#FFC800", "#1CB0F6", "#CE82FF", "#FF4B4B"
BG, CARD, CARD_LIP, LINE, TXT, SUB = "#0B1013", "#131F24", "#37464F", "#2A363D", "#F1F7FB", "#8A9BA6"

# ---------------- maths ----------------
clamp = lambda x, a=0.0, b=1.0: max(a, min(b, x))
lerp = lambda a, b, t: a + (b - a) * t
def sstep(a, b, x): t = clamp((x - a) / (b - a)); return t * t * (3 - 2 * t)
def ease_out(t): t = clamp(t); return 1 - (1 - t) ** 3
def ease_in(t): t = clamp(t); return t ** 3
def ease_io(t): t = clamp(t); return 4 * t ** 3 if t < .5 else 1 - (-2 * t + 2) ** 3 / 2
def back_out(t, c=1.9): t = clamp(t); return 1 + (c + 1) * (t - 1) ** 3 + c * (t - 1) ** 2
def appear(t, t0, dur=0.35): return back_out((t - t0) / dur)
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
def catmull(pts, per=48):
    P = [pts[0]] + list(pts) + [pts[-1]]; out = []
    for i in range(1, len(P) - 2):
        p0, p1, p2, p3 = map(np.array, P[i - 1:i + 3])
        for k in range(per):
            t = k / per
            out.append(0.5 * ((2 * p1) + (-p0 + p2) * t + (2 * p0 - 5 * p1 + 4 * p2 - p3) * t * t + (-p0 + 3 * p1 - 3 * p2 + p3) * t ** 3))
    out.append(np.array(pts[-1], float)); out = np.array(out)
    s = np.concatenate([[0], np.cumsum(np.linalg.norm(np.diff(out, axis=0), axis=1))])
    return out, s

# ---------------- world layout ----------------
B = (0, 0); NODES = [(1000, 110), (1250, -60), (1500, 90)]; C1 = (2250, 0); S = (3400, 30)
LB = (4550, 0); SP = (5550, 0); HUB = (6450, 0); F = (8000, 0)
MAIN = [(-330, 178), (-60, 172), (330, 168), (700, 150), NODES[0], NODES[1], NODES[2], (1760, 0), (2250, 0), (2760, 0),
        (3150, 150), (3300, 230), (3520, 190), (3600, 30), (3500, -140), (3330, -170), (3230, -40), (3420, 40), (3800, 0),
        (4550, 0), (5000, 0), (5550, 0), (6050, 0), HUB]
TRAIL, TRAIL_S = catmull(MAIN)
def s_near(p): return float(TRAIL_S[np.argmin(np.linalg.norm(TRAIL - np.array(p), axis=1))])
def trail_at(s):
    i = int(np.clip(np.searchsorted(TRAIL_S, s), 1, len(TRAIL) - 1)); a, b = TRAIL[i - 1], TRAIL[i]
    u = (s - TRAIL_S[i - 1]) / max(1e-6, TRAIL_S[i] - TRAIL_S[i - 1]); return a + (b - a) * clamp(u)
HEAD = monotone([(0.0, 0), (0.55, 0), (1.35, s_near((700, 150))), (1.75, s_near(NODES[0])), (2.05, s_near(NODES[1])), (2.35, s_near(NODES[2])),
                 (2.85, s_near((2250, 0))), (4.8, s_near((2760, 0))), (5.05, s_near((3150, 150))), (5.6, s_near((3230, -40))),
                 (6.4, s_near((3420, 40))), (7.15, s_near((3800, 0))), (7.5, s_near((4550, 0))), (9.1, s_near((5000, 0))),
                 (9.45, s_near((5550, 0))), (11.3, s_near((6050, 0))), (11.75, TRAIL_S[-1]), (DURATION, TRAIL_S[-1])])

def layout(orient):
    if orient == "L":
        st = [(7200, -435), (7200, -145), (7200, 145), (7200, 435)]
        cam = [(0, 150, 20, 1.0), (1.35, 160, 20, 1.0), (1.8, 900, 40, 1.0), (2.45, 1450, 20, 1.0), (3.0, 2420, 0, 1.0), (4.9, 2430, 0, 1.04),
               (5.35, 3420, 30, 1.0), (7.0, 3430, 30, 1.05), (7.55, 4550, 0, 1.0), (9.1, 4560, 0, 1.05), (9.65, 5550, -40, 1.0),
               (11.3, 5560, -40, 1.04), (12.0, 6750, 0, 0.92), (14.3, 6830, 0, 0.86), (15.2, 7900, 0, 0.92), (15.8, 8000, 0, 1.0),
               (18.7, 8000, 0, 1.05)]
        return dict(stations=st, cam=cam, duo_mini=(C1[0] + 640, C1[1] + 150), flame=(S[0] - 40, S[1] - 20), counter=(S[0] + 430, S[1]),
                    bubble=(SP[0], SP[1] - 250), mic=(SP[0], SP[1] + 210), msg=[(F[0], F[1] - 30), (F[0], F[1] + 90)], txt=1.0,
                    intro_duo=(-360, -20), intro_wm=(330, 50), msg_size=120)
    st = [(6950, -660), (6950, -220), (6950, 220), (6950, 660)]
    cam = [(0, 150, -80, 0.85), (1.35, 150, -80, 0.85), (1.8, 900, 40, 0.9), (2.45, 1450, 20, 0.95), (3.0, 2250, 180, 1.0), (4.9, 2250, 190, 1.03),
           (5.35, 3380, 160, 1.0), (7.0, 3390, 170, 1.04), (7.55, 4550, 0, 1.0), (9.1, 4550, 10, 1.04), (9.65, 5550, 0, 1.0),
           (11.3, 5550, 0, 1.03), (12.0, 6650, 0, 0.8), (14.3, 6700, 0, 0.78), (15.2, 7900, 0, 0.9), (15.8, 8000, 40, 1.0), (18.7, 8000, 40, 1.04)]
    return dict(stations=st, cam=cam, duo_mini=(C1[0], C1[1] + 560), flame=(S[0], S[1] - 260), counter=(S[0], S[1] + 300),
                bubble=(SP[0], SP[1] - 330), mic=(SP[0], SP[1] + 330), msg=[(F[0], F[1] - 60), (F[0], F[1] + 60)], txt=1.12,
                intro_duo=(150, -360), intro_wm=(150, 60), msg_size=92)

# ---------------- drawing helpers ----------------
def paint(color, **kw):
    p = skia.Paint(AntiAlias=True, Color=color)
    if "stroke" in kw: p.setStyle(skia.Paint.kStroke_Style); p.setStrokeWidth(kw["stroke"]); p.setStrokeCap(skia.Paint.kRound_Cap); p.setStrokeJoin(skia.Paint.kRound_Join)
    if "blur" in kw and kw["blur"] > 0: p.setMaskFilter(skia.MaskFilter.MakeBlur(skia.kNormal_BlurStyle, kw["blur"]))
    if "shader" in kw: p.setShader(kw["shader"])
    return p
def text(c, s, x, y, size, color, weight=900, align="c", typeface=None):
    f = skia.Font(typeface or FONT[weight], size); w = f.measureText(s)
    dx = {"c": -w / 2, "l": 0, "r": -w}[align]; c.drawString(s, x + dx, y + size * 0.36, f, paint(color)); return w
def text_w(s, size, weight=900): return skia.Font(FONT[weight], size).measureText(s)
def rr(x, y, w, h, r): return skia.RRect.MakeRectXY(skia.Rect.MakeXYWH(x - w / 2, y - h / 2, w, h), r, r)
def block(c, x, y, w, h, r, face, lip, lip_h=8, border=None, shadow=True, press=0.0):
    """Duolingo-style dimensional block: face sits on a darker lip; press pushes it down."""
    lh = lip_h * (1 - press)
    if shadow: c.drawRRect(rr(x, y + lip_h + 14, w, h, r), paint(hexc("#000000", .45), blur=18))
    c.drawRRect(rr(x, y + lip_h * 0.5, w, h, r), paint(lip))
    c.drawRRect(rr(x, y + (lip_h - lh), w, h, r), paint(face))
    if border: c.drawRRect(rr(x, y + (lip_h - lh), w - 3, h - 3, r), paint(border, stroke=3))
def group_alpha(c, a): c.saveLayerAlpha(None, int(clamp(a) * 255))

# ---------------- Duo (drawn in parts so each can animate) ----------------
def duo(c, x, y, s, t, squash=0.0, wing=(0.0, 0.0), look=(0.0, 0.0), tilt=0.0, blink=0.0, jump=0.0, alpha=1.0):
    c.save(); c.translate(x, y - jump); c.scale(s, s)
    c.drawOval(skia.Rect.MakeLTRB(-120, 172, 120, 200), paint(hexc("#000000", .45 * alpha), blur=12))
    c.translate(0, 170); c.scale(1 + squash * 0.18, 1 - squash * 0.22); c.translate(0, -170); c.rotate(tilt)
    body, belly, wingc = hexc(GREEN, alpha), hexc(MASK, alpha), hexc(GREEN_LIP, alpha)
    orange, orange_l = hexc(FOX, alpha), hexc(BEE, alpha)
    for sx in (-1, 1):  # feet
        c.drawOval(skia.Rect.MakeLTRB(sx * 55 - 34, 150, sx * 55 + 34, 182), paint(orange))
    for sx, ang in ((-1, wing[0]), (1, wing[1])):  # wings
        c.save(); c.translate(sx * 132, -5); c.rotate(-sx * ang)
        c.drawRRect(rr(sx * 12, 55, 58, 128, 29), paint(wingc)); c.restore()
    for sx in (-1, 1):  # ear tufts
        pth = skia.Path(); pth.moveTo(sx * 128, -118); pth.quadTo(sx * 118, -200, sx * 70, -205); pth.quadTo(sx * 85, -160, sx * 50, -150); pth.close()
        c.drawPath(pth, paint(body))
    c.drawRRect(skia.RRect.MakeRectXY(skia.Rect.MakeLTRB(-150, -175, 150, 168), 140, 150), paint(body))
    c.drawOval(skia.Rect.MakeLTRB(-98, -5, 98, 158), paint(belly))
    c.drawRRect(skia.RRect.MakeRectXY(skia.Rect.MakeLTRB(-150, -175, 150, 168), 140, 150), paint(hexc("#FFFFFF", .10 * alpha), stroke=4))
    for sx in (-1, 1):  # eyes
        ex, ey = sx * 56, -78
        c.save(); c.translate(ex, ey); c.scale(1, max(0.08, 1 - blink))
        c.drawCircle(0, 0, 60, paint(hexc("#FFFFFF", alpha)))
        px, py = look[0] * 16 - sx * 6, look[1] * 14 + 6
        c.drawCircle(px, py, 29, paint(hexc("#1B1B1B", alpha))); c.drawCircle(px - 9, py - 10, 9, paint(hexc("#FFFFFF", alpha)))
        c.restore()
    beak = skia.Path(); beak.moveTo(-34, -32); beak.quadTo(0, -44, 34, -32); beak.quadTo(10, 12, 0, 18); beak.quadTo(-10, 12, -34, -32); beak.close()
    c.drawPath(beak, paint(orange))
    top = skia.Path(); top.moveTo(-30, -32); top.quadTo(0, -42, 30, -32); top.quadTo(0, -18, -30, -32); top.close(); c.drawPath(top, paint(orange_l))
    c.restore()

def wordmark(c, x, y, size, reveal=1.0, alpha=1.0):
    w = text_w("duolingo", size)
    c.save(); c.clipRect(skia.Rect.MakeLTRB(x - w / 2 - 10, y - size, x - w / 2 - 10 + (w + 20) * clamp(reveal), y + size))
    text(c, "duolingo", x, y, size, hexc(GREEN, alpha)); c.restore(); return w

# ---------------- trail ----------------
def stroke_poly(c, pts, width, color, blur=0):
    if len(pts) < 2: return
    p = skia.Path(); p.moveTo(*pts[0])
    for q in pts[1:]: p.lineTo(*q)
    c.drawPath(p, paint(color, stroke=width, blur=blur))
def draw_trail_pts(c, pts, width=26, base=GREEN, hi=MASK, glow=0.35, alpha=1.0):
    stroke_poly(c, pts, width * 2.1, hexc(base, glow * alpha), blur=16)
    stroke_poly(c, [(p[0], p[1] + 6) for p in pts], width, hexc(GREEN_LIP if base == GREEN else base, alpha))
    stroke_poly(c, pts, width, hexc(base, alpha))
    stroke_poly(c, [(p[0] - 1, p[1] - 5) for p in pts], width * 0.28, hexc(hi, 0.9 * alpha))
def curve(a, b, bend=0.5, n=60):
    (x0, y0), (x1, y1) = a, b; mx = lerp(x0, x1, bend)
    return [((1 - u) ** 3 * x0 + 3 * (1 - u) ** 2 * u * mx + 3 * (1 - u) * u * u * mx + u ** 3 * x1,
             (1 - u) ** 3 * y0 + 3 * (1 - u) ** 2 * u * y0 + 3 * (1 - u) * u * u * y1 + u ** 3 * y1) for u in np.linspace(0, 1, n)]
def partial(pts, frac): n = max(2, int(len(pts) * clamp(frac))); return pts[:n] if frac > 0 else []

# ---------------- voice envelope (drives the waveform) ----------------
VOICE_ENV = None
def voice_env(t):
    global VOICE_ENV
    if VOICE_ENV is None:
        import soundfile as sf
        a, sr = sf.read(f"{ROOT}/audio/voice.wav"); a = np.abs(a if a.ndim == 1 else a.mean(1)); hop = sr // 100
        VOICE_ENV = np.array([a[i:i + hop * 3].mean() for i in range(0, len(a), hop)]); VOICE_ENV /= VOICE_ENV.max() + 1e-9
    i = int(t * 100); return float(VOICE_ENV[i]) if 0 <= i < len(VOICE_ENV) else 0.0

# ---------------- scenes (world space) ----------------
def scene_intro(c, t, L):
    land = 0.5
    if t < land: y = lerp(-1100, 0, ease_in(t / land)); sq = -0.25 * (t / land)
    else: u = t - land; y = -abs(math.sin(u * 7.5)) * 70 * math.exp(-u * 4.5); sq = 0.9 * math.exp(-u * 9) * math.cos(u * 22)
    tilt = 9 * sstep(0.95, 1.25, t) * (1 - sstep(1.8, 2.1, t))
    wing = (20 * sstep(0.5, 0.65, t) * (1 - sstep(0.75, 1.0, t)), 35 * math.sin(clamp((t - 0.55) / 0.6) * math.pi))
    blink = 1 - abs(math.cos(clamp((t - 1.15) / 0.18) * math.pi)) if 1.15 < t < 1.33 else 0
    a = 1 - sstep(2.6, 3.0, t)
    if a > 0:
        dx, dy = L["intro_duo"]; duo(c, dx, dy + y, 0.82, t, squash=sq, wing=wing, look=(lerp(0, 1, sstep(0.9, 1.3, t)), 0.2), tilt=tilt, blink=blink, alpha=a)
        wordmark(c, *L["intro_wm"], 170, reveal=sstep(0.6, 1.35, t), alpha=a)

def scene_nodes(c, t, L):
    for i, (nx, ny) in enumerate(NODES):
        on = t >= EV[f"lesson_node_{i + 1}"]; pop = appear(t, EV[f"lesson_node_{i + 1}"], 0.3) if on else 1
        c.save(); c.translate(nx, ny - 34); c.scale(pop, pop)
        block(c, 0, 0, 96, 88, 44, hexc(GREEN if on else CARD_LIP), hexc(GREEN_LIP if on else LINE), lip_h=10)
        star = skia.Path()
        for k in range(10):
            r = 22 if k % 2 == 0 else 10; a = -math.pi / 2 + k * math.pi / 5; star.lineTo(r * math.cos(a), r * math.sin(a) + 2) if k else star.moveTo(r * math.cos(a), r * math.sin(a) + 2)
        star.close(); c.drawPath(star, paint(hexc("#FFFFFF" if on else "#52656D")))
        c.restore()

def scene_lesson(c, t, L):
    if not (2.4 < t < 5.6): return
    a = sstep(2.45, 2.8, t) * (1 - sstep(5.15, 5.5, t)); group_alpha(c, a)
    cx, cy = C1; W, H = 880, 640; ent = ease_out((t - 2.45) / 0.5)
    c.save(); c.translate(0, (1 - ent) * 80)
    block(c, cx, cy, W, H, 32, hexc(CARD), hexc(CARD_LIP), lip_h=10, border=hexc(CARD_LIP))
    prog = lerp(0.35, 0.78, ease_out((t - EV["correct"]) / 0.6))
    c.drawRRect(rr(cx, cy - 262, 760, 24, 12), paint(hexc(CARD_LIP)))
    c.drawRRect(skia.RRect.MakeRectXY(skia.Rect.MakeLTRB(cx - 380, cy - 274, cx - 380 + 760 * prog, cy - 250), 12, 12), paint(hexc(GREEN)))
    c.drawRRect(skia.RRect.MakeRectXY(skia.Rect.MakeLTRB(cx - 372, cy - 270, cx - 380 + 760 * prog - 8, cy - 265), 3, 3), paint(hexc("#FFFFFF", .35)))
    text(c, "Traduz esta frase", cx - 380, cy - 200, 38, hexc(TXT), 900, "l")
    c.drawCircle(cx - 350, cy - 122, 30, paint(hexc(MACAW)))
    sp = skia.Path(); sp.moveTo(cx - 362, cy - 132); sp.lineTo(cx - 352, cy - 132); sp.lineTo(cx - 340, cy - 142); sp.lineTo(cx - 340, cy - 102); sp.lineTo(cx - 352, cy - 112); sp.lineTo(cx - 362, cy - 112); sp.close()
    c.drawPath(sp, paint(hexc("#FFFFFF")))
    text(c, "Je bois de l'eau.", cx - 300, cy - 124, 40, hexc(TXT), 800, "l")
    for yy in (cy - 30, cy + 50): c.drawLine(cx - 380, yy, cx + 380, yy, paint(hexc(CARD_LIP), stroke=3))
    bank = ["água", "como", "Eu", "a", "bebo"]; picks = ["Eu", "bebo", "água"]
    bx = cx - 360; pos = {}
    for wd in bank: w = text_w(wd, 34, 800) + 44; pos[wd] = (bx + w / 2, cy + 140, w); bx += w + 16
    ax = cx - 380; target = {}
    for wd in picks: w = pos[wd][2]; target[wd] = (ax + w / 2, cy - 64); ax += w + 14
    for wd in bank:
        x0, y0, w = pos[wd]; c.drawRRect(rr(x0, y0 + 4, w, 64, 16), paint(hexc(LINE)))
    for wd in bank:
        x0, y0, w = pos[wd]; x, y = x0, y0
        if wd in picks:
            k = picks.index(wd); u = ease_io((t - EV[f"tile_{k + 1}"]) / 0.3)
            x, y = lerp(x0, target[wd][0], u), lerp(y0, target[wd][1], u) - math.sin(u * math.pi) * 60
        block(c, x, y, w, 64, 16, hexc(CARD), hexc(CARD_LIP), lip_h=6, border=hexc(CARD_LIP), shadow=False)
        text(c, wd, x, y + 1, 34, hexc(TXT), 800)
    pressed = sstep(EV["check"] - 0.05, EV["check"], t) * (1 - sstep(EV["check"] + 0.05, EV["check"] + 0.15, t))
    ok = sstep(EV["correct"], EV["correct"] + 0.2, t)
    if ok < 1:
        block(c, cx, cy + 250, 760, 70, 18, hexc(GREEN), hexc(GREEN_LIP), lip_h=8, shadow=False, press=pressed)
        text(c, "VERIFICAR", cx, cy + 250 + pressed * 6, 34, hexc("#FFFFFF"), 900)
    if ok > 0:
        c.save(); c.clipRRect(rr(cx, cy, W, H, 32)); group_alpha(c, ok)
        c.drawRect(skia.Rect.MakeLTRB(cx - W / 2, cy + 185 + (1 - ok) * 60, cx + W / 2, cy + H / 2 + 20), paint(hexc("#1E3A12")))
        c.drawCircle(cx - 330, cy + 250, 34, paint(hexc(GREEN)))
        ck = skia.Path(); ck.moveTo(cx - 346, cy + 250); ck.lineTo(cx - 334, cy + 262); ck.lineTo(cx - 312, cy + 238)
        c.drawPath(ck, paint(hexc("#FFFFFF"), stroke=8)); text(c, "Excelente!", cx - 278, cy + 250, 46, hexc(GREEN), 900, "l")
        c.restore(); c.restore()
    c.restore(); c.restore()
    mx, my = L["duo_mini"]; jump = 60 * max(0, math.sin(clamp((t - EV["correct"]) / 0.5) * math.pi))
    duo(c, mx, my, 0.55, t, wing=(40 * jump / 60, 40 * jump / 60), look=(-0.8, -0.2), jump=jump, squash=-0.3 * jump / 60, alpha=a)

def flame_path(cx, cy, s, flick):
    p = skia.Path(); p.moveTo(cx, cy + 120 * s)
    p.cubicTo(cx - 120 * s, cy + 110 * s, cx - 130 * s, cy - 10 * s, cx - 60 * s, cy - 90 * s)
    p.cubicTo(cx - 50 * s, cy - 40 * s, cx - 20 * s, cy - 30 * s, cx - 10 * s, cy - 40 * s)
    p.cubicTo(cx - 30 * s, cy - 120 * s, cx + (10 + flick) * s, cy - 170 * s, cx + (40 + flick) * s, cy - 190 * s)
    p.cubicTo(cx + 40 * s, cy - 110 * s, cx + 140 * s, cy - 60 * s, cx + 120 * s, cy + 40 * s)
    p.cubicTo(cx + 110 * s, cy + 100 * s, cx + 60 * s, cy + 120 * s, cx, cy + 120 * s); p.close(); return p
def scene_streak(c, t, L):
    if not (4.9 < t < 7.8): return
    a = sstep(4.95, 5.2, t) * (1 - sstep(7.3, 7.65, t)); group_alpha(c, a)
    fx, fy = L["flame"]; s = 1.25 * appear(t, EV["flame"], 0.45); fl = 8 * math.sin(t * 9)
    c.drawCircle(fx, fy, 260 * s, paint(hexc(FOX, .18), blur=60))
    c.drawPath(flame_path(fx, fy, s, fl), paint(hexc(FOX), shader=skia.GradientShader.MakeLinear([skia.Point(fx, fy - 200 * s), skia.Point(fx, fy + 120 * s)], [hexc(BEE), hexc(FOX)])))
    c.drawPath(flame_path(fx, fy + 40 * s, s * 0.5, -fl), paint(hexc("#FFF4C2")))
    cx, cy = L["counter"]; e = ease_io((t - EV["counter_start"]) / (EV["counter_end"] - EV["counter_start"]))
    n = int(round(math.exp(lerp(0, math.log(365), e)))) if t > EV["counter_start"] else 1
    vis = appear(t, EV["counter_start"] - 0.2, 0.4); c.save(); c.translate(cx, cy); c.scale(vis, vis)
    text(c, f"{n}", 0, -40, 190 * L["txt"], hexc(FOX), 900); text(c, "dias seguidos", 0, 90, 56 * L["txt"], hexc(TXT), 900)
    for k in range(7):
        x = (k - 3) * 64; on = e * 7 > k
        c.drawCircle(x, 185, 24, paint(hexc(FOX if on else CARD_LIP)))
        if on: ck = skia.Path(); ck.moveTo(x - 10, 185); ck.lineTo(x - 3, 193); ck.lineTo(x + 11, 177); c.drawPath(ck, paint(hexc("#FFFFFF"), stroke=5))
    c.restore(); c.restore()

LEAGUE = [("Kenji", 1420, "#1CB0F6"), ("Léa", 1385, "#FF4B4B"), ("Tomás", 1240, "#FF9600"), ("Priya", 1105, "#CE82FF"), ("Marta", 980, "#58CC02")]
def scene_league(c, t, L):
    if not (7.0 < t < 9.9): return
    a = sstep(7.05, 7.35, t) * (1 - sstep(9.4, 9.75, t)); group_alpha(c, a)
    cx, cy = LB; W, H = 820, 700
    block(c, cx, cy, W, H, 32, hexc(CARD), hexc(CARD_LIP), lip_h=10, border=hexc(CARD_LIP))
    gem = skia.Path(); gem.moveTo(cx - 360, cy - 280); gem.lineTo(cx - 330, cy - 305); gem.lineTo(cx - 300, cy - 280); gem.lineTo(cx - 330, cy - 240); gem.close()
    c.drawPath(gem, paint(hexc(MACAW))); text(c, "Liga Diamante", cx - 280, cy - 278, 44, hexc(TXT), 900, "l")
    text(c, "Os 3 primeiros sobem de liga", cx - 360, cy - 222, 26, hexc(SUB), 800, "l")
    u = ease_io((t - EV["climb_start"]) / (EV["climb_end"] - EV["climb_start"]))
    marta_rank = lerp(4, 0, u); xp = int(lerp(980, 1560, u))
    order = [(i, float(i)) for i in range(4)]
    rows = []
    for i, (name, pts, col) in enumerate(LEAGUE[:4]):
        r = i + (1 if marta_rank < i + 0.5 else 0) * clamp((i + 0.5 - marta_rank) * 2)
        rows.append((r, name, pts, col, False))
    rows.append((marta_rank, "Marta", xp, GREEN, True))
    for r, name, pts, col, me in sorted(rows, key=lambda z: z[4]):
        y = cy - 140 + r * 104
        if me: block(c, cx, y, 760, 92, 22, hexc("#1E3A12"), hexc(GREEN_LIP), lip_h=6, border=hexc(GREEN), shadow=True)
        rank = int(round(r)) + 1; medal = {1: BEE, 2: "#C0C8D0", 3: "#CD7F32"}.get(rank)
        if medal: c.drawCircle(cx - 330, y, 24, paint(hexc(medal)))
        text(c, str(rank), cx - 330, y, 30, hexc("#0B1013" if medal else SUB), 900)
        c.drawCircle(cx - 250, y, 32, paint(hexc(col))); text(c, name[0], cx - 250, y, 32, hexc("#FFFFFF"), 900)
        text(c, name, cx - 200, y, 38, hexc(TXT), 900, "l"); text(c, f"{pts:,} XP", cx + 350, y, 32, hexc(GREEN if me else SUB), 900, "r")
    if u >= 1:
        k = appear(t, EV["climb_end"], 0.35); y = cy - 140
        c.save(); c.translate(cx - 250, y - 52); c.scale(k, k)
        cr = skia.Path(); cr.moveTo(-26, 10); cr.lineTo(-30, -18); cr.lineTo(-12, -4); cr.lineTo(0, -24); cr.lineTo(12, -4); cr.lineTo(30, -18); cr.lineTo(26, 10); cr.close()
        c.drawPath(cr, paint(hexc(BEE))); c.restore()
    c.restore()

def scene_speak(c, t, L):
    if not (9.1 < t < 12.0): return
    a = sstep(9.15, 9.45, t) * (1 - sstep(11.45, 11.85, t)); group_alpha(c, a)
    bx, by = L["bubble"]; e = ease_out((t - 9.2) / 0.45)
    c.save(); c.translate(bx, by + (1 - e) * 50)
    block(c, 0, 0, 840, 210, 36, hexc(CARD), hexc(CARD_LIP), lip_h=10, border=hexc(CARD_LIP))
    tail = skia.Path(); tail.moveTo(-40, 100); tail.lineTo(0, 150); tail.lineTo(30, 100); tail.close(); c.drawPath(tail, paint(hexc(CARD)))
    c.drawCircle(-330, 0, 56, paint(hexc(BEETLE))); text(c, "L", -330, 0, 56, hexc("#FFFFFF"), 900)
    text(c, "¿Dónde está la estación?", -250, -26, 44, hexc(TXT), 900, "l"); text(c, "Onde fica a estação?", -250, 38, 30, hexc(SUB), 800, "l")
    c.restore()
    mx, my = L["mic"]; pulse = 1 + 0.06 * math.sin(t * 12) * sstep(9.5, 9.7, t)
    c.drawCircle(mx, my, 120 * pulse, paint(hexc(MACAW, .25), blur=30))
    c.save(); c.translate(mx, my); c.scale(pulse, pulse)
    block(c, 0, 0, 150, 150, 75, hexc(MACAW), hexc("#1899D6"), lip_h=10)
    c.drawRRect(rr(0, -14, 34, 60, 17), paint(hexc("#FFFFFF")))
    arc = skia.Path(); arc.addArc(skia.Rect.MakeLTRB(-30, -40, 30, 26), 20, 140); c.drawPath(arc, paint(hexc("#FFFFFF"), stroke=6)); c.drawLine(0, 26, 0, 40, paint(hexc("#FFFFFF"), stroke=6))
    c.restore(); c.restore()

def waveform(c, t):
    """the trail between x 5000..6050 becomes a live waveform driven by the narration"""
    w = sstep(EV["wave_start"] - 0.2, EV["wave_start"] + 0.2, t) * (1 - sstep(EV["wave_end"], EV["wave_end"] + 0.5, t))
    if w <= 0: return
    for x in np.arange(5030, 6050, 22):
        lag = (x - 5030) / 900; amp = voice_env(t - lag * 0.35)
        h = 26 + w * (amp * 230 + 18 * math.sin(x * 0.05 + t * 9) ** 2)
        col = hexc(MACAW) if (x - 5030) / 1020 < sstep(EV["wave_start"], EV["wave_end"], t) else hexc(GREEN)
        c.drawRRect(rr(x, 0, 14, h, 7), paint(col))

STATIONS = [("Línguas", GREEN, GREEN_LIP, "¡Hola!"), ("Matemática", MACAW, "#1899D6", "7×8"), ("Música", BEETLE, "#A568CC", "♪♫"), ("Xadrez", FOX, "#CC7900", "♞")]
KEYS = ["station_languages", "station_numbers", "station_music", "station_chess"]
def scene_skills(c, t, L):
    if t < 11.4: return
    conv = ease_io((t - EV["converge"]) / 0.7)
    for i, (name, col, lip, glyph) in enumerate(STATIONS):
        sx, sy = L["stations"][i]; t0 = EV[KEYS[i]]
        br = curve(HUB, (sx - 150, sy), 0.45)
        fade = 1 - sstep(14.95, 15.3, t)
        draw_trail_pts(c, partial(br, (t - (t0 - 0.45)) / 0.45), 22, base=col, hi="#FFFFFF", glow=.3, alpha=fade)
        if conv > 0: draw_trail_pts(c, partial(curve((sx + 150, sy), F, 0.5), conv), 22, base=col, hi="#FFFFFF", glow=.3, alpha=fade)
        k = appear(t, t0, 0.4) * (1 - sstep(15.0, 15.5, t))
        if k <= 0.01: continue
        c.save(); c.translate(sx, sy); c.scale(k, k)
        c.drawCircle(0, 0, 200, paint(hexc(col, .15), blur=50))
        block(c, 0, -20, 300, 190, 40, hexc(col), hexc(lip), lip_h=12)
        tf = SYMB if glyph in ("♪♫", "♞") else None
        text(c, glyph, 0, -24, 130 if glyph == "♞" else (96 if tf else 72), hexc("#FFFFFF"), 900, typeface=tf)
        text(c, name, 0, 120, 44 * L["txt"], hexc(TXT), 900); c.restore()

def scene_resolve(c, t, L):
    if t < 14.6: return
    gx, gy = F; g = sstep(14.9, 15.3, t) * (1 - sstep(17.0, 17.5, t))
    c.drawCircle(gx, gy, 140 * g, paint(hexc(GREEN, .35 * g), blur=50))
    m1, m2 = L["msg"]; up = ease_io((t - 17.0) / 0.5)
    for (mx, my), s, t0, col in ((m1, "Pequenos passos.", EV["msg_1"], TXT), (m2, "Mais possibilidades.", EV["msg_2"], GREEN)):
        k = ease_out((t - t0) / 0.45); a = k * (1 - up)
        if a <= 0: continue
        group_alpha(c, a); text(c, s, mx, my + (1 - k) * 40 - up * 120, L["msg_size"], hexc(col), 900); c.restore()
    if t > EV["duo_land"] - 0.4:
        u = t - EV["duo_land"]
        if u < 0: y = lerp(-900, 0, ease_in((u + 0.4) / 0.4)); sq = -0.2
        else: y = -abs(math.sin(u * 7)) * 60 * math.exp(-u * 4); sq = 0.8 * math.exp(-u * 9) * math.cos(u * 22)
        wing = 30 * max(0, math.sin(clamp((u - 0.5) / 0.7) * math.pi * 2))
        blink = 1 - abs(math.cos(clamp((t - 18.25) / 0.16) * math.pi)) if 18.25 < t < 18.41 else 0
        duo(c, gx, gy - 120 + y, 0.7, t, squash=sq, wing=(wing, wing), look=(0, 0.3), blink=blink)
        wm = sstep(EV["wordmark"], EV["wordmark"] + 0.45, t); ww = wordmark(c, gx, gy + 190, 130, reveal=wm)
        draw_trail_pts(c, partial(curve((gx - ww / 2, gy + 290), (gx + ww / 2, gy + 290), 0.5), wm), 16)

# ---------------- screen-space layers ----------------
def background(c, W, H, cam, t):
    c.clear(hexc(BG))
    cx, cy, z = cam; step = 90
    p = paint(hexc("#16222A"))
    ox, oy = (-cx * z * 0.5) % step, (-cy * z * 0.5) % step
    for x in np.arange(ox - step, W + step, step):
        for y in np.arange(oy - step, H + step, step): c.drawCircle(x, y, 2.4, p)
    c.drawRect(skia.Rect.MakeWH(W, H), paint(hexc(BG), shader=skia.GradientShader.MakeRadial(skia.Point(W / 2, H / 2), max(W, H) * 0.75, [hexc(BG, 0), hexc("#05080A", .85)])))
    c.drawCircle(W / 2, H * 0.55, min(W, H) * 0.45, paint(hexc(GREEN, .045), blur=120))

def endcard(c, W, H, t, orient):
    k = sstep(EV["to_endcard"], 19.0, t)
    if k <= 0: return
    r = math.hypot(W, H) * ease_io(k)
    c.drawCircle(W / 2, H / 2, r, paint(hexc("#0E1519")))
    c.drawCircle(W / 2, H / 2, r, paint(hexc(GREEN, .9), stroke=10))
    if t < 19.0: return
    u = t - 19.0; cy = H * (0.4 if orient == "L" else 0.42); s = 1.0 if orient == "L" else 1.2
    c.drawCircle(W / 2, cy, 210 * s, paint(hexc(GREEN, .12), blur=60))
    c.drawCircle(W / 2, cy, 120 * s, paint(hexc("#1E3A12")))
    ring = skia.Path(); ring.addArc(skia.Rect.MakeLTRB(W / 2 - 132 * s, cy - 132 * s, W / 2 + 132 * s, cy + 132 * s), -90, 360 * ease_out(u / 0.5) - 0.01)
    c.drawPath(ring, paint(hexc(GREEN), stroke=14 * s))
    text(c, AVATAR_INITIALS, W / 2, cy, 96 * s, hexc(TXT), 900)
    a = ease_out((u - 0.1) / 0.4); group_alpha(c, a)
    text(c, NAME, W / 2, cy + 225 * s + (1 - a) * 20, 76 * s, hexc(TXT), 900)
    text(c, HANDLE, W / 2, cy + 305 * s + (1 - a) * 20, 40 * s, hexc(GREEN), 800)
    text(c, "Conceito independente · sem afiliação à Duolingo", W / 2, cy + 385 * s, 26 * s, hexc(SUB), 800)
    c.restore()

# ---------------- frame ----------------
class Renderer:
    def __init__(self, orient, scale):
        self.o = orient; self.L = layout(orient); self.scale = scale
        self.W, self.H = (1920, 1080) if orient == "L" else (1080, 1920)
        self.surf = skia.Surface(int(self.W * scale), int(self.H * scale))
        cam = self.L["cam"]; self.cx, self.cy, self.cz = (monotone([(k[0], k[i]) for k in cam]) for i in (1, 2, 3))
    def cam(self, t): return self.cx(t), self.cy(t), self.cz(t)
    def draw(self, t):
        c = self.surf.getCanvas(); c.save(); c.scale(self.scale, self.scale)
        W, H = self.W, self.H; cam = self.cam(t); background(c, W, H, cam, t)
        cx, cy, z = cam
        c.save(); c.translate(W / 2, H / 2); c.scale(z, z); c.translate(-cx, -cy)
        L = self.L; s_head = HEAD(t)
        if s_head > 0:
            n = int(np.searchsorted(TRAIL_S, s_head)); pts = [tuple(p) for p in TRAIL[:n]] + [tuple(trail_at(s_head))]
            fade = 1 - sstep(14.95, 15.3, t)
            if fade > 0:
                draw_trail_pts(c, pts, alpha=fade)
                hx, hy = pts[-1]; c.drawCircle(hx, hy, 34, paint(hexc(MASK, .5 * fade), blur=16)); c.drawCircle(hx, hy, 15, paint(hexc("#EFFFD9", fade)))
        scene_nodes(c, t, L); waveform(c, t)
        scene_intro(c, t, L); scene_lesson(c, t, L); scene_streak(c, t, L); scene_league(c, t, L); scene_speak(c, t, L)
        scene_skills(c, t, L); scene_resolve(c, t, L)
        c.restore()
        endcard(c, W, H, t, self.o)
        c.restore()
        return self.surf.makeImageSnapshot().toarray()
    def frame(self, t, fps):
        # camera-aware motion blur: average sub-frames when the camera moves fast
        dt = 1 / fps; a, b = np.array(self.cam(t - dt / 2)), np.array(self.cam(t + dt / 2))
        speed = math.hypot(*(b[:2] - a[:2])) * a[2] + abs(b[2] - a[2]) * 2000
        n = 1 if speed < 4 else int(min(12, 3 + speed / 6))
        if n == 1: return self.draw(t)
        acc = sum(self.draw(t + dt * (k / n - 0.5)).astype(np.float32) for k in range(n)); return (acc / n).astype(np.uint8)

if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--orient", default="L"); ap.add_argument("--scale", type=float, default=1.0); ap.add_argument("--fps", type=int, default=FPS)
    ap.add_argument("--out", required=True); ap.add_argument("--audio", default=f"{ROOT}/audio/mix.wav"); ap.add_argument("--still", type=float, nargs="*")
    a = ap.parse_args(); R = Renderer(a.orient, a.scale)
    if a.still:
        import cv2
        for t in a.still: cv2.imwrite(a.out.replace(".png", f"_{t:05.2f}.png"), R.draw(t)[:, :, :3])
        sys.exit()
    w, h = R.surf.width(), R.surf.height()
    cmd = ["ffmpeg", "-y", "-loglevel", "error", "-f", "rawvideo", "-pix_fmt", "bgra", "-s", f"{w}x{h}", "-r", str(a.fps), "-i", "-"]
    if os.path.exists(a.audio): cmd += ["-i", a.audio, "-c:a", "aac", "-b:a", "192k", "-shortest"]
    cmd += ["-c:v", "libx264", "-preset", "medium", "-crf", "17", "-pix_fmt", "yuv420p", "-movflags", "+faststart", a.out]
    ff = subprocess.Popen(cmd, stdin=subprocess.PIPE)
    N = int(DURATION * a.fps)
    for f in range(N):
        ff.stdin.write(R.frame(f / a.fps, a.fps).tobytes())
        if f % (a.fps * 2) == 0: print(f"{f / a.fps:5.1f}s", flush=True)
    ff.stdin.close(); ff.wait(); print("done", a.out)
