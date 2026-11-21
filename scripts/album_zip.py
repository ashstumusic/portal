#!/usr/bin/env python3
"""Album downloads: one ready-made ZIP per release.

Each release's Download button is a plain link to a finished ZIP, so the visitor's browser starts saving the moment the
button is pressed and does the whole download itself (its own progress bar, pause and resume, nothing held in memory,
carries on if the page is closed). The ZIPs are too big to keep in the site's repository next to the songs, so they live
as files on a GitHub Release (tag "downloads") of the same repository, which serves them from GitHub's file CDN.

A ZIP holds "<Release> - Ash Stu/" with the release's MP3s, the cover and, when there is one, lyrics.txt. The MP3s are
the files the player uses with one difference: each copy in the ZIP carries proper song information (title, artist,
album, track number, year and the cover), written here. The files in Audio/ are not touched: several had no
information at all, or leftovers from the tools that made them, so a downloaded album showed up in a music app as
"Unknown artist". Only the label at the front of the file is replaced; the sound is byte-for-byte the same. Files are stored, not compressed (MP3s do not shrink, and it keeps making them quick). The same input
always gives byte-for-byte the same ZIP, so an unchanged release is never uploaded twice.

  python3 scripts/album_zip.py            build every ZIP into .zips/ (ignored by git) and check each one
  python3 scripts/album_zip.py --upload   also put new or changed ones on the GitHub Release (needs the gh tool, signed in)

generate_content.py calls plan() to write each release's "zip" entry (link and exact size) into releases.json; the
update-content GitHub Action runs this file with --upload whenever the songs change.
"""
import hashlib, json, os, re, subprocess, sys, unicodedata, zipfile
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
REPO, TAG = 'ashstumusic/portal', 'downloads'
OUT = os.path.join(ROOT, '.zips')
STAMP = (2020, 1, 1, 0, 0, 0)          # a fixed date inside the ZIP: the same songs always make the same file

def _safe(n): return re.sub(r'\s+', ' ', re.sub(r'[\\/:*?"<>|]+', ' ', str(n))).strip()
def asset_name(release_name):
    """The file's name on the Release: plain letters, digits and hyphens (GitHub rewrites anything else)."""
    base = release_name if 'ash stu' in release_name.lower() else release_name + ' Ash Stu'
    base = unicodedata.normalize('NFKD', base).encode('ascii', 'ignore').decode()
    return re.sub(r'[^A-Za-z0-9]+', '-', base).strip('-') + '.zip'


# ── Song information for the copies in the ZIP ───────────────────────────────────────────────────────────────────────
# Written by hand (ID3 version 2.3, the one every player reads) so that this needs nothing installed and the same
# songs always give the same bytes. An MP3 is [label][sound][old-style label]: the label at the front (ID3v2) and the
# 128-byte one some files have at the end (ID3v1) are dropped and a fresh front label is written in their place.
ARTIST, GENRE = 'Ash Stu', 'Outsider'
def _audio_span(path):
    """(start, end) of the sound itself inside the file, without its labels."""
    size = os.path.getsize(path); start = 0
    with open(path, 'rb') as f:
        head = f.read(10)
        while len(head) == 10 and head[:3] == b'ID3':                      # (a file can carry more than one front label)
            n = 10 + ((head[6] & 0x7f) << 21 | (head[7] & 0x7f) << 14 | (head[8] & 0x7f) << 7 | (head[9] & 0x7f))
            if head[5] & 0x10: n += 10                                    # a footer
            start += n; f.seek(start); head = f.read(10)
        end = size
        if size - start >= 128:
            f.seek(size - 128)
            if f.read(3) == b'TAG': end = size - 128
    return start, end
def _frame(fid, data): return fid.encode('ascii') + len(data).to_bytes(4, 'big') + b'\x00\x00' + data
def _text(fid, value): return _frame(fid, b'\x01' + b'\xff\xfe' + str(value).encode('utf-16-le'))
def _release_year(release_name):
    try:
        for line in open(os.path.join(ROOT, 'Audio', release_name, 'links.txt'), encoding='utf-8'):
            m = re.match(r'\s*date\s*:\s*(\d{4})-\d{2}-\d{2}', line)
            if m: return m.group(1)
    except OSError: pass
    return ''
