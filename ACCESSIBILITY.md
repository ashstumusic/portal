# Accessibility patterns for ashstu.art

How each interactive part of the site is meant to work for keyboard, screen-reader, low-vision and motion-sensitive
visitors. Read this before adding or changing a component, and add to it when you do. The log of fixes that led to
these rules is in `a11y-audit.log`.

Automated scanning (axe) is run on the home page, both players, the menu and a lyric page at desktop and phone
sizes and must stay at zero issues. It only catches about half of real problems: the checks listed under
"Check by hand" at the end are part of every change.

## Ground rules

- Fix problems in the source. No third-party accessibility overlays or widgets.
- Every control is a real `<button>` or `<a>` with a name that says what it does.
- A control does from the keyboard exactly what its icon shows.
- State is never shown by colour alone: use text ("On"/"Off"), an outline, or an ARIA state as well.
- Nothing essential depends on motion, hover or a pointer.

## Components

### Skip link
- First thing in the page. "Skip to content" on the home page; "Skip to the song" on lyric pages.
- It must move keyboard focus to its target, not only scroll. Lyric pages have `<base href="/">`, so in-page links
  are handled by a small script that scrolls **and** focuses the target (`scripts/build_lyrics_pages.py`).
- While focused it is fixed to the screen (not the page top), so focusing it never scrolls the page.

### Toolbar
- A `<nav aria-label="Main navigation">`. The current section's link has `aria-current`; it is also outlined, not
  just recoloured.
- Streaming links open a new tab and say so (see "Links that open a new tab").

### Menu and settings (dialog)
- A native `<dialog>` opened with `showModal()`: the page behind is inert and Tab stays inside.
- Focus starts on the first section button (phones) or the first setting (wide screens). Never on a link that
  leaves the site.
- Escape or Close shuts it; focus returns to the button that opened it.
- On phones "Settings" is a fold: `<button aria-expanded aria-controls>`. The folded group uses the `hidden`
  attribute so it is out of the tab order.

### Settings switches
- `<button role="switch" aria-checked>`.
- Name = the setting's label (`aria-labelledby`); description = the line under it (`aria-describedby`).
  Announced as "Effects, switch, on. Haze, stars, tag flare, confetti and fireworks."
- Enter or Space flips it; focus stays on the row. The visible "On"/"Off" is `aria-hidden` (the state comes from
  `aria-checked`).

### Search
- A combobox (`role="combobox"`, `aria-expanded`, `aria-controls`, `aria-activedescendant`) with a listbox of
  options. Arrow keys move, Enter opens, Escape clears then closes.
- The number of suggestions is announced politely after typing pauses ("3 suggestions", "0 suggestions").
- Choosing a song or a lyric from the toolbar field starts it in the mini player and moves focus to its Play/Pause
  button (focus is never left on nothing).

### Album cards
- Cover button: named "Play <album>" / "Pause <album>" and plays or pauses with Enter or Space. With a mouse or
  finger the disc plays and the rest of the cover opens the tracklist.
- Tracklist button: visible text "10 tracks", spoken name "10 tracks on <album>", with `aria-expanded`.
- Each track: "Play <title>, track N"; its lyrics button "Show lyrics for <title>" with `aria-expanded`.
- The song in the player has `aria-current` on its row.

### Mini player
- A region labelled "Now playing".
- Main button: "Open full-screen player. Playing: <song>, from <album>" (updated with every song). Its cover image
  is decorative (`alt=""`) because the button already has a name.
- Seek bar: `role="slider"` with `aria-valuetext` such as "1:00 of 2:57". Arrows move 5 s, Page Up/Down 30 s,
  Home/End jump. The value is refreshed on load, play, pause, jump and every 15 s, but not while the bar has
  focus (a changing value there would be read over the music).
- While the bar is showing, the page keeps the strip under it clear when scrolling a focused control into view
  (`scroll-padding-bottom`), so focus is never hidden behind it.
- Closed from the keyboard, focus goes to the song that was playing (if its row is showing) or to that album's
  cover button, never to nothing. A mouse or touch close does not move focus or scroll.
