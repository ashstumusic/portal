# Full-stack audit: ashstu.art

Date: 2026-11-06. Scope: live homepage (`index-src.html` → `index.html`),
redesign (`redesign/`), back-end (`server.js`), data layer (`db.js`, `data.db`),
admin (`admin.html`), and build scripts. Every finding below was reproduced
with a test (curl probes, Puppeteer + axe-core in Chrome), and every fix was
re-tested after it was applied.

## Architectural scorecard

| Area | Before | After | Notes |
|---|---|---|---|
| Front-end | B+ | A− | Semantic, accessible, fast. Two separate front-end pipelines remain (biggest maintenance cost). |
| Back-end | D | B | Existed but unused, couldn't start, and exposed the whole project folder. Now locked down, validated, rate-limited. |
| Data layer | C | B− | Sensible SQLite schema; no migrations, no constraints. Constraints added for new databases; migrations still needed. |
| Security | F | B | Two critical holes fixed (file exposure, admin XSS). |
| Accessibility (WCAG 2.2 AA) | B | A− | axe: 0 violations in 6 states + homepage. One real gap: video captions. |
| Responsiveness | B | A | 280 px to 3440 px, landscape phones, 200% text, 400% zoom. |
| Performance | A | A | One request, LCP = first paint, CLS 0; idle CPU/GPU work removed. |
| Test coverage in repo | F | F | Tests exist (this audit) but live outside the repo. Roadmap step 1. |

## Phase 1: the three pillars

| Pillar | Present? | Health |
|---|---|---|
| **Front-end** | Yes, two of them: the live homepage and `redesign/` | Healthy. Static, semantic, progressively enhanced. |
| **Back-end** | Yes (`server.js`, Express): contact/subscribe API, admin inbox | **Was dead code.** Not deployed (GitHub Pages is static), no page called its API, and it crashed on start (native module built for an older Node). |
| **Data layer** | Yes (`db.js`, SQLite via better-sqlite3) | Reasonable schema and indexes; 0 subscribers, 0 messages stored. No migration mechanism. |

**Gap bridged:** the stack existed but wasn't connected. The redesign now has
an accessible contact/subscribe form wired to `POST /api/contact`. It only
appears when the page is served by `server.js`, which adds
`<meta name="contact-api">` to the page; on GitHub Pages the form stays hidden
and makes no request, so production behavior is unchanged. Admin gained a
"Data deletion requests" list. See `README.md` → *Run everything locally*.

## Severity audit, root causes, and fixes

### Critical

**C1. The server published the entire project folder, database included.**
Root cause: `app.use(express.static(__dirname))`. Verified: `/data.db`,
`/data.db-wal` (1.1 MB of journal pages, which can contain deleted rows),
`/.git/config` (so the whole repo history), `server.js`, `node_modules`, and
build scripts all returned 200. (Not exploitable today only because the server
isn't deployed.)
Fix (`server.js`): an allowlist. Only public folders and named root files
are served; dotfiles are denied; everything else is a 404.
```js
const PUBLIC_DIRS = ['Audio', 'Videos', 'Images', 'Icons', 'Fonts', 'Journal', 'redesign'];
const PUBLIC_ROOT_FILE = /^\/(?:index|resume|google[\w-]+)\.html$|^\/(?:main\.[0-9a-f]+\.js|styles(?:\.[0-9a-f]+\.min)?\.css)$|.../;
for (const dir of PUBLIC_DIRS) app.use(`/${dir}`, blockPrivate, express.static(path.join(__dirname, dir), { dotfiles: 'deny' }));
app.use((req, res, next) => (PUBLIC_ROOT_FILE.test(req.path) ? rootStatic(req, res, next) : next()));
```
Re-tested: 16 private paths (including `/%2e%2e/server.js` and `/Images/../server.js`) all return 404.

**C2. Stored XSS in the admin inbox.**
Root cause: `esc()` used `textContent → innerHTML`, which escapes `< > &` but
**not quotes**, and its output went inside `href="mailto:…"`. The server's
email check (`/^[^\s@]+@[^\s@]+\.[^\s@]+$/`) accepts quotes, so a submitted
"email" like `x"onmouseover=…"@a.co` would run script in the admin session
and could steal the admin key.
Fix: escape for attribute context, and reject quotes and angle brackets server-side.
```js
// admin.html
function esc(s) { return s == null ? '' : String(s).replace(/[&<>"'`]/g, (c) => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;', '`': '&#96;' })[c]); }
// server.js
const EMAIL_RE = /^[A-Za-z0-9.!#$%&*+/=?^_`{|}~-]+@[A-Za-z0-9-]+(?:\.[A-Za-z0-9-]+)+$/;
```

### High

**H1. Anyone could delete anyone's data.** `POST /api/delete-my-data` deleted
all rows for any email address it was given, with no proof of ownership.
Fix: it now records a request in a new `deletion_requests` table. The owner
confirms by email, then deletes from `/admin` (`POST /api/admin/delete-data`,
one transaction).

**H2. The back-end couldn't start.** `better-sqlite3` was compiled for Node 20
(`libnode.so.109`) and the machine runs Node 24.
Fix: `npm rebuild better-sqlite3` (now `npm run rebuild-native`), plus
`"engines": { "node": ">=20" }` in `package.json`.

**H3. No front-end used the back-end.** Fixed as described above (gated contact form).

**H4. CSV formula injection in the subscriber export.** A name like
`=HYPERLINK(...)` would execute when the CSV is opened in Excel or Sheets.
Fix: `csvCell()` quotes every cell, doubles inner quotes, and prefixes `= + - @` with `'`.

