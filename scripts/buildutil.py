#!/usr/bin/env python3
"""Shared helpers for the Ash Music single-file and multi-file builds."""
import base64
import io
import re

from PIL import Image

SCALE = 0.90


def img_b64(path, quality=78):
    """Downscale to 90% of original pixels, re-encode as WebP, return a
    base64 data URI. Used by both build-single.py (inline everything) and
    scripts/prerender.py (bake base64 art/thumb paths into the HTML + JSON)."""
    im = Image.open(path)
    w, h = im.size
    nw, nh = max(1, round(w * SCALE)), max(1, round(h * SCALE))
    im = im.resize((nw, nh), Image.LANCZOS)
    buf = io.BytesIO()
    if im.mode in ("RGBA", "LA", "P"):
        im = im.convert("RGBA")
        im.save(buf, "WEBP", quality=quality, method=6)
    else:
        im.convert("RGB").save(buf, "WEBP", quality=quality, method=6)
    return "data:image/webp;base64," + base64.b64encode(buf.getvalue()).decode()


def b64_font(path):
    with open(path, "rb") as fh:
        return "data:font/woff2;base64," + base64.b64encode(fh.read()).decode()


def minify_css(s):
    stash = []

    def keep(m):
        stash.append(m.group(0))
        return "\x00%d\x00" % (len(stash) - 1)

    s = re.sub(r"url\(data:[^)]+\)", keep, s)
    s = re.sub(r"/\*.*?\*/", "", s, flags=re.S)
    s = re.sub(r"\s+", " ", s)
    s = re.sub(r"\s*([{};:,>~])\s*", r"\1", s)
    s = s.replace(";}", "}")
    s = re.sub(r"\x00(\d+)\x00", lambda m: stash[int(m.group(1))], s)
    return s.strip()


def minify_js_body(body):
    """Light JS minify: drop block comments, full-line comments, blank lines.
    Trailing line comments are left in place (risky to strip blind)."""
    body = re.sub(r"/\*.*?\*/", "", body, flags=re.S)
    lines = []
    for ln in body.split("\n"):
        t = ln.strip()
        if not t or t.startswith("//"):
            continue
        lines.append(t)
    return "\n".join(lines)
