"""Cut vintage engraved stars out of Johann Bayer's Uranometria (1603).

Makes Images/cutouts/stars.webp, the sheet of paper-cutout stars the
homepage scatters across its space-black background (shared/psyche.js).

  1. fetch     15 Uranometria plates from Wikimedia Commons (public domain
               / CC0; see Images/cutouts/CREDITS.md)
  2. detect    stars by scale-space blob detection (the rays of an engraved
               star merge into a round blob at low resolution; shading and
               lines don't)
  3. cut       each star: ink thresholded to stark black, only the ink
               joined to the star's centre (no hatching or figure lines),
               printed onto aged paper taken from the plates' blank areas,
               cut out along a rough hand-scissored outline with a scorched
               edge. Rejects: too few rays, off-centre (two stars / a
               letter), stray specks, hatching in the outer reach.
  4. pack      the hand-reviewed picks (PICKS) into a 10-column sheet of
               128px cells: 12 colours, crisp alpha, lossless WebP.

Needs numpy, scipy and pillow (python3 -m venv .venv && .venv/bin/pip
install numpy scipy pillow), then: .venv/bin/python scripts/make_star_cutouts.py WORKDIR
Downloads go to WORKDIR/stars-raw. Rerunning reproduces the sheet exactly
(fixed random seeds); PICKS index the candidates in their sorted order.
"""
import sys, os, math, json, glob, random, time, urllib.request, urllib.parse
from collections import Counter

import numpy as np
from PIL import Image, ImageDraw, ImageFilter
from scipy import ndimage as ndi

SOURCES = [
 [
  "b00.jpg",
  "File:Aquila Uranometria.jpg"
 ],
 [
  "b01.jpg",
  "File:Bootes Uranometria.jpg"
 ],
 [
  "b02.jpg",
  "File:Canis Minor Uranometria.jpg"
 ],
 [
  "b03.jpg",
  "File:Corona Borealis Uranometria.jpg"
 ],
 [
  "b04.jpg",
  "File:Cygnus Uranometria.jpg"
 ],
 [
  "b06.jpg",
  "File:Equuleus Uranometria.jpg"
 ],
 [
  "b07.jpg",
  "File:Hydra Uranometria.jpg"
 ],
 [
  "b08.jpg",
  "File:Libra Uranometria.jpg"
 ],
 [
  "b09.jpg",
  "File:Lyra Uranometria.jpg"
 ],
 [
  "b10.jpg",
  "File:ORION Uranometria orion.jpg"
 ],
 [
  "b11.jpg",
  "File:Ophiuchus Uranometria.jpg"
 ],
 [
  "b12.jpg",
  "File:Pegasus Uranometria.jpg"
 ],
 [
  "b13.jpg",
  "File:Scorpius Uranometria.jpg"
 ],
 [
  "b14.jpg",
  "File:Triangulum Uranometria.jpg"
 ],
 [
  "b15.jpg",
  "File:Uranometria Canis Major (1603).jpg"
 ]
]

def fetch(D):
    os.makedirs(D, exist_ok=True)
    UA = {'User-Agent': 'AshStuSite/1.0 (site build script)'}
    q = urllib.parse.urlencode({'action': 'query', 'titles': '|'.join(t for _, t in SOURCES), 'prop': 'imageinfo', 'iiprop': 'url', 'iiurlwidth': 2000, 'format': 'json'})
    pages = json.load(urllib.request.urlopen(urllib.request.Request('https://commons.wikimedia.org/w/api.php?' + q, headers=UA), timeout=30))['query']['pages']
    urls = {p['title']: p['imageinfo'][0].get('thumburl') or p['imageinfo'][0]['url'] for p in pages.values() if 'imageinfo' in p}
    for fn, title in SOURCES:
        if os.path.exists(os.path.join(D, fn)): continue
        open(os.path.join(D, fn), 'wb').write(urllib.request.urlopen(urllib.request.Request(urls[title], headers=UA), timeout=90).read()); time.sleep(4)

