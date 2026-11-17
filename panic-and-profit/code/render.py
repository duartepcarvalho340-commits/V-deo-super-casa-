"""Panic & Profit — launch reel renderer (Skia 2D -> FFmpeg).

Concept "Front page -> explainer": generic headline slips slam in, stack and tremble while a red chart falls;
they drop away for "Every headline moves your money."; one slip flips over and opens into an explainer
(Geopolitics -> Macro -> Markets); the slips come back as a calm bento grid whose red markers flip to green;
the V chart line draws the logo; end card.

Usage:
  python3 code/render.py --orient V --out exports/panicandprofit_EN_1080x1920.mp4
  python3 code/render.py --orient L --scale 0.5 --out previews/s.png --still 1 4 8
"""
import argparse, math, os, subprocess, sys
import numpy as np, skia
sys.path.insert(0, os.path.dirname(__file__))
from timing import FPS, DURATION, EVENTS as EV, FAST, TEXT, HANDLE

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TF = {k: skia.Typeface.MakeFromFile(f"{ROOT}/assets/fonts/{v}.ttf") for k, v in {
    "F600": "Fraunces-600", "F700": "Fraunces-700", "F900": "Fraunces-900", "F400": "Fraunces-400", "FI": "Fraunces-400i",
    "I400": "Inter-400", "I500": "Inter-500", "I600": "Inter-600", "I700": "Inter-700", "I800": "Inter-800"}.items()}

# ---------------- palette (from the Panic & Profit logo) ----------------
def hexc(h, a=1.0):
    h = h.lstrip("#"); return skia.Color(int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16), int(max(0, min(1, a)) * 255))
WHITE, INK, RED, GREEN, GREY = "#FFFFFF", "#151515", "#C8102E", "#1B7F4B", "#6B6B6B"
RULE, FAINT = "#DADADA", "#EFEFEF"

# ---------------- maths ----------------
clamp = lambda x, a=0.0, b=1.0: max(a, min(b, x))
lerp = lambda a, b, t: a + (b - a) * t
def sstep(a, b, x): t = clamp((x - a) / (b - a)); return t * t * (3 - 2 * t)
def ease_out(t): t = clamp(t); return 1 - (1 - t) ** 3
def ease_in(t): t = clamp(t); return t ** 3
def ease_io(t): t = clamp(t); return 4 * t ** 3 if t < .5 else 1 - (-2 * t + 2) ** 3 / 2
def back_out(t, c=1.7): t = clamp(t); return 1 + (c + 1) * (t - 1) ** 3 + c * (t - 1) ** 2
def noise(t, seed, f=1.0):  # smooth pseudo-noise in [-1, 1]
    return (math.sin(t * 7.3 * f + seed * 1.7) * .5 + math.sin(t * 13.1 * f + seed * 3.1) * .3 + math.sin(t * 23.7 * f + seed * 5.3) * .2)

# ---------------- drawing helpers ----------------
def paint(color, stroke=None, blur=0, cap="round"):
    p = skia.Paint(AntiAlias=True, Color=color)
    if stroke:
        p.setStyle(skia.Paint.kStroke_Style); p.setStrokeWidth(stroke)
        p.setStrokeCap(skia.Paint.kRound_Cap if cap == "round" else skia.Paint.kButt_Cap); p.setStrokeJoin(skia.Paint.kRound_Join)
    if blur > 0: p.setMaskFilter(skia.MaskFilter.MakeBlur(skia.kNormal_BlurStyle, blur))
    return p
def tw(s, size, tf, track=0.0):
    f = skia.Font(TF[tf], size)
    return f.measureText(s) + track * size * max(0, len(s) - 1)
def text(c, s, x, y, size, color, tf="F600", align="c", track=0.0, cap=0.36):
    """Draw text vertically centred on y (cap=0.36 ~ centre of caps/x-height). Returns width."""
    f = skia.Font(TF[tf], size); f.setSubpixel(True); w = tw(s, size, tf, track)
    x0 = x + {"c": -w / 2, "l": 0, "r": -w}[align]; yb = y + size * cap; p = paint(color)
    if track == 0: c.drawString(s, x0, yb, f, p)
    else:
        for ch in s: c.drawString(ch, x0, yb, f, p); x0 += f.measureText(ch) + track * size
    return w
