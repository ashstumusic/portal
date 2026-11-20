"""Draw the Woody Guthrie quote's quotation marks: Images/chalk-quotes.webp.

Simple and hand-drawn: each mark is two quick strokes, a little uneven (the
second never quite matches the first), tapering where the hand lifts and fuller
where it presses. Drawn in chalk the same way as the homepage's chalk stars
(scripts/make_chalk_stars.py): the board's grain and streaks break the line up
and a little dust is shed along it. Row 1 is the opening mark, row 2 the
closing mark, each drawn three times ("boil" frames) so the marks shiver like a
flipbook when the frames cycle. White, used by the stylesheet as a stencil over
the name's flowing gradient. 192px cells (the sheet layout the stylesheet expects).

Needs numpy, scipy and pillow; fixed seeds, so rerunning reproduces the sheet.
"""
import math, os
import numpy as np
from PIL import Image
from scipy import ndimage as ndi

CELL, FRAMES, SS = 192, 3, 4
N = CELL * SS
OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'Images', 'chalk-quotes.webp')

def bez(p0, p1, p2, n=40):
    return [((1 - t) ** 2 * p0[0] + 2 * (1 - t) * t * p1[0] + t * t * p2[0],
             (1 - t) ** 2 * p0[1] + 2 * (1 - t) * t * p1[1] + t * t * p2[1]) for t in np.linspace(0, 1, n)]

# One tick of a mark (unit coordinates, y down). Opening: the pen starts light up
# and to the right, curves down and lands with pressure. Closing: starts with
# pressure at the top and flicks away down to the left, lifting as it goes.
def tick_open(x, s, lean):
    return (bez((x + .12 * s + lean, -.26 * s), (x - .14 * s, -.06 * s), (x - .02 * s, .2 * s)), 'grow')
def tick_close(x, s, lean):
    return (bez((x + .02 * s, -.2 * s), (x + .15 * s, .04 * s), (x - .12 * s + lean, .26 * s)), 'fade')
DESIGNS = [
    [tick_open(-.3, 1.5, 0), tick_open(.28, 1.38, .04)],
    [tick_close(-.28, 1.4, .04), tick_close(.3, 1.5, 0)],
]

def draw(strokes, rng):
    ink = np.zeros((N, N), np.float32); dust = np.zeros((N, N), np.float32)
    scale = N * .44; c = N / 2
    # the whole drawing sits a little differently each time it's redrawn
    g_rot = rng.uniform(-.07, .07); g_dx, g_dy = rng.uniform(-.025, .025), rng.uniform(-.025, .025)
    yy, xx = np.mgrid[0:N, 0:N]
    for pts, kind in strokes:
        # hand wobble: a small smooth drift across the line
        walk = ndi.gaussian_filter1d(np.cumsum(rng.normal(0, .007, (len(pts), 2)), 0), 4, axis=0)
        width = SS * 5.8 * rng.uniform(.9, 1.1)
        for i, ((x, y), (wx, wy)) in enumerate(zip(pts, walk)):
            x, y = x + wx + g_dx, y + wy + g_dy
            x, y = x * math.cos(g_rot) - y * math.sin(g_rot), x * math.sin(g_rot) + y * math.cos(g_rot)
            px, py = c + x * scale, c + y * scale
            t = i / (len(pts) - 1)
            p = (.45 + .55 * t ** .8) if kind == 'grow' else (1 - .6 * t ** 1.2)   # hand pressure
            r = width * p * (1 + rng.uniform(-.06, .06))
            x0, x1, y0, y1 = int(px - r - 2), int(px + r + 3), int(py - r - 2), int(py + r + 3)
            sub = ((xx[y0:y1, x0:x1] - px) ** 2 + (yy[y0:y1, x0:x1] - py) ** 2 <= r * r) * rng.uniform(.8, 1)
            ink[y0:y1, x0:x1] = np.maximum(ink[y0:y1, x0:x1], sub)
            if rng.random() < .5:   # chalk dust shed along the stroke
                dx, dy = rng.normal(0, r * 1.3, 2)
                if 0 <= int(py + dy) < N and 0 <= int(px + dx) < N: dust[int(py + dy), int(px + dx)] = rng.uniform(.3, .7)
    # the board's grain and streaks break the line up (as on the stars)
    grain = ndi.gaussian_filter(rng.random((N, N)).astype(np.float32), 1.2); grain = (grain - grain.mean()) / grain.std()
    streak = ndi.gaussian_filter(rng.random((N, N)).astype(np.float32), (0.6, 5)); streak = (streak - streak.mean()) / streak.std()
    a = ink * np.clip(0.75 + 0.45 * grain + 0.25 * streak, 0, 1)
    a = np.maximum(a, ndi.gaussian_filter(dust, 1.2) * 2.2)
    img = Image.fromarray((np.clip(a, 0, 1) * 255).astype(np.uint8)).resize((CELL, CELL), Image.LANCZOS)
    return np.asarray(img)

sheet = np.zeros((len(DESIGNS) * CELL, FRAMES * CELL, 4), np.uint8)
for d, strokes in enumerate(DESIGNS):
    for f in range(FRAMES):
        a = draw(strokes, np.random.default_rng(7000 + d * 10 + f))
        cell = sheet[d * CELL:(d + 1) * CELL, f * CELL:(f + 1) * CELL]
        cell[..., 0], cell[..., 1], cell[..., 2] = 246, 243, 234
        cell[..., 3] = a
Image.fromarray(sheet, 'RGBA').save(OUT, 'WEBP', quality=88, alpha_quality=90, method=6)
print('wrote', OUT, os.path.getsize(OUT), 'bytes', sheet.shape[1], 'x', sheet.shape[0])
