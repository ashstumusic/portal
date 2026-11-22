#!/usr/bin/env python3
"""Static lyric pages for search engines, AI crawlers and readers.

For every track in releases.json that has lyrics in lyrics.json this writes
lyrics/<song-slug>/index.html: the full lyrics as plain HTML (one <p> per
verse, <br> between lines), JSON-LD (MusicRecording + MusicComposition with
the lyrics text), Open Graph / Twitter tags and a canonical URL. It also
writes lyrics/index.html (every song, grouped by release), adds the pages
to sitemap.xml between LYRICS markers, and keeps robots.txt open to search
and AI crawlers.

No JavaScript is needed to read any of it. Re-running is safe: a page's
"modified" date only changes when its content does.

Run: python3 scripts/build_lyrics_pages.py   (npm run build runs it too)
"""
import datetime
import hashlib
import html
import json
import os
import re
import unicodedata
import urllib.parse
import sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import song_keys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SITE = 'https://ashstu.art'
ARTIST = 'Ash Stu'
ARTIST_FULL = 'Ashton Stubblefield'
GENRE = 'Outsider'
OUT = os.path.join(ROOT, 'lyrics')
TODAY = datetime.date.today().isoformat()


def esc(s):
    # &, <, > and double quotes only: apostrophes stay readable for scrapers.
    return html.escape(str(s), quote=False).replace('"', '&quot;')


def slugify(s):
    s = unicodedata.normalize('NFKD', s).encode('ascii', 'ignore').decode()
    s = re.sub(r"['’]", '', s.lower())
    return re.sub(r'[^a-z0-9]+', '-', s).strip('-') or 'song'


def cover_alts():
    """Descriptive cover alt text, kept in scripts/cover_alts.json (picture path -> description). It used to be read from
    redesign/facts.json, which is no longer published, so the site's automatic rebuild lost the descriptions."""
    try:
        with open(os.path.join(ROOT, 'scripts', 'cover_alts.json'), encoding='utf-8') as f:
            return json.load(f)
    except (OSError, ValueError):
        return {}


def human_date(iso):
    d = datetime.date.fromisoformat(iso)
    return f'{d.day} {d.strftime("%B")} {d.year}'


def release_date(release_name):
    """The `date:` line in Audio/<release>/links.txt, if any."""
    path = os.path.join(ROOT, 'Audio', release_name, 'links.txt')
    try:
        with open(path, encoding='utf-8') as f:
            for line in f:
                m = re.match(r'\s*date\s*:\s*(\d{4}-\d{2}-\d{2})', line)
                if m:
                    return m.group(1)
    except OSError:
        pass
    return None


def stanzas(entry, file=None):
    """The lyrics as one block: every line in order, no verse breaks (the
    lines come already cleaned from lyrics.json - see clean_lyric in
    generate_content.py). Kept as a list of verses for the page builders."""
    lines = [(text or '').strip() for _, text in (entry.get('lines') or [])]
    lines = [l for l in lines if l]
    return [lines] if lines else []


def previous_meta(path):
    """(content hash, modified date) recorded in an existing page."""
    try:
        with open(path, encoding='utf-8') as f:
            head = f.read(4000)
    except OSError:
        return None, None
    h = re.search(r'<meta name="(?:lyrics|album|video|section)-hash" content="([0-9a-f]+)"', head)
    d = re.search(r'<meta property="article:modified_time" content="(\d{4}-\d{2}-\d{2})"', head)
    return (h.group(1) if h else None), (d.group(1) if d else None)


STYLE = """
@font-face { font-family: 'Headline'; src: url('/Fonts/subsetted/Battambang-Bold.woff2') format('woff2'); font-weight: 700; font-display: swap; }   /* titles of works: same face as the release titles on the home page */
@font-face { font-family: 'Lyrics'; src: url('/Fonts/subsetted/Fraunces-Regular-opsz.woff2') format('woff2'); font-display: swap; }
@font-face { font-family: 'Text'; src: url('/Fonts/subsetted/BricolageGrotesque-VF.woff2') format('woff2'); font-weight: 200 800; font-display: swap; }   /* the site's interface and body face */
:root { --paper: #F0F5F6; --surface: #FAFCFC; --ink: #084C61; --ink-soft: #3A6574; --gold: #F7C549; --rule: rgba(8,76,97,.14); color-scheme: light; }
@media (prefers-color-scheme: dark) { :root { --paper: #0B171C; --surface: #13232A; --ink: #DCEEF2; --ink-soft: #9DB7C0; --rule: rgba(220,238,242,.14); color-scheme: dark; } }
* { box-sizing: border-box; }
body { margin: 0; background: var(--paper); color: var(--ink); font: 400 1rem/1.6 'Text', system-ui, -apple-system, 'Segoe UI', Roboto, sans-serif;
  padding-inline: max(16px, env(safe-area-inset-left, 0px)) max(16px, env(safe-area-inset-right, 0px)); }
body { max-width: 44rem; margin-inline: auto; padding-block: 1.5rem 4rem; }
.site { display: flex; justify-content: space-between; align-items: center; gap: 1rem; flex-wrap: wrap; padding-bottom: 1rem; border-bottom: 3px solid var(--gold); }
.site a { color: var(--ink); font-weight: 600; text-decoration: none; }
.site a:hover, .site a:focus-visible { text-decoration: underline; }
.crumbs { font-size: .9rem; color: var(--ink-soft); }
.crumbs a { color: inherit; }
h1, h2 { font-family: 'Headline', Georgia, serif; font-weight: 700; font-synthesis: none; line-height: 1.15; text-wrap: balance; margin: 0; }
h1 { font-size: clamp(2rem, 6vw, 2.8rem); }
h2 { font-size: 1.35rem; margin-top: 2rem; }
.song-head { display: grid; grid-template-columns: 9rem 1fr; gap: 1.25rem; align-items: center; margin-top: 2rem; }
.song-head hgroup { margin: 0; }
table { border-collapse: collapse; width: 100%; margin-top: .75rem; font-size: .95rem; }
caption { text-align: left; font-weight: 600; color: var(--ink-soft); padding-bottom: .4rem; }
th, td { text-align: left; vertical-align: top; padding: .45rem .6rem; border-bottom: 1px solid var(--rule); }
th { font-weight: 600; }
tbody th[scope="row"] { width: 38%; }
.release tbody th { width: auto; }
thead th { color: var(--ink-soft); font-size: .85rem; }
td.num { font-variant-numeric: tabular-nums; width: 1%; white-space: nowrap; }
.song-head img { width: 100%; height: auto; border-radius: 10px; display: block; }
.byline { color: var(--ink-soft); margin: .5rem 0 0; }
.byline a { color: inherit; }
.lyrics p { font: 400 1.15rem/1.65 'Lyrics', Georgia, 'Times New Roman', serif; margin: 0 0 1.4em; max-width: 60ch; }
.listen { display: flex; flex-wrap: wrap; gap: .6rem; margin-top: 1.5rem; padding: 0; list-style: none; }
.listen a { display: inline-block; padding: .55rem 1rem; border: 1px solid var(--rule); border-radius: 10px; background: var(--surface); color: var(--ink); text-decoration: none; font-weight: 600; }
.listen a:hover, .listen a:focus-visible { background: var(--gold); border-color: var(--gold); color: #084C61; }
.more { margin-top: 2.5rem; border-top: 1px solid var(--rule); padding-top: 1rem; font-size: .95rem; }
.more a { color: var(--ink); }
.release { margin-top: 2rem; }
.release a, td a { color: var(--ink); }
.muted { color: var(--ink-soft); }
footer { margin-top: 3rem; font-size: .85rem; color: var(--ink-soft); }
a:focus-visible { outline: 2px solid var(--gold); outline-offset: 2px; }
@media (max-width: 480px) { .song-head { grid-template-columns: 1fr; } .song-head img { max-width: 12rem; } }
"""


def page(title, description, canonical, og_type, image, image_alt, body, jsonld, extra_head=''):
    return f"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{esc(title)}</title>
<meta name="description" content="{esc(description)}">
<meta name="robots" content="index, follow, max-snippet:-1, max-image-preview:large">
<link rel="canonical" href="{esc(canonical)}">
{extra_head}<meta property="og:site_name" content="{ARTIST}">
<meta property="og:type" content="{og_type}">
<meta property="og:title" content="{esc(title)}">
<meta property="og:description" content="{esc(description)}">
<meta property="og:url" content="{esc(canonical)}">
<meta property="og:image" content="{esc(image)}">
<meta property="og:image:alt" content="{esc(image_alt)}">
<meta property="og:locale" content="en_US">
<meta name="twitter:card" content="summary">
<meta name="twitter:title" content="{esc(title)}">
<meta name="twitter:description" content="{esc(description)}">
<meta name="twitter:image" content="{esc(image)}">
<meta name="twitter:image:alt" content="{esc(image_alt)}">
<link rel="icon" href="/favicon.ico" sizes="48x48">
<link rel="icon" href="/favicon.svg" type="image/svg+xml" sizes="any">
<link rel="apple-touch-icon" href="/apple-touch-icon.png">
<script type="application/ld+json">
{json.dumps(jsonld, ensure_ascii=False, indent=1)}
</script>
<style>{STYLE}</style>
</head>
<body>
<header class="site">
  <a href="/">Ash Stu</a>
  <nav aria-label="Site"><a href="/#music">Listen</a></nav>
