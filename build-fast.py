#!/usr/bin/env python3
"""Build the deployed index.html + cached assets from index-src.html.

Edit index-src.html + styles.css, then run: python3 build-fast.py && python3 scripts/prerender.py"""
import base64, io, json, re, sys, os
from fontTools.subset import Subsetter, Options, load_font, save_font
from PIL import Image

ROOT = "/home/oem/Documents/Websites/Ash Music"
os.chdir(ROOT)

# ---------- fonts: subset -> woff2 -> external file ----------
SUBSET_DIR = "Fonts/subsetted"
os.makedirs(SUBSET_DIR, exist_ok=True)

UNICODES = "U+0020-007E,U+00B7,U+00E9,U+2013-2014,U+2018-201F,U+2026,U+2022,U+2605,U+2715"
FIGMENT_TEXT = "A figment of my own imagination."

FONT_FILES = [
    "Fonts/Header.ttf", "Fonts/Header-Italic.ttf",
    "Fonts/j.d.ttf", "Fonts/Handmade.otf",
    "Fonts/xperimental/Boiled-Pasta.ttf", "Fonts/Body.ttf",
]
FONT_RELPATHS = {}

print("Subsetting fonts...")
for f in FONT_FILES:
    opts = Options()
    opts.flavor = "woff2"
    opts.desubroutinize = True
    opts.hinting = False
    opts.drop_tables += ["FFTM", "meta"]
    font = load_font(f, opts)
    exact = FIGMENT_TEXT if f == "Fonts/j.d.ttf" else None
    if exact is not None:
        codes = sorted(set(ord(c) for c in exact))
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
    woff2_data = buf.getvalue()
    stem = os.path.splitext(os.path.basename(f))[0]
    out_name = stem + ".woff2"
    out_path = os.path.join(SUBSET_DIR, out_name)
    with open(out_path, "wb") as fh:
        fh.write(woff2_data)
    print(f"  font {f}: {os.path.getsize(f)//1024}KB -> {len(woff2_data)//1024}KB woff2 -> {out_path}")
    FONT_RELPATHS[f] = f"{SUBSET_DIR}/{out_name}"

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
for src_path, rel_path in FONT_RELPATHS.items():
    css = css.replace(f"url('{src_path}') format('truetype')", f"url('{rel_path}') format('woff2')")
    css = css.replace(f"url('{src_path}') format('opentype')", f"url('{rel_path}') format('woff2')")

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

# Write external CSS file (audit tools penalize "zero stylesheets" and
# inline CSS bloats the HTML payload). The browser caches the file across
# repeat visits, and the single network request is offset by the smaller
# HTML parse time.
css_hash = __import__('hashlib').sha256(css_min.encode()).hexdigest()[:8]
css_out = f"styles.{css_hash}.min.css"
with open(css_out, "w") as fh:
    fh.write(css_min)
print(f"Wrote {css_out}: {len(css_min)//1024}KB")

# ---------- HTML ----------
html = open("index-src.html").read()

# drop stylesheet link, inject external stylesheet + font preloads
html = re.sub(r'<link rel="stylesheet"[^>]*>', "", html)
html = re.sub(r'<link rel="preload"[^>]*>\n?', "", html)
# Only preload the fonts used above the fold (hero name: Logo, fallback:
# Display). The rest (italic, handwriting, grit, body) are used below the
# fold and load lazily on first use via font-display: swap - preloading
# them all just burns ~90KB of rural-cell-tower bandwidth on a race the
# first paint never waits on.
_PRELOAD_FONTS = {"Fonts/Header.ttf", "Fonts/xperimental/Boiled-Pasta.ttf"}
preloads = "\n".join(
    f'<link rel="preload" href="{rel}" as="font" type="font/woff2" crossorigin>'
    for src, rel in FONT_RELPATHS.items() if src in _PRELOAD_FONTS
) + '\n<link rel="preload" as="image" href="Images/embedded/hero-ash-stu-guitar.webp" fetchpriority="high">'
html = html.replace("</head>", f'{preloads}\n<link rel="stylesheet" href="{css_out}"/>\n</head>')

# favicon -> external webp file (10KB vs ~80KB inlined base64 in the
# critical HTML payload; one small cached fetch wins for a page-load win)
html = re.sub(r'<link rel="icon"[^>]*/>', '<link rel="icon" type="image/webp" href="favicon.webp"/>', html)
html = re.sub(r'<link rel="apple-touch-icon"[^>]*/>\n?', '<link rel="apple-touch-icon" href="favicon.webp"/>', html)

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
    # The hero is preloaded in <head> with fetchpriority="high", so shipping
    # it as an external file costs no LCP round-trip while keeping the
    # critical HTML payload lean (an inline 60-80KB base64 hero bloats the
    # first byte more than the extra request saves).
    if "hero-" in path:
        return m.group(0)
    # Below-the-fold photos (press kit strip, about section) stay external:
    # inlining them as base64 bloats the critical HTML payload ~95KB for
    # images the browser wouldn't need until scroll - loading="lazy" only
    # helps if they're actually separate fetches. They also skip this
    # script's 90%-downscale re-encode, so they ship at full original
    # quality. Only above-the-fold LCP images (hero, featured) stay inline.
    if "/epk-" in path or path.startswith("Images/Profile-"):
        return m.group(0)
    q = 65 if "hero-" in path else 78
    return f'src="{img_b64(path, quality=q)}"'
print("Inlining images...")
_script_re = re.compile(r'(<script\b[^>]*>.*?</script>)', re.S)
_parts = _script_re.split(html)
for _i in range(0, len(_parts), 2):  # even indices = markup outside <script>
    _parts[_i] = re.sub(r'src="([^"]+\.(?:webp|png|jpg))"', repl_src, _parts[_i])
html = "".join(_parts)

# Externalize the main script: one hashed, cached file instead of an
# inline render-blocking block that re-downloads every visit. `defer` runs
# it after the prerendered DOM is ready; the inline data-all JSON (injected
# later by prerender.py) and any content JSON lives in the page already.
def minify_js_body(body):
    # light JS minify: strip full-line comments + blank lines; trailing
    # line comments are risky, so leave them in place
    lines = []
    for ln in body.split("\n"):
        t = ln.strip()
        if not t or t.startswith("//"):
            continue
        lines.append(t)
    return "\n".join(lines)

_m = re.search(r"<script>(.*?)</script>", html, flags=re.S)
if _m:
    js_min = minify_js_body(_m.group(1))
    js_hash = __import__('hashlib').sha256(js_min.encode()).hexdigest()[:8]
    js_out = f"main.{js_hash}.js"
    with open(js_out, "w") as fh:
        fh.write(js_min)
    html = html.replace(_m.group(0), f'<script src="{js_out}" defer></script>')
    print(f"Wrote {js_out}: {len(js_min)//1024}KB")

# strip HTML comments + indentation, collapse blank lines
html = re.sub(r"<!--(?!\[).*?-->", "", html, flags=re.S)
html = "\n".join(l.strip() for l in html.split("\n") if l.strip())

open("index.html", "w").write(html)
print(f"\nWrote index.html: {len(html)//1024}KB")
