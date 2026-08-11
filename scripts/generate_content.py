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
            tracks.append({
                'title': title,
                'file': os.path.join(folder, f).replace(os.sep, '/'),
            })
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
        releases.append({
            'name': name,
            'type': classify_release(len(tracks)),
            'art': art,
            'apple': links.get('apple'),
            'spotify': links.get('spotify'),
            'tracks': tracks,
            '_sort': sort_val,
        })
    releases.sort(key=lambda r: r['_sort'], reverse=True)
    for r in releases:
        del r['_sort']
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
        videos.append({
            'title': base,
            'file': path.replace(os.sep, '/'),
            'youtube': youtube,
            'thumb': find_thumb(base),
            '_sort': git_first_added_epoch(path),
        })
    videos.sort(key=lambda v: v['_sort'], reverse=True)
    for v in videos:
        del v['_sort']
    return videos




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
    write_json('releases.json', gen_releases())
    write_json('videos.json', gen_videos())
    touch_sitemap()