PICKS = [0, 3, 4, 5, 9, 12, 13, 17, 18, 19, 20, 21, 22, 23, 26, 28, 30, 31, 33, 34, 36, 37, 38, 39, 42, 44, 50, 51, 52, 53, 56, 58, 59, 60, 61, 62, 63, 65, 66, 70, 74, 75, 78, 79, 81, 82, 83, 87, 88, 93, 94, 95, 96, 98, 102, 106, 113, 114, 117, 120, 122, 125, 130, 131, 133, 143, 144, 145, 147, 156, 162, 165, 166, 167, 177, 178, 188, 189, 194, 195]


SIGMAS = [3, 4, 5, 6.5, 8, 10, 13]
def detect(path, debug=None, work=1280, thresh=0.16):
    full = Image.open(path).convert('L')
    k = full.width / work
    g = np.asarray(full.resize((work, round(full.height / k)), Image.LANCZOS), dtype=np.float32)
    bg = ndi.uniform_filter(ndi.maximum_filter(g, 41), 81)
    dk = np.clip(1 - g / np.maximum(bg, 1), 0, 1)                       # ink darkness, 0..1
    stack = np.stack([-(s * s) * ndi.gaussian_laplace(dk, s) for s in SIGMAS])   # scale-normalised LoG
    peaks = (stack == ndi.maximum_filter(stack, size=(3, 11, 11))) & (stack > thresh)
    H, W = dk.shape; m = int(W * 0.035)
    cands = []
    for si, y, x in zip(*np.nonzero(peaks)):
        if x < m or y < m or x > W - m or y > H - m: continue
        s = SIGMAS[si]
        # isotropy: Hessian of the smoothed darkness at the peak
        sm = ndi.gaussian_filter(dk[max(0, y - 3 * int(s)):y + 3 * int(s) + 1, max(0, x - 3 * int(s)):x + 3 * int(s) + 1], s)
        cy, cx = min(y, 3 * int(s)), min(x, 3 * int(s))
        try:
            dyy = sm[cy + 1, cx] - 2 * sm[cy, cx] + sm[cy - 1, cx]; dxx = sm[cy, cx + 1] - 2 * sm[cy, cx] + sm[cy, cx - 1]
            dxy = (sm[cy + 1, cx + 1] - sm[cy + 1, cx - 1] - sm[cy - 1, cx + 1] + sm[cy - 1, cx - 1]) / 4
        except IndexError: continue
        tr, det = dxx + dyy, dxx * dyy - dxy * dxy
        if det <= 0 or tr * tr / det > 5: continue                     # elongated: a line or a letter stroke
        cands.append((float(stack[si, y, x]), x, y, s))
    # strongest first, drop overlaps
    cands.sort(reverse=True); found = []
    for resp, x, y, s in cands:
        r = s * 1.6
        if any(math.hypot(x - f[1], y - f[2]) < (r + f[3]) * 0.9 for f in found): continue
        found.append((resp, x, y, r))
    out = [{'cx': x * k, 'cy': y * k, 'r': r * k, 'resp': round(resp, 3)} for resp, x, y, r in found]
    if debug:
        d = full.convert('RGB'); dr = ImageDraw.Draw(d)
        for f in out: dr.ellipse((f['cx'] - f['r'], f['cy'] - f['r'], f['cx'] + f['r'], f['cy'] + f['r']), outline=(255, 0, 255), width=8)
        d.resize((1200, round(1200 * d.height / d.width))).save(debug)
    return out, full


S = sys.argv[1] if len(sys.argv) > 1 else 'star-work'
D = S + '/stars-raw'; OUT = S + '/cut'; os.makedirs(OUT, exist_ok=True)
fetch(D)
import numpy as np
from PIL import Image, ImageDraw, ImageFilter
from scipy import ndimage as ndi


rng = random.Random(7)

# ── aged paper: blank patches from the plates' margins ──
papers = []
def harvest_paper(full):
    g = np.asarray(full.convert('L'), dtype=np.float32); rgb = np.asarray(full.convert('RGB'))
    H, W = g.shape
    for (y0, y1, x0, x1) in [(int(H*.94), H, 0, W), (0, int(H*.06), 0, W), (0, H, 0, int(W*.05)), (0, H, int(W*.95), W), (int(H*.1), int(H*.9), int(W*.1), int(W*.9))]:
        for _ in range(12):
            P = 140
            if y1 - y0 < P or x1 - x0 < P: continue
            y = rng.randint(y0, y1 - P); x = rng.randint(x0, x1 - P)
            pg = g[y:y+P, x:x+P]
            if np.percentile(pg, 1) > pg.mean() * 0.62 and pg.mean() > 140:   # no real ink (faint show-through is fine: it reads as old paper)
                papers.append(rgb[y:y+P, x:x+P].copy())

