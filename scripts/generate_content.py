#!/usr/bin/env python3
"""Scan Audio/ and Videos/ and emit releases.json and videos.json at the
repo root. Run by the update-content GitHub Action whenever those folders
change - see .github/workflows/update-content.yml.

Can also be run locally: python3 scripts/generate_content.py
"""
import datetime
import json
import os
import re
import subprocess
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
os.chdir(ROOT)

AUDIO_EXTS = ('.mp3',)
VIDEO_EXTS = ('.mp4', '.mov', '.webm')
ART_EXTS = ('.webp', '.png', '.jpg', '.jpeg')


def git_first_added_epoch(path):
    """Epoch timestamp of the first commit that added anything under path.
    Falls back to 0 (sorts last) if the path isn't tracked yet - e.g. it
    was only just added in the same run this script is scanning."""
    try:
        out = subprocess.run(
            ['git', 'log', '--diff-filter=A', '--follow', '--format=%at', '--', path],
            capture_output=True, text=True, check=False
        ).stdout.strip()
        if out:
            return int(out.splitlines()[-1])
    except Exception:
        pass
    return 0


def strip_track_prefix(filename_no_ext):
    return re.sub(r'^\d+\.\s*', '', filename_no_ext)


def track_number(filename_no_ext):
    m = re.match(r'^(\d+)\.', filename_no_ext)
    return int(m.group(1)) if m else None


def parse_upcoming_txt(path):
    """upcoming.txt: songs on the release that aren't out yet, one per
    line as "N. Title" (N = its place on the tracklist). They're listed
    greyed out and can't be played. When one comes out, add its
    "N. Title.mp3" and delete its line here."""
    out = []
    if not os.path.isfile(path):
        return out
    with open(path, encoding='utf-8') as fh:
        for line in fh:
            m = re.match(r'^\s*(\d+)\.\s*(.+?)\s*$', line)
            if m:
                out.append({'num': int(m.group(1)), 'title': m.group(2)})
            elif line.strip():
                print(f'  WARNING: {path}: "{line.strip()}" is not "N. Title" - ignoring', file=sys.stderr)
    return out


def classify_release(track_count):
    if track_count >= 7:
        return 'Album'
    if track_count >= 4:
        return 'EP'
    return 'Single'


def parse_links_txt(path):
    links = {}
    if not os.path.isfile(path):
        return links
    with open(path, encoding='utf-8') as f:
        for line in f:
            line = line.strip()
            if not line or ':' not in line:
                continue
            key, _, val = line.partition(':')
            links[key.strip().lower()] = val.strip()
    return links


def find_art(name):
    for ext in ART_EXTS:
        p = os.path.join('Images', 'Releases', name + ext)
        if os.path.isfile(p):
            return p.replace(os.sep, '/')
    return None


def find_thumb(name):
    for ext in ART_EXTS:
        p = os.path.join('Videos', 'Thumbnails', name + ext)
        if os.path.isfile(p):
            return p.replace(os.sep, '/')
    return None


def _int_or_none(v):
    try:
        return int(str(v).strip())
    except (TypeError, ValueError):
        return None


