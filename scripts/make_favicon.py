"""Make the favicon: a hollow chalk star (the site's own motif - the page is scattered with them): just its outline, drawn
in a heavy chalk line in the four colours of the name's gradient (gold, pink, orange, sky blue), dusty and wavering like
chalk on a board, over a near-black edge so it shows on light browser tabs as well as dark ones. It is tilted and slightly uneven, like the stars on the page, and fills the icon edge to edge.

Writes favicon.svg (vector: sharp at any size), favicon.png (1024px, also the Apple touch icon) and favicon.webp.
Needs playwright (Chrome) and pillow, only to make the raster copies.
"""
import io, math, os
from playwright.sync_api import sync_playwright
from PIL import Image
ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..')
PX, EDGE, OUTLINE = 1024, 26, '#15171c'
TILT = -11                                                    # degrees: not upright
OUTER = [1.00, .94, 1.03, .97, 1.01]                          # each point a little different: drawn by hand, not stamped
INNER = [.47, .44, .46, .43, .45]
def points(R, cx, cy):
    pts = []
    for i in range(10):
        a = math.radians(-90 + TILT + i * 36); r = R * (OUTER[i // 2] if i % 2 == 0 else INNER[i // 2])
        pts.append((cx + r * math.cos(a), cy + r * math.sin(a)))
    return pts
STROKE = 118                                                  # the chalk line: heavy, so the hollow star still reads at 16px
CHALK = ('<filter id="chalk" x="-10%" y="-10%" width="120%" height="120%" color-interpolation-filters="sRGB">'
         '<feTurbulence type="fractalNoise" baseFrequency=".012" numOctaves="2" seed="5" result="w"/><feDisplacementMap in="SourceGraphic" in2="w" scale="20" xChannelSelector="R" yChannelSelector="G" result="d"/>'
         '<feTurbulence type="fractalNoise" baseFrequency=".2" numOctaves="2" seed="11" result="g"/><feColorMatrix in="g" type="matrix" values="0 0 0 0 0  0 0 0 0 0  0 0 0 0 0  0 0 0 -6 4.25" result="a"/>'
         '<feComposite in="d" in2="a" operator="in"/></filter>'                                   # wavering edge + dusty gaps: chalk on a board
         '<filter id="waver" x="-10%" y="-10%" width="120%" height="120%"><feTurbulence type="fractalNoise" baseFrequency=".012" numOctaves="2" seed="5" result="w"/>'
         '<feDisplacementMap in="SourceGraphic" in2="w" scale="20" xChannelSelector="R" yChannelSelector="G"/></filter>')   # the same waver, no gaps (for the dark edge under the chalk)
def svg_for(R, cx, cy):
    d = 'M' + 'L'.join('%.1f %.1f' % p for p in points(R, cx, cy)) + 'Z'
    return ('<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 1000 1000"><defs><linearGradient id="g" gradientUnits="userSpaceOnUse" x1="120" y1="820" x2="880" y2="180">'
            '<stop offset="0" stop-color="#8FE6FF"/><stop offset=".34" stop-color="#FFA36B"/><stop offset=".64" stop-color="#FF8AC8"/><stop offset="1" stop-color="#F7C549"/></linearGradient>' + CHALK.replace('%', '%%') + '<style>@media (max-width:72px){.c{filter:url(#waver)}}</style></defs>'   # shown small (a browser tab), the chalk dust would only be dark specks: there the line is solid, still wavering
            '<path d="%s" fill="none" stroke="%s" stroke-width="%d" stroke-linejoin="round" filter="url(#waver)"/>'
            '<path d="%s" fill="none" stroke="url(#g)" stroke-width="%d" stroke-linejoin="round" filter="url(#chalk)" class="c"/></svg>') % (d, OUTLINE, STROKE + EDGE * 2, d, STROKE)
with sync_playwright() as p:
    br = p.chromium.launch(channel="chrome"); pg = br.new_page(viewport={"width": PX, "height": PX})
    def shot(svg):
        pg.set_content("<!doctype html><html><body style='margin:0;background:transparent'>" + svg.replace("<svg ", "<svg width='%d' height='%d' style='display:block' " % (PX, PX)) + "</body></html>")
        return Image.open(io.BytesIO(pg.screenshot(omit_background=True, clip={"x": 0, "y": 0, "width": PX, "height": PX}))).convert("RGBA")
    # first pass small and centred; then scale and shift so the ink (edge included) touches the icon's sides
    R, cx, cy = 300.0, 500.0, 500.0
    bb = shot(svg_for(R, cx, cy)).split()[3].point(lambda v: 255 if v > 24 else 0).getbbox(); u = 1000 / PX
    x0, y0, x1, y1 = [v * u for v in bb]; k = 1000 / max(x1 - x0, y1 - y0)
    R2 = R * k * .995                                             # the edge's width does not scale with the star, so leave a hair's room
    cx2 = 500 + (cx - (x0 + x1) / 2) * k; cy2 = 500 + (cy - (y0 + y1) / 2) * k
    svg = svg_for(R2, cx2, cy2); im = shot(svg)
    for _ in range(3):                                            # settle it exactly inside the square
        bb = im.split()[3].point(lambda v: 255 if v > 24 else 0).getbbox(); x0, y0, x1, y1 = [v * u for v in bb]
        k = 1000 / max(x1 - x0, y1 - y0); R2 *= min(1, k) if k < 1 else 1 + (k - 1) * .9
        cx2 += 500 - (x0 + x1) / 2; cy2 += 500 - (y0 + y1) / 2; svg = svg_for(R2, cx2, cy2); im = shot(svg)
    br.close()
open(os.path.join(ROOT, 'favicon.svg'), 'w', encoding='utf-8').write(svg)
im.save(os.path.join(ROOT, 'favicon.png'), optimize=True); im.save(os.path.join(ROOT, 'favicon.webp'), 'WEBP', quality=95, method=6)
print('wrote favicon.svg (%d bytes), favicon.png, favicon.webp (%dpx); ink box %s' % (len(svg), PX, im.getbbox()))
