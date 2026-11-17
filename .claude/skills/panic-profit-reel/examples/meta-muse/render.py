"""Meta Muse spec film renderer (independent educational concept, not affiliated with Meta).

Draws every frame with Skia (vector 2D) and pipes raw frames to FFmpeg.
  python3 code/render.py --orient L --out exports/muse_spec_PT_1920x1080.mp4
  python3 code/render.py --orient V --scale 0.5 --fps 30 --out previews/rough_V.mp4
  python3 code/render.py --orient L --scale 0.5 --out previews/s.png --still 3.6 8.0
"""
import argparse, math, os, subprocess, sys
import numpy as np, skia
sys.path.insert(0, os.path.dirname(__file__))
from timing import FPS, DURATION, EVENTS as EV, NAME, HANDLE, AVATAR_INITIALS

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
FONT = {"display": skia.Typeface.MakeFromFile(f"{ROOT}/assets/fonts/InterDisplay-Bold.otf"),
        "bold": skia.Typeface.MakeFromFile(f"{ROOT}/assets/fonts/Inter-Bold.otf"),
        "semi": skia.Typeface.MakeFromFile(f"{ROOT}/assets/fonts/Inter-SemiBold.otf"),
        "med": skia.Typeface.MakeFromFile(f"{ROOT}/assets/fonts/Inter-Medium.otf")}

def hexc(h, a=1.0):
    h = h.lstrip("#"); return skia.Color(int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16), int(max(0, min(1, a)) * 255))
BLUE, VIOLET, PINK, CYAN, WA = "#0064E0", "#3D8BFF", "#8EC5FF", "#5AB8FF", "#25D366"
BUBBLE, NAVY = "#DCE8FF", "#1C2B33"
BG, CARD, EDGE, TXT, SUB, OK = "#F4F7FC", "#FFFFFF", "#E3E8F0", "#1C2B33", "#65676B", "#31A24C"
GRAD = [BLUE, VIOLET, PINK, VIOLET, BLUE]

clamp = lambda x, a=0.0, b=1.0: max(a, min(b, x))
lerp = lambda a, b, t: a + (b - a) * t
def sstep(a, b, x): t = clamp((x - a) / (b - a)); return t * t * (3 - 2 * t)
def ease_out(t): t = clamp(t); return 1 - (1 - t) ** 3
def ease_in(t): t = clamp(t); return t ** 3
def ease_io(t): t = clamp(t); return 4 * t ** 3 if t < .5 else 1 - (-2 * t + 2) ** 3 / 2
def back_out(t, c=1.7): t = clamp(t); return 1 + (c + 1) * (t - 1) ** 3 + c * (t - 1) ** 2
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
            t = k / per; out.append(0.5 * ((2 * p1) + (-p0 + p2) * t + (2 * p0 - 5 * p1 + 4 * p2 - p3) * t * t + (-p0 + 3 * p1 - 3 * p2 + p3) * t ** 3))
    out.append(np.array(pts[-1], float)); out = np.array(out)
    return out, np.concatenate([[0], np.cumsum(np.linalg.norm(np.diff(out, axis=0), axis=1))])

# ---------------- world ----------------
P1, TR, EM, SH, BGP, MEM, HUB, F = (1700, 0), (2950, 0), (4150, 0), (5350, 0), (6550, 0), (7750, 0), (8850, 0), (10400, 0)
MAIN = [(-300, 0), (60, 250), (420, 250), (800, 120), (1150, 0), (1700, 0), (2250, 0), (2600, 160), (2950, 200), (3350, 120), (3650, 0),
        (4150, 0), (4650, 0), (5000, -120), (5350, -170), (5700, -60), (5950, 0), (6250, 260), (6550, 330), (6850, 260), (6950, 0),
        (6850, -280), (6550, -340), (6280, -200), (6400, 0), (7100, 40), (7750, 0), (8300, 0), HUB]
TRAIL, TRAIL_S = catmull(MAIN)
def s_near(p): return float(TRAIL_S[np.argmin(np.linalg.norm(TRAIL - np.array(p), axis=1))])
def trail_at(s):
    i = int(np.clip(np.searchsorted(TRAIL_S, s), 1, len(TRAIL) - 1)); a, b = TRAIL[i - 1], TRAIL[i]
    u = (s - TRAIL_S[i - 1]) / max(1e-6, TRAIL_S[i] - TRAIL_S[i - 1]); return a + (b - a) * clamp(u)
HEAD = monotone([(0.0, 0), (0.35, 0), (1.25, s_near((800, 120))), (2.9, s_near((2250, 0))), (4.8, s_near((3650, 0))),
                 (6.4, s_near((4650, 0))), (7.0, s_near((5000, -120))), (9.1, s_near((5950, 0))), (11.3, s_near((6400, 0))),
                 (13.0, s_near((8300, 0))), (13.35, TRAIL_S[-1]), (DURATION, TRAIL_S[-1])])