def gen_releases():
    audio_dir = 'Audio'
    if not os.path.isdir(audio_dir):
        return []
    releases = []
    for name in sorted(os.listdir(audio_dir)):
        folder = os.path.join(audio_dir, name)
        if not os.path.isdir(folder):
            continue
        if os.path.isfile(os.path.join(folder, '.hidden')):
            continue
        tracks_files = sorted(
            f for f in os.listdir(folder) if f.lower().endswith(AUDIO_EXTS)
        )
        if not tracks_files:
            continue
        tracks = []
        for f in tracks_files:
            base = os.path.splitext(f)[0]
            title = strip_track_prefix(base)
            track = {
                'title': title,
                'file': os.path.join(folder, f).replace(os.sep, '/'),
            }
            num = track_number(base)
            if num is not None:
                track['num'] = num
            tracks.append(track)
        upcoming = parse_upcoming_txt(os.path.join(folder, 'upcoming.txt'))
        released_nums = {t.get('num') for t in tracks}
        for u in upcoming:
            if u['num'] in released_nums:
                print(f'  WARNING: "{name}" upcoming.txt lists track {u["num"]} ({u["title"]}), '
                      f'but it is already released - remove that line', file=sys.stderr)
        upcoming = [u for u in upcoming if u['num'] not in released_nums]
        art = find_art(name)
        if not art:
            print(f'  WARNING: no cover art found for release "{name}" '
                  f'(looked for Images/Releases/{name}.[webp|png|jpg|jpeg]) - skipping', file=sys.stderr)
            continue
        links = parse_links_txt(os.path.join(folder, 'links.txt'))
        # An explicit release date (links.txt: date: YYYY-MM-DD) drives
        # "latest release" ordering - git history reflects when a file
        # was added to the repo, not when a song actually came out, so
        # it's only a fallback for releases that don't bother setting one.
        sort_val = git_first_added_epoch(folder)
        if links.get('date'):
            try:
                sort_val = datetime.datetime.strptime(links['date'], '%Y-%m-%d').timestamp()
            except ValueError:
                print(f'  WARNING: "{name}" links.txt has an unparseable date '
                      f'"{links["date"]}" (want YYYY-MM-DD) - using file history instead', file=sys.stderr)
        # links.txt "type: Album" (or EP / Single) overrides the track-count
        # guess - e.g. an album with only some of its songs on the site.
        rtype = classify_release(len(tracks))
        if links.get('type'):
            t = links['type'].strip().lower()
            if t in ('album', 'ep', 'single'):
                rtype = {'album': 'Album', 'ep': 'EP', 'single': 'Single'}[t]
            else:
                print(f'  WARNING: "{name}" links.txt type "{links["type"]}" is not Album, EP or Single - ignoring', file=sys.stderr)
        releases.append({
            'name': name,
            'type': rtype,
            'art': art,
            'apple': links.get('apple'),
            'spotify': links.get('spotify'),
            'tracks': tracks,
            **({'upcoming': upcoming} if upcoming else {}),
            '_sort': sort_val,
            '_lead': links.get('featured', 'yes').strip().lower() not in ('no', 'false', '0'),
            '_order': _int_or_none(links.get('order')),
        })
    # Discography order: links.txt "order: N" first (1 = top), then newest
    # date first. The featured "Latest release" (r['featured']) is the first
    # release in that order without "featured: no"; it no longer has to sit
    # at the top of the list.
    releases.sort(key=lambda r: (r['_order'] is None, r['_order'] or 0, -r['_sort']))
    lead = next((r for r in releases if r['_lead']), releases[0] if releases else None)
    for r in releases:
        r['featured'] = r is lead
        del r['_sort'], r['_lead'], r['_order']
    return releases


def gen_videos():
    video_dir = 'Videos'
    if not os.path.isdir(video_dir):
        return []
    videos = []
    for f in sorted(os.listdir(video_dir)):
        path = os.path.join(video_dir, f)
        if not os.path.isfile(path):
            continue
        base, ext = os.path.splitext(f)
        if ext.lower() not in VIDEO_EXTS:
            continue
        txt_path = os.path.join(video_dir, base + '.txt')
        youtube = None
        if os.path.isfile(txt_path):
            with open(txt_path, encoding='utf-8') as fh:
                youtube = fh.read().strip() or None
        cap = os.path.join(video_dir, 'Captions', base + '.vtt')
        videos.append({
            'title': base,
            'file': path.replace(os.sep, '/'),
            'youtube': youtube,
            'captions': cap.replace(os.sep, '/') if os.path.isfile(cap) else None,
            'thumb': find_thumb(base),
            '_sort': git_first_added_epoch(path),
        })
    # Optional Videos/order.txt: one video title per line, top first.
    # Listed videos come first in that order; the rest follow, newest first.
    order_path = os.path.join(video_dir, 'order.txt')
    order = []
    if os.path.isfile(order_path):
        with open(order_path, encoding='utf-8') as fh:
            order = [l.strip() for l in fh if l.strip()]
    rank = {t: i for i, t in enumerate(order)}
    videos.sort(key=lambda v: -v['_sort'])
    videos.sort(key=lambda v: rank.get(v['title'], len(order)))
    for v in videos:
        del v['_sort']
    return videos




