#!/usr/bin/env python3
"""Scan Audio/, Videos/, and Journal/ and emit releases.json, videos.json,
and journal.json at the repo root. Run by the update-content GitHub Action
whenever those folders change - see .github/workflows/update-content.yml.

Can also be run locally: python3 scripts/generate_content.py
"""
import datetime
import html
import json
import os
import re
import subprocess
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
os.chdir(ROOT)

# Quoted spans that are scare quotes / use-mention, not spoken dialogue -
# excluded from the auto-bold-quotes rule below since that rule can't tell
# the two apart syntactically (source uses the same curly quotes for both).
SCARE_QUOTES = {
    '“sky”', '“humane”', '“lose”', '“Old Man”', '“Coach,”',
    '“goof”', '“coolest”', '“problem”',
}

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


QUOTE_LINE_RE = re.compile(r'^[“"].*—\s*\S.*$')


def parse_essay_or_entry(path, category):
    with open(path, encoding='utf-8') as f:
        raw = f.read()
    lines = raw.split('\n')
    idx = 0

    substack = None
    if lines and lines[0].strip().lower().startswith('substack link:'):
        substack = lines[0].split(':', 1)[1].strip()
        idx = 1

    while idx < len(lines) and lines[idx].strip() == '':
        idx += 1

    title_lines = []
    while idx < len(lines) and not lines[idx].lstrip().startswith('- '):
        title_lines.append(lines[idx])
        idx += 1
    if idx >= len(lines):
        raise ValueError(f'{path}: missing "- Date" line (required to terminate the title block)')
    date_line = lines[idx].lstrip()[2:].strip()
    idx += 1

    tl = list(title_lines)
    if not tl:
        raise ValueError(f'{path}: no title found')
    tl[0] = re.sub(r'^["“]', '', tl[0])
    tl[0] = re.sub(r'["”]\s*$', '', tl[0])
    tl[-1] = re.sub(r'["”]\s*$', '', tl[-1])
    headline = tl[0].strip()
    dek = tl[1].strip() if len(tl) > 1 else None

    while idx < len(lines) and lines[idx].strip() == '':
        idx += 1
    body_lines = lines[idx:]
    while body_lines and body_lines[-1].strip() == '':
        body_lines.pop()

    blocks, cur = [], []
    for ln in body_lines:
        if ln.strip() == '':
            if cur:
                blocks.append(cur)
                cur = []
        else:
            cur.append(ln)
    if cur:
        blocks.append(cur)

    html_parts = []
    word_count = len(headline.split()) + (len(dek.split()) if dek else 0)

    for block in blocks:
        groups = []
        for ln in block:
            kind = 'quote' if QUOTE_LINE_RE.match(ln.strip()) else 'prose'
            if groups and groups[-1][0] == kind:
                groups[-1][1].append(ln)
            else:
                groups.append((kind, [ln]))
        for kind, glines in groups:
            if kind == 'quote':
                lines_html = []
                for l in glines:
                    l = l.strip()
                    if '—' in l:
                        q, cite = re.split(r'\s—\s', l, maxsplit=1)
                    else:
                        q, cite = l, ''
                    cite_html = f' <cite>&mdash; {html.escape(cite)}</cite>' if cite else ''
                    lines_html.append(f'<p>{html.escape(q)}{cite_html}</p>')
                html_parts.append('<blockquote class="journal-epigraph">' + ''.join(lines_html) + '</blockquote>')
            else:
                text = ' '.join(l.strip() for l in glines)
                word_count += len(text.split())
                escaped = html.escape(text)
                escaped = re.sub(
                    r'“[^“”]*”',
                    lambda m: m.group(0) if m.group(0) in SCARE_QUOTES else f'<strong>{m.group(0)}</strong>',
                    escaped,
                )
                html_parts.append(f'<p>{escaped}</p>')

    return {
        'category': category,
        'headline': headline,
        'dek': dek,
        'date': date_line,
        'substack': substack,
        'bodyHtml': '\n'.join(html_parts),
        'readMin': max(1, round(word_count / 200)),
    }


def parse_date_epoch(date_str):
    """Best-effort parse of a human date line ('May 11, 2026') to epoch,
    for sorting. Returns None if it doesn't parse."""
    if not date_str:
        return None
    for fmt in ('%b %d, %Y', '%B %d, %Y'):
        try:
            return datetime.datetime.strptime(date_str, fmt).timestamp()
        except ValueError:
            continue
    return None


def parse_lyrics(path):
    base = os.path.splitext(os.path.basename(path))[0]
    with open(path, encoding='utf-8') as f:
        raw = f.read().strip('\n')
    paras = [p.strip() for p in re.split(r'\n\s*\n', raw) if p.strip()]
    body_html = '\n'.join(f'<p>{html.escape(p)}</p>' for p in paras)
    return {
        'category': 'lyrics',
        'headline': base,
        'dek': None,
        'date': None,
        'substack': None,
        'bodyHtml': body_html,
        'readMin': None,
    }


def find_journal_audio(base_name):
    p = os.path.join('Journal', 'Audio', base_name + '.mp3')
    return p.replace(os.sep, '/') if os.path.isfile(p) else None


def gen_journal():
    entries = []
    for category, sub in (('essay', 'Essays'), ('entry', 'Entries')):
        folder = os.path.join('Journal', sub)
        if not os.path.isdir(folder):
            continue
        for f in sorted(os.listdir(folder)):
            if not f.lower().endswith('.txt'):
                continue
            path = os.path.join(folder, f)
            try:
                entry = parse_essay_or_entry(path, category)
            except ValueError as e:
                print(f'  WARNING: skipping "{path}": {e}', file=sys.stderr)
                continue
            # Prefer the essay's own dateline for ordering (several can
            # land in the same commit, which would otherwise tie-break
            # arbitrarily); fall back to git history if it doesn't parse.
            entry['_sort'] = parse_date_epoch(entry['date']) or git_first_added_epoch(path)
            # Optional spoken-audio version, matched by filename (same
            # convention as Videos/Thumbnails) - absent until someone
            # drops a matching mp3 in Journal/Audio/.
            entry['audio'] = find_journal_audio(os.path.splitext(f)[0])
            entries.append(entry)

    lyrics_folder = os.path.join('Journal', 'Lyrics')
    if os.path.isdir(lyrics_folder):
        for f in sorted(os.listdir(lyrics_folder)):
            if not f.lower().endswith('.txt'):
                continue
            path = os.path.join(lyrics_folder, f)
            entry = parse_lyrics(path)
            entry['_sort'] = git_first_added_epoch(path)
            entries.append(entry)

    entries.sort(key=lambda e: e['_sort'], reverse=True)
    for e in entries:
        del e['_sort']
    return entries


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
    write_json('journal.json', gen_journal())
    touch_sitemap()
