"""SUPERCASA spec film renderer (independent concept, not affiliated with SUPERCASA / Janela Digital).

Concept: the home search as a pop-up book. Each page turn is a feature; houses, cards and pins
pop up from the paper and fold flat again when the page turns.
Draws every frame with Skia (vector 2D) and pipes raw frames to FFmpeg.
Usage:
  python3 code/render.py --orient L --lang en --out exports/supercasa_spec_EN_1920x1080.mp4
  python3 code/render.py --orient V --lang en --scale 0.5 --out previews/s.png --still 1 4 8
"""
import argparse, math, os, subprocess, sys
import numpy as np, skia
sys.path.insert(0, os.path.dirname(__file__))
from timing import FPS, DURATION, TURNS, COVER_OPEN, BOOK_CLOSE, END_OPEN, EVENTS as EV, TEXT, NAME, HANDLE, AVATAR_INITIALS

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
FD = f"{ROOT}/assets/fonts"
TF = {"disp": skia.Typeface.MakeFromFile(f"{FD}/InterDisplay-Bold.otf"), "bold": skia.Typeface.MakeFromFile(f"{FD}/Inter-Bold.otf"),
      "semi": skia.Typeface.MakeFromFile(f"{FD}/Inter-SemiBold.otf"), "med": skia.Typeface.MakeFromFile(f"{FD}/Inter-Medium.otf"),
      "serif": skia.Typeface.MakeFromFile(f"{FD}/Fraunces-600-normal.ttf"), "serifb": skia.Typeface.MakeFromFile(f"{FD}/Fraunces-700-normal.ttf"),
      "ital": skia.Typeface.MakeFromFile(f"{FD}/Fraunces-500-italic.ttf")}

# ---------------- palette (SUPERCASA base colours: blue + white; names kept generic) ----------------
def hexc(h, a=1.0):
    h = h.lstrip("#"); return skia.Color(int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16), int(max(0, min(1, a)) * 255))
TABLE, TABLE_D, TABLE_L = "#C9D6EA", "#9FB3D3", "#E6EDF7"
PAPER, PAPER_D, INK, INK_S = "#FCFCFA", "#E6ECF5", "#14284B", "#66738A"
CORAL, CORAL_D, CORAL_L = "#1658D6", "#0D3E9E", "#CFDDF8"
TEAL, TEAL_D, SAGE, SUN, SKY, SEA, SAND, WHITE = "#4C8FF0", "#1A4FB5", "#BFD4F2", "#F4B740", "#DCE8FA", "#D6E5F8", "#F1F3F6", "#FFFFFF"

# ---------------- maths ----------------
clamp = lambda x, a=0.0, b=1.0: max(a, min(b, x))
lerp = lambda a, b, t: a + (b - a) * t
def sstep(a, b, x): t = clamp((x - a) / (b - a)); return t * t * (3 - 2 * t)
def ease_out(t): t = clamp(t); return 1 - (1 - t) ** 3
def ease_io(t): t = clamp(t); return 4 * t ** 3 if t < .5 else 1 - (-2 * t + 2) ** 3 / 2
def back_out(t, c=1.7): t = clamp(t); return 1 + (c + 1) * (t - 1) ** 3 + c * (t - 1) ** 2
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

# ---------------- drawing helpers ----------------
def paint(color, **kw):
    p = skia.Paint(AntiAlias=True, Color=color)
    if "stroke" in kw: p.setStyle(skia.Paint.kStroke_Style); p.setStrokeWidth(kw["stroke"]); p.setStrokeCap(skia.Paint.kRound_Cap); p.setStrokeJoin(skia.Paint.kRound_Join)
    if kw.get("blur", 0) > 0: p.setMaskFilter(skia.MaskFilter.MakeBlur(skia.kNormal_BlurStyle, kw["blur"]))
    if "shader" in kw: p.setShader(kw["shader"])
    if kw.get("effect") is not None: p.setPathEffect(kw["effect"])
    return p
def text(c, s, x, y, size, color, tf="bold", align="c"):
    f = skia.Font(TF[tf], size); w = f.measureText(s)
    dx = {"c": -w / 2, "l": 0, "r": -w}[align]; c.drawString(s, x + dx, y + size * 0.36, f, paint(color)); return w
def text_w(s, size, tf="bold"): return skia.Font(TF[tf], size).measureText(s)
def fit(s, size, tf, maxw): return min(size, size * maxw / max(1, text_w(s, size, tf)))
def rr(x, y, w, h, r): return skia.RRect.MakeRectXY(skia.Rect.MakeXYWH(x - w / 2, y - h / 2, w, h), r, r)
def R(l, t, r, b): return skia.Rect.MakeLTRB(l, t, r, b)
def layer_alpha(c, a): c.saveLayerAlpha(None, int(clamp(a) * 255))

def make_grain(n=256, seed=3, amp=26):
    g = np.random.default_rng(seed).normal(0, 1, (n, n)); img = np.zeros((n, n, 4), np.uint8)
    v = np.clip(128 + g * amp, 0, 255).astype(np.uint8); img[..., 0] = img[..., 1] = img[..., 2] = v; img[..., 3] = 255
    return skia.Image.fromarray(img).makeShader(skia.TileMode.kRepeat, skia.TileMode.kRepeat)
GRAIN = None
def grain(c, rect, a=0.07):
    global GRAIN
    if GRAIN is None: GRAIN = make_grain()
    p = skia.Paint(Shader=GRAIN, Alpha=int(a * 255)); p.setBlendMode(skia.BlendMode.kOverlay); c.drawRect(rect, p)

# pop-up: the element rises from its base line (scale y) and casts a growing shadow onto the page
def popup(c, x, base, k, fn, bounds, shadow=1.0):
    if k <= 0.002: return
    c.save(); c.translate(x, base); c.scale(1, k); c.translate(-x, -base)
    sp = skia.Paint(); sp.setImageFilter(skia.ImageFilters.DropShadow(10 * k * shadow, 14 * k * shadow, 9, 9, hexc("#0B1F45", .25 * clamp(k))))
    c.saveLayer(bounds, sp); fn(c); c.restore()
    if k < 1:  # tilted away from the light while it rises
        c.drawRect(bounds, paint(hexc("#0B1F45", .18 * (1 - clamp(k)))))
    c.restore()

