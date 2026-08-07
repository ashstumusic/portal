#!/usr/bin/env python3
"""Build a fully self-contained single-file index.html for ashstu.media.

Inline everything: minified CSS in <head>, minified JS at end of <body>,
subsetted fonts and every raster image as base64 data URIs, favicon as a
data URI. Resulting index.html makes zero network requests for the initial
render (only user-triggered media: audio files, videos, goatcounter).

Run: python3 build-single.py && python3 scripts/prerender.py
"""
import base64
import io
import json
import os
import re
import sys

from PIL import Image

ROOT = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(ROOT, "scripts"))
from buildutil import b64_font, img_b64, minify_css, minify_js_body  # noqa: E402
from fontTools.subset import Options, Subsetter, load_font, save_font  # noqa: E402

os.chdir(ROOT)

UNICODES = "U+0020-007E,U+00B7,U+00E9,U+2013-2014,U+2018-201F,U+2026,U+2022,U+2605,U+2715"
FIGMENT_TEXT = "A figment of my own imagination."

FONT_FILES = [
    "Fonts/Header.ttf", "Fonts/Header-Italic.ttf",
    "Fonts/j.d.ttf", "Fonts/Handmade.otf",
    "Fonts/xperimental/Boiled-Pasta.ttf", "Fonts/Body.ttf",
]
SUBSET_DIR = "Fonts/subsetted"
os.makedirs(SUBSET_DIR, exist_ok=True)

print("Subsetting fonts...")
FONT_URI = {}
for f in FONT_FILES:
    opts = Options()
    opts.flavor = "woff2"
    opts.desubroutinize = True
    opts.hinting = False
    opts.drop_tables += ["FFTM", "meta"]
    font = load_font(f, opts)
    if f == "Fonts/j.d.ttf":
        codes = sorted(set(ord(c) for c in FIGMENT_TEXT))
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
    stem = os.path.splitext(os.path.basename(f))[0]
    out_path = os.path.join(SUBSET_DIR, stem + ".woff2")
    with open(out_path, "wb") as fh:
        fh.write(buf.getvalue())
    FONT_URI[f] = b64_font(out_path)
    print(f"  {f}: {len(buf.getvalue())//1024}KB woff2 inline")

print("Inlining CSS...")
css = open("styles.css").read()
for src_path, uri in FONT_URI.items():
    css = css.replace(f"url('{src_path}') format('truetype')", f"url({uri}) format('woff2')")
    css = css.replace(f"url('{src_path}') format('opentype')", f"url({uri}) format('woff2')")

def repl_css_url(m):
    path = m.group(2)
    if path.startswith("data:") or path.startswith("http"):
        return m.group(0)
    q = 65 if "hero-" in path else 78
    return f"url({img_b64(path, q)})"

css = re.sub(r"url\((['\"]?)([^'\"()]+)\1\)", repl_css_url, css)
css_min = minify_css(css)
print(f"  css {len(css_min)//1024}KB inline")

print("Building HTML...")
html = open("index-src.html").read()

html = re.sub(r'<link rel="stylesheet"[^>]*>', "", html)
html = re.sub(r'<link rel="preload"[^>]*>\n?', "", html)

fav_b64 = b64_font("favicon.webp").replace("data:font/woff2;base64,", "data:image/webp;base64,")
html = re.sub(r'<link rel="icon"[^>]*/>', f'<link rel="icon" type="image/webp" href="{fav_b64}"/>', html)
html = re.sub(r'<link rel="apple-touch-icon"[^>]*/>\n?', f'<link rel="apple-touch-icon" href="{fav_b64}"/>', html)

html = html.replace("</head>", f"<style>{css_min}</style></head>")

def min_jsonld(m):
    return '<script type="application/ld+json">' + json.dumps(json.loads(m.group(1)), separators=(",", ":")) + "</script>"

html = re.sub(r'<script type="application/ld\+json">(.*?)</script>', min_jsonld, html, flags=re.S)

def repl_src(m):
    path = m.group(1)
    if path.startswith("data:") or path.startswith("http"):
        return m.group(0)
    q = 65 if "hero-" in path else 78
    return f'src="{img_b64(path, q)}"'

print("Inlining images in markup...")
_script_re = re.compile(r'(<script\b[^>]*>.*?</script>)', re.S)
_parts = _script_re.split(html)
for _i in range(0, len(_parts), 2):
    _parts[_i] = re.sub(r'src="([^"]+\.(?:webp|png|jpg))"', repl_src, _parts[_i])
html = "".join(_parts)

_m = re.search(r"<script>(.*?)</script>", html, flags=re.S)
if _m:
    js = minify_js_body(_m.group(1))
    print("Inlining images in JS literals...")
    for path in sorted(set(re.findall(r"[\"']((?:Images|Icons)/[^\"']+\.(?:webp|png|jpg))[\"']", js))):
        if os.path.exists(path):
            js = js.replace(path, img_b64(path, 78))
    js = re.sub(r"Promise\.all\(\[[\s\S]*?\n\}\);", "/* single-file: no runtime fetch */", js)
    js = js.replace("</script", "<\\/script")
    html = html.replace(_m.group(0), "<script>" + js + "</script>")
    print(f"  js {len(js)//1024}KB inline")

html = re.sub(r"<!--(?!\[).*?-->", "", html, flags=re.S)
html = "\n".join(l.strip() for l in html.split("\n") if l.strip())

open("index.html", "w").write(html)
print(f"\nWrote index.html: {len(html)//1024}KB single file")
