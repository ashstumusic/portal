#!/usr/bin/env python3
"""Album downloads: one ready-made ZIP per release.

Each release's Download button is a plain link to a finished ZIP, so the visitor's browser starts saving the moment the
button is pressed and does the whole download itself (its own progress bar, pause and resume, nothing held in memory,
carries on if the page is closed). The ZIPs are too big to keep in the site's repository next to the songs, so they live
as files on a GitHub Release (tag "downloads") of the same repository, which serves them from GitHub's file CDN.

A ZIP holds "<Release> - Ash Stu/" with the release's MP3s (the same files the player uses), the cover and, when there is
one, lyrics.txt. Files are stored, not compressed (MP3s do not shrink, and it keeps making them quick). The same input
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

def plan(rel):
    """-> {'file', 'url', 'bytes', 'entries': [(name inside the ZIP, path on disk)]} or None if the release has no songs."""
    tracks = rel.get('tracks') or []
    if not tracks: return None
    folder = _safe(rel['name'] + ' - Ash Stu'); entries = [(folder + '/' + _safe(os.path.basename(t['file'])), t['file']) for t in tracks]
    if rel.get('art') and os.path.isfile(os.path.join(ROOT, rel['art'])): entries.append((folder + '/cover.' + rel['art'].rsplit('.', 1)[-1], rel['art']))
    ly = os.path.dirname(tracks[0]['file']) + '/lyrics.txt'
    if os.path.isfile(os.path.join(ROOT, ly)): entries.append((folder + '/lyrics.txt', ly))
    size = 22 + sum(76 + 2 * len(n.encode('utf-8')) + os.path.getsize(os.path.join(ROOT, p)) for n, p in entries)   # 30-byte header + name + data, 46 + name in the index, 22 to close
    f = asset_name(rel['name'])
    return {'file': f, 'url': 'https://github.com/%s/releases/download/%s/%s' % (REPO, TAG, f), 'bytes': size, 'entries': entries}

def build(rel):
    pl = plan(rel); os.makedirs(OUT, exist_ok=True); path = os.path.join(OUT, pl['file'])
    with zipfile.ZipFile(path, 'w', zipfile.ZIP_STORED) as z:
        for name, src in pl['entries']:
            zi = zipfile.ZipInfo(name, STAMP); zi.compress_type = zipfile.ZIP_STORED; zi.external_attr = 0o644 << 16; zi.create_system = 3
            z.writestr(zi, open(os.path.join(ROOT, src), 'rb').read())
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