def layout(o):
    if o == "L":
        cam = [(0, 0, 40, 1.0), (1.3, 120, 40, 1.0), (1.85, 1700, 0, 1.0), (2.85, 1720, 0, 1.03), (3.35, 2950, 0, 1.0), (4.85, 2960, 0, 1.04),
               (5.35, 4150, 0, 1.0), (7.0, 4160, 0, 1.04), (7.55, 5350, 0, 1.0), (9.1, 5360, 0, 1.04), (9.6, 6650, 0, 1.0), (11.3, 6660, 0, 1.03),
               (11.8, 7750, 0, 1.0), (13.0, 7760, 0, 1.03), (13.55, 9300, 0, 0.9), (15.55, 9380, 0, 0.86), (16.25, 10400, 0, 1.0), (19.45, 10400, 0, 1.06)]
        st = [(9600, -435), (9600, -145), (9600, 145), (9600, 435)]
        return dict(cam=cam, st=st, wm=(260, 0), orb=(-300, 0), tasks=(BGP[0] + 520, BGP[1]), msg=[(F[0], -40), (F[0], 80)], msg_size=128,
                    suggest=(MEM[0] + 420, MEM[1] + 40), cards=(TR[0] - 230, TR[0] + 230), txt=1.0)
    cam = [(0, 0, 40, 0.9), (1.3, 0, 40, 0.9), (1.85, 1700, 0, 1.0), (2.85, 1700, 0, 1.03), (3.35, 2950, 0, 1.0), (4.85, 2950, 0, 1.04),
           (5.35, 4150, 0, 1.0), (7.0, 4150, 0, 1.04), (7.55, 5350, 0, 1.0), (9.1, 5350, 0, 1.04), (9.6, 6550, 150, 1.0), (11.3, 6550, 150, 1.03),
           (11.8, 7750, 120, 1.0), (13.0, 7750, 120, 1.03), (13.55, 9250, 0, 0.8), (15.55, 9300, 0, 0.78), (16.25, 10400, 0, 1.0), (19.45, 10400, 0, 1.05)]
    st = [(9450, -660), (9450, -220), (9450, 220), (9450, 660)]
    return dict(cam=cam, st=st, wm=(20, 70), orb=(0, -280), tasks=(BGP[0], BGP[1] + 560), msg=[(F[0], -50), (F[0], 60)], msg_size=104,
                suggest=(MEM[0], MEM[1] + 470), cards=(TR[0], TR[0]), txt=1.1)

# ---------------- drawing helpers ----------------
def paint(color, stroke=None, blur=0, shader=None):
    p = skia.Paint(AntiAlias=True, Color=color)
    if stroke: p.setStyle(skia.Paint.kStroke_Style); p.setStrokeWidth(stroke); p.setStrokeCap(skia.Paint.kRound_Cap); p.setStrokeJoin(skia.Paint.kRound_Join)
    if blur > 0: p.setMaskFilter(skia.MaskFilter.MakeBlur(skia.kNormal_BlurStyle, blur))
    if shader is not None: p.setShader(shader)
    return p
def text(c, s, x, y, size, color, face="bold", align="c", shader=None):
    f = skia.Font(FONT[face], size); w = f.measureText(s); dx = {"c": -w / 2, "l": 0, "r": -w}[align]
    c.drawString(s, x + dx, y + size * 0.36, f, paint(color, shader=shader)); return w
def text_w(s, size, face="bold"): return skia.Font(FONT[face], size).measureText(s)
def rr(x, y, w, h, r): return skia.RRect.MakeRectXY(skia.Rect.MakeXYWH(x - w / 2, y - h / 2, w, h), r, r)
def grad_lin(x0, period=1400, phase=0.0):
    return skia.GradientShader.MakeLinear([skia.Point(x0 + phase, 0), skia.Point(x0 + phase + period, 0)], [hexc(c) for c in GRAD], None, skia.TileMode.kRepeat)
def card(c, x, y, w, h, r=30, glow=0.0):
    c.drawRRect(rr(x, y + 16, w, h, r), paint(hexc("#1C3B6E", .13), blur=30))
    if glow: c.drawRRect(rr(x, y, w + 8, h + 8, r + 4), paint(hexc(VIOLET, .30 * glow), blur=22))
    c.drawRRect(rr(x, y, w, h, r), paint(hexc(CARD)))
    c.drawRRect(rr(x, y, w, h, r), paint(hexc("#FFFFFF", .04), shader=skia.GradientShader.MakeLinear([skia.Point(x, y - h / 2), skia.Point(x, y + h / 2)], [hexc("#FFFFFF", .06), hexc("#FFFFFF", 0)])))
    c.drawRRect(rr(x, y, w - 2, h - 2, r), paint(hexc(EDGE), stroke=2))
def group_alpha(c, a): c.saveLayerAlpha(None, int(clamp(a) * 255))
def check(c, x, y, r, a=1.0, col=OK):
    c.drawCircle(x, y, r, paint(hexc(col, a))); p = skia.Path(); p.moveTo(x - r * .42, y); p.lineTo(x - r * .1, y + r * .32); p.lineTo(x + r * .45, y - r * .32)
    c.drawPath(p, paint(hexc("#FFFFFF", a), stroke=r * .22))
