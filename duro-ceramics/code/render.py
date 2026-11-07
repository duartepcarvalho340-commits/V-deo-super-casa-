"""Duro Ceramics spec film renderer (independent concept, not affiliated with Duro Ceramics / Duro Designers).

Concept "Da roda à mesa": one round form that keeps transforming. Clay on the wheel -> thrown plate -> glazed ->
hand-painted on the banding wheel -> lifted onto a set table -> swallows on a lime wall -> a stack of plates ->
the logo painted by hand -> the plate flips and the end card is the potter's mark on its back.
Everything is drawn with Skia (vector 2D) and piped to FFmpeg.
Usage:
  python3 code/render.py --orient L --out exports/duro_spec_PT_1920x1080.mp4
  python3 code/render.py --orient V --scale 0.5 --out previews/s.png --still 1 4 8
"""
import argparse, math, os, subprocess, sys
import numpy as np, skia
from scipy.ndimage import gaussian_filter
sys.path.insert(0, os.path.dirname(__file__))
from timing import FPS, DURATION, EV, TEXT, NAME, HANDLE, MONOGRAM

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
FD = f"{ROOT}/assets/fonts"
TF = {"serif": "cormorant-garamond-600-normal.ttf", "ital": "cormorant-garamond-600-italic.ttf", "serifb": "cormorant-garamond-700-normal.ttf",
      "sans": "manrope-600-normal.ttf", "sansb": "manrope-700-normal.ttf", "sansm": "manrope-500-normal.ttf", "script": "caveat-700-normal.ttf"}
TF = {k: skia.Typeface.MakeFromFile(f"{FD}/{v}") for k, v in TF.items()}

# ---------------- palette ----------------
def hexc(h, a=1.0):
    h = h.lstrip("#"); return skia.Color(int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16), int(max(0, min(1, a)) * 255))
COBALT, COBALT_D, COBALT_L = "#2546A4", "#183076", "#3A62C4"
CORAL, TURQ, OCHRE, GREEN, PINK = "#E2603F", "#1E9C9A", "#E7A93A", "#6DB33F", "#E07AA0"
FISH_COLS = [COBALT, CORAL, TURQ, OCHRE, GREEN, PINK]
GLAZE, GLAZE_D, GLAZE_E = "#F8F4EC", "#E9E2D5", "#C9BFAE"
CLAY, CLAY_L, CLAY_D = "#A65834", "#CF7F51", "#6E361F"
BISQUE, BISQUE_D = "#E6CDAE", "#CBAE8B"
INK, INK_S, CREAM, CREAM_S = "#2A1E17", "#6B5848", "#F4EBDD", "#D9A066"
LINEN, WALL, STUDIO = "#E9E1D3", "#F2EDE3", "#1C1714"

# ---------------- maths ----------------
clamp = lambda x, a=0.0, b=1.0: max(a, min(b, x))
lerp = lambda a, b, t: a + (b - a) * t
def sstep(a, b, x): t = clamp((x - a) / (b - a)); return t * t * (3 - 2 * t)
def ease_out(t): t = clamp(t); return 1 - (1 - t) ** 3
def ease_in(t): t = clamp(t); return t ** 3
def ease_io(t): t = clamp(t); return 4 * t ** 3 if t < .5 else 1 - (-2 * t + 2) ** 3 / 2
def back_out(t, c=1.6): t = clamp(t); return 1 + (c + 1) * (t - 1) ** 3 + c * (t - 1) ** 2
def win(t, a, b, fi=0.45, fo=0.35):
    """0..1 envelope: in at a, out at b"""
    return sstep(a, a + fi, t) * (1 - sstep(b - fo, b, t))

# wheel speed (rad/s) -> plate angle
_W = [(0, 0), (0.30, 0), (0.75, 8.5), (4.2, 8.5), (4.9, 2.8), (5.22, 2.8), (5.42, 11.5), (5.88, 11.5), (6.03, 3.49),
      (7.62, 3.49), (7.85, 1.0), (8.18, 0), (99, 0)]
_TT = np.arange(0, DURATION + 1, 0.001); _OM = np.interp(_TT, [k[0] for k in _W], [k[1] for k in _W]); _TH = np.cumsum(_OM) * 0.001
def theta(t): return float(np.interp(t, _TT, _TH))

# ---------------- drawing helpers ----------------
def paint(color, **kw):
    p = skia.Paint(AntiAlias=True, Color=color)
    if "stroke" in kw: p.setStyle(skia.Paint.kStroke_Style); p.setStrokeWidth(kw["stroke"]); p.setStrokeCap(skia.Paint.kRound_Cap); p.setStrokeJoin(skia.Paint.kRound_Join)
    if kw.get("blur", 0) > 0: p.setMaskFilter(skia.MaskFilter.MakeBlur(skia.kNormal_BlurStyle, kw["blur"]))
    if "shader" in kw: p.setShader(kw["shader"]); p.setAlphaf(1.0)
    if kw.get("effect") is not None: p.setPathEffect(kw["effect"])
    if kw.get("blend") is not None: p.setBlendMode(kw["blend"])
    return p
def R(l, t, r, b): return skia.Rect.MakeLTRB(l, t, r, b)
def circ(r, x=0, y=0): return R(x - r, y - r, x + r, y + r)
def P(x, y): return skia.Point(x, y)
def layer_alpha(c, a): c.saveLayerAlpha(None, int(clamp(a) * 255))
def lin(p0, p1, cols, pos=None): return skia.GradientShader.MakeLinear([P(*p0), P(*p1)], [hexc(*x) if isinstance(x, tuple) else hexc(x) for x in cols], pos)
def rad(p, r, cols, pos=None): return skia.GradientShader.MakeRadial(P(*p), r, [hexc(*x) if isinstance(x, tuple) else hexc(x) for x in cols], pos)

def text_w(s, size, tf, track=0.0): return skia.Font(TF[tf], size).measureText(s) + track * size * max(0, len(s) - 1)
def text(c, s, x, y, size, color, tf="serif", align="c", track=0.0):
    """y is the visual centre of the cap height"""
    f = skia.Font(TF[tf], size); f.setSubpixel(True); w = text_w(s, size, tf, track)
    x0 = x + {"c": -w / 2, "l": 0, "r": -w}[align]; yb = y + size * 0.33; p = paint(color)
    if track == 0: c.drawString(s, x0, yb, f, p)
    else:
        for ch in s: c.drawString(ch, x0, yb, f, p); x0 += f.measureText(ch) + track * size
    return w
def fit(s, size, tf, maxw, track=0.0): return min(size, size * maxw / max(1, text_w(s, size, tf, track)))

def make_tile(arr):
    img = np.ascontiguousarray(np.clip(arr, 0, 255).astype(np.uint8))
    return skia.Image.fromarray(img)
def grain_tile(n=256, seed=3, amp=30):
    g = np.random.default_rng(seed).normal(0, 1, (n, n)); v = 128 + g * amp
    a = np.zeros((n, n, 4)); a[..., 0] = a[..., 1] = a[..., 2] = v; a[..., 3] = 255; return make_tile(a)
def colour_tile(n, base, var, seed, sig, extra=None):
    rng = np.random.default_rng(seed); g = gaussian_filter(rng.normal(0, 1, (n, n)), sig, mode="wrap"); g /= g.std() + 1e-9
    if extra is not None: g = g + extra(rng, n)
    b = np.array([int(base[i:i + 2], 16) for i in (1, 3, 5)], float)
    a = np.zeros((n, n, 4)); a[..., :3] = b + g[..., None] * np.array(var, float); a[..., 3] = 255; return make_tile(a)
def linen_extra(rng, n):
    h = gaussian_filter(rng.normal(0, 1, (n, 1)), (1.2, 0), mode="wrap") * np.ones((1, n))
    v = gaussian_filter(rng.normal(0, 1, (1, n)), (0, 1.2), mode="wrap") * np.ones((n, 1))
    fine = rng.normal(0, 1, (n, n)) * 0.5
    return 0.9 * h + 0.9 * v + fine
TILES = {}
def tile_shader(name, offset=(0, 0), scale=1.0):
    if name not in TILES:
        TILES[name] = {"grain": lambda: grain_tile(),
                       "linen": lambda: colour_tile(512, LINEN, (5, 5, 6), 11, 6, linen_extra),
                       "wall": lambda: colour_tile(512, WALL, (2.2, 2.2, 2.6), 21, 22, lambda r, n: gaussian_filter(r.normal(0, 1, (n, n)), 1.2, mode="wrap") * 0.7),
                       "clay": lambda: colour_tile(256, "#808080", (30, 30, 30), 5, 1.5)}[name]()
    m = skia.Matrix(); m.setScale(scale, scale); m.postTranslate(*offset)
    return TILES[name].makeShader(skia.TileMode.kRepeat, skia.TileMode.kRepeat, skia.SamplingOptions(skia.FilterMode.kLinear), m)
def grain(c, rect, t, a=0.07):
    rng = np.random.default_rng(int(t * 60) + 1)
    p = skia.Paint(Shader=tile_shader("grain", (float(rng.integers(0, 256)), float(rng.integers(0, 256)))), Alpha=int(a * 255))
    p.setBlendMode(skia.BlendMode.kOverlay); c.drawRect(rect, p)
def vignette(c, W, H, a=0.45, col="#000000"):
    c.drawRect(R(0, 0, W, H), paint(0, shader=rad((W / 2, H / 2), math.hypot(W, H) * 0.62, [(col, 0), (col, 0), (col, a)], [0, 0.55, 1])))

# ---------------- motifs (hand-painted look) ----------------
def fish_path():
    p = skia.Path(); p.moveTo(0.50, 0.00)
    p.cubicTo(0.47, -0.10, 0.30, -0.150, 0.05, -0.145); p.cubicTo(-0.18, -0.14, -0.33, -0.07, -0.40, -0.030)
    p.lineTo(-0.53, -0.135); p.cubicTo(-0.49, -0.05, -0.49, 0.05, -0.53, 0.135); p.lineTo(-0.40, 0.030)
    p.cubicTo(-0.33, 0.07, -0.18, 0.13, 0.05, 0.135); p.cubicTo(0.30, 0.14, 0.47, 0.09, 0.50, 0.00); p.close(); return p
