#!/usr/bin/env python3
"""Build redesign/index.html: a fully static, AI-crawler-first page.

Reads releases.json, videos.json, Audio/*/links.txt (release dates),
redesign/facts.json (hand-entered facts and alt text), the MP3/MP4 files
(lengths via ffprobe) and ash-stu-press-kit.zip (contents and size), then
fills the @GENERATED markers in redesign/index.template.html.

Every fact shown on the page and every fact in the JSON-LD comes from the
same Python objects below, so the two can never disagree.

Run from anywhere:  python3 scripts/build_redesign.py
Needs: ffprobe (part of ffmpeg) for song and video lengths.
"""
import datetime
import html
import json
import os
import re
import shutil
import subprocess
import sys
import zipfile
from urllib.parse import quote

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
os.chdir(ROOT)

TEMPLATE = 'redesign/index.template.html'
OUTPUT = 'redesign/index.html'
PRESS_KIT = 'ash-stu-press-kit.zip'

if not shutil.which('ffprobe'):
    sys.exit('ffprobe not found: install ffmpeg (sudo apt install ffmpeg) and run again.')

facts = json.load(open('redesign/facts.json', encoding='utf-8'))
releases = json.load(open('releases.json', encoding='utf-8'))
videos = json.load(open('videos.json', encoding='utf-8'))
SITE = facts['site']['url']
PAGE = facts['site']['page_url']
ARTIST = facts['artist']
ALT = facts['alt']

esc = lambda s: html.escape(str(s), quote=True)


def rel_url(path):
    """Path from the page (in /redesign/) to a project file, URL-encoded."""
    return '../' + '/'.join(quote(p) for p in path.split('/'))


def abs_url(path):
    return SITE + '/'.join(quote(p) for p in path.split('/'))


def alt_for(path):
    if path not in ALT:
        sys.exit(f'Missing alt text for {path!r}: add it to redesign/facts.json "alt".')
    return ALT[path]


def slug(s):
    return re.sub(r'[^a-z0-9]+', '-', s.lower()).strip('-')


def seconds(path):
    out = subprocess.run(
        ['ffprobe', '-v', 'error', '-show_entries', 'format=duration', '-of', 'csv=p=0', path],
        capture_output=True, text=True, check=True).stdout.strip()
    return round(float(out))


def iso_dur(s):
    h, rem = divmod(s, 3600)
    m, sec = divmod(rem, 60)
    return 'PT' + (f'{h}H' if h else '') + (f'{m}M' if m else '') + f'{sec}S'


def clock(s):
    m, sec = divmod(s, 60)
    return f'{m}:{sec:02d}'


def words_dur(s):
    """'34 minutes 12 seconds': explicit units, no ambiguity."""
    m, sec = divmod(s, 60)
    parts = []
    if m:
        parts.append(f'{m} minute' + ('s' if m != 1 else ''))
    if sec or not m:
        parts.append(f'{sec} second' + ('s' if sec != 1 else ''))
    return ' '.join(parts)


def long_date(iso):
    d = datetime.date.fromisoformat(iso)
    return f'{d:%B} {d.day}, {d.year}'


def megabytes(n):
    return f'{n / 1_000_000:.1f} megabytes'


def links_txt(folder):
    out = {}
    path = os.path.join(folder, 'links.txt')
    if os.path.exists(path):
        for line in open(path, encoding='utf-8'):
            if ':' in line:
                k, v = line.split(':', 1)
                out[k.strip().lower()] = v.strip()
    return out


# ── GATHER FACTS ──────────────────────────────────────────────────────
for r in releases:
    folder = os.path.dirname(r['tracks'][0]['file'])
    info = links_txt(folder)
    if 'date' not in info:
        sys.exit(f'{folder}/links.txt has no "date: YYYY-MM-DD" line.')
    r['date'] = info['date']
    r['slug'] = slug(r['name'])
    extra = facts.get('release_extras', {}).get(r['name'], {})
    r['full_title'] = extra.get('full_title', r['name'])
    r['featured'] = extra.get('featured_artists', [])
    for t in r['tracks']:
        t['seconds'] = seconds(t['file'])
    r['seconds'] = sum(t['seconds'] for t in r['tracks'])
    r['count'] = len(r['tracks'])
    r['songs'] = f"{r['count']} song" + ('s' if r['count'] != 1 else '')