def chip(c, x, y, label, done, t0, t, w=None):
    k = appear(t, t0 - 0.35, 0.35)
    if k <= 0.01: return
    w = w or text_w(label, 30, "semi") + 120; c.save(); c.translate(x, y); c.scale(k, k)
    c.drawRRect(rr(0, 0, w, 72, 36), paint(hexc(CARD))); c.drawRRect(rr(0, 0, w - 2, 70, 36), paint(hexc(EDGE), stroke=2))
    if done: check(c, -w / 2 + 40, 0, 18, ease_out((t - t0) / .25))
    else:
        arc = skia.Path(); arc.addArc(skia.Rect.MakeLTRB(-w / 2 + 24, -16, -w / 2 + 56, 16), (t * 500) % 360, 270); c.drawPath(arc, paint(hexc(SUB), stroke=4))
    text(c, label, -w / 2 + 72, 0, 30, hexc(TXT), "semi", "l"); c.restore()

# ---------------- Muse avatar (assistant presence) ----------------
def orb(c, x, y, r, t, a=1.0, energy=1.0):
    if a <= 0 or r <= 0: return
    c.drawCircle(x, y, r * 1.9, paint(hexc(VIOLET, .16 * a * energy), blur=r * .8))
    if energy > 1.05:  # thinking ring
        c.save(); c.translate(x, y); c.rotate((t * 160) % 360)
        arc = skia.Path(); arc.addArc(skia.Rect.MakeLTRB(-r * 1.35, -r * 1.35, r * 1.35, r * 1.35), 0, 250)
        c.drawPath(arc, paint(hexc(BLUE, .6 * a * min(1, energy - 1)), stroke=r * .07, shader=grad_lin(-r, r * 3))); c.restore()
    c.save(); c.translate(x, y); c.scale(r, r); bob = 0.03 * math.sin(t * 3); c.translate(0, bob)
    body = skia.Path(); body.moveTo(-.82, .78); body.cubicTo(-.95, -.15, -.62, -1.0, 0, -1.0); body.cubicTo(.62, -1.0, .95, -.15, .82, .78)
    body.cubicTo(.5, .95, -.5, .95, -.82, .78); body.close()
    c.drawPath(body, paint(hexc("#1C3B6E", .14 * a), blur=.12) if False else paint(hexc("#1C3B6E", .12 * a), blur=.1))
    c.drawPath(body, paint(hexc("#E9DDC9", a), shader=skia.GradientShader.MakeLinear([skia.Point(-.5, -1), skia.Point(.5, .9)], [hexc("#F6EEE1", a), hexc("#D8C6A8", a)])))
    blink = 0.12 if (t % 3.1) < 0.12 else 1.0
    for sx in (-1, 1):
        c.save(); c.translate(sx * .26, -.12); c.scale(1, blink); c.drawOval(skia.Rect.MakeLTRB(-.075, -.11, .075, .11), paint(hexc("#3A3026", a))); c.restore()
        c.drawCircle(sx * .46, .12, .13, paint(hexc("#F0B49B", .35 * a), blur=.05))
    c.drawOval(skia.Rect.MakeLTRB(-.5, -.88, -.12, -.6), paint(hexc("#FFFFFF", .55 * a), blur=.06))
    c.restore()

# ---------------- ribbon ----------------
def poly_path(pts):
    p = skia.Path(); p.moveTo(*pts[0])
    for q in pts[1:]: p.lineTo(*q)
    return p
def ribbon(c, pts, t, width=18, alpha=1.0, solid=None):
    if len(pts) < 2: return
    p = poly_path(pts); x0 = min(q[0] for q in pts)
    sh = grad_lin(-2000, phase=-t * 260) if solid is None else None
    col = hexc(solid or BLUE, alpha)
    g = paint(col, stroke=width * 2.2, blur=16, shader=sh) if sh else paint(hexc(solid), stroke=width * 2.2, blur=16); g.setAlphaf(.28 * alpha); c.drawPath(p, g)
    q = paint(col, stroke=width, shader=sh); q.setAlphaf(alpha); c.drawPath(p, q)
    c.drawPath(poly_path([(a, b - width * .18) for a, b in pts]), paint(hexc("#FFFFFF", .35 * alpha), stroke=width * .22))
def curve(a, b, bend=0.5, n=60):
    (x0, y0), (x1, y1) = a, b; mx = lerp(x0, x1, bend)
    return [((1 - u) ** 3 * x0 + 3 * (1 - u) ** 2 * u * mx + 3 * (1 - u) * u * u * mx + u ** 3 * x1,
             (1 - u) ** 3 * y0 + 3 * (1 - u) ** 2 * u * y0 + 3 * (1 - u) * u * u * y1 + u ** 3 * y1) for u in np.linspace(0, 1, n)]
def partial(pts, frac): n = max(2, int(len(pts) * clamp(frac))); return pts[:n] if frac > 0 else []

