"""Draw About's divider: a line of waves with a rubber duck swimming a figure 8 in it, whistling a tune (owner's requests).

Writes four things:
  Images/pool-waves.svg   the water: a hand-drawn line of gentle waves, drawn four times with a different hand
                          wobble each time (1200 x 60 units per frame, stacked top to bottom). A white stencil:
                          the stylesheet lays it over the name's gradient.
  Images/rubber-duck.svg  the duck in five poses (rows: side on, three-quarter towards you, front, three-quarter
                          away, back), each drawn four times (columns) with a different hand wobble and bob, with a
                          ripple mark either side. 120 x 60 units per cell. Drawn in About's deep gradient, filled
                          white so the water line doesn't show through its body; its bill pursed into a whistling "o".
  Images/duck-notes.svg   the tune: music notes drifting out of the bill, 12 drawings per pose (rows match the duck's).
  the @keyframes duck-eight block, printed: paste it into shared/system.css ("About's divider"). The duck swims a
                          figure 8 across the width of the line, 96 positions over 16 seconds (six a second, the
                          page's flipbook beat). Seen from the side, the loop's depth shows as the duck getting a
                          little smaller and higher on the far side and bigger and lower on the near side, and it
                          turns like a hand-drawn flipbook: it steps through the drawn poses for its heading (not a
                          flat picture spinning), mirrored when heading left.

How the line is drawn (owner's request: every frame drawn with care, as if by hand): every line is a pencil stroke,
not a uniform pen line - a filled shape that starts light, swells as the pencil presses and lifts away at the end,
with a little uneven pressure along it - following a smooth curve (no straight-segment facets), with a gentle hand
wobble that is drawn afresh in every frame (the flipbook "boil"). Closed shapes (the head) overlap where the pencil
comes back round, as a hand-drawn circle does.

Plain Python, fixed seed, so rerunning reproduces everything.
"""
import math, os, random

HERE = os.path.dirname(os.path.abspath(__file__))
IMG = os.path.join(HERE, '..', 'Images')
FRAMES = 4

def qbez(p0, p1, p2, n=14):
    return [((1 - t) ** 2 * p0[0] + 2 * (1 - t) * t * p1[0] + t * t * p2[0],
             (1 - t) ** 2 * p0[1] + 2 * (1 - t) * t * p1[1] + t * t * p2[1]) for t in (i / n for i in range(n + 1))]

def arc(cx, cy, r, a0, a1, n=40):
    return [(cx + r * math.cos(a0 + (a1 - a0) * i / n), cy + r * math.sin(a0 + (a1 - a0) * i / n)) for i in range(n + 1)]

def resample(pts, step):
    """the same line, as points about `step` apart"""
    out = [pts[0]]
    for (x0, y0), (x1, y1) in zip(pts, pts[1:]):
        d = math.hypot(x1 - x0, y1 - y0); k = max(1, int(d / step))
        out += [(x0 + (x1 - x0) * i / k, y0 + (y1 - y0) * i / k) for i in range(1, k + 1)]
    return out

def wobble(pts, rng, amp):
    """a hand's slight unsteadiness: a slow random drift, never a jag"""
    out, dx, dy = [], 0.0, 0.0
    for x, y in pts:
        dx = dx * .86 + rng.gauss(0, amp); dy = dy * .86 + rng.gauss(0, amp)
        out.append((x + dx, y + dy))
    return out

def smooth(pts, passes=2):
    """Chaikin corner-cutting: rounds the line off as a moving hand does"""
    for _ in range(passes):
        q = [pts[0]]
        for (x0, y0), (x1, y1) in zip(pts, pts[1:]):
            q += [(.75 * x0 + .25 * x1, .75 * y0 + .25 * y1), (.25 * x0 + .75 * x1, .25 * y0 + .75 * y1)]
        q.append(pts[-1]); pts = q
    return pts

def _n(v):
    """a number, short: one decimal, no leading zero, no trailing .0"""
    t = f'{v:.1f}'.rstrip('0').rstrip('.') if abs(v) >= .05 else '0'
    return t.replace('0.', '.', 1) if t.startswith('0.') else t.replace('-0.', '-.', 1)

