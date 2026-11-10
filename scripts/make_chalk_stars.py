"""Draw the homepage's chalk stars: Images/chalk-stars.webp.

Six hand-drawn hollow five-point stars, each drawn three times ("boil" frames:
the same drawing redone with fresh hand wobble and chalk grain, so the
line shimmers like hand-drawn stop motion when the frames cycle). White
chalk with pressure variation, broken by the board's grain, with a little
dust. Rows are designs, columns are frames; 128px cells.

Needs numpy, scipy and pillow (python3 -m venv .venv && .venv/bin/pip
install numpy scipy pillow), then: .venv/bin/python scripts/make_chalk_stars.py
Fixed seeds: rerunning reproduces the sheet.
"""
import math, os, random
import numpy as np
from PIL import Image
from scipy import ndimage as ndi

CELL, FRAMES, SS = 128, 3, 4            # cell px, boil frames, supersampling
N = CELL * SS
OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'Images', 'chalk-stars.webp')

# ── the designs, in unit coordinates (-1..1, y down); each is a list of strokes ──
def star_pts(n, r_out, r_in, rot=-math.pi / 2):
    return [((r_out if i % 2 == 0 else r_in) * math.cos(rot + i * math.pi / n), (r_out if i % 2 == 0 else r_in) * math.sin(rot + i * math.pi / n)) for i in range(2 * n)]
def outline_star(n=5, ro=.86, ri=.38, overshoot=.35):
    p = star_pts(n, ro, ri); pts = p + [p[0]]
    # carry on past the start a little, the way a hand doesn't stop exactly
    a, b = p[0], p[1]; pts.append((a[0] + (b[0] - a[0]) * overshoot, a[1] + (b[1] - a[1]) * overshoot))
    return [pts]
def pentagram(r=.86):
    v = [(r * math.cos(-math.pi / 2 + k * 4 * math.pi / 5), r * math.sin(-math.pi / 2 + k * 4 * math.pi / 5)) for k in range(6)]
    return [v]
def asterisk(n, r=.85, wob=0):
    return [[(-r * math.cos(t), -r * math.sin(t)), (r * math.cos(t), r * math.sin(t))] for t in [k * math.pi / n + wob for k in range(n)]]
def twinkle(r=.88, k=.16):
    pts = []
    for q in range(4):
        a0 = q * math.pi / 2 - math.pi / 2
        for s in range(9):
            t = s / 8
            tip = (r * math.cos(a0), r * math.sin(a0)); nxt = (r * math.cos(a0 + math.pi / 2), r * math.sin(a0 + math.pi / 2))
            # concave side: a curve pulled toward the centre
            x = (1 - t) ** 2 * tip[0] + 2 * (1 - t) * t * 0 * k + t * t * nxt[0]
            y = (1 - t) ** 2 * tip[1] + 2 * (1 - t) * t * 0 * k + t * t * nxt[1]
            pts.append((x, y))
    pts.append(pts[0])
    return [pts]
def burst(n=10, r0=.28, r1=.88):
    strokes = [[(r0 * math.cos(t), r0 * math.sin(t)) for t in np.linspace(0, 2 * math.pi, 14)]]
    for k in range(n):
        t = k * 2 * math.pi / n; rr = r1 if k % 2 == 0 else r1 * .72
        strokes.append([((r0 + .12) * math.cos(t), (r0 + .12) * math.sin(t)), (rr * math.cos(t), rr * math.sin(t))])
    return strokes
def sparkle():
    return [[(0, -.9), (0, .9)], [(-.9, 0), (.9, 0)], [(-.42, -.42), (.42, .42)], [(-.42, .42), (.42, -.42)]]
def shine_star():
    s = outline_star(5, .62, .27)
    for t in (-2.2, -1.55, -0.9):
        s.append([(.78 * math.cos(t), .78 * math.sin(t)), (.96 * math.cos(t), .96 * math.sin(t))])
    return s
def sun_star():
    s = [[(.3 * math.cos(t), .3 * math.sin(t)) for t in np.linspace(0, 2 * math.pi, 16)]]
    for k in range(8):
        t = k * math.pi / 4 + .2
        s.append([(.45 * math.cos(t), .45 * math.sin(t)), (.82 * math.cos(t), .82 * math.sin(t))])
    return s
def scribble_star():
    s = outline_star(5, .86, .4, .2)
    # quick hatching inside, back and forth
    pts = []
    for i, y in enumerate(np.linspace(-.5, .45, 8)):
        w = .34 - abs(y) * .2
        pts += [(-w, y), (w, y + .06)] if i % 2 == 0 else [(w, y), (-w, y + .06)]
    s.append(pts)
    return s
def shooting():
    s = [[(x * .55 + .3, y * .55 - .3) for x, y in outline_star(5, .86, .38, .25)[0]]]
    for dy in (-.12, 0, .12):
        s.append([(-.05, -.02 + dy * 1.2), (-.88, .7 + dy)])
    return s
