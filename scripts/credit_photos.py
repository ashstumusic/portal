#!/usr/bin/env python3
"""Photo credits written into the press kit's photo files themselves (owner's request: "hardcode credit onto emma's
image files so she has credit on the download version too").

For each credited photo, from its clean original: the credit in the file's details only (PNG text: Author,
Copyright, Description). Nothing is drawn on the picture (owner's request: no watermark).

The clean original is never touched: both photos are cut from Emma Evans's own file, 720 x 1280, kept on this
computer in 'Unpublished assets/' (owner, 2026-11-24: "heres the original emma evans image to use. crop as
necessary"). They were made from Images/Piano Batch/2.png before, a square of it enlarged to 1080 with added grain.
Live at the Keyboard (Wide) is that same square at its true size (720 x 720, no enlarging); Headshot-2 is a square
round the face, a little wider than before (380px of real picture rather than 286px enlarged), so it is sharp.
Rerunning reproduces the same files, and the page's copies in Images/embedded.

  python3 scripts/credit_photos.py
"""
import os
from PIL import Image, ImageDraw, ImageFont, PngImagePlugin

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
KIT = os.path.join(ROOT, 'Images', 'press-kit')
FONT = os.path.join(ROOT, 'Fonts', 'bricolage', 'BricolageGrotesque-VF.ttf')
ORIGINAL = os.path.join(ROOT, 'Unpublished assets', 'Emma Evans - Live at the Keyboard (original).jpg')
WIDE_BOX = (0, 167, 720, 887)          # the square the site has always shown (found by matching the old file against the original)
HEADSHOT_2_BOX = (195, 140, 575, 520)  # the face, head and shoulders, with the microphone
EMBED = os.path.join(ROOT, 'Images', 'embedded')

PHOTOS = [   # (file in the kit, the clean picture it is made from, photographer)
    ('Ash Stu - Live at the Keyboard (Wide).png', lambda: Image.open(ORIGINAL).convert('RGB').crop(WIDE_BOX), 'Emma Evans'),
    ('Ash Stu - Headshot-2.png', lambda: Image.open(ORIGINAL).convert('RGB').crop(HEADSHOT_2_BOX), 'Emma Evans'),
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
    im = source()   # (the picture untouched: no label drawn on it)
    info = PngImagePlugin.PngInfo()
    info.add_text('Author', who)
    info.add_text('Copyright', 'Photo by ' + who + '. Used with permission by Ash Stu.')
    info.add_text('Description', 'Ash Stu. Photo: ' + who + '.')
    im.save(os.path.join(KIT, name), pnginfo=info, optimize=True)
    print('credited', name, im.size)

# the page's own copies (the press kit's photo tiles and the photo viewer), from the same crops
for name, size, out in (('Ash Stu - Live at the Keyboard (Wide).png', 481, 'epk-ash-stu-performing.webp'),
                        ('Ash Stu - Headshot-2.png', 429, 'epk-ash-stu-singing.webp')):
    im = Image.open(os.path.join(KIT, name)).convert('RGB')
    if im.width != size: im = im.resize((size, size), Image.LANCZOS)
    im.save(os.path.join(EMBED, out), 'WEBP', quality=86, method=6)
    print('page copy', out, im.size)
