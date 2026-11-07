# Accessibility pattern library: ashstu.art redesign

Target: **WCAG 2.2 level AA**. This file documents how every component on the
redesign stays usable by keyboard, screen reader, low-vision, and
motion-sensitive visitors, and how to check it.

**Rule for new work:** when you add or change a component, add or update its
entry here *in the same change*, and run the checklist at the bottom before
pushing. No third-party "accessibility overlay" widgets, ever: fixes go in the
code.

Last full audit: 2026-11-06 (automated + scripted manual checks, see the end of this file).

---

## Foundations

### Color and contrast

Every pair below was measured (WCAG relative luminance). Text needs 4.5:1;
focus rings and control boundaries need 3:1.

| Use | Light | Dark |
|---|---|---|
| Body text (ink on paper) | 15.3:1 | 15.6:1 |
| Secondary text (ink-2 on paper) | 6.6:1 | 8.5:1 |
| Secondary text on cards | 5.9:1 | 7.6:1 |
| Links and clay labels | 5.9:1 | 6.4:1 |
| Links on cards | 5.3:1 | 5.8:1 |
| Primary button text | 5.9:1 | 6.4:1 |
| "Copied" status (stem green) | 5.0:1 | 8.1:1 |
| Player title / secondary text | 14.6:1 / 7.9:1 | 12.8:1 / 6.9:1 |
| Badge text on daffodil ("Now playing", "Play") | 9.5:1 | 9.5:1 |
| Focus ring on page / on cards / in player | 5.9 / 5.3 / 9.5:1 | 10.1 / 9.0 / 8.3:1 |
| Motion and Copy button borders | 6.6:1 | 8.5:1 |
| Seek bar: unplayed track / thumb / played fill | 4.0 / 14.6 / 9.5:1 | 3.8 / 12.8 / 8.3:1 |

Rules:
- **Daffodil yellow is never text on paper.** It's only a fill behind dark ink.
- **Never color alone.** The current nav section has a dashed underline (shape);
  the playing song is bold, highlighted, *and* labelled "Now playing" in text;
  links in prose are underlined.
- Change a color token → re-measure every row that uses it.

### Type and zoom
- All sizes are `rem`/`clamp()`, so browser zoom and OS text size scale everything.
- Verified with Chrome's real text-size setting at 200% (desktop and a 390px
  phone), plus 280px folding-phone screens: no sideways scroll, nothing clipped.
