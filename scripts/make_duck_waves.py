"""Draw About's divider: a line of waves with a rubber duck swimming a figure 8 in it (the owner's request).

Writes three things:
  Images/pool-waves.svg   the water: a hand-drawn line of gentle waves, drawn four times with a different hand
                          wobble each time (1200 x 60 units per frame, stacked top to bottom). A white stencil:
                          the stylesheet lays it over the name's gradient.
  Images/rubber-duck.svg  the duck, side on and facing right, with a ripple mark either side: four drawings
                          (120 x 60 units each, stacked), each wobbled and bobbing a touch differently. Drawn in
                          About's deep gradient, filled white so the water line doesn't show through its body.
  the @keyframes duck-eight block, printed: paste it into shared/system.css ("About's divider"). The duck swims a
                          figure 8 across the width of the line, 96 positions over 16 seconds (six a second, the
                          page's flipbook beat). Seen from the side, the loop's depth shows as the duck getting a
                          little smaller and higher on the far side and bigger and lower on the near side, and it
                          turns (a partial turn about its upright axis) as its heading swings into and out of the
                          depth, coming round at each end of the pool.

Plain Python, fixed seed, so rerunning reproduces everything.
"""
import math, os, random

HERE = os.path.dirname(os.path.abspath(__file__))
IMG = os.path.join(HERE, '..', 'Images')
FRAMES = 4

def qbez(p0, p1, p2, n=14):
    return [((1 - t) ** 2 * p0[0] + 2 * (1 - t) * t * p1[0] + t * t * p2[0],
             (1 - t) ** 2 * p0[1] + 2 * (1 - t) * t * p1[1] + t * t * p2[1]) for t in (i / n for i in range(n + 1))]

def arc(cx, cy, r, a0, a1, n=22):
    return [(cx + r * math.cos(a0 + (a1 - a0) * i / n), cy + r * math.sin(a0 + (a1 - a0) * i / n)) for i in range(n + 1)]

def wobble(pts, rng, amp):
    out, dx, dy = [], 0.0, 0.0
    for x, y in pts:
        dx = dx * .8 + rng.gauss(0, amp); dy = dy * .8 + rng.gauss(0, amp)
        out.append((x + dx, y + dy))
    return out

def path(pts, close=False):
    return 'M' + ' L'.join(f'{x:.1f} {y:.1f}' for x, y in pts) + (' Z' if close else '')

rng = random.Random(1907)

# ── the water ──
W, H, WATER = 1200, 60, 40
groups = []
for f in range(FRAMES):
    pts = [(x, WATER + 3.6 * math.sin((x + f * 9) / 15) + 1 * math.sin((x + f * 15) / 6.5)) for x in range(0, W + 1, 6)]
    groups.append(f'<path transform="translate(0 {f * H})" d="{path(wobble(pts, rng, .45))}"/>')
open(os.path.join(IMG, 'pool-waves.svg'), 'w').write(
    f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {W} {H * FRAMES}" width="{W}" height="{H * FRAMES}">'
    f'<g fill="none" stroke="#fff" stroke-width="3.2" stroke-linecap="round" stroke-linejoin="round">{"".join(groups)}</g></svg>\n')

# ── the duck ── (duck space: waterline y=0, facing right; only what's above the water is drawn)
CW, CH, CX, CY, S = 120, 60, 60, 44, 1.25
def duck_lines():
    return [
        qbez((-25, -13), (-22, -3), (-15, 0)),                  # tail down to the water
        qbez((-25, -13), (-14, -5), (-3, -9)),                  # back
        arc(6, -20, 8.5, 1.9, 1.9 + 2 * math.pi * 1.05),        # head
        qbez((12, -13), (22, -9), (17, 0)),                     # chest down to the water
        qbez((-13, -6), (-6, -1), (2, -6)),                     # wing
        qbez((14, -22), (21, -21), (23, -18)) + qbez((23, -18), (19, -15.5), (14, -16.5))[1:],   # beak
    ]
def duck_body():   # the white fill behind the lines
    return qbez((-25, -13), (-14, -5), (-3, -9)) + arc(6, -20, 8.5, 2.2, 2.2 + 2 * math.pi * .78) + qbez((12, -13), (22, -9), (17, 0))[1:] + [(-15, 0)] + qbez((-15, 0), (-22, -3), (-25, -13))[1:]
groups = []
for f in range(FRAMES):
    bob = (-.8, .4, -.4, .7)[f]; tip = math.radians((-3, 2.5, -1.5, 3)[f])
    place = lambda pts: [(CX + S * (x * math.cos(tip) - y * math.sin(tip)), CY + bob + S * (x * math.sin(tip) + y * math.cos(tip))) for x, y in pts]
    lines = [path(wobble(place(st), rng, .3)) for st in duck_lines()]
    lines += [path(wobble(st, rng, .3)) for st in (qbez((CX - 48, CY + 9), (CX - 40, CY + 6), (CX - 32, CY + 9)),
                                                   qbez((CX + 34, CY + 9), (CX + 42, CY + 6), (CX + 50, CY + 9)))]
    ex, ey = place([(9, -22)])[0]
    groups.append(f'<g transform="translate(0 {f * CH})"><path d="{path(place(duck_body()), True)}" fill="#fff" stroke="none"/>'
                  f'<path d="{" ".join(lines)}" fill="none"/><circle cx="{ex:.1f}" cy="{ey:.1f}" r="1.9" fill="url(#g)" stroke="none"/></g>')
open(os.path.join(IMG, 'rubber-duck.svg'), 'w').write(
    f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {CW} {CH * FRAMES}" width="{CW}" height="{CH * FRAMES}">'
    '<defs><linearGradient id="g" gradientUnits="userSpaceOnUse" x1="25" y1="0" x2="95" y2="0">'
    '<stop offset="0" stop-color="#B0145E"/><stop offset=".5" stop-color="#A8400A"/><stop offset="1" stop-color="#0B6A8C"/></linearGradient></defs>'
    f'<g stroke="url(#g)" stroke-width="3.2" stroke-linecap="round" stroke-linejoin="round">{"".join(groups)}</g></svg>\n')

# ── the figure 8 ──
N, AX, DEPTH = 96, 40, .5   # positions; how far either side of the middle it swims (% of the line); loop depth vs width
out, prev = ['@keyframes duck-eight {'], None
for i in range(N):
    th = 2 * math.pi * i / N
    x = 50 + AX * math.sin(th)
    z = math.sin(2 * th) / 2                                    # + is the far side of the loop
    heading = math.degrees(math.atan2(DEPTH * math.cos(2 * th), math.cos(th)))   # 0 = swimming right, 180 = left
    side = 0 if abs(heading) < 90 else (180 if heading > 0 else -180)
    yaw = side + (heading - side) * .65                         # mostly side on: only part of the turn shows
    sc, dy = 1 - .28 * z, -7 * z
    out.append(f'  {100 * i / N:.4g}% {{ left: {x:.2f}%; transform: translate(-50%, {dy:.1f}px) scale({sc:.3f}) rotateY({yaw:.0f}deg); }}')
out.append('}')
print('\n'.join(out))