FISH = fish_path()
def dorsal_path():
    p = skia.Path(); p.moveTo(-0.08, -0.14); p.cubicTo(-0.04, -0.21, 0.04, -0.22, 0.08, -0.145); p.close(); return p
DORSAL = dorsal_path()

def painted_fish(c, x, y, L, ang, col, reveal=1.0, glossy=False, belly=True):
    """sardine centred at (x,y), length L, angle ang (rad, head direction); reveal 0..1 from tail to head"""
    if reveal <= 0: return
    c.save(); c.translate(x, y); c.rotate(math.degrees(ang)); c.scale(L, L)
    if reveal < 1: c.clipRect(R(-0.6, -0.4, -0.53 + 1.06 * reveal, 0.4), True)
    pc = hexc(col, 0.95)
    c.drawPath(DORSAL, paint(pc)); c.drawPath(FISH, paint(pc))
    c.save(); c.clipPath(FISH, doAntiAlias=True)
    if belly: c.drawOval(R(-0.40, 0.02, 0.48, 0.20), paint(hexc("#FFFFFF", .30)))
    sp = paint(hexc("#FFFFFF", .55), stroke=0.012)  # scales: overlapping arcs
    for i in range(9):
        sx = -0.30 + i * 0.065
        for j in range(-2, 3):
            sy = j * 0.05 + (0.025 if i % 2 else 0)
            pa = skia.Path(); pa.addArc(R(sx - 0.035, sy - 0.03, sx + 0.035, sy + 0.03), -70, 140); c.drawPath(pa, sp)
    c.drawPath(FISH, paint(hexc("#000000", .18), stroke=0.018))
    c.restore()
    g = skia.Path(); g.moveTo(0.31, -0.125); g.quadTo(0.24, 0.0, 0.30, 0.115); c.drawPath(g, paint(hexc("#FFFFFF", .8), stroke=0.016))
    if reveal > 0.92:
        c.drawCircle(0.40, -0.028, 0.030, paint(hexc("#FFFFFF"))); c.drawCircle(0.405, -0.028, 0.015, paint(hexc("#1A1A1A")))
    if glossy:
        h = skia.Path(); h.moveTo(-0.25, -0.10); h.cubicTo(-0.05, -0.135, 0.20, -0.135, 0.38, -0.09)
        c.drawPath(h, paint(hexc("#FFFFFF", .75), stroke=0.022, blur=0.006))
    c.restore()

def swallow_parts(flex=0.0):
    b = skia.Path(); b.moveTo(0, -0.56)
    b.cubicTo(0.12, -0.56, 0.16, -0.42, 0.13, -0.28); b.cubicTo(0.10, -0.10, 0.09, 0.10, 0.07, 0.30); b.lineTo(0.27, 0.88)
    b.cubicTo(0.16, 0.66, 0.06, 0.50, 0.0, 0.44); b.cubicTo(-0.06, 0.50, -0.16, 0.66, -0.27, 0.88); b.lineTo(-0.07, 0.30)
    b.cubicTo(-0.09, 0.10, -0.10, -0.10, -0.13, -0.28); b.cubicTo(-0.16, -0.42, -0.12, -0.56, 0, -0.56); b.close()
    ws = []
    for s in (1, -1):
        k = 1 + flex; ty = 0.10 - 0.25 * flex
        w = skia.Path(); w.moveTo(s * 0.06, -0.24)
        w.cubicTo(s * 0.35 * k, -0.46 - 0.1 * flex, s * 0.86 * k, -0.30, s * 1.06 * k, ty)
        w.cubicTo(s * 0.74 * k, -0.02, s * 0.40 * k, 0.06, s * 0.07, 0.14); w.close(); ws.append(w)
    return b, ws

def swallow(c, x, y, S, ang, col, flex=0.0, shadow=(0.10, 0.16), sh_a=0.30, alpha=1.0, flat=False):
    """ceramic swallow facing `ang` (rad, 0 = up). shadow offset in units of S (screen-down-right)"""
    if alpha <= 0: return
    b, ws = swallow_parts(flex)
    if alpha < 1: layer_alpha(c, alpha)
    if shadow and not flat:
        c.save(); c.translate(x + shadow[0] * S, y + shadow[1] * S); c.rotate(math.degrees(ang)); c.scale(S, S)
        sp = paint(hexc("#2A1A10", sh_a), blur=0.05)
        for pth in [b] + ws: c.drawPath(pth, sp)
        c.restore()
    c.save(); c.translate(x, y); c.rotate(math.degrees(ang)); c.scale(S, S)
    if flat: fp = paint(hexc(col, .95))
    else:
        cl = skia.Color4f(hexc(col)); light = skia.Color4f(min(1, cl.fR * 1.25 + .08), min(1, cl.fG * 1.25 + .08), min(1, cl.fB * 1.25 + .08), 1).toColor()
        dark = skia.Color4f(cl.fR * .62, cl.fG * .62, cl.fB * .62, 1).toColor()
        fp = skia.Paint(AntiAlias=True, Shader=skia.GradientShader.MakeLinear([P(-0.8, -0.6), P(0.8, 0.8)], [light, hexc(col), dark]))
    for pth in ws + [b]: c.drawPath(pth, fp)
    if not flat:
        hp = paint(hexc("#FFFFFF", .6), stroke=0.022, blur=0.008)
        for s in (1, -1):
            h = skia.Path(); h.moveTo(s * 0.12, -0.30); h.cubicTo(s * 0.40, -0.44, s * 0.75, -0.34, s * 0.95, -0.08); c.drawPath(h, hp)
        c.drawCircle(-0.04, -0.46, 0.035, paint(hexc("#FFFFFF", .7), blur=0.01))
        c.drawLine(0, -0.20, 0, 0.30, paint(hexc("#FFFFFF", .18), stroke=0.03, blur=0.02))
    c.restore()
    if alpha < 1: c.restore()

# ---------------- plates ----------------
def plate_shadow(c, R_, lift=0.0, a=0.42):
    off = R_ * (0.035 + 0.10 * lift); bl = R_ * (0.035 + 0.10 * lift)
    c.drawCircle(off * 0.7, off, R_ * (1 + 0.02 * lift), paint(hexc("#140C06", a * (1 - 0.35 * lift)), blur=bl))
def glazed_plate(c, R_, rot_deg, pattern=None, lift=0.0, shadow=True, edge=True, base=GLAZE):
    """centred at origin. pattern(c, R_) is drawn in the plate's rotating frame, under the glaze highlight"""
    if shadow: plate_shadow(c, R_, lift)
    if edge: c.drawCircle(0, R_ * 0.022, R_, paint(hexc(GLAZE_E)))
    c.drawCircle(0, 0, R_, paint(0, shader=rad((-0.25 * R_, -0.3 * R_), 1.35 * R_, [base, base, GLAZE_D], [0, .55, 1])))
    # well: concave -> top-left inner wall darker, bottom-right lit
    c.drawCircle(0, 0, 0.64 * R_, paint(0, shader=lin((-0.6 * R_, -0.6 * R_), (0.6 * R_, 0.6 * R_), [("#D8CFBF", 1), (base, 1), ("#FFFFFF", 1)])))
    c.drawCircle(0, 0, 0.60 * R_, paint(hexc(base)))
    if pattern is not None:
        c.save(); c.clipPath(skia.Path().addCircle(0, 0, R_ * 0.985), doAntiAlias=True); c.rotate(rot_deg); pattern(c, R_); c.restore()
    # glaze highlights (fixed light, do not rotate)
    c.drawOval(R(-0.62 * R_, -0.70 * R_, -0.05 * R_, -0.38 * R_), paint(hexc("#FFFFFF", .38), blur=0.07 * R_))
    arc = skia.Path(); arc.addArc(circ(0.955 * R_), 195, 70); c.drawPath(arc, paint(hexc("#FFFFFF", .85), stroke=0.018 * R_, blur=0.004 * R_))
    arc = skia.Path(); arc.addArc(circ(0.62 * R_), 15, 70); c.drawPath(arc, paint(hexc("#FFFFFF", .7), stroke=0.012 * R_, blur=0.004 * R_))
    c.drawCircle(0, 0, R_, paint(hexc("#000000", .10), stroke=0.012 * R_))

def pat_rosette(t_paint=99.0):
    """the sardine plate painted on the banding wheel; t_paint = current time (for progressive painting)"""
    def f(c, R_):
        ring_k = PAINT["ring"](t_paint)
        if ring_k[1] > 0:
            a = skia.Path(); a.addArc(circ(0.86 * R_), ring_k[0], ring_k[1])
            c.drawPath(a, paint(hexc(COBALT, .93), stroke=0.075 * R_, blur=0.002 * R_))
            if ring_k[1] >= 359.9:
                c.drawCircle(0, 0, 0.955 * R_, paint(hexc(COBALT, .9), stroke=0.012 * R_))
        for k, (ang, rev) in enumerate(PAINT["fish"](t_paint)):
            if rev <= 0: continue
            rr_ = 0.35 * R_; painted_fish(c, math.cos(ang) * rr_, math.sin(ang) * rr_, 0.40 * R_, ang, FISH_COLS[k], rev)
        for (x, y, r, col, k) in PAINT["dots"](t_paint):
            if k > 0: c.drawCircle(x * R_, y * R_, r * R_ * back_out(k, 2.2), paint(hexc(col, .93)))
    return f

def pat_splash(c, R_):
    rng = np.random.default_rng(4)
    c.drawCircle(0, 0, 0.94 * R_, paint(hexc(COBALT, .9), stroke=0.03 * R_))
    for i in range(46):
        a = rng.uniform(0, 2 * math.pi); r = math.sqrt(rng.uniform(0.0, 0.8)) * R_; s = rng.uniform(0.025, 0.085) * R_
        col = FISH_COLS[i % 6]; x, y = math.cos(a) * r, math.sin(a) * r
        c.drawCircle(x, y, s, paint(hexc(col, .9)))
        for _ in range(2):
            b = rng.uniform(0, 2 * math.pi); d = s * rng.uniform(1.3, 2.0)
            c.drawCircle(x + math.cos(b) * d, y + math.sin(b) * d, s * rng.uniform(0.15, 0.3), paint(hexc(col, .9)))