from collections import Counter
REJ = Counter()
cands = []
for path in sorted(glob.glob(D + '/b*.jpg')):
    found, full = detect(path)
    harvest_paper(full)
    g = np.asarray(full, dtype=np.float32)
    for f in found:
        cx, cy, r = f['cx'], f['cy'], f['r']
        R = int(r * 2.2)
        y0, y1, x0, x1 = int(cy - R), int(cy + R), int(cx - R), int(cx + R)
        if y0 < 0 or x0 < 0 or y1 > g.shape[0] or x1 > g.shape[1]: continue
        win = g[y0:y1, x0:x1]
        paper = np.percentile(win, 92)
        ink = win < paper * 0.58                                     # stark: ink or not
        yy, xx = np.mgrid[0:2 * R, 0:2 * R]; dist = np.hypot(xx - R, yy - R)
        joined = ndi.binary_dilation(ink, iterations=2)
        lab, _ = ndi.label(joined)
        c = lab[R - 2:R + 3, R - 2:R + 3]; c = c[c > 0]
        if not len(c): continue
        comp = (lab == np.bincount(c).argmax()) & ink                # the star: ink joined to the centre
        if (comp & (dist > R * 0.95)).sum() > 3: continue           # runs into neighbouring engraving
        ys, xs = np.nonzero(comp)
        if len(xs) < 80: continue
        rad = np.hypot(xs - R, ys - R); rs = np.percentile(rad, 97)
        if rs < r * 0.6: continue
        # rays: around a ring at 70% of the star's reach, ink and paper alternate
        ring = [comp[int(R + math.sin(t) * rs * .7), int(R + math.cos(t) * rs * .7)] for t in np.linspace(0, 2 * math.pi, 120, endpoint=False)]
        rays = sum(1 for i in range(120) if ring[i] and not ring[i - 1])
        if rays < 6: REJ['rays'] += 1; continue
        fill = comp[dist < rs].mean()
        if fill < 0.22 or fill > 0.8: REJ['fill'] += 1; continue
        # off-centre mass: two stars stuck together, or a star plus a letter
        if math.hypot(xs.mean() - R, ys.mean() - R) > rs * 0.14: REJ['offcentre'] += 1; continue
        # stray specks (letters, dots) outside the star's own disc
        lab2, n2 = ndi.label(ndi.binary_dilation(comp, iterations=2))
        if n2 > 1 and (np.bincount(lab2.ravel())[1:].max() < lab2.astype(bool).sum() * 0.93): REJ['specks'] += 1; continue
        # hatching: long horizontal ink runs away from the centre row
        hatch = 0
        for yy_ in range(comp.shape[0]):
            if abs(yy_ - R) < rs * 0.5: continue   # the star's own body has long runs; only look at its outer reach
            row = comp[yy_]; run = best = 0
            for v in row: run = run + 1 if v else 0; best = max(best, run)
            if best > rs * 0.55: hatch += 1
        if hatch > 2: REJ['hatch'] += 1; continue
        cands.append(dict(src=os.path.basename(path), cx=cx, cy=cy, R=R, rs=rs, rays=rays, fill=float(fill), comp=comp))
print('candidates', len(cands), 'papers', len(papers), dict(REJ))