# ---------------- icons (approximations drawn in code) ----------------
def house_icon(c, x, y, s, wall, roof, door=None, win=None, lights=0.0, chimney=True):
    """house centred on x, base at y; s = width"""
    w, wh, rh = s, s * 0.62, s * 0.46
    if chimney: c.drawRect(R(x + w * 0.2, y - wh - rh * 0.85, x + w * 0.32, y - wh - rh * 0.2), paint(hexc(roof)))
    c.drawRect(R(x - w / 2, y - wh, x + w / 2, y), paint(hexc(wall)))
    rp = skia.Path(); rp.moveTo(x - w * 0.6, y - wh + 2); rp.lineTo(x, y - wh - rh); rp.lineTo(x + w * 0.6, y - wh + 2); rp.close()
    c.drawPath(rp, paint(hexc(roof)))
    c.drawRect(R(x - w * 0.6, y - wh - 2, x + w * 0.6, y - wh + w * 0.04), paint(hexc("#000000", .12)))
    c.drawRRect(skia.RRect.MakeRectXY(R(x - w * 0.09, y - wh * 0.52, x + w * 0.09, y), w * 0.03, w * 0.03), paint(hexc(door or CORAL_D)))
    wc = win or SKY
    for sx in (-1, 1):
        cx = x + sx * w * 0.28; cy = y - wh * 0.55; ww = w * 0.17
        c.drawRect(R(cx - ww / 2, cy - ww / 2, cx + ww / 2, cy + ww / 2), paint(hexc(wc)))
        if lights > 0:
            c.drawRect(R(cx - ww / 2, cy - ww / 2, cx + ww / 2, cy + ww / 2), paint(hexc(SUN, lights)))
            c.drawCircle(cx, cy, ww * 1.1, paint(hexc(SUN, .35 * lights), blur=ww * 0.5))
        c.drawLine(cx, cy - ww / 2, cx, cy + ww / 2, paint(hexc(wall), stroke=max(1.5, w * 0.012)))
        c.drawLine(cx - ww / 2, cy, cx + ww / 2, cy, paint(hexc(wall), stroke=max(1.5, w * 0.012)))
    rw = w * 0.13; c.drawCircle(x, y - wh - rh * 0.42, rw * 0.5, paint(hexc(wc)))

def tree(c, x, y, s, col=TEAL):
    c.drawRect(R(x - s * 0.06, y - s * 0.7, x + s * 0.06, y), paint(hexc("#7C8CA8")))
    c.drawCircle(x, y - s * 0.95, s * 0.42, paint(hexc(col)))
    c.drawCircle(x - s * 0.12, y - s * 1.08, s * 0.16, paint(hexc("#FFFFFF", .18)))

def heart_path(x, y, s):
    p = skia.Path(); p.moveTo(x, y + s * 0.35)
    p.cubicTo(x - s * 0.9, y - s * 0.25, x - s * 0.45, y - s * 0.95, x, y - s * 0.42)
    p.cubicTo(x + s * 0.45, y - s * 0.95, x + s * 0.9, y - s * 0.25, x, y + s * 0.35); p.close(); return p

def roof_mark(c, x, y, s, col, stroke, k=1.0):
    p = skia.Path(); p.moveTo(x - s, y + s * 0.55); p.lineTo(x, y - s * 0.25); p.lineTo(x + s, y + s * 0.55)
    if k <= 0.001: return
    if k >= 0.999: c.drawPath(p, paint(hexc(col), stroke=stroke))
    else: c.drawPath(p, paint(hexc(col), stroke=stroke, effect=skia.TrimPathEffect.Make(0, clamp(k))))

def magnifier(c, x, y, s, col):
    c.drawCircle(x - s * 0.12, y - s * 0.12, s * 0.38, paint(hexc(col), stroke=s * 0.14))
    c.drawLine(x + s * 0.16, y + s * 0.16, x + s * 0.45, y + s * 0.45, paint(hexc(col), stroke=s * 0.16))

def pin(c, x, y, s, col=CORAL):
    """map pin with a tiny house, tip at (x, y)"""
    p = skia.Path(); p.moveTo(x, y)
    p.cubicTo(x - s * 0.3, y - s * 0.45, x - s * 0.6, y - s * 0.7, x - s * 0.6, y - s * 1.05)
    p.cubicTo(x - s * 0.6, y - s * 1.45, x - s * 0.3, y - s * 1.7, x, y - s * 1.7)
    p.cubicTo(x + s * 0.3, y - s * 1.7, x + s * 0.6, y - s * 1.45, x + s * 0.6, y - s * 1.05)
    p.cubicTo(x + s * 0.6, y - s * 0.7, x + s * 0.3, y - s * 0.45, x, y); p.close()
    c.drawPath(p, paint(hexc(col)))
    hx, hy = x, y - s * 0.86
    hp = skia.Path(); hp.moveTo(hx - s * 0.3, hy - s * 0.12); hp.lineTo(hx, hy - s * 0.38); hp.lineTo(hx + s * 0.3, hy - s * 0.12)
    hp.lineTo(hx + s * 0.3, hy + s * 0.2); hp.lineTo(hx - s * 0.3, hy + s * 0.2); hp.close(); c.drawPath(hp, paint(hexc(WHITE)))

def bell(c, x, y, s, col, swing=0.0):
    c.save(); c.translate(x, y - s * 0.55); c.rotate(swing); c.translate(-x, -(y - s * 0.55))
    p = skia.Path(); p.moveTo(x - s * 0.5, y + s * 0.3); p.cubicTo(x - s * 0.38, y + s * 0.1, x - s * 0.42, y - s * 0.5, x, y - s * 0.5)
    p.cubicTo(x + s * 0.42, y - s * 0.5, x + s * 0.38, y + s * 0.1, x + s * 0.5, y + s * 0.3); p.close()
    c.drawPath(p, paint(hexc(col))); c.drawCircle(x, y + s * 0.42, s * 0.12, paint(hexc(col))); c.drawCircle(x, y - s * 0.56, s * 0.08, paint(hexc(col)))
    c.restore()

