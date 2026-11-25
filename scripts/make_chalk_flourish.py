"""Draw the flourishes above and below the Woody Guthrie quote: Images/chalk-flourish.webp.

(owner, 2026-11-25: "put a little handdrawn simple western flourish above and below the quote ... in the style of the other
animations, high resolution, flip book, well thought out, each stroke with intention, using elements of art, looking
handdrawn. like the stars or the duck or the section logos".)

The design, after a sign-painter's divider: a small diamond at the centre with a dot over and under it (the point the eye
lands on), and from it one long S-sweep out to each side - it rises, dips, and rolls into a curl at its end - with a short
leaf-flick under the first rise to balance the weight. Every stroke is a pen stroke: it starts light, swells where the hand
presses through the curve and thins to nothing as it lifts, so the line has rhythm (thick and thin) rather than an even wire.
The two halves are drawn separately, so they mirror each other the way a hand mirrors - nearly, never exactly.

Drawn in chalk the same way as the quote's marks and the homepage's stars (scripts/make_chalk_quotes.py, make_chalk_stars.py):
the board's grain and streaks break the line up, solid down the middle and skipping toward its edges, and a little dust
is shed along it. Row 1 is the flourish over the quote, row 2 the one under it (the same figure turned upside down, so the
pair frames the words); each is drawn three times ("boil" frames) so it shivers like a flipbook when the frames cycle.
White, used by the stylesheet as a stencil.

Needs numpy, scipy and pillow; fixed seeds, so rerunning reproduces the sheet.
  python3 scripts/make_chalk_flourish.py
"""
import math, os
import numpy as np
from PIL import Image
from scipy import ndimage as ndi

CW, CH, FRAMES, SS = 1500, 400, 3, 2   # each cell 1500 x 400 (3.75:1), drawn at twice that: sharp at its largest size on 3x screens
W, H = CW * SS, CH * SS
OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'Images', 'chalk-flourish.webp')


def cubic(p0, p1, p2, p3, n):
    t = np.linspace(0, 1, n)[:, None]
    p0, p1, p2, p3 = (np.array(p, float) for p in (p0, p1, p2, p3))
    return (1 - t) ** 3 * p0 + 3 * (1 - t) ** 2 * t * p1 + 3 * (1 - t) * t * t * p2 + t ** 3 * p3


def curl(end, prev, turn, r0, n):
    """A curl rolling on from a stroke's end: it carries on in the stroke's direction and winds inward, `turn` = +1 / -1."""
    d = np.array(end) - np.array(prev); d /= np.linalg.norm(d)
    nrm = np.array([-d[1], d[0]]) * turn                     # toward the curl's centre
    c = np.array(end) + nrm * r0
    a0 = math.atan2(end[1] - c[1], end[0] - c[0])
    th = np.linspace(0, 1.85 * math.pi, n)
    r = r0 * (1 - .66 * th / th[-1])                        # winding in: each turn tighter
    a = a0 - turn * th
    return np.stack([c[0] + r * np.cos(a), c[1] + r * np.sin(a)], 1)


def half(sign):
    """The right half (sign=+1) or the left (-1): unit coordinates, x from the centre outward, y down; height about +-0.5."""
    s = lambda pts: [(sign * x, y) for x, y in pts]
    strokes = []
    # the main sweep: leaves the diamond, rises, dips through the middle and rolls into the end curl
    sweep = cubic((.12, 0), (.55, -.46), (1.0, .42), (1.5, -.04), 170)
    tail = curl(sweep[-1], sweep[-6], -1, .19, 90)
    pts = np.vstack([sweep, tail[1:]])
    strokes.append((s(pts), 'swell', 1.0))
    # the leaf-flick under the first rise: a short counter-stroke that balances the sweep's weight
    flick = cubic((.3, .07), (.48, .3), (.76, .3), (.92, .12), 70)
    strokes.append((s(flick), 'lift', .42))
    return strokes


def centre():
    # the diamond (two strokes, each side of it) and a dot above and below
    left = cubic((0, -.2), (-.08, -.08), (-.08, .08), (0, .2), 40)
    right = cubic((0, -.2), (.08, -.08), (.08, .08), (0, .2), 40)
    return [(list(map(tuple, left)), 'swell', .7), (list(map(tuple, right)), 'swell', .7),
            ([(0, -.34)] * 6, 'dot', .75), ([(0, .34)] * 6, 'dot', .75)]


