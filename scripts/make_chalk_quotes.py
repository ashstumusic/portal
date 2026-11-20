"""Draw the Woody Guthrie quote's quotation marks: Images/chalk-quotes.webp.

Simple and hand-drawn, the way a person jots quotation marks with a pen: each
mark is two quick strokes, a little uneven (the second never quite matches
the first), tapering where the pen lifts and fuller where it presses. Solid
line, no chalk grain. Row 1 is the opening mark, row 2 the closing mark, each
drawn three times ("boil" frames) so the marks shiver like a flipbook when
the frames cycle. White, used by the stylesheet as a stencil over the name's
flowing gradient. 192px cells (the sheet layout the stylesheet expects).

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
    ink = np.zeros((N, N), np.float32)
    scale = N * .44; c = N / 2
    # the whole drawing sits a little differently each time it's redrawn
    g_rot = rng.uniform(-.07, .07); g_dx, g_dy = rng.uniform(-.025, .025), rng.uniform(-.025, .025)
    yy, xx = np.mgrid[0:N, 0:N]
    for pts, kind in strokes:
        # hand wobble: a small smooth drift across the line
        walk = ndi.gaussian_filter1d(np.cumsum(rng.normal(0, .007, (len(pts), 2)), 0), 4, axis=0)
        k = rng.uniform(.9, 1.1)
        width = SS * 9 * k
        for i, ((x, y), (wx, wy)) in enumerate(zip(pts, walk)):
            x, y = x + wx + g_dx, y + wy + g_dy
            x, y = x * math.cos(g_rot) - y * math.sin(g_rot), x * math.sin(g_rot) + y * math.cos(g_rot)
            px, py = c + x * scale, c + y * scale
            t = i / (len(pts) - 1)
            p = (.25 + .75 * t ** .8) if kind == 'grow' else (1 - .78 * t ** 1.2)   # pen pressure
            r = width * p
            x0, x1, y0, y1 = int(px - r - 2), int(px + r + 3), int(py - r - 2), int(py + r + 3)
            sub = ((xx[y0:y1, x0:x1] - px) ** 2 + (yy[y0:y1, x0:x1] - py) ** 2 <= r * r).astype(np.float32)
            ink[y0:y1, x0:x1] = np.maximum(ink[y0:y1, x0:x1], sub)
    # a slightly soft, slightly uneven edge, like ink on paper
    ink = ndi.gaussian_filter(ink, SS * .6)
    img = Image.fromarray((np.clip(ink, 0, 1) * 255).astype(np.uint8)).resize((CELL, CELL), Image.LANCZOS)
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