def wordmark(c, x, y, size, col, gleam=-1.0):
    w = text_w("SUPERCASA", size, "disp"); c.saveLayer(None, None)
    text(c, "SUPERCASA", x, y, size, hexc(col), "disp")
    cw_ = text_w("CASA", size, "disp"); roof_mark(c, x + w * 0.5 - cw_ * 0.5, y - size * 1.08, cw_ * 0.4, col, size * 0.085)
    if 0 <= gleam <= 1:
        gx = x - w / 2 + (w + 200) * gleam - 100
        sh = skia.GradientShader.MakeLinear([skia.Point(gx - 60, y), skia.Point(gx + 60, y)], [hexc("#7FB0FF", 0), hexc("#7FB0FF", .9), hexc("#7FB0FF", 0)])
        c.save(); c.clipRect(R(x - w / 2, y - size * 1.1, x + w / 2, y + size * 0.6))
        p = skia.Paint(AntiAlias=True, Shader=sh); p.setBlendMode(skia.BlendMode.kSrcATop)
        c.drawRect(R(gx - 60, y - size * 1.1, gx + 60, y + size * 0.6), p); c.restore()
    c.restore(); return w

# ---------------- book geometry ----------------
def layout(orient):
    if orient == "L":
        PW, PH = 740, 900
        A, B = (-PW / 2, 0), (PW / 2, 0)
        rA, rB = R(-PW, -PH / 2, 0, PH / 2), R(0, -PH / 2, PW, PH / 2)
        cam = [(0, 370, 0, 1.1), (0.3, 370, 0, 1.1), (1.3, 0, 0, 1.0), (2.95, 0, 0, 1.025), (3.15, 0, 0, 1.0),
               (3.9, 0, 0, 1.0), (6.6, 0, 0, 1.03), (6.85, 0, 0, 1.0), (7.6, 0, 0, 1.0), (8.6, 0, 0, 1.02), (9.45, -110, 95, 1.2),
               (9.7, -110, 95, 1.2), (10.2, 0, 0, 1.0), (10.95, 0, 0, 1.0), (14.45, 0, 0, 1.03), (14.6, 0, 0, 1.0),
               (15.45, 370, 0, 1.0), (18.15, 370, 0, 1.1), (18.95, 0, 0, 1.0), (21, 0, 0, 1.04)]
    else:
        PW, PH = 940, 800
        A, B = (0, -PH / 2), (0, PH / 2)
        rA, rB = R(-PW / 2, -PH, PW / 2, 0), R(-PW / 2, 0, PW / 2, PH)
        cam = [(0, 0, 400, 1.0), (0.3, 0, 400, 1.0), (1.3, 0, 0, 1.0), (2.95, 0, 0, 1.025), (3.15, 0, 0, 1.0),
               (3.9, 0, 0, 1.0), (6.6, 0, 0, 1.03), (6.85, 0, 0, 1.0), (7.6, 0, 0, 1.0), (8.6, 0, 0, 1.02), (9.45, -140, 160, 1.2),
               (9.7, -140, 160, 1.2), (10.2, 0, 0, 1.0), (10.95, 0, 0, 1.0), (14.45, 0, 0, 1.03), (14.6, 0, 0, 1.0),
               (15.45, 0, 400, 1.0), (18.15, 0, 400, 1.1), (18.95, 0, 0, 1.0), (21, 0, 0, 1.04)]
    return dict(o=orient, PW=PW, PH=PH, A=A, B=B, rA=rA, rB=rB, cam=cam)

# lifecycle of each spread: (lands at, starts leaving at)
LAND = [COVER_OPEN[0] + COVER_OPEN[1], TURNS[0][0] + TURNS[0][1], TURNS[1][0] + TURNS[1][1], TURNS[2][0] + TURNS[2][1]]
LEAVE = [TURNS[0][0], TURNS[1][0], TURNS[2][0], BOOK_CLOSE[0]]
def pk(t, i, t0=None, dur=0.42):
    """pop factor of an element on spread i (0-based) appearing at t0"""
    start = max(LAND[i] + 0.02, t0 if t0 is not None else LAND[i])
    return back_out((t - start) / dur) * (1 - sstep(LEAVE[i], LEAVE[i] + 0.3, t))

# ---------------- spreads (spread coordinates: spine at origin) ----------------
def endpaper(c, rect, col=CORAL, a=0.12):
    step = 92; layer_alpha(c, a)
    for i, y in enumerate(np.arange(rect.top() + 40, rect.bottom(), step)):
        for x in np.arange(rect.left() + 40 + (i % 2) * step / 2, rect.right(), step): roof_mark(c, x, y, 13, col, 3.2)
    c.restore()