### Medium

| # | Issue | Root cause | Fix |
|---|---|---|---|
| M1 | Every unknown URL returned the homepage with status 200 ("soft 404") | `app.get('*', sendFile('index.html'))` | Real 404s (`text` for pages, JSON for `/api`) |
| M2 | Fragile hand-written gzip | Monkey-patched `res.write/end`, buffered whole responses | `compression` middleware |
| M3 | `/api/unsubscribe` had no rate limit; admin errors returned `err.message`; IP log trusted `X-Forwarded-For` | Inconsistent limiter use; spoofable header | Limits on every public route; generic errors; `req.ip` with opt-in `TRUST_PROXY` |
| M4 | A video that failed to load showed a black box | No `error` listener on `<video>` | `role="alert"` message with a YouTube link |
| M5 | The whole effects layer crashed on browsers without IntersectionObserver | Unguarded `new IntersectionObserver` at module top | Feature check with an "always visible" fallback |
| M6 | 280 px phones scrolled sideways; content was clipped inside cards; the nav overflowed with 200% browser text | Grid items' `min-width: auto`, an auto-layout `<table>`, unwrappable buttons and nav; `contain: paint` hid the overflow | `min-width: 0` on grid items, `table-layout: fixed` plus wrapping titles, `flex-wrap` on `.btn` and `.nav-list` |
| M7 | The particle headline redrew a 3 MB image 60×/s even at rest | Unconditional `putImageData` | Tracks particle energy and skips idle frames (measured: 60 → 0 redraws/s at rest) |
| M8 | GitHub Pages publicly serves `server.js`, `admin.html`, `package.json`, `data.json` | Pages publishes the whole repo | No secrets in them (verified, including git history). Roadmap step 2 removes them from the published site |

### Low

- Admin inserted dates and ids into HTML unescaped → escaped.
- Non-numeric ids (`/messages/abc/read`) caused a 500 → validated, 400.
- `%` and `_` in admin search acted as wildcards → `ESCAPE '\'`.
- Malformed JSON returned an HTML error page → JSON 400 / 413.
- `admin_log` grew forever → 90-day cleanup at startup and daily.
- `showModal()` on an already-open dialog throws → guarded.
- Live homepage: the logo's alt text repeated its link's name → `alt=""`.
- Schema had no `CHECK` constraints and no index on `messages.email` → added
  (applies to **new** databases only; see roadmap step 4).
- Repo root holds about 30 superseded `main.*.js` / `styles.*.css` builds and a
  stale `data.json` that nothing reads (all publicly served).

### Chaos QA: tested and holding (no fix needed)

40 song clicks in a second · 31 play/pause clicks (label always matches the
real audio state) · 50 next/previous clicks · 10× close and reopen the player ·
41 Motion-button toggles (no duplicated canvases, letters or scenes) · video
dialog spam and Esc spam · seek values of `-5`, `1e9`, `"abc"` before metadata
loaded · clicks before JavaScript loads (links fall back to the MP3) · MP3
failures (message shown) · WebGL/canvas unavailable · `localStorage` blocked
(private mode) · ultra-wide 3440×1440 · 4:3 1024×768 · landscape phone
844×390 · 10 rapid form submits (exactly 1 stored) · API: wrong types,
200,000-character fields (truncated to 200/5,000), control characters
(stripped), honeypot (silently dropped), rate limiting (readable message in the form).

