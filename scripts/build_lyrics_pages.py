#!/usr/bin/env python3
"""Lyrics live on one page: the homepage (scripts/prerender.py writes every
song's lyrics into the Music section's tracklists, with JSON-LD). The old
per-song URLs (/lyrics/<song>/ and /lyrics/) are kept only as redirects to
/#music, so links people already have keep working; they're noindex and
left out of the sitemap. This also keeps robots.txt open to crawlers.

stanzas() and slugify() here are shared with prerender.py.

Run: python3 scripts/build_lyrics_pages.py   (npm run build runs it too)
"""
import datetime
import html
import json
import os
import re
import unicodedata

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SITE = 'https://ashstu.art'
ARTIST = 'Ash Stu'
ARTIST_FULL = 'Ashton Stubblefield'
GENRE = 'Outsider-Folk'
OUT = os.path.join(ROOT, 'lyrics')
TODAY = datetime.date.today().isoformat()


def esc(s):
    # &, <, > and double quotes only: apostrophes stay readable for scrapers.
    return html.escape(str(s), quote=False).replace('"', '&quot;')


def slugify(s):
    s = unicodedata.normalize('NFKD', s).encode('ascii', 'ignore').decode()
    s = re.sub(r"['’]", '', s.lower())
    return re.sub(r'[^a-z0-9]+', '-', s).strip('-') or 'song'


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


def stanzas(entry):
    """Split lyric lines into verses. Blank lines always split. Synced
    lyrics also split at long pauses in the timing (a gap well beyond the
    song's usual line-to-line gap), which is where verses and choruses
    usually break."""
    lines = entry.get('lines') or []
    times = [l[0] for l in lines]
    gaps = [b - a for a, b in zip(times, times[1:]) if isinstance(a, (int, float)) and isinstance(b, (int, float))]
    limit = None
    if entry.get('synced') is not False and len(gaps) >= 4:
        med = sorted(gaps)[len(gaps) // 2]
        limit = max(7.0, med * 1.9)
    out, cur = [], []
    for i, (t, text) in enumerate(lines):
        text = (text or '').strip()
        if not text:
            if cur:
                out.append(cur); cur = []
            continue
        if cur and limit is not None and i > 0:
            prev = lines[i - 1][0]
            if isinstance(prev, (int, float)) and isinstance(t, (int, float)) and t - prev > limit:
                out.append(cur); cur = []
        cur.append(text)
    if cur:
        out.append(cur)
    return out


def stub(title):
    """Sends visitors (and search engines) on to the homepage's Music
    section, where every song's lyrics live."""
    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="lyrics-redirect" content="1">
<meta name="robots" content="noindex, follow">
<link rel="canonical" href="{SITE}/">
<meta http-equiv="refresh" content="0; url=/#music">
<title>{esc(title)} | {ARTIST}</title>
</head>
<body>
<p><a href="/#music">{esc(title)}: the lyrics are on the Ash Stu homepage, in the Music section.</a></p>
<script>location.replace('/#music')</script>
</body>
</html>
"""


def main():
    with open(os.path.join(ROOT, 'releases.json'), encoding='utf-8') as f:
        releases = json.load(f)
    with open(os.path.join(ROOT, 'lyrics.json'), encoding='utf-8') as f:
        lyrics = json.load(f)
    os.makedirs(OUT, exist_ok=True)

    slugs, used = [], set()
    for rel in releases:
        for t in rel.get('tracks', []):
            entry = lyrics.get(t['file'])
            if not entry or not entry.get('lines'):
                continue
            slug = slugify(t['title'])
            if slug in used:
                slug = f"{slug}-{slugify(rel['name'])}"
            used.add(slug)
            slugs.append((slug, t['title']))

    for slug, title in slugs:
        os.makedirs(os.path.join(OUT, slug), exist_ok=True)
        with open(os.path.join(OUT, slug, 'index.html'), 'w', encoding='utf-8') as f:
            f.write(stub(f'{title} lyrics'))
    with open(os.path.join(OUT, 'index.html'), 'w', encoding='utf-8') as f:
        f.write(stub(f'{ARTIST} lyrics'))

    # Remove pages for songs that no longer exist (only folders this script made).
    live = {s for s, _ in slugs}
    for d in os.listdir(OUT):
        p = os.path.join(OUT, d, 'index.html')
        if d not in live and os.path.isfile(p):
            head = open(p, encoding='utf-8').read(4000)
            if 'name="lyrics-hash"' in head or 'name="lyrics-redirect"' in head:
                os.remove(p)
                try:
                    os.rmdir(os.path.join(OUT, d))
                except OSError:
                    pass

    # sitemap.xml: no lyrics pages (the homepage carries the lyrics).
    sm_path = os.path.join(ROOT, 'sitemap.xml')
    with open(sm_path, encoding='utf-8') as f:
        sm = f.read()
    sm = re.sub(r'\n?  <!-- LYRICS:START.*?<!-- LYRICS:END -->', '', sm, flags=re.S)
    with open(sm_path, 'w', encoding='utf-8') as f:
        f.write(sm)

    # robots.txt: open to everyone, AI crawlers named explicitly.
    agents = ['*', 'Googlebot', 'Bingbot', 'Google-Extended', 'GPTBot', 'OAI-SearchBot', 'ChatGPT-User', 'ClaudeBot',
              'Claude-User', 'Claude-SearchBot', 'anthropic-ai', 'PerplexityBot', 'Perplexity-User', 'Applebot',
              'Applebot-Extended', 'CCBot', 'Bytespider', 'Amazonbot', 'meta-externalagent', 'DuckAssistBot', 'cohere-ai']
    robots = ('# Everything on ashstu.art may be crawled and indexed by search engines\n'
              '# and AI crawlers, including the lyrics on the homepage.\n\n'
              + '\n'.join(f'User-agent: {a}\nAllow: /\n' for a in agents)
              + f'\nSitemap: {SITE}/sitemap.xml\n')
    with open(os.path.join(ROOT, 'robots.txt'), 'w', encoding='utf-8') as f:
        f.write(robots)

    print(f'Lyrics: {len(slugs)} old lyric URLs redirect to /#music; sitemap and robots.txt updated')


if __name__ == '__main__':
    main()