def spread1(c, t, L, TX):  # story + house
    ax, ay = L["A"]; bx, by = L["B"]
    endpaper(c, L["rA"])
    roof_mark(c, ax, ay - 235, 46, CORAL, 9, sstep(0.9, 1.6, t))
    for i, k in enumerate(("story_1", "story_2", "story_3")):
        a = sstep(0.95 + i * 0.35, 1.45 + i * 0.35, t)
        layer_alpha(c, a); text(c, TX[k], ax, ay - 100 + i * 105 + (1 - a) * 14, 88, hexc(CORAL if i == 2 else INK), "serif"); c.restore()
    PH = L["PH"]; PW = L["PW"]; g = by + PH * 0.3
    c.drawRect(R(bx - PW / 2, g, bx + PW / 2, by + PH / 2), paint(hexc(PAPER_D, .6)))
    sx, sy = bx + PW * 0.24, by - PH * 0.23
    popup(c, sx, sy + 80, pk(t, 0, EV["house_pop"] - 0.25), lambda c: c.drawCircle(sx, sy, 70, paint(hexc(SUN))), R(sx - 90, sy - 90, sx + 90, sy + 90))
    hill = lambda dx, w, h, col: (lambda c: c.drawOval(R(bx + dx - w / 2, g - h, bx + dx + w / 2, g + h), paint(hexc(col))))
    popup(c, bx - 150, g, pk(t, 0, EV["house_pop"] - 0.15), hill(-150, 560, 120, SAGE), R(bx - 440, g - 130, bx + 140, g + 2))
    popup(c, bx + 190, g, pk(t, 0, EV["house_pop"] - 0.1), hill(190, 480, 90, "#D5E3F7"), R(bx - 60, g - 100, bx + 440, g + 2))
    lights = sstep(EV["house_lights"], EV["house_lights"] + 0.3, t)
    popup(c, bx, g, pk(t, 0, EV["house_pop"], 0.5), lambda c: house_icon(c, bx, g, 300, WHITE, CORAL, lights=lights), R(bx - 200, g - 360, bx + 200, g + 2))
    for dx, s, d in ((-250, 120, 0.15), (250, 100, 0.25)):
        popup(c, bx + dx, g, pk(t, 0, EV["house_pop"] + d), lambda c, dx=dx, s=s: tree(c, bx + dx, g, s), R(bx + dx - 70, g - 180, bx + dx + 70, g + 2))
    # little path to the door
    pth = skia.Path(); pth.moveTo(bx - 28, g); pth.lineTo(bx + 28, g); pth.lineTo(bx + 70, by + PH / 2); pth.lineTo(bx - 70, by + PH / 2); pth.close()
    c.drawPath(pth, paint(hexc("#DCE5F2")))

def spread2(c, t, L, TX):  # search
    ax, ay = L["A"]; bx, by = L["B"]; PW, PH = L["PW"], L["PH"]
    for i, k in enumerate(("search_h1", "search_h2", "search_h3")):
        sz = fit(TX[k], 80, "serif", PW - 120)
        text(c, TX[k], ax, ay - 190 + i * 98, sz, hexc(CORAL if i == 2 else INK), "serif")
    # buy / rent toggle
    ty = ay + 150; tw, th = 460, 92
    def toggle(c):
        c.drawRRect(rr(ax, ty, tw, th, th / 2), paint(hexc(WHITE)))
        c.drawRRect(rr(ax, ty, tw, th, th / 2), paint(hexc(PAPER_D), stroke=3))
        u = ease_io((t - EV["toggle_rent"]) / 0.3); kx = ax + lerp(-tw / 4, tw / 4, u)
        c.drawRRect(rr(kx, ty, tw / 2 - 12, th - 14, (th - 14) / 2), paint(hexc(CORAL)))
        for j, k in enumerate(("buy", "rent")):
            on = (1 - u) if j == 0 else u
            col = skia.Color4f.FromColor(hexc(INK)); col2 = skia.Color4f.FromColor(hexc(WHITE))
            mix = skia.Color4f(lerp(col.fR, col2.fR, on), lerp(col.fG, col2.fG, on), lerp(col.fB, col2.fB, on), 1).toColor()
            text(c, TX[k], ax + (j - 0.5) * tw / 2, ty, 36, mix, "semi")
    popup(c, ax, ty + th / 2, pk(t, 1, LAND[1] + 0.05), toggle, R(ax - tw / 2 - 10, ty - th, ax + tw / 2 + 10, ty + th))
    # search card
    cw, ch = min(PW - 110, 640), 330; cy = by - PH * 0.17
    def card(c):
        c.drawRRect(rr(bx, cy, cw, ch, 28), paint(hexc(WHITE)))
        fy = cy - ch / 2 + 70
        c.drawRRect(rr(bx, fy, cw - 60, 84, 42), paint(hexc("#EEF2F8")))
        magnifier(c, bx - cw / 2 + 74, fy, 34, INK)
        n = int(len(TX["search_q"]) * clamp((t - EV["type_start"]) / (EV["type_end"] - EV["type_start"])))
        x0 = bx - cw / 2 + 108
        if n == 0: text(c, TX["search_ph"], x0, fy, 32, hexc(INK_S), "med", "l"); w = 0
        else: w = text(c, TX["search_q"][:n], x0, fy, 36, hexc(INK), "semi", "l")
        if (t * 2.2) % 1 < 0.6 and t < EV["results"]: c.drawRect(R(x0 + w + 4, fy - 22, x0 + w + 7, fy + 22), paint(hexc(CORAL)))
        # chips
        xs = bx - cw / 2 + 30; chy = fy + 108
        for j, s in enumerate(TX["chips"]):
            ww = text_w(s, 28, "semi") + 52; on = sstep(EV[f"chip_{j + 1}"], EV[f"chip_{j + 1}"] + 0.15, t)
            sc = back_out((t - EV[f"chip_{j + 1}"] + 0.25) / 0.3)
            if sc > 0:
                c.save(); c.translate(xs + ww / 2, chy); c.scale(sc, sc); c.translate(-(xs + ww / 2), -chy)
                c.drawRRect(rr(xs + ww / 2, chy, ww, 60, 30), paint(hexc(CORAL if on > .5 else WHITE)))
                c.drawRRect(rr(xs + ww / 2, chy, ww, 60, 30), paint(hexc(CORAL), stroke=3))
                text(c, s, xs + ww / 2, chy, 28, hexc(WHITE if on > .5 else CORAL), "semi"); c.restore()
            xs += ww + 14
        ra = sstep(EV["results"], EV["results"] + 0.3, t)
        if ra > 0:
            layer_alpha(c, ra); c.drawCircle(bx - cw / 2 + 46, chy + 92, 9, paint(hexc(TEAL)))
            text(c, TX["results"], bx - cw / 2 + 66, chy + 92, 30, hexc(TEAL_D), "semi", "l"); c.restore()
    popup(c, bx, cy + ch / 2, pk(t, 1, LAND[1] + 0.12, 0.5), card, R(bx - cw / 2 - 10, cy - ch / 2 - 10, bx + cw / 2 + 30, cy + ch / 2 + 30))
    g = by + PH * 0.33
    c.drawRect(R(bx - PW / 2, g, bx + PW / 2, by + PH / 2), paint(hexc(PAPER_D, .6)))
    cols = [(CORAL, WHITE), (TEAL, "#EEF3FB"), (SUN, WHITE)]
    for j, dx in enumerate((-210, 0, 210)):
        roof, wall = cols[j]
        popup(c, bx + dx, g, pk(t, 1, EV["results"] + 0.08 * j), lambda c, dx=dx, roof=roof, wall=wall: house_icon(c, bx + dx, g, 150, wall, roof, chimney=j != 1),
              R(bx + dx - 100, g - 190, bx + dx + 100, g + 2))

