"""Draw the logo mark: the tilted hand-drawn hollow star (design 6 of the
chalk stars, scripts/make_chalk_stars.py), redrawn large.

Writes Images/logo-mark.webp (512px, white, solid and bold like the name, used as a
CSS mask so it takes the name's fill), favicon.png (192px) and
favicon.webp: the same star solid black (no grain, so it stays crisp small).
Needs numpy, scipy, pillow. Fixed seed.
"""
import os, re
from PIL import Image
import numpy as np
HERE = os.path.dirname(os.path.abspath(__file__)); ROOT = os.path.join(HERE, '..')
src = open(os.path.join(HERE, 'make_chalk_stars.py')).read()
src = src[:src.index('sheet = np.zeros')]
src = re.sub(r'^CELL, FRAMES, SS = .*$', 'CELL, FRAMES, SS = 512, 1, 2', src, flags=re.M)
src = src.replace('width = SS * rng.uniform(3.0, 3.8)', 'width = SS * WIDTH * rng.uniform(3.0, 3.8)')
src = src.replace('a = stroke * np.clip(0.75 + 0.45 * grain + 0.25 * streak, 0, 1)', 'a = stroke * (np.clip(0.75 + 0.45 * grain + 0.25 * streak, 0, 1) if GRAIN else 1)')
src = src.replace('a = np.maximum(a, ndi.gaussian_filter(dust, 1.2) * 2.2)', 'a = np.maximum(a, ndi.gaussian_filter(dust, 1.2) * 2.2) if GRAIN else a')
def render(width, grain):
    g = {'__name__': 'logo', '__file__': os.path.join(HERE, 'make_chalk_stars.py'), 'WIDTH': width, 'GRAIN': grain}
    exec(src, g)
    return g['draw'](g['DESIGNS'][5], np.random.default_rng(1050))
def crop(a, pad=.04):
    ys, xs = np.nonzero(a > 8); n = a.shape[0]; p = int(n * pad)
    side = max(ys.max() - ys.min(), xs.max() - xs.min()) + 2 * p
    cy, cx = (ys.max() + ys.min()) // 2, (xs.max() + xs.min()) // 2
    out = np.zeros((side, side), np.uint8)
    y0, x0 = cy - side // 2, cx - side // 2
    sy0, sx0 = max(0, y0), max(0, x0); sy1, sx1 = min(n, y0 + side), min(n, x0 + side)
    out[sy0 - y0:sy1 - y0, sx0 - x0:sx1 - x0] = a[sy0:sy1, sx0:sx1]
    return out
mark = crop(render(5.0, False))
m = Image.fromarray(mark).resize((512, 512), Image.LANCZOS)
rgba = Image.merge('RGBA', [Image.new('L', m.size, 255)] * 3 + [m])
rgba.save(os.path.join(ROOT, 'Images', 'logo-mark.webp'), 'WEBP', quality=90, alpha_quality=95, method=6)
fav = crop(render(4.2, False), .06)
f = Image.fromarray(fav).resize((192, 192), Image.LANCZOS)
frgba = Image.merge('RGBA', [Image.new('L', f.size, 17)] * 3 + [f])
frgba.save(os.path.join(ROOT, 'favicon.png'), optimize=True)
frgba.save(os.path.join(ROOT, 'favicon.webp'), 'WEBP', quality=92, method=6)
print('wrote logo-mark.webp, favicon.png, favicon.webp')