# ---------------- icons ----------------
def icon(c, kind, x, y, s, col="#FFFFFF"):
    p = paint(hexc(col), stroke=s * .11); f = paint(hexc(col))
    if kind == "plane":
        q = skia.Path(); q.moveTo(x - s * .5, y + s * .05); q.lineTo(x + s * .5, y - s * .35); q.lineTo(x + s * .1, y + s * .45); q.lineTo(x - s * .05, y + s * .1); q.close(); c.drawPath(q, f)
    elif kind == "bed":
        c.drawRRect(rr(x, y + s * .12, s, s * .3, s * .06), f); c.drawRRect(rr(x - s * .25, y - s * .12, s * .38, s * .22, s * .08), f)
        c.drawLine(x - s * .5, y + s * .25, x - s * .5, y + s * .42, p); c.drawLine(x + s * .5, y + s * .25, x + s * .5, y + s * .42, p)
    elif kind == "mail":
        c.drawRRect(rr(x, y, s, s * .7, s * .1), p); q = skia.Path(); q.moveTo(x - s * .45, y - s * .27); q.lineTo(x, y + s * .08); q.lineTo(x + s * .45, y - s * .27); c.drawPath(q, p)
    elif kind == "bag":
        c.drawRRect(rr(x, y + s * .1, s * .8, s * .7, s * .1), f); arc = skia.Path(); arc.addArc(skia.Rect.MakeLTRB(x - s * .22, y - s * .5, x + s * .22, y - s * .02), 180, 180); c.drawPath(arc, p)
    elif kind == "lock":
        c.drawRRect(rr(x, y + s * .15, s * .7, s * .55, s * .1), f); arc = skia.Path(); arc.addArc(skia.Rect.MakeLTRB(x - s * .22, y - s * .45, x + s * .22, y + s * .05), 180, 180); c.drawPath(arc, p)
    elif kind == "phone":
        c.drawRRect(rr(x, y, s * .58, s, s * .12), p); c.drawLine(x - s * .08, y + s * .38, x + s * .08, y + s * .38, p)
    elif kind == "chat":
        q = skia.Path(); q.addCircle(x, y - s * .05, s * .42); c.drawPath(q, p); t = skia.Path(); t.moveTo(x - s * .3, y + s * .25); t.lineTo(x - s * .42, y + s * .45); t.lineTo(x - s * .1, y + s * .35); c.drawPath(t, f)
        r = skia.Path(); r.moveTo(x - s * .14, y - s * .2); r.quadTo(x - s * .2, y + s * .08, x + s * .12, y + s * .14); c.drawPath(r, p)
    elif kind == "globe":
        c.drawCircle(x, y, s * .45, p); c.drawOval(skia.Rect.MakeLTRB(x - s * .2, y - s * .45, x + s * .2, y + s * .45), p); c.drawLine(x - s * .45, y, x + s * .45, y, p)
    elif kind == "laptop":
        c.drawRRect(rr(x, y - s * .08, s * .78, s * .5, s * .06), p); c.drawLine(x - s * .5, y + s * .27, x + s * .5, y + s * .27, p)
    elif kind == "glasses":
        for sx in (-1, 1): c.drawRRect(rr(x + sx * s * .26, y, s * .42, s * .32, s * .12), p)
        c.drawLine(x - s * .05, y - s * .04, x + s * .05, y - s * .04, p)
    elif kind == "send":
        q = skia.Path(); q.moveTo(x - s * .4, y - s * .4); q.lineTo(x + s * .45, y); q.lineTo(x - s * .4, y + s * .4); q.lineTo(x - s * .2, y); q.close(); c.drawPath(q, f)

# ---------------- scenes ----------------
def scene_intro(c, t, L):
    a = 1 - sstep(2.1, 2.5, t)
    if a <= 0: return
    ox, oy = L["orb"]; r = 120 * back_out(t / 0.55) * (1 + 0.04 * math.sin(t * 6))
    orb(c, ox, oy, r, t, a, energy=1 + 1.5 * math.exp(-t * 3))
    wx, wy = L["wm"]; size = 190; w = text_w("Muse", size, "display"); rev = sstep(0.45, 1.15, t)
    c.save(); c.clipRect(skia.Rect.MakeLTRB(wx - w / 2 - 20, wy - size, wx - w / 2 - 20 + (w + 40) * rev, wy + size))
    group_alpha(c, a); text(c, "Muse", wx, wy, size, hexc(TXT), "display"); text(c, "da Meta", wx, wy + 128, 40, hexc(SUB), "semi"); c.restore(); c.restore()

