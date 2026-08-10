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

from buildutil import img_b64

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
os.chdir(ROOT)


def esc(s):
    if s is None:
        return ''
    return (str(s).replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;')
            .replace('"', '&quot;').replace("'", '&#39;'))


def enc_path(p):
    return p.replace('"', '%22')


def render_release_card(rel, r_idx):
    kind_word = ('Single artwork for ' if rel['type'] == 'Single'
                 else 'EP artwork for ' if rel['type'] == 'EP'
                 else 'Album cover for ')
    btns = ''
    if rel.get('apple'):
        btns += (f'<a href="{esc(rel["apple"])}" target="_blank" rel="noopener noreferrer" class="rel-btn" '
                  f'aria-label="Listen to {esc(rel["name"])} on Apple Music" itemprop="url">'
                   f'<span class="pt pt--apple" aria-hidden="true"></span> Apple Music</a>')
    if rel.get('spotify'):
        btns += (f'<a href="{esc(rel["spotify"])}" target="_blank" rel="noopener noreferrer" class="rel-btn" '
                  f'aria-label="Listen to {esc(rel["name"])} on Spotify">'
                   f'<span class="pt pt--spotify" aria-hidden="true"></span> Spotify</a>')
    if not btns:
        btns = '<span class="rel-btn rel-btn--label">Distributing Soon</span>'
    tracklist = ''
    if len(rel['tracks']) > 1:
        items = ''.join(f'<li>{esc(t["title"])}</li>' for t in rel['tracks'])
        tracklist = (f'<div class="rel-tracklist" id="tracklist-{r_idx}">'
                     f'<ol aria-label="Tracklist for {esc(rel["name"])}">{items}</ol></div>')
    return (f'<article class="rel-card" aria-label="{esc(rel["name"])} - {esc(rel["type"])} by Ash Stu" '
            f'itemscope itemtype="https://schema.org/MusicAlbum">'
            f'<div class="rel-art-wrap">'
            f'<img src="{esc(rel["art"])}" alt="Album artwork: {esc(kind_word + rel["name"] + " by Ash Stu")}" '
            f'class="rel-art" width="560" height="560" itemprop="image"/>'
            f'<div class="rel-overlay"><div class="rel-overlay-inner">'
            f'<p class="rel-cat">{esc(rel["type"])}</p>'
            f'<h3 class="rel-name" itemprop="name">{esc(rel["name"])}</h3>'
            f'</div></div></div>'
            f'<div class="rel-btns">{btns}</div>'
            f'{tracklist}</article>')


def render_video_card(v, v_idx):
    yt_btn = ''
    if v.get('youtube'):
        yt_btn = (f'<a class="vid-yt" href="{esc(v["youtube"])}" target="_blank" rel="noopener noreferrer" '
                   f'aria-label="Watch &quot;{esc(v["title"])}&quot; on YouTube">'
                   f'<span class="pt pt--youtube" aria-hidden="true"></span>YouTube</a>')
    if v.get('thumb'):
        thumb_el = f'<img src="{esc(v["thumb"])}" alt="Music video: {esc(v["title"])} by Ash Stu" width="640" height="360"/>'
    else:
        thumb_el = f'<video src="{enc_path(v["file"])}" preload="metadata" muted playsinline aria-label="Video thumbnail" alt="Video thumbnail"></video>'
    return (f'<div class="vid-card-wrap">'
            f'<div class="vid-card" tabindex="0" role="button" '
            f'aria-label="Play &quot;{esc(v["title"])}&quot;" data-video-index="{v_idx}">'
            f'<div class="vid-thumb">{thumb_el}'
            f'<div class="vid-play-overlay"><div class="vid-play-circle">'
            f'<svg width="16" height="16" viewBox="0 0 24 24" fill="currentColor" aria-hidden="true">'
            f'<polygon points="5,3 19,12 5,21"/></svg></div></div></div>'
            f'</div>'
            f'<div class="vid-info"><h3 class="vid-title">{esc(v["title"])}</h3>{yt_btn}</div>'
            f'</div>')


JOURNAL_CHEVRON_SVG = ('<svg class="journal-chevron" width="10" height="10" viewBox="0 0 24 24" fill="none" '
                        'stroke="currentColor" stroke-width="3" stroke-linecap="round" stroke-linejoin="round" '
                        'aria-hidden="true"><polyline points="6 9 12 15 18 9"/></svg>')
JOURNAL_LISTEN_SVG = ('<svg width="12" height="12" viewBox="0 0 24 24" fill="currentColor" aria-hidden="true">'
                       '<polygon points="5,3 19,12 5,21"/></svg>')