def _cover_jpeg(rel):
    """The cover as a JPEG for the label (Images/share/<album>.jpg, made by build_lyrics_pages.py), or None.
    Music apps read JPEG covers reliably; the site's own covers are WebP, which many do not."""
    stem = os.path.splitext(os.path.basename(rel.get('art') or ''))[0]
    f = os.path.join(ROOT, 'Images', 'share', re.sub(r'[^a-z0-9]+', '-', stem.lower()).strip('-') + '.jpg')
    return f if stem and os.path.isfile(f) else None
def _label(rel, t, num, total, cover):
    frames = _text('TIT2', t['title']) + _text('TPE1', ARTIST) + _text('TPE2', ARTIST) + _text('TALB', rel['name']) + _text('TRCK', '%d/%d' % (num, total)) + _text('TCON', GENRE)
    y = _release_year(rel['name'])
    if y: frames += _text('TYER', y)
    if cover: frames += _frame('APIC', b'\x00' + b'image/jpeg\x00' + b'\x03' + b'\x00' + cover)
    n = len(frames)
    return b'ID3\x03\x00\x00' + bytes([(n >> 21) & 0x7f, (n >> 14) & 0x7f, (n >> 7) & 0x7f, n & 0x7f]) + frames
def _song(rel, t, num, total, cover):
    """(the label to write, start and end of the sound in the file) for one song's copy in the ZIP."""
    start, end = _audio_span(os.path.join(ROOT, t['file']))
    return _label(rel, t, num, total, cover), start, end

def plan(rel):
    """-> {'file', 'url', 'bytes', 'entries': [(name inside the ZIP, path on disk)], 'songs': {path: (label, start, end)}}
    or None if the release has no songs."""
    tracks = rel.get('tracks') or []
    if not tracks: return None
    folder = _safe(rel['name'] + ' - Ash Stu'); entries = [(folder + '/' + _safe(os.path.basename(t['file'])), t['file']) for t in tracks]
    if rel.get('art') and os.path.isfile(os.path.join(ROOT, rel['art'])): entries.append((folder + '/cover.' + rel['art'].rsplit('.', 1)[-1], rel['art']))
    ly = os.path.dirname(tracks[0]['file']) + '/lyrics.txt'
    if os.path.isfile(os.path.join(ROOT, ly)): entries.append((folder + '/lyrics.txt', ly))
    total = len(tracks) + len(rel.get('upcoming') or [])
    cj = _cover_jpeg(rel); cover = open(cj, 'rb').read() if cj else None
    songs = {t['file']: _song(rel, t, t.get('num', i + 1), total, cover) for i, t in enumerate(tracks)}
    def length(pth):
        if pth in songs: lab, a, b = songs[pth]; return len(lab) + (b - a)
        return os.path.getsize(os.path.join(ROOT, pth))
    size = 22 + sum(76 + 2 * len(n.encode('utf-8')) + length(pth) for n, pth in entries)   # 30-byte header + name + data, 46 + name in the index, 22 to close
    f = asset_name(rel['name'])
    return {'file': f, 'url': 'https://github.com/%s/releases/download/%s/%s' % (REPO, TAG, f), 'bytes': size, 'entries': entries, 'songs': songs}