CITIES = [("Porto", "Porto", -8.61, 41.15), ("Coimbra", "Coimbra", -8.43, 40.2), ("Lisbon", "Lisboa", -9.14, 38.72),
          ("Évora", "Évora", -7.91, 38.57), ("Faro", "Faro", -7.93, 37.02)]
PT = [(-8.87, 41.87), (-8.62, 42.05), (-8.2, 42.15), (-8.05, 41.82), (-7.4, 41.88), (-6.9, 41.95), (-6.55, 41.68), (-6.2, 41.58),
      (-6.5, 41.25), (-6.9, 41.0), (-6.8, 40.6), (-6.85, 40.25), (-7.0, 39.67), (-7.5, 39.62), (-7.3, 39.42), (-7.05, 38.88),
      (-7.3, 38.42), (-7.0, 38.05), (-7.5, 37.55), (-7.41, 37.18), (-7.9, 36.97), (-8.6, 37.1), (-8.99, 37.02), (-8.8, 37.42),
      (-8.82, 37.95), (-8.78, 38.3), (-8.95, 38.48), (-9.2, 38.42), (-9.1, 38.62), (-9.48, 38.72), (-9.42, 39.1), (-9.36, 39.36),
      (-9.05, 39.7), (-8.88, 40.1), (-8.68, 40.6), (-8.7, 41.15), (-8.8, 41.6)]
SPAIN = PT[:20] + [(-6.9, 37.15), (-6.3, 36.8), (3.0, 36.5), (3.0, 44.5), (-9.4, 44.5), (-9.3, 43.2), (-8.95, 42.5)]
def geo(L):
    s = 165 if L["o"] == "L" else 250
    return lambda lon, lat: ((lon + 7.85) * 0.77 * s, (39.58 - lat) * s)

def spread3(c, t, L, TX):  # map
    PW, PH = L["PW"], L["PH"]; P = geo(L)
    c.drawRect(R(-PW * 2, -PH * 2, PW * 2, PH * 2), paint(hexc(SEA)))
    for poly, col in ((SPAIN, "#E3EAF4"), (PT, WHITE)):
        p = skia.Path(); p.moveTo(*P(*poly[0]))
        for q in poly[1:]: p.lineTo(*P(*q))
        p.close(); c.drawPath(p, paint(hexc(col)))
        if poly is PT:
            c.drawPath(p, paint(hexc(CORAL, .9), stroke=3.5, effect=skia.DashPathEffect.Make([14, 9], 0)))
    # waves in the ocean
    for i in range(7):
        y = -PH * 0.8 + i * 150 + (40 if L["o"] == "V" else 0); x = -PW * 0.75 + (i % 2) * 90
        if L["o"] == "V": x = -PW * 0.47 + (i % 2) * 40
        wv = skia.Path(); wv.moveTo(x, y)
        for k in range(3): wv.quadTo(x + 15 + 30 * k, y - 10, x + 30 + 30 * k, y)
        c.drawPath(wv, paint(hexc(TEAL, .35), stroke=3))
    # compass
    cx, cy = (-PW * 0.68, PH * 0.3) if L["o"] == "L" else (-PW * 0.38, PH * 0.78)
    c.drawCircle(cx, cy, 46, paint(hexc(INK, .5), stroke=2.5))
    nd = skia.Path(); nd.moveTo(cx, cy - 58); nd.lineTo(cx + 12, cy); nd.lineTo(cx, cy + 58); nd.lineTo(cx - 12, cy); nd.close(); c.drawPath(nd, paint(hexc(INK, .55)))
    text(c, "N", cx, cy - 80, 24, hexc(INK, .6), "bold")
    hx, hy = (-PW + 70, -PH / 2 + 80) if L["o"] == "L" else (-PW / 2 + 60, -PH + 70)
    text(c, TX["map_h"], hx, hy, 50, hexc(INK), "serif", "l")
    lang = TX is TEXT["pt"]
    for j, (en, pt_, lon, lat) in enumerate(CITIES):
        x, y = P(lon, lat); c.drawCircle(x, y, 6, paint(hexc(INK)))
        text(c, pt_ if lang else en, x + 16, y + 20, 24, hexc(INK), "semi", "l")
    for j, (en, pt_, lon, lat) in enumerate(CITIES):
        x, y = P(lon, lat)
        popup(c, x, y, pk(t, 2, EV[f"pin_{j + 1}"], 0.38), lambda c, x=x, y=y: pin(c, x, y, 44), R(x - 40, y - 82, x + 40, y + 2))
    # near me
    nx, ny = P(-9.0, 38.9); k = sstep(EV["near_me"], EV["near_me"] + 0.25, t) * (1 - sstep(LEAVE[2], LEAVE[2] + 0.2, t))
    if k > 0:
        for r in range(3):
            ph = ((t - EV["near_me"]) * 0.9 + r / 3) % 1
            c.drawCircle(nx, ny, 14 + ph * 90, paint(hexc("#0D3E9E", .35 * (1 - ph) * k), stroke=4))
        c.drawCircle(nx, ny, 20 * k, paint(hexc(WHITE))); c.drawCircle(nx, ny, 14 * k, paint(hexc("#0D3E9E")))
        lw = text_w(TX["near_me"], 28, "semi") + 70; lx = nx - 40 - lw / 2 - (0 if L["o"] == "L" else 0)
        def chip(c):
            c.drawRRect(rr(lx, ny - 70, lw, 58, 29), paint(hexc(INK)))
            nav = skia.Path(); px, py = lx - lw / 2 + 32, ny - 70
            nav.moveTo(px + 10, py - 11); nav.lineTo(px - 11, py - 1); nav.lineTo(px - 1, py + 1); nav.lineTo(px + 1, py + 11); nav.close()
            c.drawPath(nav, paint(hexc(WHITE)))
            text(c, TX["near_me"], lx + 14, ny - 70, 28, hexc(WHITE), "semi")
        popup(c, lx, ny - 41, pk(t, 2, EV["near_me"] + 0.1, 0.35), chip, R(lx - lw / 2 - 5, ny - 105, lx + lw / 2 + 25, ny - 30))