LRC_LINE = re.compile(r'^\[(\d+):(\d+(?:\.\d+)?)\](.*)$')


def parse_lyrics_txt(path):
    """{track number: [lines]} from an album's lyrics.txt ("TRACK N: Title"
    headings, one lyric line per line, blank lines ignored)."""
    if not os.path.isfile(path):
        return {}
    src = open(path, encoding='utf-8').read()
    out = {}
    for m in re.finditer(r'^TRACK (\d+):[^\n]*\n(.*?)(?=^TRACK \d+:|\Z)', src, re.S | re.M):
        lines = [l.strip() for l in m.group(2).splitlines() if l.strip()]
        if lines:
            out[int(m.group(1))] = lines
    return out


def gen_lyrics(releases):
    """Lyrics for each track, keyed by its audio file path.

    Source: a .lrc file with the same name as the MP3 ("01. Song.lrc" next
    to "01. Song.mp3"). Timestamped lines -> synced lyrics the player can
    highlight in real time. Edit the .lrc by hand (or in any LRC editor) to
    fix a line's timing; this script just reads it.
    """
    out = {}
    album_txt = {}
    for rel in releases:
        for t in rel['tracks']:
            lrc = os.path.join(ROOT, os.path.splitext(t['file'])[0] + '.lrc')
            if not os.path.isfile(lrc):
                # No timing file: fall back to the album's lyrics.txt
                # ("TRACK N: Title" sections, N = the file's number prefix)
                # and show the words without line-by-line highlighting.
                folder = os.path.dirname(os.path.join(ROOT, t['file']))
                if folder not in album_txt:
                    album_txt[folder] = parse_lyrics_txt(os.path.join(folder, 'lyrics.txt'))
                m = re.match(r'(\d+)\.', os.path.basename(t['file']))
                plain = album_txt[folder].get(int(m.group(1))) if m else None
                if plain:
                    out[t['file']] = {'synced': False, 'lines': [[None, l] for l in plain]}
                continue
            lines = []
            for raw in open(lrc, encoding='utf-8').read().splitlines():
                m = LRC_LINE.match(raw.strip())
                if m and m.group(3).strip():
                    lines.append([round(int(m.group(1)) * 60 + float(m.group(2)), 2), m.group(3).strip()])
            lines.sort(key=lambda l: l[0])
            if lines:
                out[t['file']] = {'synced': True, 'lines': lines}
    return out


def write_json(name, data):
    path = os.path.join(ROOT, name)
    with open(path, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
        f.write('\n')
    print(f'Wrote {name}: {len(data)} item(s)')


def touch_sitemap():
    """Bump sitemap.xml's <lastmod> to today whenever content regenerates,
    so it doesn't silently go stale - search engines use it as a signal
    for how often to recrawl."""
    path = os.path.join(ROOT, 'sitemap.xml')
    if not os.path.isfile(path):
        return
    with open(path, encoding='utf-8') as f:
        xml = f.read()
    today = datetime.date.today().isoformat()
    new_xml = re.sub(r'<lastmod>\d{4}-\d{2}-\d{2}</lastmod>', f'<lastmod>{today}</lastmod>', xml, count=1)
    if new_xml != xml:
        with open(path, 'w', encoding='utf-8') as f:
            f.write(new_xml)
        print(f'Updated sitemap.xml lastmod to {today}')


if __name__ == '__main__':
    releases = gen_releases()
    write_json('releases.json', releases)
    write_json('lyrics.json', gen_lyrics(releases))
    write_json('videos.json', gen_videos())
    touch_sitemap()