def fit(s, size, tf, maxw, track=0.0): w = tw(s, size, tf, track); return size if w <= maxw else size * maxw / w
def rect(x, y, w, h): return skia.Rect.MakeXYWH(x - w / 2, y - h / 2, w, h)
def rr(x, y, w, h, r): return skia.RRect.MakeRectXY(rect(x, y, w, h), r, r)
def alpha_layer(c, a): c.saveLayerAlpha(None, int(clamp(a) * 255))
def tri(c, x, y, s, up, color):
    p = skia.Path()
    if up: p.moveTo(x - s, y + s * .6); p.lineTo(x + s, y + s * .6); p.lineTo(x, y - s * .75)
    else: p.moveTo(x - s, y - s * .6); p.lineTo(x + s, y - s * .6); p.lineTo(x, y + s * .75)
    p.close(); c.drawPath(p, paint(color))
def partial_path(pts, k):
    """Polyline through pts, cut at fraction k of its length; returns (path, head point)."""
    pts = np.asarray(pts, float); seg = np.linalg.norm(np.diff(pts, axis=0), axis=1); L = seg.sum() * clamp(k)
    p = skia.Path(); p.moveTo(*pts[0]); acc = 0; head = pts[0]
    for i, d in enumerate(seg):
        if acc + d >= L:
            u = (L - acc) / max(d, 1e-6); head = pts[i] + (pts[i + 1] - pts[i]) * u; p.lineTo(*head); return p, head
        p.lineTo(*pts[i + 1]); acc += d; head = pts[i + 1]
    return p, head
def rise_word(c, s, x, y, size, color, tf, k, align="l"):
    """Word slides up from behind its own baseline mask (editorial type reveal)."""
    if k <= 0: return tw(s, size, tf)
    c.save(); w = tw(s, size, tf); x0 = x + {"c": -w / 2, "l": 0, "r": -w}[align]
    c.clipRect(skia.Rect.MakeLTRB(x0 - size, y - size * 0.95, x0 + w + size, y + size * 0.42))
    text(c, s, x, y + (1 - ease_out(k)) * size * 1.25, size, color, tf, align); c.restore(); return w

# ---------------- headline slip ----------------
def slip(c, x, y, w, h, kicker, head, state=0.0, rot=0.0, sc=1.0, alpha=1.0, flipy=1.0, shadow=1.0, calm=None):
    """A newsprint headline slip. state 0 = red/down (panic), 1 = green/up (calm).
    flipy squashes vertically (page flip); if calm is given and flipy<0, the back shows the calm headline."""
    if alpha <= 0.01 or sc <= 0.001: return
    c.save(); c.translate(x, y); c.rotate(rot); c.scale(sc, sc)
    back = flipy < 0; c.scale(1, max(0.002, abs(flipy)))
    alpha_layer(c, alpha)
    if shadow > 0: c.drawRect(rect(10, 14, w, h), paint(hexc("#000000", .10 * shadow), blur=16))
    c.drawRect(rect(0, 0, w, h), paint(hexc(WHITE)))
    c.drawRect(rect(0, 0, w, h), paint(hexc(INK), stroke=3, cap="butt"))
    up = back or state >= 1; col = GREEN if up else RED
    if back and calm: kicker, head = "UPDATE", calm
    pad = h * 0.16; box = h * 0.56
    ks = ("" if up else "BREAKING · ") + kicker
    text(c, ks, -w / 2 + pad, -h / 2 + pad + h * 0.06, fit(ks, h * 0.11, "I700", w - pad * 3 - box, 0.12), hexc(col), "I700", "l", track=0.12)
    size = fit(head, h * 0.40, "F900", w - pad * 3 - box)
    text(c, head, -w / 2 + pad, h * 0.13, size, hexc(INK), "F900", "l", cap=0.34)
    bx = w / 2 - pad - box / 2
    c.drawRect(rect(bx, h * 0.06, box, box), paint(hexc(col)))
    tri(c, bx, h * 0.06, box * 0.24, up, hexc(WHITE))
    c.restore(); c.restore()

# ---------------- icons for the explainer ----------------
def icon_globe(c, x, y, r, t, k):
    c.save(); c.translate(x, y); c.scale(k, k); s = paint(hexc(INK), stroke=r * 0.06)
    c.drawCircle(0, 0, r, s)
    for ph in (0, 1, 2):
        e = math.cos(t * 1.4 + ph * math.pi / 3) * r
        c.drawOval(skia.Rect.MakeLTRB(-abs(e), -r, abs(e), r), s)
    for yy in (-0.5, 0, 0.5):
        hw = r * math.sqrt(1 - yy * yy); c.drawLine(-hw, yy * r, hw, yy * r, s)
    c.restore()
