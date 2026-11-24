import time
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
FIGMENT_TEXT = "A figment of my own imagination. HI, HOW ARE YOU"   # (the second: the 1-in-100 tagline)

FONT_FILES = [
    "Fonts/Header.ttf", "Fonts/Header-Italic.ttf",
    "Fonts/j.d.ttf", "Fonts/Handmade.otf",
    "Fonts/xperimental/Boiled-Pasta.ttf", "Fonts/Body.ttf",
    "Fonts/outfit/Outfit-VF.ttf",              # body text (OFL)
    "Fonts/archivonarrow/ArchivoNarrow-VF.ttf",  # small labels (OFL)
    "Fonts/crimsonpro/CrimsonPro-Italic-VF.ttf",  # quote (OFL)
    "Fonts/youngserif/YoungSerif-Regular.ttf",   # release/video titles (OFL, see Fonts/youngserif/OFL.txt)
    "Fonts/fraunces/Fraunces-Regular-opsz.ttf",  # no longer used by the site's stylesheet (lyrics are in Reddit Sans Condensed); still read by scripts/build_lyrics_pages.py
    "Fonts/bricolage/BricolageGrotesque-VF.ttf", # UI (OFL, see Fonts/bricolage/OFL.txt)
    "Fonts/redditsanscondensed/RedditSansCondensed-VF.ttf",  # body text and lyrics (OFL, see Fonts/redditsanscondensed/OFL.txt)
    "Fonts/nationalpark/NationalPark-VF.ttf",  # category labels such as "ALBUM" (OFL, see Fonts/nationalpark/OFL.txt)
    "Fonts/battambang/Battambang-Bold.ttf",  # release titles (OFL, see Fonts/battambang/OFL.txt)
    "Fonts/cabinsketch/CabinSketch-Bold.ttf",  # section headers (OFL, see Fonts/cabinsketch/OFL.txt)
    "Fonts/vastshadow/VastShadow-Regular.ttf",        # the name under the quote (OFL, see Fonts/vastshadow/OFL.txt)
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
    # Body text and lyrics are only ever set at regular weight too.
    if f.endswith("RedditSansCondensed-VF.ttf"):
        from fontTools.varLib import instancer
        font = instancer.instantiateVariableFont(font, {"wght": 400})
    exact = FIGMENT_TEXT if f == "Fonts/j.d.ttf" else None
    # Cabin Sketch draws only the section headers ("Music", "Videos"...). Its sketched outlines are heavy (95KB for the
    # usual character set), so it ships with exactly the letters those headers use, read from the page itself: a new
    # or renamed header is picked up on the next build. (A header written by script would fall back to the UI font.)
    if f.endswith("CabinSketch-Bold.ttf"):
        _src = open("index-src.html", encoding="utf-8").read()
        _heads = re.findall(r'<h[1-6][^>]*class="[^"]*\bsection-h\b[^"]*"[^>]*>(.*?)</h[1-6]>', _src, flags=re.S)
        exact = "".join(re.sub(r"<[^>]+>", "", h) for h in _heads) + " "
        exact += exact.upper() + exact.lower()   # (both cases, in case the headers are ever set in capitals)
        assert len(_heads) >= 3, "no section headers found for the Cabin Sketch subset"
    # Vast Shadow sets one thing: the name under the quote ("Woody Guthrie"). Same treatment, read from the page.
    if f.endswith("VastShadow-Regular.ttf"):
        _src = open("index-src.html", encoding="utf-8").read()
        _cites = re.findall(r'<blockquote class="disc-quote">.*?<cite>(.*?)</cite>', _src, flags=re.S)
        assert _cites, "no quote name found for the Vast Shadow subset"
        exact = "".join(re.sub(r"<[^>]+>", "", c) for c in _cites) + " "
        exact += exact.upper() + exact.lower()   # (it is shown in capitals by the stylesheet: both cases, so a style change cannot strand letters)
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
# the phone toolbar on tablets, touch screens and narrow windows (copies of the phone toolbar rules; see the script)
sys.path.insert(0, "scripts"); from compact_toolbar import compact_toolbar
css = compact_toolbar(css)
# The stylesheets raise a rule's priority with a run of ":not(#\\#)" (each one counts as an ID) - up to 60 in a row,
# about 330KB of the 790KB stylesheet. A run of N is written here as ONE ":not(#\\##\\#...)" with N IDs in it: the
# same priority, the same meaning (it matches every element), a third of the size, and much less for a phone to parse.
import re as _reNot
css = _reNot.sub(r"(?::not\(#\\#\)){2,}", lambda m: ":not(" + "#\\#" * (len(m.group(0)) // 9) + ")", css)
# Those runs only need to keep their ORDER: run lengths are renumbered smaller, keeping every gap of up to 3 exactly
# (a selector adds at most 2 real IDs of its own, so a gap of 3 or more already decides the winner whatever it is) -
# which rule wins is unchanged, and the shipped stylesheet loses about a third of the runs' weight.
_runs = [len(m) // 3 for m in _reNot.findall(r"(?<=:not\()(?:#\\#)+(?=\))", css)]
_vals = sorted(set(_runs) | {0}); _map = {0: 0}
for _a, _b in zip(_vals, _vals[1:]): _map[_b] = _map[_a] + min(_b - _a, 3)
css = _reNot.sub(r":not\(((?:#\\#)+)\)", lambda m: ":not(" + "#\\#" * _map[len(m.group(1)) // 3] + ")", css)
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
_PRELOAD_FONTS = {"Fonts/battambang/Battambang-Bold.ttf", "Fonts/xperimental/Boiled-Pasta.ttf", "Fonts/bricolage/BricolageGrotesque-VF.ttf",
                  # (also the small ones whose late arrival moved the page: the quote's name above Videos gained a line when
                  # Vast Shadow arrived, the About tagline changed size when its handwriting did, and the category labels;
                  # a page opened at a section - /videos/, /about/ - jumped as they landed)
                  "Fonts/vastshadow/VastShadow-Regular.ttf", "Fonts/j.d.ttf", "Fonts/nationalpark/NationalPark-VF.ttf"}
preloads = "\n".join(
    f'<link rel="preload" href="{rel}" as="font" type="font/woff2" crossorigin>'
    for src, rel in FONT_RELPATHS.items() if src in _PRELOAD_FONTS
) + '\n<link rel="preload" as="image" href="Images/embedded/hero-ash-stu-guitar.webp" imagesrcset="Images/embedded/hero-ash-stu-guitar.webp 1400w, Images/embedded/hero-ash-stu-guitar-2000.webp 2000w" imagesizes="(max-width: 767px) 100vw, 80vw" fetchpriority="high">'
html = html.replace("</head>", f'{preloads}\n<link rel="stylesheet" href="{css_out}"/>\n</head>')

# icons: cache-bust them when the artwork changes (favicon.ico for old browsers and the bare /favicon.ico request,
# favicon.svg for browsers that take vector icons, a square opaque PNG for iOS, and the manifest for Android)
_fv = __import__('hashlib').sha256(open("favicon.svg", "rb").read()).hexdigest()[:8]
for _n in ('favicon.ico', 'apple-touch-icon.png', 'site.webmanifest'):
    assert f'href="{_n}"' in html, _n
    html = html.replace(f'href="{_n}"', f'href="{_n}?v={_fv}"')
html = html.replace('<link href="favicon.svg"', f'<link href="favicon.svg?v={_fv}"')   # the vector icon (browsers that take SVG icons prefer it)

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
    # (and inside srcset / imagesrcset lists: the browser picks from those, so an untagged entry there was a second download)
    _parts[_i] = re.sub(r'((?:image)?srcset)="([^"]+)"', lambda m: m.group(1) + '="' + re.sub(r'(Images/[^\s,?]+)', lambda q: q.group(1) + ('?v=' + _CSS_IMG_V[q.group(1)] if q.group(1) in _CSS_IMG_V else ''), m.group(2)) + '"', _parts[_i])
html = "".join(_parts)
# The head script that waits for the pencil-shading image before showing the name's shading asks for it by the
# stylesheet's exact URL too (it asked for the bare "/Images/pencil-hatch.webp", so the 216KB image was downloaded twice).
if _CSS_IMG_V.get("Images/pencil-hatch.webp"):
    html = html.replace('h.src="/Images/pencil-hatch.webp"', 'h.src="/Images/pencil-hatch.webp?v=' + _CSS_IMG_V["Images/pencil-hatch.webp"] + '"')

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

# The main script is the LARGEST plain inline <script> (not the first one: the first is a few
# lines that must run before the first paint, and taking it by mistake left ~125KB of script
# inside the page, where it delayed the first paint and was downloaded again on every visit).
# The small inline scripts that follow it rely on what it sets up, so they go into the same
# file, in the same order, each in its own try block so one failing cannot stop the rest.
_plain = list(re.finditer(r"<script>(.*?)</script>", html, flags=re.S))
if _plain:
    _m = max(_plain, key=lambda m: len(m.group(1)))
    _tail = [m for m in _plain if m.start() > _m.start()]
    _end = _m.end()
    for m in _tail:
        assert not html[_end:m.start()].strip(), "markup between the main script and a later inline script"
        _end = m.end()
    js_src = _m.group(1) + "".join(
        "\n;try{\n" + m.group(1) + "\n}catch(e){setTimeout(function(){throw e})}" for m in _tail)
    _esb0 = os.path.join(ROOT, "node_modules", ".bin", "esbuild")
    if os.path.exists(_esb0):
        import subprocess as _sp0
        js_min = _sp0.run([_esb0, "--minify", "--target=es2020", "--legal-comments=none"], input=js_src,
                          capture_output=True, text=True, check=True).stdout
    else:
        js_min = minify_js_body(js_src)
    js_hash = __import__('hashlib').sha256(js_min.encode()).hexdigest()[:8]
    js_out = f"main.{js_hash}.js"
    for _old in __import__('glob').glob("main.*.js"):
        if _old != js_out: os.remove(_old)
    with open(js_out, "w") as fh:
        fh.write(js_min)
    html = html[:_m.start()] + f'<script src="{js_out}" defer></script>' + html[_end:]
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

# The three scripts start AFTER the first paint. With plain `defer` the browser ran all of them
# (about 130KB) before it painted anything, so a slow phone showed a blank page while it worked.
# They are still downloaded straight away (preload), then run in order (main, kinetic, psyche)
# one frame after the page is parsed; in a background tab, where frames do not happen, at once.
_late = [u for u in (globals().get("js_out"), k_out, p_out) if u]
for u in _late:
    assert f'<script src="{u}" defer></script>' in html, u
    html = html.replace(f'<script src="{u}" defer></script>\n', "").replace(f'<script src="{u}" defer></script>', "")
# (No preload for them: fetched in parallel they took bandwidth from the stylesheet the first paint waits for; they are
# fetched when the loader below adds them, right after the page is parsed.)
_loader = ('<script>(function(s){var d=document,done=0;function go(){if(done)return;done=1;s.forEach(function(u){var e=d.createElement("script");e.src=u;e.async=false;d.body.appendChild(e)})}'
           'function after(){if(d.hidden)return go();requestAnimationFrame(function(){setTimeout(go,0)});setTimeout(go,600)}'
           'd.readyState==="loading"?d.addEventListener("DOMContentLoaded",after):after()})(' + __import__("json").dumps(_late) + ')</script>')
html = html.replace("</body>", _loader + "\n</body>", 1)
print(f"Wrote {p_out}: {len(_p)//1024}KB")

# ── PRESS KIT ─────────────────────────────────────────────────────────────────────────────────────────────────────
# No ZIP is kept anywhere (owner's request: "just compile it all live, dont pre zip it. that takes up too much storage
# on github"). The kit is a list of files already on the site, written here into the page (kit-data); pressing Download
# makes the ZIP in the visitor's browser from them (kitZip in index-src.html). What is in it:
#   Songs/        the kit's songs (KIT_SONGS), the site's own recordings, labelled "Ash Stu - Press Kit" with Headshot-1
#                 as their cover (the label is written in the browser; the sound is the site's file, unchanged)
#   the fact sheet and the lyrics (plain text, written here into Images/press-kit/)
#   Photos/       the PNGs in Images/press-kit/
KIT_DIR = os.path.join(ROOT, "Images", "press-kit")
KIT_TOP = "Ash Stu - Press Kit/"
KIT_SONGS = ["Dirge for Ducklings", "Still Sad", "Summertime Even on the Moon", "Worship Song", "You Are What You Love"]
KIT_PHOTO_ORDER = ["Ash Stu - Headshot-1.png", "Ash Stu - Headshot-2.png", "Ash Stu - Live at the Keyboard (Wide).png",
                   "Ash Stu - Headshot-3.png", "Ash Stu - Guitar in Alley (Wide).png",
                   "Ash Stu - Alley at Sunset (Wide).png", "Ash Stu - Alley Portrait.png"]   # (the last two new, 2026-11-24: owner's photos; see scripts/kit_photos.py)   # (the photos' order on the page, the ZIP's list and the Fact Sheet)
KIT_VIDEOS = ["The Cloud for the Desert", "Theory of Hope"]   # (owner's choice: live solo acoustic performances, the first leads)
KIT_VIDEO_NOTE = ""   # (owner's request, 2026-11-23: "remove the live, and solo acoustic")
KIT_SONG_COVER = "Images/embedded/kit-song-cover.jpg"   # (Headshot-1 as a JPEG: the picture music apps show for the kit's songs)
# The artist's facts, as the site states them (About section, contact line). One place to change them: the Fact Sheet
# and the press kit card are both written from here.
KIT_FACTS = {
    "pitch": "Outsider singer-songwriter from Guthrie, Oklahoma, formerly known as Ashton Stubblefield.",
    "from": "Guthrie, Oklahoma",
    "aka": "Ashton Stubblefield",
    "email": (re.search(r'mailto:([^"?]+)', open(os.path.join(ROOT, "index-src.html"), encoding="utf-8").read()) or [None, ""])[1],
    "site": "https://ashstu.art",
}
# Photo credits: shown on each of these photos on the page and listed in the Fact Sheet.
PHOTOGRAPHERS = {"Emma Evans": "https://www.facebook.com/profile.php?id=100018702414515"}
_KIT_CREDIT = {"Ash Stu - Headshot-2.png": "Emma Evans", "Ash Stu - Live at the Keyboard (Wide).png": "Emma Evans"}
_KIT_THUMB = {"Ash Stu - Headshot-1.png": "epk-ash-stu-stairs.webp", "Ash Stu - Headshot-2.png": "epk-ash-stu-singing.webp?v=5",
              "Ash Stu - Headshot-3.png": "epk-ash-stu-guitar-door.webp?v=2", "Ash Stu - Guitar in Alley (Wide).png": "epk-ash-stu-alley.webp?v=2",
              "Ash Stu - Alley at Sunset (Wide).png": "epk-ash-stu-sunset.webp", "Ash Stu - Alley Portrait.png": "epk-ash-stu-alley-portrait.webp",
              "Ash Stu - Live at the Keyboard (Wide).png": "epk-ash-stu-performing.webp?v=5"}
def _press_kit():
    import json as _json
    rels = _json.load(open(os.path.join(ROOT, "releases.json"), encoding="utf-8"))
    lyr = _json.load(open(os.path.join(ROOT, "lyrics.json"), encoding="utf-8"))
    def find(title):
        for ri, r in enumerate(rels):
            for ti, t in enumerate(r.get("tracks") or []):
                if t["title"].lower() == title.lower(): return ri, ti, r, t
        return None
    def date_of(r):
        m = re.match(r"(\d{4})-(\d{2})-(\d{2})$", r.get("date") or "")
        if not m: return str(r.get("year") or "")
        return ["January","February","March","April","May","June","July","August","September","October","November","December"][int(m[2]) - 1] + f" {int(m[3])}, {m[1]}"
    def year_of(r): return (r.get("date") or "")[:4] or str(r.get("year") or "")
    def size(rel_path): return os.path.getsize(os.path.join(ROOT, rel_path))
    def length(rel_path):   # "2:23" (empty if it cannot be read)
        try:
            from mutagen.mp3 import MP3
            n = round(MP3(os.path.join(ROOT, rel_path)).info.length); return f"{n // 60}:{n % 60:02d}"
        except Exception: return ""
    def fmt(n): return f"{n / 1048576:.1f} MB" if n >= 104858 else f"{max(1, round(n / 1024))} KB"
    files = []
    songs = [x for x in (find(t) for t in KIT_SONGS) if x]
    for k, (ri, ti, r, t) in enumerate(songs, 1):
        files.append({"path": KIT_TOP + "Songs/" + t["title"] + " - " + r["name"] + ".mp3", "src": t["file"], "type": "song", "title": t["title"],   # ("its name - the album it's from", as listed on the page)
                      "ri": ri, "ti": ti, "from": r["name"] + (" (" + year_of(r) + ")" if year_of(r) else ""), "length": length(t["file"]), "tag": {"title": t["title"], "album": "Ash Stu - Press Kit", "track": f"{k}/{len(songs)}", "cover": KIT_SONG_COVER}})
    photos = sorted((f for f in os.listdir(KIT_DIR) if f.lower().endswith((".png", ".jpg", ".jpeg"))),
                    key=lambda n: (KIT_PHOTO_ORDER.index(n) if n in KIT_PHOTO_ORDER else len(KIT_PHOTO_ORDER), n.lower()))   # (the owner's order; any new photo after them)
    # the two text files
    # the live videos' songs too (owner's request): their words as on the release they are from (lyrics.json, keyed by the
    # release's song file, or by its lyrics file for a song not released yet), never the video's captions
    vsongs = []
    for title in KIT_VIDEOS:
        for r in rels:
            hit = next((t for t in (r.get("tracks") or []) if t["title"].lower() == title.lower()), None)
            key = hit and hit["file"]
            if not hit:
                up = next((t for t in (r.get("upcoming") or []) if t["title"].lower() == title.lower()), None)
                key = up and up.get("lyrics"); hit = up
            if hit: vsongs.append((r, hit, key)); break
    lines = ["ASH STU - LYRICS", "", "The words to the " + str(len(songs)) + " songs in the Songs folder of this press kit, in its order" + (", then to the songs of its " + str(len(vsongs)) + " live videos." if vsongs else ".")]
    lines += [""]
    for ri, ti, r, t in songs:
        words = [(x or "").strip() for _, x in ((lyr.get(t["file"]) or {}).get("lines") or [])]
        words = [w for w in words if w]
        lines += ["", "=" * 40, t["title"].upper(), "From " + r["name"] + (" (" + year_of(r) + ")" if year_of(r) else ""), "=" * 40, ""]
        lines += words or ["(Instrumental)"]
        lines += [""]
    if vsongs:
        lines += ["", "", "LIVE VIDEOS", "-" * 40, ""]
        for r, t, key in vsongs:
            words = [(x or "").strip() for _, x in ((lyr.get(key) or {}).get("lines") or [])]
            words = [w for w in words if w]
            lines += ["", "=" * 40, t["title"].upper(), "From " + r["name"] + (" (" + year_of(r) + ")" if year_of(r) else "") + ", seen in the live video", "=" * 40, ""]
            lines += words or ["(Instrumental)"]
            lines += [""]
    lines += ["", "-" * 40, "Ash Stu  -  " + KIT_FACTS["site"], ""]
    F = KIT_FACTS
    fs = ["ASH STU - FACT SHEET", "", F["pitch"], "",
          "Artist:              Ash Stu", "Formerly known as:   " + F["aka"], "From:                " + F["from"], "",
          "Booking and press:   " + F["email"], "Website:             " + F["site"], ""]
    # the artist's own pages (what a booker or writer looks up first), read from the site's "sameAs" list in
    # index-src.html so the two never drift apart; one line per service (the first link wins)
    _sa = re.search(r'"sameAs"\s*:\s*\[(.*?)\]', open(os.path.join(ROOT, "index-src.html"), encoding="utf-8").read(), re.S)
    _pages = {}
    for _u in re.findall(r'"(https?://[^"]+)"', _sa[1] if _sa else ""):
        _lb = next((lb for dom, lb in (("music.apple.com", "Apple Music"), ("open.spotify.com", "Spotify"), ("music.youtube.com", "YouTube Music"),
                                        ("youtube.com", "YouTube"), ("deezer.com", "Deezer"), ("substack.com", "Substack"), ("patreon.com", "Patreon"),
                                        ("instagram.com", "Instagram"), ("tiktok.com", "TikTok"), ("bandcamp.com", "Bandcamp"), ("facebook.com", "Facebook"))
                    if dom in _u), None)
        if _lb and _lb not in _pages: _pages[_lb] = _u
    if _pages:
        fs += ["", "ARTIST PAGES", "-" * 40, ""] + [f"{lb + ':':<21}{u}" for lb, u in _pages.items()] + [""]
    fs += ["", "RELEASES", "-" * 40]
    for r in rels:
        n_out, n_soon = len(r.get("tracks") or []), len(r.get("upcoming") or [])
        line = r["name"] + "  -  " + (r.get("type") or "Album").lower() + ", " + (date_of(r) or "date to come")
        line += f", {n_out} songs" if not n_soon else f", {n_out} of its {n_out + n_soon} songs released so far"
        fs += ["", line]
        for key, label in (("apple", "Apple Music"), ("spotify", "Spotify"), ("ytmusic", "YouTube Music"), ("deezer", "Deezer")):
            if r.get(key): fs.append(f"  {label + ':':<16}{r[key]}")
    _w = max([len(t["title"] + " - " + r["name"] + ".mp3") for _, _, r, t in songs] or [0]) + 3
    fs += ["", "", "IN THIS PRESS KIT", "-" * 40, "",
           "Songs folder: a sampler of " + str(len(songs)) + " songs (MP3), each named for the song and the album it is from, with the year and length:",
           *["  " + (t["title"] + " - " + r["name"] + ".mp3").ljust(_w) + (year_of(r) or "") + ((", " + length(t["file"])) if length(t["file"]) else "") for _, _, r, t in songs], "",
           "Ash Stu - Lyrics.txt", "  The words to the " + str(len(songs)) + " songs in the Songs folder" + (" and to the songs of the live videos." if vsongs else "."), "",
           "Ash Stu - Fact Sheet.txt", "  This file.", "",
           "Photos folder (PNG), with photo credits:", *["  " + (f.ljust(max(map(len, photos)) + 3) + ("Photo: " + _KIT_CREDIT[f] if f in _KIT_CREDIT else "")).rstrip() for f in photos], ""]
    for _who, _url in PHOTOGRAPHERS.items():
        if any(_KIT_CREDIT.get(f) == _who for f in photos): fs += [_who + ", photographer: " + _url, ""]
    vids = []
    _vl = {v["title"]: v for v in _json.load(open(os.path.join(ROOT, "videos.json"), encoding="utf-8"))}
    for title in KIT_VIDEOS:
        v = _vl.get(title)
        if not v: continue
        try:
            from mutagen.mp4 import MP4
            n = round(MP4(os.path.join(ROOT, v["file"])).info.length); ln = f"{n // 60}:{n % 60:02d}"
        except Exception: ln = ""
        _vb = os.path.getsize(os.path.join(ROOT, v["file"]))
        _hit = next(((r, t) for r in rels for t in (r.get("tracks") or []) + (r.get("upcoming") or []) if t["title"].lower() == title.lower()), None)   # (the release its song is from)
        _rel = _hit[0]["name"] if _hit else ""   # (the album it is on, or will be on)
        _soon = bool(_hit) and not any(t is _hit[1] for t in (_hit[0].get("tracks") or []))   # (not out yet: "unreleased")
        _lk = (_hit[1].get("file") or _hit[1].get("lyrics") or "") if _hit else ""   # (its words, as on the release: never the video's captions)
        vids.append({"title": title, "from": _rel, "soon": _soon, "lyricsKey": _lk, "length": ln, "youtube": v.get("youtube", ""), "thumb": v.get("thumb", ""), "note": KIT_VIDEO_NOTE,
                     "file": v["file"], "size": f"{_vb / 1048576:.0f} MB"})
    if vids:
        _vw = max(len(v["title"] + " - Ash Stu (Live).mp4") for v in vids) + 3
        fs += ["Videos folder: " + str(len(vids)) + " live videos (MP4):"]
        for v in vids:
            fs += ["  " + (v["title"] + " - Ash Stu (Live).mp4").ljust(_vw) + v["note"].lower() + ((", " + v["length"]) if v["length"] else "")]
        fs += [""]
        for v in vids:   # (in the ZIP too: owner's request)
            files.append({"path": KIT_TOP + "Videos/" + v["title"] + " - Ash Stu (Live).mp4", "src": v["file"], "type": "video"})
    fs += ["Free to use for booking, press and promotion of Ash Stu.", ""]
    texts = {"Ash Stu - Fact Sheet.txt": fs, "Ash Stu - Lyrics.txt": lines}
    for name, body in texts.items():
        data = "\r\n".join(body).encode("utf-8-sig")   # (the mark at the start tells every browser and editor it is UTF-8)
        dst = os.path.join(KIT_DIR, name)
        if not (os.path.exists(dst) and open(dst, "rb").read() == data):
            open(dst, "wb").write(data); print("Press kit: wrote " + name)
        files.append({"path": KIT_TOP + name, "src": "Images/press-kit/" + name, "type": "text"})
    for f in photos:
        dims = None
        with open(os.path.join(KIT_DIR, f), "rb") as fh: hd = fh.read(24)
        if hd[:8] == b"\x89PNG\r\n\x1a\n": dims = [int.from_bytes(hd[16:20], "big"), int.from_bytes(hd[20:24], "big")]
        files.append({"path": KIT_TOP + "Photos/" + f, "src": "Images/press-kit/" + f, "type": "photo", "thumb": ("Images/embedded/" + _KIT_THUMB[f]) if f in _KIT_THUMB else "", "dims": dims,
                      **({"credit": _KIT_CREDIT[f], "creditUrl": PHOTOGRAPHERS.get(_KIT_CREDIT[f], "")} if f in _KIT_CREDIT else {})})
    for f in files:
        f["name"] = f["path"].rsplit("/", 1)[1]; f["ext"] = f["name"].rsplit(".", 1)[1].upper()
        n = size(f["src"]); f["bytes"] = n; f["size"] = fmt(n); f["mb"] = round(n / 1048576, 1)
    # (when the kit last changed: the last commit that touched its files or the songs list here; a file's own date is
    # useless, since a fresh copy of the repository dates every file to the moment it was copied)
    try:
        import subprocess as _sp2
        _upd = _sp2.run(["git", "log", "-1", "--format=%cs", "--", "Images/press-kit", "releases.json"], cwd=ROOT, capture_output=True, text=True).stdout.strip()
    except Exception: _upd = ""
    return {"top": KIT_TOP, "files": files, "bytes": sum(f["bytes"] for f in files), "facts": KIT_FACTS,
            "updated": _upd or time.strftime("%Y-%m-%d"), "videos": vids}
_kitdata = _press_kit()
html = html.replace("__KIT_MB__", str(max(1, round(_kitdata["bytes"] / 1048576))))
html = html.replace("__KIT_JSON__", json.dumps(_kitdata, separators=(",", ":")).replace("</", "<\\/"))

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