PROMPT = "Planeia um fim de semana em Lisboa"
def scene_prompt(c, t, L):
    if not (1.3 < t < 3.6): return
    a = sstep(1.35, 1.65, t) * (1 - sstep(3.1, 3.5, t)); group_alpha(c, a)
    x, y = P1; e = ease_out((t - 1.35) / 0.45); c.save(); c.translate(0, (1 - e) * 60)
    n = int(len(PROMPT) * clamp((t - EV["type_start"]) / (EV["type_end"] - EV["type_start"])))
    sent = sstep(EV["send"], EV["send"] + 0.25, t)
    # composer
    card(c, x, y + 30, 900, 120, 60, glow=1 - sent)
    orb(c, x - 390, y + 30, 26, t, 1.0, 0.4)
    if sent < 1: text(c, PROMPT[:n] + ("|" if (t * 2.5) % 1 < 0.6 and sent == 0 else ""), x - 340, y + 30, 38, hexc(TXT, 1 - sent), "semi", "l")
    press = 1 - 0.12 * sstep(EV["send"] - 0.08, EV["send"], t) * (1 - sstep(EV["send"] + 0.05, EV["send"] + 0.18, t))
    c.save(); c.translate(x + 390, y + 30); c.scale(press, press); c.drawCircle(0, 0, 38, paint(hexc(BLUE), shader=grad_lin(-40, 80)))
    icon(c, "send", 2, 0, 34); c.restore()
    if sent > 0:  # message bubble rises
        bw = text_w(PROMPT, 36, "semi") + 70; by = y + 30 - 170 * ease_out((t - EV["send"]) / 0.4)
        c.drawRRect(rr(x + 450 - bw / 2, by, bw, 92, 46), paint(hexc(BUBBLE)))
        text(c, PROMPT, x + 450 - bw / 2, by, 36, hexc(NAVY), "semi")
    c.restore(); c.restore()

def booking(c, x, y, ic, title, sub, ok_t, t, col):
    card(c, x, y, 420, 300, 32)
    c.drawCircle(x - 140, y - 80, 44, paint(hexc(col, .18))); icon(c, ic, x - 140, y - 80, 52, col)
    text(c, title, x - 180, y + 10, 36, hexc(TXT), "bold", "l"); text(c, sub, x - 180, y + 58, 26, hexc(SUB), "med", "l")
    done = t >= ok_t; lab = "Confirmado" if done else "A reservar…"
    c.drawRRect(rr(x - 70, y + 112, 220, 50, 25), paint(hexc(OK if done else EDGE, .2 if done else 1)))
    if done: check(c, x - 152, y + 112, 14, ease_out((t - ok_t) / .2))
    else: arc = skia.Path(); arc.addArc(skia.Rect.MakeLTRB(x - 166, y + 100, x - 142, y + 124), (t * 500) % 360, 270); c.drawPath(arc, paint(hexc(SUB), stroke=3))
    text(c, lab, x - 130, y + 112, 24, hexc(OK if done else SUB), "semi", "l")
def scene_travel(c, t, L):
    if not (2.9 < t < 5.6): return
    a = sstep(2.95, 3.25, t) * (1 - sstep(5.1, 5.5, t)); group_alpha(c, a)
    x1, x2 = L["cards"]; vert = L["cards"][0] == L["cards"][1]
    k1 = appear(t, 3.05, 0.4); k2 = appear(t, 3.3, 0.4)
    y1, y2 = (-185, 185) if vert else (0, 0)
    c.save(); c.translate(x1, TR[1] + y1); c.scale(k1, k1); booking(c, 0, 0, "plane", "Voo para Lisboa", "Sex · 18:40 · janela", EV["flight_ok"], t, CYAN); c.restore()
    c.save(); c.translate(x2, TR[1] + y2); c.scale(k2, k2); booking(c, 0, 0, "bed", "Hotel em Alfama", "2 noites · vista rio", EV["hotel_ok"], t, BLUE); c.restore()
    c.restore()

def scene_email(c, t, L):
    if not (4.9 < t < 7.8): return
    a = sstep(4.95, 5.25, t) * (1 - sstep(7.25, 7.65, t)); group_alpha(c, a)
    x, y = EM; fly = ease_in((t - EV["email_send"]) / 0.6)
    c.save(); c.translate(x + fly * 900, y - fly * 260); c.rotate(-12 * fly); c.scale(1 - .75 * fly, 1 - .75 * fly)
    card(c, 0, 0, 780, 470, 32)
    text(c, "Nova mensagem", -340, -190, 34, hexc(TXT), "bold", "l"); icon(c, "mail", 320, -190, 46, BLUE)
    c.drawLine(-350, -140, 350, -140, paint(hexc(EDGE), stroke=2))
    text(c, "Para:  Marta", -340, -100, 30, hexc(SUB), "med", "l")
    text(c, "Assunto:  Fim de semana em Lisboa", -340, -50, 30, hexc(TXT), "semi", "l")
    body = ["Já está tudo marcado: voo sexta às 18:40", "e hotel em Alfama. Jantar sábado às 20h?"]
    shown = clamp((t - 5.15) / 0.55)
    for i, ln in enumerate(body):
        k = int(len(ln) * clamp(shown * 2 - i)); text(c, ln[:k], -340, 20 + i * 48, 30, hexc(TXT), "med", "l")
    press = sstep(EV["email_send"] - .08, EV["email_send"], t) * (1 - sstep(EV["email_send"] + .05, EV["email_send"] + .15, t))
    c.save(); c.translate(250, 170); c.scale(1 - .08 * press, 1 - .08 * press)
    c.drawRRect(rr(0, 0, 200, 70, 35), paint(hexc(BLUE), shader=grad_lin(-100, 300))); text(c, "Enviar", 0, 0, 30, hexc("#FFFFFF"), "bold"); c.restore()
    c.restore()
    if t > EV["email_sent"] - 0.1: chip(c, x, y + 20, "Email enviado", True, EV["email_sent"], t)
    c.restore()