- Verified: 200% zoom (no sideways scroll), 400% zoom / 320px (no sideways scroll;
  masthead wraps; masthead stops being sticky on viewports under 30rem tall so
  it can't hide content), increased text spacing (WCAG 1.4.12; nothing clips).
- System fonts only, so nothing swaps or reflows after load.

### Focus
- `:focus-visible` ring: 3px solid, 3px offset, clay (light) / daffodil (dark and
  inside the player and video viewer).
- Never `outline: none` on a control. Only `main:focus` hides its ring (it's a
  skip-link target, not a control).
- Paint containment (`contain: paint`) clips focus rings, so it is **not** used on
  `.record` or `.video` (their links touch the box edge). Check this before adding
  `contain: paint` anywhere.

### Motion
- Default: effects **off** when the OS asks for reduced motion; on otherwise.
- The **Motion button** (masthead, sparkle icon, `aria-pressed`) turns all effects
  on/off for anyone; the choice is remembered.
- With reduced motion, CSS also removes smooth scrolling, transitions, the player
  slide-in, and the tilted photos.
- Effects never carry information: everything they show also exists as static text.

### Targets
- Controls are at least 44×44px; inline text links get vertical padding so their
  hit area is at least 24px tall (WCAG 2.5.8).
- `touch-action: manipulation` removes the double-tap delay on phones.

---

## Components

### Skip links
- **What:** "Skip to main content" (always first Tab stop); "Skip to music
  player" (appears only while the player is open).
- **Keyboard:** hidden until focused, then shown top-left above the masthead.
  "Skip to music player" moves focus straight to the play/pause button.
- **Why:** the player sits at the end of the tab order (33 Tab presses from a
  mid-page song without this link).

### Masthead navigation
- `<header>` → banner landmark; `<nav aria-label="Page sections">`.
- Four always-visible links; no hamburger menu (nothing hidden behind a gesture).
- The current section gets `aria-current="true"` plus a dashed underline.

### Motion toggle
- `<button aria-label="Motion effects" aria-pressed="true|false">` with a
  decorative SVG (`aria-hidden`).
- Rendered in the static HTML and shown only when JavaScript runs (`.js` class set
  before first paint), so it never appears late or shifts the nav.

### Particle headline (effect 3)
- The real `<h1>Ash Stu</h1>` text stays in the DOM (selectable, read by screen
  readers and crawlers); it's painted transparent while a canvas draws it.
- The canvas is `aria-hidden="true"` and ignores pointer events.

### Kinetic headings (effects 2 and 5)
- Headings are split into letter `<span>`s for the animation. To keep screen
  readers from spelling them out, each heading becomes:
  `<span class="sr-only">Full text</span><span aria-hidden="true">l-e-t-t-e-r-s</span>`.
- Verified: the accessibility tree reads each heading once, as whole words.
- Animation is transform-only (no layout change), so text never reflows under
  the reader's eyes.

### Liquid images (effects 1 and 2)
- One WebGL canvas, `aria-hidden`, `pointer-events: none`, drawn over the hovered
  image. Clicks reach the real link underneath.
- The image's own `alt` text is unchanged.

### 3D flythrough (effect 4)
- Whole scene is `aria-hidden="true"`: it repeats the Listen section, so screen
  readers skip it.
- Contains no focusable elements, so keyboard users pass straight through.
- A visible "Skip the 3D tour of the records" link precedes it.
- Its space is reserved in CSS before first paint (no layout shift).

### Discography records
- Each release is an `<article>` in an `<ol aria-label="Releases, newest first">`.
- Facts are a `<dl>` (Release type, Release date, Number of songs, Total length).
  Dates use `<time datetime>`.
- Tracklist is a real `<table>` with a (visually hidden) `<caption>`,
  `<th scope="col">` headers, and the song title as `<th scope="row">`.
  Lengths are labelled "(minutes:seconds)".
- Every song title is a link to its MP3: works with JavaScript off. With JS, it
  plays in the docked player; pressing Enter on the playing song pauses it.

### Docked music player
- `<section aria-label="Music player">`, hidden until the first play.
- Starting a song does **not** move focus (the visitor stays in the tracklist).
- Song title has `aria-live="polite"`: the new title is announced once.
- Buttons have text names ("Previous song", "Pause"/"Play", "Next song",
  "Stop music and close player"); labels update with state.
- Seek is a native `<input type="range">` (arrow keys work) with
  `aria-valuetext="1:23 of 3:40"`.
- Closing the player returns focus to whatever started the music.
- Lock-screen and headphone controls via the Media Session API.

### Video viewer
- Native `<dialog>` opened with `showModal()`: focus is trapped inside, Esc
  closes, the page behind is inert, and focus returns to the video link.
  (Verified: 6 Tabs stayed inside; Esc closed; focus returned.)
- Each video link's name says what happens and how long:
  "Play the music video for VCR (5 minutes 16 seconds)".
- Music pauses when a video opens (never two soundtracks).
- If the video file fails, the player is replaced by a `role="alert"` message
  ("This video could not be loaded") with a link to the YouTube copy.

### Contact form (only with the Node back-end)
- Hidden unless the page was served by `server.js` (it adds
  `<meta name="contact-api">`), so it never appears where it can't work.
- Every field has a visible `<label>`; `autocomplete` and `inputmode` set so
  phones offer the right keyboard and autofill.
- Validation runs on submit (not while typing). Each error is text with a ⚠
  icon and a thicker border (never color alone), linked to its field with
  `aria-describedby`, and the field gets `aria-invalid="true"`. Focus moves to
  the first invalid field. Errors clear as soon as the field is fixed.
- One `role="status"` message reports Sending / Sent / failure in plain
  language, always with the email address as a fallback.
- Double-clicks and repeated Enter are ignored while sending
  (`aria-busy`/`aria-disabled`); requests time out after 10 seconds.
- Spam trap field is off-screen, `aria-hidden`, and `tabindex="-1"`, so
  keyboard and screen-reader users never meet it.

### Copy email button
- Shown only when JavaScript runs; removed if the browser lacks the Clipboard API.
- Result is announced through a `role="status"` region ("Copied … to the
  clipboard." / a fallback instruction).
- The address is also plain, selectable text and a `mailto:` link.

### Images and alt text
- Every content image has factual alt text describing what's visible
  (`redesign/facts.json` → `"alt"`). The build refuses to run if one is missing.
- Decorative duplicates use `alt=""` (the masthead logo inside a labelled link;
  the player's cover art until a song loads).
- Writing guide: say what a sighted visitor actually learns from the picture
  (who, doing what, where). Don't start with "Image of". Don't repeat an adjacent
  heading word-for-word unless the picture adds nothing else.

---

### Shared interaction layer (shared/kinetic.js + kinetic.css, on every page)
- **Theme toggle** (`.k-theme-btn`): its label always names the action
  ("Switch to dark theme"). The theme is set before first paint from the
  saved choice or the OS setting, so there's no flash. The change is
  announced ("Dark theme on"). The circular View Transitions reveal is
  skipped with reduced motion. Both palettes were checked with axe on all
  three pages.
- **Command palette** (⌘K / Ctrl+K, `/`, or the search button): a native
  modal `<dialog>`. The input is `role="combobox"` with `aria-controls`,
  `aria-autocomplete="list"` and `aria-activedescendant`; results are a
  `role="listbox"` of `role="option"` rows. Arrow keys, Home/End, Enter and Esc
  all work, and focus returns to where it was. Result counts are announced
  politely. Section jumps move focus to the section heading.
- **Single-key shortcuts** (`g` then a section letter, `/`): ignored while
  typing or inside dialogs, and switchable off in the palette ("Turn off
  single-key shortcuts", remembered), as WCAG 2.1.4 requires. The palette shows
  each section's keys as `<kbd>` badges.
- **Header that recedes on scroll-down**: it always returns on any upward
  scroll, near the top, when focus moves into it, and while the palette, the
  mobile menu or the full-screen player is open.
- **Decoration** (magnetic buttons, cursor lens, card spotlight, grain,
  parallax): pointer-only and `aria-hidden`. It never carries information and
  is off under reduced motion.
  The native cursor is never hidden.
- **Haptics and sounds**: 6 ms vibration on touch presses (where supported).
  Interface sounds are **off** by default and can be turned on in the palette.
- **Optimistic copy**: the Copy button flips to "Copied!" immediately without
  changing width, rolls back if the clipboard refuses, and the result is
  always announced in its `role="status"` line.
- **Forms**: floating labels keep the real `<label>` (only its position
  animates); invalid fields shake once (not with reduced motion), plus
  the text error and icon described above; the custom checkbox is still a
  native `<input type="checkbox">`.
- **Homepage tracklist**: the per-song lyrics button is a sibling of the
  `role="button"` row, not inside it (no nested interactive controls), with
  `aria-expanded` and a song-specific name.

### Homepage fixes (2026-11-06 compliance sweep)
- **Focus rings everywhere**: the global `:focus { outline: none }` became
  `:focus:not(:focus-visible)`, so keyboard focus always shows a ring (all
  58 Tab stops verified). Cover buttons draw their ring *inside* the image
  (gold over a teal band) because the card's rounded corners clip anything
  outside.
- **Full-screen player is keyboard-operable**: the bar's art/title area is
  a real button ("Open full-screen player", Enter/Space). Opening moves
  focus inside; the rest of the page becomes `inert` (true modal: Tab
  can't reach content behind it, screen readers don't read it); Esc
  closes and focus returns to the bar.
- **Album name in the full-screen player**: contrast raised from 2.8:1 to
  4.97:1.
- **Video titles wrap** instead of truncating, so nothing is lost with
  increased text spacing (WCAG 1.4.12).
- **"Home" text links removed**: the logo link is the single home control,
  labelled "Ash Stu · home".

## Testing checklist (run before every push)

Automated (catches roughly half of issues):
1. `python3 scripts/build_redesign.py` (fails on missing alt text).
2. axe-core (WCAG 2.2 AA + best practices) in six states: effects on, effects
   off, dark mode, player open, video viewer open, 390px phone.

Manual, with a keyboard only (no mouse):
3. Tab from the top to the footer: every stop has a visible ring and isn't
   hidden behind the header or player.
4. Play a song with Enter; press Enter again to pause; use "Skip to music player".
5. Open a video with Enter; Tab stays inside; Esc closes; focus returns.
6. Toggle the Motion button with Space/Enter.

Visual:
7. Zoom to 200% and 400%: no sideways scrolling, nothing overlapping.
8. Turn on "Reduce motion" in the OS: effects start off.
9. Check light and dark mode.

Screen reader (not yet done on real NVDA/VoiceOver, see gaps):
10. VoiceOver (macOS: Cmd+F5) or NVDA (Windows): list headings (VO+U / NVDA+F7)
    and landmarks; read a tracklist row by row; start and pause a song; open and
    close a video.

---

## Known gaps (open items)

| Gap | Why it matters | What's needed |
|---|---|---|
| No test on a real screen reader yet | The accessibility tree was checked by script, which can't judge the listening experience | Run step 10 with VoiceOver and NVDA |
| No testing with disabled users | Co-creation catches problems no checklist does | Ask a few listeners who use assistive tech to try the page and say what's hard |
| Caption timing is machine-made | Captions were time-aligned automatically (Demucs + MMS forced alignment, cross-checked with Whisper); a few cues in repeated choruses may sit a second early or late | Watch each video once with captions on and nudge any off cue in `Videos/Captions/*.vtt` |
| Real-device testing | Only desktop Chrome was tested | Check Safari (iOS/macOS) and Firefox |