for v in videos:
    v['seconds'] = seconds(v['file'])
    v['slug'] = 'video-' + slug(v['title'])
    v['date'] = facts['video_upload_dates'].get(v['title'])
    v['yt_id'] = (v.get('youtube') or '').rstrip('/').split('/')[-1] or None

kit_size = os.path.getsize(PRESS_KIT)
with zipfile.ZipFile(PRESS_KIT) as z:
    kit_files = [i for i in z.infolist() if not i.is_dir()]
kit_songs = sorted(os.path.splitext(os.path.basename(i.filename))[0] for i in kit_files if i.filename.lower().endswith('.mp3'))
kit_images = sorted(os.path.basename(i.filename) for i in kit_files if not i.filename.lower().endswith('.mp3'))

newest = releases[0]
profiles = ARTIST['profiles']


def byline(r):
    s = f"{r['type']} by {ARTIST['name']}"
    if r['featured']:
        s += ' featuring ' + ' and '.join(r['featured'])
    return s


def stream_links(r):
    out = []
    if r.get('apple'):
        out.append(f'<a href="{esc(r["apple"])}">{esc(r["full_title"])} on Apple Music</a>')
    if r.get('spotify'):
        out.append(f'<a href="{esc(r["spotify"])}">{esc(r["full_title"])} on Spotify</a>')
    return out


# ── HTML FRAGMENTS ────────────────────────────────────────────────────
def hero_photo():
    p = 'Images/embedded/hero-ash-stu-guitar.webp'
    return (f'<img src="{rel_url(p)}" alt="{esc(alt_for(p))}" width="1260" height="855" fetchpriority="high">')


def newest_release():
    r = newest
    first = r['tracks'][0]
    kind = r['type'].lower()
    label = 'Play the song' if r['count'] == 1 else f'Play the {kind}'
    links = ' / '.join(
        f'<a href="{esc(u)}">{n}</a>' for n, u in (('Apple Music', r.get('apple')), ('Spotify', r.get('spotify'))) if u)
    return f'''<article class="new-record" aria-labelledby="newest-title">
      <img class="new-record-art" src="{rel_url(r['art'])}" alt="{esc(alt_for(r['art']))}" width="160" height="160">
      <p class="kicker"><span class="stitch-dot" aria-hidden="true"></span>Newest release: {esc(r['type'])}</p>
      <h2 class="new-record-title" id="newest-title"><span class="sr-only">Newest release: </span>{esc(r['full_title'])}</h2>
      <p class="new-record-meta">Released <time datetime="{r['date']}">{long_date(r['date'])}</time> · {r['songs']} · <time datetime="{iso_dur(r['seconds'])}">{words_dur(r['seconds'])}</time></p>
      <footer class="new-record-actions">
        <a class="btn btn-primary" href="{rel_url(first['file'])}" data-play="0:0" aria-label="{esc(label)}: {esc(r['full_title'])}, starting with track 1, {esc(first['title'])}">
          <svg aria-hidden="true" viewBox="0 0 24 24" width="18" height="18"><path d="M7 4.5v15l12-7.5z" fill="currentColor"/></svg>
          {esc(label)}
        </a>
        <p class="stream-links">Or stream it on {links}</p>
      </footer>
    </article>'''


def discography_summary():
    albums = sum(1 for r in releases if r['type'] == 'Album')
    singles = sum(1 for r in releases if r['type'] == 'Single')
    songs = sum(r['count'] for r in releases)
    return (f'<p class="section-lede">{len(releases)} releases ({albums} album{"s" if albums != 1 else ""}, '
            f'{singles} single{"s" if singles != 1 else ""}), {songs} songs in total, newest first. '
            'Select any song title to play it.</p>')