def pat_calcada(c, R_):
    c.save(); c.clipPath(skia.Path().addCircle(0, 0, 0.6 * R_), doAntiAlias=True)
    lam = 0.42 * R_; A = 0.07 * R_; band = 0.085 * R_
    for j in range(-8, 9, 2):
        y0 = j * band; p = skia.Path(); xs = np.linspace(-R_, R_, 60)
        for i, x in enumerate(xs):
            y = y0 + A * math.sin(2 * math.pi * x / lam)
            (p.moveTo if i == 0 else p.lineTo)(x, y)
        for x in xs[::-1]: p.lineTo(x, y0 + band + A * math.sin(2 * math.pi * x / lam))
        p.close(); c.drawPath(p, paint(hexc("#2E2E34", .9)))
    c.restore()
    c.drawCircle(0, 0, 0.6 * R_, paint(hexc("#2E2E34", .9), stroke=0.02 * R_))
    for i in range(24):
        a = i / 24 * 2 * math.pi; c.drawCircle(math.cos(a) * 0.82 * R_, math.sin(a) * 0.82 * R_, 0.03 * R_, paint(hexc(OCHRE if i % 2 else COBALT, .9)))
def pat_swallows(c, R_):
    c.drawCircle(0, 0, 0.93 * R_, paint(hexc(CORAL, .9), stroke=0.022 * R_))
    c.drawCircle(0, 0, 0.84 * R_, paint(hexc(CORAL, .9), stroke=0.008 * R_))
    for k, col in enumerate((COBALT, TURQ, COBALT)):
        a = -math.pi / 2 + k * 2 * math.pi / 3
        swallow(c, math.cos(a) * 0.36 * R_, math.sin(a) * 0.36 * R_, 0.2 * R_, a + math.pi * 0.62, col, flat=True)
def pat_white(c, R_): pass

# --- progressive painting (banding wheel), all in plate-local angles ---
PHI_B = -0.72  # world angle of the brush (up-right)
def _ring(t):
    t0, t1 = EV["ring"], EV["ring_end"]
    if t <= t0: return (0, 0)
    sweep = math.degrees(theta(min(t, t1)) - theta(t0))
    start = math.degrees(PHI_B - theta(min(t, t1)))
    return (start, min(360.0, sweep))
FISH_T = [EV["fish0"] + k * EV["fish_dur"] for k in range(6)]; FISH_D = 0.24
def _fish(t):
    out = []
    for tk in FISH_T:
        ang = PHI_B - theta(tk + FISH_D / 2); out.append((ang, clamp((t - tk) / FISH_D)))
    return out
_rng = np.random.default_rng(9)
DOTS = []
for i in range(18):
    a = i / 18 * 2 * math.pi + 0.17; r = 0.70 if i % 2 else 0.64
    DOTS.append((math.cos(a) * r, math.sin(a) * r, 0.022 if i % 2 else 0.016, FISH_COLS[(i * 5) % 6], EV["dots"] + i * 0.016))
DOTS += [(0, 0, 0.055, OCHRE, EV["dots"] + 0.0)] + [(math.cos(a) * 0.075, math.sin(a) * 0.075, 0.026, CORAL, EV["dots"] + 0.05 + j * 0.02) for j, a in enumerate(np.linspace(0, 2 * math.pi, 6, endpoint=False))]
def _dots(t): return [(x, y, r, col, clamp((t - td) / 0.08)) for (x, y, r, col, td) in DOTS]
PAINT = {"ring": _ring, "fish": _fish, "dots": _dots}

def brush_tip(t, R_):
    """world (plate-centred) position of the brush tip and its height above the plate (0 = touching)"""
    def loc_to_world(lx, ly, tt):
        th = theta(tt); return (lx * math.cos(th) - ly * math.sin(th), lx * math.sin(th) + ly * math.cos(th))
    ring_pt = (math.cos(PHI_B) * 0.86 * R_, math.sin(PHI_B) * 0.86 * R_)
    far = (math.cos(PHI_B + 0.25) * 2.6 * R_, math.sin(PHI_B + 0.25) * 2.6 * R_)
    if t < EV["ring"]:
        u = ease_out((t - EV["brush_in"]) / (EV["ring"] - EV["brush_in"])); return lerp(far[0], ring_pt[0], u), lerp(far[1], ring_pt[1], u), 1 - u
    if t < EV["ring_end"]: return ring_pt[0], ring_pt[1], 0.0
    fish = _fish(t)
    for k, tk in enumerate(FISH_T):
        ang = fish[k][0]
        tail = loc_to_world(math.cos(ang) * 0.35 * R_ - math.cos(ang) * 0.2 * R_, math.sin(ang) * 0.35 * R_ - math.sin(ang) * 0.2 * R_, t)
        head = loc_to_world(math.cos(ang) * 0.35 * R_ + math.cos(ang) * 0.2 * R_, math.sin(ang) * 0.35 * R_ + math.sin(ang) * 0.2 * R_, t)
        prev_end = (ring_pt[0], ring_pt[1]) if k == 0 else None
        t_start = EV["ring_end"] if k == 0 else FISH_T[k - 1] + FISH_D
        if t < tk:  # travelling to the tail of fish k (lifted)
            if k == 0: p0 = ring_pt
            else:
                pa = fish[k - 1][0]; p0 = loc_to_world(math.cos(pa) * 0.55 * R_, math.sin(pa) * 0.55 * R_, t)
            u = ease_io((t - t_start) / max(0.01, tk - t_start)); return lerp(p0[0], tail[0], u), lerp(p0[1], tail[1], u), math.sin(math.pi * u) * 0.6
        if t < tk + FISH_D:
            u = (t - tk) / FISH_D; return lerp(tail[0], head[0], u), lerp(tail[1], head[1], u), 0.0
    last = fish[5][0]; p0 = loc_to_world(math.cos(last) * 0.55 * R_, math.sin(last) * 0.55 * R_, t)
    if t < EV["dots"]:
        u = ease_io((t - FISH_T[5] - FISH_D) / (EV["dots"] - FISH_T[5] - FISH_D)); return lerp(p0[0], 0, u), lerp(p0[1], 0, u), math.sin(math.pi * u) * 0.5
    # dabbing the dots
    i = int(clamp((t - EV["dots"]) / 0.016, 0, len(DOTS) - 1)); x, y = DOTS[min(i, 17)][:2]
    if t < EV["dots"] + 0.3: q = loc_to_world(x * R_, y * R_, t); return q[0], q[1], 0.15 + 0.15 * math.sin(t * 60)
    u = ease_in((t - EV["dots"] - 0.3) / (EV["brush_out"] + 0.25 - EV["dots"] - 0.3)); q = loc_to_world(x * R_, y * R_, t)
    return lerp(q[0], far[0], u), lerp(q[1], far[1], u), u

def brush(c, x, y, h, phi_h, col, scale=1.0):
    """artist's brush seen from above; tip at (x,y); handle towards phi_h; h = height (0..1)"""
    s = scale * (1 + 0.10 * h); ux, uy = math.cos(phi_h), math.sin(phi_h)
    sh = (22 + 90 * h) * scale, (34 + 120 * h) * scale
    def shape(cc, ox, oy, p_bristle, p_ferr, p_wood, p_dark):
        cc.save(); cc.translate(x + ox, y + oy); cc.rotate(math.degrees(phi_h)); cc.scale(s, s)
        b = skia.Path(); b.moveTo(0, 0); b.cubicTo(18, -4, 46, -13, 78, -12); b.lineTo(78, 12); b.cubicTo(46, 13, 18, 4, 0, 0); b.close()
        cc.drawPath(b, p_bristle)
        cc.drawRoundRect(R(76, -13, 132, 13), 3, 3, p_ferr)
        w = skia.Path(); w.moveTo(130, -12); w.lineTo(980, -18); w.lineTo(980, 18); w.lineTo(130, 12); w.close(); cc.drawPath(w, p_wood)
        if p_dark is not None:
            cc.drawLine(140, -6, 970, -9, paint(hexc("#FFFFFF", .25), stroke=3)); cc.drawRect(R(76, 4, 132, 13), p_dark)
            tipp = skia.Path(); tipp.moveTo(0, 0); tipp.cubicTo(10, -3, 22, -7, 30, -7); tipp.lineTo(30, 7); tipp.cubicTo(22, 7, 10, 3, 0, 0); tipp.close()
            cc.drawPath(tipp, paint(hexc(col)))
        cc.restore()
    sp = paint(hexc("#120A05", .30 * (1 - 0.4 * h)), blur=8 + 14 * h)
    shape(c, sh[0], sh[1], sp, sp, sp, None)
    shape(c, 0, 0, paint(hexc("#3B2A20")), paint(0, shader=lin((0, -13), (0, 13), ["#E8E6E1", "#9A958C", "#5E5A55"])),
          paint(0, shader=lin((0, -18), (0, 18), ["#E2B783", "#B9824E", "#7C5230"])), paint(hexc("#000000", .25)))