def spread4(c, t, L, TX):  # save + alerts
    ax, ay = L["A"]; bx, by = L["B"]; PW, PH = L["PW"], L["PH"]; V = L["o"] == "V"
    hy = ay - (330 if not V else 320)
    if V:
        text(c, TX["save_h1"] + " " + TX["save_h2"], ax, hy, fit(TX["save_h1"] + " " + TX["save_h2"], 64, "serif", PW - 100), hexc(INK), "serif")
    else:
        text(c, TX["save_h1"], ax, hy, 70, hexc(INK), "serif"); text(c, TX["save_h2"], ax, hy + 82, 70, hexc(CORAL), "serif")
    cw, ch = (540, 560) if not V else (560, 560); cy = ay + (95 if not V else 60)
    ph = 300
    def card(c):
        top = cy - ch / 2
        c.drawRRect(rr(ax, cy, cw, ch, 26), paint(hexc(WHITE)))
        c.save(); c.clipRRect(skia.RRect.MakeRectXY(R(ax - cw / 2, top, ax + cw / 2, top + ph), 26, 26))
        c.drawRect(R(ax - cw / 2, top, ax + cw / 2, top + ph + 30), paint(hexc(SKY)))
        c.drawCircle(ax + cw * 0.3, top + 70, 34, paint(hexc(SUN)))
        c.drawOval(R(ax - cw * 0.8, top + ph - 70, ax + cw * 0.2, top + ph + 80), paint(hexc(SAGE)))
        c.drawOval(R(ax - cw * 0.1, top + ph - 50, ax + cw * 0.9, top + ph + 90), paint(hexc("#D5E3F7")))
        house_icon(c, ax - 20, top + ph - 18, 190, "#EEF3FB", TEAL, lights=0)
        tree(c, ax + 150, top + ph - 18, 80); tree(c, ax - 180, top + ph - 18, 70, "#2F6FD8")
        c.restore()
        hx2, hy2 = ax + cw / 2 - 52, top + 52; hk = sstep(EV["heart"], EV["heart"] + 0.12, t)
        bump = 1 + 0.35 * math.sin(clamp((t - EV["heart"]) / 0.35) * math.pi)
        c.drawCircle(hx2, hy2, 34, paint(hexc(WHITE)))
        c.save(); c.translate(hx2, hy2); c.scale(bump, bump); c.translate(-hx2, -hy2)
        hp = heart_path(hx2, hy2 + 4, 30)
        if hk > 0: c.drawPath(hp, paint(hexc(CORAL, hk)))
        c.drawPath(hp, paint(hexc(CORAL), stroke=4)); c.restore()
        u = clamp((t - EV["heart"]) / 0.55)
        if 0 < u < 1:
            for j in range(8):
                a = j * math.pi / 4; r = 40 + u * 46
                c.drawCircle(hx2 + math.cos(a) * r, hy2 + math.sin(a) * r, 7 * (1 - u), paint(hexc([CORAL, SUN][j % 2])))
        tx = ax - cw / 2 + 34
        text(c, TX["listing_p"], tx, top + ph + 56, 46, hexc(INK), "disp", "l")
        text(c, TX["listing_t"], tx, top + ph + 116, 30, hexc(INK), "semi", "l")
        text(c, TX["listing_m"], tx, top + ph + 166, 26, hexc(INK_S), "med", "l")
    popup(c, ax, cy + ch / 2, pk(t, 3, LAND[3] + 0.1, 0.5), card, R(ax - cw / 2 - 10, cy - ch / 2 - 10, ax + cw / 2 + 30, cy + ch / 2 + 30))
    # alerts page
    sw = 18 * math.sin((t - EV["bell"]) * 18) * math.exp(-(t - EV["bell"]) * 3) if t > EV["bell"] else 0
    bly = by - (285 if not V else 270)
    popup(c, bx, bly + 40, pk(t, 3, EV["bell"] - 0.25, 0.35), lambda c: (c.drawCircle(bx, bly, 62, paint(hexc(CORAL_L))), bell(c, bx, bly + 6, 64, CORAL_D, sw)),
          R(bx - 80, bly - 80, bx + 80, bly + 80))
    text(c, TX["alerts_h"], bx, bly + (130 if not V else 115), fit(TX["alerts_h"], 64, "serif", PW - 100), hexc(INK), "serif")
    nw, nh = min(PW - 120, 600), 128
    for j, (ev, lines, tm) in enumerate((("alert_1", TX["alert_1"], TX["min"]), ("alert_2", TX["alert_2"], TX["now"]))):
        ny = by + (25 if not V else 10) + j * (nh + 30)
        sl = ease_out((t - EV[ev]) / 0.5); dx = (1 - sl) * (PW * 0.9)
        if sl <= 0: continue
        def note(c, ny=ny, lines=lines, tm=tm, dx=dx):
            x = bx + dx
            c.drawRRect(rr(x, ny, nw, nh, 24), paint(hexc(WHITE)))
            c.drawRRect(rr(x - nw / 2 + 58, ny, 64, 64, 16), paint(hexc(CORAL)))
            roof_mark(c, x - nw / 2 + 58, ny + 2, 18, WHITE, 5)
            text(c, lines[0], x - nw / 2 + 108, ny - 22, 29, hexc(INK), "bold", "l")
            text(c, lines[1], x - nw / 2 + 108, ny + 22, 25, hexc(INK_S), "med", "l")
            text(c, tm, x + nw / 2 - 26, ny - 22, 22, hexc(INK_S), "med", "r")
        popup(c, bx, ny + nh / 2, pk(t, 3, EV[ev] - 0.05, 0.3), note, R(bx - nw / 2 - 10 + dx, ny - nh / 2 - 10, bx + nw / 2 + 30 + dx, ny + nh / 2 + 30))

