#!/usr/bin/env python3
"""Bake the current releases/videos/journal content directly into the
static index.html, mirroring index-src.html's renderReleaseCard /
renderVideoCard / renderJournalEntry / renderFeatured JS functions.

Why: index.html normally ships with empty #releases-grid / #video-grid
/ #journal-list containers that JS fills in at runtime by fetching
releases.json / videos.json / journal.json. That's invisible to any
crawler or scraper that doesn't execute JavaScript (most AI/LLM
crawlers included) - they'd see three empty <div>s. This script
injects the same HTML those JS functions would produce directly into
index.html after build-fast.py runs, so the raw HTML payload already
has the real content. JS still re-fetches and re-renders on top for
real browsers, so this is purely additive - it only changes what a
non-JS request sees.

Must run AFTER build-fast.py, against its freshly-built index.html
(whose grid containers are still pristine/empty) - not designed to be
idempotent against an already-injected file.
"""
import html as htmlmod
import json
import os
import re
import sys

from build_lyrics_pages import stanzas, slugify

LYRICS = {}   # lyrics.json, loaded in main()


def song_words(releases, lyrics):
    """One-word lookups for the site's search: {'songs': [...], 'words': {word: index}}.
    See scripts/song_keys.py."""
    import song_keys
    songs, used = [], set()
    for rel in releases:
        rows = [(t['title'], bool((lyrics.get(t['file']) or {}).get('lines')), False) for t in rel.get('tracks', [])]
        rows += [(u['title'], bool((lyrics.get(u.get('lyrics') or '') or {}).get('lines')), True) for u in rel.get('upcoming', [])]
        for title, has_page, unreleased in rows:
            slug = slugify(title)
            if has_page:
                if slug in used:
                    slug = f"{slug}-{slugify(rel['name'])}"
                used.add(slug)
            songs.append({'title': title, 'release': rel['name'], 'slug': slug if has_page else '', 'unreleased': unreleased})
    keys, lookup = song_keys.assign([s['title'] for s in songs])
    index = {s['title']: i for i, s in enumerate(songs)}
    for s in songs:
        s['key'] = keys[s['title']]
    return {'songs': songs, 'words': {w: index[t] for w, t in sorted(lookup.items())}}


def lyrics_html(file):
    """A song's full lyrics as a collapsed panel (one <p> per verse), so
    crawlers and no-JS readers get them in the page itself."""
    entry = LYRICS.get(file)
    if not entry or not entry.get('lines'):
        return ''
    verses = ''.join('<p>' + '<br>'.join(esc(l) for l in v) + '</p>' for v in stanzas(entry, file))
    return f'<details class="rel-lyrics-static"><summary>Lyrics</summary>{verses}</details>'

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
os.chdir(ROOT)


def esc(s):
    if s is None:
        return ''
    return (str(s).replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;')
            .replace('"', '&quot;').replace("'", '&#39;'))


def enc_path(p):
    return p.replace('"', '%22')


def full_date(iso):
    """'2026-06-12' -> 'June 12, 2026'"""
    y, m, d = iso.split('-')
    return f"{['January','February','March','April','May','June','July','August','September','October','November','December'][int(m) - 1]} {int(d)}, {y}"



def run_time(secs):
    """A release's total length in words, as on its card: "34 min", "1 hr 5 min"."""
    m = int(round(secs / 60))
    return f'{m // 60} hr {m % 60} min' if m >= 60 else f'{max(m, 1)} min'