# ---------------- layout ----------------
def layout(o):
    if o == "L":
        return dict(o=o, W=1920, H=1080, R=380, pc=(1270, 540), txt=(150, 540, "l"), txt_tab=(150, 540, "l"), txt_wall=(150, 520, "l"),
                    txt_stack=(150, 540, "l"), hsize=104, maxw=860, phi_h=-0.55,
                    cam_tab=(-560, 0, 0.56), stack_pc=(1290, 545), stack_R=350, end_pc=(960, 500), essence_y=975, disc_y=1010,
                    swallows=[(1170, 735, 150), (1450, 540, 126), (1700, 365, 106)], tile=128, band_y=944,
                    items=dict(platter=(-800, -560, 420, 280, -14), bowl_t=(-660, 560, 235), bowl_c=(730, -720, 205), cup=(975, 235, 140),
                               fish=(600, 660, 560, -28), lemon=(-1500, 690, -25), half=(-1240, 880), sprig=(-1760, -760, 30), napkin=(-2050, 830, 8)))
    return dict(o=o, W=1080, H=1920, R=400, pc=(540, 850), txt=(540, 1580, "c"), txt_tab=(540, 330, "c"), txt_wall=(540, 380, "c"),
                txt_stack=(540, 360, "c"), hsize=100, maxw=960, phi_h=-0.95,
                cam_tab=(0, -300, 0.6), stack_pc=(540, 1180), stack_R=390, end_pc=(540, 860), essence_y=1400, disc_y=1420,
                swallows=[(290, 1330, 185), (600, 1085, 158), (880, 855, 132)], tile=135, band_y=1650,
                items=dict(platter=(-330, -820, 360, 240, 12), bowl_t=(-560, 610, 210), bowl_c=(590, -540, 185), cup=(-700, 40, 130),
                           fish=(470, 650, 470, -30), lemon=(700, 120, -60), half=(640, 1110), sprig=(-600, 1130, -20), napkin=(-120, 1330, 6)))

# ---------------- headline / kicker ----------------
def kicker(c, s, x, y, size, col, k, align="l"):
    if k <= 0: return
    layer_alpha(c, k); w = text_w(s, size, "sansb", 0.32)
    x0 = x if align == "l" else x - w / 2 + 34
    c.drawLine(x0 - (0 if align == "l" else 34), y, x0 - (0 if align == "l" else 34) + 22 * k, y, paint(hexc(col), stroke=2.2))
    text(c, s, x0 + 34 if align == "l" else x0, y, size, hexc(col), "sansb", "l", 0.32); c.restore()

def headline(c, lines, x, y, size, col, t, t0, t1, align="l", maxw=900):
    """lines rise one by one from behind a mask; y = vertical centre of the block"""
    if t < t0 or t > t1: return
    size = min([fit(s, size, tf, maxw) for s, tf in lines] + [size])
    lh = size * 1.02; top = y - lh * len(lines) / 2 + lh / 2
    out = sstep(t1 - 0.35, t1, t)
    for i, (s, tf) in enumerate(lines):
        u = ease_out((t - t0 - i * 0.09) / 0.6)
        if u <= 0: continue
        ly = top + i * lh; w = text_w(s, size, tf)
        x0 = {"l": x, "c": x - w / 2, "r": x - w}[align]
        c.save(); c.clipRect(R(x0 - 40, ly - size * 0.75, x0 + w + 60, ly + size * 0.62))
        layer_alpha(c, u * (1 - out)); text(c, s, x0, ly + (1 - u) * size * 0.9 - out * size * 0.25, size, hexc(col), tf, "l"); c.restore()
        c.restore()
    return top - lh / 2

def script_line(c, s, x, y, size, col, t, t0, dur, t1, align="l"):
    if t < t0 or t > t1: return
    w = text_w(s, size, "script"); x0 = {"l": x, "c": x - w / 2}[align]; u = clamp((t - t0) / dur)
    c.save(); c.clipRect(R(x0 - 20, y - size, x0 - 20 + (w + 40) * u, y + size)); layer_alpha(c, 1 - sstep(t1 - 0.3, t1, t))
    text(c, s, x0, y, size, hexc(col), "script", "l"); c.restore(); c.restore()

# ---------------- scenes ----------------
WHEEL_STREAKS = [(r, a, l, w, al, li) for r, a, l, w, al, li in zip(*[np.random.default_rng(1).uniform(lo, hi, 130) for lo, hi in
                 ((0.5, 1.47), (0, 360), (15, 90), (1.5, 7), (0.05, 0.2), (0, 1))])]

def clay_form(c, t, R_):
    """clay from the drop to the thrown plate (in the rotating frame, origin = wheel centre)"""
    th = theta(t); r0 = 0.42 * R_
    land = EV["clay_land"]
    if t < land:  # falling towards the wheel (shrinks as it gets further from camera)
        u = clamp((t - EV["clay_drop"]) / (land - EV["clay_drop"])); s = lerp(2.3, 1.0, u * u)
        c.drawCircle(0.05 * R_ * s, 0.07 * R_ * s, r0 * (0.75 + 0.25 * u), paint(hexc("#000000", .5 * u), blur=40 * (1 - u) + 10))
        c.drawCircle(0, 0, r0 * s, paint(0, shader=rad((-0.35 * r0 * s, -0.4 * r0 * s), 1.4 * r0 * s, [CLAY_L, CLAY, CLAY_D], [0, .5, 1])))
        return
    dt = t - land; squash = 1 + 0.10 * math.exp(-dt * 8) * math.cos(dt * 28)
    so = ease_io((t - EV["open_start"]) / (EV["open_end"] - EV["open_start"]))
    Rout = lerp(r0 * squash, R_, so); amp = 0.09 * (1 - sstep(land, EV["centre_end"], t)) * (1 - so)
    # wobbly outline (centring)
    pth = skia.Path(); n = 90
    for i in range(n + 1):
        a = i / n * 2 * math.pi
        rr_ = Rout * (1 + amp * (0.6 * math.sin(2 * a + 0.7) + 0.4 * math.sin(3 * a + 2.1) + 0.3 * math.sin(5 * a)))
        (pth.moveTo if i == 0 else pth.lineTo)(rr_ * math.cos(a), rr_ * math.sin(a))
    pth.close()
    c.drawCircle(0.03 * R_, 0.045 * R_, Rout, paint(hexc("#000000", .45), blur=18))
    c.save(); c.rotate(math.degrees(th))
    c.drawPath(pth, paint(0, shader=rad((-0.35 * Rout * (1 - so), -0.4 * Rout * (1 - so)), 1.3 * Rout, [CLAY_L, CLAY, CLAY_D], [0, .55, 1])))
    if so > 0.05:  # opening: rim + well
        rw = 0.62 * R_ * so
        c.drawCircle(0, 0, Rout, paint(0, shader=lin((-Rout, -Rout), (Rout, Rout), [(CLAY_L, .55 * so), (CLAY, 0), (CLAY_D, .6 * so)])))
        c.drawCircle(0, 0, rw * 1.04, paint(0, shader=lin((-rw, -rw), (rw, rw), [(CLAY_D, 1), (CLAY, 1), (CLAY_L, 1)])))
        c.drawCircle(0, 0, rw * 0.95, paint(hexc(CLAY)))
        c.drawCircle(0, 0, rw * 0.95, paint(0, shader=rad((0, 0), max(1, rw), [(CLAY_D, .0), (CLAY_D, .25)])))
    # throwing lines (concentric, broken so the spin reads)
    for i in range(14):
        rr_ = Rout * (0.12 + 0.85 * i / 13)
        if so > 0.05 and abs(rr_ - 0.62 * R_ * so) < 0.03 * R_: continue
        a = skia.Path(); a.addArc(circ(rr_), i * 47, 250 + 60 * math.sin(i))
        c.drawPath(a, paint(hexc("#FFFFFF" if i % 2 else "#3A1A0A", .10 if i % 2 else .16), stroke=1.6 + 1.2 * (i % 3)))
    # groove + trimmed rim ("moldado")
    g = clamp((t - EV["groove"]) / 0.5)
    if g > 0:
        for rr_, w, col, al in ((0.62 * R_, 3.0, "#3A1A0A", .55), (0.63 * R_, 2.0, "#FFFFFF", .25), (0.93 * R_, 2.5, "#3A1A0A", .45)):
            a = skia.Path(); a.addArc(circ(rr_), -math.degrees(th) - 40, 360 * g); c.drawPath(a, paint(hexc(col, al), stroke=w))
    c.restore()
    # wet sheen (fixed light)
    c.drawOval(R(-0.55 * Rout, -0.62 * Rout, -0.05 * Rout, -0.25 * Rout), paint(hexc("#FFFFFF", .22), blur=0.08 * Rout))
    c.save(); c.rotate(math.degrees(th)); c.drawPath(pth, paint(hexc("#FFE2C8", .16), stroke=3)); c.restore()

def glaze_wipe(c, t, R_):
    """clay plate -> glazed plate, swept across by a hot glowing front (kiln + glaze, one match cut)"""
    u = ease_io((t - EV["glaze"]) / (EV["glaze_end"] - EV["glaze"]))
    d = lerp(-1.25 * R_, 1.35 * R_, u)  # front position along the (1,1) diagonal
    def front(off=0.0):
        p = skia.Path(); n = 40; pts = []
        for i in range(n + 1):
            s = lerp(-1.6 * R_, 1.6 * R_, i / n); w = 0.05 * R_ * math.sin(s / R_ * 7 + t * 9) + 0.03 * R_ * math.sin(s / R_ * 13 - t * 5)
            k = d + w + off; pts.append(((k - s) / math.sqrt(2), (k + s) / math.sqrt(2)))
        return pts
    pts = front(); p = skia.Path(); p.moveTo(*pts[0])
    for q in pts[1:]: p.lineTo(*q)
    p.lineTo(-3 * R_, 0); p.lineTo(-3 * R_, -3 * R_); p.lineTo(0, -3 * R_); p.close()
    c.save(); c.clipPath(p, doAntiAlias=True); glazed_plate(c, R_, math.degrees(theta(t)), None, shadow=False, edge=False); c.restore()
    if 0 < u < 1:
        q = skia.Path(); q.moveTo(*pts[0])
        for pt in pts[1:]: q.lineTo(*pt)
        c.save(); c.clipPath(skia.Path().addCircle(0, 0, R_ * 1.0), doAntiAlias=True)
        c.drawPath(q, paint(hexc("#FF8A2A", .85), stroke=0.10 * R_, blur=0.06 * R_)); c.drawPath(q, paint(hexc("#FFE3A1", .9), stroke=0.02 * R_, blur=0.01 * R_))
        c.restore()

