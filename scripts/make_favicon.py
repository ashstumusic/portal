"""Make the favicon: the toolbar's songbird mark, filling the icon edge to edge.

The bird is drawn by the page's own drawing code (the "Toolbar songbird" script in
index-src.html), so the icon is exactly the same mark, standing still, cropped to
its shape. One colour: near-black, and in the SVG it turns off-white on dark tabs.

Writes favicon.svg (vector: sharp at any size), favicon.png (512px, also used as
the Apple touch icon) and favicon.webp (512px). Needs playwright (Chrome) and pillow.
"""
import io, os, re
from playwright.sync_api import sync_playwright
from PIL import Image
ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..')
src = open(os.path.join(ROOT, 'index-src.html'), encoding='utf-8').read()
a = src.index("var seed=1;function rnd()"); b = src.index("function wrap(walk,idle)")
code = src[a:b]
JS = "(code)=>{const art=new Function(code+';return bird({});')();" \
     "const NS='http://www.w3.org/2000/svg';const svg=document.createElementNS(NS,'svg');svg.setAttribute('viewBox','-100 -100 500 500');svg.style.cssText='position:fixed;left:0;top:0;width:500px;height:500px;color:#15171c';" \
     "svg.innerHTML='<g>'+art+'</g>';document.body.appendChild(svg);" \
     "const bb=svg.firstChild.getBBox();svg.remove();return {art:art,x:bb.x,y:bb.y,w:bb.width,h:bb.height};}"
with sync_playwright() as p:
    br = p.chromium.launch(channel="chrome"); pg = br.new_page(viewport={"width": 600, "height": 600})
    pg.set_content("<!doctype html><html><body style='margin:0;background:transparent'></body></html>")
    r = pg.evaluate(JS, code)
    def render(vx, vy, side):
        svg = ('<svg xmlns="http://www.w3.org/2000/svg" viewBox="%.2f %.2f %.2f %.2f">'
               '<style>svg{color:#15171c}@media (prefers-color-scheme: dark){svg{color:#F2F4F6}}</style><g>%s</g></svg>') % (vx, vy, side, side, r["art"])
        pg.set_viewport_size({"width": 512, "height": 512})
        pg.set_content("<!doctype html><html><body style='margin:0;background:transparent'>" + svg.replace("<svg ", "<svg width='512' height='512' style='display:block' ") + "</body></html>")
        return svg, pg.screenshot(omit_background=True, clip={"x": 0, "y": 0, "width": 512, "height": 512})
    # first pass with room to spare, then crop the sheet to exactly where the ink (line included) reaches,
    # so the drawing touches the icon's edges on its longer side
    side = max(r["w"], r["h"]) + 40; vx = r["x"] - 20 - (side - 40 - r["w"]) / 2; vy = r["y"] - 20 - (side - 40 - r["h"]) / 2
    svg, png = render(vx, vy, side)
    bb = Image.open(io.BytesIO(png)).convert("RGBA").split()[3].point(lambda v: 255 if v > 24 else 0).getbbox(); u = side / 512
    x0, y0, x1, y1 = vx + bb[0] * u, vy + bb[1] * u, vx + bb[2] * u, vy + bb[3] * u
    side = max(x1 - x0, y1 - y0); vx = x0 - (side - (x1 - x0)) / 2; vy = y0 - (side - (y1 - y0)) / 2
    svg, png = render(vx, vy, side); br.close()
    open(os.path.join(ROOT, 'favicon.svg'), 'w', encoding='utf-8').write(svg)
im = Image.open(io.BytesIO(png)).convert("RGBA")
im.save(os.path.join(ROOT, 'favicon.png'), optimize=True)
im.save(os.path.join(ROOT, 'favicon.webp'), 'WEBP', quality=95, method=6)
bb = im.getbbox(); print('wrote favicon.svg (%d bytes), favicon.png, favicon.webp; ink reaches', bb, 'of 512' % ()) if False else print('wrote favicon.svg (%d bytes), favicon.png, favicon.webp; ink box %s of 512x512' % (len(svg), bb))
