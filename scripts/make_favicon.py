"""Make the favicon: the toolbar's songbird mark, filling the icon edge to edge.

The bird is drawn by the page's own drawing code (the "Toolbar songbird" script in
index-src.html), so the icon is exactly the same mark, standing still, cropped to
its shape, and filled with the four colours of the name's gradient (gold, pink,
orange, sky blue) running from tail to beak. An icon cannot animate, so the
gradient is still. It has a thin near-black edge, and a dark eye and wing line, so
it is clearly visible on light browser tabs as well as dark ones.

Writes favicon.svg (vector: sharp at any size), favicon.png (1024px, also used as
the Apple touch icon) and favicon.webp (1024px). Needs playwright (Chrome) and pillow.
"""
import io, os, re
from playwright.sync_api import sync_playwright
from PIL import Image
ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..')
PX = 1024                                 # size of the raster copies
src = open(os.path.join(ROOT, 'index-src.html'), encoding='utf-8').read()
a = src.index("var seed=1;function rnd()"); b = src.index("function wrap(walk,idle)")
code = src[a:b]
JS = "(code)=>{const both=new Function(code+';var a0=bird({});seed=8101;var s0=sketch({});return [a0,s0];')();const art=both[0];" \
     "const NS='http://www.w3.org/2000/svg';const svg=document.createElementNS(NS,'svg');svg.setAttribute('viewBox','-100 -100 500 500');svg.style.cssText='position:fixed;left:0;top:0;width:500px;height:500px;color:#15171c';" \
     "svg.innerHTML='<g>'+art+'</g>';document.body.appendChild(svg);" \
     "const bb=svg.firstChild.getBBox();svg.remove();return {art:art,sk:both[1],x:bb.x,y:bb.y,w:bb.width,h:bb.height};}"
OUTLINE, EDGE = '#15171c', 7.0
# The top layer is the toolbar's own pencil drawing (sketch() in the page), with the same pencil filter the toolbar uses.
PENCIL = ('<filter id="fav-pencil" x="-10%" y="-10%" width="120%" height="120%" color-interpolation-filters="sRGB"><feTurbulence type="fractalNoise" baseFrequency=".06" numOctaves="2" seed="7" result="n"/>'
          '<feDisplacementMap in="SourceGraphic" in2="n" scale="3.4" xChannelSelector="R" yChannelSelector="G" result="d"/><feTurbulence type="fractalNoise" baseFrequency=".9" numOctaves="1" seed="3" result="g"/>'
          '<feColorMatrix in="g" type="matrix" values="0 0 0 0 0  0 0 0 0 0  0 0 0 0 0  0 0 0 -3.2 2.55" result="a"/><feComposite in="d" in2="a" operator="in"/></filter>')
def outline(art):
    """A near-black copy of the bird, drawn underneath and a little fatter, so a dark edge shows all round it.
    The pastel gradient alone is under 3:1 against a light browser tab; the edge is about 18:1. The copy is solid
    (no cut-outs), so the eye and the wing line show dark through the gradient layer on top."""
    a = re.sub(r'<mask.*?</mask>', '', art)
    a = re.sub(r' mask="[^"]*"', '', a)
    a = a.replace('fill="currentColor" stroke="none"', 'fill="%s" stroke="%s" stroke-width="%s" stroke-linejoin="round"' % (OUTLINE, OUTLINE, EDGE * 2))
    a = re.sub(r'stroke="currentColor" stroke-width="([0-9.]+)"', lambda m: 'stroke="%s" stroke-width="%s"' % (OUTLINE, float(m.group(1)) + EDGE * 2), a)
    return a
with sync_playwright() as p:
    br = p.chromium.launch(channel="chrome"); pg = br.new_page(viewport={"width": 600, "height": 600})
    pg.set_content("<!doctype html><html><body style='margin:0;background:transparent'></body></html>")
    r = pg.evaluate(JS, code)
    def render(vx, vy, side):
        svg = ('<svg xmlns="http://www.w3.org/2000/svg" viewBox="%.2f %.2f %.2f %.2f">'
               '<defs><linearGradient id="fav-grad" gradientUnits="userSpaceOnUse" x1="%.1f" y1="%.1f" x2="%.1f" y2="%.1f">'
               '<stop offset="0" stop-color="#F7C549"/><stop offset=".36" stop-color="#FF8AC8"/><stop offset=".66" stop-color="#FFA36B"/><stop offset="1" stop-color="#8FE6FF"/>'
               '</linearGradient>' + PENCIL.replace('%', '%%') + '</defs><g>%s</g><g fill="none" stroke-linecap="round" stroke-linejoin="round" filter="url(#fav-pencil)">%s</g></svg>') % (vx, vy, side, side, r["x"], r["y"] + r["h"] * .35, r["x"] + r["w"], r["y"] + r["h"] * .65, outline(r["art"]), r["sk"].replace("currentColor", "url(#fav-grad)"))
        pg.set_viewport_size({"width": PX, "height": PX})
        pg.set_content("<!doctype html><html><body style='margin:0;background:transparent'>" + svg.replace("<svg ", "<svg width='%d' height='%d' style='display:block' " % (PX, PX)) + "</body></html>")
        return svg, pg.screenshot(omit_background=True, clip={"x": 0, "y": 0, "width": PX, "height": PX})
    # first pass with room to spare, then crop the sheet to exactly where the ink (line included) reaches,
    # so the drawing touches the icon's edges on its longer side
    side = max(r["w"], r["h"]) + 40; vx = r["x"] - 20 - (side - 40 - r["w"]) / 2; vy = r["y"] - 20 - (side - 40 - r["h"]) / 2
    svg, png = render(vx, vy, side)
    bb = Image.open(io.BytesIO(png)).convert("RGBA").split()[3].point(lambda v: 255 if v > 24 else 0).getbbox(); u = side / PX
    x0, y0, x1, y1 = vx + bb[0] * u, vy + bb[1] * u, vx + bb[2] * u, vy + bb[3] * u
    side = max(x1 - x0, y1 - y0); vx = x0 - (side - (x1 - x0)) / 2; vy = y0 - (side - (y1 - y0)) / 2
    svg, png = render(vx, vy, side); br.close()
    open(os.path.join(ROOT, 'favicon.svg'), 'w', encoding='utf-8').write(svg)
im = Image.open(io.BytesIO(png)).convert("RGBA")
im.save(os.path.join(ROOT, 'favicon.png'), optimize=True)
im.save(os.path.join(ROOT, 'favicon.webp'), 'WEBP', quality=95, method=6)
bb = im.getbbox(); print('wrote favicon.svg (%d bytes), favicon.png, favicon.webp; ink reaches', bb, 'of 512' % ()) if False else print('wrote favicon.svg (%d bytes), favicon.png, favicon.webp (%dpx); ink box %s' % (len(svg), PX, bb))