</header>
{body}
<footer><p>Lyrics © {ARTIST} ({ARTIST_FULL}). Published by the artist at <a href="{SITE}/">ashstu.art</a>.</p></footer>
</body>
</html>
"""


ROBOTS_META = '<meta name="robots" content="index, follow, max-snippet:-1, max-image-preview:large, max-video-preview:-1"/>\n'


ARTIST_NODE = {'@type': ['MusicGroup', 'Person'], '@id': f'{SITE}/#artist', 'name': ARTIST,
               'alternateName': ARTIST_FULL, 'url': f'{SITE}/', 'genre': GENRE}


HOME_HTML = None
def _neighbours(songs, s):
    i = songs.index(s); out = []
    # (each link shows an arrow as well as its words: every control has a picture and a word)
    arrow = lambda d: f'<svg class="spn-arrow" aria-hidden="true" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round"><path d="{d}"/></svg>'
    if i > 0: out.append(f'<a href="/lyrics/{songs[i-1]["slug"]}/" rel="prev">{arrow("M19 12H5M11 6l-6 6 6 6")}Previous: {esc(songs[i-1]["title"])} lyrics</a>')
    if i < len(songs) - 1: out.append(f'<a href="/lyrics/{songs[i+1]["slug"]}/" rel="next">Next: {esc(songs[i+1]["title"])} lyrics{arrow("M5 12h14M13 6l6 6-6 6")}</a>')
    return '<nav class="song-page-nav" aria-label="More lyrics">' + ''.join(out) + '</nav>\n' if out else ''


def iso_duration(rel_path):
    """The audio file's running time as ISO 8601 (PT3M41S), or '' if it cannot be read
    (no file, or the mutagen library is not installed where this runs)."""
    try:
        from mutagen.mp3 import MP3
        secs = int(round(MP3(os.path.join(ROOT, rel_path)).info.length))
        return f'PT{secs // 60}M{secs % 60}S' if secs > 0 else ''
    except Exception:
        return ''


def clone_page(title, description, url, art, alt, jsonld, extra, deep_key, song_title, article='',
               deep_meta='deep-song', og_type='music.song', skip=('#song', 'Skip to the song'), early=None):
    """A song's page is the whole site with that song opened: the built
    homepage (index.html) with this song's title, description, canonical
    address, Open Graph / Twitter tags and JSON-LD, <base href="/"> so every
    asset and data file resolves from the root, a small script so in-page
    links (#music, #epk...) scroll here instead of loading the homepage, and
    <meta name="deep-song"> for the homepage script, which opens the song's
    tracklist and lyrics and loads it in the player. Its lyrics are also
    open in the page's own HTML. Returns None if index.html isn't built."""
    global HOME_HTML
    if HOME_HTML is None:
        hp = os.path.join(ROOT, 'index.html')
        HOME_HTML = open(hp, encoding='utf-8').read() if os.path.isfile(hp) else ''
    h = HOME_HTML
    if not h or not deep_key:
        return None
    def sub(pattern, repl, text):
        out, n = re.subn(pattern, lambda m: repl, text, count=1)
        return out
    a = esc(title); d = esc(description)
    h = sub(r'<title>.*?</title>', f'<title>{a}</title>', h)
    h = sub(r'<meta name="description" content="[^"]*"\s*/?>', f'<meta name="description" content="{d}"/>', h)
    h = sub(r'<link rel="canonical" href="[^"]*"\s*/?>', f'<link rel="canonical" href="{url}"/>', h)
    h = sub(r'<meta property="og:title" content="[^"]*"\s*/?>', f'<meta property="og:title" content="{a}"/>', h)
    h = sub(r'<meta property="og:description" content="[^"]*"\s*/?>', f'<meta property="og:description" content="{d}"/>', h)
    h = sub(r'<meta property="og:type" content="[^"]*"\s*/?>', f'<meta property="og:type" content="{og_type}"/>', h)
    h = sub(r'<meta property="og:url" content="[^"]*"\s*/?>', f'<meta property="og:url" content="{url}"/>', h)
    page_art = art
    art = share_art(art)   # link previews get the JPEG copy; the page itself and its structured data keep the WebP
    h = sub(r'<meta property="og:image" content="[^"]*"\s*/?>', f'<meta property="og:image" content="{esc(art)}"/>', h)
    # the image tags must describe the cover now in og:image, not the homepage's social card
    w, hgt, mime = image_facts(art)
    h = sub(r'<meta property="og:image:type" content="[^"]*"\s*/?>', f'<meta property="og:image:type" content="{mime}"/>' if mime else '', h)
    h = sub(r'<meta property="og:image:width" content="[^"]*"\s*/?>', f'<meta property="og:image:width" content="{w}"/>' if w else '', h)
    h = sub(r'<meta property="og:image:height" content="[^"]*"\s*/?>', f'<meta property="og:image:height" content="{hgt}"/>' if hgt else '', h)
    h = sub(r'<meta property="og:image:alt" content="[^"]*"\s*/?>', f'<meta property="og:image:alt" content="{esc(alt)}"/>', h)
    h = sub(r'<meta name="twitter:image:alt" content="[^"]*"\s*/?>', f'<meta name="twitter:image:alt" content="{esc(alt)}"/>', h)
    h = sub(r'<meta name="twitter:image" content="[^"]*"\s*/?>', f'<meta name="twitter:image" content="{esc(art)}"/>', h)
    # a square cover on the wide card is cropped to a strip (the face cut in half); the small card shows it whole
    h = sub(r'<meta name="twitter:card" content="[^"]*"\s*/?>', '<meta name="twitter:card" content="summary"/>', h)
    art = page_art
    h = sub(r'<meta name="twitter:title" content="[^"]*"\s*/?>', f'<meta name="twitter:title" content="{a}"/>', h)
    h = sub(r'<meta name="twitter:description" content="[^"]*"\s*/?>', f'<meta name="twitter:description" content="{d}"/>', h)
    head_add = ('<base href="/"/>\n'
                f'<meta name="{deep_meta}" content="{esc(deep_key)}"/>\n' + extra +
                '<script type="application/ld+json">' + json.dumps(jsonld, ensure_ascii=False).replace('</', '<\\/') + '</script>\n'
                # with <base href="/">, "#music" would point at the homepage:
                # keep in-page links scrolling on this page
                '<script>addEventListener("click",function(e){if(e.defaultPrevented||e.button||e.metaKey||e.ctrlKey||e.shiftKey)return;'
                'var a=e.target.closest&&e.target.closest("a[href^=\'#\']");if(!a||a.target)return;e.preventDefault();'
                'var id=decodeURIComponent(a.getAttribute("href").slice(1)),t=id&&document.getElementById(id);'
                'var sm=matchMedia("(prefers-reduced-motion: reduce)").matches?"auto":"smooth";'
                't?t.scrollIntoView({behavior:sm,block:"start"}):scrollTo({top:0,behavior:sm});'
                # ...and move keyboard focus there too. Without this the "Skip" link scrolled the page but left focus on
                # itself, so the next Tab went through the whole toolbar anyway: it skipped nothing for keyboard users.
                'if(t){if(!t.hasAttribute("tabindex"))t.setAttribute("tabindex","-1");t.focus({preventScroll:true});}});</script>\n')
    h = sub(r'(<meta charset="[^"]*"\s*/?>)', None, h) if False else re.sub(r'(<meta charset="[^"]*"\s*/?>)', lambda m: m.group(1) + '\n' + head_add, h, count=1)
    # On a song's page the skip link goes to the song itself (the page is the whole site; the song is what was asked for).
    if article:
        h = re.sub(r'<a href="#main" class="skip">(.*?)Skip to content</a>', lambda m: f'<a href="{skip[0]}" class="skip">{m.group(1)}{skip[1]}</a>', h, count=1)
    # the song's lyrics already open in the static HTML
    if song_title:
        h = h.replace(f'{esc(song_title)}<details class="rel-lyrics-static">', f'{esc(song_title)}<details class="rel-lyrics-static" open>', 1)
    if article:
        # This page is about one song. Its words sit in an <article> of their
        # own under the page's only <h1>; the homepage's copy of every other
        # song's words (static <details> and the all-songs JSON-LD) is left
        # out, so 36 song pages are not 36 near-copies of the homepage.
        h = re.sub(r'<details class="rel-lyrics-static"[^>]*>.*?</details>', '', h, flags=re.S)
        h = re.sub(r'<script type="application/ld\+json" id="lyrics-ld">.*?</script>\n?', '', h, count=1, flags=re.S)
        # The homepage's own structured data describes its videos and its contact section; a song page is about
        # neither, so those entries are left out here (the artist, the site and the album stay).
        def _trim(m):
            try:
                j = json.loads(m.group(1))
                j['@graph'] = [n for n in j['@graph'] if n.get('@type') not in ('VideoObject', 'ContactPage')]
                return '<script type="application/ld+json">' + json.dumps(j, ensure_ascii=False).replace('</', '<\\/') + '</script>'
            except Exception:
                return m.group(0)
        _home = re.search(r'<script type="application/ld\+json">(.*?)</script>', HOME_HTML, flags=re.S)
        if _home:
            h = h.replace(_home.group(0), _trim(_home), 1)
        h, n1 = re.subn(r'<h1 class="hero-name">(.*?)</h1>', lambda m: '<p class="hero-name">' + m.group(1) + '</p>', h, count=1, flags=re.S)
        h, n2 = re.subn(r'(<section[^>]*\bid="music"[^>]*>)', lambda m: m.group(1) + '\n' + article, h, count=1)
        if not (n1 and n2):
            return None
    if early:
        # Go to the target as soon as the page has read that far, before the first screen is even drawn. (Waiting for
        # the page to finish loading showed the top of the site for about two seconds on a slow phone, then jumped.)
        # Everything above the target is already read and its pictures carry their sizes, so the place is right; the
        # page script lands once more after the fonts arrive. A visitor who has scrolled meanwhile is left alone.
        jump = ('<script>(function(){var t=document.getElementById(' + json.dumps(early) + ');if(!t||scrollY>2)return;'
                'try{history.scrollRestoration="manual"}catch(e){}var d=document.documentElement,b=d.style.scrollBehavior;'
                'd.style.scrollBehavior="auto";t.scrollIntoView({block:"start"});d.style.scrollBehavior=b;})()</script>')
        h = re.sub(r'(<section[^>]*\bid="' + re.escape(early) + r'"[^>]*>)', lambda m: m.group(1) + jump, h, count=1)
    return h


def share_art(url):
    """The picture link previews should use for a cover: a 1000px JPEG in Images/share/.

    The covers on the page are small WebP files, which several apps that draw link previews (LinkedIn, some
    chat apps and older scrapers) cannot read, so a shared song link showed no picture there. The JPEG is made
    once from the full-size PNG beside the WebP (needs pillow) and committed; without it the WebP is used as before.
    """
    rel = urllib.parse.unquote(url.replace(SITE + '/', '', 1))
    stem = os.path.splitext(os.path.basename(rel))[0]
    out_rel = 'Images/share/' + re.sub(r'[^a-z0-9]+', '-', stem.lower()).strip('-') + '.jpg'
    out = os.path.join(ROOT, out_rel)
    if not os.path.isfile(out):
        src = os.path.join(ROOT, os.path.splitext(rel)[0] + '.png')
        try:
            from PIL import Image
            with Image.open(src) as im:
                im = im.convert('RGB').resize((1000, 1000), Image.LANCZOS)   # 1000px at quality 80 keeps each under 300 KB, the limit some chat apps set for preview pictures
                os.makedirs(os.path.dirname(out), exist_ok=True)
                im.save(out, 'JPEG', quality=80, optimize=True, progressive=True)
        except Exception:
            return url
    return SITE + '/' + urllib.parse.quote(out_rel)


def image_facts(url):
    """(width, height, mime type) of a site image given its absolute URL."""
    path = os.path.join(ROOT, urllib.parse.unquote(url.replace(SITE + '/', '', 1)))
    mime = {'.webp': 'image/webp', '.png': 'image/png', '.jpg': 'image/jpeg', '.jpeg': 'image/jpeg'}.get(os.path.splitext(path)[1].lower(), '')
    try:
        from PIL import Image
        with Image.open(path) as im:
            return im.size[0], im.size[1], mime
    except Exception:
        pass
    # No pillow (the update-content GitHub Action does not install it): read the size from the file's own header, so
    # the pages come out the same there as on a computer that has it. (Without this every Action run took the
    # og:image width and height out of all the lyric pages, and the next local build put them back.)
    try:
        import struct
        with open(path, 'rb') as f:
            head = f.read(32)
            if head[:8] == b'\x89PNG\r\n\x1a\n':
                w, h = struct.unpack('>II', head[16:24]); return w, h, mime
            if head[:4] == b'RIFF' and head[8:12] == b'WEBP':
                kind = head[12:16]
                if kind == b'VP8X': return 1 + int.from_bytes(head[24:27], 'little'), 1 + int.from_bytes(head[27:30], 'little'), mime
                if kind == b'VP8 ': return struct.unpack('<H', head[26:28])[0] & 0x3FFF, struct.unpack('<H', head[28:30])[0] & 0x3FFF, mime
                if kind == b'VP8L':
                    b = int.from_bytes(head[21:25], 'little'); return 1 + (b & 0x3FFF), 1 + ((b >> 14) & 0x3FFF), mime
            if head[:2] == b'\xff\xd8':
                f.seek(2)
                while True:
                    m = f.read(4)
                    if len(m) < 4 or m[0] != 0xFF: break
                    size = struct.unpack('>H', m[2:4])[0]
                    if 0xC0 <= m[1] <= 0xCF and m[1] not in (0xC4, 0xC8, 0xCC):
                        d = f.read(5); h, w = struct.unpack('>HH', d[1:5]); return w, h, mime
                    f.seek(size - 2, 1)
    except Exception:
        pass
    return None, None, mime


def share_thumb(rel_path, slug):
    """The picture link previews should use for a video: a 1280px-wide JPEG in Images/share/ made once from the
    full-size PNG beside the WebP thumbnail (needs pillow) and committed; without it the WebP is used."""
    out_rel = 'Images/share/video-' + slug + '.jpg'
    out = os.path.join(ROOT, out_rel)
    if not os.path.isfile(out):
        src = os.path.join(ROOT, os.path.splitext(rel_path)[0] + '.png')
        try:
            from PIL import Image
            with Image.open(src) as im:
                im = im.convert('RGB')
                if im.size[0] > 1280: im = im.resize((1280, round(1280 * im.size[1] / im.size[0])), Image.LANCZOS)
                os.makedirs(os.path.dirname(out), exist_ok=True)
                im.save(out, 'JPEG', quality=82, optimize=True, progressive=True)
        except Exception:
            return SITE + '/' + urllib.parse.quote(rel_path)
    return SITE + '/' + urllib.parse.quote(out_rel)


def vtt_lines(rel_path):
    """The words of a caption file, one entry per caption, in order."""
    try:
        text = open(os.path.join(ROOT, rel_path), encoding='utf-8').read().replace('\r', '')
    except OSError:
        return []
    out = []
    for block in re.split(r'\n\n+', text):
        lines = block.split('\n')
        i = next((k for k, l in enumerate(lines) if '-->' in l), -1)
        if i < 0:
            continue
        words = re.sub(r'\s+', ' ', re.sub(r'<[^>]+>', '', ' '.join(lines[i + 1:]))).strip()
        if words:
            out.append(words)
    return out


def video_seconds(rel_path):
    """Running time of a video in whole seconds, or 0 (no file, or the mutagen library is not installed here)."""
    try:
        from mutagen.mp4 import MP4
        return int(round(MP4(os.path.join(ROOT, rel_path)).info.length))
    except Exception:
        return 0


def main():
    with open(os.path.join(ROOT, 'releases.json'), encoding='utf-8') as f:
        releases = json.load(f)
    with open(os.path.join(ROOT, 'lyrics.json'), encoding='utf-8') as f:
        lyrics = json.load(f)
    # Songs that have a video on the site: their pages offer it (for a song that is not released yet it is the only
    # way to hear it). Matched by title.
    try:
        with open(os.path.join(ROOT, 'videos.json'), encoding='utf-8') as f:
            videos = {v['title'].strip().lower(): v for v in json.load(f) if v.get('title')}
    except Exception:
        videos = {}
    os.makedirs(OUT, exist_ok=True)

    songs, used = [], set()
    for rel in releases:
        rdate = release_date(rel['name'])
        for i, t in enumerate(rel.get('tracks', [])):
            entry = lyrics.get(t['file'])
            if not entry or not entry.get('lines'):
                continue
            slug = slugify(t['title'])
            if slug in used:
                slug = f"{slug}-{slugify(rel['name'])}"
            used.add(slug)
            songs.append({'key': t['file'], 'title': t['title'], 'slug': slug, 'release': rel, 'position': t.get('num', i + 1),
                          'total': len(rel.get('tracks', [])) + len(rel.get('upcoming', [])),
                          'date': rdate, 'verses': stanzas(entry, t['file'])})
        # Songs not out yet (upcoming.txt) whose words are in lyrics.txt:
        # a lyrics page too, marked unreleased, with nothing to play.
        for u in rel.get('upcoming', []):
            entry = lyrics.get(u.get('lyrics') or '')
            if not entry or not entry.get('lines'):
                continue
            slug = slugify(u['title'])
            if slug in used:
                slug = f"{slug}-{slugify(rel['name'])}"
            used.add(slug)
            songs.append({'key': u.get('lyrics'), 'title': u['title'], 'slug': slug, 'release': rel, 'position': u['num'],
                          'total': len(rel.get('tracks', [])) + len(rel.get('upcoming', [])),
                          'date': None, 'verses': stanzas(entry, None),
                          'unreleased': True, 'traditional': bool(u.get('traditional'))})
    songs.sort(key=lambda s: (releases.index(s['release']), s['position']))
    # one-word identifiers (scripts/song_keys.py), assigned across every song in the catalogue
    every = [x['title'] for rel in releases for x in rel.get('tracks', []) + rel.get('upcoming', [])]
    KEYS, _ = song_keys.assign(every)
    for s in songs:
        s['word'] = KEYS[s['title']]

    written = []
    ALTS = cover_alts()
    for s in songs:
        rel = s['release']
        url = f"{SITE}/lyrics/{s['slug']}/"
        art_path = '/' + rel['art'].replace(' ', '%20') if rel.get('art') else '/Images/social-card.png'
        art = SITE + art_path   # absolute for Open Graph / JSON-LD
        text = '\n\n'.join('\n'.join(v) for v in s['verses'])
        # 'layout 2' is part of the hash: bump it when the page template changes, so <lastmod> tells crawlers to come back
        digest = hashlib.sha256(('layout 3' + s['title'] + rel['name'] + text).encode()).hexdigest()[:16]
        album_url = f"{SITE}/albums/{slugify(rel['name'])}/"   # the album's own page (made further down)
        path = os.path.join(OUT, s['slug'], 'index.html')
        old_hash, old_date = previous_meta(path)
        modified = old_date if (old_hash == digest and old_date) else TODAY
        first = s['verses'][0][0] if s['verses'] else ''
        kind = rel.get('type') or 'Album'
        year = (s['date'] or '')[:4]
        trad, unrel = s.get('traditional'), s.get('unreleased')
        who = f'the traditional song “{s["title"]}”, arranged by {ARTIST}' if trad else f'“{s["title"]}” by {ARTIST}'
        description = (f"Full lyrics to {who}, from the {kind.lower()} {rel['name']}"
                       f"{' (not released yet)' if unrel else (' (' + year + ')' if year else '')}. Begins: “{first}”")
        if len(description) > 160:
            description = description[:159].rsplit(' ', 1)[0].rstrip(' ,.;:“') + '…'
        title = f"{s['title']} Lyrics | {ARTIST}"
        listen = []
        if rel.get('apple'):
            listen.append(f'<li><a href="{esc(rel["apple"])}" rel="noopener">Apple Music</a></li>')
        if rel.get('spotify'):
            listen.append(f'<li><a href="{esc(rel["spotify"])}" rel="noopener">Spotify</a></li>')
        for key, store in (('ytmusic', 'YouTube Music'), ('deezer', 'Deezer')):
            if rel.get(key):
                listen.append(f'<li><a href="{esc(rel[key])}" rel="noopener">{store}</a></li>')
        listen.append('<li><a href="/#music">Play on ashstu.art</a></li>')
        if unrel:
            listen = ['<li>Not released yet</li>']
        verses_html = '\n'.join('<p>' + '<br>\n'.join(esc(l) for l in v) + '</p>' for v in s['verses'])
        others = [o for o in songs if o['release'] is rel and o is not s]
        more = ''
        if others:
            more = ('<nav class="more" aria-label="More from this release"><p>More lyrics from '
                    f'{esc(rel["name"])}: ' + ', '.join(f'<a href="/lyrics/{o["slug"]}/">{esc(o["title"])}</a>' for o in others) + '</p></nav>')
        alt = ALTS.get(rel.get('art') or '', f"{kind} cover: {rel['name']}")
        date_row = (f'<tr><th scope="row">Release date</th><td><time datetime="{s["date"]}">{human_date(s["date"])}</time></td></tr>'
                    if s['date'] else '')
        body = f"""<main>
<article>
  <nav class="crumbs" aria-label="Breadcrumb">{esc(rel['name'])}</nav>
  <header class="song-head">
    <img src="{esc(art_path)}" alt="{esc(alt)}" width="288" height="288">
    <hgroup>
      <h1>{esc(s['title'])}</h1>
      <p class="byline">{'Traditional, arranged by' if trad else 'Lyrics by'} <a href="/">{ARTIST}</a> · track {s['position']} of {s['total']} on <cite>{esc(rel['name'])}</cite>{' · not released yet' if unrel else ''}</p>
    </hgroup>
  </header>
  <section class="lyrics" aria-labelledby="lyrics-heading">
    <h2 id="lyrics-heading">Lyrics</h2>
{verses_html}
  </section>
  <section aria-labelledby="details-heading">
    <h2 id="details-heading">Song details</h2>
    <table>
      <caption>Facts about “{esc(s['title'])}”</caption>
      <tbody>
        <tr><th scope="row">Song title</th><td>{esc(s['title'])}</td></tr>
        <tr><th scope="row">Artist</th><td>{ARTIST} ({ARTIST_FULL})</td></tr>
        <tr><th scope="row">Songwriter and lyricist</th><td>{'Traditional (arranged by ' + ARTIST + ')' if trad else ARTIST + ' (' + ARTIST_FULL + ')'}</td></tr>
        <tr><th scope="row">Release</th><td>{esc(rel['name'])} ({esc(kind.lower())})</td></tr>
        <tr><th scope="row">Track number</th><td>{s['position']} of {s['total']} tracks</td></tr>
        {date_row}
        <tr><th scope="row">Genre</th><td>{GENRE}</td></tr>
        <tr><th scope="row">Language</th><td>English</td></tr>
        <tr><th scope="row">Lyrics length</th><td>{sum(len(v) for v in s['verses'])} lines in {len(s['verses'])} verses</td></tr>
      </tbody>
    </table>
  </section>
  <section aria-labelledby="listen-heading">
    <h2 id="listen-heading">Listen</h2>
    <ul class="listen">{''.join(listen)}</ul>
  </section>
  {more}
</article>
</main>"""
        comp_id = url + '#composition'
        dur = '' if unrel else iso_duration(s.get('key'))   # running time, e.g. PT3M41S (a hard fact for crawlers; read from the audio file)
        writer = {'@type': 'Person', 'name': 'Traditional'} if trad else {'@id': f'{SITE}/#artist'}
        jsonld = {'@context': 'https://schema.org', '@graph': [
            ARTIST_NODE,
            *([] if unrel else [{'@type': 'MusicRecording', '@id': url + '#recording', 'name': s['title'], 'url': url,
             'byArtist': {'@id': f'{SITE}/#artist'}, 'inLanguage': 'en', 'genre': GENRE,
             **({'datePublished': s['date']} if s['date'] else {}),
             'inAlbum': {'@type': 'MusicAlbum', '@id': album_url + '#album', 'name': rel['name'], 'url': album_url, 'image': art,
                         'albumReleaseType': 'SingleRelease' if kind == 'Single' else 'AlbumRelease', 'byArtist': {'@id': f'{SITE}/#artist'}},
             'position': s['position'], 'recordingOf': {'@id': comp_id}, 'isAccessibleForFree': True,
             **({'duration': dur} if dur else {}),
             'audio': {'@type': 'AudioObject', 'contentUrl': SITE + '/' + urllib.parse.quote(s['key']), 'encodingFormat': 'audio/mpeg', **({'duration': dur} if dur else {})}}]),
            {'@type': 'MusicComposition', '@id': comp_id, 'name': s['title'], 'url': url, 'inLanguage': 'en', 'genre': GENRE,
             'identifier': s['word'], 'keywords': f"{ARTIST} {s['word']}", 'sameAs': f"{SITE}/{s['word']}/",
             'composer': writer, 'lyricist': writer,
             **({'arranger': {'@id': f'{SITE}/#artist'}} if trad else {}),
             **({'datePublished': s['date']} if s['date'] else {}),
             'lyrics': {'@type': 'CreativeWork', 'inLanguage': 'en', 'text': text},
             **({} if trad else {'copyrightHolder': {'@id': f'{SITE}/#artist'}}),
             **({'recordedAs': {'@id': url + '#recording'}} if not unrel else {}),
             'dateModified': modified},
            {'@type': 'WebPage', '@id': url, 'url': url, 'name': title, 'inLanguage': 'en',
             'dateModified': modified, 'mainEntity': {'@id': comp_id}, 'primaryImageOfPage': art,
             'breadcrumb': {'@type': 'BreadcrumbList', 'itemListElement': [
                 {'@type': 'ListItem', 'position': 1, 'name': ARTIST, 'item': f'{SITE}/'},
                 {'@type': 'ListItem', 'position': 2, 'name': s['title'], 'item': url}]}},
        ]}
        extra = (f'<meta name="lyrics-hash" content="{digest}">\n'
                 f'<meta property="article:modified_time" content="{modified}">\n'
                 f'<meta property="music:musician" content="{SITE}/">\n')
        os.makedirs(os.path.dirname(path), exist_ok=True)
        deep_key = s.get('key')
        year_note = f' ({year})' if year and not unrel else ''
        vid = videos.get(s['title'].strip().lower())
        # A plain link to YouTube that works with scripts off; with scripts on, index-src.html opens the site's own
        # video viewer instead (data-song-video).
        watch = (f'<p class="song-page-watch"><a class="vid-yt" href="/videos/{slugify(vid["title"])}/" data-song-video="{esc(vid["title"])}">'
                 f'<span class="pt pt--youtube" aria-hidden="true"></span>Watch the video</a></p>\n') if vid and vid.get('youtube') else ''
        article = (f'<article class="song-page" id="song" aria-labelledby="song-h" lang="en">\n'
                   f'<header class="song-page-head">\n<p class="song-page-kicker">Lyrics</p>\n<h1 id="song-h">{esc(s["title"])}</h1>\n'
                   f'<p class="song-page-by">{"Traditional, arranged by" if trad else "Written and performed by"} <a href="/">{ARTIST}</a>'
                   f' · track {s["position"]} of {s["total"]} on <cite><a href="/albums/{slugify(rel["name"])}/">{esc(rel["name"])}</a></cite>{year_note}{" · not released yet" if unrel else ""}</p>\n{watch}</header>\n'
                   f'<div class="song-page-lyrics" id="song-lyrics">\n<h2 class="sr-only">{esc(s["title"])}: full lyrics</h2>\n{verses_html}\n</div>\n'
                   f'<p class="song-page-foot">Lyrics © {ARTIST} ({ARTIST_FULL}).</p>\n'
                   # each song links to its neighbours, so a crawler (and a reader) can walk the whole set from any page
                   + _neighbours(songs, s) +
                   f'<p class="song-page-short">Short link: <a href="/{s["word"]}/">ashstu.art/{s["word"]}</a></p>\n</article>')
        html = clone_page(title, description, url, art, alt, jsonld, extra + ('' if 'name="robots"' in (HOME_HTML or open(os.path.join(ROOT, 'index.html'), encoding='utf-8').read()) else ROBOTS_META), deep_key, s['title'], article)
        with open(path, 'w', encoding='utf-8') as f:
            f.write(html or page(title, description, url, 'music.song', art, alt, body, jsonld, extra))
        written.append((url, modified))


    # ── Album pages ──────────────────────────────────────────────────────────────────────────────────────────────
    # /albums/<album>/ is to an album what /lyrics/<song>/ is to a song: what a search for the album lands on. It is
    # the whole site with <meta name="deep-album"> naming the release; the page script (openDeepAlbum in
    # index-src.html) goes to that album's card, opens its tracklist, puts its first song in the player ready for Play
    # and rings the card for a few seconds. The album's facts and track list are also in the page's own HTML, under
    # the page's only <h1>, with each song linking to its lyrics page.
    ALB = os.path.join(ROOT, 'albums')
    os.makedirs(ALB, exist_ok=True)
    albums_written, album_slugs = [], {}
    for rel in releases:
        if not (rel.get('tracks') or rel.get('upcoming')):
            continue
        aslug = slugify(rel['name'])
        album_slugs[rel['name']] = aslug
    for rel in releases:
        aslug = album_slugs.get(rel['name'])
        if not aslug:
            continue
        url = f'{SITE}/albums/{aslug}/'
        kind = rel.get('type') or 'Album'
        rdate = release_date(rel['name'])
        year = (rdate or '')[:4]
        art_path = '/' + rel['art'].replace(' ', '%20') if rel.get('art') else '/Images/social-card.png'
        art = SITE + art_path
        alt = ALTS.get(rel.get('art') or '', f"{kind} cover: {rel['name']}")
        rows = [(t.get('num', i + 1), t['title'], t, False) for i, t in enumerate(rel.get('tracks', []))]
        rows += [(u['num'], u['title'], u, True) for u in rel.get('upcoming', [])]
        rows.sort(key=lambda r: r[0])
        song_of = {x['title']: x for x in songs if x['release'] is rel}
        n_out, n_all = len(rel.get('tracks', [])), len(rows)
        waiting = n_all - n_out
        names = [r[1] for r in rows]
        description = (f"{rel['name']}, {'an' if kind[:1].lower() in 'aeiou' else 'a'} {kind.lower()} by {ARTIST}"
                       f"{' (' + year + ')' if year else ''}: {n_all} track{'s' if n_all != 1 else ''}"
                       f"{', ' + str(n_out) + ' out now' if waiting and n_out else ''}. Listen, read the lyrics and download. Tracks: " + ', '.join(names))
        if len(description) > 160:
            description = description[:159].rsplit(' ', 1)[0].rstrip(' ,.;:') + '…'
        title = f"{rel['name']} | {kind} by {ARTIST}"
        digest = hashlib.sha256(('album layout 1' + rel['name'] + kind + (rdate or '') + '|'.join(f'{n}{t}{u}' for n, t, _, u in rows)
                                 + (rel.get('apple') or '') + (rel.get('spotify') or '')).encode()).hexdigest()[:16]
        path = os.path.join(ALB, aslug, 'index.html')
        old_hash, old_date = previous_meta(path)
        modified = old_date if (old_hash == digest and old_date) else TODAY
        items, ld_tracks = [], []
        for num, ttl, t, unrel in rows:
            sg = song_of.get(ttl)
            label = f'<a href="/lyrics/{sg["slug"]}/">{esc(ttl)}</a>' if sg else esc(ttl)
            items.append(f'<li value="{num}">{label}{" (not released yet)" if unrel else ""}</li>')
            if not unrel:
                dur = iso_duration(t['file'])
                ld_tracks.append({'@type': 'ListItem', 'position': num, 'item': {
                    '@type': 'MusicRecording', 'name': ttl, 'position': num, 'byArtist': {'@id': f'{SITE}/#artist'},
                    **({'url': f"{SITE}/lyrics/{sg['slug']}/", '@id': f"{SITE}/lyrics/{sg['slug']}/#recording"} if sg else {}),
                    **({'duration': dur} if dur else {})}})
        listen = []
        if rel.get('apple'): listen.append(f'<a href="{esc(rel["apple"])}" rel="noopener">Apple Music</a>')
        if rel.get('spotify'): listen.append(f'<a href="{esc(rel["spotify"])}" rel="noopener">Spotify</a>')
        for key, store in (('ytmusic', 'YouTube Music'), ('deezer', 'Deezer')):
            if rel.get(key): listen.append(f'<a href="{esc(rel[key])}" rel="noopener">{store}</a>')
        listen_line = (' · Listen on ' + (', '.join(listen[:-1]) + ' and ' + listen[-1] if len(listen) > 1 else listen[0])) if listen else ''
        status = ''
        if waiting and n_out: status = f' · {n_out} of {n_all} tracks out now'
        elif waiting: status = ' · not released yet'
        others = [o for o in releases if o is not rel and album_slugs.get(o['name'])]
        more = ('<nav class="song-page-nav" aria-label="More albums">'
                + ''.join(f'<a href="/albums/{album_slugs[o["name"]]}/">{esc(o["name"])}</a>' for o in others) + '</nav>\n') if others else ''
        article = (f'<article class="song-page album-page" id="album" aria-labelledby="album-h" lang="en">\n'
                   f'<header class="song-page-head">\n<p class="song-page-kicker">{esc(kind)}</p>\n<h1 id="album-h">{esc(rel["name"])}</h1>\n'
                   f'<p class="song-page-by">By <a href="/">{ARTIST}</a> · {n_all} track{"s" if n_all != 1 else ""}'
                   f'{" · " + year if year else ""}{status}{listen_line}</p>\n</header>\n'
                   f'<div class="song-page-lyrics album-page-tracks" id="album-tracks">\n<h2 class="sr-only">{esc(rel["name"])}: track list</h2>\n'
                   f'<ol>\n' + '\n'.join(items) + '\n</ol>\n</div>\n'
                   + more + '</article>')
        # The owner does not want this block on the page: the album itself (its card, opened and ringed) is the page.
        # It stays in the HTML for crawlers and screen readers and is hidden from sight by the stylesheet (.album-page),
        # so its links are taken out of the Tab order (focus must never land on something that cannot be seen).
        article = article.replace('<a href=', '<a tabindex="-1" href=')
        album_id = url + '#album'
        jsonld = {'@context': 'https://schema.org', '@graph': [
            ARTIST_NODE,
            {'@type': 'MusicAlbum', '@id': album_id, 'name': rel['name'], 'url': url, 'image': art, 'inLanguage': 'en', 'genre': GENRE,
             'byArtist': {'@id': f'{SITE}/#artist'}, 'albumProductionType': 'SelfReleasedAlbum',
             'albumReleaseType': {'Single': 'SingleRelease', 'EP': 'EPRelease'}.get(kind, 'AlbumRelease'),
             **({'datePublished': rdate} if rdate else {}),
             'numTracks': n_all,
             **({'sameAs': [u for u in (rel.get('apple'), rel.get('spotify'), rel.get('ytmusic'), rel.get('deezer')) if u]} if (rel.get('apple') or rel.get('spotify') or rel.get('ytmusic') or rel.get('deezer')) else {}),
             **({'track': {'@type': 'ItemList', 'numberOfItems': len(ld_tracks), 'itemListElement': ld_tracks}} if ld_tracks else {}),
             'dateModified': modified},
            {'@type': 'WebPage', '@id': url, 'url': url, 'name': title, 'inLanguage': 'en', 'dateModified': modified,
             'mainEntity': {'@id': album_id}, 'primaryImageOfPage': art,
             'breadcrumb': {'@type': 'BreadcrumbList', 'itemListElement': [
                 {'@type': 'ListItem', 'position': 1, 'name': ARTIST, 'item': f'{SITE}/'},
                 {'@type': 'ListItem', 'position': 2, 'name': rel['name'], 'item': url}]}},
        ]}
        extra = (f'<meta name="album-hash" content="{digest}">\n'
                 f'<meta property="article:modified_time" content="{modified}">\n'
                 f'<meta property="music:musician" content="{SITE}/">\n')
        html = clone_page(title, description, url, art, alt, jsonld,
                          extra + ('' if 'name="robots"' in (HOME_HTML or open(os.path.join(ROOT, 'index.html'), encoding='utf-8').read()) else ROBOTS_META),
                          rel['name'], None, article, deep_meta='deep-album', og_type='music.album', early='music', skip=('#album', 'Skip to the album'))
        if not html:
            continue   # index.html is not built yet: nothing to clone (the next build makes the page)
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, 'w', encoding='utf-8') as f:
            f.write(html)
        albums_written.append((url, modified, rel['name']))
    # Remove pages for albums that no longer exist (only folders this script made).
    live_albums = {u.rstrip('/').rsplit('/', 1)[-1] for u, _, _ in albums_written}
    for d in os.listdir(ALB):
        pth = os.path.join(ALB, d, 'index.html')
        if d not in live_albums and os.path.isfile(pth) and 'name="album-hash"' in open(pth, encoding='utf-8').read(4000):
            os.remove(pth)
            try:
                os.rmdir(os.path.join(ALB, d))
            except OSError:
                pass

    # ── Video pages ──────────────────────────────────────────────────────────────────────────────────────────────
    # /videos/<video>/ is a video's own page: what a search for the video lands on, and a link to share. It is the
    # whole site with <meta name="deep-video"> naming the video; the page script (openDeepVideo in index-src.html)
    # goes to the Videos section, rings that video and opens it in the viewer, ready to play. The video's facts and
    # its words (from its caption file) are in the page's own HTML under the page's only <h1>, out of sight like an
    # album page's heading block. (The video files themselves live in /Video Files/, so /videos/ is free for the pages:
    # a folder named Videos/ beside it could not exist on a Mac or Windows copy of the site.) The old addresses -
    # /watch/<video>/ and /music-videos/ - are kept as small pages that send visitors on to the new ones.
    WATCH = os.path.join(ROOT, 'videos')
    os.makedirs(WATCH, exist_ok=True)
    try:
        with open(os.path.join(ROOT, 'videos.json'), encoding='utf-8') as f:
            video_list = [v for v in json.load(f) if v.get('title') and v.get('file')]
    except Exception:
        video_list = []
    # upload dates and YouTube embeds are kept in the home page's own structured data: reuse those entries
    home_nodes = {}
    try:
        hp = HOME_HTML or open(os.path.join(ROOT, 'index.html'), encoding='utf-8').read()
        for m in re.finditer(r'<script type="application/ld\+json"[^>]*>(.*?)</script>', hp, flags=re.S):
            for n in (json.loads(m.group(1)).get('@graph') or []):
                if n.get('@type') == 'VideoObject' and n.get('name'):
                    home_nodes[n['name'].strip().lower()] = n
    except Exception:
        pass
    song_by_title = {x['title'].strip().lower(): x for x in songs}
    vslugs, videos_written = {}, []
    for v in video_list:
        vs = slugify(v['title'])
        while vs in vslugs.values():
            vs += '-video'
        vslugs[v['title']] = vs
    for v in video_list:
        vs = vslugs[v['title']]
        url = f'{SITE}/videos/{vs}/'
        words = vtt_lines(v['captions']) if v.get('captions') else []
        thumb = share_thumb(v['thumb'], vs) if v.get('thumb') else SITE + '/Images/social-card.jpg'
        secs = video_seconds(v['file'])
        sg = song_by_title.get(v['title'].strip().lower())
        base = home_nodes.get(v['title'].strip().lower(), {})
        title = f"{v['title']} | Video by {ARTIST}"
        description = f"Watch “{v['title']}”, a video by {ARTIST} ({ARTIST_FULL})" + (f". Begins: “{words[0]}”" if words else '.')
        if len(description) > 160:
            description = description[:159].rsplit(' ', 1)[0].rstrip(' ,.;:“') + '…'
        digest = hashlib.sha256(('video layout 1' + v['title'] + (v.get('youtube') or '') + v['file'] + '\n'.join(words)
                                 + (base.get('uploadDate') or '')).encode()).hexdigest()[:16]
        path = os.path.join(WATCH, vs, 'index.html')
        old_hash, old_date = previous_meta(path)
        modified = old_date if (old_hash == digest and old_date) else TODAY
        others = [o for o in video_list if o is not v]
        more = ('<nav class="song-page-nav" aria-label="More videos">'
                + ''.join(f'<a href="/videos/{vslugs[o["title"]]}/">{esc(o["title"])}</a>' for o in others) + '</nav>\n') if others else ''
        links = []
        if sg: links.append(f'<a href="/lyrics/{sg["slug"]}/">Lyrics</a>')
        if v.get('youtube'): links.append(f'<a href="{esc(v["youtube"])}" rel="noopener">YouTube</a>')
        mins = f' · {secs // 60}:{secs % 60:02d}' if secs else ''
        article = (f'<article class="song-page album-page video-page" id="video" aria-labelledby="video-h" lang="en">\n'
                   f'<header class="song-page-head">\n<p class="song-page-kicker">Video</p>\n<h1 id="video-h">{esc(v["title"])}</h1>\n'
                   f'<p class="song-page-by">Video by <a href="/">{ARTIST}</a>{mins}'
                   f'{" · " + " · ".join(links) if links else ""}</p>\n</header>\n'
                   + (f'<div class="song-page-lyrics" id="video-words">\n<h2 class="sr-only">{esc(v["title"])}: words</h2>\n<p>'
                      + '<br>\n'.join(esc(w) for w in words) + '</p>\n</div>\n' if words else '')
                   + more + '</article>')
        article = article.replace('<a href=', '<a tabindex="-1" href=')   # (out of sight, so out of the Tab order: see the album pages)
        vid_id = url + '#video'
        node = {'@type': 'VideoObject', '@id': vid_id, 'name': v['title'],
                'description': base.get('description') or f'Video for "{v["title"]}" by {ARTIST}.',
                'thumbnailUrl': thumb, 'contentUrl': SITE + '/' + urllib.parse.quote(v['file']), 'url': url, 'inLanguage': 'en',
                'creator': {'@id': f'{SITE}/#artist'}, 'isFamilyFriendly': True,
                **({'uploadDate': base['uploadDate']} if base.get('uploadDate') else {}),
                **({'embedUrl': base['embedUrl']} if base.get('embedUrl') else {}),
                **({'sameAs': v['youtube']} if v.get('youtube') else {}),
                **({'duration': f'PT{secs // 60}M{secs % 60}S'} if secs else {}),
                **({'transcript': ' / '.join(words)} if words else {}),
                'dateModified': modified}
        jsonld = {'@context': 'https://schema.org', '@graph': [
            ARTIST_NODE, node,
            {'@type': 'WebPage', '@id': url, 'url': url, 'name': title, 'inLanguage': 'en', 'dateModified': modified,
             'mainEntity': {'@id': vid_id}, 'primaryImageOfPage': thumb,
             'breadcrumb': {'@type': 'BreadcrumbList', 'itemListElement': [
                 {'@type': 'ListItem', 'position': 1, 'name': ARTIST, 'item': f'{SITE}/'},
                 {'@type': 'ListItem', 'position': 2, 'name': v['title'], 'item': url}]}},
        ]}
        extra = (f'<meta name="video-hash" content="{digest}">\n'
                 f'<meta property="article:modified_time" content="{modified}">\n'
                 f'<meta property="og:video" content="{SITE}/{urllib.parse.quote(v["file"])}">\n'
                 f'<meta property="og:video:type" content="video/mp4">\n')
        html = clone_page(title, description, url, thumb, f'Still from the video “{v["title"]}” by {ARTIST}', jsonld,
                          extra + ('' if 'name="robots"' in (HOME_HTML or open(os.path.join(ROOT, 'index.html'), encoding='utf-8').read()) else ROBOTS_META),
                          v['title'], None, article, deep_meta='deep-video', og_type='video.other', early='videos', skip=('#video', 'Skip to the video'))
        if not html:
            continue
        # a wide picture: the large card suits it (song and album pages use the small card for their square covers)
        html = html.replace('<meta name="twitter:card" content="summary"/>', '<meta name="twitter:card" content="summary_large_image"/>', 1)
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, 'w', encoding='utf-8') as f:
            f.write(html)
        videos_written.append((url, modified, v['title']))
    live_videos = {u.rstrip('/').rsplit('/', 1)[-1] for u, _, _ in videos_written}
    for d in os.listdir(WATCH):
        pth = os.path.join(WATCH, d, 'index.html')
        if d not in live_videos and os.path.isfile(pth) and 'name="video-hash"' in open(pth, encoding='utf-8').read(4000):
            os.unlink(pth)
            try:
                os.rmdir(os.path.join(WATCH, d))
            except OSError:
                pass

    # ── Section pages ────────────────────────────────────────────────────────────────────────────────────────────
    # /press-kit/, /contact/, /music/, /videos/ and /about/ are the site opened at one of its sections: an
    # address of its own for each (a "#music" ending is not an address a search engine lists), to share and to index.
    # Each is the whole site with <meta name="deep-section"> naming the section's id; the page script
    # (openDeepSection in index-src.html) goes there. Its heading and a line about it are in the page's own HTML under
    # the page's only <h1>, out of sight like an album page's. (The videos section is /videos/; the video files live in
    # /Video Files/.)
    kit_mb = ''
    try:
        kit_mb = ''   # (the press kit ZIP is made in the visitor's browser now: there is no file to measure)
    except OSError:
        pass
    album_names = [r['name'] for r in releases if r.get('tracks') or r.get('upcoming')]
    video_names = [v['title'] for v in video_list]
    def _join(names):
        return ', '.join(names[:-1]) + (' and ' if len(names) > 1 else '') + names[-1] if names else ''
    SECTION_PAGES = [
        ('press-kit', 'epk', 'Electronic Press Kit (EPK)', 'WebPage',
         f'Electronic press kit (EPK) for {ARTIST}, outsider singer-songwriter from Guthrie, Oklahoma: songs, lyrics, fact sheet, photos, in one download{kit_mb}.',
         ['<a href="/Images/press-kit/Ash%20Stu%20-%20Fact%20Sheet.txt">The EPK fact sheet</a>']),
        ('contact', 'contact', 'Contact', 'ContactPage',
         f'Contact {ARTIST} ({ARTIST_FULL}) for shows, press or anything else: ashstumusic@gmail.com.',
         ['<a href="mailto:ashstumusic@gmail.com">ashstumusic@gmail.com</a>']),
        ('music', 'music', 'Music', 'CollectionPage',
         f'Music by {ARTIST}: the albums {_join(album_names)}. Listen on the site, read the lyrics and download each album.',
         [f'<a href="/albums/{album_slugs[n]}/">{esc(n)}</a>' for n in album_names if n in album_slugs]),
        ('videos', 'videos', 'Videos', 'CollectionPage',
         f'Videos by {ARTIST}: {_join(video_names)}.',
         [f'<a href="/videos/{vslugs[n]}/">{esc(n)}</a>' for n in video_names if n in vslugs]),
        ('about', 'about', 'About', 'AboutPage',
         f'About {ARTIST}: outsider singer-songwriter from Guthrie, Oklahoma, formerly known as {ARTIST_FULL}.',
         []),
    ]
    sections_written = []
    card = SITE + '/Images/social-card.jpg'
    for slug, sec_id, name, ld_type, description, links in SECTION_PAGES:
        url = f'{SITE}/{slug}/'
        title = f'{name} | {ARTIST}'
        if len(description) > 160:
            description = description[:159].rsplit(' ', 1)[0].rstrip(' ,.;:') + '…'
        digest = hashlib.sha256(('section layout 1' + slug + sec_id + name + description + ''.join(links)).encode()).hexdigest()[:16]
        path = os.path.join(ROOT, slug, 'index.html')
        old_hash, old_date = previous_meta(path)
        modified = old_date if (old_hash == digest and old_date) else TODAY
        others = [(sl, nm) for sl, _, nm, _, _, _ in SECTION_PAGES if sl != slug]
        article = (f'<article class="song-page album-page section-page" id="section" aria-labelledby="section-h" lang="en">\n'
                   f'<header class="song-page-head">\n<p class="song-page-kicker">{ARTIST}</p>\n<h1 id="section-h">{esc(name)}</h1>\n'
                   f'<p class="song-page-by">{esc(description)}</p>\n</header>\n'
                   + ('<ul>\n' + '\n'.join(f'<li>{l}</li>' for l in links) + '\n</ul>\n' if links else '')
                   + '<nav class="song-page-nav" aria-label="More sections">' + ''.join(f'<a href="/{sl}/">{esc(nm)}</a>' for sl, nm in others) + '</nav>\n</article>')
        article = article.replace('<a href=', '<a tabindex="-1" href=')   # (out of sight, so out of the Tab order: see the album pages)
        jsonld = {'@context': 'https://schema.org', '@graph': [
            ARTIST_NODE,
            {'@type': ld_type, '@id': url, 'url': url, 'name': title, 'description': description, 'inLanguage': 'en', 'dateModified': modified,
             'about': {'@id': f'{SITE}/#artist'}, 'isPartOf': {'@type': 'WebSite', 'url': f'{SITE}/', 'name': ARTIST}, 'primaryImageOfPage': card,
             'breadcrumb': {'@type': 'BreadcrumbList', 'itemListElement': [
                 {'@type': 'ListItem', 'position': 1, 'name': ARTIST, 'item': f'{SITE}/'},
                 {'@type': 'ListItem', 'position': 2, 'name': name, 'item': url}]}},
        ]}
        extra = (f'<meta name="section-hash" content="{digest}">\n'
                 f'<meta property="article:modified_time" content="{modified}">\n')
        html = clone_page(title, description, url, card, f'{ARTIST} ({ARTIST_FULL}) - Outsider singer-songwriter from Guthrie, Oklahoma', jsonld,
                          extra + ('' if 'name="robots"' in (HOME_HTML or open(os.path.join(ROOT, 'index.html'), encoding='utf-8').read()) else ROBOTS_META),
                          sec_id, None, article, deep_meta='deep-section', og_type='website', early=sec_id, skip=('#' + sec_id, f'Skip to {name}'))
        if not html:
            continue
        html = html.replace('<meta name="twitter:card" content="summary"/>', '<meta name="twitter:card" content="summary_large_image"/>', 1)
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, 'w', encoding='utf-8') as f:
            f.write(html)
        sections_written.append((url, modified, name))

    # ── Old addresses ────────────────────────────────────────────────────────────────────────────────────────────
    # Videos used to be at /watch/<video>/ and their section at /music-videos/. Links to those are out in the world,
    # so each old address is a small page that sends the visitor straight on to the new one (and tells search engines
    # where it went: canonical link, noindex).
    def _redirect(folder, to):
        to_url = SITE + to
        html = ('<!doctype html>\n<html lang="en"><head><meta charset="utf-8">\n'
                f'<title>Moved: {esc(to_url)}</title>\n<meta name="robots" content="noindex">\n'
                f'<link rel="canonical" href="{esc(to_url)}">\n<meta http-equiv="refresh" content="0; url={esc(to)}">\n'
                f'<script>location.replace({json.dumps(to)} + location.search + location.hash)</script>\n'
                f'</head><body><p>This page has moved to <a href="{esc(to)}">{esc(to_url)}</a>.</p></body></html>\n')
        d = os.path.join(ROOT, folder)
        os.makedirs(d, exist_ok=True)
        with open(os.path.join(d, 'index.html'), 'w', encoding='utf-8') as f:
            f.write(html)
    _redirect('music-videos', '/videos/')
    _redirect('watch', '/videos/')   # (the bare /watch/ too, which showed a file listing or a 404)
    for t, vs in vslugs.items():
        _redirect(os.path.join('watch', vs), f'/videos/{vs}/')

    # Index of every song, grouped by release.
    groups = []
    for rel in releases:
        rs = [s for s in songs if s['release'] is rel]
        if not rs:
            continue
        year = (release_date(rel['name']) or '')[:4]
        rows = '\n'.join(f'        <tr><td class="num">{s["position"]}</td><th scope="row"><a href="/lyrics/{s["slug"]}/">{esc(s["title"])}</a>{" (not released yet)" if s.get("unreleased") else ""}</th></tr>' for s in rs)
        rd = release_date(rel['name'])
        groups.append(f'  <section class="release" aria-labelledby="r-{slugify(rel["name"])}">\n'
                      f'    <h2 id="r-{slugify(rel["name"])}">{esc(rel["name"])}</h2>\n'
                      f'    <p class="muted">{esc(rel.get("type") or "Album")}{", released " + human_date(rd) if rd else ""} · {len(rs)} songs with lyrics</p>\n'
                      f'    <table>\n      <caption>Songs on {esc(rel["name"])} with lyrics</caption>\n'
                      f'      <thead><tr><th scope="col">Track number</th><th scope="col">Song title</th></tr></thead>\n'
                      f'      <tbody>\n{rows}\n      </tbody>\n    </table>\n  </section>')
    index_url = f'{SITE}/lyrics/'
    index_mod = max([m for _, m in written] or [TODAY])
    index_jsonld = {'@context': 'https://schema.org', '@graph': [
        ARTIST_NODE,
        {'@type': 'CollectionPage', '@id': index_url, 'url': index_url, 'name': f'{ARTIST} Lyrics', 'inLanguage': 'en',
         'dateModified': index_mod,
         'mainEntity': {'@type': 'ItemList', 'numberOfItems': len(songs), 'itemListElement': [
             {'@type': 'ListItem', 'position': n + 1, 'url': f"{SITE}/lyrics/{s['slug']}/", 'name': s['title']} for n, s in enumerate(songs)]}}]}
    index_body = (f'<main>\n  <h1>{ARTIST} Lyrics</h1>\n  <p class="byline">Full lyrics to every released song by {ARTIST} '
                  f'({ARTIST_FULL}), outsider singer-songwriter from Guthrie, Oklahoma.</p>\n' + '\n'.join(groups) + '\n</main>')
    # The all-songs index page (/lyrics/) is NOT published: the owner took it out of public view. Each song
    # still has its own page; they are found through the sitemap and each other's next/previous links.
    _idx = os.path.join(OUT, 'index.html')
    if os.path.isfile(_idx):
        os.remove(_idx)

    # Remove pages for songs that no longer exist (only folders this script made).
    live = {s['slug'] for s in songs}
    for d in os.listdir(OUT):
        p = os.path.join(OUT, d, 'index.html')
        if d not in live and os.path.isfile(p) and 'name="lyrics-hash"' in open(p, encoding='utf-8').read(4000):
            os.remove(p)
            try:
                os.rmdir(os.path.join(OUT, d))
            except OSError:
                pass

    # sitemap.xml: replace the block between the LYRICS markers.
    sm_path = os.path.join(ROOT, 'sitemap.xml')
    with open(sm_path, encoding='utf-8') as f:
        sm = f.read()
    entries = [f'  <url>\n    <loc>{u}</loc>\n    <lastmod>{m}</lastmod>\n    <changefreq>yearly</changefreq>\n    <priority>0.6</priority>\n  </url>' for u, m in written]
    block = '  <!-- LYRICS:START (generated by scripts/build_lyrics_pages.py) -->\n' + '\n'.join(entries) + '\n  <!-- LYRICS:END -->'
    if '<!-- LYRICS:START' in sm:
        sm = re.sub(r'  <!-- LYRICS:START.*?<!-- LYRICS:END -->', lambda m: block, sm, flags=re.S)
    else:
        sm = sm.replace('</urlset>', block + '\n</urlset>')
    a_entries = [f'  <url>\n    <loc>{u}</loc>\n    <lastmod>{m}</lastmod>\n    <changefreq>monthly</changefreq>\n    <priority>0.8</priority>\n  </url>' for u, m, _ in albums_written]
    a_block = '  <!-- ALBUMS:START (generated by scripts/build_lyrics_pages.py) -->\n' + '\n'.join(a_entries) + '\n  <!-- ALBUMS:END -->'
    if '<!-- ALBUMS:START' in sm:
        sm = re.sub(r'  <!-- ALBUMS:START.*?<!-- ALBUMS:END -->', lambda m: a_block, sm, flags=re.S)
    else:
        sm = sm.replace('  <!-- LYRICS:START', a_block + '\n  <!-- LYRICS:START', 1) if '<!-- LYRICS:START' in sm else sm.replace('</urlset>', a_block + '\n</urlset>')
    s_entries = [f'  <url>\n    <loc>{u}</loc>\n    <lastmod>{m}</lastmod>\n    <changefreq>monthly</changefreq>\n    <priority>0.8</priority>\n  </url>' for u, m, _ in sections_written]
    s_block = '  <!-- SECTIONS:START (generated by scripts/build_lyrics_pages.py) -->\n' + '\n'.join(s_entries) + '\n  <!-- SECTIONS:END -->'
    if '<!-- SECTIONS:START' in sm:
        sm = re.sub(r'  <!-- SECTIONS:START.*?<!-- SECTIONS:END -->', lambda m: s_block, sm, flags=re.S)
    else:
        sm = sm.replace('  <!-- ALBUMS:START', s_block + '\n  <!-- ALBUMS:START', 1) if '<!-- ALBUMS:START' in sm else sm.replace('</urlset>', s_block + '\n</urlset>')
    v_entries = [f'  <url>\n    <loc>{u}</loc>\n    <lastmod>{m}</lastmod>\n    <changefreq>monthly</changefreq>\n    <priority>0.7</priority>\n  </url>' for u, m, _ in videos_written]
    v_block = '  <!-- VIDEOS:START (generated by scripts/build_lyrics_pages.py) -->\n' + '\n'.join(v_entries) + '\n  <!-- VIDEOS:END -->'
    if '<!-- VIDEOS:START' in sm:
        sm = re.sub(r'  <!-- VIDEOS:START.*?<!-- VIDEOS:END -->', lambda m: v_block, sm, flags=re.S)
    else:
        sm = sm.replace('  <!-- LYRICS:START', v_block + '\n  <!-- LYRICS:START', 1) if '<!-- LYRICS:START' in sm else sm.replace('</urlset>', v_block + '\n</urlset>')
    with open(sm_path, 'w', encoding='utf-8') as f:
        f.write(sm)

    # robots.txt: open to everyone, AI crawlers named explicitly.
    agents = ['*', 'Googlebot', 'Bingbot', 'Google-Extended', 'GPTBot', 'OAI-SearchBot', 'ChatGPT-User', 'ClaudeBot',
              'Claude-User', 'Claude-SearchBot', 'anthropic-ai', 'PerplexityBot', 'Perplexity-User', 'Applebot',
              'Applebot-Extended', 'CCBot', 'Bytespider', 'Amazonbot', 'meta-externalagent', 'DuckAssistBot', 'cohere-ai']
    robots = ('# Everything on ashstu.art may be crawled and indexed by search engines\n'
              '# and AI crawlers, including the lyrics at /lyrics/.\n\n'
              + '\n'.join(f'User-agent: {a}\nAllow: /\n' for a in agents)
              + f'\nSitemap: {SITE}/sitemap.xml\n')
    with open(os.path.join(ROOT, 'robots.txt'), 'w', encoding='utf-8') as f:
        f.write(robots)

    # Short links: ashstu.art/<word>/ sends people (and crawlers, through the
    # canonical link) to the song. Each folder carries a .song-key marker so
    # only folders made here are ever cleaned up.
    page_of = {s['title']: s for s in songs}
    made = set()
    for title, word in KEYS.items():
        s = page_of.get(title)
        target = f"/lyrics/{s['slug']}/" if s else '/#music'
        d = os.path.join(ROOT, word)
        os.makedirs(d, exist_ok=True)
        open(os.path.join(d, '.song-key'), 'w').write(title + '\n')
        with open(os.path.join(d, 'index.html'), 'w', encoding='utf-8') as f:
            f.write(f'<!doctype html>\n<html lang="en">\n<head>\n<meta charset="utf-8">\n<title>{esc(title)} | {ARTIST}</title>\n'
                    f'<link rel="canonical" href="{SITE}{target if s else "/"}">\n<meta http-equiv="refresh" content="0; url={target}">\n'
                    f'<meta name="viewport" content="width=device-width, initial-scale=1">\n<script>location.replace({json.dumps(target)})</script>\n</head>\n'
                    f'<body>\n<p><a href="{target}">{esc(title)} by {ARTIST}</a></p>\n</body>\n</html>\n')
        made.add(word)
    for d in os.listdir(ROOT):
        mark = os.path.join(ROOT, d, '.song-key')
        if d not in made and os.path.isfile(mark):
            for fn in ('index.html', '.song-key'):
                try: os.remove(os.path.join(ROOT, d, fn))
                except OSError: pass
            try: os.rmdir(os.path.join(ROOT, d))
            except OSError: pass

    lines = [f'# {ARTIST}', '',
             f'> Official site of {ARTIST} ({ARTIST_FULL}), outsider singer-songwriter from Guthrie, Oklahoma. '
             'Every song\'s full lyrics are published here by the artist as plain HTML, one page per song.', '',
             'Each song has a one-word identifier ("cloud" is The Cloud for the Desert): ashstu.art/<word> opens that song.', '',
             '## Lyrics', '']
    for rel in releases:
        rs = [s for s in songs if s['release'] is rel]
        if rs:
            lines += ['', f'### {rel["name"]}', '']
            lines += [f'- [{s["title"]}]({SITE}/lyrics/{s["slug"]}/): one-word lookup "{s["word"]}" ({SITE}/{s["word"]}/)' + (' (not released yet)' if s.get('unreleased') else '') for s in rs]
    if albums_written:
        lines += ['', '## Albums', ''] + [f'- [{n}]({u}): track list, with each song linking to its lyrics' for u, _, n in albums_written]
    if videos_written:
        lines += ['', '## Videos', ''] + [f'- [{n}]({u}): the video, with its words' for u, _, n in videos_written]
    if sections_written:
        lines += ['', '## Sections', ''] + [f'- [{n}]({u})' for u, _, n in sections_written]
    lines += ['', '## Site', '', f'- [Home]({SITE}/): music, videos, press kit and contact', f'- [Sitemap]({SITE}/sitemap.xml)', '']
    with open(os.path.join(ROOT, 'llms.txt'), 'w', encoding='utf-8') as f:
        f.write('\n'.join(lines))

    print(f'Lyrics pages: {len(written)} songs -> lyrics/ (no public index page); album pages: {len(albums_written)} -> albums/; video pages: {len(videos_written)} -> videos/; section pages: {len(sections_written)}; sitemap, robots.txt and llms.txt updated')


if __name__ == '__main__':
    main()