def curve(pts, close=True):
    """A smooth path through the points: quadratic curves bent at each point and joined at the midpoints between them
    (a smooth line with no straight-segment facets), written with relative coordinates to keep the file small."""
    n = len(pts)
    if n < 3: return 'M' + ' L'.join(f'{_n(x)} {_n(y)}' for x, y in pts)
    mid = lambda a, b: ((a[0] + b[0]) / 2, (a[1] + b[1]) / 2)
    start = mid(pts[-1], pts[0]) if close else pts[0]
    cx, cy = round(start[0], 1), round(start[1], 1)
    d = f'M{_n(cx)} {_n(cy)}q'
    seq = range(n) if close else range(1, n - 1)
    parts = []
    for i in seq:
        c = pts[i]; e = mid(pts[i], pts[(i + 1) % n]) if (close or i < n - 2) else pts[n - 1]
        c1 = (round(c[0] - cx, 1), round(c[1] - cy, 1)); e1 = (round(e[0] - cx, 1), round(e[1] - cy, 1))
        parts.append(f'{_n(c1[0])} {_n(c1[1])} {_n(e1[0])} {_n(e1[1])}')
        cx, cy = round(cx + e1[0], 1), round(cy + e1[1], 1)
    return d + ' '.join(parts) + ('Z' if close else '')

def pencil(pts, rng, w=3.2, amp=.2, step=1.6, lift=.2, res=2.8):
    """One pencil stroke along the line, as a filled outline: it starts light, swells as the pencil presses, keeps a
    little uneven pressure along its length, and lifts away at the end. Returns a smooth closed path."""
    c = smooth(wobble(resample(pts, step), rng, amp), 1)
    L = [0.0]
    for (x0, y0), (x1, y1) in zip(c, c[1:]): L.append(L[-1] + math.hypot(x1 - x0, y1 - y0))
    tot = L[-1] or 1; ph = rng.uniform(0, 6.28); ph2 = rng.uniform(0, 6.28)
    w *= min(1, .55 + tot / 40)   # (a short flick of the pencil is lighter than a long pressed line)
    left, right = [], []
    for i, (x, y) in enumerate(c):
        t = L[i] / tot
        a = c[max(0, i - 1)]; b = c[min(len(c) - 1, i + 1)]
        nx, ny = -(b[1] - a[1]), b[0] - a[0]; nl = math.hypot(nx, ny) or 1; nx /= nl; ny /= nl
        press = min(1, t / lift) ** .7 * min(1, (1 - t) / (lift * 1.3)) ** .8       # pencil down ... lifted off
        hw = w / 2 * (.28 + .72 * press) * (1 + .1 * math.sin(t * 9 + ph) + .05 * math.sin(t * 23 + ph2))
        left.append((x + nx * hw, y + ny * hw)); right.append((x - nx * hw, y - ny * hw))
    # (a smooth curve needs a point only every `res` units: the rest are thinned out, keeping both lifted ends)
    def thin(side):
        kept = [side[0]]
        for q in side[1:-1]:
            if math.hypot(q[0] - kept[-1][0], q[1] - kept[-1][1]) >= res: kept.append(q)
        return kept + [side[-1]]
    return curve(thin(left) + thin(right[::-1]), True)

def fill_shape(pts, rng=None, amp=0):
    p = resample(pts, 3.2)
    if rng: p = wobble(p, rng, amp)
    return curve(p[::1], True)

rng = random.Random(1907)

# ── the water ──
W, H, WATER = 1200, 60, 40
groups = []
for f in range(FRAMES):
    pts = [(x, WATER + 3.6 * math.sin((x + f * 9) / 15) + 1 * math.sin((x + f * 15) / 6.5)) for x in range(0, W + 1, 3)]
    groups.append(f'<path transform="translate(0 {f * H})" d="{pencil(pts, rng, w=3.4, amp=.12, step=3, lift=.02, res=7)}"/>')
open(os.path.join(IMG, 'pool-waves.svg'), 'w').write(
    f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {W} {H * FRAMES}" width="{W}" height="{H * FRAMES}">'
    f'<g fill="#fff" stroke="none">{"".join(groups)}</g></svg>\n')

# ── the duck ── (duck space: waterline y=0; only what's above the water is drawn)
# Five poses, drawn like a Disney flipbook turn rather than a flat card spinning: side on (facing right),
# three-quarter towards you, straight at you, three-quarter away, and straight away (its tail to you). Facing left is
# the same drawings mirrored; the mirror is swapped in only at the front or back pose, where it can't be seen.
# The bill is pursed into a whistling "o" (owner's request): one orange shape with a dark opening, in every pose
# that shows it.
CW, CH, CX, CY, S = 120, 60, 60, 44, 1.25
BILL_ORANGE, INK = '#C2560E', '#2A1A24'
def poly_close(*parts):
    pts = []
    for p in parts: pts += p
    return pts
def circle(cx, cy, r, a0=0.0, turns=1.08):
    return arc(cx, cy, r, a0, a0 + 2 * math.pi * turns, 56)
def oval(cx, cy, rx, ry, rot=0.0, n=24):
    c, s_ = math.cos(rot), math.sin(rot)
    return [(cx + rx * math.cos(a) * c - ry * math.sin(a) * s_, cy + rx * math.cos(a) * s_ + ry * math.sin(a) * c) for a in (2 * math.pi * i / n for i in range(n))]