def records():
    items = []
    for ri, r in enumerate(releases):
        rows = []
        for ti, t in enumerate(r['tracks']):
            rows.append(
                f'<tr><td>{ti + 1}</td>'
                f'<th scope="row"><a class="track" href="{rel_url(t["file"])}" data-play="{ri}:{ti}">{esc(t["title"])}</a></th>'
                f'<td><time datetime="{iso_dur(t["seconds"])}">{clock(t["seconds"])}</time></td></tr>')
        first = r['tracks'][0]
        play_label = 'Play' if r['count'] == 1 else 'Play all'
        items.append(f'''<li><article class="record" id="{r['slug']}" aria-labelledby="{r['slug']}-title">
        <img class="record-art" src="{rel_url(r['art'])}" alt="{esc(alt_for(r['art']))}" width="352" height="352" loading="{'eager' if ri == 0 else 'lazy'}">
        <header class="record-head">
          <h3 class="record-title" id="{r['slug']}-title">{esc(r['full_title'])}</h3>
          <p class="record-byline">{esc(byline(r))}</p>
        </header>
        <dl class="record-facts">
          <div><dt>Release type</dt><dd>{esc(r['type'])}</dd></div>
          <div><dt>Release date</dt><dd><time datetime="{r['date']}">{long_date(r['date'])}</time></dd></div>
          <div><dt>Number of songs</dt><dd>{r['songs']}</dd></div>
          <div><dt>Total length</dt><dd><time datetime="{iso_dur(r['seconds'])}">{words_dur(r['seconds'])}</time></dd></div>
        </dl>
        <p class="record-actions">
          <a class="btn btn-secondary" href="{rel_url(first['file'])}" data-play="{ri}:0" aria-label="{play_label}: {esc(r['full_title'])}">
            <svg aria-hidden="true" viewBox="0 0 24 24" width="14" height="14"><path d="M7 4.5v15l12-7.5z" fill="currentColor"/></svg>
            {play_label}
          </a>
          {' '.join(stream_links(r))}
        </p>
        <table class="tracks">
          <caption class="sr-only">Tracklist of {esc(r['full_title'])}: {r['songs']}, total length {words_dur(r['seconds'])}</caption>
          <thead><tr><th scope="col">Track number</th><th scope="col">Song title</th><th scope="col">Length (minutes:seconds)</th></tr></thead>
          <tbody>
            {chr(10).join('            ' + x for x in rows).strip()}
          </tbody>
        </table>
      </article></li>''')
    return '<ol class="records" role="list" aria-label="Releases, newest first">\n    ' + '\n    '.join(items) + '\n    </ol>'


def videos_summary():
    return (f'<p class="section-lede">{len(videos)} official music videos by Ash Stu, '
            'each also published on YouTube.</p>')


def video_cards():
    items = []
    for vi, v in enumerate(videos):
        date = (f' · Published on YouTube <time datetime="{v["date"]}">{long_date(v["date"])}</time>'
                if v['date'] else '')
        yt = f' · <a class="video-yt-link" href="{esc(v["youtube"])}">Watch “{esc(v["title"])}” on YouTube</a>' if v.get('youtube') else ''
        items.append(f'''<li><article class="video" id="{v['slug']}" aria-labelledby="{v['slug']}-title">
        <a class="video-link" href="{rel_url(v['file'])}" data-video="{vi}" aria-label="Play the music video for {esc(v['title'])} ({words_dur(v['seconds'])})">
          <img src="{rel_url(v['thumb'])}" alt="{esc(alt_for(v['thumb']))}" width="640" height="360" loading="lazy">
          <span class="video-play" aria-hidden="true"><svg viewBox="0 0 24 24" width="14" height="14"><path d="M7 4.5v15l12-7.5z" fill="currentColor"/></svg>Play</span>
        </a>
        <h3 class="video-name" id="{v['slug']}-title">{esc(v['title'])}</h3>
        <p class="video-meta">Music video · <time datetime="{iso_dur(v['seconds'])}">{words_dur(v['seconds'])}</time>{date}{yt}</p>
      </article></li>''')
    return '<ul class="videos" role="list">\n    ' + '\n    '.join(items) + '\n    </ul>'


def bio():
    return f'''<p class="about-lead">{esc(ARTIST['description'])}</p>'''


def snapshots():
    out = []
    for p, w, h, cls in (('Images/Profile-3.webp', 800, 800, 'snap snap-main'),
                         ('Images/Profile-4.webp', 324, 432, 'snap'),
                         ('Images/Profile-6.webp', 324, 362, 'snap')):
        out.append(f'<img class="{cls}" src="{rel_url(p)}" alt="{esc(alt_for(p))}" width="{w}" height="{h}" loading="lazy">')
    return '\n      '.join(out)


def email():
    e = ARTIST['email']
    return f'<p class="email" id="email-address"><a href="mailto:{esc(e)}">{esc(e)}</a></p>'