def rel_summary(rel, upcoming):
    """The line under an album's name (owner, 2026-11-24: "keep polishing the release cards"): how many songs and how
    long, so every album card says the same things in the same place; an album still coming out also says how many are
    ready ("4 of 10 songs out · 14 min · the rest coming soon", which says why some rows are dim). The matching
    JavaScript is relSummary in index-src.html."""
    tr = rel.get("tracks") or []
    if not tr or (len(tr) == 1 and not upcoming): return ''
    secs = sum(t.get("secs", 0) for t in tr)
    t = f'<span class="rp-len"><span class="rp-sep"> · </span>{run_time(secs)}</span>' if secs else ''
    if rel.get("runtime"):   # (the whole album's length, as the owner gives it in links.txt: "about 30 min")
        t = f'<span class="rp-len"><span class="rp-sep"> · </span>about {run_time(rel["runtime"] * 60)}</span>'
    if upcoming:
        return f'<p class="rel-progress">{len(tr)} of {len(tr) + len(upcoming)} songs out{t}<span class="rp-sep"> · </span><span class="rp-rest">the rest coming soon</span></p>'
    return f'<p class="rel-progress">{len(tr)} songs{t}</p>'

def render_release_card(rel, r_idx):
    kind_word = ('Single cover: ' if rel['type'] == 'Single'
                 else 'EP cover: ' if rel['type'] == 'EP'
                 else 'Album cover: ')
    btns = ''
    listen = ''   # streaming links: the card's availability line, apart from its own actions
    if rel.get('apple'):
        listen += (f'<a href="{esc(rel["apple"])}" target="_blank" rel="noopener noreferrer" class="rel-btn" '
                  f'aria-label="Listen on Apple Music: {esc(rel["name"])}" itemprop="url">'
                   f'<span class="pt pt--apple" aria-hidden="true"></span> Apple Music</a>')
    if rel.get('spotify'):
        listen += (f'<a href="{esc(rel["spotify"])}" target="_blank" rel="noopener noreferrer" class="rel-btn" '
                  f'aria-label="Listen on Spotify: {esc(rel["name"])}">'
                   f'<span class="pt pt--spotify" aria-hidden="true"></span> Spotify</a>')
    for key, store in (('ytmusic', 'YouTube Music'), ('deezer', 'Deezer')):
        if rel.get(key):
            listen += (f'<a href="{esc(rel[key])}" target="_blank" rel="noopener noreferrer" class="rel-btn" '
                       f'aria-label="Listen on {store}: {esc(rel["name"])}"><span class="pt pt--{key}" aria-hidden="true"></span> {store}</a>')
    import datetime as _dt
    _out = bool(rel.get('date')) and rel['date'] <= _dt.date.today().isoformat()   # (already out, not on the services yet)
    # (owner, 2026-11-23: "the coming soon tag should be near the top by the release year": a tag in the date line)
    _clock = ('<svg class="soon-ico" aria-hidden="true" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" '
              'stroke-width="2.4" stroke-linecap="round" stroke-linejoin="round"><circle cx="12" cy="12" r="9"/><path d="M12 7v5l3 2"/></svg>')
    rel_tag = (f'<span class="rel-tag{" rel-tag--out" if _out else ""}">{_clock}<span>{"Not on streaming services yet" if _out else "Coming soon to streaming"}</span></span>'
               if not listen or rel.get('soon') else '')
    status = ''
    if listen:
        status += (f'<div class="rel-listen"><span class="rel-listen-label" id="rel-listen-{r_idx}">Listen on</span>'
                   f'<span class="rel-stores" role="group" aria-labelledby="rel-listen-{r_idx}">{listen}</span></div>')
    tracklist = ''
    upcoming = rel.get('upcoming', [])
    if len(rel['tracks']) + len(upcoming) > 1:
        rows = [(t.get('num', i + 1), esc(t['title']) + lyrics_html(t['file'])) for i, t in enumerate(rel['tracks'])]
        rows += [(u['num'], f'{esc(u["title"])} (not released yet)' + (lyrics_html(u['lyrics']) if u.get('lyrics') else '')) for u in upcoming]
        items = ''.join(f'<li value="{n}">{title}</li>' for n, title in sorted(rows, key=lambda r: r[0]))
        tracklist = (f'<div class="rel-tracklist" id="tracklist-{r_idx}">'
                     f'<ol aria-label="Tracklist for {esc(rel["name"])}">{items}</ol></div>')
    # (aria-label: the visible words, "10 tracks", plus which album - three buttons that differ only by a number tell a
    # screen-reader user nothing about what each one opens)
    tl_toggle = (f'<button type="button" class="rel-tl-toggle" aria-expanded="false" aria-controls="tracklist-{r_idx}" aria-label="{len(rel["tracks"]) + len(upcoming)} tracks on {esc(rel["name"])}">'
                 '<svg class="rel-tl-ico" aria-hidden="true" width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.2" stroke-linecap="round"><line x1="9" y1="6" x2="20" y2="6"/><line x1="9" y1="12" x2="20" y2="12"/><line x1="9" y1="18" x2="20" y2="18"/><circle cx="4.5" cy="6" r="1.2" fill="currentColor" stroke="none"/><circle cx="4.5" cy="12" r="1.2" fill="currentColor" stroke="none"/><circle cx="4.5" cy="18" r="1.2" fill="currentColor" stroke="none"/></svg>'
                 f'<span class="rel-tl-label">{len(rel["tracks"]) + len(upcoming)} tracks</span>'
                 '<svg class="rel-tl-chev" aria-hidden="true" width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" '
                 'stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round"><polyline points="6 9 12 15 18 9"/></svg></button>') if tracklist else ''
    return (f'<article class="rel-card" aria-label="{esc(rel["name"])} - {esc(rel["type"])} by Ash Stu" '
            f'itemscope itemtype="https://schema.org/MusicAlbum">'
            f'<div class="rel-info"><p class="rel-cat"><span class="rel-cat-main">{esc(rel["type"])}'
            + (f'<span class="rel-year"><span class="rel-sep"> · </span><time itemprop="datePublished" datetime="{rel["date"]}">{full_date(rel["date"])}</time></span>' if rel.get("date")
               else f'<span class="rel-year"><span class="rel-sep"> · </span><time itemprop="datePublished">{rel["year"]}</time></span>' if rel.get("year") else '') +
            f'</span>{rel_tag}</p><h3 class="rel-name" itemprop="name">{esc(rel["name"])}</h3>'
            + rel_summary(rel, upcoming)   # (owner, 2026-11-24: "the music cards still do not look as good as they can" - says why some rows are dim)
            + '</div>'
            + (f'<div class="rel-avail">{status}</div>' if status else '') +
            f'<div class="rel-art-wrap">'
            f'<img src="{esc(rel["art"])}" alt="{esc(kind_word + rel["name"])}" '
            + (f'srcset="{esc(rel["art"].replace(" ", "%20"))} 504w, {esc(rel["art2x"].replace(" ", "%20"))} 800w" sizes="(max-width: 767px) 160px, 304px" ' if rel.get("art2x") else '') +
            f'class="rel-art" width="504" height="504" loading="lazy" decoding="async" itemprop="image"/>'
            f'</div>'
            f'<div class="rel-btns">{btns}</div>'
            f'{tl_toggle}'
            f'{tracklist}'
            f'{lyrics_html(rel["tracks"][0]["file"]) if len(rel["tracks"]) == 1 and not upcoming else ""}</article>')