- The toolbar's strip at the top is kept clear the same way (`scroll-padding-top` on the page), for tabbing back
  up. Section links take their offset from that too: do not add `scroll-margin-top` to sections as well.

### Full-screen player (dialog)
- `role="dialog" aria-modal="true"`, labelled "Now playing". Focus moves to "Close player" on opening and back
  to the opener on closing. Escape closes.
- The page behind is made inert once the player has finished opening.
- Cover image: `alt="Album cover: <album>"`.
- Lyrics: a list of buttons, one tab stop with arrow keys between lines (roving tabindex); the current line has
  `aria-current`. Lines are not announced as they change.

### Video viewer (dialog)
- `role="dialog" aria-modal="true"`; focus is kept inside; Escape closes and returns focus to the video's button.
- Left and Right arrows change video, except while the video itself has focus: there they belong to its own
  controls (skip back and forward).

### Loading and failure
- Song still arriving: the play buttons show a turning ring (still, with reduced motion) and carry `aria-busy`.
- Song failed: the message is shown in the bar and spoken; pressing Play tries again.
- Video failed: a message replaces the picture, is spoken, and offers a "Try again" button.

### Short and sideways screens
- Every dialog and the first screen must fit a phone held sideways (844 x 390, 667 x 375, 568 x 320) with nothing
  overlapping and every control reachable. Check these sizes when changing the players, the video viewer or the hero.

### Spoken messages (live regions)
- `#sr-status` (polite): which song has started. Must not interrupt.
- `#sr-announce` (assertive): errors only ("Couldn't load this song. Check your connection and try again.").
- The visible song title is **not** a live region (it used to double every announcement).

### Links that open a new tab
- Every `target="_blank"` link gets "(opens in a new tab)" added to its spoken name by `shared/kinetic.js`,
  including links drawn later by script.
- Two links with different destinations never share a name (the first-screen buttons add the release name).
- A control's spoken name contains its visible words, so voice-control users can say what they see (the email link
  is "Email Ash Stu: " followed by the address shown).

### Downloads
- Say the file type and size: "Download Press Kit (ZIP file, 33 MB)" (size measured at build time).

### Lyric pages
- The song's words are in the page's own HTML under its `<h1>`. While the interactive copy is open they are hidden
  from sight only (`.sr-only`), never from assistive technology.
- Printed, a lyric page is the song alone: title, credit, words, short address.

## System preferences

- **Reduced motion / Effects off:** all looping animation stops, including when the setting changes mid-visit.
  New animations need a rule under `prefers-reduced-motion: reduce` and under `.psy-calm`, strong enough to win.
  Animations driven from script (`shared/kinetic.js`, "stepped") are cancelled there when the styles drop them.
- **Forced colours (Windows Contrast Themes):** icons take the system text colour (`forced-color-adjust: auto` on
  `svg`); icons drawn as filled shapes or masks need `forced-color-adjust: none` with `ButtonText`; sliders get an
  outline and a `Highlight` fill; anything marked by colour gets an outline.
- **Reduced transparency:** glass panels fall back to a solid colour.
- **Zoom and text spacing:** no sideways scrolling or clipped labels at 200% and 400% zoom, or with the WCAG text
  spacing settings applied.

## Sizes and contrast

- Touch targets are 44px on touch screens (sliders are the exception: 24px minimum, because a taller hit strip
  would overlap the buttons beside them).
- Text contrast is at least 4.5:1, measured on the real background. For glass panels, measure against a white
  page behind them (the worst case).
- Focus is always visible: gold fill with a white ring, or a 3px white outline.

## Check by hand (every change)

1. Tab through the whole page, forwards and back. Is focus always visible and in a sensible order?
2. Open and close each dialog with the keyboard. Does focus go in, stay in, and come back?
3. Read the control's name aloud. Does it make sense with no surrounding context?
4. Turn on reduced motion, forced colours, and 200% zoom. Does it still work and show?
5. Listen with a real screen reader (VoiceOver, NVDA). This has **not** been done yet for this site and is the
   most valuable check still outstanding, along with testing by disabled users.