POSES = []
# side, facing right
POSES.append(dict(
    lines=[qbez((-25, -13), (-22, -3), (-15, 0)), qbez((-25, -13), (-14, -5), (-3, -9)), circle(6, -20, 8.5, 1.9),
           qbez((12, -13), (22, -9), (17, 0)), qbez((-13, -6), (-6, -1), (2, -6))],
    fills=[poly_close(qbez((-25, -13), (-14, -5), (-3, -9)), qbez((12, -13), (22, -9), (17, 0)), [(-15, 0)], qbez((-15, 0), (-22, -3), (-25, -13))), circle(6, -20, 8.5, 0, 1)],
    bill=[(13.4, -21.3), (17.4, -21.6), (20.4, -20.4), (21.8, -18.6), (20.6, -16.8), (17.2, -16.3), (13.6, -16.9)],
    hole=(21.0, -18.6, .95, 1.4),
    eyes=[(9, -22)]))
# three-quarter, turned towards you (still heading right)
POSES.append(dict(
    lines=[qbez((-20, -11), (-18, -3), (-12, 0)), qbez((-20, -11), (-12, -6), (-5, -9)), circle(3, -20, 8.5, 1.9),
           qbez((9, -13), (17, -7), (12, 0)), qbez((-12, -5), (-6, -1), (-1, -5))],
    fills=[poly_close(qbez((-20, -11), (-12, -6), (-5, -9)), qbez((9, -13), (17, -7), (12, 0)), [(-12, 0)], qbez((-12, 0), (-18, -3), (-20, -11))), circle(3, -20, 8.5, 0, 1)],
    bill=[(6.4, -18.7), (10.4, -19.2), (13.3, -17.4), (13.1, -14.7), (10.4, -13.3), (6.8, -14.2)],
    hole=(11.4, -16.0, 1.45, 1.6),
    eyes=[(0, -22), (6.5, -22.5)]))
# straight at you: a low round body under a round head, and the bill puckered into a round "o" pointing at you
POSES.append(dict(
    lines=[qbez((-21, 0), (-23, -8), (-9, -10)), qbez((21, 0), (23, -8), (9, -10)), circle(0, -22, 9.5, 1.9)],
    fills=[poly_close(qbez((-21, 0), (-23, -8), (-9, -10)), qbez((9, -10), (23, -8), (21, 0))), circle(0, -22, 9.5, 0, 1)],
    bill=oval(0, -14.5, 4.4, 4.0), hole=(0, -14.3, 1.6, 1.8),
    eyes=[(-4, -23.5), (4, -23.5)]))