SPREADS = [spread1, spread2, spread3, spread4]

def cover(c, t, L, TX, logo_k=1.0):
    bx, by = L["B"]; PW, PH = L["PW"], L["PH"]; m = 16
    rect = R(bx - PW / 2 - m, by - PH / 2 - m, bx + PW / 2 + m, by + PH / 2 + m)
    c.drawRRect(skia.RRect.MakeRectXY(rect, 14, 14), paint(hexc(CORAL)))
    c.save(); c.clipRect(rect)
    for i in range(6):  # embossed rooflines
        roof_mark(c, bx, by - PH / 2 + 20 + i * 190, PW * 0.9, CORAL_D, 3)
    grain(c, rect, .12); c.restore()
    sp = (rect.left() + 10, rect.right() - 10) if L["o"] == "L" else (rect.top() + 10, rect.bottom() - 10)
    if L["o"] == "L": c.drawRect(R(rect.left(), rect.top(), rect.left() + 26, rect.bottom()), paint(hexc(CORAL_D, .5)))
    else: c.drawRect(R(rect.left(), rect.top(), rect.right(), rect.top() + 26), paint(hexc(CORAL_D, .5)))
    gl = (t - EV["logo_gleam"]) / 0.9 if t > 14 else (t - 0.05) / 0.9
    wordmark(c, bx, by + 10, fit("SUPERCASA", 104, "disp", PW - 180), WHITE, gleam=gl)
    k = sstep(EV["tagline"], EV["tagline"] + 0.6, t) if t > 14 else 0
    if k > 0:
        layer_alpha(c, k); text(c, TX["tagline"], bx, by + 210 + (1 - k) * 16, fit(TX["tagline"], 46, "ital", PW - 120), hexc(WHITE), "ital"); c.restore()
    text(c, "supercasa.pt", bx, by + PH / 2 - 60, 26, hexc(WHITE, .75), "semi")

def endcard_page(c, t, L, TX):
    pass  # the card itself is drawn above the book (it straddles the spine)

def endcard(c, t, L, TX):
    k = back_out((t - EV["card"]) / 0.45)
    if k <= 0: return
    V = L["o"] == "V"; cw, ch = (900, 640) if not V else (860, 820); base = ch / 2
    def card(c):
        c.drawRRect(rr(0, 0, cw, ch, 30), paint(hexc(WHITE)))
        cy = -ch / 2 + (170 if not V else 210); u = t - EV["card"]
        c.drawCircle(0, cy, 96, paint(hexc(CORAL_L, .5)))
        ring = skia.Path(); ring.addArc(R(-108, cy - 108, 108, cy + 108), -90, 360 * ease_out(u / 0.6) - 0.01)
        c.drawPath(ring, paint(hexc(CORAL), stroke=12))
        text(c, AVATAR_INITIALS, 0, cy, 84, hexc(INK), "disp")
        text(c, NAME, 0, cy + 180, 72, hexc(INK), "disp")
        text(c, HANDLE, 0, cy + 255, 40, hexc(CORAL), "semi")
        text(c, TX["disclaimer"], 0, cy + 335, fit(TX["disclaimer"], 27, "med", cw - 80), hexc(INK_S), "med")
    popup(c, 0, base, k, card, R(-cw / 2 - 10, -ch / 2 - 10, cw / 2 + 30, ch / 2 + 30), shadow=1.6)

# ---------------- book state machine ----------------
def book_state(t):
    """returns (underA, underB, boardA, turn) where turn = (u, forward, front, back) and each page is a key"""
    def prog(seg): return ease_io((t - seg[0]) / seg[1])
    if t < COVER_OPEN[0]: return None, "cover", False, None
    if t < LAND[0]: return None, 0, False, (prog(COVER_OPEN), True, "cover", 0)
    for i, (t0, d) in enumerate(TURNS):
        if t < t0: return i, i, True, None
        if t < t0 + d: return i, i + 1, True, (prog((t0, d)), True, i, i + 1)
    if t < BOOK_CLOSE[0]: return 3, 3, True, None
    if t < sum(BOOK_CLOSE): return None, 3, False, (prog(BOOK_CLOSE), False, 3, "cover")
    if t < END_OPEN[0]: return None, "cover", False, None
    if t < sum(END_OPEN): return None, "end", False, (prog(END_OPEN), True, "cover", "endA")
    return "endA", "end", True, None