def press_kit():
    songs = ''.join(f'<li>{esc(s)}</li>' for s in kit_songs)
    images = ''.join(f'<li>{esc(i)}</li>' for i in kit_images)
    return f'''<article class="book-card" aria-labelledby="kit-title">
      <h3 class="kicker" id="kit-title">Press kit download</h3>
      <p>One ZIP file, {megabytes(kit_size)}, containing {len(kit_songs)} songs (MP3 audio) and {len(kit_images)} images (PNG) for posters and press.</p>
      <a class="btn btn-secondary" href="../{PRESS_KIT}" download aria-describedby="kit-contents-title">
        <svg aria-hidden="true" viewBox="0 0 24 24" width="18" height="18" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M12 3v12m0 0-5-5m5 5 5-5M4 19h16"/></svg>
        Download press kit <span class="file-meta">(ZIP, {megabytes(kit_size)})</span>
      </a>
      <h4 class="kit-heading" id="kit-contents-title">Contents of the press kit</h4>
      <p class="kit-label">Songs (MP3):</p>
      <ul class="kit-list">{songs}</ul>
      <p class="kit-label">Images (PNG):</p>
      <ul class="kit-list">{images}</ul>
    </article>'''


def press_photos():
    out = []
    for n in ('piano', 'performing', 'portrait', 'studio-session'):
        p = f'Images/embedded/epk-ash-stu-{n}.webp'
        out.append(f'<li><img src="{rel_url(p)}" alt="{esc(alt_for(p))}" width="481" height="481" loading="lazy"></li>')
    return ('<ul class="press-photos" role="list" aria-label="Live performance photos of Ash Stu">\n      '
            + '\n      '.join(out) + '\n    </ul>')


def footer():
    links = ''.join(f'<li><a href="{esc(u)}">Ash Stu on {esc(n)}</a></li>' for n, u in profiles.items())
    year = datetime.date.today().year
    logo = f'<img src="{rel_url(ARTIST["logo"])}" alt="{esc(alt_for(ARTIST["logo"]))}" width="56" height="56" loading="lazy">'
    return (logo + '\n  ' + f'<ul class="footer-links" role="list" aria-label="Ash Stu on other sites">{links}</ul>\n'
            f'  <p class="fine-print">© {year} Ash Stu</p>')