RELEASES_FOR_VIDEOS = []   # (set in main: the album each video's song was released on, for its card)
def video_album(title, upcoming=False):   # the album the song is on (released) or will be on (upcoming)
    for r in RELEASES_FOR_VIDEOS:
        for t in (r.get('upcoming' if upcoming else 'tracks') or []):
            if t['title'].lower() == title.lower(): return r['name']
    return ''
def video_from(title):
    out, soon = video_album(title), video_album(title, True)
    if out: return f'From <a href="/albums/{slugify(out)}/">{esc(out)}</a>'
    if soon: return f'From <a href="/albums/{slugify(soon)}/">{esc(soon)}</a>'
    return ''
def render_video_card(v, v_idx):
    yt_btn = ''
    if v.get('youtube'):
        yt_btn = (f'<a class="vid-yt vid-ytbig" href="{esc(v["youtube"])}" target="_blank" rel="noopener noreferrer" '
                  f'aria-label="Watch &quot;{esc(v["title"])}&quot; on YouTube">'
                  f'<span class="pt pt--youtube" aria-hidden="true"></span><span class="btn-word">YouTube</span></a>')
    if v.get('thumb'):
        srcset = (f' srcset="{esc(v["thumb"].replace(" ", "%20"))} 576w, {esc(v["thumb2x"].replace(" ", "%20"))} 1280w" sizes="(max-width: 767px) 160px, 400px"' if v.get('thumb2x') else '')
        thumb_el = f'<img src="{esc(v["thumb"])}"{srcset} alt="Video: {esc(v["title"])} by Ash Stu" width="576" height="324" loading="lazy" decoding="async"/>'
    else:
        thumb_el = f'<video src="{enc_path(v["file"])}" preload="metadata" muted playsinline aria-label="Video thumbnail" alt="Video thumbnail"></video>'
    # Laid out like an album card: the title (and the album it is from), then one row of two buttons - Play, and YouTube,
    # the larger; the thumbnail on the right with nothing over it. Only Play plays (not the card or the thumbnail).
    return (f'<div class="vid-card-wrap">'
            f'<div class="vid-info"><h3 class="vid-title">{esc(v["title"])}</h3>'   # (no "Video · year" line: the section says Videos and every year was the same)
            + (f'<p class="vid-from">{video_from(v["title"])}</p>' if video_from(v['title']) else '<p class="vid-from vid-from--none" aria-hidden="true">&nbsp;</p>')
            + '</div>'
            f'<button type="button" class="vid-card" tabindex="-1" aria-hidden="true" data-video-index="{v_idx}">'
            f'<span class="vid-thumb">{thumb_el}</span>'
            f'</button>'
            f'<div class="vid-btns">{yt_btn}<button type="button" class="vid-yt vid-play" data-video-index="{v_idx}" aria-label="Play &quot;{esc(v["title"])}&quot;">'
            f'<svg width="14" height="14" viewBox="0 0 24 24" fill="currentColor" aria-hidden="true"><polygon points="5,3 19,12 5,21"/></svg><span class="btn-word">Play</span></button></div>'
            f'</div>')