def scene_shop(c, t, L):
    if not (7.1 < t < 9.9): return
    a = sstep(7.15, 7.45, t) * (1 - sstep(9.35, 9.75, t)); group_alpha(c, a)
    x, y = SH; k = appear(t, 7.25, 0.45); c.save(); c.translate(x, y); c.scale(k, k)
    card(c, 0, 0, 760, 520, 34)
    c.drawRRect(rr(-210, -60, 260, 260, 26), paint(hexc("#EEF3FB")))
    shoe = skia.Path(); shoe.moveTo(-320, 10); shoe.quadTo(-300, -70, -240, -80); shoe.lineTo(-200, -30); shoe.quadTo(-140, -10, -100, 20); shoe.quadTo(-90, 50, -130, 52); shoe.lineTo(-310, 52); shoe.close()
    c.drawPath(shoe, paint(hexc(PINK), shader=grad_lin(-400, 400))); c.drawLine(-318, 52, -100, 52, paint(hexc("#C9D6EA"), stroke=10))
    text(c, "Ténis de corrida", -40, -140, 36, hexc(TXT), "bold", "l"); text(c, "Tamanho 42 · entrega sábado", -40, -92, 26, hexc(SUB), "med", "l")
    text(c, "89,90 €", -40, -20, 54, hexc(TXT), "display", "l")
    paid = t >= EV["paid"]; press = sstep(EV["pay_press"] - .08, EV["pay_press"], t) * (1 - sstep(EV["pay_press"] + .05, EV["pay_press"] + .15, t))
    c.save(); c.translate(0, 170); c.scale(1 - .05 * press, 1 - .05 * press)
    c.drawRRect(rr(0, 0, 660, 90, 45), paint(hexc(OK if paid else BLUE), shader=None if paid else grad_lin(-400, 800)))
    if paid: check(c, -60, 0, 24, 1, "#0B2A19"); text(c, "Pago", -20, 0, 36, hexc("#0B2A19"), "bold", "l")
    else: icon(c, "lock", -205, -4, 36); text(c, "Pagar com segurança", 25, 0, 32, hexc("#FFFFFF"), "bold")
    c.restore(); c.restore(); c.restore()

def scene_background(c, t, L):
    if not (9.2 < t < 12.0): return
    a = sstep(9.25, 9.55, t) * (1 - sstep(11.5, 11.9, t)); group_alpha(c, a)
    x, y = BGP; k = appear(t, 9.3, 0.4); c.save(); c.translate(x, y); c.scale(k, k)
    c.drawRRect(rr(0, 16, 300, 600, 52), paint(hexc("#1C3B6E", .16), blur=30)); c.drawRRect(rr(0, 0, 300, 600, 52), paint(hexc(NAVY)))
    c.drawRRect(rr(0, 0, 296, 596, 50), paint(hexc("#3A4A55"), stroke=4))
    dim = sstep(EV["lock"] - .2, EV["lock"] + .2, t)
    c.drawRRect(rr(0, 0, 270, 570, 40), paint(hexc("#FFFFFF"))); c.drawRRect(rr(0, 0, 270, 570, 40), paint(hexc("#DCE6F5", dim * .9)))
    text(c, "21:47", 0, -170, 64, hexc(TXT, .3 + .7 * dim), "display"); icon(c, "lock", 0, -250, 34, SUB)
    orb(c, 0, 60, 40, t, .4 + .6 * dim, .6); text(c, "A trabalhar…", 0, 140, 24, hexc(SUB, dim), "semi")
    c.restore()
    tx, ty = L["tasks"]; lst = [("Comparar preços", EV["task_1"]), ("Reservar jantar", EV["task_2"]), ("Check-in online", EV["task_3"])]
    for i, (lab, t0) in enumerate(lst):
        chip(c, tx, ty - 110 + i * 110, lab, t >= t0, t0 - 0.3, t, w=440)
    c.restore()

MEMS = [("Prefere janela", -330, -230), ("Jantar às 20h", 340, -230), ("Adora fado", -360, 180)]
def scene_memory(c, t, L):
    if not (11.35 < t < 13.6): return
    a = sstep(11.4, 11.65, t) * (1 - sstep(13.1, 13.5, t)); group_alpha(c, a)
    x, y = MEM; orb(c, x, y, 95, t, 1.0, 1.2)
    for i, (lab, dx, dy) in enumerate(MEMS):
        k = appear(t, EV[f"mem_{i + 1}"], 0.4); fl = 8 * math.sin(t * 2 + i)
        if k <= 0.01: continue
        c.drawLine(x, y, x + dx * k, y + dy * k + fl, paint(hexc(VIOLET, .35), stroke=3))
        c.save(); c.translate(x + dx, y + dy + fl); c.scale(k, k)
        w = text_w(lab, 30, "semi") + 64; c.drawRRect(rr(0, 0, w, 66, 33), paint(hexc(CARD))); c.drawRRect(rr(0, 0, w - 2, 64, 33), paint(hexc(VIOLET, .7), stroke=2))
        text(c, lab, 0, 0, 30, hexc(TXT), "semi"); c.restore()
    sx, sy = L["suggest"]; k = ease_out((t - EV["suggest"]) / 0.4)
    if k > 0:
        c.save(); c.translate(sx, sy + (1 - k) * 40); group_alpha(c, k)
        card(c, 0, 0, 560, 170, 30, glow=.6)
        text(c, "Sugestão", -240, -45, 24, hexc(BLUE), "bold", "l"); text(c, "Fado no sábado às 21h?", -240, 2, 34, hexc(TXT), "bold", "l")
        c.drawRRect(rr(170, 52, 150, 50, 25), paint(hexc(BLUE), shader=grad_lin(0, 400))); text(c, "Reservar", 170, 52, 24, hexc("#FFFFFF"), "bold")
        c.restore(); c.restore()
    c.restore()