def scene_wheel(c, t, Lo, draw_plate=True, bg_only=False):
    W, H, R_ = Lo["W"], Lo["H"], Lo["R"]; px, py = Lo["pc"]
    c.drawRect(R(0, 0, W, H), paint(hexc(STUDIO)))
    c.drawRect(R(0, 0, W, H), paint(0, shader=rad((px - 0.3 * R_, py - 0.4 * R_), 1.9 * R_, [("#5A4232", .9), ("#2A201A", .6), (STUDIO, 0)], [0, .45, 1])))
    z = lerp(1.38, 1.0, ease_io((t - 0.0) / 3.4)) * (1 + 0.05 * sstep(5.2, 8.3, t)) * (1 - 0.05 * sstep(8.3, 8.6, t)) if t > 0 else 1.38
    c.save(); c.translate(px, py); c.scale(z, z)
    th = theta(t)
    # splash pan + wheel head
    c.drawCircle(0, 0, 1.78 * R_, paint(hexc("#120E0B"))); c.drawCircle(0, 0, 1.78 * R_, paint(hexc("#4A3D33", .6), stroke=6))
    c.drawCircle(0.03 * R_, 0.05 * R_, 1.5 * R_, paint(hexc("#000000", .6), blur=24))
    c.drawCircle(0, 0, 1.5 * R_, paint(0, shader=rad((-0.4 * R_, -0.5 * R_), 2.2 * R_, ["#6A5A4C", "#46392F", "#2B231D"], [0, .5, 1])))
    c.save(); c.rotate(math.degrees(th))
    for r, a, l, w, al, li in WHEEL_STREAKS:
        p = skia.Path(); p.addArc(circ(r * R_), a, l); c.drawPath(p, paint(hexc("#C9A68A" if li > .5 else "#1A120D", al), stroke=w))
    c.restore()
    c.drawCircle(0, 0, 1.5 * R_, paint(0, shader=lin((-R_, -R_), (R_, R_), [("#E8CDB4", .7), ("#000000", 0), ("#000000", .6)]), stroke=7))
    if not bg_only:
        if t < EV["glaze"]: clay_form(c, t, R_)
        elif t < EV["glaze_end"]:
            clay_form(c, t, R_); glaze_wipe(c, t, R_)
        elif draw_plate:
            glazed_plate(c, R_, math.degrees(th), pat_rosette(t), shadow=True)
        if EV["brush_in"] <= t < EV["brush_out"] + 0.3:
            bx, by, bh = brush_tip(t, R_)
            col = COBALT
            for k, tk in enumerate(FISH_T):
                if t >= tk - 0.005: col = FISH_COLS[k]
            if t >= EV["dots"] - 0.05: col = OCHRE
            brush(c, bx, by, bh, Lo["phi_h"], col, scale=R_ / 380)
    c.restore()
    vignette(c, W, H, .55)

def ceramic_bowl(c, r, col, pat):
    c.drawCircle(0.06 * r, 0.09 * r, r * 1.01, paint(hexc("#2A1A10", .35), blur=0.07 * r))
    c.drawCircle(0, 0, r, paint(0, shader=lin((-r, -r), (r, r), ["#FFFFFF", col, col], [0, .25, 1])))
    ri = 0.88 * r
    c.drawCircle(0, 0, ri, paint(0, shader=lin((-ri, -ri), (ri, ri), [("#000000", 1), (col, 1), ("#FFFFFF", 1)], [0, .5, 1])))
    c.drawCircle(0, 0, ri, paint(hexc(col, .55)))
    c.drawCircle(0.04 * r, 0.04 * r, 0.80 * r, paint(hexc(col)))
    c.save(); c.clipPath(skia.Path().addCircle(0.04 * r, 0.04 * r, 0.80 * r), doAntiAlias=True)
    if pat == "dots":
        for i in range(40):
            a = i * 2.39996; rr_ = 0.12 * r * math.sqrt(i); c.drawCircle(math.cos(a) * rr_, math.sin(a) * rr_, 0.035 * r, paint(hexc("#FFFFFF", .9)))
    elif pat == "stripes":
        for k in range(1, 7): c.drawCircle(0.04 * r, 0.04 * r, k * 0.12 * r, paint(hexc("#FFFFFF", .85), stroke=0.025 * r))
    c.drawCircle(-0.3 * r, -0.3 * r, 0.9 * r, paint(hexc("#000000", .18), stroke=0.25 * r, blur=0.12 * r))
    c.restore()
    c.drawOval(R(-0.62 * r, -0.66 * r, -0.12 * r, -0.42 * r), paint(hexc("#FFFFFF", .45), blur=0.06 * r))
    arc = skia.Path(); arc.addArc(circ(0.94 * r), 190, 80); c.drawPath(arc, paint(hexc("#FFFFFF", .8), stroke=0.025 * r, blur=0.005 * r))

def oval_platter(c, rx, ry):
    c.drawOval(R(-rx + 0.04 * ry, -ry + 0.07 * ry, rx + 0.04 * ry, ry + 0.07 * ry), paint(hexc("#2A1A10", .35), blur=0.06 * ry))
    c.drawOval(R(-rx, -ry + 0.02 * ry, rx, ry + 0.02 * ry), paint(hexc(GLAZE_E)))
    c.drawOval(R(-rx, -ry, rx, ry), paint(0, shader=rad((-0.3 * rx, -0.4 * ry), 1.3 * rx, [GLAZE, GLAZE, GLAZE_D], [0, .6, 1])))
    c.drawOval(R(-0.82 * rx, -0.80 * ry, 0.82 * rx, 0.80 * ry), paint(0, shader=lin((-rx, -ry), (rx, ry), ["#D8CFBF", GLAZE, "#FFFFFF"])))
    c.drawOval(R(-0.79 * rx, -0.76 * ry, 0.79 * rx, 0.76 * ry), paint(hexc(GLAZE)))
    c.drawOval(R(-0.93 * rx, -0.91 * ry, 0.93 * rx, 0.91 * ry), paint(hexc(COBALT, .9), stroke=0.05 * ry))
    for k, (dy, col) in enumerate(((-0.40, TURQ), (0.0, COBALT), (0.40, CORAL))):
        painted_fish(c, (0.03 if k == 1 else -0.03) * rx, dy * 0.92 * ry, 1.0 * rx, 0.0 if k != 1 else math.pi, col)
    rng = np.random.default_rng(12)
    for i in range(22):
        a = rng.uniform(0, 2 * math.pi); c.drawCircle(math.cos(a) * rx * rng.uniform(.3, .72), math.sin(a) * ry * rng.uniform(.3, .7), ry * rng.uniform(.012, .03), paint(hexc(FISH_COLS[i % 6], .9)))
    c.drawOval(R(-0.65 * rx, -0.82 * ry, 0.0, -0.45 * ry), paint(hexc("#FFFFFF", .35), blur=0.06 * ry))

def cup_saucer(c, r):
    c.drawCircle(0.05 * r, 0.08 * r, r, paint(hexc("#2A1A10", .3), blur=0.07 * r))
    c.drawCircle(0, 0, r, paint(0, shader=rad((-0.3 * r, -0.3 * r), 1.4 * r, [GLAZE, GLAZE_D])))
    c.drawCircle(0, 0, 0.9 * r, paint(hexc(COBALT, .9), stroke=0.035 * r))
    c.drawCircle(0.06 * r, 0.09 * r, 0.56 * r, paint(hexc("#2A1A10", .35), blur=0.05 * r))
    c.drawRoundRect(R(0.45 * r, -0.1 * r, 0.78 * r, 0.1 * r), 0.1 * r, 0.1 * r, paint(hexc(GLAZE_D)))
    c.drawCircle(0, 0, 0.55 * r, paint(0, shader=lin((-r, -r), (r, r), ["#FFFFFF", GLAZE, GLAZE_D])))
    c.drawCircle(0, 0, 0.45 * r, paint(hexc("#3B2416")))
    c.drawCircle(0, 0, 0.45 * r, paint(hexc("#9A6A44", .8), stroke=0.05 * r))
    c.drawOval(R(-0.3 * r, -0.32 * r, -0.05 * r, -0.18 * r), paint(hexc("#FFFFFF", .25), blur=0.03 * r))

def ceramic_sardine(c, L, ang, lift=0.0):
    off = (0.05 + 0.30 * lift) * L
    c.save(); c.translate(off * 0.6, off); c.rotate(math.degrees(ang)); c.scale(L, L)
    c.drawPath(FISH, paint(hexc("#2A1A10", .38 * (1 - .5 * lift)), blur=0.02 + 0.05 * lift)); c.restore()
    c.save(); c.scale(1 + 0.45 * lift, 1 + 0.45 * lift)
    c.save(); c.rotate(math.degrees(ang)); c.scale(L, L)
    c.drawPath(FISH, paint(0, shader=lin((0, -0.15), (0, 0.15), ["#F08A62", CORAL, "#B8432A"]))); c.drawPath(DORSAL, paint(hexc(CORAL)))
    c.restore()
    painted_fish(c, 0, 0, L, ang, COBALT, 1.0, glossy=True, belly=False)
    c.restore()

def lemon(c, s, ang):
    c.save(); c.rotate(ang)
    c.drawOval(R(-0.95 * s + 0.08 * s, -0.7 * s + 0.12 * s, 0.95 * s + 0.08 * s, 0.7 * s + 0.12 * s), paint(hexc("#2A1A10", .3), blur=0.09 * s))
    lp = skia.Path(); lp.addOval(R(-0.9 * s, -0.68 * s, 0.9 * s, 0.68 * s)); lp.addCircle(-0.92 * s, 0, 0.12 * s); lp.addCircle(0.92 * s, 0, 0.1 * s)
    c.drawPath(lp, paint(0, shader=rad((-0.3 * s, -0.3 * s), 1.2 * s, ["#FFE47A", "#F2C230", "#C9921A"], [0, .55, 1])))
    for i in range(60):
        rng = np.random.default_rng(i); c.drawCircle(rng.uniform(-.7, .7) * s, rng.uniform(-.5, .5) * s, 0.012 * s, paint(hexc("#B88A10", .35)))
    c.drawOval(R(-0.5 * s, -0.5 * s, -0.05 * s, -0.25 * s), paint(hexc("#FFFFFF", .45), blur=0.06 * s))
    leaf = skia.Path(); leaf.moveTo(-0.95 * s, 0); leaf.cubicTo(-1.25 * s, -0.55 * s, -1.75 * s, -0.55 * s, -2.0 * s, -0.35 * s)
    leaf.cubicTo(-1.7 * s, -0.05 * s, -1.25 * s, 0.05 * s, -0.95 * s, 0); c.drawPath(leaf, paint(0, shader=lin((-2 * s, -0.4 * s), (-1 * s, 0), ["#2F6B2E", "#4F8E3B"])))
    c.restore()
