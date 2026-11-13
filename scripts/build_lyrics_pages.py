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
    """Descriptive cover alt text kept in redesign/facts.json."""
    try:
        with open(os.path.join(ROOT, 'redesign', 'facts.json'), encoding='utf-8') as f:
            return json.load(f).get('alt', {})
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
    h = re.search(r'<meta name="lyrics-hash" content="([0-9a-f]+)"', head)
    d = re.search(r'<meta property="article:modified_time" content="(\d{4}-\d{2}-\d{2})"', head)
    return (h.group(1) if h else None), (d.group(1) if d else None)


STYLE = """
@font-face { font-family: 'Headline'; src: url('/Fonts/subsetted/YoungSerif-Regular.woff2') format('woff2'); font-display: swap; }
@font-face { font-family: 'Lyrics'; src: url('/Fonts/subsetted/Fraunces-Regular-opsz.woff2') format('woff2'); font-display: swap; }
@font-face { font-family: 'Text'; src: url('/Fonts/subsetted/Outfit-VF.woff2') format('woff2'); font-weight: 100 900; font-display: swap; }
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
h1, h2 { font-family: 'Headline', Georgia, serif; font-weight: 400; line-height: 1.15; text-wrap: balance; margin: 0; }
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
  <nav aria-label="Site"><a href="/lyrics/">All lyrics</a> · <a href="/#music">Listen</a></nav>
</header>
{body}
<footer><p>Lyrics © {ARTIST} ({ARTIST_FULL}). Published by the artist at <a href="{SITE}/">ashstu.art</a>.</p></footer>
</body>
</html>
"""


ARTIST_NODE = {'@type': ['MusicGroup', 'Person'], '@id': f'{SITE}/#artist', 'name': ARTIST,
               'alternateName': ARTIST_FULL, 'url': f'{SITE}/', 'genre': GENRE}


HOME_HTML = None
def clone_page(title, description, url, art, alt, jsonld, extra, deep_key, song_title):
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
    h = sub(r'<meta property="og:type" content="[^"]*"\s*/?>', '<meta property="og:type" content="music.song"/>', h)
    h = sub(r'<meta property="og:url" content="[^"]*"\s*/?>', f'<meta property="og:url" content="{url}"/>', h)
    h = sub(r'<meta property="og:image" content="[^"]*"\s*/?>', f'<meta property="og:image" content="{esc(art)}"/>', h)
    h = sub(r'<meta name="twitter:title" content="[^"]*"\s*/?>', f'<meta name="twitter:title" content="{a}"/>', h)
    h = sub(r'<meta name="twitter:description" content="[^"]*"\s*/?>', f'<meta name="twitter:description" content="{d}"/>', h)
    head_add = ('<base href="/"/>\n'
                f'<meta name="deep-song" content="{esc(deep_key)}"/>\n' + extra +
                '<script type="application/ld+json">' + json.dumps(jsonld, ensure_ascii=False).replace('</', '<\\/') + '</script>\n'
                # with <base href="/">, "#music" would point at the homepage:
                # keep in-page links scrolling on this page
                '<script>addEventListener("click",function(e){if(e.defaultPrevented||e.button||e.metaKey||e.ctrlKey||e.shiftKey)return;'
                'var a=e.target.closest&&e.target.closest("a[href^=\'#\']");if(!a||a.target)return;e.preventDefault();'
                'var id=decodeURIComponent(a.getAttribute("href").slice(1)),t=id&&document.getElementById(id);'
                'var sm=matchMedia("(prefers-reduced-motion: reduce)").matches?"auto":"smooth";'
                't?t.scrollIntoView({behavior:sm,block:"start"}):scrollTo({top:0,behavior:sm});});</script>\n')
    h = sub(r'(<meta charset="[^"]*"\s*/?>)', None, h) if False else re.sub(r'(<meta charset="[^"]*"\s*/?>)', lambda m: m.group(1) + '\n' + head_add, h, count=1)
    # the song's lyrics already open in the static HTML
    h = h.replace(f'{esc(song_title)}<details class="rel-lyrics-static">', f'{esc(song_title)}<details class="rel-lyrics-static" open>', 1)
    return h