def render_journal_entry(entry, idx):
    dek_html = f'<p class="journal-dek">{esc(entry["dek"])}</p>' if entry.get('dek') else ''
    meta_parts = ['By Ash Stu']
    if entry.get('date'):
        meta_parts.append(esc(entry['date']))
    if entry.get('readMin'):
        meta_parts.append(f'{entry["readMin"]} min read')
    byline = ''.join(p if i == 0 else f'<span class="journal-dot">&middot;</span>{p}'
                      for i, p in enumerate(meta_parts))
    kicker = {'essay': 'Essay', 'entry': 'Entry'}.get(entry['category'], 'Lyrics')
    source_html = ''
    if entry.get('substack'):
        source_html = (f'<p class="journal-source"><a href="{esc(entry["substack"])}" target="_blank" '
f'rel="noopener noreferrer" class="vid-yt" aria-label="Read on Substack"><span class="pt pt--substack" aria-hidden="true"></span>Substack</a></p>')
    listen_btn = ''
    if entry.get('audio'):
        listen_btn = (f'<button type="button" class="journal-listen-btn vid-yt" data-journal-idx="{idx}" '
                       f'aria-label="Listen to audio version of {esc(entry["headline"])}">'
                       f'{JOURNAL_LISTEN_SVG}<span>Listen</span></button>')
    return (f'<article class="journal-entry">'
            f'<div class="journal-entry-head" role="button" tabindex="0" aria-expanded="false" '
            f'aria-controls="journal-body-{idx}" id="journal-toggle-{idx}" '
            f'aria-label="Toggle {esc(entry["headline"])}">'
            f'<span class="journal-kicker">{kicker}</span>'
            f'<h3 class="journal-title">{esc(entry["headline"])}</h3>{dek_html}'
            f'<div class="journal-byline">{byline}</div>'
            f'<span class="journal-readmore"><span class="journal-readmore-label">Read</span>'
            f'{JOURNAL_CHEVRON_SVG}</span></div>{listen_btn}'
            f'<div class="journal-body" id="journal-body-{idx}" role="region" '
            f'aria-labelledby="journal-toggle-{idx}">'
            f'<div class="journal-body-inner">{entry["bodyHtml"]}{source_html}</div></div></article>')


def inject_container(page, container_id, cls_attr, inner_html):
    pattern = re.compile(
        r'(<div [^>]*id="' + re.escape(container_id) + r'"[^>]*>)\s*(</div>)'
    )
    new_page, n = pattern.subn(lambda m: m.group(1) + inner_html + m.group(2), page, count=1)
    if n != 1:
        print(f'  WARNING: could not find empty #{container_id} container to inject into', file=sys.stderr)
    return new_page


def inject_featured(page, rel):
    if not rel:
        return page
    page = re.sub(
        r'(<img src=")[^"]*(" alt=")[^"]*("\s*class="featured-art featured-art-rounded")',
        lambda m: m.group(1) + esc(rel['art']) + m.group(2) + esc(rel['name']) + m.group(3),
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
    btns = ''
    if rel.get('apple'):
        btns += (f'<a href="{esc(rel["apple"])}" target="_blank" rel="noopener noreferrer" class="f-btn" '
                   f'aria-label="Apple Music"><span class="pt pt--apple" aria-hidden="true"></span> Apple Music</a>')
    if rel.get('spotify'):
        btns += (f'<a href="{esc(rel["spotify"])}" target="_blank" rel="noopener noreferrer" class="f-btn" '
                   f'aria-label="Spotify"><span class="pt pt--spotify" aria-hidden="true"></span> Spotify</a>')
    page = re.sub(
        r'(<div class="featured-btns">).*?(</div>)',
        lambda m: m.group(1) + btns + m.group(2),
        page, count=1, flags=re.DOTALL,
    )
    # Badge doubles as the release-status tag: no streaming links yet
    # reads "Distributing Soon" instead of "Latest Release". The .soon
    # class flips it gold (see .featured-badge.soon in styles.css) - the
    # class is rewritten along with the text so the static snapshot always
    # matches what the JS render would produce.
    has_links = bool(rel.get('apple') or rel.get('spotify'))
    badge = ('<span aria-hidden="true">\u2605</span> Latest Release'
             if has_links else 'Distributing Soon')
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
    with open('journal.json', encoding='utf-8') as f:
        journal = json.load(f)

    # Single-file build: bake raster art/thumb paths as 90%-scale base64
    # WebP data URIs so the prerendered cards AND the embedded data-all JSON
    # make zero image requests. (Audio/video file paths stay external - they
    # are user-triggered media, not initial-render assets.)
    for r in releases:
        if r.get('art'):
            r['art'] = img_b64(r['art'])
    for v in videos:
        if v.get('thumb'):
            v['thumb'] = img_b64(v['thumb'])

    with open('index.html', encoding='utf-8') as f:
        page = f.read()

    releases_html = ''.join(render_release_card(r, i) for i, r in enumerate(releases))
    videos_html = ''.join(render_video_card(v, i) for i, v in enumerate(videos))
    journal_html = ''.join(render_journal_entry(e, i) for i, e in enumerate(journal))

    page = inject_container(page, 'releases-grid', 'releases-grid', releases_html)
    page = inject_container(page, 'video-grid', 'video-grid', videos_html)
    page = inject_container(page, 'journal-list', 'journal-list', journal_html)
    page = inject_featured(page, releases[0] if releases else None)

    # Embed the content JSON directly in the page so the runtime JS can
    # render instantly with zero fetches on first paint. The JS still
    # revalidates against the live .json files in the background (content
    # added purely via the GitHub web UI, with no local rebuild, would
    # otherwise go stale here).
    with open('lyrics.json', encoding='utf-8') as f:
        lyrics = json.load(f)
    combined = {
        'releases': releases, 'videos': videos,
        'journal': journal, 'lyrics': lyrics,
    }
    payload = json.dumps(combined, separators=(',', ':')).replace('</', '<\\/')
    blocks = f'<script type="application/json" id="data-all">{payload}</script>'
    idx = page.rindex('<script')
    page = page[:idx] + blocks + page[idx:]

    with open('index.html', 'w', encoding='utf-8') as f:
        f.write(page)
    print(f'Prerendered {len(releases)} release(s), {len(videos)} video(s), '
          f'{len(journal)} journal entr(y/ies) into index.html')


if __name__ == '__main__':
    main()
