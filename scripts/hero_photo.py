#!/usr/bin/env python3
"""The home photo, made from the photographer's own unedited file (owner, 2026-11-24: "this should replace the hero, not
be added to the footer photos. this should only be in the header hero").

The original is kept on this computer in 'Unpublished assets/Press kit originals/ashton2022-1 (8) (alley at sunset).jpg'
(2301 x 1536) and never touched. It is the same framing as the edited copy the owner marked (Downloads/Guitar.png): the
marked rectangle falls at 8.7% -> 99.0% across and 5.8% -> 96.7% down, inside the numbers the page's rules keep whole
("Home photo: the required area is never cut" in shared/system.css), so those rules stand as they are.

Writes the page's two sizes, 1400 and 2000 pixels wide (WebP).
  python3 scripts/hero_photo.py && python3 build-fast.py && python3 scripts/prerender.py
"""
import os
from PIL import Image, ImageOps
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SRC = os.path.join(ROOT, 'Unpublished assets', 'Press kit originals', 'ashton2022-1 (8) (alley at sunset).jpg')
im = ImageOps.exif_transpose(Image.open(SRC)).convert('RGB')
for w, name in ((1400, 'hero-ash-stu-guitar.webp'), (2000, 'hero-ash-stu-guitar-2000.webp')):
    h = round(im.height * w / im.width)
    im.resize((w, h), Image.LANCZOS).save(os.path.join(ROOT, 'Images', 'embedded', name), 'WEBP', quality=86, method=6)
    print(name, w, h)