def inject_container(page, container_id, cls_attr, inner_html):
    pattern = re.compile(
        r'(<div [^>]*id="' + re.escape(container_id) + r'"[^>]*>)\s*(</div>)'
    )
    new_page, n = pattern.subn(lambda m: m.group(1) + inner_html + m.group(2), page, count=1)
    if n != 1:
        print(f'  WARNING: could not find empty #{container_id} container to inject into', file=sys.stderr)
    return new_page


def render_kit_shell(page):
    """The press kit card as the page script first draws it (collapsed), written into the page so it is there from the
    first paint: the script later draws the same card in its place, so nothing moves (it used to arrive after the
    first paint and push every section below it down - a visible jump on pages opened at /music/, /videos/, /about/).
    Built from the page's own kit data, exactly as renderPressKit() in index-src.html builds it; marked .kit-shell and
    hidden without JavaScript (those visitors get the section's plain links instead)."""
    import urllib.parse
    m = re.search(r'<script type="application/json" id="kit-data">(.*?)</script>', page, re.S)
    if not m:
        return ''
    kit = json.loads(m.group(1))
    files = kit.get('files') or []
    if not files:
        return ''
    facts = kit.get('facts') or {}
    photos = [f for f in files if f.get('type') == 'photo']
    n_songs = len([f for f in files if f.get('type') == 'song'])
    has_lyr = any(f.get('type') == 'text' and re.search('lyrics', f.get('name', ''), re.I) for f in files)
    n_vids = len([f for f in files if f.get('type') == 'video'])
    sheet = next((f for f in files if f.get('type') == 'text' and re.search('fact sheet', f.get('name', ''), re.I)), None)
    lead = next((f for f in photos if re.search('headshot-1', f.get('name', ''), re.I)), None) or next((f for f in photos if not re.search('logo', f.get('name', ''), re.I)), None)
    in_kit = [f"{n_songs} {'song' if n_songs == 1 else 'songs'}{' with lyrics' if has_lyr else ''}"]
    if n_vids: in_kit.append(f"{n_vids} {'live video' if n_vids == 1 else 'live videos'}")
    if photos: in_kit.append(f"{len(photos)} {'photo' if len(photos) == 1 else 'photos'}")
    if sheet:
        in_kit.append('a\u00a0fact sheet')   # (plain words: the fact sheet has its own row in the open kit)
    if has_lyr:
        in_kit.append('a\u00a0lyrics sheet')   # (it has its own row beside the fact sheet)
    if facts.get('pitch'): in_kit.insert(0, 'a\u00a0bio')   # (the bio is in the open kit: owner, 2026-11-25)
    in_kit_html = (', '.join(in_kit[:-1]) + ' and ' + in_kit[-1]) if len(in_kit) > 1 else in_kit[0]
    facts_html = f'<p class="epk-summary">{in_kit_html[:1].upper() + in_kit_html[1:]}.</p>'
    # the card's heading, as an album card's: the update date in the gold line, the name as the title
    upd = f'<span class="rel-year"> <time datetime="{esc(kit["updated"])}">{full_date(kit["updated"])}</time></span>' if kit.get('updated') else ''
    info = ''   # (no "Updated" date: owner, 2026-11-25, "remove the date updated on the epk"; no "Ash Stu" title: owner, 2026-11-23)
    art = ''; kit_types = ''
    if lead and lead.get('thumb'):
        # (the kinds of thing in the kit, as tags on the photo - Songs, Videos, Photos, Text: owner's request)
        _icons = {'song': '<svg class="kit-type-ico" aria-hidden="true" focusable="false" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round"><path d="M9 18V5.5l11-2V16"/><circle cx="6.5" cy="18" r="2.5"/><circle cx="17.5" cy="16" r="2.5"/></svg>', 'video': '<svg class="kit-type-ico" aria-hidden="true" focusable="false" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round"><rect x="3" y="6" width="13" height="12" rx="2.5"/><path d="m16 10.5 5-3v9l-5-3"/></svg>', 'photo': '<svg class="kit-type-ico" aria-hidden="true" focusable="false" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round"><rect x="3" y="4.5" width="18" height="15" rx="2.5"/><circle cx="9" cy="10" r="1.8"/><path d="m21 16-5-5-8.5 8.5"/></svg>', 'text': '<svg class="kit-type-ico" aria-hidden="true" focusable="false" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round"><path d="M14 3H7a2 2 0 0 0-2 2v14a2 2 0 0 0 2 2h10a2 2 0 0 0 2-2V8z"/><path d="M14 3v5h5"/><path d="M9 13h6M9 17h6"/></svg>'}
        _names = {'song': 'Songs', 'video': 'Videos', 'photo': 'Photos', 'text': 'Documents'}   # (as the open kit's section is called: owner, 2026-11-25)
        _seen = [k for k in ['song', 'video', 'photo', 'text'] if any(('text' if f.get('type') == 'lyrics' else f.get('type')) == k for f in files)]
        kit_types = ('<p class="kit-types"><span class="sr-only">In the kit: </span>' + ''.join(f'<span class="kit-type kit-type--{k}">{_icons[k]}<span class="kit-type-word">{_names[k]}</span></span>' for k in _seen) + '</p>') if _seen else ''
        art = f'<div class="rel-art-wrap"><img src="{esc(urllib.parse.quote(lead["thumb"], safe="/:,"))}" alt="Ash Stu, lead press photo" class="rel-art" width="481" height="481" loading="lazy" decoding="async"/>{kit_types}</div>'
    btns = ('<div class="rel-btns"><button type="button" class="rel-btn rel-dl epk-show" aria-expanded="false" aria-label="Show the bio, music tracks, live videos, photos, fact sheet and lyrics sheet">'
            '<svg class="rel-dl-ico epk-show-chev" aria-hidden="true" width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.4" stroke-linecap="round" stroke-linejoin="round"><polyline points="6 9 12 15 18 9"/></svg><span class="btn-word" aria-hidden="true">Show</span></button>'
            '<a href="Images/press-kit/Ash%20Stu%20-%20Fact%20Sheet.txt" class="rel-btn rel-dl epk-zip" aria-label="Download the Press Kit" title="Download the Press Kit">'
            '<svg class="rel-dl-ico" aria-hidden="true" width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round"><path d="M12 4v11"/><path d="M7 11l5 5 5-5"/><path d="M5 20h14"/></svg><span class="btn-word" aria-hidden="true">Download</span></a>'
            '<p class="epk-progress" role="status" aria-live="polite"></p></div>')
    return ('<article class="rel-card epk-card kit-collapsed kit-shell" data-release="-1" aria-label="Ash Stu press kit">'
            + info +
            '<div class="rel-avail epk-about">' + f'<div class="epk-facts">{facts_html}</div></div>'
            + art + btns + '</article>')