def main():
    with open(os.path.join(ROOT, 'releases.json'), encoding='utf-8') as f:
        releases = json.load(f)
    with open(os.path.join(ROOT, 'lyrics.json'), encoding='utf-8') as f:
        lyrics = json.load(f)
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

    written = []
    ALTS = cover_alts()
    for s in songs:
        rel = s['release']
        url = f"{SITE}/lyrics/{s['slug']}/"
        art_path = '/' + rel['art'].replace(' ', '%20') if rel.get('art') else '/Images/social-card.png'
        art = SITE + art_path   # absolute for Open Graph / JSON-LD
        text = '\n\n'.join('\n'.join(v) for v in s['verses'])
        digest = hashlib.sha256((s['title'] + rel['name'] + text).encode()).hexdigest()[:16]
        path = os.path.join(OUT, s['slug'], 'index.html')
        old_hash, old_date = previous_meta(path)
        modified = old_date if (old_hash == digest and old_date) else TODAY
        first = s['verses'][0][0] if s['verses'] else ''
        kind = rel.get('type') or 'Album'
        year = (s['date'] or '')[:4]
        trad, unrel = s.get('traditional'), s.get('unreleased')
        who = f'the traditional song “{s["title"]}”, arranged by {ARTIST}' if trad else f'“{s["title"]}” by {ARTIST}'
        description = (f"Full lyrics to {who}, from the {kind.lower()} {rel['name']}"
                       f"{' (not released yet)' if unrel else (' (' + year + ')' if year else '')}. Begins: “{first}”")[:300]
        title = f"{s['title']} Lyrics | {ARTIST}"
        listen = []
        if rel.get('apple'):
            listen.append(f'<li><a href="{esc(rel["apple"])}" rel="noopener">Apple Music</a></li>')
        if rel.get('spotify'):
            listen.append(f'<li><a href="{esc(rel["spotify"])}" rel="noopener">Spotify</a></li>')
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
  <nav class="crumbs" aria-label="Breadcrumb"><a href="/lyrics/">Lyrics</a> › {esc(rel['name'])}</nav>
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
        writer = {'@type': 'Person', 'name': 'Traditional'} if trad else {'@id': f'{SITE}/#artist'}
        jsonld = {'@context': 'https://schema.org', '@graph': [
            ARTIST_NODE,
            *([] if unrel else [{'@type': 'MusicRecording', '@id': url + '#recording', 'name': s['title'], 'url': url,
             'byArtist': {'@id': f'{SITE}/#artist'}, 'inLanguage': 'en', 'genre': GENRE,
             **({'datePublished': s['date']} if s['date'] else {}),
             'inAlbum': {'@type': 'MusicAlbum', 'name': rel['name'], 'url': f'{SITE}/#music', 'image': art,
                         'albumReleaseType': 'SingleRelease' if kind == 'Single' else 'AlbumRelease', 'byArtist': {'@id': f'{SITE}/#artist'}},
             'position': s['position'], 'recordingOf': {'@id': comp_id}}]),
            {'@type': 'MusicComposition', '@id': comp_id, 'name': s['title'], 'url': url, 'inLanguage': 'en', 'genre': GENRE,
             'composer': writer, 'lyricist': writer,
             **({'arranger': {'@id': f'{SITE}/#artist'}} if trad else {}),
             **({'datePublished': s['date']} if s['date'] else {}),
             'lyrics': {'@type': 'CreativeWork', 'inLanguage': 'en', 'text': text},
             'dateModified': modified},
            {'@type': 'WebPage', '@id': url, 'url': url, 'name': title, 'inLanguage': 'en',
             'dateModified': modified, 'mainEntity': {'@id': comp_id}, 'primaryImageOfPage': art,
             'breadcrumb': {'@type': 'BreadcrumbList', 'itemListElement': [
                 {'@type': 'ListItem', 'position': 1, 'name': ARTIST, 'item': f'{SITE}/'},
                 {'@type': 'ListItem', 'position': 2, 'name': 'Lyrics', 'item': f'{SITE}/lyrics/'},
                 {'@type': 'ListItem', 'position': 3, 'name': s['title'], 'item': url}]}},
        ]}
        extra = (f'<meta name="lyrics-hash" content="{digest}">\n'
                 f'<meta property="article:modified_time" content="{modified}">\n'
                 f'<meta property="music:musician" content="{SITE}/">\n')
        os.makedirs(os.path.dirname(path), exist_ok=True)
        deep_key = s.get('key')
        html = clone_page(title, description, url, art, alt, jsonld, extra, deep_key, s['title'])
        with open(path, 'w', encoding='utf-8') as f:
            f.write(html or page(title, description, url, 'music.song', art, alt, body, jsonld, extra))
        written.append((url, modified))

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
    with open(os.path.join(OUT, 'index.html'), 'w', encoding='utf-8') as f:
        f.write(page(f'{ARTIST} Lyrics | All Songs', f'Full lyrics to every released song by {ARTIST} ({ARTIST_FULL}), outsider singer-songwriter from Guthrie, Oklahoma.',
                     index_url, 'website', f'{SITE}/Images/social-card.png', f'{ARTIST}, outsider singer-songwriter', index_body, index_jsonld))

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
    entries = [f'  <url>\n    <loc>{index_url}</loc>\n    <lastmod>{index_mod}</lastmod>\n    <changefreq>monthly</changefreq>\n    <priority>0.8</priority>\n  </url>']
    entries += [f'  <url>\n    <loc>{u}</loc>\n    <lastmod>{m}</lastmod>\n    <changefreq>yearly</changefreq>\n    <priority>0.6</priority>\n  </url>' for u, m in written]
    block = '  <!-- LYRICS:START (generated by scripts/build_lyrics_pages.py) -->\n' + '\n'.join(entries) + '\n  <!-- LYRICS:END -->'
    if '<!-- LYRICS:START' in sm:
        sm = re.sub(r'  <!-- LYRICS:START.*?<!-- LYRICS:END -->', lambda m: block, sm, flags=re.S)
    else:
        sm = sm.replace('</urlset>', block + '\n</urlset>')
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

    print(f'Lyrics pages: {len(written)} songs + index -> lyrics/; sitemap and robots.txt updated')


if __name__ == '__main__':
    main()