def lemon_half(c, s):
    c.drawCircle(0.07 * s, 0.1 * s, s, paint(hexc("#2A1A10", .3), blur=0.08 * s))
    c.drawCircle(0, 0, s, paint(hexc("#EDB824"))); c.drawCircle(0, 0, 0.9 * s, paint(hexc("#FBF1C6")))
    for k in range(9):
        a0 = k * 40
        p = skia.Path(); p.moveTo(0, 0); p.arcTo(circ(0.82 * s), a0 + 3, 34, False); p.close(); c.drawPath(p, paint(hexc("#F6D660")))
    c.drawCircle(0, 0, 0.1 * s, paint(hexc("#FBF1C6")))
    c.drawOval(R(-0.6 * s, -0.6 * s, -0.1 * s, -0.3 * s), paint(hexc("#FFFFFF", .4), blur=0.06 * s))
def sprig(c, s):
    st = skia.Path(); st.moveTo(-s, 0.2 * s); st.cubicTo(-0.3 * s, -0.1 * s, 0.3 * s, 0.1 * s, s, -0.15 * s)
    c.drawPath(st, paint(hexc("#2A1A10", .25), stroke=0.03 * s, blur=4)); c.drawPath(st, paint(hexc("#6A6A42"), stroke=0.025 * s))
    for i in range(9):
        u = i / 8; x = lerp(-0.9, 0.9, u) * s; y = 0.2 * s * (1 - u) - 0.15 * s * u; side = 1 if i % 2 else -1
        c.save(); c.translate(x, y); c.rotate(-30 * side - 10)
        c.drawOval(R(0.02 * s + 0.03 * s, -0.06 * s + 0.05 * s, 0.38 * s + 0.03 * s, 0.06 * s + 0.05 * s), paint(hexc("#2A1A10", .22), blur=4))
        c.drawOval(R(0.02 * s, -0.06 * s, 0.38 * s, 0.06 * s), paint(0, shader=lin((0, -0.06 * s), (0, 0.06 * s), ["#9DB07F", "#6E8455"])))
        c.restore()
    for x, y in ((0.35, -0.32), (-0.2, 0.35)):
        c.drawCircle(x * s + 6, y * s + 9, 0.08 * s, paint(hexc("#2A1A10", .3), blur=5)); c.drawCircle(x * s, y * s, 0.08 * s, paint(0, shader=rad((x * s - 0.03 * s, y * s - 0.03 * s), 0.1 * s, ["#6C6A3A", "#2E2E1E"])))
def napkin(c, w, h):
    c.drawRect(R(-w / 2 + 14, -h / 2 + 20, w / 2 + 14, h / 2 + 20), paint(hexc("#2A1A10", .22), blur=16))
    c.drawRect(R(-w / 2, -h / 2, w / 2, h / 2), paint(hexc("#F6F2EA")))
    for k in (0.08, 0.12, 0.88, 0.92): c.drawRect(R(-w / 2, -h / 2 + h * k - 5, w / 2, -h / 2 + h * k + 5), paint(hexc(COBALT, .85)))
    c.drawRect(R(-w / 2, -h / 2, w / 2, h / 2), paint(0, shader=lin((-w / 2, 0), (w / 2, 0), [("#000000", 0), ("#000000", .06), ("#FFFFFF", .1), ("#000000", 0)], [0, .45, .55, 1])))

def table_items(c, t, Lo):
    it = Lo["items"]; base = EV["items"]
    def slide(i, x, y, fn, rot=0.0, d=(0, -1)):
        u = ease_out((t - base - i * 0.11) / 0.6)
        if u <= 0: return
        c.save(); c.translate(x + d[0] * 2200 * (1 - u), y + d[1] * 2200 * (1 - u)); c.rotate(rot + 14 * (1 - u)); fn(); c.restore()
    nx, ny, nr = it["napkin"]; slide(0, nx, ny, lambda: napkin(c, 760, 520), nr, (-1, 0.3))
    px_, py_, rx, ry, pr = it["platter"]; slide(1, px_, py_, lambda: oval_platter(c, rx, ry), pr, (-0.6, -1))
    bx, by, br = it["bowl_t"]; slide(2, bx, by, lambda: ceramic_bowl(c, br, TURQ, "dots"), 0, (-0.7, 1))
    bx, by, br = it["bowl_c"]; slide(3, bx, by, lambda: ceramic_bowl(c, br, CORAL, "stripes"), 0, (0.8, -1))
    cx_, cy_, cr = it["cup"]; slide(4, cx_, cy_, lambda: cup_saucer(c, cr), 0, (1, 0.2))
    lx, ly, la = it["lemon"]; slide(5, lx, ly, lambda: lemon(c, 120, la), 0, (-1, 0.5))
    hx, hy = it["half"]; slide(6, hx, hy, lambda: lemon_half(c, 105), 0, (-0.5, 1))
    sx, sy, sa = it["sprig"]; slide(7, sx, sy, lambda: sprig(c, 260), sa, (-1, -0.6))

def scene_table(c, t, Lo):
    W, H, R_ = Lo["W"], Lo["H"], Lo["R"]; px, py = Lo["pc"]; tcx, tcy, tz = Lo["cam_tab"]
    u = ease_io((t - EV["zoom"]) / (EV["zoom_end"] - EV["zoom"]))
    z = math.exp(lerp(0, math.log(tz), u)) * (1 + 0.035 * sstep(EV["zoom_end"], EV["whip"] + 0.3, t))
    c0 = ((W / 2 - px), (H / 2 - py)); cx, cy = lerp(c0[0], tcx, u), lerp(c0[1], tcy, u)
    c.save(); c.translate(W / 2, H / 2); c.scale(z, z); c.translate(-cx, -cy)
    vis = R(cx - W / 2 / z - 10, cy - H / 2 / z - 10, cx + W / 2 / z + 10, cy + H / 2 / z + 10)
    c.drawRect(vis, paint(0, shader=tile_shader("linen", (0, 0), 1.0)))
    c.drawRect(vis, paint(0, shader=lin((vis.left(), vis.top()), (vis.right(), vis.bottom()), [("#FFF6E6", .35), ("#FFFFFF", 0), ("#3A2A1A", .18)])))
    table_items(c, t, Lo)
    # the plate (lifted off the wheel, set down on the table)
    lift = sstep(EV["lift"], EV["lift"] + 0.3, t) * (1 - sstep(EV["set"], EV["set"] + 0.28, t))
    c.save(); c.scale(1 + 0.06 * lift, 1 + 0.06 * lift)
    glazed_plate(c, R_, math.degrees(theta(t)), pat_rosette(t), lift=lift); c.restore()
    # splash ring + the ceramic sardine that leaps off the plate
    j0, j1 = EV["jump"], EV["jump_end"]
    if t > j0 - 0.05:
        k = clamp((t - j0 + 0.05) / 0.5)
        if k < 1: c.drawCircle(0, 0, 0.1 * R_ + 0.6 * R_ * ease_out(k), paint(hexc("#FFFFFF", .7 * (1 - k)), stroke=6 * (1 - k) + 1))
        fx, fy, fl, fr = Lo["items"]["fish"]; v = clamp((t - j0) / (j1 - j0)); e = ease_io(v)
        c.save(); c.translate(lerp(0, fx, e), lerp(0, fy, e)); a = math.radians(fr) + (1 - e) * -2 * math.pi
        ceramic_sardine(c, fl * lerp(0.6, 1.0, ease_out(v * 1.5)), a, lift=math.sin(math.pi * v) if v < 1 else 0.0); c.restore()
    # shadow of a swallow crossing the table (foreshadowing)
    sp = clamp((t - EV["shadow_pass"]) / 0.55)
    if 0 < sp < 1:
        sx_ = lerp(vis.left() - 400, vis.right() + 400, sp); sy_ = lerp(vis.bottom() + 300, vis.top() - 300, sp)
        b, ws = swallow_parts(0.15 * math.sin(sp * 30)); c.save(); c.translate(sx_, sy_); c.rotate(48); c.scale(520, 520)
        for pth in [b] + ws: c.drawPath(pth, paint(hexc("#2A1A10", .22), blur=0.06))
        c.restore()
    c.restore()
    TX = TEXT["pt"]; tx, ty, al = Lo["txt_tab"]
    headline(c, TX["h4"], tx, ty, Lo["hsize"], INK, t, 9.0, EV["whip"] - 0.02, al, Lo["maxw"])
    vignette(c, W, H, .25, "#3A2414")

def azulejo(c, x, y, s):
    c.drawRect(R(x, y, x + s, y + s), paint(hexc("#F7F4EE")))
    m = s / 2; cb = hexc(COBALT, .92)
    for cx_, cy_ in ((x, y), (x + s, y), (x, y + s), (x + s, y + s)): c.drawCircle(cx_, cy_, s * 0.22, paint(cb))
    p = skia.Path()
    for k in range(4):
        a = k * math.pi / 2; p.addCircle(x + m + math.cos(a) * s * 0.17, y + m + math.sin(a) * s * 0.17, s * 0.13)
    c.drawPath(p, paint(cb)); c.drawCircle(x + m, y + m, s * 0.09, paint(hexc("#F7F4EE"))); c.drawCircle(x + m, y + m, s * 0.045, paint(hexc(OCHRE)))
    c.drawRect(R(x, y, x + s, y + s), paint(hexc("#B9B2A6"), stroke=2))