def inject_featured(page, rel, rel_idx=0):
    if not rel:
        return page
    page = re.sub(
        r'(<img src=")[^"]*(" alt=")[^"]*("\s*class="featured-art featured-art-rounded")',
        # (a sharper copy for high-resolution screens, when the release has one: the same files the album cards use)
        lambda m: m.group(1) + esc(rel['art'])
        + (f'" srcset="{esc(rel["art"].replace(" ", "%20"))} 504w, {esc(rel["art2x"].replace(" ", "%20"))} 800w" sizes="(max-width: 767px) 50vw, 400px' if rel.get('art2x') else '')
        + m.group(2) + esc(rel['name']) + m.group(3),
        page, count=1,
    )
    page = re.sub(
        r'(id="featured-play"[^>]*aria-label=")[^"]*(")',
        lambda m: m.group(1) + 'Play ' + esc(rel['name']) + m.group(2),
        page, count=1,
    )
    page = re.sub(
        r'(id="featured-play"[^>]*title=")[^"]*(")',
        lambda m: m.group(1) + 'Play ' + esc(rel['name']) + m.group(2),
        page, count=1,
    )
    page = re.sub(
        r'(<span class="featured-kicker">)[^<]*(</span>)',
        lambda m: m.group(1) + esc(rel['type']) + m.group(2),
        page, count=1,
    )
    page = re.sub(
        r'(<p class="featured-title">)[^<]*(</p>)',
        lambda m: m.group(1) + esc(rel['name']) + m.group(2),
        page, count=1,
    )
    # Download under Play: the featured album's ZIP (as zipOK/zipName/albumHref in index-src.html)
    if rel.get('zip', {}).get('files') and rel.get('tracks'):
        n = len(rel['tracks'])
        dl_name = f"Download {rel['name']} as a ZIP file ({n} song{'' if n == 1 else 's'}, about {round(rel['zip']['bytes'] / 1048576)} MB)"
        slug = re.sub(r'^-|-$', '', re.sub(r'[^a-z0-9]+', '-', rel['name'].lower().replace('&', 'and')))
        page = re.sub(r'(<a href=")[^"]*(" class="rel-btn rel-dl f-dl" id="featured-dl" data-live-zip data-rel=")[^"]*(" aria-label=")[^"]*(" title=")[^"]*(")',
                      lambda m: m.group(1) + f'albums/{slug}/' + m.group(2) + str(rel_idx) + m.group(3) + esc(dl_name) + m.group(4) + esc(dl_name) + m.group(5),
                      page, count=1)
    else:
        page = page.replace('id="featured-dl" data-live-zip', 'id="featured-dl" hidden data-live-zip', 1)
    stores = [(k, n, w) for k, n, w in (('apple', 'Apple Music', 'Apple Music'), ('spotify', 'Spotify', 'Spotify'), ('ytmusic', 'YouTube Music', 'YouTube Music'),
                                       ('deezer', 'Deezer', 'Deezer')) if rel.get(k)]
    btns = ('<p class="f-listen-label" id="f-listen-label">Listen on</p><div class="f-stores" role="group" aria-labelledby="f-listen-label">' + ''.join(
        f'<a href="{esc(rel[k])}" target="_blank" rel="noopener noreferrer" class="f-store" aria-label="Listen on {n}: {esc(rel["name"])}">'
        f'<span class="pt pt--{k}" aria-hidden="true"></span><span class="f-store-word" aria-hidden="true">{w}</span></a>' for k, n, w in stores) + '</div>') if stores else ''
    page = re.sub(
        r'(<div class="featured-btns">).*?(</div>)',
        lambda m: m.group(1) + btns + m.group(2),
        page, count=1, flags=re.DOTALL,
    )
    # Badge doubles as the release-status tag: no streaming links yet
    # reads "Coming soon to streaming" instead of "Latest Release". The .soon
    # class flips it gold (see .featured-badge.soon in styles.css) - the
    # class is rewritten along with the text so the static snapshot always
    # matches what the JS render would produce.
    has_links = bool(rel.get('apple') or rel.get('spotify'))
    badge = ('<span aria-hidden="true">\u2605</span> Latest Release'
             if has_links else 'Coming soon to streaming')
    badge_cls = 'featured-badge' if has_links else 'featured-badge soon'
    page = re.sub(
        r'<span class="featured-badge[^"]*"([^>]*)>.*?(</span>\s*<div class="featured-art-wrap)',
        lambda m: f'<span class="{badge_cls}"' + m.group(1) + '>' + badge + m.group(2),
        page, count=1, flags=re.DOTALL,
    )
    return page


