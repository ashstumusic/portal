"""Draw About's divider: a line of waves with a rubber duck swimming a figure 8 in it (the owner's request).

Writes three things:
  Images/pool-waves.svg   the water: a hand-drawn line of gentle waves, drawn four times with a different hand
                          wobble each time (1200 x 60 units per frame, stacked top to bottom). A white stencil:
                          the stylesheet lays it over the name's gradient.
  Images/rubber-duck.svg  the duck in five poses (rows: side on, three-quarter towards you, front, three-quarter
                          away, back), each drawn four times (columns) with a different hand wobble and bob, with a
                          ripple mark either side. 120 x 60 units per cell. Drawn in About's deep gradient, filled
                          white so the water line doesn't show through its body.
  the @keyframes duck-eight block, printed: paste it into shared/system.css ("About's divider"). The duck swims a
                          figure 8 across the width of the line, 96 positions over 16 seconds (six a second, the
                          page's flipbook beat). Seen from the side, the loop's depth shows as the duck getting a
                          little smaller and higher on the far side and bigger and lower on the near side, and it
                          turns like a hand-drawn flipbook: it steps through the drawn poses for its heading (not a
                          flat picture spinning), mirrored when heading left.

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

# ── the duck ── (duck space: waterline y=0; only what's above the water is drawn)
# Five poses, drawn like a Disney flipbook turn rather than a flat card spinning: side on (facing right),
# three-quarter towards you, straight at you, three-quarter away, and straight away (its tail to you). Facing left is
# the same drawings mirrored; the mirror is swapped in only at the front or back pose, where it can't be seen.
CW, CH, CX, CY, S = 120, 60, 60, 44, 1.25
def poly_close(*parts):
    pts = []
    for p in parts: pts += p
    return pts
def circle(cx, cy, r, a0=0.0, turns=1.05):
    return arc(cx, cy, r, a0, a0 + 2 * math.pi * turns)
def mirror(pts): return [(-x, y) for x, y in pts]
POSES = []
# side, facing right
POSES.append(dict(
    lines=[qbez((-25, -13), (-22, -3), (-15, 0)), qbez((-25, -13), (-14, -5), (-3, -9)), circle(6, -20, 8.5, 1.9),
           qbez((12, -13), (22, -9), (17, 0)), qbez((-13, -6), (-6, -1), (2, -6)),
           qbez((14, -21.5), (18.5, -21), (19.5, -19.5)) + qbez((19.5, -16.5), (18, -15.5), (14, -16.5)),   # (whistling: the bill pursed short...)
           circle(21.3, -18, 2.1, 2.2)],                                                                     # (...round a little "o")
    fills=[poly_close(qbez((-25, -13), (-14, -5), (-3, -9)), qbez((12, -13), (22, -9), (17, 0)), [(-15, 0)], qbez((-15, 0), (-22, -3), (-25, -13))), circle(6, -20, 8.5, 0, 1)],
    eyes=[(9, -22)]))
# three-quarter, turned towards you (still heading right)
POSES.append(dict(
    lines=[qbez((-20, -11), (-18, -3), (-12, 0)), qbez((-20, -11), (-12, -6), (-5, -9)), circle(3, -20, 8.5, 1.9),
           qbez((9, -13), (17, -7), (12, 0)), qbez((-12, -5), (-6, -1), (-1, -5)),
           qbez((4, -17.5), (8.5, -17.5), (9.5, -16.5)) + qbez((9.5, -14), (8, -13.2), (4, -14.5)),
           circle(11, -15.3, 1.9, 2.2)],
    fills=[poly_close(qbez((-20, -11), (-12, -6), (-5, -9)), qbez((9, -13), (17, -7), (12, 0)), [(-12, 0)], qbez((-12, 0), (-18, -3), (-20, -11))), circle(3, -20, 8.5, 0, 1)],
    eyes=[(0, -22), (6.5, -22.5)]))
# straight at you: a low round body under a round head, and the bill a small solid shape pointing at you
POSES.append(dict(
    lines=[qbez((-21, 0), (-23, -8), (-9, -10)), qbez((21, 0), (23, -8), (9, -10)), circle(0, -22, 9.5, 1.9)],
    fills=[poly_close(qbez((-21, 0), (-23, -8), (-9, -10)), qbez((9, -10), (23, -8), (21, 0))), circle(0, -22, 9.5, 0, 1)],
    solids=[circle(0, -14.5, 4.2, 0, 1)],          # (whistling: the bill puckered into a round "o"...)
    holes=[circle(0, -14.3, 1.7, 0, 1)],          # (...open in the middle)
    eyes=[(-4, -23.5), (4, -23.5)]))
# three-quarter, turned away (still heading right): its tail to you, the head going away
POSES.append(dict(
    lines=[qbez((-17, -12), (-14, -4), (-9, 0)), qbez((-17, -12), (-10, -8.5), (-3, -10)), circle(5, -21, 8.5, 1.9),
           qbez((11, -12), (19, -6), (14, 0)), qbez((-6, -6), (0, -2), (6, -6)),
           qbez((13, -22), (16.5, -21.5), (17, -19.5))],
    fills=[poly_close(qbez((-17, -12), (-10, -8.5), (-3, -10)), qbez((11, -12), (19, -6), (14, 0)), [(-9, 0)], qbez((-9, 0), (-14, -4), (-17, -12))), circle(5, -21, 8.5, 0, 1)],
    eyes=[]))
# straight away (its back to you): the low round body under the head, and the little tail flicked up
POSES.append(dict(
    lines=[qbez((-21, 0), (-23, -9), (-8, -12)), qbez((21, 0), (23, -9), (8, -12)), circle(0, -21, 9, 1.9),
           qbez((-3.5, -2), (0, -8), (3.5, -2))],
    fills=[poly_close(qbez((-21, 0), (-23, -9), (-8, -12)), qbez((8, -12), (23, -9), (21, 0))), circle(0, -21, 9, 0, 1)],
    eyes=[]))
RIPPLES = (qbez((-48, 9), (-40, 6), (-32, 9)), qbez((34, 9), (42, 6), (50, 9)))
cells = []
for pi, pose in enumerate(POSES):
    for f in range(FRAMES):
        bob = (-.8, .4, -.4, .7)[f]; tip = math.radians((-3, 2.5, -1.5, 3)[f])
        place = lambda pts: [(CX + S * (x * math.cos(tip) - y * math.sin(tip)), CY + bob + S * (x * math.sin(tip) + y * math.cos(tip))) for x, y in pts]
        lines = [path(wobble(place(st), rng, .28)) for st in pose['lines']]
        lines += [path(wobble([(CX + x, CY + y) for x, y in st], rng, .3)) for st in RIPPLES]
        fills = ''.join(f'<path d="{path(place(fp), True)}" fill="#fff" stroke="none"/>' for fp in pose['fills'])
        solids = ''.join(f'<path d="{path(wobble(place(sp), rng, .2), True)}" fill="#C2560E" stroke="none"/>' for sp in pose.get('solids', []))   # (the bill: one orange, as a rubber duck's is)
        solids += ''.join(f'<path d="{path(place(hp), True)}" fill="#2A1A24" stroke="none"/>' for hp in pose.get('holes', []))
        eyes = ''.join(f'<circle cx="{ex:.1f}" cy="{ey:.1f}" r="1.8" fill="#2A1A24" stroke="none"/>' for ex, ey in place(pose['eyes']))
        cells.append(f'<g transform="translate({f * CW} {pi * CH})">{fills}<path d="{" ".join(lines)}" fill="none"/>{solids}{eyes}</g>')
NP = len(POSES)
open(os.path.join(IMG, 'rubber-duck.svg'), 'w').write(
    f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {CW * FRAMES} {CH * NP}" width="{CW * FRAMES}" height="{CH * NP}">'
    '<defs><linearGradient id="g" gradientUnits="objectBoundingBox" x1="0" y1="0" x2="1" y2="0">'
    '<stop offset="0" stop-color="#B0145E"/><stop offset=".5" stop-color="#A8400A"/><stop offset="1" stop-color="#0B6A8C"/></linearGradient></defs>'
    f'<g stroke="url(#g)" stroke-width="3.2" stroke-linecap="round" stroke-linejoin="round">{"".join(cells)}</g></svg>\n')

# ── the tune ── (owner's request: the duck whistles)
# Images/duck-notes.svg: little hand-drawn music notes drifting up out of the duck's bill, 12 drawings stepped six a
# second (a 2-second loop). Each cell is 120 x 120 units: its lower half lines up with a duck cell (so the bill, side
# on, is at about (89, 81)) and the notes rise into the upper half. Three notes are in the air at a time, each carried
# forward from the bill and rising a little in a gentle wave (staying clear of the name above), turning a little, growing as they leave the bill and shrinking away near the top. Same pencil
# line and gradient as the duck; drawn afresh each frame, so they boil like everything else.
NCW, NCH, NF = 120, 120, 12
BILL = (89, 81)
def note_shape(kind):
    """note drawings in note space (head at the origin, about 10 units tall): (stroked lines, filled heads)"""
    head = lambda cx, cy: [(cx + 2.6 * math.cos(a) * math.cos(-.45) - 1.8 * math.sin(a) * math.sin(-.45),
                            cy + 2.6 * math.cos(a) * math.sin(-.45) + 1.8 * math.sin(a) * math.cos(-.45)) for a in (2 * math.pi * i / 16 for i in range(17))]
    if kind == 0:   # a single eighth note
        return [[(2.2, -.8), (2.2, -11)], qbez((2.2, -11), (6.5, -8.5), (5.5, -4.5))], [head(0, 0)]
    else:           # two beamed notes
        return [[(2.2, -.8), (2.2, -11)], [(10.2, -2.3), (10.2, -12.5)], [(2.2, -11), (10.2, -12.5)], [(2.2, -9), (10.2, -10.5)]], [head(0, 0), head(8, -1.5)]
ncells = []
for f in range(NF):
    parts = []
    for k in range(3):
        t = ((f / NF) + k / 3) % 1                       # 0 = just left the bill, 1 = gone
        kind = (k + (1 if (f + 4 * k) // NF % 2 else 0)) % 2
        x = BILL[0] + 4 + 26 * t                                            # (carried forward from the bill, at head height...)
        y = BILL[1] - 3 - 9 * t - 3.5 * math.sin(t * 2 * math.pi + k * 2.1)  # (...lifting only a little, in a gentle wave: the name sits close above)
        sc = 1.2 * ((.55 + 1.6 * t) if t < .3 else 1.03 - .45 * max(0, t - .7) / .3)
        rot = math.radians(-12 + 22 * math.sin(t * 5 + k))
        tf = lambda pts: [(x + sc * (px * math.cos(rot) - py * math.sin(rot)), y + sc * (px * math.sin(rot) + py * math.cos(rot))) for px, py in pts]
        strokes, heads = note_shape(kind)
        parts.append(''.join(f'<path d="{path(wobble(tf(h), rng, .18), True)}" fill="url(#g)" stroke="none"/>' for h in heads))
        parts.append(f'<path d="{" ".join(path(wobble(tf(st), rng, .22)) for st in strokes)}" fill="none"/>')
    ncells.append(f'<g transform="translate({f * NCW} 0)">{"".join(parts)}</g>')
open(os.path.join(IMG, 'duck-notes.svg'), 'w').write(
    f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {NCW * NF} {NCH}" width="{NCW * NF}" height="{NCH}">'
    '<defs><linearGradient id="g" gradientUnits="userSpaceOnUse" x1="70" y1="0" x2="120" y2="0" spreadMethod="pad">'
    '<stop offset="0" stop-color="#B0145E"/><stop offset=".5" stop-color="#A8400A"/><stop offset="1" stop-color="#0B6A8C"/></linearGradient></defs>'
    f'<g stroke="url(#g)" stroke-width="2.6" stroke-linecap="round" stroke-linejoin="round">{"".join(ncells)}</g></svg>\n')

# ── the figure 8 ──
# 96 stepped positions over 16 seconds. Each picks the pose for the duck's heading (side on when crossing the pool,
# coming round through three-quarter and front or back views at the ends), mirrored when it's heading left; the
# far side of the loop is a little smaller and higher, the near side bigger and lower. Rows of the sheet:
# 0 side, 1 three-quarter towards, 2 front, 3 three-quarter away, 4 back.
N, AX, DEPTH = 96, 40, .5
out = ['@keyframes duck-eight {']
for i in range(N):
    th = 2 * math.pi * i / N
    x = 50 + AX * math.sin(th)
    z = math.sin(2 * th) / 2                                    # + is the far side of the loop
    h = math.degrees(math.atan2(DEPTH * math.cos(2 * th), math.cos(th)))   # 0 = heading right, 180 = left, + = away
    off = abs(h) if abs(h) <= 90 else 180 - abs(h)               # how far it has turned from side on
    away = h > 0
    if off < 20: row = 0
    elif off < 78: row = 3 if away else 1
    else: row = 4 if away else 2
    left = abs(h) > 90 or (abs(h) == 90 and False)
    sc, dy = 1 - .28 * z, -7 * z
    sx = -sc if left else sc
    out.append(f'  {100 * i / N:.4g}% {{ left: {x:.2f}%; transform: translate(-50%, {dy:.1f}px) scale({sx:.3f}, {sc:.3f}); background-position-y: {row * 25}%; }}')
out.append('}')
print('\n'.join(out))