class Renderer:
    def __init__(self, orient, scale, lang):
        self.L = layout(orient); self.o = orient; self.scale = scale; self.TX = TEXT[lang]
        self.W, self.H = (1920, 1080) if orient == "L" else (1080, 1920)
        self.surf = skia.Surface(int(self.W * scale), int(self.H * scale))
        cam = self.L["cam"]; self.cx, self.cy, self.cz = (monotone([(k[0], k[i]) for k in cam]) for i in (1, 2, 3))
    def cam(self, t): return self.cx(t), self.cy(t), self.cz(t)

    def page(self, c, t, key, side):
        L, TX = self.L, self.TX; rect = L["rA"] if side == "A" else L["rB"]
        if key == "cover": cover(c, t, L, TX); return
        c.save(); c.clipRect(rect, True); c.drawRect(rect, paint(hexc(PAPER)))
        if key == "endA": endpaper(c, rect, CORAL, .16)
        elif key == "end": pass
        else: SPREADS[key](c, t, L, TX)
        grain(c, rect, .08)
        # gutter shading
        if L["o"] == "L":
            p0, p1 = (skia.Point(-70, 0), skia.Point(0, 0)) if side == "A" else (skia.Point(70, 0), skia.Point(0, 0))
        else:
            p0, p1 = (skia.Point(0, -70), skia.Point(0, 0)) if side == "A" else (skia.Point(0, 70), skia.Point(0, 0))
        c.drawRect(rect, paint(0, shader=skia.GradientShader.MakeLinear([p0, p1], [hexc("#0B1F45", 0), hexc("#0B1F45", .16)])))
        c.restore()

    def board(self, c, side, shadow=True):
        L = self.L; rect = L["rA"] if side == "A" else L["rB"]; m = 16
        big = R(rect.left() - m, rect.top() - m, rect.right() + m, rect.bottom() + m)
        if shadow: c.drawRect(R(big.left() + 18, big.top() + 26, big.right() + 18, big.bottom() + 26), paint(hexc("#0B1F45", .35), blur=26))
        c.drawRRect(skia.RRect.MakeRectXY(big, 14, 14), paint(hexc(CORAL_D)))
        for k in range(3, 0, -1):  # page block edges
            c.drawRect(rect.makeOffset(k * 2, k * 2), paint(hexc("#D3DCEA" if k % 2 else "#F1F4F9")))

    def draw(self, t):
        c = self.surf.getCanvas(); c.save(); c.scale(self.scale, self.scale); W, H = self.W, self.H; L = self.L
        c.clear(hexc(TABLE))
        c.drawRect(R(0, 0, W, H), paint(0, shader=skia.GradientShader.MakeRadial(skia.Point(W / 2, H * 0.45), max(W, H) * 0.8, [hexc(TABLE_L), hexc(TABLE_D)])))
        grain(c, R(0, 0, W, H), .10)
        cx, cy, z = self.cam(t)
        c.save(); c.translate(W / 2, H / 2); c.scale(z, z); c.translate(-cx, -cy)
        underA, underB, boardA, turn = book_state(t)
        if boardA: self.board(c, "A")
        self.board(c, "B")
        if underA is not None: self.page(c, t, underA, "A")
        if underB is not None: self.page(c, t, underB, "B")
        if turn: self.turning(c, t, *turn)
        if t > END_OPEN[0] + END_OPEN[1] - 0.05: endcard(c, t, L, self.TX)
        c.restore(); c.restore()
        return self.surf.makeImageSnapshot().toarray()

    def turning(self, c, t, u, forward, front, back):
        L = self.L; th = math.pi * u; s = math.cos(th); lift = 0.05 * math.sin(th)
        src, dst = ("B", "A") if forward else ("A", "B")
        key, side = (front, src) if s > 0 else (back, dst)
        a = abs(s)
        def xf():
            if L["o"] == "L": c.scale(a, 1 + lift)
            else: c.scale(1 + lift, a)
        rect = L["rA"] if side == "A" else L["rB"]
        # cast shadow on the page below
        c.save(); xf()
        sr = R(rect.left() - 16, rect.top() - 16, rect.right() + 16, rect.bottom() + 16)
        off = 40 * math.sin(th)
        c.drawRect(sr.makeOffset(off * (1 if L["o"] == "L" else 0.3), off * (0.3 if L["o"] == "L" else 1)), paint(hexc("#0B1F45", .3 * math.sin(th)), blur=30))
        c.restore()
        c.save(); xf()
        is_cover = key == "cover" or (key == 0 and front == "cover") or (key == "endA") or (not forward)
        if is_cover:  # the board travels with this sheet
            m = 16; c.drawRRect(skia.RRect.MakeRectXY(R(rect.left() - m, rect.top() - m, rect.right() + m, rect.bottom() + m), 14, 14), paint(hexc(CORAL_D)))
        self.page(c, t, key, side)
        c.drawRect(R(rect.left() - 16, rect.top() - 16, rect.right() + 16, rect.bottom() + 16), paint(hexc("#0B1F45", .3 * (1 - a))))
        c.restore()

    def frame(self, t, fps):
        dt = 1 / fps; a, b = np.array(self.cam(t - dt / 2)), np.array(self.cam(t + dt / 2))
        speed = math.hypot(*(b[:2] - a[:2])) * a[2] + abs(b[2] - a[2]) * 2000
        st = book_state(t)[3]
        n = 1 if speed < 4 else int(min(10, 3 + speed / 6))
        if st is not None and 0.05 < st[0] < 0.95: n = max(n, 4)
        if n == 1: return self.draw(t)
        acc = sum(self.draw(t + dt * (k / n - 0.5)).astype(np.float32) for k in range(n)); return (acc / n).astype(np.uint8)

if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--orient", default="L"); ap.add_argument("--scale", type=float, default=1.0); ap.add_argument("--fps", type=int, default=FPS)
    ap.add_argument("--lang", default="en"); ap.add_argument("--out", required=True); ap.add_argument("--audio", default=None)
    ap.add_argument("--still", type=float, nargs="*")
    a = ap.parse_args(); Rr = Renderer(a.orient, a.scale, a.lang)
    if a.still:
        import cv2
        for t in a.still: cv2.imwrite(a.out.replace(".png", f"_{t:05.2f}.png"), Rr.draw(t)[:, :, :3])
        sys.exit()
    audio = a.audio or f"{ROOT}/audio/mix_{a.lang}.wav"
    w, h = Rr.surf.width(), Rr.surf.height()
    cmd = ["ffmpeg", "-y", "-loglevel", "error", "-f", "rawvideo", "-pix_fmt", "bgra", "-s", f"{w}x{h}", "-r", str(a.fps), "-i", "-"]
    if os.path.exists(audio): cmd += ["-i", audio, "-c:a", "aac", "-b:a", "192k", "-shortest"]
    cmd += ["-c:v", "libx264", "-preset", "medium", "-crf", "17", "-pix_fmt", "yuv420p", "-movflags", "+faststart", a.out]
    ff = subprocess.Popen(cmd, stdin=subprocess.PIPE)
    N = int(DURATION * a.fps)
    for f in range(N):
        ff.stdin.write(Rr.frame(f / a.fps, a.fps).tobytes())
        if f % (a.fps * 2) == 0: print(f"{f / a.fps:5.1f}s", flush=True)
    ff.stdin.close(); ff.wait(); print("done", a.out)
