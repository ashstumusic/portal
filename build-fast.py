#!/usr/bin/env python3
"""Build the deployed index.html + cached assets from index-src.html.

Edit index-src.html + styles.css, then run: python3 build-fast.py && python3 scripts/prerender.py"""
import base64, io, json, re, sys, os
from fontTools.subset import Subsetter, Options, load_font, save_font

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
    "Fonts/outfit/Outfit-VF.ttf",              # body text (OFL)
    "Fonts/archivonarrow/ArchivoNarrow-VF.ttf",  # small labels (OFL)
    "Fonts/crimsonpro/CrimsonPro-Italic-VF.ttf",  # quote (OFL)
    "Fonts/youngserif/YoungSerif-Regular.ttf",   # release/video titles (OFL, see Fonts/youngserif/OFL.txt)
    "Fonts/fraunces/Fraunces-Regular-opsz.ttf",  # lyrics (OFL, see Fonts/fraunces/OFL.txt)
    "Fonts/bricolage/BricolageGrotesque-VF.ttf", # UI and body text (OFL, see Fonts/bricolage/OFL.txt)
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
    # Bricolage ships a width axis (75-100%) the site never uses: every rule
    # sets it at normal width. Pinning it drops the unused condensed outlines
    # from the file (weight and optical size stay variable).
    if f.endswith("BricolageGrotesque-VF.ttf"):
        from fontTools.varLib import instancer
        font = instancer.instantiateVariableFont(font, {"wdth": 100})
    # The quote face is only ever set at regular weight: ship that one
    # weight instead of the whole 200-900 range.
    if f.endswith("CrimsonPro-Italic-VF.ttf"):
        from fontTools.varLib import instancer
        font = instancer.instantiateVariableFont(font, {"wght": 400})
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

# ---------- CSS ----------
css = open("styles.css").read()
# Shared interaction/material layer used by every page (theme, palette,
# springs, glass header...). Appended so page rules can still override it.
css += "\n" + open("shared/kinetic.css").read()
css += "\n" + open("shared/psyche.css").read()   # homepage-only psychedelic layer
css += "\n" + open("shared/system.css").read()   # design system: type, spacing, radii, states (last word)
# Hover styles only while a mouse/trackpad is in use. A touch screen keeps
# :hover on the last thing tapped, so a tapped toggle (shuffle, repeat...)
# kept its hover look and seemed stuck "on" until you tapped elsewhere.
# The page sets .touch on <html> on a finger press and clears it when a
# mouse moves; every :hover (including :not(:hover)) is tied to that here.
# :where() adds no specificity, so the cascade is unchanged.
import re as _re0
css = _re0.sub(r"(?<!hover):hover(?![\w-])", ":hover:where(:root:not(.touch) *)", css)
# Images the stylesheet references get a content-hash query, so a browser
# holding an older copy under the same name fetches the new one (a stale
# star sheet showed the old textures as squares).
import hashlib as _hl, re as _re
_CSS_IMG_V = {}   # path -> version tag, reused for the same image in the HTML
def _bust(m):
    path = m.group(2)
    if path.startswith(("data:", "http")) or "?" in path or not __import__("os").path.isfile(path): return m.group(0)
    _CSS_IMG_V[path] = _hl.sha256(open(path, 'rb').read()).hexdigest()[:8]
    return f"url({m.group(1)}{path}?v={_CSS_IMG_V[path]}{m.group(1)})"
css = _re.sub(r"""url\((['"]?)(Images/[^'")]+)\1\)""", _bust, css)
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
    s = re.sub(r"\s*([{};,>~])\s*", r"\1", s)
    # Colons: only drop spaces AFTER them. A space BEFORE a colon can be a
    # descendant combinator (".a :is(.b)", ":root[x] :where(...)"); removing
    # it silently turned those into different, never-matching selectors.
    s = re.sub(r":\s+", ":", s)
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
# (UI = Bricolage is the nav and all body text; Outfit used to be preloaded
# here but nothing on the page renders in it any more, so that preload was
# 20KB fetched at top priority and thrown away.)
_PRELOAD_FONTS = {"Fonts/youngserif/YoungSerif-Regular.ttf", "Fonts/xperimental/Boiled-Pasta.ttf", "Fonts/bricolage/BricolageGrotesque-VF.ttf"}
preloads = "\n".join(
    f'<link rel="preload" href="{rel}" as="font" type="font/woff2" crossorigin>'
    for src, rel in FONT_RELPATHS.items() if src in _PRELOAD_FONTS
) + '\n<link rel="preload" as="image" href="Images/embedded/hero-ash-stu-guitar.webp" fetchpriority="high">'
html = html.replace("</head>", f'{preloads}\n<link rel="stylesheet" href="{css_out}"/>\n</head>')

