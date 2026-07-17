# Adding & removing content

The site reads its Music, Videos, and Journal sections from `releases.json`,
`videos.json`, and `journal.json` at the repo root. Those files are
generated automatically by a GitHub Action (`.github/workflows/update-content.yml`)
whenever you add or remove files in the folders below — **you never need to
touch HTML or JS**. Just add/delete files (via git, or by uploading directly
in the GitHub web UI) and push to `main`. The live site updates within a
minute or two of the Action finishing.

To do it locally instead of waiting on GitHub, run:
```
python3 scripts/generate_content.py
```

---

## Music

Each release is a folder under `Audio/`:

```
Audio/My New Song/
  01. My New Song.mp3
  links.txt          (optional)
```

- **Track order & titles** come from the filenames. Keep the `01. `, `02. `
  numbering prefix — it's stripped for display, and only used for order.
  Whatever's left after that prefix (and the `.mp3`) is the track title
  exactly as typed, so type it exactly as you want it shown (including
  apostrophes, capitalization, etc).
- **Album / EP / Single** is decided automatically by track count:
  7+ tracks → Album, 4–6 → EP, 1–3 → Single.
- **Cover art** must be in `Images/Releases/`, named *exactly* like the
  folder (any of `.webp` / `.png` / `.jpg` / `.jpeg`):
  `Images/Releases/My New Song.webp`. No matching art file = the release
  is skipped with a warning (won't silently show a broken image).
- **`links.txt`** (optional) holds streaming links and, optionally, a
  release date used for sorting ("Latest Release" and grid order):
  ```
  apple: https://music.apple.com/...
  spotify: https://open.spotify.com/...
  date: 2026-03-01
  ```
  Any line can be left out. Without a `date:` line, releases sort by
  when their files were first committed to git — set the date explicitly
  if you care about exact ordering (e.g. backdating an older release).
- **To hide a release** (keep the files but drop it from the site) without
  deleting anything, add an empty file named `.hidden` inside its folder.
- **A release with no streaming links yet** (no `apple:`/`spotify:` lines,
  or no `links.txt` at all) shows a "Distributing Soon" tag in place of the
  platform buttons — add the links later and the buttons appear.
- **To remove a release**, delete its whole folder under `Audio/` (and its
  art file under `Images/Releases/`, if you don't want it lingering).

## Videos

Each video is just two files directly in `Videos/`:

```
Videos/My New Video.mp4
Videos/My New Video.txt              (optional - YouTube link)
Videos/Thumbnails/My New Video.webp  (optional - custom thumbnail)
```

- **Title** is the filename, minus the extension, exactly as typed.
- **YouTube link** (optional) goes in a `.txt` file with the *same name* as
  the video, containing just the URL on one line. No `.txt` file = no
  YouTube button on that video.
- **Thumbnail** (optional) goes in `Videos/Thumbnails/`, named *exactly*
  like the video (any of `.webp` / `.png` / `.jpg` / `.jpeg`). No thumbnail
  file = the player automatically grabs a frame from the video itself, so
  this is only needed if you want a specific, chosen image instead.
- **To remove a video**, delete its `.mp4` (and matching `.txt`/thumbnail).

## Journal

Essays, journal entries, and lyrics each live in their own subfolder:

```
Journal/Essays/
Journal/Entries/
Journal/Lyrics/
```

**Essays and Entries** use the same plain-text format:

```
substack link: https://...          (optional)

"Entry Title"
"Optional subtitle"                 (optional second line)
- March 1, 2026

First paragraph of the entry...

Second paragraph...

"A quoted line someone actually said" — Whoever Said It, Some Source

Another paragraph...
```

- The title line(s) and the `- Date` line are required; everything else
  (the substack link, the subtitle) is optional.
- Any line that's a quotation ending in an em dash (—) + attribution gets
  pulled out and styled as a pull-quote automatically — no markup needed,
  just write it as its own line/paragraph.
- Curly-quoted phrases inside regular paragraphs (`"like this"`) render
  bold, since that's almost always someone being quoted directly. Scare
  quotes and titles-in-quotes will also come out bold with no way to tell
  the two apart automatically — if that matters for a specific entry, say
  so and it can be special-cased.

**Lyrics** are simpler — just the song title as the filename, and the raw
lyrics as the file content (blank line between verses/sections):

```
Journal/Lyrics/My New Song.txt
```
```
First verse line one
First verse line two

Chorus line one
Chorus line two
```

- **To remove any journal item**, delete its `.txt` file.

**Audio essays** (optional, Essays and Entries only) - a spoken-word
recording of a piece, named exactly like its `.txt` file:

```
Journal/Audio/An Occurrence at Cottonwood-Creek Bridge.mp3
```

A "Listen" button appears under that entry's title automatically once
the file is there - no file yet, no button. Playing one uses the same
mini-player as the music tracks, except it never shows an album cover
and can't be expanded to the fullscreen player (there's no release or
playlist behind it, so neither makes sense here). To remove one,
delete the mp3 - the button disappears with it.

---

## Things that still need a real edit (not covered by this system)

- **Site design/layout/styling** (colors, fonts, page sections themselves)
  still goes through `index-src.html` + `styles.css` + `build-fast.py`,
  same as before.
- The **structured data** (`<script type="application/ld+json">` in
  `index-src.html`, used for search engine rich results) isn't
  auto-regenerated from these folders — it'll gradually go stale as
  releases are added/removed. Low priority to fix unless SEO for new
  releases specifically matters.
- **index.html ships with the current releases/videos/journal baked
  directly into the HTML** (not just the empty containers JS fills in),
  so a crawler or AI/LLM scraper that doesn't execute JavaScript still
  sees real content instead of blank `<div>`s. That snapshot is written
  by `scripts/prerender.py`, which must run locally, right after
  `build-fast.py`, whenever `index-src.html` changes:
  ```
  python3 build-fast.py && python3 scripts/prerender.py
  ```
  It reads the same `releases.json`/`videos.json`/`journal.json` the
  GitHub Action already keeps current, so as long as it's re-run before
  each push it can't drift out of sync. It is **not** wired into the
  GitHub Action itself (`build-fast.py` has a hardcoded local path and
  extra Python dependencies not currently in CI) — so a release added
  purely by uploading files through GitHub's web UI, with no local
  rebuild afterward, will show up correctly for real visitors (JS still
  fetches the JSON live) but won't be in the raw HTML until the next
  local rebuild+push.
