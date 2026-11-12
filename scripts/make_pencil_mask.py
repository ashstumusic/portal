"""Make Images/pencil-hatch.webp: the pencil shading the name is drawn with.

Real pencil shading is not a row of even bars: it is a great many short, thin strokes laid over one another, all leaning
roughly the same way but none quite parallel, pressed harder in some places than others, with the paper's tooth showing
through as fine grain. This draws exactly that: a couple of thousand fine strokes of varying length, lean, curve and
pressure, built up in layers, then the paper grain. Only the sheet's transparency matters: the stylesheet uses it as a
mask over the gradient lettering ("Ash Stu" in the hero, the toolbar and About). The sheet repeats in both directions
(strokes that run off one edge come back in at the other). Needs numpy, opencv, pillow.
"""
import os, numpy as np, cv2
from PIL import Image
W, H, SS = 540, 270, 3                       # one tile is 3em x 1.5em of lettering
EM = W / 3 * SS
rng = np.random.default_rng(23)
w, h = W * SS, H * SS
acc = np.zeros((h, w), np.float32)
LAYERS, PER = 7, 360
for L in range(LAYERS):
    lay = np.zeros((h, w), np.uint8)
    lean = np.deg2rad(-63 + rng.normal(0, 2.5))            # each pass of the hand leans a touch differently
    for _ in range(PER):
        cx, cy = rng.uniform(0, w), rng.uniform(0, h)
        a = lean + np.deg2rad(rng.normal(0, 4.5))
        ln = EM * rng.uniform(.3, 1.05); bow = EM * rng.normal(0, .018)
        wd = max(1, int(round(EM * rng.uniform(.006, .014))))
        t = np.linspace(-.5, .5, 9)
        xs = cx + np.cos(a) * ln * t - np.sin(a) * bow * (1 - (2 * t) ** 2)
        ys = cy + np.sin(a) * ln * t + np.cos(a) * bow * (1 - (2 * t) ** 2)
        for ox in (-w, 0, w):
            for oy in (-h, 0, h):
                if xs.max() + ox < 0 or xs.min() + ox > w or ys.max() + oy < 0 or ys.min() + oy > h: continue
                pts = np.stack([xs + ox, ys + oy], 1).astype(np.int32).reshape(-1, 1, 2)
                cv2.polylines(lay, [pts], False, 255, wd, cv2.LINE_AA)
    press = rng.uniform(.4, .58)
    acc = 1 - (1 - acc) * (1 - press * cv2.GaussianBlur(lay, (0, 0), .5 * SS).astype(np.float32) / 255)
# heavier where the hand pressed (slow, broad variation), lighter elsewhere
soft = cv2.resize(rng.random((6, 12)).astype(np.float32), (w, h), interpolation=cv2.INTER_CUBIC)
acc = np.clip(acc * (1.06 + .5 * (soft - .5)), 0, 1)
# the paper's tooth: fine grain the graphite skips over
n = cv2.GaussianBlur(rng.random((h, w)).astype(np.float32), (0, 0), .55 * SS)
n = (n - n.mean()) / n.std()
acc *= np.clip(.96 + .24 * n, 0, 1)
a = cv2.resize(acc, (W, H), interpolation=cv2.INTER_AREA)
al = (np.clip(a * 1.12, 0, 1) * 255).astype(np.uint8)
out = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'Images', 'pencil-hatch.webp')
Image.merge('RGBA', [Image.new('L', (W, H), 255)] * 3 + [Image.fromarray(al)]).save(out, 'WEBP', quality=38, alpha_quality=45, method=6, exact=True)
print('wrote', out, os.path.getsize(out), 'bytes; coverage %.0f%%' % (al.mean() / 2.55))