def swallow_state(i, t, Lo):
    """position, size, heading, flex, alpha of the wall swallow i"""
    fx, fy, S = Lo["swallows"][i]; t_land = EV[f"sw{i}"]; W, H = Lo["W"], Lo["H"]; fa = math.radians(52)
    sx, sy = -0.25 * W, H * (1.15 + 0.1 * i)
    if t < t_land:
        u = clamp((t - (t_land - 0.75)) / 0.75); e = ease_out(u)
        c1 = (lerp(sx, fx, 0.35), fy + 0.45 * H)
        x = (1 - e) ** 2 * sx + 2 * (1 - e) * e * c1[0] + e * e * fx; y = (1 - e) ** 2 * sy + 2 * (1 - e) * e * c1[1] + e * e * fy
        dx = 2 * (1 - e) * (c1[0] - sx) + 2 * e * (fx - c1[0]); dy = 2 * (1 - e) * (c1[1] - sy) + 2 * e * (fy - c1[1])
        head = math.atan2(dx, -dy); ang = lerp(head, fa, sstep(0.75, 1, u))
        return x, y, S * lerp(1.7, 1, e), ang, 0.25 * math.sin(t * 38) * (1 - u), 1.0, u
    if t < EV["takeoff"] or i == 0 and t < EV["takeover"]:
        s = math.exp(-(t - t_land) * 7) * math.sin((t - t_land) * 22)
        return fx, fy, S, fa + 0.06 * s, 0, 1.0, 1
    if i == 0:  # flies at the camera and fills the frame with cobalt
        u = clamp((t - EV["takeover"]) / (EV["takeover_end"] - EV["takeover"])); e = ease_in(u)
        return lerp(fx, W * 0.5, e), lerp(fy, H * 0.55, e), S * lerp(1, 26, e), fa + 0.5 * e, 0.2 * math.sin(t * 40), 1.0, 1
    u = clamp((t - EV["takeoff"] - 0.06 * i) / 0.55); e = ease_in(u)
    return fx + e * W * 0.9, fy - e * H * 0.9, S * (1 + 0.3 * e), fa, 0.3 * math.sin(t * 40), 1.0, 1

def scene_wall(c, t, Lo):
    W, H = Lo["W"], Lo["H"]
    c.drawRect(R(0, 0, W, H), paint(0, shader=tile_shader("wall", (0, 0), 1.0)))
    c.drawRect(R(0, 0, W, H), paint(0, shader=lin((0, 0), (W, H), [("#FFFFFF", .25), ("#FFFFFF", 0), ("#6B5040", .10)])))
    # window light falling across the lime wall
    lp = skia.Path(); ox = W * (0.18 if Lo["o"] == "L" else 0.0)
    for (a, b) in ((0, 0.47), (0.53, 1.0)):
        for (cc_, d) in ((0, 0.47), (0.53, 1.0)):
            x0, y0 = ox + W * 0.55 * a, H * (-0.1) + H * 0.6 * cc_; x1, y1 = ox + W * 0.55 * b, H * (-0.1) + H * 0.6 * d
            sk = 0.55 * H
            lp.moveTo(x0 + sk * 0.5, y0); lp.lineTo(x1 + sk * 0.5, y0); lp.lineTo(x1 + sk * 0.5 + (y1 - y0) * 0.6, y1); lp.lineTo(x0 + sk * 0.5 + (y1 - y0) * 0.6, y1); lp.close()
    c.drawPath(lp, paint(hexc("#FFE6B8", .30), blur=34))
    # azulejo wainscot
    s = Lo["tile"]; y0 = Lo["band_y"]
    c.drawRect(R(0, y0 - 18, W, y0), paint(hexc(COBALT, .9)))
    for i in range(int(W / s) + 2): azulejo(c, i * s, y0, s)
    c.drawRect(R(0, y0 - 18, W, H), paint(0, shader=lin((0, y0), (0, H), [("#FFFFFF", .18), ("#000000", .0), ("#000000", .15)])))
    c.drawRect(R(0, y0 - 22, W, y0 - 14), paint(hexc("#FFFFFF", .5), blur=3))
    cols = (COBALT, CORAL, OCHRE)
    order = [1, 2, 0] if t >= EV["takeover"] else [0, 1, 2]
    for i in order:
        if t < EV[f"sw{i}"] - 0.75: continue
        x, y, S, ang, flex, al, landed = swallow_state(i, t, Lo)
        swallow(c, x, y, S, ang, cols[i], flex, shadow=(0.10 + 0.5 * (1 - landed), 0.16 + 0.6 * (1 - landed)), sh_a=0.3 * (0.5 + 0.5 * landed))
    TX = TEXT["pt"]; tx, ty, al_ = Lo["txt_wall"]
    headline(c, TX["h5"], tx, ty, Lo["hsize"], INK, t, 11.3, EV["takeover"] + 0.1, al_, Lo["maxw"])
    vignette(c, W, H, .22, "#3A2414")

STACK = [pat_splash, pat_calcada, pat_swallows, None, pat_white]
STACK_OFF = [(-14, 10, -20), (12, -8, 25), (-8, -12, 60), (10, 6, 0), (0, 0, 0)]

def logo(c, t, R_):
    u = clamp((t - EV["logo"]) / (EV["logo_end"] - EV["logo"] - 0.2))
    size = 0.40 * R_; w = text_w("DURO", size, "serifb", 0.06)
    if u > 0:
        c.save(); c.clipRect(R(-w / 2 - 20, -R_, -w / 2 - 20 + (w + 40) * u, -0.02 * R_))
        text(c, "DURO", 0, -0.18 * R_, size, hexc(COBALT, .95), "serifb", "c", 0.06); c.restore()
        swallow(c, 0, -0.50 * R_, 0.11 * R_, 0.9, COBALT, flat=True, alpha=sstep(EV["logo"] + 0.5, EV["logo"] + 0.8, t))
        if u < 1: brush(c, -w / 2 + w * u, -0.12 * R_, 0.0, -0.75, COBALT, scale=R_ / 520)
    k = sstep(EV["logo_end"] - 0.25, EV["logo_end"] + 0.15, t)
    if k > 0:
        layer_alpha(c, k); c.drawLine(-0.30 * R_, 0.04 * R_, 0.30 * R_, 0.04 * R_, paint(hexc(COBALT, .8), stroke=2))
        text(c, "CERAMICS", 0, 0.14 * R_, 0.075 * R_, hexc(COBALT), "sansb", "c", 0.5); c.restore()
    rk = clamp((t - EV["ring_text"]) / 0.7)
    if rk > 0:
        s = TEXT["pt"]["ring"]; f = skia.Font(TF["sansb"], 0.052 * R_); rr_ = 0.80 * R_
        total = sum(f.measureText(ch) + 0.18 * 0.052 * R_ for ch in s); scale = 2 * math.pi * rr_ / total
        a = -math.pi / 2; n_show = int(len(s) * rk)
        for ch in s[:n_show]:
            cw = (f.measureText(ch) + 0.18 * 0.052 * R_) * scale
            c.save(); c.rotate(math.degrees(a + cw / rr_ / 2) + 90); c.translate(0, -rr_)
            c.drawString(ch, -f.measureText(ch) / 2, 0.052 * R_ * 0.35, f, paint(hexc(COBALT, .9))); c.restore()
            a += cw / rr_

def plate_back(c, R_):
    plate_shadow(c, R_)
    c.drawCircle(0, 0, R_, paint(hexc(GLAZE)))
    c.drawCircle(0, 0, 0.965 * R_, paint(0, shader=rad((-0.3 * R_, -0.3 * R_), 1.4 * R_, ["#EFD9BC", BISQUE, BISQUE_D], [0, .6, 1])))
    rng = np.random.default_rng(31)
    for _ in range(260):  # pores of unglazed clay
        a = rng.uniform(0, 2 * math.pi); r = math.sqrt(rng.uniform(0.47, 0.93)) * R_
        c.drawCircle(math.cos(a) * r, math.sin(a) * r, rng.uniform(0.6, 1.6), paint(hexc("#8A6A4A", rng.uniform(.15, .35))))
    fr = 0.68 * R_
    c.drawCircle(0, 0, fr, paint(0, shader=lin((-fr, -fr), (fr, fr), [("#FFF2DE", 1), (BISQUE, 1), ("#9C7C5A", 1)]), stroke=0.05 * R_))
    c.drawCircle(0, 0, fr - 0.03 * R_, paint(hexc("#7A5A3E", .35), stroke=3, blur=2))
    c.drawCircle(0, 0, fr - 0.026 * R_, paint(hexc("#DCC09C")))
    # potter's mark (impressed): monogram, name, handle
    sy = -0.33 * R_; sr = 0.17 * R_
    c.drawCircle(1.5, sy + 2, sr, paint(hexc("#FFF4E2", .7), stroke=3)); c.drawCircle(0, 0 + sy, sr, paint(hexc("#5A3E28", .75), stroke=3))
    c.drawCircle(0, sy, sr * 0.82, paint(hexc("#5A3E28", .4), stroke=1.4))
    for dx, dy, col in ((1.5, 2, ("#FFF4E2", .7)), (0, 0, ("#4A3220", .95))):
        text(c, MONOGRAM, dx, sy + dy, 0.17 * R_, hexc(*col), "serifb", "c", 0.02)
    ns = fit(NAME, 0.19 * R_, "serif", 1.22 * fr)
    for dx, dy, col in ((1.2, 1.6, ("#FFF4E2", .6)), (0, 0, ("#3E2A1C", 1))):
        text(c, NAME, dx, 0.03 * R_ + dy, ns, hexc(*col), "serif", "c")
    text(c, HANDLE, 0, 0.22 * R_, 0.085 * R_, hexc("#7A5236"), "sansb", "c", 0.04)
    c.drawLine(-0.16 * R_, 0.36 * R_, 0.16 * R_, 0.36 * R_, paint(hexc("#7A5A3E", .5), stroke=2))
    swallow(c, 0, 0.47 * R_, 0.075 * R_, 0.9, COBALT, flat=True)
    c.drawOval(R(-0.7 * R_, -0.75 * R_, -0.1 * R_, -0.45 * R_), paint(hexc("#FFFFFF", .10), blur=0.08 * R_))

