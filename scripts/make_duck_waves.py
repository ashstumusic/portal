"""Draw About's divider: Images/duck-waves.svg.

A simple hand-drawn sketch of a line of waves with a little rubber duck
bobbing in it (the owner's request), drawn four times with a different hand
wobble each time so it boils like a flipbook when the frames cycle. The duck
bobs and tips a touch from frame to frame. Frames are stacked top to bottom
(1200 x 60 units each). The stylesheet uses the sheet as a stencil over the
name's flowing gradient, scaled to the line's height and centred, so the duck
sits in the middle and the waves run off both sides.

Plain Python, fixed seed, so rerunning reproduces the sheet.
"""
import math, os, random

W, H, FRAMES = 1200, 60, 4
WATER = 40          # the waterline
DX = 600            # where the duck sits
OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'Images', 'duck-waves.svg')

def qbez(p0, p1, p2, n=14):
    return [((1 - t) ** 2 * p0[0] + 2 * (1 - t) * t * p1[0] + t * t * p2[0],
             (1 - t) ** 2 * p0[1] + 2 * (1 - t) * t * p1[1] + t * t * p2[1]) for t in (i / n for i in range(n + 1))]

def circle(cx, cy, r, n=22, start=0.0):
    return [(cx + r * math.cos(start + 2 * math.pi * i / n * 1.08), cy + r * math.sin(start + 2 * math.pi * i / n * 1.08)) for i in range(n + 1)]

def duck():
    """Strokes in duck space (waterline at y=0, facing right). Only what's above the water is drawn."""
    return [
        qbez((-25, -13), (-22, -3), (-15, 0)),                 # tail down to the water
        qbez((-25, -13), (-14, -5), (-3, -9)),                 # back
        circle(6, -20, 8.5, start=1.9),                        # head
        qbez((12, -13), (22, -9), (17, 0)),                    # chest down to the water
        qbez((-13, -6), (-6, -1), (2, -6)),                    # wing
        qbez((14, -22), (21, -21), (23, -18)) + qbez((23, -18), (19, -15.5), (14, -16.5))[1:],   # beak
    ]

def waves(rng, phase):
    pts = []
    for i in range(0, W + 1, 6):
        x = i
        calm = min(1, max(0, (abs(x - DX) - 30) / 40)) ** 2   # the water settles right around the duck
        y = WATER + calm * (5 * math.sin((x + phase) / 15) + 1.2 * math.sin((x + phase * 1.7) / 6.5))
        pts.append((x, y))
    return pts

def ripples():
    # two short ripple marks either side of the duck
    return [qbez((DX - 52, WATER + 9), (DX - 44, WATER + 6), (DX - 36, WATER + 9)),
            qbez((DX + 38, WATER + 9), (DX + 46, WATER + 6), (DX + 54, WATER + 9))]

def wobble(pts, rng, amp):
    # a smooth hand drift across the line, plus a little shake
    out, dx, dy = [], 0.0, 0.0
    for x, y in pts:
        dx = dx * .8 + rng.gauss(0, amp); dy = dy * .8 + rng.gauss(0, amp)
        out.append((x + dx, y + dy))
    return out

def path(pts):
    return 'M' + ' L'.join(f'{x:.1f} {y:.1f}' for x, y in pts)

rng = random.Random(1907)
groups = []
for f in range(FRAMES):
    oy = f * H
    bob = (-1.2, .4, -.6, .9)[f]            # the duck bobs
    tip = math.radians((-3, 2.5, -1.5, 3)[f])   # and tips a touch
    ds = []
    for st in duck():
        pts = [(DX + 1.25 * (x * math.cos(tip) - y * math.sin(tip)), WATER + bob + 1.25 * (x * math.sin(tip) + y * math.cos(tip))) for x, y in st]
        ds.append(path(wobble(pts, rng, .35)))
    ds.append(path(wobble(waves(rng, f * 9), rng, .45)))
    for st in ripples():
        ds.append(path(wobble(st, rng, .35)))
    eye = (DX + 1.25 * 9 + rng.uniform(-.4, .4), WATER + bob + 1.25 * -22 + rng.uniform(-.4, .4))
    groups.append(f'<g transform="translate(0 {oy})"><path d="{" ".join(ds)}"/><circle cx="{eye[0]:.1f}" cy="{eye[1]:.1f}" r="1.9" fill="#fff" stroke="none"/></g>')

svg = (f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {W} {H * FRAMES}" width="{W}" height="{H * FRAMES}">'
       f'<g fill="none" stroke="#fff" stroke-width="3.2" stroke-linecap="round" stroke-linejoin="round">{"".join(groups)}</g></svg>\n')
open(OUT, 'w').write(svg)
print('wrote', OUT, len(svg), 'bytes')
