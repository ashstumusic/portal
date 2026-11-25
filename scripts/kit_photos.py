#!/usr/bin/env python3
"""The press kit's photos from the 2022 alley shoot, made from the photographer's own unedited files.

(owner, 2026-11-24: "use these. some new photos some replacements for old photos (with the original undedited
versions)".) The originals are kept on this computer in 'Unpublished assets/Press kit originals/' and never touched:

  IMG_2703 (guitar by the door)       -> Guitar in Alley (Wide): the whole frame, 2301 x 1536 (it was a colour-pushed
                                         1602px crop of it that cut off the guitar case)
                                      -> Headshot-3: a square round the head, guitar and hands, 860px of real picture
                                         (it was a 650px square enlarged to 1000)
  ashton2022-1 (8) (alley at sunset)  -> not in the kit: it is the home photo, and only that (owner, 2026-11-24: "this should
                                         replace the hero, not be added to the footer photos"): scripts/hero_photo.py
  ashton2022-1 (1)~2 (alley portrait) -> Alley Portrait: new, the whole frame (square, 1537 x 1537)

Each also gets the page's own copy (Images/embedded, 481px square, WebP) for the kit's photo tiles and the About wall.
Nothing is drawn on the pictures. Rerunning reproduces the same files.

  python3 scripts/kit_photos.py && python3 build-fast.py && python3 scripts/prerender.py
"""
import os
from PIL import Image, ImageOps

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SRC = os.path.join(ROOT, 'Unpublished assets', 'Press kit originals')
KIT = os.path.join(ROOT, 'Images', 'press-kit')
EMBED = os.path.join(ROOT, 'Images', 'embedded')

DOOR = 'IMG_2703 (guitar by the door).jpg'
PORTRAIT = 'ashton2022-1 (1)~2 (alley portrait).jpg'

# (kit file, original, crop box in the original or None for the whole frame, page copy, square box for the page copy or None)
PHOTOS = [
    ('Ash Stu - Guitar in Alley (Wide).png', DOOR, None, 'epk-ash-stu-alley.webp', (660, 0, 2196, 1536)),
    ('Ash Stu - Headshot-3.png', DOOR, (539, 355, 1399, 1215), 'epk-ash-stu-guitar-door.webp', None),
    ('Ash Stu - Alley Portrait.png', PORTRAIT, (0, 0, 1537, 1537), 'epk-ash-stu-alley-portrait.webp', None),   # (trimmed to an exact square: the file is 1538 x 1537)
]

for name, src, box, thumb, tbox in PHOTOS:
    im = ImageOps.exif_transpose(Image.open(os.path.join(SRC, src))).convert('RGB')
    if box: im = im.crop(box)
    im.save(os.path.join(KIT, name), optimize=True)   # (PNG, as the rest of the kit; no camera details carried over)
    t = im.crop(tbox) if tbox else im
    if t.width != t.height:   # (a square from the middle)
        s = min(t.size); t = t.crop(((t.width - s) // 2, (t.height - s) // 2, (t.width - s) // 2 + s, (t.height - s) // 2 + s))
    t = t.resize((481, 481), Image.LANCZOS)
    t.save(os.path.join(EMBED, thumb), 'WEBP', quality=86, method=6)
    print(name, im.size, '->', thumb)