### Runtime performance (Phase 4)

- **Layout thrashing:** none. The animation loop reads all layout first, then
  writes; letter positions are cached; listeners are passive and only store numbers.
- **Memory/events:** effects add and remove their DOM and listeners cleanly
  (verified across 41 toggles); WebGL contexts are explicitly released.
- **Main thread:** 0 ms blocking time on a warm desktop load; effects start
  one per task after first paint; WebGL is created on first hover.
- **DOM/paint:** 678 elements, max depth 11; no shadows, blur, or gradients;
  only `transform`/`opacity` animate.

## Phase 2: structural health and cognitive debt

- **Modularity:** inside the redesign, content (template plus `facts.json`),
  presentation (`redesign.css`) and behavior (`redesign.js` for the player and
  form, `effects.js` for motion) are cleanly separated, and effects are
  self-contained modules with `start/stop/read/write`. **The biggest debt is
  duplication:** the live homepage and the redesign render the same
  content through two different pipelines (`build-fast.py` + `prerender.py`
  vs. `build_redesign.py`). Every content change must be correct in both.
- **State:** the player's state lives in one closure (`current`, `releases`),
  but its queue is rebuilt from DOM attributes (`data-play="0:3"`), so the
  markup is the source of truth. That's predictable and works without
  JavaScript, but it couples behavior to markup shape. Effects share a few
  module-level flags (`enabled`, `resized`), all inside one loop; easy to trace.
- **Back-end structure:** routes call SQL statements directly (no service
  layer), there are no automated tests in the repo, and there's no migration
  system. Adding an external business API (payments, POS, a mailing service)
  would mean touching route code directly; a thin service module per concern
  is the first step before that.
- **Comments vs self-documentation:** names are descriptive, but files lean on
  long rationale comments (stripped from the published page). That helps
  newcomers, but it drifts if not maintained alongside the code.
  `build_redesign.py` (~520 lines) should be split into data gathering, HTML
  fragments, JSON-LD, and bundling.

## Your three questions

- **Is it accessible?** The redesign has 0 axe violations (WCAG 2.2 AA plus
  best practices) across light, dark, effects on and off, player open, video
  open, and phone. It also passes scripted keyboard, focus, zoom, text-spacing,
  and contrast checks (38 color pairs). The live homepage has 0 violations after
  the alt-text fix. **Remaining gaps:** music videos have no captions (WCAG
  1.2.2); not yet tested with NVDA/VoiceOver or with disabled users.
- **Is it mobile-responsive?** Yes. Tested from 280 px to 3440 px, landscape
  phones, 4:3, 200% browser text size, and 400% zoom: no sideways scrolling and
  no clipped content.
- **Does it follow modern semantic HTML?** Yes. Landmarks (`header`, `nav`,
  `main`, `section`, `article`, `footer`), one `h1` with no skipped heading
  levels, `table`/`th scope` for tracklists, `dl` for facts, `time datetime`
  for dates and durations, native `dialog`, `form` labels, and JSON-LD
  structured data.

## Refactoring roadmap (highest long-term return first)

1. **Put the tests in the repo.** Move the Puppeteer/axe/API checks from this
   audit into `tests/`, add `npm test`, and run it in GitHub Actions on every
   push. Everything else gets safer once this exists.
2. **Deploy Pages through Actions with a filtered artifact.** The workflow runs
   `npm run build` and publishes only public files (no `server.js`,
   `admin.html`, `package*.json`, old builds). This removes M8 and the "build
   before you push" step.
3. **Pick one front-end.** Promote the redesign to the homepage, retire
   `index-src.html` / `build-fast.py` / `prerender.py`, and delete the ~30 old
   hashed builds and `data.json`. That halves the content pipeline.
4. **Back-end hygiene before it goes live:** add migrations
   (`PRAGMA user_version` plus numbered SQL files) so schema changes such as
   the new constraints reach existing databases. Split routes, services and data
   access. Add email double opt-in for subscriptions and deletion confirmation.
   Then host it (Render, Fly.io, or a small VPS) if you want the form public.
5. **Captions for the music videos** (WebVTT, for example exported from
   YouTube's caption editor), wired to the `<video>` element with `<track>`.
6. **Real-world testing:** VoiceOver and NVDA passes, Safari and Firefox, and a
   few listeners who use assistive technology.