STATIONS = [("Telemóvel", BLUE, "phone", "st_app"), ("Mac", NAVY, "laptop", "st_mac"), ("WhatsApp", WA, "chat", "st_whatsapp"), ("Óculos", VIOLET, "glasses", "st_glasses")]
def scene_platforms(c, t, L):
    if t < 13.2: return
    conv = ease_io((t - EV["converge"]) / 0.6); fade = 1 - sstep(16.15, 16.55, t)
    for i, (name, col, ic, ev) in enumerate(STATIONS):
        sx, sy = L["st"][i]; t0 = EV[ev]
        ribbon(c, partial(curve(HUB, (sx - 140, sy), 0.45), (t - (t0 - 0.4)) / 0.4), t, 18, fade, solid=col)
        if conv > 0: ribbon(c, partial(curve((sx + 140, sy), F, 0.5), conv), t, 18, fade, solid=col)
        k = appear(t, t0, 0.4) * (1 - sstep(15.85, 16.25, t))
        if k <= 0.01: continue
        c.save(); c.translate(sx, sy); c.scale(k, k)
        c.drawCircle(0, 0, 190, paint(hexc(col, .14), blur=50)); card(c, 0, -10, 280, 190, 36)
        c.drawCircle(0, -30, 54, paint(hexc(col, .2))); icon(c, ic, 0, -30, 62, col)
        text(c, name, 0, 52, 34 * L["txt"], hexc(TXT), "bold")
        if name == "Óculos": text(c, "em breve", 0, 128, 24, hexc(SUB), "semi")
        c.restore()

def scene_resolve(c, t, L):
    if t < 15.65: return
    gx, gy = F; g = sstep(15.95, 16.35, t) * (1 - sstep(17.95, 18.35, t))
    c.drawCircle(gx, gy, 160 * g, paint(hexc(VIOLET, .3 * g), blur=60))
    up = ease_io((t - 18.0) / 0.45); size = L["msg_size"]
    for (mx, my), s, t0, white in ((L["msg"][0], "Menos tarefas.", EV["msg_1"], True), (L["msg"][1], "Mais tempo.", EV["msg_2"], False)):
        k = ease_out((t - t0) / 0.45); a = k * (1 - up)
        if a <= 0: continue
        w = text_w(s, size, "display"); group_alpha(c, a)
        text(c, s, mx, my + (1 - k) * 40 - up * 120, size, hexc(TXT), "display", shader=None if white else grad_lin(mx - w / 2, w * 1.2, phase=-t * 200))
        c.restore()
    b = t - EV["brand"]
    if b > -0.1:
        r = 130 * back_out((b + 0.1) / 0.5) * (1 + 0.03 * math.sin(t * 5)); orb(c, gx, gy - 140, r, t, clamp((b + .1) / .2), 1 + math.exp(-max(0, b) * 3))
        size2 = 170; w = text_w("Muse", size2, "display"); rev = sstep(EV["brand"] + .15, EV["brand"] + .7, t)
        c.save(); c.clipRect(skia.Rect.MakeLTRB(gx - w / 2 - 20, gy, gx - w / 2 - 20 + (w + 40) * rev, gy + 400))
        text(c, "Muse", gx, gy + 110, size2, hexc(TXT), "display"); text(c, "da Meta", gx, gy + 225, 40, hexc(SUB), "semi"); c.restore()
        ribbon(c, partial(curve((gx - w / 2, gy + 290), (gx + w / 2, gy + 290)), rev), t, 12)

# ---------------- screen space ----------------
def background(c, W, H, cam, t):
    c.clear(hexc(BG)); cx, cy, z = cam; step = 96; p = paint(hexc("#DEE5F0"))
    ox, oy = (-cx * z * .5) % step, (-cy * z * .5) % step
    for x in np.arange(ox - step, W + step, step):
        for y in np.arange(oy - step, H + step, step): c.drawCircle(x, y, 2.2, p)
    c.drawCircle(W * .18, H * .12, min(W, H) * .5, paint(hexc("#BFD5FF", .55), blur=180)); c.drawCircle(W * .85, H * .85, min(W, H) * .45, paint(hexc("#D6E6FF", .5), blur=180))
    c.drawRect(skia.Rect.MakeWH(W, H), paint(hexc(BG), shader=skia.GradientShader.MakeRadial(skia.Point(W / 2, H / 2), max(W, H) * .75, [hexc("#FFFFFF", 0), hexc("#E6ECF6", .6)])))