# three-quarter, turned away (still heading right): its tail to you, the head going away, the tip of the bill showing
POSES.append(dict(
    lines=[qbez((-17, -12), (-14, -4), (-9, 0)), qbez((-17, -12), (-10, -8.5), (-3, -10)), circle(5, -21, 8.5, 1.9),
           qbez((11, -12), (19, -6), (14, 0)), qbez((-6, -6), (0, -2), (6, -6))],
    fills=[poly_close(qbez((-17, -12), (-10, -8.5), (-3, -10)), qbez((11, -12), (19, -6), (14, 0)), [(-9, 0)], qbez((-9, 0), (-14, -4), (-17, -12))), circle(5, -21, 8.5, 0, 1)],
    bill=[(12.6, -22.4), (15.6, -22.2), (17.3, -20.4), (15.6, -18.9), (12.8, -19.3)],
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
        strokes = [pencil(place(st), rng) for st in pose['lines']]
        strokes += [pencil([(CX + x, CY + y) for x, y in st], rng, w=2.6, amp=.12, lift=.32) for st in RIPPLES]
        fills = ''.join(f'<path d="{fill_shape(place(fp))}" fill="#fff"/>' for fp in pose['fills'])
        bill = ''
        if pose.get('bill'):
            bill = f'<path d="{fill_shape(place(pose["bill"]), rng, .12)}" fill="{BILL_ORANGE}"/>'
            if pose.get('hole'):
                hx, hy, rx, ry = pose['hole']; bill += f'<path d="{fill_shape(place(oval(hx, hy, rx, ry, 0, 14)), rng, .05)}" fill="{INK}"/>'
        eyes = ''
        for ex, ey in place(pose['eyes']):
            eyes += f'<path d="{fill_shape(oval(ex, ey, 1.75, 1.95, rng.uniform(-.3, .3), 14), rng, .04)}" fill="{INK}"/>'
            eyes += f'<circle cx="{ex - .55:.2f}" cy="{ey - .7:.2f}" r=".5" fill="#fff"/>'
        cells.append(f'<g transform="translate({f * CW} {pi * CH})">{fills}<path d="{" ".join(strokes)}" fill="url(#g)"/>{bill}{eyes}</g>')
NP = len(POSES)
open(os.path.join(IMG, 'rubber-duck.svg'), 'w').write(
    f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {CW * FRAMES} {CH * NP}" width="{CW * FRAMES}" height="{CH * NP}">'
    '<defs><linearGradient id="g" gradientUnits="objectBoundingBox" x1="0" y1="0" x2="1" y2="0">'
    '<stop offset="0" stop-color="#B0145E"/><stop offset=".5" stop-color="#A8400A"/><stop offset="1" stop-color="#0B6A8C"/></linearGradient></defs>'
    f'{"".join(cells)}</svg>\n')

# ── the tune ── (owner's request: the duck whistles)
# Images/duck-notes.svg: hand-drawn music notes drifting out of the duck's bill, 12 drawings per pose stepped six a
# second (a 2-second loop), one row per pose in the duck sheet's order (the swim picks the row for the duck and the
# notes alike, so the tune always leaves the bill). Each cell is 240 x 120 units and the duck's own cell sits in its
# bottom middle (x 60-180, y 60-120), so the notes have room to travel ahead of the bill without crowding: three in the
# air at a time, each carried forward and lifting a little in a gentle wave, swelling as it leaves the bill and
# shrinking away at the end. Same pencil line and gradient as the duck, drawn afresh in every frame.
NCW, NCH, NF, OX, OY = 240, 120, 12, 60, 60
def note_shape(kind):
    """a note in note space (head at the origin, about 11 units tall): (pencil lines, solid heads)"""
    head = lambda cx, cy: oval(cx, cy, 2.7, 1.9, -.42, 9)
    if kind == 0:   # a single eighth note
        return [[(2.3, -.6), (2.2, -11)], qbez((2.2, -11), (7, -8.3), (5.6, -3.8))], [head(0, 0)]
    else:           # two beamed eighth notes
        return [[(2.3, -.6), (2.2, -11)], [(10.3, -2.1), (10.2, -12.5)], [(2.2, -11), (10.2, -12.5)], [(2.2, -8.6), (10.2, -10.1)]], [head(0, 0), head(8, -1.5)]
# where the bill is in each pose (duck-cell units, before the cell offset), and how far the notes travel across and up
BILLS = [((88, 81 - 60), 52, 13),   # side on: straight ahead from the bill
         ((76, 85 - 60), 44, 14),   # three-quarter towards you
         ((66, 87 - 60), 36, 20),   # facing you: from the "o", up and off to the side, clear of the face
         ((83, 79 - 60), 44, 12),   # three-quarter away
         ((66, 70 - 60), 32, 12)]   # back to you: from beyond the head
ncells = []
for row, (BILL, DX, DY) in enumerate(BILLS):
    bx, by = BILL[0] + OX, BILL[1] + OY
    for f in range(NF):
        lines, heads = [], []
        for k in range(3):
            t = ((f / NF) + k / 3) % 1                        # 0 = just left the bill, 1 = gone
            kind = (k + (1 if (f + 4 * k) // NF % 2 else 0)) % 2
            x = bx + 5 + DX * t
            y = by - 3 - DY * t - 3 * math.sin(t * 2 * math.pi + k * 2.1)
            sc = 1.25 * ((.5 + 1.75 * t) if t < .29 else 1.0 - .42 * max(0, t - .7) / .3)
            rot = math.radians(-10 + 18 * math.sin(t * 5 + k))
            tf = lambda pts: [(x + sc * (px * math.cos(rot) - py * math.sin(rot)), y + sc * (px * math.sin(rot) + py * math.cos(rot))) for px, py in pts]
            strokes, hs = note_shape(kind)
            lines += [pencil(tf(st), rng, w=2.3 * min(1.15, sc), amp=.1, step=2, lift=.18, res=2.2) for st in strokes]
            heads += [curve(wobble(tf(h), rng, .05), True) for h in hs]
        ncells.append(f'<g transform="translate({f * NCW} {row * NCH})"><path d="{" ".join(lines + heads)}" fill="url(#g)"/></g>')
NR = len(BILLS)
open(os.path.join(IMG, 'duck-notes.svg'), 'w').write(
    f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {NCW * NF} {NCH * NR}" width="{NCW * NF}" height="{NCH * NR}">'
    '<defs><linearGradient id="g" gradientUnits="objectBoundingBox" x1="0" y1="0" x2="1" y2="0">'
    '<stop offset="0" stop-color="#B0145E"/><stop offset=".5" stop-color="#A8400A"/><stop offset="1" stop-color="#0B6A8C"/></linearGradient></defs>'
    f'{"".join(ncells)}</svg>\n')

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