def scene_stack(c, t, Lo):
    W, H = Lo["W"], Lo["H"]; R_ = Lo["stack_R"]
    c.drawRect(R(0, 0, W, H), paint(hexc(COBALT_D)))
    c.drawRect(R(0, 0, W, H), paint(0, shader=rad((W * 0.62, H * 0.45), max(W, H) * 0.75, [COBALT_L, COBALT, COBALT_D], [0, .5, 1])))
    # plate glides to centre for the logo / end card
    g = ease_io((t - 17.0) / 0.55); px = lerp(Lo["stack_pc"][0], Lo["end_pc"][0], g); py = lerp(Lo["stack_pc"][1], Lo["end_pc"][1], g)
    shake = 0
    for td in EV["drops"] + [EV["white"]]:
        if td + 0.3 < t < td + 0.6: shake += 4 * math.exp(-(t - td - 0.3) * 18) * math.sin((t - td) * 90)
    c.save(); c.translate(px, py + shake)
    f = ease_io((t - EV["flip"]) / (EV["flip_end"] - EV["flip"]))
    times = EV["drops"] + [EV["white"]]
    for i, (pat, td) in enumerate(zip(STACK, times)):
        u = clamp((t - td) / 0.32)
        if u <= 0: continue
        if f > 0 and i < 4: continue
        dx, dy, rot = STACK_OFF[i]; e = ease_in(u); s = lerp(1.5, 1.0, e)
        bounce = 1 - 0.018 * math.exp(-(t - td - 0.32) * 14) * math.sin((t - td - 0.32) * 40) if u >= 1 else 1
        c.save(); c.translate(dx * e, dy * e)
        if i < 4 and t > times[i + 1] + 0.3: pass
        if i == 4 and f > 0:  # flip to show the back
            sx = math.cos(math.pi * f); lift = math.sin(math.pi * f); sc = 1 + 0.10 * lift + 0.06 * f
            c.scale(sc, sc)
            c.drawCircle(R_ * (0.04 + 0.12 * lift), R_ * (0.06 + 0.15 * lift), R_ * abs(sx) * 0.98 + 4, paint(hexc("#000000", .35), blur=20 + 30 * lift))
            c.scale(max(0.002, abs(sx)), 1)
            if sx >= 0: glazed_plate(c, R_, 0, None, shadow=False); logo(c, t, R_)
            else: plate_back(c, R_)
            c.drawCircle(0, 0, R_ * 1.01, paint(hexc("#000000", .35 * (1 - abs(sx)))))
            c.restore(); continue
        c.scale(s * bounce, s * bounce); layer_alpha(c, clamp(u * 3))
        glazed_plate(c, R_, rot, pat if pat is not None else pat_rosette(99), lift=(1 - e) * 1.2)
        if i == 4: logo(c, t, R_)
        c.restore(); c.restore()
    c.restore()
    TX = TEXT["pt"]; tx, ty, al = Lo["txt_stack"]
    top = headline(c, TX["h6"], tx, ty, Lo["hsize"] * 1.1, CREAM, t, 14.05, 17.0, al, Lo["maxw"] * 0.75)
    if top is not None:
        kicker(c, TX["k6"], tx, top - 30, 24, CREAM_S, win(t, 14.0, 17.0, .4, .35), al)
    k = win(t, EV["essence"], EV["flip"] + 0.1, .5, .3)
    if k > 0:
        layer_alpha(c, k); s = TX["essence"]; sz = fit(s, 46 if Lo["o"] == "L" else 50, "ital", W - 140)
        text(c, s, W / 2, Lo["essence_y"] + (1 - k) * 12, sz, hexc(CREAM), "ital", "c"); c.restore()
    kd = sstep(EV["card"] - 0.05, EV["card"] + 0.4, t)
    if kd > 0:
        layer_alpha(c, kd); s = TX["disclaimer"]; sz = fit(s, 28 if Lo["o"] == "L" else 32, "sansm", W - 120)
        text(c, s, W / 2, Lo["disc_y"] if Lo["o"] == "L" else Lo["end_pc"][1] + Lo["stack_R"] * 1.16 + 70, sz, hexc(CREAM, .85), "sansm", "c", 0.02); c.restore()
    vignette(c, W, H, .4, "#060C24")

# ---------------- renderer ----------------
class Renderer:
    def __init__(self, orient, scale):
        self.L = layout(orient); self.scale = scale; self.W, self.H = self.L["W"], self.L["H"]
        self.surf = skia.Surface(int(self.W * scale), int(self.H * scale))

    def text_wheel(self, c, t):
        Lo = self.L; TX = TEXT["pt"]; tx, ty, al = Lo["txt"]; hs = Lo["hsize"]
        top = headline(c, TX["h1"], tx, ty, hs, CREAM, t, 1.25, 3.5, al, Lo["maxw"])
        kicker(c, TX["kicker"], tx, (top if top is not None else ty - hs) - 34, 24, CREAM_S, win(t, 0.55, 3.5, .5, .3), al)
        headline(c, TX["h2"], tx, ty, hs, CREAM, t, 3.68, 5.12, al, Lo["maxw"])
        headline(c, TX["h3"], tx, ty - hs * 0.32, hs, CREAM, t, 5.35, 8.35, al, Lo["maxw"])
        script_line(c, TX["h3_script"], tx, ty + hs * 1.05, hs * 0.62, CREAM_S, t, 6.35, 1.1, 8.35, al)

    def draw(self, t):
        c = self.surf.getCanvas(); c.save(); c.scale(self.scale, self.scale); W, H, Lo = self.W, self.H, self.L
        c.clear(hexc("#000000"))
        if t < EV["lift"]:
            scene_wheel(c, t, Lo); self.text_wheel(c, t)
        elif t < EV["whip"]:
            scene_table(c, t, Lo)
            k = sstep(EV["lift"], EV["set"] + 0.05, t)
            if k < 1:  # the atelier dissolves away around the lifted plate
                layer_alpha(c, 1 - k); scene_wheel(c, t, Lo, bg_only=True); c.restore()
                self._plate_only(c, t)
        elif t < EV["whip_end"]:
            u = ease_io((t - EV["whip"]) / (EV["whip_end"] - EV["whip"]))
            c.save(); c.translate(0, u * H); scene_table(c, t, Lo); c.restore()
            c.save(); c.translate(0, -(1 - u) * H); scene_wall(c, t, Lo); c.restore()
        elif t < EV["takeover_end"] - 0.12:
            scene_wall(c, t, Lo)
            if t > EV["takeover_end"] - 0.3:
                layer_alpha(c, sstep(EV["takeover_end"] - 0.3, EV["takeover_end"] - 0.12, t)); c.drawRect(R(0, 0, W, H), paint(hexc(COBALT))); c.restore()
        else:
            scene_stack(c, t, Lo)
            if t < EV["takeover_end"] + 0.1:
                layer_alpha(c, 1 - sstep(EV["takeover_end"] - 0.12, EV["takeover_end"] + 0.1, t)); c.drawRect(R(0, 0, W, H), paint(hexc(COBALT))); c.restore()
        grain(c, R(0, 0, W, H), t, .085)
        c.restore()
        return self.surf.makeImageSnapshot().toarray()

    def _plate_only(self, c, t):
        Lo = self.L; R_ = Lo["R"]; px, py = Lo["pc"]
        lift = sstep(EV["lift"], EV["lift"] + 0.3, t) * (1 - sstep(EV["set"], EV["set"] + 0.28, t))
        c.save(); c.translate(px, py); c.scale(1 + 0.06 * lift, 1 + 0.06 * lift)
        glazed_plate(c, R_, math.degrees(theta(t)), pat_rosette(t), lift=lift); c.restore()

    def samples(self, t):
        if EV["whip"] - 0.02 < t < EV["whip_end"] + 0.02: return 10
        if EV["takeover"] < t < EV["takeover_end"]: return 7
        if EV["flip"] < t < EV["flip_end"]: return 6
        if EV["clay_drop"] < t < EV["clay_land"] + 0.05: return 5
        if EV["jump"] < t < EV["jump_end"] or EV["items"] < t < EV["items"] + 1.4: return 4
        if any(td < t < td + 0.34 for td in EV["drops"] + [EV["white"]]): return 4
        if EV["zoom"] < t < EV["zoom_end"] or EV["shadow_pass"] < t < EV["shadow_pass"] + 0.55: return 3
        if any(EV[f"sw{i}"] - 0.75 < t < EV[f"sw{i}"] for i in range(3)) or EV["takeoff"] < t < EV["takeover"] + 0.5: return 3
        if t < 4.4: return 3  # fast-spinning wheel
        return 1

    def frame(self, t, fps):
        n = self.samples(t); dt = 1 / fps
        if n == 1: return self.draw(t)
        acc = None
        for k in range(n):
            f = self.draw(t + dt * 0.9 * (k / n - 0.5)).astype(np.float32); acc = f if acc is None else acc + f
        return (acc / n).astype(np.uint8)

if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--orient", default="L"); ap.add_argument("--scale", type=float, default=1.0); ap.add_argument("--fps", type=int, default=FPS)
    ap.add_argument("--lang", default="pt"); ap.add_argument("--out", required=True); ap.add_argument("--audio", default=None)
    ap.add_argument("--still", type=float, nargs="*")
    a = ap.parse_args(); Rr = Renderer(a.orient, a.scale)
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
    for fi in range(N):
        ff.stdin.write(Rr.frame(fi / a.fps, a.fps).tobytes())
        if fi % (a.fps * 2) == 0: print(f"{fi / a.fps:5.1f}s", flush=True)
    ff.stdin.close(); ff.wait(); print("done", a.out)