def endcard(c, W, H, t, o):
    k = sstep(EV["to_endcard"], EV["endcard"], t)
    if k <= 0: return
    r = math.hypot(W, H) * ease_io(k)
    c.drawCircle(W / 2, H / 2, r, paint(hexc(BG))); c.drawCircle(W / 2, H / 2, r, paint(hexc(BLUE), stroke=10, shader=grad_lin(0, W)))
    if t < EV["endcard"]: return
    u = t - EV["endcard"]; cy = H * (.4 if o == "L" else .42); s = 1.0 if o == "L" else 1.2
    c.drawCircle(W / 2, cy, 210 * s, paint(hexc(VIOLET, .14), blur=60)); c.drawCircle(W / 2, cy + 12 * s, 120 * s, paint(hexc("#1C3B6E", .12), blur=20)); c.drawCircle(W / 2, cy, 120 * s, paint(hexc("#FFFFFF")))
    ring = skia.Path(); ring.addArc(skia.Rect.MakeLTRB(W / 2 - 132 * s, cy - 132 * s, W / 2 + 132 * s, cy + 132 * s), -90, 360 * ease_out(u / .5) - .01)
    c.drawPath(ring, paint(hexc(BLUE), stroke=14 * s, shader=skia.GradientShader.MakeSweep(W / 2, cy, [hexc(c_) for c_ in (CYAN, BLUE, VIOLET, PINK, CYAN)])))
    text(c, AVATAR_INITIALS, W / 2, cy, 96 * s, hexc(TXT), "display")
    a = ease_out((u - .1) / .4); group_alpha(c, a)
    text(c, NAME, W / 2, cy + 225 * s + (1 - a) * 20, 76 * s, hexc(TXT), "display")
    text(c, HANDLE, W / 2, cy + 305 * s + (1 - a) * 20, 40 * s, hexc(BLUE), "semi", shader=grad_lin(W / 2 - 200, 500))
    text(c, "Conceito independente · sem afiliação à Meta", W / 2, cy + 385 * s, 26 * s, hexc(SUB), "med")
    c.restore()

class Renderer:
    def __init__(self, o, scale):
        self.o = o; self.L = layout(o); self.scale = scale
        self.W, self.H = (1920, 1080) if o == "L" else (1080, 1920)
        self.surf = skia.Surface(int(self.W * scale), int(self.H * scale))
        cam = self.L["cam"]; self.cx, self.cy, self.cz = (monotone([(k[0], k[i]) for k in cam]) for i in (1, 2, 3))
    def cam(self, t): return self.cx(t), self.cy(t), self.cz(t)
    def draw(self, t):
        c = self.surf.getCanvas(); c.save(); c.scale(self.scale, self.scale)
        W, H = self.W, self.H; cam = self.cam(t); background(c, W, H, cam, t); cx, cy, z = cam
        c.save(); c.translate(W / 2, H / 2); c.scale(z, z); c.translate(-cx, -cy)
        sh = HEAD(t); fade = 1 - sstep(16.15, 16.55, t)
        if sh > 0 and fade > 0:
            n = int(np.searchsorted(TRAIL_S, sh)); pts = [tuple(p) for p in TRAIL[:n]] + [tuple(trail_at(sh))]
            ribbon(c, pts, t, 22, fade); hx, hy = pts[-1]
            c.drawCircle(hx, hy, 34, paint(hexc(VIOLET, .45 * fade), blur=16)); c.drawCircle(hx, hy, 14, paint(hexc("#FFFFFF", fade))); c.drawCircle(hx, hy, 14, paint(hexc(BLUE, fade), stroke=4))
        L = self.L
        for f in (scene_intro, scene_prompt, scene_travel, scene_email, scene_shop, scene_background, scene_memory, scene_platforms, scene_resolve): f(c, t, L)
        c.restore(); endcard(c, W, H, t, self.o); c.restore()
        return self.surf.makeImageSnapshot().toarray()
    def frame(self, t, fps):
        dt = 1 / fps; a, b = np.array(self.cam(t - dt / 2)), np.array(self.cam(t + dt / 2))
        speed = math.hypot(*(b[:2] - a[:2])) * a[2] + abs(b[2] - a[2]) * 2000
        n = 1 if speed < 4 else int(min(12, 3 + speed / 6))
        if n == 1: return self.draw(t)
        return (sum(self.draw(t + dt * (k / n - .5)).astype(np.float32) for k in range(n)) / n).astype(np.uint8)

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
    for f in range(int(DURATION * a.fps)):
        ff.stdin.write(R.frame(f / a.fps, a.fps).tobytes())
        if f % (a.fps * 2) == 0: print(f"{f / a.fps:5.1f}s", flush=True)
    ff.stdin.close(); ff.wait(); print("done", a.out)