def cross():
    return [[(0, -.62), (0, .62)], [(-.62, 0), (.62, 0)], [(-.08, -.04), (.06, .05), (-.02, .08), (-.07, -.03)]]

# Just basic hollow five-point stars: six hand-drawn variations (fatter or
# skinnier points, a little tilt, the stroke closing short or long).
def tilted(strokes, t):
    return [[(x * math.cos(t) - y * math.sin(t), x * math.sin(t) + y * math.cos(t)) for x, y in st] for st in strokes]
DESIGNS = [outline_star(5, .86, .38, .30), tilted(outline_star(5, .86, .42, .18), .12), outline_star(5, .88, .34, .45),
           tilted(outline_star(5, .84, .40, .25), -.10), outline_star(5, .86, .44, .12), tilted(outline_star(5, .87, .36, .38), .2)]

# ── chalk ──
def resample(pts, step):
    out = []
    for (x0, y0), (x1, y1) in zip(pts, pts[1:]):
        L = math.hypot(x1 - x0, y1 - y0); n = max(1, int(L / step))
        out += [(x0 + (x1 - x0) * i / n, y0 + (y1 - y0) * i / n) for i in range(n)]
    out.append(pts[-1]); return out
def draw(strokes, rng):
    stroke = np.zeros((N, N), np.float32); dust = np.zeros((N, N), np.float32)
    scale = N * .44; cx = cy = N / 2
    # the whole drawing sits a little differently each time it's redrawn
    g_rot = rng.uniform(-.06, .06); g_dx, g_dy = rng.uniform(-.02, .02), rng.uniform(-.02, .02)
    yy, xx = np.mgrid[0:N, 0:N]
    for s in strokes:
        pts = resample(s, .02)
        # hand wobble: a smooth random walk across the line
        walk = np.cumsum(rng.normal(0, .006, (len(pts), 2)), 0); walk -= np.linspace(0, 1, len(pts))[:, None] * walk[-1]
        walk = ndi.gaussian_filter1d(walk, 3, axis=0) + rng.normal(0, .004, (1, 2))
        width = SS * rng.uniform(3.0, 3.8)
        for i, ((x, y), (wx, wy)) in enumerate(zip(pts, walk)):
            x, y = x + wx + g_dx, y + wy + g_dy
            x, y = x * math.cos(g_rot) - y * math.sin(g_rot), x * math.sin(g_rot) + y * math.cos(g_rot)
            px, py = cx + x * scale, cy + y * scale
            t = i / max(1, len(pts) - 1)
            r = width * (0.75 + 0.35 * math.sin(math.pi * t) + rng.uniform(-.08, .08))   # pressure: lighter at the ends
            x0, x1, y0, y1 = int(px - r - 2), int(px + r + 3), int(py - r - 2), int(py + r + 3)
            sub = (xx[y0:y1, x0:x1] - px) ** 2 + (yy[y0:y1, x0:x1] - py) ** 2 <= r * r
            stroke[y0:y1, x0:x1] = np.maximum(stroke[y0:y1, x0:x1], sub * rng.uniform(.75, 1))
            if rng.random() < .35:   # chalk dust shed along the stroke
                dx, dy = rng.normal(0, r * 1.6, 2)
                if 0 <= int(py + dy) < N and 0 <= int(px + dx) < N: dust[int(py + dy), int(px + dx)] = rng.uniform(.3, .7)
    # the board's grain breaks the line up
    grain = ndi.gaussian_filter(rng.random((N, N)).astype(np.float32), 1.2)
    grain = (grain - grain.mean()) / grain.std()
    streak = ndi.gaussian_filter(rng.random((N, N)).astype(np.float32), (0.6, 5)); streak = (streak - streak.mean()) / streak.std()
    a = stroke * np.clip(0.75 + 0.45 * grain + 0.25 * streak, 0, 1)
    a = np.maximum(a, ndi.gaussian_filter(dust, 1.2) * 2.2)
    img = Image.fromarray((np.clip(a, 0, 1) * 255).astype(np.uint8)).resize((CELL, CELL), Image.LANCZOS)
    return np.asarray(img)

sheet = np.zeros((len(DESIGNS) * CELL, FRAMES * CELL, 4), np.uint8)
for d, strokes in enumerate(DESIGNS):
    for f in range(FRAMES):
        a = draw(strokes, np.random.default_rng(1000 + d * 10 + f))
        cell = sheet[d * CELL:(d + 1) * CELL, f * CELL:(f + 1) * CELL]
        cell[..., 0], cell[..., 1], cell[..., 2] = 246, 243, 234   # warm chalk white
        cell[..., 3] = a
Image.fromarray(sheet, 'RGBA').save(OUT, 'WEBP', quality=88, alpha_quality=90, method=6)
print('wrote', OUT, os.path.getsize(OUT), 'bytes', sheet.shape[1], 'x', sheet.shape[0])
