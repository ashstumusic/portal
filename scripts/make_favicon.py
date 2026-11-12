"""Make the site icon: the "A" of the Ash Stu wordmark (the same lettering, Boiled Pasta, drawn as a vector outline so no
font is needed), in the name's colours (pink, orange, gold, sky blue) with the wordmark's red offset shadow, on a
near-black rounded tile. The tile fills the whole icon, so it is as large as an icon can be and reads on light and dark
browser tabs alike. Shown small (a browser tab) the shadow is dropped and the letter is a little larger.

Writes
  favicon.svg            vector, for browsers that take SVG icons
  favicon.ico            16, 32 and 48px, each drawn at its own size (not shrunk from a big one)
  favicon.png / .webp    512px / 192px, rounded tile on transparent
  apple-touch-icon.png   180px, square and opaque (iOS rounds the corners itself)
  icon-192.png, icon-512.png   square and opaque with the letter inside the safe zone ("maskable"), for site.webmanifest
Needs fonttools, playwright (Chrome) and pillow.
"""
import io, os
from fontTools.ttLib import TTFont
from fontTools.pens.svgPathPen import SVGPathPen
from fontTools.pens.boundsPen import BoundsPen
from playwright.sync_api import sync_playwright
from PIL import Image
ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..')
TILE, SHADOW = '#10161d', '#DF2B2C'
STOPS = (('0', '#FF8AC8'), ('.36', '#FFA36B'), ('.68', '#F7C549'), ('1', '#8FE6FF'))
font = TTFont(os.path.join(ROOT, 'Fonts', 'xperimental', 'Boiled-Pasta.ttf')); gs = font.getGlyphSet(); name = font.getBestCmap()[ord('A')]
pen = SVGPathPen(gs); gs[name].draw(pen); D = pen.getCommands()
bp = BoundsPen(gs); gs[name].draw(bp); GX0, GY0, GX1, GY1 = bp.bounds

def letter(size, fill, dx=0, dy=0, extra=''):
    """The A, `size` units tall-or-wide (whichever is larger), centred on the 1000-unit square, moved by dx, dy."""
    k = size / max(GX1 - GX0, GY1 - GY0)
    tx = 500 - (GX0 + GX1) / 2 * k + dx; ty = 500 + (GY0 + GY1) / 2 * k + dy
    return '<path d="%s" transform="translate(%.1f %.1f) scale(%.4f -%.4f)" fill="%s"%s/>' % (D, tx, ty, k, k, fill, extra)

def icon(size=690, shadow=True, radius=225, responsive=False):
    """size: the letter's size in the 1000-unit square. radius: tile corner (0 = square, full bleed)."""
    h = size / 2
    grad = ('<linearGradient id="g" gradientUnits="userSpaceOnUse" x1="%.0f" y1="%.0f" x2="%.0f" y2="%.0f">' % (500 - h * .8, 500 + h, 500 + h * .8, 500 - h)
            + ''.join('<stop offset="%s" stop-color="%s"/>' % s for s in STOPS) + '</linearGradient>')
    style = '<style>@media (max-width:48px){.s{display:none}.a{transform:scale(1.09);transform-origin:500px 500px}}</style>' if responsive else ''
    off = size * .045
    body = '<rect width="1000" height="1000" rx="%d" fill="%s"/>' % (radius, TILE)
    if shadow: body += letter(size, SHADOW, off - off * .45, off - off * .45, ' class="s"')
    body += '<g class="a">' + letter(size, 'url(#g)', -off * .45 if shadow else 0, -off * .45 if shadow else 0) + '</g>'
    return '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 1000 1000"><defs>' + grad + style + '</defs>' + body + '</svg>'

with sync_playwright() as p:
    br = p.chromium.launch(channel="chrome")
    def shot(svg, px):
        pg = br.new_page(viewport={"width": px, "height": px})
        pg.set_content("<!doctype html><html><body style='margin:0;background:transparent'>" + svg.replace("<svg ", "<svg width='%d' height='%d' style='display:block' " % (px, px)) + "</body></html>")
        im = Image.open(io.BytesIO(pg.screenshot(omit_background=True, clip={"x": 0, "y": 0, "width": px, "height": px}))).convert("RGBA"); pg.close(); return im
    out = lambda n: os.path.join(ROOT, n)
    open(out('favicon.svg'), 'w', encoding='utf-8').write(icon(responsive=True))
    small = [shot(icon(size=750, shadow=False), s) for s in (16, 32, 48)]          # tab sizes: no shadow, larger letter
    small[-1].save(out('favicon.ico'), format='ICO', append_images=small[:-1], sizes=[(48, 48), (32, 32), (16, 16)])
    shot(icon(), 512).save(out('favicon.png'), optimize=True)
    shot(icon(), 192).save(out('favicon.webp'), 'WEBP', lossless=True, method=6)
    shot(icon(radius=0), 180).convert('RGB').save(out('apple-touch-icon.png'), optimize=True)
    for s in (192, 512): shot(icon(size=560, radius=0), s).convert('RGB').save(out('icon-%d.png' % s), optimize=True)   # letter within the middle 80%: safe under any mask shape
    br.close()
for n in ('favicon.svg', 'favicon.ico', 'favicon.png', 'favicon.webp', 'apple-touch-icon.png', 'icon-192.png', 'icon-512.png'):
    print('%-22s %6d bytes' % (n, os.path.getsize(out(n))))