def main():
    with open('releases.json', encoding='utf-8') as f:
        releases = json.load(f)
    with open('videos.json', encoding='utf-8') as f:
        videos = json.load(f)
    with open('lyrics.json', encoding='utf-8') as f:
        LYRICS.update(json.load(f))

    # Cover art and video thumbnails stay ordinary image files (lazy-loaded,
    # cached, shared by the homepage and every song page). They used to be
    # baked in as base64, twice (cards + data-all): 620KB of an 800KB page,
    # and because the embedded copy then never matched the live .json files,
    # the script re-rendered everything and downloaded the images anyway.

    with open('index.html', encoding='utf-8') as f:
        page = f.read()

    RELEASES_FOR_VIDEOS[:] = releases
    releases_html = ''.join(render_release_card(r, i) for i, r in enumerate(releases))
    videos_html = ''.join(render_video_card(v, i) for i, v in enumerate(videos))

    page = inject_container(page, 'releases-grid', 'releases-grid', releases_html)
    page = inject_container(page, 'epk-card', 'epk-card-slot', render_kit_shell(page))   # (the press kit card from the first paint: see render_kit_shell)
    # Every song with lyrics as structured data (MusicComposition + lyrics text).
    comps, used_slugs = [], set()
    for rel in releases:
        for i, t in enumerate(rel['tracks']):
            entry = LYRICS.get(t['file'])
            if not entry or not entry.get('lines'):
                continue
            text = '\n\n'.join('\n'.join(v) for v in stanzas(entry, t['file']))
            # Each song's own lyrics page (same slugs as build_lyrics_pages.py);
            # structured data only - nothing on the homepage links to it.
            slug = slugify(t['title'])
            if slug in used_slugs:
                slug = f"{slug}-{slugify(rel['name'])}"
            used_slugs.add(slug)
            song_url = f'https://ashstu.art/lyrics/{slug}/'
            comps.append({'@type': 'MusicComposition', 'name': t['title'], 'inLanguage': 'en',
                          'url': song_url, 'mainEntityOfPage': song_url,
                          'composer': {'@id': 'https://ashstu.art/#artist'}, 'lyricist': {'@id': 'https://ashstu.art/#artist'},
                          'lyrics': {'@type': 'CreativeWork', 'inLanguage': 'en', 'text': text},
                          'recordedAs': {'@type': 'MusicRecording', 'name': t['title'], 'byArtist': {'@id': 'https://ashstu.art/#artist'},
                                         'inAlbum': {'@type': 'MusicAlbum', 'name': rel['name']}, 'position': t.get('num', i + 1)}})
    # unreleased songs with lyrics (traditional songs credited as such)
    for rel in releases:
        for u in rel.get('upcoming', []):
            entry = LYRICS.get(u.get('lyrics') or '')
            if not entry or not entry.get('lines'):
                continue
            slug = slugify(u['title'])
            if slug in used_slugs:
                slug = f"{slug}-{slugify(rel['name'])}"
            used_slugs.add(slug)
            song_url = f'https://ashstu.art/lyrics/{slug}/'
            text = '\n\n'.join('\n'.join(v) for v in stanzas(entry, None))
            who = {'@type': 'Person', 'name': 'Traditional'} if u.get('traditional') else {'@id': 'https://ashstu.art/#artist'}
            comps.append({'@type': 'MusicComposition', 'name': u['title'], 'inLanguage': 'en', 'url': song_url, 'mainEntityOfPage': song_url,
                          'composer': who, 'lyricist': who,
                          'lyrics': {'@type': 'CreativeWork', 'inLanguage': 'en', 'text': text}})
    if comps:
        ld = json.dumps({'@context': 'https://schema.org', '@graph': comps}, ensure_ascii=False).replace('</', '<\\/')
        # (at the end of the page, not in the head: 48KB there held back the stylesheet and the first paint)
        page = page.replace('</body>', f'<script type="application/ld+json" id="lyrics-ld">{ld}</script>\n</body>', 1)
    page = inject_container(page, 'video-grid', 'video-grid', videos_html)
    featured = next((r for r in releases if r.get('featured')), releases[0] if releases else None)
    page = inject_featured(page, featured, releases.index(featured) if featured else 0)

    # Embed the content JSON directly in the page so the runtime JS can
    # render instantly with zero fetches on first paint. The JS still
    # revalidates against the live .json files in the background (content
    # added purely via the GitHub web UI, with no local rebuild, would
    # otherwise go stale here).
    with open('lyrics.json', encoding='utf-8') as f:
        lyrics = json.load(f)
    combined = {
        'releases': releases, 'videos': videos,
        'lyrics': lyrics,
        'keys': song_words(releases, lyrics),
    }
    payload = json.dumps(combined, separators=(',', ':')).replace('</', '<\\/')
    blocks = f'<script type="application/json" id="data-all">{payload}</script>'
    # The data must sit BEFORE the script that reads it (readEmbedded('data-all') runs as that script executes).
    # It used to go before the last <script> on the page, which stopped being the main one once later scripts were
    # added: the page then never found its own data, always waited on the three .json requests, and lost its
    # releases if one of them failed.
    # (The main script is now its own deferred file, main.<hash>.js: the data goes just before its tag.)
    if "readEmbedded('data-all')" in page:
        idx = page.rindex('<script', 0, page.index("readEmbedded('data-all')"))
    else:
        # (the scripts are started by a small loader after the first paint: the data goes just before it)
        _ld = '<script>(function(s){var d=document,done=0'
        idx = page.index(_ld) if _ld in page else page.index('<script src="main.')
    page = page[:idx] + blocks + page[idx:]

    with open('index.html', 'w', encoding='utf-8') as f:
        f.write(page)
    print(f'Prerendered {len(releases)} release(s), {len(videos)} video(s) '
          f'into index.html')


if __name__ == '__main__':
    main()
    # Song pages are copies of this page (one per song, with that song
    # opened): rebuild them whenever index.html changes, so they never point
    # at bundles that no longer exist.
    import subprocess, sys
    subprocess.run([sys.executable, os.path.join('scripts', 'build_lyrics_pages.py')], check=True)