def live_plan(rel):
    """The album download as the visitor's browser makes it (owner's request: "do the album downloads live too"; no ZIP is
    stored anywhere): -> {'name': file name, 'bytes': about how big, 'files': [{'path', 'src', 'bytes', 'tag'?}]} or None.
    Same contents as before: the songs (each labelled: title, artist, album, track, genre, year, cover), the cover and,
    when there is one, lyrics.txt, in one folder named like the file. The label is written in the browser (liveZip in
    index-src.html); the sound is the site's own file, unchanged."""
    tracks = rel.get('tracks') or []
    if not tracks: return None
    base = rel['name'] if 'ash stu' in rel['name'].lower() else 'Ash Stu - ' + rel['name']
    folder = _safe(base) + '/'
    total = len(tracks) + len(rel.get('upcoming') or [])
    cj = _cover_jpeg(rel); cover = os.path.relpath(cj, ROOT).replace(os.sep, '/') if cj else ''
    year = _release_year(rel['name']) or (rel.get('date') or '')[:4] or str(rel.get('year') or '')
    files = []
    for i, t in enumerate(tracks):
        tag = {'title': t['title'], 'album': rel['name'], 'track': '%d/%d' % (t.get('num', i + 1), total), 'genre': GENRE, 'cover': cover}
        if year: tag['year'] = year
        files.append({'path': folder + _safe(os.path.basename(t['file'])), 'src': t['file'], 'tag': tag})
    art = rel.get('art') or ''
    png = os.path.splitext(art)[0] + '.png'
    art = png if art and os.path.isfile(os.path.join(ROOT, png)) else art
    if art and os.path.isfile(os.path.join(ROOT, art)): files.append({'path': folder + _safe(rel['name'] + ' - Cover') + os.path.splitext(art)[1], 'src': art})   # ("Ash Stu, Vol. II - Cover.png": says what it is, even out of its folder)
    ly = os.path.dirname(tracks[0]['file']) + '/lyrics.txt'
    if os.path.isfile(os.path.join(ROOT, ly)): files.append({'path': folder + _safe(rel['name'] + ' - Lyrics') + '.txt', 'src': ly})
    for f in files: f['bytes'] = os.path.getsize(os.path.join(ROOT, f['src']))
    return {'name': _safe(base) + '.zip', 'bytes': sum(f['bytes'] for f in files), 'files': files}

def build(rel):
    pl = plan(rel); os.makedirs(OUT, exist_ok=True); path = os.path.join(OUT, pl['file'])
    with zipfile.ZipFile(path, 'w', zipfile.ZIP_STORED) as z:
        for name, src in pl['entries']:
            zi = zipfile.ZipInfo(name, STAMP); zi.compress_type = zipfile.ZIP_STORED; zi.external_attr = 0o644 << 16; zi.create_system = 3
            data = open(os.path.join(ROOT, src), 'rb').read()
            if src in pl['songs']: lab, a, b = pl['songs'][src]; data = lab + data[a:b]   # the fresh label, then the sound unchanged
            z.writestr(zi, data)
    assert os.path.getsize(path) == pl['bytes'], (pl['file'], os.path.getsize(path), pl['bytes'])   # releases.json promises this size
    with zipfile.ZipFile(path) as z: assert z.testzip() is None
    h = hashlib.sha256()
    with open(path, 'rb') as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b''): h.update(chunk)
    return path, pl, h.hexdigest()

def gh(*a, check=True): return subprocess.run(['gh', *a, '-R', REPO], check=check, capture_output=True, text=True)

if __name__ == '__main__':
    os.chdir(ROOT); upload = '--upload' in sys.argv
    built = [build(r) for r in json.load(open('releases.json', encoding='utf-8')) if r.get('tracks')]
    for path, pl, sha in built: print('  %-28s %6.1f MB  %d files  sha256 %s' % (pl['file'], pl['bytes'] / 1048576, len(pl['entries']), sha[:12]))
    if upload:
        v = gh('release', 'view', TAG, '--json', 'assets', check=False)
        if v.returncode:
            gh('release', 'create', TAG, '--latest=false', '--title', 'Album downloads', '--notes',
               'The ZIP files behind the Download buttons on ashstu.art. Made by scripts/album_zip.py; replaced automatically when the songs change.')
            have = {}
        else: have = {a['name']: a for a in json.loads(v.stdout)['assets']}
        for path, pl, sha in built:
            a = have.get(pl['file'])
            same = a and a.get('size') == pl['bytes'] and (a.get('digest') in (None, '', 'sha256:' + sha))
            if same: print('  unchanged:', pl['file']); continue
            gh('release', 'upload', TAG, path, '--clobber'); print('  uploaded: ', pl['file'])
        for n in set(have) - {pl['file'] for _, pl, _ in built}:          # a release that no longer exists
            gh('release', 'delete-asset', TAG, n, '--yes'); print('  removed:  ', n)