# ── cut each star out ──
CELL = 144
def scissor(mask, R):
    """Rough hand-scissored outline around the star: sample the silhouette's
    reach at many angles, keep ~30 straight snips, jitter them."""
    sil = ndi.binary_fill_holes(ndi.binary_dilation(mask, iterations=max(4, int(R * 0.09))))
    n = rng.randint(26, 36); pts = []
    for i in range(n):
        t = i / n * 2 * math.pi + rng.uniform(-.05, .05)
        rr = 0
        for d in np.arange(0, R, 0.5):
            x, y = int(R + math.cos(t) * d), int(R + math.sin(t) * d)
            if 0 <= x < 2 * R and 0 <= y < 2 * R and sil[y, x]: rr = d
        rr = max(rr, R * 0.25) + rng.uniform(-0.5, 1.8) * R * 0.03
        pts.append((R + math.cos(t) * rr, R + math.sin(t) * rr))
    return pts

cands.sort(key=lambda c: (-min(c['rays'], 16), -c['fill'], -c['rs']))
manifest = []
for i, c in enumerate(cands):
    R, comp = c['R'], c['comp']
    poly = scissor(comp, R)
    # parchment, sized to the window, a little warmer
    p = Image.fromarray(rng.choice(papers)).resize((2 * R, 2 * R), Image.LANCZOS).rotate(rng.choice([0, 90, 180, 270]))
    p = np.asarray(p, dtype=np.float32) * np.array([1.02, 0.97, 0.86])
    star = ndi.binary_dilation(comp, iterations=0) if False else comp
    rgb = np.clip(p, 0, 255) * (1 - star[..., None]) + np.array([18, 14, 12]) * star[..., None]   # stark black ink on aged paper
    cut = Image.new('L', (2 * R, 2 * R), 0); ImageDraw.Draw(cut).polygon(poly, fill=255)
    out = Image.fromarray(rgb.astype(np.uint8)).convert('RGBA'); out.putalpha(cut)
    # a scorched paper edge: darken just inside the cut
    edge = np.asarray(cut.filter(ImageFilter.MinFilter(5)), dtype=np.float32) / 255
    a = np.asarray(out, dtype=np.float32); a[..., :3] *= (0.78 + 0.22 * edge[..., None]); out = Image.fromarray(a.astype(np.uint8))
    out = out.crop(out.getbbox())
    s = (CELL - 4) / max(out.size); out = out.resize((max(1, round(out.width * s)), max(1, round(out.height * s))), Image.LANCZOS)
    fn = f'{i:03d}.png'; out.save(os.path.join(OUT, fn))
    manifest.append(dict(file=fn, src=c['src'], rays=c['rays'], size=round(c['rs']), fill=round(c['fill'], 2)))
json.dump(manifest, open(OUT + '/manifest.json', 'w'), indent=1)


# ── pack the reviewed picks ──
from PIL import ImageFilter
SITE = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'Images', 'cutouts', 'stars.webp')
CELL2, COLS = 128, 10
sheet = Image.new('RGBA', (COLS * CELL2, ((len(PICKS) + COLS - 1) // COLS) * CELL2), (0, 0, 0, 0))
for i, k in enumerate(PICKS):
    im = Image.open(f"{OUT}/{manifest[k]['file']}").convert('RGBA')
    s = (CELL2 - 4) / max(im.size); im = im.resize((round(im.width * s), round(im.height * s)), Image.LANCZOS)
    sheet.alpha_composite(im, ((i % COLS) * CELL2 + (CELL2 - im.width) // 2, (i // COLS) * CELL2 + (CELL2 - im.height) // 2))
a = np.asarray(sheet).astype(np.float32); ink = a[..., :3].mean(-1) < 70
sm = np.asarray(sheet.filter(ImageFilter.GaussianBlur(1.6))).astype(np.float32)
a[~ink, :3] = sm[~ink, :3]; a[ink, :3] = [18, 14, 12]                       # smooth paper grain, stark ink
smooth = Image.fromarray(a.astype(np.uint8)); alpha = np.asarray(smooth)[..., 3]
rgb = smooth.convert('RGB').quantize(colors=12, method=Image.Quantize.MEDIANCUT, dither=Image.Dither.NONE).convert('RGB')
out = np.dstack([np.asarray(rgb), np.where(alpha >= 128, 255, 0).astype(np.uint8)]); out[out[..., 3] == 0, :3] = 0
Image.fromarray(out, 'RGBA').save(SITE, 'WEBP', lossless=True, method=6)
print('wrote', SITE, 'mags', [manifest[k]['size'] for k in PICKS])