# favicon -> external webp file (10KB vs ~80KB inlined base64 in the
# critical HTML payload; one small cached fetch wins for a page-load win)
_fv = __import__('hashlib').sha256(open("favicon.webp", "rb").read()).hexdigest()[:8]   # cache-bust a changed icon
html = re.sub(r'<link rel="icon"[^>]*/>', f'<link rel="icon" type="image/webp" href="favicon.webp?v={_fv}"/>', html)
html = re.sub(r'<link rel="apple-touch-icon"[^>]*/>\n?', f'<link rel="apple-touch-icon" href="favicon.png?v={_fv}"/>', html)

# minify JSON-LD
def min_jsonld(m):
    return '<script type="application/ld+json">' + json.dumps(json.loads(m.group(1)), separators=(",", ":")) + "</script>"
html = re.sub(r'<script type="application/ld\+json">(.*?)</script>', min_jsonld, html, flags=re.S)

# Images stay ordinary files: lazy-loaded where they sit below the fold,
# cached by the browser, and shared with every song page (each of those is a
# copy of this page). Nothing is inlined as base64 any more.
#
# An image the stylesheet also draws (the hero photo is both an <img> and a
# CSS background) must use the very same URL in the HTML, version tag and
# all: with two different URLs the browser downloaded the hero twice.
def _same_url_as_css(m):
    v = _CSS_IMG_V.get(m.group(2))
    return f'{m.group(1)}="{m.group(2)}?v={v}"' if v else m.group(0)
_script_re = re.compile(r'(<script\b[^>]*>.*?</script>)', re.S)
_parts = _script_re.split(html)
for _i in range(0, len(_parts), 2):  # even indices = markup outside <script>
    _parts[_i] = re.sub(r'(src|href)="(Images/[^"?]+)"', _same_url_as_css, _parts[_i])
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

# Shared interaction script (shared/kinetic.js), minified by esbuild into a
# hashed file next to main.*.js, loaded deferred at the end of <body>.
import subprocess as _sp
_esb = os.path.join(ROOT, "node_modules", ".bin", "esbuild")
if os.path.exists(_esb):
    _k = _sp.run([_esb, "--minify", "--target=es2020", "--legal-comments=none"], input=open("shared/kinetic.js").read(),
                 capture_output=True, text=True, check=True).stdout
else:
    print("  (esbuild not found: shipping shared/kinetic.js unminified; run npm install)")
    _k = open("shared/kinetic.js").read()
k_out = f"kinetic.{__import__('hashlib').sha256(_k.encode()).hexdigest()[:8]}.js"
open(k_out, "w").write(_k)
html = html.replace("</body>", f'<script src="{k_out}" defer></script>\n</body>', 1)
print(f"Wrote {k_out}: {len(_k)//1024}KB")

# Homepage-only psychedelic layer (shared/psyche.js), same treatment.
if os.path.exists(_esb):
    _p = _sp.run([_esb, "--minify", "--target=es2020", "--legal-comments=none"], input=open("shared/psyche.js").read(),
                 capture_output=True, text=True, check=True).stdout
else:
    _p = open("shared/psyche.js").read()
p_out = f"psyche.{__import__('hashlib').sha256(_p.encode()).hexdigest()[:8]}.js"
open(p_out, "w").write(_p)
html = html.replace("</body>", f'<script src="{p_out}" defer></script>\n</body>', 1)
print(f"Wrote {p_out}: {len(_p)//1024}KB")

# strip HTML comments + indentation, collapse blank lines
html = re.sub(r"<!--(?!\[).*?-->", "", html, flags=re.S)
html = "\n".join(l.strip() for l in html.split("\n") if l.strip())

open("index.html", "w").write(html)
print(f"\nWrote index.html: {len(html)//1024}KB")

# Delete hashed bundles from earlier builds (anything index.html no longer
# loads), so old builds don't pile up and weigh down every deploy.
_keep = set(re.findall(r"(?:main|styles|kinetic|psyche)\.[0-9a-f]{8}(?:\.min)?\.(?:js|css)", html))
_old = [f for f in os.listdir(".") if re.fullmatch(r"(?:main|styles|kinetic|psyche)\.[0-9a-f]{8}(?:\.min)?\.(?:js|css)", f) and f not in _keep]
for f in _old: os.remove(f)
if _old: print(f"Removed {len(_old)} old build file(s)")