def icon_macro(c, x, y, r, t, k):
    c.save(); c.translate(x, y); c.scale(k, k)
    for i, hgt in enumerate((0.55, 0.95, 1.35)):
        g = ease_out(clamp(k * 1.6 - i * 0.25)); hh = r * hgt * g
        c.drawRect(skia.Rect.MakeLTRB(-r + i * r * 0.62, r * 0.75 - hh, -r + i * r * 0.62 + r * 0.42, r * 0.75), paint(hexc(INK)))
    c.drawLine(-r * 1.1, r * 0.75, r * 1.1, r * 0.75, paint(hexc(INK), stroke=r * 0.05))
    text(c, "%", r * 0.78, -r * 0.35, r * 1.05, hexc(INK), "F600")
    c.restore()
def icon_markets(c, x, y, r, t, k):
    c.save(); c.translate(x, y); c.scale(k, k)
    data = [(0.2, -0.3, 0.45, -0.5, 0), (-0.3, -0.05, 0.1, -0.55, 1), (-0.1, 0.35, 0.55, -0.2, 0), (0.35, -0.2, 0.6, -0.45, 1), (-0.2, -0.75, 0.0, -0.95, 1)]
    for i, (o, cl, lo, hi, upc) in enumerate(data):
        cx = -r + i * r * 0.5; col = hexc(GREEN if upc else RED)
        c.drawLine(cx, hi * r, cx, lo * r, paint(col, stroke=r * 0.04))
        c.drawRect(skia.Rect.MakeLTRB(cx - r * 0.13, min(o, cl) * r, cx + r * 0.13, max(o, cl) * r), paint(col))
    c.drawLine(-r * 1.25, r * 0.75, r * 1.25, r * 0.75, paint(hexc(INK), stroke=r * 0.05))
    c.restore()
ICONS = [icon_globe, icon_macro, icon_markets]

# ---------------- logo (redrawn from the spec) ----------------
VPTS = [(0.0, 0.12), (0.14, 0.34), (0.21, 0.27), (0.42, 1.0),     # red: the drop
        (0.58, 0.58), (0.65, 0.66), (1.0, 0.0)]                 # green: the recovery, ending on a dot
VLOW = 3
def logo(c, cx, cy, size, t, t_line, t_word, t_sub, scale=1.0, alpha=1.0):
    """Wordmark 'Panic & Profit' (Fraunces 600 + Fraunces Italic 400 '&'), V chart line, spaced subtitle."""
    if alpha <= 0: return
    c.save(); c.translate(cx, cy); c.scale(scale, scale); alpha_layer(c, alpha)
    parts = [("Panic ", "F600"), ("&", "FI"), (" Profit", "F600")]
    widths = [tw(s, size, f) for s, f in parts]; W = sum(widths); x = -W / 2
    kw = (t - t_word) / 0.55
    for i, (s, f) in enumerate(parts):
        k = clamp(kw * 1.4 - i * 0.22)
        if k > 0:
            c.save(); c.clipRect(skia.Rect.MakeLTRB(x - 20, -size * 1.0, x + widths[i] + 20, size * 0.42))
            text(c, s, x, (1 - ease_out(k)) * size * 1.2, size, hexc(INK), f, "l")
            c.restore()
        x += widths[i]
    # V chart line under the wordmark
    lw, lh, ly = W * 0.9, size * 0.95, size * 0.6
    pts = [(-lw / 2 + px * lw, ly + py * lh) for px, py in VPTS]
    kl = ease_io((t - t_line) / 0.75)
    if kl > 0:
        sw = size * 0.085
        n_red = VLOW + 1; seg = np.linalg.norm(np.diff(np.array(pts), axis=0), axis=1); L = seg.sum(); Lr = seg[:VLOW].sum()
        pr, _ = partial_path(pts[:n_red], min(1, kl * L / Lr)); c.drawPath(pr, paint(hexc(RED), stroke=sw))
        if kl * L > Lr:
            pg, head = partial_path(pts[VLOW:], (kl * L - Lr) / (L - Lr)); c.drawPath(pg, paint(hexc(GREEN), stroke=sw))
        dk = back_out((t - t_line - 0.72) / 0.3, 2.5)
        if dk > 0: c.drawCircle(pts[-1][0], pts[-1][1], sw * 1.25 * dk, paint(hexc(GREEN)))
    # subtitle, tracking in
    ks = ease_out((t - t_sub) / 0.6)
    if ks > 0:
        sub = TEXT["en"]["subtitle"]; ss = size * 0.17; track = lerp(0.6, 0.28, ks)
        sz = fit(sub, ss, "I500", W * 1.02, 0.28)
        alpha_layer(c, ks); text(c, sub, 0, ly + lh + size * 0.42, sz, hexc(GREY), "I500", "c", track=track); c.restore()
    c.restore(); c.restore()

