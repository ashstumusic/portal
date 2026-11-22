#!/usr/bin/env python3
"""Photo credits written into the press kit's photo files themselves (owner's request: "hardcode credit onto emma's
image files so she has credit on the download version too").

For each credited photo, from its clean original:
  - a small "Photo: <name>" label in the bottom right corner, drawn on the picture in the site's own lettering
    (Bricolage Grotesque) on a soft dark pill, like the credit bubble on the page - so the credit survives being
    saved, copied, converted to JPEG or WebP, or posted;
  - the credit in the file's details too (PNG text: Author, Copyright, Description), for apps that read them.

The clean originals are never touched: Live at the Keyboard (Wide) comes from Images/Piano Batch/2.png, and
Headshot-2 is cut from that clean picture (the same square as before) before the label goes on, so the wide shot's
label never appears in the crop. Rerunning reproduces the same files.

  python3 scripts/credit_photos.py
"""
import os
from PIL import Image, ImageDraw, ImageFont, PngImagePlugin

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
KIT = os.path.join(ROOT, 'Images', 'press-kit')
FONT = os.path.join(ROOT, 'Fonts', 'bricolage', 'BricolageGrotesque-VF.ttf')
WIDE_SRC = os.path.join(ROOT, 'Images', 'Piano Batch', '2.png')
HEADSHOT_2_BOX = (345, 33, 774, 462)   # Headshot-2's square inside the wide shot (found by matching; see git history)

PHOTOS = [   # (file in the kit, the clean picture it is made from, photographer)
    ('Ash Stu - Live at the Keyboard (Wide).png', lambda: Image.open(WIDE_SRC).convert('RGB'), 'Emma Evans'),
    ('Ash Stu - Headshot-2.png', lambda: Image.open(WIDE_SRC).convert('RGB').crop(HEADSHOT_2_BOX), 'Emma Evans'),
]

def label(im, who):
    """'Photo: <who>' in a soft dark pill, bottom right, sized to the picture (readable, never shouting)."""
    w, h = im.size
    size = max(12, round(min(w, h) * .026))
    font = ImageFont.truetype(FONT, size)
    font.set_variation_by_axes([12, 600, 100])   # small-size drawing, weight 600, normal width (as the page's bubble)
    text = 'Photo: ' + who
    l, t, r, b = font.getbbox(text)
    px, py, m = round(size * .65), round(size * .38), round(min(w, h) * .022)
    bw, bh = (r - l) + 2 * px, (b - t) + 2 * py
    x1, y1 = w - m, h - m
    x0, y0 = x1 - bw, y1 - bh
    layer = Image.new('RGBA', im.size, (0, 0, 0, 0))
    d = ImageDraw.Draw(layer)
    d.rounded_rectangle((x0, y0, x1, y1), radius=bh / 2, fill=(0, 0, 0, 120))
    d.text((x0 + px - l, y0 + py - t), text, font=font, fill=(255, 255, 255, 236))
    return Image.alpha_composite(im.convert('RGBA'), layer).convert('RGB')

for name, source, who in PHOTOS:
    im = label(source(), who)
    info = PngImagePlugin.PngInfo()
    info.add_text('Author', who)
    info.add_text('Copyright', 'Photo by ' + who + '. Used with permission by Ash Stu.')
    info.add_text('Description', 'Ash Stu. Photo: ' + who + '.')
    im.save(os.path.join(KIT, name), pnginfo=info, optimize=True)
    print('credited', name, im.size)
