"""Make Images/pencil-hatch.webp: the pencil shading the name is drawn with.

A sheet of slanted, hand-wobbly pencil strokes laid side by side (as when shading with the side of the lead), with
slivers of bare paper between them and fine grain knocked out. Only its transparency matters: the stylesheet uses it
as a mask over the gradient lettering ("Ash Stu" in the hero, the toolbar and About), so the name looks shaded in
coloured pencil, the same way the toolbar's bird is. The sheet repeats in both directions. Needs numpy, opencv, pillow.
"""
import os, numpy as np, cv2
from PIL import Image
W, H, SS = 640, 320, 2                      # one tile is 4em x 2em of lettering
rng = np.random.default_rng(11)
w, h = W * SS, H * SS
a = np.zeros((h, w), np.uint8)
PER = w // 46                                 # one stroke every ~0.087em
SLANT = 13 * PER / h                          # strokes leave the bottom where another enters the top
PAR = [(rng.normal(0, PER * .05), rng.uniform(0, 6.28), rng.uniform(.5, 1.4) * SS, PER * .87 * rng.uniform(.8, .9)) for _ in range(46)]
for i in range(-20, 46 + 20):
    off, ph, amp, wid = PAR[i % 46]           # the sheet repeats every 46 strokes
    x0 = i * PER + off
    ys = np.arange(-40, h + 41, 16)
    xs = x0 + (h - ys) * SLANT + amp * np.sin(ys / (90 * SS) + ph)
    for k in range(len(ys) - 1):
        t = max(2, int(wid * (1 + .08 * np.sin(ys[k] / (60 * SS) + ph * 2))))
        cv2.line(a, (int(xs[k]), int(ys[k])), (int(xs[k + 1]), int(ys[k + 1])), 255, t, cv2.LINE_AA)
    if rng.random() < .0:                    # now and then the pencil lifts for a moment
        y = int(rng.uniform(0, h)); cv2.line(a, (int(x0 + (h - y) * SLANT - PER), y), (int(x0 + (h - y) * SLANT + PER), y - int(PER * .6)), 0, max(2, PER // 5), cv2.LINE_AA)
a = cv2.GaussianBlur(a, (0, 0), 1.2 * SS).astype(np.float32) / 255
# grain: graphite skipping on the paper's tooth
n = cv2.GaussianBlur(rng.random((h, w)).astype(np.float32), (0, 0), .7 * SS)
n = (n - n.min()) / (n.max() - n.min())
a *= np.clip((n - .2) * 7, .0, 1)
a = cv2.resize(a, (W, H), interpolation=cv2.INTER_AREA)
al = (np.clip(a * 1.05, 0, 1) * 255).astype(np.uint8)
out = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'Images', 'pencil-hatch.webp')
Image.merge('RGBA', [Image.new('L', (W, H), 255)] * 3 + [Image.fromarray(al)]).save(out, 'WEBP', quality=50, method=6, exact=True)
print('wrote', out, os.path.getsize(out), 'bytes; coverage %.0f%%' % (al.mean() / 2.55))
