"""Draw the Woody Guthrie quote's chalk quotation marks: Images/chalk-quotes.webp.

Drawn the same way as the homepage's chalk stars (scripts/make_chalk_stars.py:
the same chalk, wobble, grain and dust): row 1 is the opening mark, row 2 the
closing mark, each drawn three times ("boil" frames) so the line shimmers
like stop motion when the frames cycle. White chalk, used by the stylesheet
as a stencil over the name's flowing gradient. 192px cells.

Needs numpy, scipy and pillow; fixed seeds, so rerunning reproduces the sheet.
"""
import math, os
import numpy as np
from PIL import Image
from scipy import ndimage as ndi

CELL, FRAMES, SS = 192, 3, 4
N = CELL * SS
OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'Images', 'chalk-quotes.webp')

# One comma of a closing mark (unit coordinates, y down): a round head
# coloured in with a tight spiral, and a tail that curls down to the left.
def comma(cx, cy, s):
    head = []
    for k in range(5):   # a spiral from the rim inward fills the head the way chalk is scrubbed in
        r = .24 * (1 - k / 5.2)
        head += [(r * math.cos(t), r * math.sin(t)) for t in np.linspace(k * 2 * math.pi, (k + 1) * 2 * math.pi, 18, endpoint=False)]
    tail = [(.22 * math.cos(t), .22 * math.sin(t)) for t in np.linspace(-.5, 1.2, 8)]
    tail += [(.18 - .30 * u, .2 + .55 * u - .12 * u * u) for u in np.linspace(.1, 1, 9)]
    return [[(cx + x * s, cy + y * s) for x, y in st] for st in (head, tail)]
def closing():
    return comma(-.38, -.28, 1.35) + comma(.42, -.28, 1.35)
def opening():   # the closing mark turned upside down
    return [[(-x, -y) for x, y in st] for st in closing()]
DESIGNS = [opening(), closing()]

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
        a = draw(strokes, np.random.default_rng(5000 + d * 10 + f))
        cell = sheet[d * CELL:(d + 1) * CELL, f * CELL:(f + 1) * CELL]
        cell[..., 0], cell[..., 1], cell[..., 2] = 246, 243, 234
        cell[..., 3] = a
Image.fromarray(sheet, 'RGBA').save(OUT, 'WEBP', quality=88, alpha_quality=90, method=6)
print('wrote', OUT, os.path.getsize(OUT), 'bytes', sheet.shape[1], 'x', sheet.shape[0])