def draw(flip, rng):
    ink = np.zeros((H, W), np.float32); dust = np.zeros((H, W), np.float32)
    scale = W * .47 / 1.72; cx, cy = W / 2, H / 2   # (the figure spans about 94% of its cell)
    yy, xx = np.mgrid[0:H, 0:W]
    g_rot = rng.uniform(-.012, .012); g_dy = rng.uniform(-.015, .015)   # the whole figure sits a hair differently each redraw
    strokes = half(1) + half(-1) + centre()
    for pts, kind, weight in strokes:
        pts = np.array(pts, float)
        if flip: pts[:, 1] *= -1
        n0 = len(pts)
        # (the stroke resampled every pixel or so of its length, so even its thinnest hairline is one unbroken line)
        seg = np.r_[0, np.cumsum(np.hypot(*np.diff(pts, axis=0).T))] * scale
        if seg[-1] > 0:
            n = max(n0, int(seg[-1] / 1.5)); u = np.linspace(0, seg[-1], n)
            pts = np.stack([np.interp(u, seg, pts[:, 0]), np.interp(u, seg, pts[:, 1])], 1)
        n = len(pts); k_w = n / n0
        # hand wobble: a small smooth drift, different on every stroke and every redraw (the same wavelength whatever the sampling)
        walk = ndi.gaussian_filter1d(np.cumsum(rng.normal(0, .0028 / math.sqrt(k_w), (n, 2)), 0), 6 * k_w, axis=0) + ndi.gaussian_filter1d(rng.normal(0, .0022, (n, 2)), 1.5 * k_w, axis=0)
        width = H * .021 * weight * rng.uniform(.92, 1.08)
        for i in range(n):
            x, y = pts[i] + walk[i]; y += g_dy
            x, y = x * math.cos(g_rot) - y * math.sin(g_rot), x * math.sin(g_rot) + y * math.cos(g_rot)
            px, py = cx + x * scale, cy + y * scale
            t = i / max(1, n - 1)
            if kind == 'swell':  p = .12 + .88 * math.sin(math.pi * min(1, t * 1.08)) ** .7      # light in, full through the curve, thin out
            elif kind == 'lift': p = (.35 + .65 * math.sin(math.pi * t * .5 + .3)) * (1 - .75 * t ** 1.6)   # pressed at the start, lifting away
            else:                p = 1.35                                                          # a dot: one press of the chalk
            r = max(.8, width * p * (1 + rng.uniform(-.05, .05)))
            x0, x1, y0, y1 = int(px - r - 2), int(px + r + 3), int(py - r - 2), int(py + r + 3)
            if x0 < 0 or y0 < 0 or x1 > W or y1 > H: continue
            sub = ((xx[y0:y1, x0:x1] - px) ** 2 + (yy[y0:y1, x0:x1] - py) ** 2 <= r * r) * rng.uniform(.82, 1)
            ink[y0:y1, x0:x1] = np.maximum(ink[y0:y1, x0:x1], sub)
            if rng.random() < .35 / k_w:   # chalk dust shed along the stroke (as often per length as before)
                dx, dy = rng.normal(0, r * 1.4, 2)
                if 0 <= int(py + dy) < H and 0 <= int(px + dx) < W: dust[int(py + dy), int(px + dx)] = rng.uniform(.3, .7)
    # the board's grain and streaks, as on the stars and the quote marks
    k = H / 768 * 2.2
    grain = ndi.gaussian_filter(rng.random((H, W)).astype(np.float32), 1.4 * k); grain = (grain - grain.mean()) / grain.std()
    streak = ndi.gaussian_filter(rng.random((H, W)).astype(np.float32), (0.6 * k, 5 * k)); streak = (streak - streak.mean()) / streak.std()
    core = ndi.gaussian_filter((ink > 0).astype(np.float32), 2.2 * k)
    edge = np.clip((1 - core) * 2, 0, 1)
    a = ink * np.clip(1.02 + (0.12 + 0.5 * edge) * grain + 0.1 * streak - 0.3 * edge, 0, 1)
    a = np.maximum(a, ndi.gaussian_filter(dust, 1.1 * k) * 2.0)
    return np.asarray(Image.fromarray((np.clip(a, 0, 1) * 255).astype(np.uint8)).resize((CW, CH), Image.LANCZOS))


sheet = np.zeros((2 * CH, FRAMES * CW, 4), np.uint8)
for row, flip in enumerate((False, True)):
    for f in range(FRAMES):
        a = draw(flip, np.random.default_rng(9100 + row * 10 + f))
        cell = sheet[row * CH:(row + 1) * CH, f * CW:(f + 1) * CW]
        cell[..., 0], cell[..., 1], cell[..., 2] = 246, 243, 234
        cell[..., 3] = a
Image.fromarray(sheet, 'RGBA').save(OUT, 'WEBP', quality=92, alpha_quality=95, method=6)
print('wrote', OUT, os.path.getsize(OUT), 'bytes', sheet.shape[1], 'x', sheet.shape[0])