# ---------------- layouts ----------------
def layout(o):
    rng = np.random.default_rng(7)
    if o == "L":
        W, H = 1920, 1080
        stack = [(960 + rx * 330, 600 + ry * 260, rr_ * 7) for rx, ry, rr_ in rng.uniform(-1, 1, (8, 3))]
        grid = [(960 + (i % 2 - 0.5) * 860, 555 + (i // 2 - 1.5) * 192) for i in range(8)]
        return dict(W=W, H=H, slip=(1000, 190), stack=stack, grid=grid, gslip=(830, 172),
                    chart=[(0.04, 0.30), (0.96, 0.92)], top=70,
                    turn=dict(lines=[[0, 1], [2, 3, 4]], x=210, y0=430, lh=210, size=170),
                    card=(960, 560, 1660, 840), tiles=[(-540, 70), (0, 70), (540, 70)], tile=(450, 470), tile_o="col",
                    stmt=dict(lines=[[0, 1, 2], [3, 4]], x=None, y0=470, lh=175, size=150),
                    logo=(960, 410, 165), cta=(960, 845), end_logo=(960, 330, 0.8))
    W, H = 1080, 1920
    stack = [(540 + rx * 50, 420 + i * 162 + ry * 30, rr_ * 6) for i, (rx, ry, rr_) in enumerate(rng.uniform(-1, 1, (8, 3)))]
    grid = [(540, 960 + (i - 3.5) * 168) for i in range(8)]
    return dict(W=W, H=H, slip=(960, 196), stack=stack, grid=grid, gslip=(930, 152),
                chart=[(0.06, 0.24), (0.94, 0.86)], top=150,
                turn=dict(lines=[[0], [1], [2, 3], [4]], x=110, y0=640, lh=215, size=190),
                card=(540, 940, 960, 1500), tiles=[(0, -300), (0, 120), (0, 540)], tile=(860, 360), tile_o="row",
                stmt=dict(lines=[[0], [1, 2], [3], [4]], x=None, y0=700, lh=200, size=165),
                logo=(540, 760, 150), cta=(540, 1240), end_logo=(540, 660, 0.86))

# ---------------- scenes ----------------
def chrome_panic(c, L, t, T):
    """Masthead strip: red BREAKING tag, blinking LIVE dot, hairline and a red ticker band."""
    a = sstep(0.0, 0.25, t) * (1 - sstep(3.5, 3.75, t))
    if a <= 0: return
    W, y = L["W"], L["top"]; alpha_layer(c, a)
    bw = tw(T["breaking"], 26, "I800", 0.14) + 36
    c.drawRect(skia.Rect.MakeXYWH(60, y - 24, bw, 48), paint(hexc(RED)))
    text(c, T["breaking"], 78, y, 26, hexc(WHITE), "I800", "l", track=0.14)
    if int(t * 4) % 2 == 0: c.drawCircle(60 + bw + 34, y, 9, paint(hexc(RED)))
    text(c, T["live"], 60 + bw + 54, y, 24, hexc(INK), "I700", "l", track=0.14)
    c.drawLine(60, y + 46, W - 60, y + 46, paint(hexc(INK), stroke=2, cap="butt"))
    by = y + 46 + 34; c.drawRect(skia.Rect.MakeLTRB(0, by - 26, W, by + 26), paint(hexc(RED)))
    c.save(); c.clipRect(skia.Rect.MakeLTRB(0, by - 26, W, by + 26))
    items = T["ticker"] * 3; x = W - t * 520 - 200
    for s in items:
        tri(c, x, by, 9, False, hexc(WHITE)); x += 24
        x += text(c, s, x, by, 24, hexc(WHITE), "I700", "l", track=0.1) + 70
    c.restore(); c.restore()

def falling_chart(c, L, t):
    if t > 4.1: return
    W, H = L["W"], L["H"]; (x0, y0), (x1, y1) = L["chart"]
    a = 1 - sstep(3.55, 3.95, t)
    for i in range(6):  # faint chart-paper rules
        yy = H * (0.28 + i * 0.12); c.drawLine(0, yy, W, yy, paint(hexc(FAINT, a), stroke=2, cap="butt"))
    rng = np.random.default_rng(3); n = 26
    xs = np.linspace(x0, x1, n) * W; ys = np.linspace(y0, y1, n) * H + rng.uniform(-1, 1, n) * H * 0.045 * np.linspace(.3, 1, n)
    ys[0] = y0 * H; k = sstep(0.2, 3.5, t) ** 0.9
    p, head = partial_path(list(zip(xs, ys)), k)
    c.drawPath(p, paint(hexc(RED, .9 * a), stroke=10))
    if k > 0.02: c.drawCircle(head[0], head[1], 16, paint(hexc(RED, a)))

def shake(t):
    """Camera tremble that grows through the panic, plus a kick on every slam."""
    if t > 3.9: return 0, 0, 0
    amp = sstep(0.3, 3.4, t) * 7
    for e in EV["slips"]:
        if t >= e: amp += 22 * math.exp(-(t - e) * 14)
    return noise(t, 1, 2.2) * amp, noise(t, 2, 2.5) * amp, noise(t, 3, 1.6) * amp * 0.06

def scene_panic(c, L, t, T):
    if t > 4.3: return
    sw, sh = L["slip"]
    for i, (e, (x, y, r)) in enumerate(zip(EV["slips"], L["stack"])):
        if t < e: continue
        u = t - e; k = ease_out(u / 0.16)
        sc = lerp(1.55, 1.0, k); rot = lerp(r * 2.2, r, k)
        # tremble, growing with time; the whole pile falls away at 'fall'
        tr = sstep(0.4, 3.4, t) * (1 + i * 0.15)
        dx = noise(t, i * 3.7, 3) * 4 * tr; dy = noise(t, i * 5.1, 3.3) * 3 * tr; dr = noise(t, i, 2.8) * 1.2 * tr
        f = max(0, t - EV["fall"] - i * 0.025); fy = 2600 * f * f + 300 * f; fr = f * (90 if i % 2 else -90) * (0.6 + 0.1 * i)
        kick, head = T["slips"][i]
        slip(c, x + dx, y + dy + fy, sw, sh, kick, head, rot=rot + dr + fr, sc=sc, alpha=min(1, u / 0.06), shadow=0.6 + 0.4 * k)

def scene_turn(c, L, t, T):
    if not (3.6 < t < 6.3): return
    cfg = L["turn"]; words = T["turn"]; keys = ["w_every", "w_headline", "w_moves", "w_your", "w_money"]
    out = ease_in((t - EV["turn_out"]) / 0.3); size = cfg["size"]
    for line in cfg["lines"]:
        lw_ = sum(tw(words[wi][0], size, "FI" if wi == len(words) - 1 else "F600") for wi in line) + size * 0.24 * (len(line) - 1)
        size = min(size, size * (L["W"] - 2 * cfg["x"]) / lw_)
    for li, line in enumerate(cfg["lines"]):
        x = cfg["x"]; y = cfg["y0"] + li * cfg["lh"] - out * 120
        for wi in line:
            s, _ = words[wi]; last = wi == len(words) - 1
            tf = "FI" if last else "F600"; col = hexc(INK, 1 - out)
            w = rise_word(c, s, x, y, size, col, tf, (t - EV[keys[wi]]) / 0.35)
            if last:  # red underline strikes under "money."
                ku = ease_out((t - EV["w_money"] - 0.3) / 0.4)
                if ku > 0: c.drawLine(x, y + size * 0.5, x + w * ku, y + size * 0.5, paint(hexc(RED, 1 - out), stroke=10, cap="butt"))
            x += w + size * 0.24

def card_geom(L, t):
    """The OIL SPIKES slip returns, flips (scaleY through 0) and expands into the explainer card."""
    sw, sh = L["slip"]; cx, cy, cw, ch = L["card"]
    kin = ease_out((t - EV["slip_back"]) / 0.35); kf = ease_io((t - EV["flip"]) / 0.55)
    ke = ease_io((t - EV["expand"]) / 0.7)
    x = lerp(L["W"] / 2, cx, ke); y = lerp(cy + (1 - kin) * 900, cy, kin)
    w, h = lerp(sw, cw, ke), lerp(sh, ch, ke)
    return x, y, w, h, math.cos(math.pi * kf), kin, ke

def scene_explain(c, L, t, T):
    if not (EV["slip_back"] <= t < 11.8): return
    x, y, w, h, fl, kin, ke = card_geom(L, t)
    out = ease_in((t - EV["card_out"]) / 0.35)
    if fl > 0:  # front: the panic headline
        kick, head = T["slips"][2]
        slip(c, x, y, w, h, kick, head, flipy=fl, sc=1 + 0.06 * (1 - kin))
        return
    c.save(); c.translate(x, y - out * 80); c.scale(1 - 0.08 * out, abs(fl) * (1 - 0.08 * out)); alpha_layer(c, 1 - out)
    c.drawRect(rect(10, 16, w, h), paint(hexc("#000000", .08), blur=20))
    c.drawRect(rect(0, 0, w, h), paint(hexc(WHITE))); c.drawRect(rect(0, 0, w, h), paint(hexc(INK), stroke=3, cap="butt"))
    _, _, cw, ch = L["card"]; s = h / ch
    if ke > 0.55:
        a = sstep(0.55, 1.0, ke); top = -h / 2
        text(c, T["back_kicker"], -w / 2 + 70, top + 70, 26, hexc(GREEN, a), "I800", "l", track=0.18)
        text(c, T["back_title"], -w / 2 + 68, top + 140, 66 if L["tile_o"] == "col" else 70, hexc(INK, a), "F600", "l")
        c.drawLine(-w / 2 + 70, top + 200, w / 2 - 70 - (w - 140) * (1 - a), top + 200, paint(hexc(INK, a), stroke=2, cap="butt"))
    tw_, th = L["tile"]
    for i, ((tx, ty), (num, title, cap)) in enumerate(zip(L["tiles"], T["tiles"])):
        e = EV[f"tile_{i + 1}"]; k = back_out((t - e) / 0.4, 1.3)
        if i > 0:  # arrow from the previous tile
            ka = ease_out((t - (e - 0.3)) / 0.3)
            if ka > 0:
                (px, py) = L["tiles"][i - 1]
                if L["tile_o"] == "col": a0, a1 = (px + tw_ / 2 + 14, ty), (tx - tw_ / 2 - 14, ty)
                else: a0, a1 = (tx, py + th / 2 + 10), (tx, ty - th / 2 - 10)
                ex, ey = lerp(a0[0], a1[0], ka), lerp(a0[1], a1[1], ka)
                c.drawLine(a0[0], a0[1], ex, ey, paint(hexc(INK), stroke=5))
                ang = math.atan2(a1[1] - a0[1], a1[0] - a0[0])
                for da in (2.5, -2.5):
                    c.drawLine(ex, ey, ex + 22 * math.cos(ang + da), ey + 22 * math.sin(ang + da), paint(hexc(INK), stroke=5))
        if k <= 0: continue
        c.save(); c.translate(tx, ty + (1 - clamp(k)) * 40); alpha_layer(c, clamp(k * 1.5))
        c.drawRect(rect(0, 0, tw_, th), paint(hexc("#F6F6F4")))
        c.drawLine(-tw_ / 2, -th / 2, tw_ / 2, -th / 2, paint(hexc(INK), stroke=6, cap="butt"))
        if L["tile_o"] == "col":
            text(c, num, -tw_ / 2 + 34, -th / 2 + 48, 30, hexc(GREY), "I700", "l", track=0.1)
            ICONS[i](c, 0, -55, 78, t, clamp(k))
            text(c, title, 0, 105, 56, hexc(INK), "F600")
            text(c, cap, 0, 168, fit(cap, 27, "I500", tw_ - 50), hexc(GREY), "I500")
        else:
            text(c, num, -tw_ / 2 + 34, -th / 2 + 48, 30, hexc(GREY), "I700", "l", track=0.1)
            ICONS[i](c, -tw_ / 2 + 190, 25, 92, t, clamp(k))
            text(c, title, -tw_ / 2 + 360, -10, 74, hexc(INK), "F600", "l")
            text(c, cap, -tw_ / 2 + 362, 72, fit(cap, 32, "I500", tw_ - 400), hexc(GREY), "I500", "l")
        c.restore(); c.restore()
    c.restore(); c.restore()

def scene_recover(c, L, t, T):
    if not (EV["grid_in"] - 0.05 < t < 16.4): return
    gw, gh = L["gslip"]; back = ease_io((t - (EV["w_understand"] - 0.15)) / 0.5)
    out = ease_in((t - EV["statement_out"]) / 0.35)
    c.save(); cx, cy = L["W"] / 2, L["H"] / 2 + (40 if L["H"] > L["W"] else 0)
    c.translate(cx, cy); s = 1 - 0.1 * back; c.scale(s, s); c.translate(-cx, -cy)
    ga = (1 - 0.88 * back) * (1 - out)
    for i, ((gx, gy), (sx, sy, sr)) in enumerate(zip(L["grid"], L["stack"])):
        k = ease_io((t - EV["grid_in"] - i * 0.06) / 0.7)
        if k <= 0: continue
        x, y = lerp(sx, gx, k), lerp(sy + L["H"] * 0.72, gy, k); rot = lerp(sr * 3, 0, k)
        kf = ease_io((t - EV["flip_green"] - i * 0.1) / 0.32); fl = math.cos(math.pi * kf)
        kick, head = T["slips"][i]
        slip(c, x, y, gw, gh, kick, head, rot=rot, alpha=ga, flipy=fl, calm=T["calm"][i], shadow=0.6)
    c.restore()
    # statement over the receding grid
    cfg = L["stmt"]; words = T["statement"]; keys = ["w_understand", "w_understand", "w_world", "w_invest", "w_better"]
    delays = [0, 0.18, 0.3, 0, 0.12]; size = cfg["size"]
    for li, line in enumerate(cfg["lines"]):
        widths = [tw(words[wi][0], size, "F600") for wi in line]; total = sum(widths) + size * 0.24 * (len(line) - 1)
        x = L["W"] / 2 - total / 2; y = cfg["y0"] + li * cfg["lh"] - out * 140
        for wi, w in zip(line, widths):
            s, g = words[wi]; col = hexc(GREEN if g else INK, 1 - out)
            rise_word(c, s, x, y, size, col, "F600", (t - EV[keys[wi]] - delays[wi]) / 0.38)
            if wi == 4:
                ku = ease_out((t - EV["w_better"] - 0.35) / 0.45)
                if ku > 0: c.drawLine(x, y + size * 0.5, x + w * ku, y + size * 0.5, paint(hexc(GREEN, 1 - out), stroke=10, cap="butt"))
            x += w + size * 0.24

def scene_logo(c, L, t, T):
    if t < EV["vline"] - 0.05: return
    lx, ly, size = L["logo"]; ex, ey, es = L["end_logo"]
    k = ease_io((t - EV["to_endcard"]) / 0.45)
    logo(c, lerp(lx, ex, k), lerp(ly, ey, k), size, t, EV["vline"], EV["wordmark"], EV["subtitle"], scale=lerp(1, es, k))
    # CTA pill
    kc = back_out((t - EV["cta"]) / 0.4, 1.4); out = ease_in((t - EV["to_endcard"]) / 0.3)
    if kc > 0 and out < 1:
        x, y = L["cta"]; s = T["cta"]; fs = 46 if L["W"] > L["H"] else 44; w = tw(s, fs, "I600") + 90
        c.save(); c.translate(x, y + out * 60); c.scale(kc, kc); alpha_layer(c, 1 - out)
        c.drawRRect(rr(0, 0, w, fs * 2.1, fs * 1.05), paint(hexc(INK)))
        text(c, s, 0, 0, fs, hexc(WHITE), "I600")
        c.restore(); c.restore()

def endcard(c, L, t, T):
    if t < EV["to_endcard"] + 0.15: return
    W, H = L["W"], L["H"]; u = t - EV["to_endcard"]
    # editorial frame closing in
    kf = ease_out(u / 0.5); m = 46
    p, _ = partial_path([(W / 2, m), (W - m, m), (W - m, H - m), (m, H - m), (m, m), (W / 2, m)], kf)
    c.drawPath(p, paint(hexc(INK), stroke=3, cap="butt"))
    ex, ey, es = L["end_logo"]; size = L["logo"][2] * es; base = ey + size * 2.25
    v = L["H"] > L["W"]
    items = [(HANDLE, 64 if v else 60, "I700", INK, 0.0, 0.0), (T["end_line"], 36 if v else 34, "I500", GREY, 0.0, 0.1)]
    y = base + (60 if v else 40)
    for i, (s, fs, tf, col, track, d) in enumerate(items):
        k = ease_out((u - 0.15 - d) / 0.4)
        if k > 0: text(c, s, W / 2, y + (1 - k) * 24, fit(s, fs, tf, W - 160), hexc(col, k), tf)
        y += fs * (1.9 if i == 0 else 1.6)
    k = ease_out((u - 0.4) / 0.4)
    if k > 0:
        c.drawLine(W / 2 - 60 * k, y + 10, W / 2 + 60 * k, y + 10, paint(hexc(RULE), stroke=2, cap="butt"))
        text(c, T["end_small"], W / 2, y + 58, 22 if not v else 24, hexc(GREY, k), "I600", track=0.2)

# ---------------- frame ----------------
class Renderer:
    def __init__(self, orient, scale, lang="en"):
        self.o = orient; self.L = layout(orient); self.T = TEXT[lang]; self.scale = scale
        self.W, self.H = self.L["W"], self.L["H"]
        self.surf = skia.Surface(int(self.W * scale), int(self.H * scale))
    def draw(self, t):
        c = self.surf.getCanvas(); c.save(); c.scale(self.scale, self.scale); c.clear(hexc(WHITE))
        L, T, W, H = self.L, self.T, self.W, self.H
        dx, dy, dr = shake(t)
        c.save(); c.translate(W / 2 + dx, H / 2 + dy); c.rotate(dr)
        z = 1 + 0.025 * sstep(6.2, 11.2, t) + 0.02 * sstep(15.8, 18.7, t); c.scale(z, z); c.translate(-W / 2, -H / 2)
        falling_chart(c, L, t); scene_panic(c, L, t, T)
        scene_turn(c, L, t, T); scene_explain(c, L, t, T); scene_recover(c, L, t, T); scene_logo(c, L, t, T)
        c.restore()
        chrome_panic(c, L, t, T); endcard(c, L, t, T)
        c.restore()
        return self.surf.makeImageSnapshot().toarray()
    def frame(self, t, fps):
        n = 1
        for a, b, k in FAST:
            if a <= t <= b: n = max(n, k)
        for e in EV["slips"]:
            if e <= t <= e + 0.16: n = max(n, 4)
        if 0.3 < t < 3.55: n = max(n, 2)
        if n == 1: return self.draw(t)
        dt = 1 / fps
        acc = sum(self.draw(t + dt * ((k + 0.5) / n - 0.5)).astype(np.float32) for k in range(n)); return (acc / n).astype(np.uint8)

if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--orient", default="V"); ap.add_argument("--scale", type=float, default=1.0); ap.add_argument("--fps", type=int, default=FPS)
    ap.add_argument("--lang", default="en"); ap.add_argument("--out", required=True); ap.add_argument("--audio", default=None)
    ap.add_argument("--still", type=float, nargs="*")
    a = ap.parse_args(); R = Renderer(a.orient, a.scale, a.lang); audio = a.audio or f"{ROOT}/audio/mix_{a.lang}.wav"
    if a.still:
        import cv2
        for t in a.still: cv2.imwrite(a.out.replace(".png", f"_{t:05.2f}.png"), R.draw(t)[:, :, :3])
        sys.exit()
    w, h = R.surf.width(), R.surf.height()
    cmd = ["ffmpeg", "-y", "-loglevel", "error", "-f", "rawvideo", "-pix_fmt", "bgra", "-s", f"{w}x{h}", "-r", str(a.fps), "-i", "-"]
    if os.path.exists(audio): cmd += ["-i", audio, "-c:a", "aac", "-b:a", "192k", "-shortest"]
    cmd += ["-c:v", "libx264", "-preset", "medium", "-crf", "17", "-pix_fmt", "yuv420p", "-movflags", "+faststart", a.out]
    ff = subprocess.Popen(cmd, stdin=subprocess.PIPE)
    for f in range(int(DURATION * a.fps)):
        ff.stdin.write(R.frame(f / a.fps, a.fps).tobytes())
        if f % (a.fps * 2) == 0: print(f"{f / a.fps:5.1f}s", flush=True)
    ff.stdin.close(); ff.wait(); print("done", a.out)