# ── JSON-LD ───────────────────────────────────────────────────────────
def jsonld():
    artist_id = SITE + '#artist'
    place = {
        '@type': 'Place',
        'name': f"{ARTIST['city']}, {ARTIST['region']}, {ARTIST['country']}",
        'address': {'@type': 'PostalAddress', 'addressLocality': ARTIST['city'],
                    'addressRegion': ARTIST['region_code'], 'addressCountry': ARTIST['country_code']},
    }
    graph = [
        {
            '@type': 'WebSite', '@id': SITE + '#website', 'url': SITE,
            'name': 'Ash Stu', 'inLanguage': facts['site']['language'],
            'publisher': {'@id': artist_id},
        },
        {
            '@type': 'ProfilePage', '@id': PAGE + '#webpage', 'url': PAGE,
            'name': 'Ash Stu: outsider-folk singer-songwriter from Guthrie, Oklahoma',
            'isPartOf': {'@id': SITE + '#website'}, 'inLanguage': facts['site']['language'],
            'mainEntity': {'@id': artist_id},
            'dateModified': datetime.date.today().isoformat(),
            'primaryImageOfPage': {'@id': SITE + '#portrait'},
        },
        {
            '@type': 'ImageObject', '@id': SITE + '#portrait',
            'contentUrl': abs_url('Images/Profile-3.webp'), 'description': alt_for('Images/Profile-3.webp'),
            'width': 800, 'height': 800,
        },
        {
            '@type': 'MusicGroup', '@id': artist_id,
            'name': ARTIST['name'], 'alternateName': ARTIST['legal_name'],
            'description': ARTIST['description'], 'url': SITE,
            'genre': ARTIST['genres'],
            'image': {'@id': SITE + '#portrait'},
            'logo': abs_url(ARTIST['logo']),
            'foundingLocation': place, 'location': place,
            'member': {'@type': 'Person', '@id': SITE + '#person', 'name': ARTIST['legal_name'],
                       'alternateName': ARTIST['name'], 'homeLocation': place},
            'email': ARTIST['email'],
            'contactPoint': {'@type': 'ContactPoint', 'contactType': 'Booking and press',
                             'email': ARTIST['email'], 'availableLanguage': 'English'},
            'sameAs': list(profiles.values()),
            'album': [{'@id': SITE + '#' + r['slug']} for r in releases],
        },
    ]
    for r in releases:
        tracks = []
        for i, t in enumerate(r['tracks']):
            rec = {
                '@type': 'MusicRecording', 'name': t['title'], 'position': i + 1,
                'duration': iso_dur(t['seconds']), 'byArtist': {'@id': artist_id},
                'inAlbum': {'@id': SITE + '#' + r['slug']},
                'audio': {'@type': 'AudioObject', 'contentUrl': abs_url(t['file']),
                          'encodingFormat': 'audio/mpeg', 'duration': iso_dur(t['seconds'])},
            }
            if r['featured']:
                rec['contributor'] = [{'@type': 'Person', 'name': n} for n in r['featured']]
            tracks.append(rec)
        graph.append({
            '@type': 'MusicAlbum', '@id': SITE + '#' + r['slug'],
            'name': r['full_title'],
            **({'alternateName': r['name']} if r['full_title'] != r['name'] else {}),
            'albumReleaseType': 'AlbumRelease' if r['type'] == 'Album' else 'SingleRelease',
            'datePublished': r['date'],
            'numTracks': r['count'],
            'duration': iso_dur(r['seconds']),
            'byArtist': {'@id': artist_id},
            'image': abs_url(r['art']),
            'sameAs': [u for u in (r.get('apple'), r.get('spotify')) if u],
            'track': tracks,
        })
    for v in videos:
        obj = {
            '@type': 'VideoObject', '@id': SITE + '#' + v['slug'],
            'name': f"{v['title']} (official music video)",
            'description': f"Official music video for the song \"{v['title']}\" by Ash Stu.",
            'thumbnailUrl': abs_url(v['thumb']),
            'contentUrl': abs_url(v['file']),
            'encodingFormat': 'video/mp4',
            'duration': iso_dur(v['seconds']),
            'creator': {'@id': artist_id},
        }
        if v['date']:
            obj['uploadDate'] = v['date']
        if v['yt_id']:
            obj['embedUrl'] = f"https://www.youtube.com/embed/{v['yt_id']}"
            obj['url'] = v['youtube']
        graph.append(obj)
    graph.append({
        '@type': 'DataDownload', '@id': SITE + '#press-kit',
        'name': 'Ash Stu press kit',
        'description': (f'ZIP file with {len(kit_songs)} songs (MP3): {", ".join(kit_songs)}; '
                        f'and {len(kit_images)} images (PNG): {", ".join(kit_images)}.'),
        'contentUrl': abs_url(PRESS_KIT), 'encodingFormat': 'application/zip',
        'contentSize': megabytes(kit_size).replace(' megabytes', ' MB'),
        'creator': {'@id': artist_id},
    })
    body = json.dumps({'@context': 'https://schema.org', '@graph': graph}, ensure_ascii=False, indent=1)
    return '<script type="application/ld+json">\n' + body.replace('</', '<\\/') + '\n</script>'


# ── ASSEMBLE ──────────────────────────────────────────────────────────
FRAGMENTS = {
    'JSONLD': jsonld(), 'HERO_PHOTO': hero_photo(), 'NEWEST_RELEASE': newest_release(),
    'DISCOGRAPHY_SUMMARY': discography_summary(), 'RECORDS': records(),
    'VIDEOS_SUMMARY': videos_summary(), 'VIDEOS': video_cards(),
    'BIO': bio(), 'SNAPSHOTS': snapshots(), 'EMAIL': email(),
    'PRESS_KIT': press_kit(), 'PRESS_PHOTOS': press_photos(), 'FOOTER': footer(),
}
page = open(TEMPLATE, encoding='utf-8').read()
for key, frag in FRAGMENTS.items():
    marker = f'<!--@GENERATED:{key}-->'
    if marker not in page:
        sys.exit(f'Template is missing {marker}')
    page = page.replace(marker, frag)
leftover = re.findall(r'<!--@GENERATED:\w+-->', page)
if leftover:
    sys.exit(f'No generator for {leftover}')

# Strip author comments: they're design notes for humans, noise for crawlers.
page = re.sub(r'<!--.*?-->\n?', '', page, flags=re.S)
page = re.sub(r'\n[ \t]*\n(?:[ \t]*\n)+', '\n\n', page)

with open(OUTPUT, 'w', encoding='utf-8') as f:
    f.write(page)
print(f'Wrote {OUTPUT}: {len(releases)} releases, {sum(r["count"] for r in releases)} songs, '
      f'{len(videos)} videos, press kit {megabytes(kit_size)}')
