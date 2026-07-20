#!/usr/bin/env python3
"""Build the deployed single-file index.html from index-src.html.

Edit index-src.html + styles.css, then run: python3 build-fast.py"""
import base64, io, json, re, sys, os
from fontTools.subset import Subsetter, Options, load_font, save_font
from PIL import Image

ROOT = "/home/oem/Documents/Websites/Ash Music 2"
os.chdir(ROOT)

# ---------- fonts: subset -> woff2 -> base64 ----------
UNICODES = "U+0020-007E,U+00B7,U+00E9,U+2013-2014,U+2018-201F,U+2026,U+2022,U+2605,U+2715"
def font_b64(path, exact_text=None):
    opts = Options()
    opts.flavor = "woff2"
    opts.desubroutinize = True
    opts.hinting = False
    opts.drop_tables += ["FFTM", "meta"]
    font = load_font(path, opts)
    if exact_text is not None:
        # This font is only ever used to render one fixed, hardcoded string
        # (not arbitrary user content) - subsetting to exactly the
        # characters that string uses, instead of the full site-wide
        # charset, cuts a heavy decorative typeface down drastically.
        # Computed from the literal text so it can't drift out of sync -
        # if that text ever changes, this recomputes automatically.
        codes = sorted(set(ord(c) for c in exact_text))
    else:
        codes = []
        for r in UNICODES.replace("U+", "").split(","):
            if "-" in r:
                a, b = r.split("-")
                codes.extend(range(int(a, 16), int(b, 16) + 1))
            else:
                codes.append(int(r, 16))
    ss = Subsetter(options=opts)
    ss.populate(unicodes=codes)
    ss.subset(font)
    buf = io.BytesIO()
    save_font(font, buf, opts)
    data = buf.getvalue()
    print(f"  font {path}: {os.path.getsize(path)//1024}KB -> {len(data)//1024}KB woff2")
    return "data:font/woff2;base64," + base64.b64encode(data).decode()

# "A figment of my own imagination." (index-src.html .bio-tagline) is the
# only text j.d.ttf is ever used for - see the narrow-subset note above.
FIGMENT_TEXT = "A figment of my own imagination."

FONT_FILES = {
    "Fonts/Header.ttf": None, "Fonts/Header-Italic.ttf": None,
    "Fonts/j.d.ttf": None, "Fonts/Handmade.otf": None,
    "Fonts/xperimental/Boiled-Pasta.ttf": None, "Fonts/Body.ttf": None,
}
print("Subsetting fonts...")
for f in FONT_FILES:
    FONT_FILES[f] = font_b64(f, exact_text=FIGMENT_TEXT if f == "Fonts/j.d.ttf" else None)

# ---------- images: decode -> 90% scale -> webp -> base64 ----------
IMG_CACHE = {}
def img_b64(path, quality=80):
    if path in IMG_CACHE:
        return IMG_CACHE[path]
    im = Image.open(path)
    w, h = im.size
    nw, nh = max(1, round(w * 0.90)), max(1, round(h * 0.90))
    im = im.resize((nw, nh), Image.LANCZOS)
    buf = io.BytesIO()
    if im.mode in ("RGBA", "LA", "P"):
        im = im.convert("RGBA")
        im.save(buf, "WEBP", quality=quality, method=6)
    else:
        im.convert("RGB").save(buf, "WEBP", quality=quality, method=6)
    data = buf.getvalue()
    uri = "data:image/webp;base64," + base64.b64encode(data).decode()
    IMG_CACHE[path] = uri
    print(f"  img {path}: {w}x{h} -> {nw}x{nh}, {os.path.getsize(path)//1024}KB -> {len(data)//1024}KB")
    return uri

# ---------- CSS ----------
css = open("styles.css").read()
for f, uri in FONT_FILES.items():
    css = css.replace(f"url('{f}') format('truetype')", f"url({uri}) format('woff2')")
    css = css.replace(f"url('{f}') format('opentype')", f"url({uri}) format('woff2')")
assert "Fonts/" not in css, "unreplaced font url"

