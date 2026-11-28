"""Draw the flourishes above and below the Woody Guthrie quote: Images/chalk-flourish.webp.

(owner, 2026-11-25: "put a little handdrawn simple western flourish above and below the quote ... in the style of the other
animations, high resolution, flip book, well thought out, each stroke with intention, using elements of art, looking
handdrawn. like the stars or the duck or the section logos".)

The design, after the owner's reference (the scrollwork over the Stables Cafe sign, 2026-11-25): wrought-iron scrollwork. From a
ball at the centre one main bar runs out to each side, dips and rises into a big scroll; three smaller scrolls sprout from it,
each winding inward and closing on a ball, as a blacksmith finishes a scroll; the one under the quote is the same figure turned
over, with three drops hanging from its centre. The bars are nearly even in weight, thinning a little into each spiral. The two
halves are drawn separately, so they mirror each other the way a hand mirrors - nearly, never exactly.

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

CW, CH, FRAMES, SS = 1800, 480, 3, 3   # each cell 1800 x 480 (3.75:1), drawn at three times that: the flourish is at most 520px wide, so even on 3x screens (1560px) every frame is shown smaller than it was drawn (owner, 2026-11-27: "ensure each frame of each animation is in the highest clarity and resolution"; it was 1500 x 400, a touch short of that)
W, H = CW * SS, CH * SS
OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'Images', 'chalk-flourish.webp')


def cubic(p0, p1, p2, p3, n):
    t = np.linspace(0, 1, n)[:, None]
    p0, p1, p2, p3 = (np.array(p, float) for p in (p0, p1, p2, p3))
    return (1 - t) ** 3 * p0 + 3 * (1 - t) ** 2 * t * p1 + 3 * (1 - t) * t * t * p2 + t ** 3 * p3


def spiral(c, r0, a0, d, turns, n):
    """A scroll's spiral: from the point at angle a0 on a circle of radius r0 round c, winding inward (d=+1 clockwise on
    screen, -1 anticlockwise) for `turns` of a full turn, each turn tighter."""
    th = np.linspace(0, turns * 2 * math.pi, n)
    r = r0 * (1 - .68 * th / th[-1])
    a = a0 + d * th
    return np.stack([c[0] + r * np.cos(a), c[1] + r * np.sin(a)], 1)


def into(start, tan, sp, k1, k2, n=90):
    """A smooth lead from `start` (leaving along `tan`) into the spiral `sp` (arriving along its own direction)."""
    t = sp[1] - sp[0]; t /= np.linalg.norm(t)
    s0 = np.array(start, float); tan = np.array(tan, float); tan /= np.linalg.norm(tan)
    return cubic(s0, s0 + tan * k1, sp[0] - t * k2, sp[0], n)


def half(sign):
    """The right half (sign=+1) or the left (-1): unit coordinates, x from the centre outward, y down.
    After the scrollwork over the Stables Cafe sign (owner's reference, 2026-11-25): a main bar leaves the centre, arches up
    and comes down into a big scroll at its outer end; two smaller scrolls peel off it - one under the arch, curling back
    toward the centre, and one rising off the far side of the arch, curling outward - each closing on a ball. Every scroll
    leaves its bar along the bar's own line, as forged iron does, never crossing it."""
    out = []
    # the main bar: up from the centre in an arch, down and out into the big end scroll
    A = cubic((0, .07), (.16, -.2), (.42, -.27), (.62, -.12), 120)
    end_sp = spiral((1.2, -.03), .165, math.pi / 2, -1, .92, 160)          # entered at its foot, travelling outward, winding up and back in
    dA = A[-1] - A[-2]; dA /= np.linalg.norm(dA)
    B = cubic(A[-1], A[-1] + dA * .2, end_sp[0] - np.array([.22, 0]), end_sp[0], 120)
    main = np.vstack([A, B[1:], end_sp[1:]])
    out += [(main, 'iron+ball', 1.0)]
    # under the arch: peels off near the top and curls down and back toward the centre
    k = 30; d = A[k + 1] - A[k - 1]
    sp1 = spiral((.36, .08), .1, 0, 1, .9, 120)                           # entered at its right side going down, winding back in
    out += [(np.vstack([into(A[k], d, sp1, .1, .12), sp1[1:]]), 'iron+ball', .82)]
    # from the top of the arch: splits off the bar, running on outward as the bar turns down, and rolls up into a scroll
    # that curls back toward the centre
    k = int(np.argmin(A[:, 1])); d = A[k + 1] - A[k - 1]
    sp2 = spiral((.9, -.32), .1, math.pi / 2, -1, .92, 120)                 # entered at its foot going outward, winding up and back in
    out += [(np.vstack([into(A[k + 6], d, sp2, .16, .16), sp2[1:]]), 'iron+ball', .82)]
    return [([(sign * x, y) for x, y in np.asarray(pts)], kind, w) for pts, kind, w in out]


def centre(drops):
    """The centre, inside the V where the two bars meet: a ball over the quote; under it, three drops hanging there instead,
    the middle one longest, as on the reference."""
    if not drops:
        return [([(0, -.1)] * 4, 'ball', 1.1)]
    out = [(cubic((0, .04), (0, -.06), (0, -.18), (0, -.3), 40), 'drop', 1.05)]
    for sg in (1, -1):
        out.append((cubic((sg * .022, -.02), (sg * .035, -.07), (sg * .055, -.13), (sg * .085, -.19), 40), 'drop', .72))   # (inside the V, clear of its arms)
    return out


def smooth(rng, n, sd, sigma):
    """Smooth noise along a stroke: n points, about `sd` units from the line, wandering over about `sigma` points."""
    v = ndi.gaussian_filter1d(rng.normal(0, 1, (n, 2)), sigma, axis=0)
    return v / max(1e-9, v.std()) * sd


def draw(flip, rng):   # flip: the one under the quote (turned over, with the drops)
    ink = np.zeros((H, W), np.float32); dust = np.zeros((H, W), np.float32)
    scale = min(W * .47 / 1.4, H * .47 / .47); cx, cy = W / 2, H / 2   # (as large as the cell allows)
    yy, xx = np.mgrid[0:H, 0:W]
    # (owner, 2026-11-27: "the jittering on the top and bottom flourish is jacked". Each frame used to draw its own
    # random-walk wobble, so the long bars drifted 5-8px between frames and the whole figure tilted and jumped. Now the
    # hand's wobble is the same in all three frames (seeded by the stroke, not the frame); a frame only adds a shiver of
    # under a pixel on screen, and fresh chalk grain - the way the stars boil.)
    g_rot = rng.uniform(-.0015, .0015); g_dy = rng.uniform(-.0015, .0015)
    strokes = half(1) + half(-1) + centre(flip)
    for si, (pts, kind, weight) in enumerate(strokes):
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
        hand = np.random.default_rng(7700 + 50 * flip + si)   # the same in every frame
        walk = smooth(hand, n, .006, 60 * k_w) + smooth(hand, n, .0018, 8 * k_w) + smooth(rng, n, .0025, 25 * k_w)
        width = scale * .017 * weight * hand.uniform(.95, 1.05) * rng.uniform(.985, 1.015)
        for i in range(n):
            x, y = pts[i] + walk[i]; y += g_dy
            x, y = x * math.cos(g_rot) - y * math.sin(g_rot), x * math.sin(g_rot) + y * math.cos(g_rot)
            px, py = cx + x * scale, cy + y * scale
            t = i / max(1, n - 1)
            if kind.startswith('iron'): p = min(1, .45 + t * 9) * (.82 + .22 * math.sin(math.pi * min(1, t / .55))) * (1 - .32 * max(0, (t - .55) / .45))   # forged bar: full along, thinning a little into the spiral
            elif kind == 'drop': p = .15 + 1.75 * t ** 1.5                                        # a drop: from a point to its full belly
            else:                p = 1.5                                                           # a ball: one round press of the chalk
            r = max(.8, width * p * (1 + rng.uniform(-.05, .05)))
            if kind == 'iron+ball' and i == n - 1: r = width * 1.55   # the ball the scroll closes on
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
Image.fromarray(sheet, 'RGBA').save(OUT, 'WEBP', quality=92, alpha_quality=100, method=6)   # (the picture is all in the alpha - the stencil - and alpha_quality 100 keeps it lossless)
print('wrote', OUT, os.path.getsize(OUT), 'bytes', sheet.shape[1], 'x', sheet.shape[0])