def minify_css(s):
    # protect data URIs
    stash = []
    def keep(m):
        stash.append(m.group(0)); return f"\x00{len(stash)-1}\x00"
    s = re.sub(r"url\(data:[^)]+\)", keep, s)
    s = re.sub(r"/\*.*?\*/", "", s, flags=re.S)
    s = re.sub(r"\s+", " ", s)
    s = re.sub(r"\s*([{};:,>~])\s*", r"\1", s)
    s = s.replace(";}", "}")
    s = re.sub(r"\x00(\d+)\x00", lambda m: stash[int(m.group(1))], s)
    return s.strip()

css_min = minify_css(css)

# ---------- HTML ----------
html = open("index-src.html").read()

# drop stylesheet link + preloads, inject inline style
html = re.sub(r'<link rel="stylesheet"[^>]*>', "", html)
html = re.sub(r'<link rel="preload"[^>]*>\n?', "", html)
html = html.replace("</head>", f"<style>{css_min}</style></head>")

# favicon -> inline webp
fav = img_b64("favicon.png", quality=75)
html = re.sub(r'<link rel="icon"[^>]*/>', f'<link rel="icon" type="image/webp" href="{fav}"/>', html)
html = re.sub(r'<link rel="apple-touch-icon"[^>]*/>\n?', "", html)

# minify JSON-LD
def min_jsonld(m):
    return '<script type="application/ld+json">' + json.dumps(json.loads(m.group(1)), separators=(",", ":")) + "</script>"
html = re.sub(r'<script type="application/ld\+json">(.*?)</script>', min_jsonld, html, flags=re.S)

# inline all local raster imgs referenced in src="..." - but only in real
# HTML markup, never inside <script> blocks. Dynamic card renderers
# (renderReleaseCard, renderFeatured, etc.) hold icon/art paths as literal
# strings in their JS template code, e.g. '<img src="Icons/Apple_Music.webp"
# ...'; blindly inlining those turns every small icon into a duplicated
# base64 blob baked directly into the page's JS payload, once per render
# function that happens to reference it, instead of one small file the
# browser fetches once and reuses from cache across every card.
def repl_src(m):
    path = m.group(1)
    if path.startswith("data:") or path.startswith("http"):
        return m.group(0)
    # These small icons appear repeatedly across the page (nav, hero,
    # platform buttons, fullscreen player...) - one cached file the
    # browser fetches once beats several duplicated inline copies.
    if path.startswith("Icons/") or path == "Images/Icon.webp":
        return m.group(0)
    # Below-the-fold photos (press kit strip, about section) stay external:
    # inlining them as base64 bloats the critical HTML payload ~95KB for
    # images the browser wouldn't need until scroll - loading="lazy" only
    # helps if they're actually separate fetches. They also skip this
    # script's 90%-downscale re-encode, so they ship at full original
    # quality. Only above-the-fold LCP images (hero, featured) stay inline.
    if "/epk-" in path or path.startswith("Images/Profile-"):
        return m.group(0)
    q = 82 if "hero-" in path or "featured-" in path else 78
    return f'src="{img_b64(path, quality=q)}"'
print("Inlining images...")
_script_re = re.compile(r'(<script\b[^>]*>.*?</script>)', re.S)
_parts = _script_re.split(html)
for _i in range(0, len(_parts), 2):  # even indices = markup outside <script>
    _parts[_i] = re.sub(r'src="([^"]+\.(?:webp|png|jpg))"', repl_src, _parts[_i])
html = "".join(_parts)

# light JS minify: strip full-line comments, trailing line comments are risky -> only strip leading whitespace + blank lines
def minify_js_block(m):
    body = m.group(1)
    lines = []
    for ln in body.split("\n"):
        t = ln.strip()
        if not t or t.startswith("//"):
            continue
        lines.append(t)
    return "<script>" + "\n".join(lines) + "</script>"
html = re.sub(r"<script>(.*?)</script>", minify_js_block, html, flags=re.S)

# strip HTML comments + indentation, collapse blank lines
html = re.sub(r"<!--(?!\[).*?-->", "", html, flags=re.S)
html = "\n".join(l.strip() for l in html.split("\n") if l.strip())

open("index.html", "w").write(html)
print(f"\nWrote index.html: {len(html)//1024}KB")
