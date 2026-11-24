/* ════════════════════════════════════════════════════════════════════
   KINETIC: shared interaction layer for every ashstu.art page.
   Pairs with shared/kinetic.css. Feature-detects each page's markup, so
   one file serves the homepage, /redesign/ and /redesign-2/.

     theme      light/dark toggle, View Transitions reveal, persisted
     header     recedes on scroll-down, returns on any scroll-up
     palette    ⌘K / Ctrl+K command palette (ARIA combobox + listbox)
     magnets    spring-physics magnetic pull on primary buttons
     spotlight  cursor-tracked light across cards
     links      direction-aware underlines, hover-intent prefetch
     misc       idle-fading scrollbars, grain overlay, announcements

   Rules: passive listeners that only record numbers; one rAF loop that
   reads, then writes; transform/opacity only; everything decorative is
   skipped under prefers-reduced-motion and on touch-only devices.
   ════════════════════════════════════════════════════════════════════ */
(() => {
  'use strict';
  // Start after the first frame has painted: rAF fires before paint, the
  // timeout after it. Nothing here is needed for the first frame (the
  // theme is already set by the inline <head> script and every control is
  // in the static HTML), so it never delays first paint.
  requestAnimationFrame(() => setTimeout(init, 0));
  function init() {
  const doc = document, root = doc.documentElement;
  const $ = (s, el = doc) => el.querySelector(s);
  const $$ = (s, el = doc) => [...el.querySelectorAll(s)];
  const reduce = matchMedia('(prefers-reduced-motion: reduce)');
  const finePointer = matchMedia('(hover: hover) and (pointer: fine)').matches;
  const motionOK = () => !reduce.matches;
  const store = {
    get: (k) => { try { return localStorage.getItem(k); } catch { return null; } },
    set: (k, v) => { try { localStorage.setItem(k, v); } catch {} },
  };

  // ── ANNOUNCEMENTS (screen readers) ───────────────────────────────
  const live = doc.createElement('div');
  live.className = 'sr-only';
  live.setAttribute('aria-live', 'polite');
  live.setAttribute('aria-atomic', 'true');
  Object.assign(live.style, { position: 'absolute', width: '1px', height: '1px', overflow: 'hidden', clip: 'rect(0 0 0 0)', whiteSpace: 'nowrap' });
  doc.body.append(live);
  let liveT;
  function announce(msg) {
    clearTimeout(liveT);
    live.textContent = '';
    liveT = setTimeout(() => { live.textContent = msg; }, 60);   // re-announce identical messages
  }

  // ── THEME ─────────────────────────────────────────────────────────
  // The system setting (no toggle): the inline <head> script set
  // data-theme before first paint; this keeps it in step if the OS
  // switches (e.g. sunset auto dark mode) while the page is open. A page
  // can lock its theme with data-theme-lock (the homepage is always dark:
  // a space-black sky for its cutout stars).
  const sysDark = matchMedia('(prefers-color-scheme: dark)');
  const theme = () => root.dataset.themeLock || (sysDark.matches ? 'dark' : 'light');
  function syncTheme() { root.setAttribute('data-theme', theme()); root.classList.toggle('k-dark', theme() === 'dark'); }
  sysDark.addEventListener?.('change', syncTheme);
  syncTheme();

  // ── FRAME STATE ───────────────────────────────────────────────────
  const ptr = { x: -1e4, y: -1e4, active: false };
  addEventListener('pointermove', (e) => { ptr.x = e.clientX; ptr.y = e.clientY; ptr.active = true; kick(); }, { passive: true });
  doc.addEventListener('mouseout', (e) => { if (!e.relatedTarget) { ptr.active = false; kick(); } }, { passive: true });

  // ── HEADER: recede on scroll-down, return on scroll-up ───────────
  const header = $('.masthead') || $('nav.nav');
  const timelineCSS = CSS.supports?.('animation-timeline: scroll()');
  let lastY = scrollY, scrollTimer;
  const palette = { open: false };
  function headerPinned() {
    return palette.open || !header || header.contains(doc.activeElement) ||
      root.classList.contains('fs-locked') || $('.nav-drawer[aria-hidden="false"]');
  }
  addEventListener('scroll', () => {
    // (This used to mark the page "k-scrolling" to brighten the scrollbar thumb while it moved. The scrollbar's colour
    // is inherited by every element, so setting and clearing that mark made the browser restyle the whole page at the
    // start and end of every scroll: a visible hitch, worst on phones. The thumb is now one steady strength.)
    kick();
  }, { passive: true });
  if (header) header.addEventListener('focusin', () => header.classList.remove('k-hide'));

  // ── MAGNETS (spring physics) ──────────────────────────────────────
  // Each magnet is a damped spring pulled toward an offset proportional
  // to the pointer's distance from its center (capped), and back to 0
  // when the pointer leaves. Semi-implicit Euler, stiffness 240 /
  // damping 17 (slightly underdamped: a small, natural settle).
  const MAGNET_SEL = '.btn-primary, .f-btn:not(:has(.pt)), .icon-btn-main, .fs-play, .featured-play-overlay .rel-play-circle, .video-play';
  const magnets = (finePointer ? $$(MAGNET_SEL) : []).map((el) => {
    el.classList.add('k-magnet');
    return { el, x: 0, y: 0, vx: 0, vy: 0, tx: 0, ty: 0, rect: null, shown: '' };
  });

  // ── SPOTLIGHT CARDS ───────────────────────────────────────────────
  // (Removed, owner's request 2026-11-22: "remove the light on the cursor". The soft light that followed the pointer
  // across release and video cards is gone; litCard stays null so the per-frame code below never draws it.)
  let litCard = null, litRect = null, stale = true, measuredT = 0;
  addEventListener('scroll', () => { stale = true; }, { passive: true }); addEventListener('resize', () => { stale = true; }, { passive: true });

  // (A cursor-following "Play / Watch" lens used to live here. Removed: a
  // circle chasing the pointer over the content was disorienting, and the
  // covers and videos already show their own play buttons.)

  // ── DIRECTION-AWARE UNDERLINES ───────────────────────────────────
  doc.addEventListener('pointerover', (e) => {
    const a = e.target.closest?.('.nav-links a, .footer-links a');
    if (!a || a.contains(e.relatedTarget)) return;
    const r = a.getBoundingClientRect();
    a.style.setProperty('--k-from', e.clientX < r.left + r.width / 2 ? 'left' : 'right');
  }, { passive: true });
  doc.addEventListener('pointerout', (e) => {
    const a = e.target.closest?.('.nav-links a, .footer-links a');
    if (!a || a.contains(e.relatedTarget)) return;
    const r = a.getBoundingClientRect();
    a.style.setProperty('--k-from', e.clientX < r.left + r.width / 2 ? 'left' : 'right');   // retract toward the exit side
  }, { passive: true });

  // ── MAIN LOOP (runs only while something is moving) ──────────────
  let raf = 0, lastT = 0;
  function kick() { if (!raf) raf = requestAnimationFrame(frame); }
  function frame(now) {
    raf = 0;
    let moving = false;
    // Real elapsed time (capped), so springs behave the same at 60, 120 or
    // 144 Hz. A fixed 1/60 s step ran them twice as fast on 120 Hz screens.
    const dt = Math.min(1 / 30, Math.max(1 / 240, lastT ? (now - lastT) / 1000 : 1 / 60));
    lastT = now;
    // READ
    // (Only what this frame will actually use is measured. Asking the browser for a position in the middle of a frame
    // makes it recompute the page's styles there and then; on a plain scroll, with the pointer nowhere near a magnetic
    // button, nothing here needs measuring at all.)
    const y = header && !timelineCSS ? scrollY : lastY, dy = y - lastY;
    const live = ptr.active || magnets.some((m) => m.x || m.y || m.vx || m.vy);   // a pointer on the page, or a button still springing back
    // Where the buttons and the lit card are is measured once and remembered until something could have moved them
    // (a scroll, a resize, half a second passing), not on every frame the pointer moves.
    if (live && (stale || now - measuredT > 500)) {
      // (not ones inside a closed dialog: measuring those makes the browser lay out a part of the page it is deliberately skipping)
      for (const m of magnets) if (m.el.isConnected && (!m.el.checkVisibility || m.el.checkVisibility())) { const r = m.rect = m.el.getBoundingClientRect(); m.rx = r.left + r.width / 2 - m.x; m.ry = r.top + r.height / 2 - m.y; }
      if (litCard) litRect = litCard.getBoundingClientRect();
      stale = false; measuredT = now;
    }
    if (litCard && !litRect) litRect = litCard.getBoundingClientRect();
    // WRITE
    if (header) {
      // The toolbar stays on screen at all times: it used to slide away on
      // scroll-down and return on scroll-up (class k-hide). Not any more.
      if (header.classList.contains('k-hide')) header.classList.remove('k-hide');
      if (!timelineCSS) root.style.setProperty('--k-recess', Math.min(1, y / 240).toFixed(3));
    }
    lastY = y;
    if (live) for (const m of magnets) {
      const r = m.rect;
      if (!r) continue;
      const cx = m.rx, cy = m.ry;   // rest position (measured without the current offset)
      const dx = ptr.x - cx, dyp = ptr.y - cy, reach = Math.max(r.width, r.height) * 0.9;
      const near = ptr.active && motionOK() && Math.abs(dx) < reach && Math.abs(dyp) < reach;
      m.tx = near ? Math.max(-6, Math.min(6, dx * 0.18)) : 0;
      m.ty = near ? Math.max(-6, Math.min(6, dyp * 0.18)) : 0;
      m.vx += ((m.tx - m.x) * 240 - m.vx * 17) * dt; m.x += m.vx * dt;
      m.vy += ((m.ty - m.y) * 240 - m.vy * 17) * dt; m.y += m.vy * dt;
      if (Math.abs(m.x - m.tx) > 0.05 || Math.abs(m.vx) > 0.05 || Math.abs(m.y - m.ty) > 0.05 || Math.abs(m.vy) > 0.05) moving = true;
      else { m.x = m.tx; m.y = m.ty; m.vx = m.vy = 0; }
      const s = `${m.x.toFixed(2)}px|${m.y.toFixed(2)}px`;
      if (s !== m.shown) { m.el.style.setProperty('--k-mx', `${m.x.toFixed(2)}px`); m.el.style.setProperty('--k-my', `${m.y.toFixed(2)}px`); m.shown = s; }
    }
    if (litCard && litRect) {
      litCard.style.setProperty('--mx', `${(ptr.x - litRect.left).toFixed(0)}px`);
      litCard.style.setProperty('--my', `${(ptr.y - litRect.top).toFixed(0)}px`);
    }
    if (moving) kick();
  }


  // ── PREFETCH ON INTENT ───────────────────────────────────────────
  // Speculation Rules where supported (browser prefetches same-origin
  // pages on hover); otherwise a <link rel=prefetch> after 80 ms of hover.
  if (HTMLScriptElement.supports?.('speculationrules')) {
    const s = doc.createElement('script');
    s.type = 'speculationrules';
    s.textContent = JSON.stringify({ prefetch: [{ source: 'document', where: { and: [{ href_matches: '/*' }, { not: { href_matches: '/*.(mp3|mp4|zip|pdf)' } }] }, eagerness: 'moderate' }] });
    doc.head.append(s);
  } else {
    const done = new Set();
    let hoverT;
    doc.addEventListener('pointerover', (e) => {
      const a = e.target.closest?.('a[href]');
      clearTimeout(hoverT);
      if (!a || a.origin !== location.origin || a.pathname === location.pathname || /\.(mp3|mp4|zip|pdf)$/i.test(a.pathname) || done.has(a.href)) return;
      hoverT = setTimeout(() => {
        const l = doc.createElement('link'); l.rel = 'prefetch'; l.href = a.href; doc.head.append(l); done.add(a.href);
      }, 80);
    }, { passive: true });
  }

  // ── JITTER-FREE LABEL SWAP ───────────────────────────────────────
  function swapLabel(btn, text, ms = 2000) {
    if (!btn.querySelector(':scope > .k-label')) {
      const span = doc.createElement('span');
      span.className = 'k-label';
      span.textContent = btn.textContent.trim();
      btn.replaceChildren(span);
    }
    const label = btn.querySelector(':scope > .k-label');
    const original = btn.dataset.kOrig || (btn.dataset.kOrig = label.textContent);
    btn.setAttribute('data-k-alt', original.length >= text.length ? original : text);
    label.textContent = text;
    clearTimeout(btn._kT);
    btn._kT = setTimeout(() => { label.textContent = original; }, ms);
  }

  // ── COMMAND PALETTE ──────────────────────────────────────────────
  const textOf = (el) => {
    if (!el) return '';
    const sr = el.querySelector(':scope > .sr-only');   // kinetic-type headings keep the clean text here
    if (sr && el.querySelector('.fx-letters')) return sr.textContent.trim();
    let s = '';
    el.childNodes.forEach((n) => { if (n.nodeType === 3) s += n.textContent; else if (n.nodeType === 1 && n.getAttribute('aria-hidden') !== 'true') s += n.textContent; });
    return s.replace(/\s+/g, ' ').trim();
  };
  function gatherItems() {
    const items = [];
    const seen = new Set();
    for (const a of $$('nav a[href^="#"]')) {
      const href = a.getAttribute('href');
      const target = href.length > 1 && doc.getElementById(href.slice(1));
      if (!target || seen.has(href)) continue;
      seen.add(href);
      items.push({ group: 'Go to', tag: 'Section', title: textOf(a), run: () => goTo(target) });
    }
    // Sections that have a heading but no toolbar button (About) can be searched for too.
    for (const sec of $$('main section[id][aria-labelledby]')) {
      const h = doc.getElementById(sec.getAttribute('aria-labelledby')), name = h && textOf(h);
      if (!name || seen.has('#' + sec.id) || items.some((i) => i.title.toLowerCase() === name.toLowerCase())) continue;
      seen.add('#' + sec.id);
      items.push({ group: 'Go to', tag: 'Section', title: name, run: () => goTo(sec) });
    }
    // Songs: static pages expose a.track links; the homepage exposes RELEASE_LIST + playTrack().
    const tracks = $$('a.track[data-play]');
    if (tracks.length) {
      for (const a of tracks) items.push({ group: 'Play a song', tag: 'Song', title: a.textContent.trim(), sub: textOf(a.closest('.record')?.querySelector('.record-title')), run: () => a.click() });
    } else if (Array.isArray(window.RELEASE_LIST) && typeof window.playTrack === 'function') {
      // albums first (each goes to its release), then every song on them
      window.RELEASE_LIST.forEach((rel, r) => { const card = $$('.rel-card')[r]; if (card && rel.name) items.push({ group: 'Albums', tag: 'Album', title: rel.name, sub: `${rel.tracks.length} song${rel.tracks.length === 1 ? '' : 's'}`, run: () => {
        goTo(card);
        // ringed for a few seconds, as on the album's own page (/albums/<album>/), so the eye finds it among the others
        const now = $$('.rel-card')[r] || card;
        for (const c of $$('.rel-card.album-arrived')) c.classList.remove('album-arrived');
        now.classList.add('album-arrived'); clearTimeout(window.__albumRing);
        window.__albumRing = setTimeout(() => now.classList.remove('album-arrived'), 4200);
      } }); });
      window.RELEASE_LIST.forEach((rel, r) => rel.tracks.forEach((t, ti) => items.push({ group: 'Play a song', tag: 'Song', title: t.title, sub: rel.name, run: () => window.playTrack(r, ti) })));
    }
    for (const v of $$('a.video-link')) items.push({ group: 'Watch a video', tag: 'Video', title: textOf(v.closest('.video')?.querySelector('.video-name')), run: () => v.click() });
    for (const v of $$('.vid-card')) items.push({ group: 'Watch a video', tag: 'Video', title: (v.getAttribute('aria-label') || '').replace(/^Play\s*/, '').replace(/^["“]|["”]$/g, ''), run: () => v.click() });
    const fx = $('.fx-toggle');
    if (fx) items.push({ group: 'Actions', title: fx.getAttribute('aria-pressed') === 'true' ? 'Turn motion effects off' : 'Turn motion effects on', run: () => fx.click() });
    const mail = $('a[href^="mailto:"]');
    if (mail && navigator.clipboard) items.push({ group: 'Actions', title: 'Copy booking email address', sub: mail.href.slice(7).split('?')[0], run: () => navigator.clipboard.writeText(mail.href.slice(7).split('?')[0]).then(() => announce('Email address copied')) });
    const kit = $('[data-kit-zip]');   // (the press kit's Download: its ZIP is made in the browser, so it is no .zip link)
    if (kit) items.push({ group: 'Actions', title: 'Download the press kit', sub: 'ZIP', run: () => kit.click() });
    // Streaming services (the toolbar's links): each opens Ash Stu's page there.
    const seenP = new Set();
    for (const a of $$('.nav-platforms a.nav-platform')) { const name = a.getAttribute('title') || textOf(a); if (!name || seenP.has(name)) continue; seenP.add(name); items.push({ group: 'Streaming', tag: 'Streaming', title: name, sub: 'Opens in a new tab', run: () => a.click() }); }
    for (const i of items) if (!i.tag) i.tag = 'Action';
    return items.filter((i) => i.title);
  }
  // Tags: every suggestion says what kind of thing it is, and the kind can be typed as part of the search
  // ("video hope", "song raven", "album", "setting", "streaming"; "music" covers songs and albums; #video and video: work too).
  const TAG_WORDS = { Section: 'section sections page go', Song: 'song songs music track tracks play audio', Album: 'album albums music release releases record', Video: 'video videos watch', Streaming: 'streaming stream service services listen link links platform', Setting: 'setting settings option options preference preferences toggle', Lyric: 'lyric lyrics words line lines', Action: 'action actions' };
  // Lyrics: every line of every song. They are only looked through once something is typed (never in the opening
  // list); picking a line plays that song from that line (from the start when the song's lyrics are not timed).
  function lyricItems() {
    const L = window.LYRICS, R = window.RELEASE_LIST, out = [];
    if (!L || !Array.isArray(R) || typeof window.playTrack !== 'function') return out;
    R.forEach((rel, r) => rel.tracks.forEach((t, ti) => {
      const e = L[t.file]; if (!e || !Array.isArray(e.lines)) return;
      const seen = new Set();
      for (const ln of e.lines) {
        const text = String(ln[1] || '').trim(), key = text.toLowerCase(); if (!text || seen.has(key)) continue; seen.add(key);
        const at = typeof ln[0] === 'number' ? ln[0] : null;
        out.push({ group: 'Lyrics', tag: 'Lyric', title: text, sub: t.title, run: () => {
          window.playTrack(r, ti);
          const a = doc.getElementById('np-audio'); if (!a || at === null) return;
          const seek = () => { try { a.currentTime = Math.max(0, at - .3); } catch {} };
          if (a.readyState >= 1) seek(); else a.addEventListener('loadedmetadata', seek, { once: true });
        } });
      }
    }));
    return out;
  }
  // Video transcripts: every line of every video's captions (Video Files/Captions/*.vtt, the same files the video viewer
  // shows as captions) can be searched like a lyric. Picking one opens that video at that line. One of the videos is
  // a song that is on no album, so its words could not be found any other way. The caption files are small text
  // files, fetched once, the first time the search field is used (never on page load); results appear as soon as
  // they have arrived.
  let transcripts = null, transcriptsBusy = false, transcriptsReady = null;
  function parseVtt(text) {
    const out = [], blocks = String(text || '').replace(/\r/g, '').split(/\n\n+/);
    for (const b of blocks) {
      const lines = b.split('\n'), ti = lines.findIndex((l) => l.includes('-->'));
      if (ti < 0) continue;
      const m = lines[ti].match(/(?:(\d+):)?(\d{1,2}):(\d{2})[.,](\d{1,3})\s*-->/);
      if (!m) continue;
      const at = (+(m[1] || 0)) * 3600 + (+m[2]) * 60 + (+m[3]) + (+m[4]) / 1000;
      const words = lines.slice(ti + 1).join(' ').replace(/<[^>]+>/g, '').replace(/\s+/g, ' ').trim();
      if (words) out.push({ at, text: words });
    }
    return out;
  }
  function loadTranscripts() {
    if (transcripts || transcriptsBusy) return;
    const V = window.VIDEO_LIST;
    if (!Array.isArray(V) || !V.some((v) => v && v.captions) || typeof fetch !== 'function') return;
    transcriptsBusy = true;
    Promise.all(V.map((v) => (v && v.captions) ? fetch(encodeURI(v.captions)).then((r) => (r.ok ? r.text() : '')).catch(() => '') : Promise.resolve('')))
      .then((texts) => { transcripts = texts.map(parseVtt); transcriptsBusy = false; if (transcriptsReady) transcriptsReady(); });
  }
  function transcriptItems() {
    const V = window.VIDEO_LIST, out = [];
    if (!transcripts || !Array.isArray(V) || typeof window.openLightbox !== 'function') return out;
    transcripts.forEach((cues, vi) => {
      const v = V[vi]; if (!v || !cues.length) return;
      const seen = new Set();
      for (const c of cues) {
        const key = c.text.toLowerCase(); if (seen.has(key)) continue; seen.add(key);
        out.push({ group: 'Videos', tag: 'Video', line: true, title: c.text, sub: v.title + ' (video)',
          own: `${c.text} video videos transcript transcripts caption captions words line lines`.toLowerCase(),
          run: () => {
            window.openLightbox(v);
            const el = doc.getElementById('lb-video'); if (!el) return;
            const seek = () => { try { el.currentTime = Math.max(0, c.at - .3); } catch {} };
            if (el.readyState >= 1) seek(); else el.addEventListener('loadedmetadata', seek, { once: true });
          } });
      }
    });
    return out;
  }
  // One-word song lookups (scripts/song_keys.py): every song has a word of its own ("cloud" is The Cloud for the Desert).
  // "ash stu" in front of other words is ignored, so "ash stu cloud" works the way it would in a search engine.
  // Returns the words to search with and, when one of them is a song's word, that song as a result to show first
  // (songs that are not out yet have no row to play, so theirs opens the song's page).
  function songWord(q, pool) {
    let words = q;
    if (q.length > 1) { const rest = q.filter((w) => w !== 'ash' && w !== 'stu'); if (rest.length) words = rest; }
    const K = window.SONG_KEYS; let top = null;
    if (K && K.words) for (const w of words) {
      const n = K.words[w.replace(/[^a-z0-9]/g, '')]; const s = n === undefined ? null : K.songs[n]; if (!s) continue;
      top = pool.find((i) => i.tag === 'Song' && i.title === s.title)
        || { group: 'Play a song', tag: 'Song', title: s.title, sub: s.release + (s.unreleased ? ' · not released yet' : ''), run: () => { if (s.slug) location.href = '/lyrics/' + s.slug + '/'; } };
      break;
    }
    return { words, top };
  }
  // What a result can be found by: its title, sub-line and kind, plus the ways people really type them. The title with
  // punctuation dropped ("cant" finds Can't), the title run together ("presskit" finds Press Kit), and the volume
  // numbers written as digits or words ("vol 2", "volume two" find Vol. II).
  const VOL = [['vol. ii', ' vol 2 volume 2 volume two volume ii second'], ['vol. i', ' vol 1 volume 1 volume one volume i first']];
  const hayOf = (i) => {
    if (i._hay) return i._hay;
    const base = `${i.title} ${i.sub || ''} ${i.tag || ''} ${TAG_WORDS[i.tag] || ''}`.toLowerCase(), t = i.title.toLowerCase();
    let extra = ' ' + t.replace(/[^a-z0-9 ]/g, '') + ' ' + t.replace(/[^a-z0-9]/g, '');
    const padded = base.replace(/[^a-z0-9. ]/g, ' ') + ' ';
    for (const [key, words] of VOL) if (padded.includes(key + ' ')) extra += words;
    return (i._hay = base + extra);
  };
  function goTo(target) {
    target.scrollIntoView({ behavior: motionOK() ? 'smooth' : 'auto', block: 'start' });
    const focusable = target.matches('h1,h2,h3,[tabindex]') ? target : target.querySelector('h1, h2, h3');
    if (focusable) { if (!focusable.hasAttribute('tabindex')) focusable.setAttribute('tabindex', '-1'); focusable.focus({ preventScroll: true }); }
  }

  const dlg = doc.createElement('dialog');
  dlg.className = 'k-palette';
  dlg.setAttribute('aria-label', 'Tools and search');
  dlg.innerHTML = `<div class="k-palette-box">
      <input class="k-palette-input" type="text" role="combobox" aria-expanded="true" aria-autocomplete="list" aria-controls="k-palette-list"
             aria-label="Search songs, videos, sections and actions" placeholder="Search songs, videos, sections…" autocomplete="off" spellcheck="false">
      <div class="k-menu" id="k-menu"></div>
      <ul class="k-palette-list" id="k-palette-list" role="listbox" aria-label="Results"></ul>
      <button type="button" class="k-palette-close" aria-label="Close" title="Close"><svg aria-hidden="true" focusable="false" width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.4" stroke-linecap="round"><path d="M6 6l12 12M18 6 6 18"/></svg><span class="btn-word" aria-hidden="true">Close</span></button>
      <p class="k-palette-foot" aria-hidden="true"><span><kbd>↑</kbd> <kbd>↓</kbd> move</span><span><kbd>Enter</kbd> open</span><span><kbd>Esc</kbd> close</span></p>
    </div>`;
  doc.body.append(dlg);
  const input = $('.k-palette-input', dlg), list = $('.k-palette-list', dlg);
  let all = [], shown = [], active = 0, opener = null, countT;
  function render() {
    const typed = input.value.toLowerCase().trim().split(/\s+/).filter(Boolean);
    const sw = songWord(typed, all), q = sw.words;
    shown = all.filter((i) => { const hay = `${i.title} ${i.sub || ''} ${i.group}`.toLowerCase(); return q.every((w) => hay.includes(w)); });
    if (sw.top) shown = [sw.top].concat(shown.filter((i) => i !== sw.top && i.title !== sw.top.title));
    else if (q.length) shown.sort((a, b) => (b.title.toLowerCase().startsWith(q[0]) ? 1 : 0) - (a.title.toLowerCase().startsWith(q[0]) ? 1 : 0));
    active = Math.min(active, Math.max(0, shown.length - 1));
    const frag = doc.createDocumentFragment();
    let group = null;
    shown.forEach((it, i) => {
      if (it.group !== group && !q.length) {
        group = it.group;
        const g = doc.createElement('li'); g.className = 'k-palette-group'; g.setAttribute('role', 'presentation'); g.textContent = group; frag.append(g);
      }
      const li = doc.createElement('li');
      li.className = 'k-opt'; li.id = `k-opt-${i}`; li.setAttribute('role', 'option');
      li.setAttribute('aria-selected', String(i === active));
      const t = doc.createElement('span'); t.textContent = it.title; li.append(t);
      const sub = doc.createElement('span'); sub.className = 'k-opt-sub';
      if (it.kbd) { sub.setAttribute('aria-label', `Shortcut: ${it.kbd.join(' then ')}`); for (const k of it.kbd) { const kb = doc.createElement('kbd'); kb.textContent = k; sub.append(kb); } }
      else sub.textContent = it.sub || (q.length ? it.group : '');
      if (sub.childNodes.length) li.append(sub);
      li.addEventListener('pointermove', () => setActive(i));
      li.addEventListener('click', () => choose(i));
      frag.append(li);
    });
    if (!shown.length) { const e = doc.createElement('li'); e.className = 'k-empty'; e.setAttribute('role', 'presentation'); e.textContent = 'No matches.'; frag.append(e); }
    list.replaceChildren(frag);
    input.setAttribute('aria-activedescendant', shown.length ? `k-opt-${active}` : '');
    clearTimeout(countT);
    countT = setTimeout(() => announce(`${shown.length} result${shown.length === 1 ? '' : 's'}`), 400);
  }
  function setActive(i) {
    if (!shown.length) return;
    active = (i + shown.length) % shown.length;
    for (const o of $$('.k-opt', list)) o.setAttribute('aria-selected', String(o.id === `k-opt-${active}`));
    input.setAttribute('aria-activedescendant', `k-opt-${active}`);
    $(`#k-opt-${active}`, list)?.scrollIntoView({ block: 'nearest' });
  }
  function choose(i) {
    const it = shown[i];
    if (!it) return;
    closePalette(false);
    it.run();
  }
  // One dialog, two separate uses, each with its own button:
  //   SEARCH (the Search button, / or Ctrl/Cmd+K): the search field and its results, nothing else.
  //   MENU (the gear button on wider screens; the menu button on phones): no search field. On phones it lists the
  //   sections and the streaming links (the toolbar there has no room for them) and then the settings; on wider
  //   screens, where the toolbar already shows those, it is just the settings.
  const menuBox = $('.k-menu', dlg);
  const GEAR = '<svg class="k-gear" width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><circle cx="12" cy="12" r="3"/><path d="M19.4 15a1.65 1.65 0 0 0 .33 1.82l.06.06a2 2 0 0 1 0 2.83 2 2 0 0 1-2.83 0l-.06-.06a1.65 1.65 0 0 0-1.82-.33 1.65 1.65 0 0 0-1 1.51V21a2 2 0 0 1-2 2 2 2 0 0 1-2-2v-.09A1.65 1.65 0 0 0 9 19.4a1.65 1.65 0 0 0-1.82.33l-.06.06a2 2 0 0 1-2.83 0 2 2 0 0 1 0-2.83l.06-.06a1.65 1.65 0 0 0 .33-1.82 1.65 1.65 0 0 0-1.51-1H3a2 2 0 0 1-2-2 2 2 0 0 1 2-2h.09A1.65 1.65 0 0 0 4.6 9a1.65 1.65 0 0 0-.33-1.82l-.06-.06a2 2 0 0 1 0-2.83 2 2 0 0 1 2.83 0l.06.06a1.65 1.65 0 0 0 1.82.33H9a1.65 1.65 0 0 0 1-1.51V3a2 2 0 0 1 2-2 2 2 0 0 1 2 2v.09a1.65 1.65 0 0 0 1 1.51 1.65 1.65 0 0 0 1.82-.33l.06-.06a2 2 0 0 1 2.83 0 2 2 0 0 1 0 2.83l-.06.06a1.65 1.65 0 0 0-.33 1.82V9a1.65 1.65 0 0 0 1.51 1H21a2 2 0 0 1 2 2 2 2 0 0 1-2 2h-.09a1.65 1.65 0 0 0-1.51 1z"/></svg>';
  const escHtml = (t) => String(t).replace(/[&<>"]/g, (c) => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;' }[c]));
  // Where the toolbar is the phone one (Home, name, Menu): phones, and also tablets, touch screens and windows under
  // 1280px wide (the owner's request: "make an ipad have the mobile menu"). Keep in step with COMPACT_BAR in
  // scripts/compact_toolbar.py, which gives those screens the phone toolbar's CSS.
  const PHONE_BAR = '(max-width: 1279px), (hover: none) and (pointer: coarse)';
  let setsOpen = false;   // the phone menu's Settings fold (shut each time the menu opens)
  // Turning a phone on its side (or resizing a window) across the phone / wide boundary while the menu is open: the
  // menu is drawn again for the new layout. It used to keep the phone version's folded Settings header inside the
  // wide box, with the Close button on top of it and no settings to be seen.
  { const mqMenu = matchMedia(PHONE_BAR), redo = () => { if (dlg.open && dlg.dataset.mode === 'menu') { setsOpen = false; renderMenu(); } }; mqMenu.addEventListener ? mqMenu.addEventListener('change', redo) : mqMenu.addListener(redo); }
  // Pictures for the search suggestion tags (each tag shows its picture and its word)
  const TAG_PIC = {
    Song: '<path d="M9 18V5l11-2v13"/><circle cx="6" cy="18" r="3"/><circle cx="17" cy="16" r="3"/>',
    Lyric: '<path d="M4 6h16M4 12h16M4 18h10"/>',
    Album: '<circle cx="12" cy="12" r="9"/><circle cx="12" cy="12" r="2.5"/>',
    Video: '<rect x="2.5" y="6.5" width="13" height="11" rx="2.5"/><path d="M15.5 10.4 21.5 7v10l-6-3.4"/>',
    Section: '<path d="M5 12h14M13 6l6 6-6 6"/>',
    Setting: '<circle cx="12" cy="12" r="3"/><path d="M12 2v3M12 19v3M2 12h3M19 12h3M4.9 4.9l2.1 2.1M17 17l2.1 2.1M4.9 19.1 7 17M17 7l2.1-2.1"/>',
    Streaming: '<path d="M3 14v-2a9 9 0 0 1 18 0v2"/><rect x="2.5" y="14" width="4" height="6" rx="1.5"/><rect x="17.5" y="14" width="4" height="6" rx="1.5"/>',
  };
  function renderMenu(keep) {
    const links = $$('.nav-links a').filter((a) => a.getAttribute('href'));
    const plats = $$('.nav-platforms a');
    const sets = typeof settingsList === 'function' ? settingsList() : [];
    let h = '<p class="k-menu-title">Tools</p>';   // (owner, 2026-11-23: "rename the hamburger menu on mobile to tools. not menu")
    // Home first, full width with the house (the owner's request): the same as the toolbar's house, back to the top of the page.
    // It stands on its own above "Listen on" (the owner's order: Home, Listen on, the sections, then Search); the menu still
    // opens with focus on it, as the first button.
    const homeBtn = $('.nav .nav-logo') ? `<button type="button" class="k-menu-link k-menu-home" data-home="1"${$('.nav .nav-logo')?.getAttribute('data-home') === 'button' ? '' : ' aria-current="true"'}><svg aria-hidden="true" width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" focusable="false"><path d="M3.5 11.2 12 4l8.5 7.2"/><path d="M5.8 9.6V19a1 1 0 0 0 1 1h3.4v-5.2h3.6V20h3.4a1 1 0 0 0 1-1V9.6"/></svg><span>Home</span></button>` : '';
    h += homeBtn;
    if (plats.length) h += '<div class="k-menu-listen"><span class="k-menu-label" id="k-menu-listen">Listen on</span><div class="k-menu-plats" role="group" aria-labelledby="k-menu-listen">' + plats.map((a) => `<a class="k-menu-plat" href="${escHtml(a.href)}" target="_blank" rel="noopener noreferrer" aria-label="${escHtml(a.getAttribute('aria-label') || '')}" title="${escHtml(a.getAttribute('title') || '')}">${a.innerHTML}</a>`).join('') + '</div></div>';
    if (links.length) h += '<nav class="k-menu-links" aria-label="Sections">' + links.map((a, i) => `<button type="button" class="k-menu-link" data-link="${i}"${a.hasAttribute('aria-current') ? ' aria-current="true"' : ''}>${a.querySelector('svg.nav-ico') ? a.querySelector('svg.nav-ico').outerHTML : ''}<span>${escHtml(a.textContent.trim())}</span></button>`).join('') + '</nav>';
    // (the owner's order: Listen on, the sections, then Search; the top row is the menu's name with Close)
    // phones: Search lives here too - a real field; typing in it swaps the rest of the menu for suggestions
    h += '<div class="k-si k-si--flow"></div>';
    // On phones the menu is for going somewhere; the settings wait folded behind one row (wider screens: this panel IS the settings, so they are always open).
    // PATTERN (settings switches): each row is a real <button role="switch"> with aria-checked. Its NAME is the setting's
    // label alone and its DESCRIPTION the line under it (aria-labelledby / aria-describedby): a screen reader says
    // "Effects, switch, on. Haze, stars, tag flare, confetti and fireworks", not the two run together as one word.
    // Keyboard: Tab to a row, Enter or Space flips it, focus stays on the row. The "On"/"Off" text is for sighted
    // users (state is never shown by colour alone) and hidden from screen readers, who get it from aria-checked.
    // PATTERN (Settings fold, phones): a <button aria-expanded aria-controls>; Enter or Space opens and closes it;
    // the group it opens is hidden with the `hidden` attribute, so it is out of the tab order while shut.
    const fold = links.length && matchMedia(PHONE_BAR).matches;
    if (sets.length) h += (fold
      ? '<button type="button" class="settings-title settings-fold" id="k-menu-settings" aria-expanded="' + (setsOpen ? 'true' : 'false') + '" aria-controls="k-menu-settings-group">' + GEAR + '<span>Settings</span><svg class="settings-chev" width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><polyline points="6 9 12 15 18 9"/></svg></button>'
      : '<p class="settings-title" id="k-menu-settings">' + GEAR + 'Settings</p>')
      + '<div class="k-menu-settings" id="k-menu-settings-group" role="group" aria-labelledby="k-menu-settings"' + (fold && !setsOpen ? ' hidden' : '') + '>' + sets.map((it, i) => `<button type="button" class="settings-row" role="switch" aria-checked="${it.on ? 'true' : 'false'}" data-set="${i}" aria-labelledby="k-set-l${i}"${it.sub ? ` aria-describedby="k-set-d${i}"` : ''}><span class="settings-text"><span class="settings-label" id="k-set-l${i}">${escHtml(it.label || it.title)}</span>${it.sub ? `<span class="settings-sub" id="k-set-d${i}">${escHtml(it.sub)}</span>` : ''}</span><span class="settings-switch" aria-hidden="true"><span class="settings-knob"></span></span><span class="settings-state" aria-hidden="true">${it.on ? 'On' : 'Off'}</span></button>`).join('') + '</div>';
    menuBox.innerHTML = h; menuBox.classList.remove('searching');
    makeSearch($('.k-si', menuBox), { flow: true, onQuery: (has) => menuBox.classList.toggle('searching', has), beforeRun: () => closePalette(false) });
    // (the menu's search field has its own full-width line now, so it keeps the same hint as the toolbar's: "Search songs, lyrics, videos")
    if (keep != null) $$('.settings-row', menuBox)[keep]?.focus({ preventScroll: true });
  }
  function setMode(m) {
    if (dlg.dataset.mode === m) return;
    dlg.dataset.mode = m;
    input.setAttribute('aria-expanded', String(m === 'search'));
    if (m === 'search') { all = gatherItems(); active = 0; render(); }
    else { list.replaceChildren(); input.removeAttribute('aria-activedescendant'); renderMenu(null); }
  }
  menuBox.addEventListener('click', (e) => {
    const l = e.target.closest('.k-menu-link'), r = e.target.closest('.settings-row'), f = e.target.closest('.settings-fold');
    if (e.target.closest('.k-si')) return;
    if (f) { setsOpen = !setsOpen; f.setAttribute('aria-expanded', String(setsOpen)); const g = $('#k-menu-settings-group', menuBox); if (g) g.hidden = !setsOpen; return; }
    if (l && l.dataset.home) { const home = $('.nav .nav-logo'); closePalette(false); home?.click(); home?.focus({ preventScroll: true }); }   // (focus goes to the toolbar's home link, never to nothing)
    else if (l) { const a = $$('.nav-links a').filter((x) => x.getAttribute('href'))[+l.dataset.link]; closePalette(false); a?.click(); }
    else if (r) { const i = +r.dataset.set, it = settingsList()[i]; if (it) { try { it.run(); } catch {} setTimeout(() => { if (dlg.open && dlg.dataset.mode === 'menu') renderMenu(i); }, 60); } }
    else if (e.target.closest('.k-menu-plat')) closePalette(false);
  });
  // ── A search field you type straight into, with suggestions listed under it ──
  // Used in the toolbar on wider screens (a drop-down under the field) and inside the phone menu (the suggestions
  // take the place of the rest of the menu while there is something typed). A standard combobox: arrow keys move
  // through the suggestions, Enter opens one, Escape clears / closes; the active suggestion is announced.
  let siN = 0;
  function makeSearch(host, opt) {
    if (!host) return null;
    const id = 'k-si-list-' + (++siN), flow = !!(opt && opt.flow);
    host.innerHTML = '<svg class="k-si-ico" aria-hidden="true" width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round"><circle cx="11" cy="11" r="7"/><path d="M20 20l-3.5-3.5"/></svg>'
      + '<input class="k-si-input" type="text" inputmode="search" enterkeyhint="search" role="combobox" aria-expanded="false" aria-autocomplete="list" aria-controls="' + id + '" aria-label="Search songs, lyrics, albums, videos, sections, streaming services and settings" placeholder="Search songs, lyrics, videos" autocomplete="off" autocapitalize="off" spellcheck="false">'
      + '<ul class="k-si-list" id="' + id + '" role="listbox" aria-label="Suggestions" tabindex="-1" hidden></ul>';
    const inp = $('.k-si-input', host), ul = $('.k-si-list', host);
    /* a narrow toolbar field has room for one word only: a short hint there, the full one elsewhere (the accessible name is unchanged) */
    // The toolbar field's hint is the longest wording that fits it whole: "Search songs, lyrics, videos" where there is
    // room, then shorter, down to "Search" - never cut off with "..." ("Search songs, ..." at 1280px wide).
    if (!flow) {
      const fullPh = inp.getAttribute('placeholder'), opts = [fullPh, 'Search songs and videos', 'Search songs', 'Search'];
      const cv = document.createElement('canvas').getContext('2d');
      const setPh = () => {
        if (host.matches(":focus-within")) return;
        const cs = getComputedStyle(inp), room = inp.clientWidth - parseFloat(cs.paddingLeft) - parseFloat(cs.paddingRight) - 2;
        if (!(room > 0)) return;
        cv.font = `${cs.fontStyle} ${cs.fontWeight} ${cs.fontSize} ${cs.fontFamily}`;
        // (under 1200px the resting field is a toolbar button, a picture and one word like its neighbours: "Search")
        const ph = matchMedia('(max-width: 1199px)').matches ? 'Search' : (opts.find((t) => cv.measureText(t).width <= room) || 'Search');
        if (inp.getAttribute('placeholder') !== ph) inp.setAttribute('placeholder', ph);
      };
      let phT = 0; const queuePh = () => { cancelAnimationFrame(phT); phT = requestAnimationFrame(setPh); };
      queuePh(); addEventListener('resize', queuePh, { passive: true }); document.fonts?.ready?.then(queuePh);
      host.addEventListener("focusout", () => setTimeout(queuePh, 250));
    }
    let items = [], lyrics = [], hits = [], act = 0, cT = 0;
    const shut = () => { ul.hidden = true; inp.setAttribute('aria-expanded', 'false'); inp.removeAttribute('aria-activedescendant'); host.classList.remove('open'); };
    function draw() {
      const typed = inp.value.toLowerCase().trim().split(/\s+/).map((w) => w.replace(/^[#@]+|:+$/g, '')).filter(Boolean);
      const sw = songWord(typed, items), q = sw.words;
      if (opt && opt.onQuery) opt.onQuery(q.length > 0);
      if (flow && !q.length) { shut(); return; }
      hits = items.filter((i) => { const hay = hayOf(i); return q.every((w) => hay.includes(w)); });
      // a lyric is matched on its own words; the song's name counts too only when the search says "lyric(s)" (as in "lyrics raven")
      if (q.join('').length >= 2) {
        const asked = q.some((w) => 'lyrics'.startsWith(w) && w.length >= 3);
        hits = hits.concat(lyrics.filter((i) => { const own = i.own || (i.own = `${i.title} lyric lyrics words line lines`.toLowerCase()), all = i.hay || (i.hay = hayOf(i)); const hay = asked ? all : own; return q.every((w) => hay.includes(w)); }).slice(0, 25));
      }
      if (q.length) { const rank = (i) => ((i.tag === 'Lyric' || i.line) ? 0 : 2) + (i.title.toLowerCase().startsWith(q[0]) ? 1 : 0); hits.sort((a, b) => rank(b) - rank(a)); }
      if (sw.top) hits = [sw.top].concat(hits.filter((i) => i !== sw.top && !(i.tag === 'Song' && i.title === sw.top.title)));
      hits = hits.slice(0, q.length ? 50 : 12);
      act = Math.min(act, Math.max(0, hits.length - 1));
      const frag = doc.createDocumentFragment();
      hits.forEach((it, i) => {
        const li = doc.createElement('li'); li.className = 'k-si-opt'; li.id = id + '-' + i; li.setAttribute('role', 'option'); li.setAttribute('aria-selected', String(i === act));
        const t = doc.createElement('span'); t.className = 'k-si-t'; t.textContent = it.title; const u = doc.createElement('span'); u.className = 'k-si-sub'; u.textContent = it.sub || '';
        const g = doc.createElement('span'); g.className = 'k-si-tag'; g.dataset.tag = it.tag; g.innerHTML = (TAG_PIC[it.tag] ? '<svg aria-hidden="true" focusable="false" width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.4" stroke-linecap="round" stroke-linejoin="round">' + TAG_PIC[it.tag] + '</svg>' : '') + '<span>' + escHtml(it.tag) + '</span>';   // (a picture beside the word, for visitors who don't read)
        li.dataset.tag = it.tag; if (it.line) li.dataset.line = "1"; li.append(g, t, u); li.addEventListener('pointermove', () => mark(i)); li.addEventListener('click', () => pick(i)); frag.append(li);
      });
      if (!hits.length) { const e = doc.createElement('li'); e.className = 'k-si-empty'; e.setAttribute('role', 'presentation'); e.textContent = 'No matches. Try a song title or a few words of a lyric.'; frag.append(e); }
      ul.replaceChildren(frag); ul.hidden = false; host.classList.add('open');
      inp.setAttribute('aria-expanded', 'true'); if (hits.length) inp.setAttribute('aria-activedescendant', id + '-' + act); else inp.removeAttribute('aria-activedescendant');
      clearTimeout(cT); cT = setTimeout(() => announce(`${hits.length} suggestion${hits.length === 1 ? '' : 's'}`), 500);
    }
    function mark(i) { if (!hits.length) return; act = (i + hits.length) % hits.length; for (const o of $$('.k-si-opt', ul)) o.setAttribute('aria-selected', String(o.id === id + '-' + act)); inp.setAttribute('aria-activedescendant', id + '-' + act); $('#' + id + '-' + act, ul)?.scrollIntoView({ block: 'nearest' }); }
    function pick(i) { const it = hits[i]; if (!it) return; inp.value = ''; shut(); if (opt && opt.onQuery) opt.onQuery(false); inp.blur(); if (opt && opt.beforeRun) opt.beforeRun(); it.run();
      /* A song or lyric starts playing in the bar at the bottom. From the toolbar field, focus used to be left on nothing
         (the next Tab started again from the top of the page): it goes to the bar's Play/Pause, the control for what just began. */
      if (!flow && (it.tag === 'Song' || it.tag === 'Lyric')) setTimeout(() => { const b = doc.getElementById('np-play'); if (b && b.checkVisibility && b.checkVisibility() && doc.activeElement === doc.body) b.focus({ preventScroll: true }); }, 120); }
    inp.addEventListener('focus', () => {
      items = gatherItems(); lyrics = lyricItems().concat(transcriptItems()); act = 0; draw();
      // (the transcripts are fetched the first time the field is used; when they arrive, the open list is redrawn with them)
      if (!transcripts) { transcriptsReady = () => { if (doc.activeElement === inp) { lyrics = lyricItems().concat(transcriptItems()); draw(); } }; loadTranscripts(); }
    });
    inp.addEventListener('input', () => { act = 0; draw(); });
    inp.addEventListener('keydown', (e) => {
      const open = !ul.hidden;
      if (e.key === 'ArrowDown') { e.preventDefault(); open ? mark(act + 1) : draw(); }
      else if (e.key === 'ArrowUp') { e.preventDefault(); if (open) mark(act - 1); }
      else if (e.key === 'Enter') { if (open && hits.length) { e.preventDefault(); pick(act); } }
      else if (e.key === 'Escape') { if (inp.value) { e.stopPropagation(); e.preventDefault(); inp.value = ''; draw(); } else if (open && !flow) { e.stopPropagation(); shut(); inp.blur(); } }
    });
    ul.addEventListener('pointerdown', (e) => e.preventDefault());   // keep the caret in the field while choosing with the pointer
    inp.addEventListener('blur', () => setTimeout(() => { if (doc.activeElement !== inp && !flow) shut(); }, 120));
    return inp;
  }
  // the toolbar's own search field (wider screens): it replaces the old Search button, which stays as the fallback
  let barSearch = null;
  for (const b of $$('.nav .k-tools .k-search-btn')) { let box = b.previousElementSibling; if (!box || !box.classList.contains('k-si--bar')) { box = doc.createElement('div'); box.className = 'k-si k-si--bar'; b.before(box); }   /* the page may already carry the field's outline, so it is in place from the first paint */
    barSearch = makeSearch(box, {}); root.classList.add('k-inline-search'); }
  const menuBtns = () => $$('.nav-toggle, .k-settings-btn');
  function syncMenuBtns(open) { const m = open && dlg.dataset.mode === 'menu'; for (const b of menuBtns()) { b.setAttribute('aria-expanded', String(m)); if (b.matches('.nav-toggle')) b.setAttribute('aria-label', m ? 'Close tools' : 'Open tools'); } }
  function openPalette(opts) {
    if (dlg.open) return;
    const menu = !!(opts && opts.menu);
    opener = doc.activeElement;
    input.value = '';
    palette.open = true;
    header?.classList.remove('k-hide');
    dlg.dataset.mode = ''; setsOpen = false;
    dlg.showModal();
    setMode(menu ? 'menu' : 'search');
    syncMenuBtns(true);
    dlg.setAttribute('aria-label', menu ? 'Tools and settings' : 'Search');
    // PATTERN (menu dialog): a native <dialog> opened with showModal(), so the page behind is inert and Tab stays inside.
    // Focus starts on the first SECTION button (phones) or the first setting (wide screens), never on a streaming
    // link: those open another site, and a second press of Enter after opening the menu would have left this one.
    // Escape or Close shuts it and focus goes back to the button that opened it.
    if (menu) { const vis = (e) => e && e.getClientRects().length; ([...menuBox.querySelectorAll('.k-menu-link, .settings-row, .settings-fold')].find(vis) || $('.k-palette-close', dlg)).focus({ preventScroll: true }); } else input.focus();
  }
  function closePalette(restore = true) {
    if (!dlg.open) return;
    dlg.close();
    palette.open = false;
    syncMenuBtns(false);
    if (restore && opener?.isConnected) opener.focus();
    // After a finger closed it, the button would keep its focus colour (gold) until something else was tapped: let go of it.
    // (Keyboard and mouse keep focus on the button, as they should.)
    if (lastTouch && opener?.isConnected) opener.blur();
  }
  let lastTouch = false;
  addEventListener('pointerdown', (e) => { lastTouch = e.pointerType === 'touch'; }, { capture: true, passive: true });
  addEventListener('keydown', () => { lastTouch = false; }, { capture: true, passive: true });
  input.addEventListener('input', () => { active = 0; render(); });
  input.addEventListener('keydown', (e) => {
    const map = { ArrowDown: active + 1, ArrowUp: active - 1, Home: 0, End: shown.length - 1, PageDown: active + 5, PageUp: active - 5 };
    if (e.key in map) { e.preventDefault(); setActive(map[e.key]); }
    else if (e.key === 'Enter') { e.preventDefault(); choose(active); }
  });
  dlg.addEventListener('click', (e) => { if (e.target === dlg) closePalette(); });
  $('.k-palette-close', dlg).addEventListener('click', () => closePalette());
  dlg.addEventListener('close', () => { if (dlg.open) return; palette.open = false; syncMenuBtns(false); });   // the event arrives a moment after closing: if the sheet was reopened meanwhile (fast double press), it must not mark the buttons closed
  doc.addEventListener('keydown', (e) => {
    const typing = /^(input|textarea|select)$/i.test(doc.activeElement?.tagName || '') || doc.activeElement?.isContentEditable;
    if ((e.key === 'k' || e.key === 'K') && (e.metaKey || e.ctrlKey)) { e.preventDefault(); if (barSearch && barSearch.offsetWidth) { if (dlg.open) closePalette(false); barSearch.focus(); barSearch.select(); } else if (!dlg.open) openPalette({ menu: true }); else closePalette(); }
    else if (e.key === '/' && !typing && !dlg.open && !e.metaKey && !e.ctrlKey && !e.altKey && !doc.querySelector('#fs-player.open, #vid-lightbox.open')) { e.preventDefault(); if (barSearch && barSearch.offsetWidth) barSearch.focus(); else openPalette({ menu: true }); }
  });
  for (const b of $$('.k-search-btn')) b.addEventListener('click', () => openPalette());
  // the one menu button: opens the box as the menu (search field + sections + settings)
  for (const b of $$('.nav-toggle, .k-settings-btn')) b.addEventListener('click', (e) => { e.stopImmediatePropagation(); dlg.open ? closePalette() : openPalette({ menu: true }); });

  // ── DYNAMIC CONTENT ANNOUNCEMENTS ────────────────────────────────
  const lyr = $('#fs-lyrics');
  if (lyr && 'MutationObserver' in window) {
    new MutationObserver(() => { if (!lyr.hidden && $('#fs-player.open')) announce('Synced lyrics available below the player controls'); })
      .observe(lyr, { attributes: true, attributeFilter: ['hidden'] });
  }

  // ── SINGLE-KEY SHORTCUTS ─────────────────────────────────────────
  // "/" search, "g" then the first letter of a section (g l = Listen,
  // g w = Watch, g a = About, g b = Book, g h = top). Ignored while typing.
  // WCAG 2.1.4: single-character shortcuts must be switchable off, so the
  // palette has "Turn off single-key shortcuts" (remembered).
  let keysOn = store.get('k-keys') !== 'off', gPending = 0;
  // Keyboard hints only where there's likely a keyboard: devices with a
  // mouse or trackpad (any fine pointer). Touch-only phones and tablets
  // hide them, until a hardware keyboard shows itself (Tab, an arrow, Esc
  // or a Cmd/Ctrl combo - keys an on-screen keyboard doesn't send).
  let hasKeys = matchMedia('(any-pointer: fine)').matches;
  const syncKeys = () => {
    root.classList.toggle('k-nokeys', !hasKeys);
    const mac = /Mac|iPhone|iPad/.test(navigator.platform || navigator.userAgent);
    for (const b of $$('.k-search-btn')) {
      if (hasKeys) { b.setAttribute('aria-keyshortcuts', mac ? 'Meta+K' : 'Control+K'); b.title = `Search (${mac ? '⌘K' : 'Ctrl+K'})`; }
      else { b.removeAttribute('aria-keyshortcuts'); b.title = 'Search'; }
    }
  };
  doc.addEventListener('keydown', (e) => {
    if (hasKeys || !(e.key === 'Tab' || e.key === 'Escape' || e.key?.startsWith('Arrow') || e.metaKey || e.ctrlKey)) return;
    hasKeys = true; syncKeys();
    if (dlg.open) { all = gatherItems(); render(); }
  }, true);
  const sectionKeys = () => {
    const map = { h: doc.getElementById('top') || doc.body };
    for (const a of $$('nav a[href^="#"]')) {
      const t = doc.getElementById(a.getAttribute('href').slice(1));
      const k = textOf(a).trim()[0]?.toLowerCase();
      if (t && k && !map[k]) map[k] = t;
    }
    // Sections with a heading but no toolbar button (About) are listed in search with a "G, A" hint: honour it.
    for (const sec of $$('main section[id][aria-labelledby]')) {
      const h = doc.getElementById(sec.getAttribute('aria-labelledby')), k = h && textOf(h).trim()[0]?.toLowerCase();
      if (k && !map[k]) map[k] = sec;
    }
    return map;
  };
  doc.addEventListener('keydown', (e) => {
    if (!keysOn || dlg.open || e.metaKey || e.ctrlKey || e.altKey) return;
    // (not while the full-screen player or the video viewer is up: the page behind them is switched off, and
    // "G, M" used to scroll it anyway, unseen, so closing the player left the visitor somewhere else)
    if (doc.querySelector('#fs-player.open, #vid-lightbox.open')) { gPending = 0; return; }
    const el = doc.activeElement;
    if (/^(input|textarea|select)$/i.test(el?.tagName || '') || el?.isContentEditable || el?.closest?.('dialog[open]')) return;
    const k = e.key.toLowerCase();
    if (gPending && Date.now() - gPending < 1200) {
      gPending = 0;
      const t = sectionKeys()[k];
      if (t) { e.preventDefault(); goTo(t); announce(`Moved to ${textOf(t.querySelector('h1, h2')) || 'section'}`); }
      return;
    }
    if (k === 'g') { gPending = Date.now(); }
  });

  // ── HAPTICS + OPTIONAL INTERFACE SOUNDS ──────────────────────────
  // A 6 ms vibration on touch presses of buttons (Android; iOS has no
  // Vibration API). Sounds are OFF by default: a site that plays music
  // should never make surprise noises; turn on from the palette.
  let soundsOn = store.get('k-sounds') === 'on', actx = null;
  // The sounds are a school band room's percussion shelf, made in the browser (no audio files): each is a struck
  // bar or block built from its real overtone recipe - a few sine partials that die away at different speeds, plus a
  // few milliseconds of filtered noise for the mallet hitting.
  //   xylophone    rosewood bar: fundamental + a twelfth (3x), short and dry      - ordinary buttons
  //   marimba      wider bar, two octaves up (4x), rounder, lower                  - opening a menu (a rising three-note figure)
  //   glockenspiel steel bar: 2.76x and 5.4x, long ring, high                      - switches, and links out to streaming
  //   wood block   two short knocks, no ring                                       - close, back, play/pause
  //   triangle     clustered high partials, long shimmer                           - downloads
  // Notes come from one pentatonic scale, so any run of presses is in tune with itself. A button always plays the
  // same bar (picked from its name); rows in a list (sections, songs) step up the scale in order.
  const SCALE = [523.25, 587.33, 659.25, 783.99, 880.0, 1046.5, 1174.66, 1318.51, 1567.98, 1760.0];   // C major pentatonic, C5-A6
  let noiseBuf = null, master = null;
  function audio() {
    actx ??= new AudioContext();
    if (actx.state === 'suspended') actx.resume();
    if (!master) { master = actx.createGain(); master.gain.value = 0.5; const c = actx.createDynamicsCompressor(); c.threshold.value = -14; c.ratio.value = 6; master.connect(c).connect(actx.destination); }
    if (!noiseBuf) { noiseBuf = actx.createBuffer(1, Math.round(actx.sampleRate * 0.05), actx.sampleRate); const d = noiseBuf.getChannelData(0); for (let i = 0; i < d.length; i++) d[i] = Math.random() * 2 - 1; }
    return actx;
  }
  function partial(f, gain, decay, at) {
    if (f > 16000) return;
    const o = actx.createOscillator(), g = actx.createGain();
    o.type = 'sine'; o.frequency.value = f;
    g.gain.setValueAtTime(0.0001, at); g.gain.exponentialRampToValueAtTime(gain, at + 0.002); g.gain.exponentialRampToValueAtTime(0.0001, at + decay);
    o.connect(g).connect(master); o.start(at); o.stop(at + decay + 0.02);
  }
  function mallet(freq, gain, at, len = 0.012) {
    const n = actx.createBufferSource(), f = actx.createBiquadFilter(), g = actx.createGain();
    n.buffer = noiseBuf; f.type = 'bandpass'; f.frequency.value = freq; f.Q.value = 1.2;
    g.gain.setValueAtTime(gain, at); g.gain.exponentialRampToValueAtTime(0.0001, at + len);
    n.connect(f).connect(g).connect(master); n.start(at); n.stop(at + len + 0.01);
  }
  const INSTR = {
    xylophone: (f, t) => { partial(f, 0.20, 0.28, t); partial(f * 3, 0.07, 0.10, t); partial(f * 6.1, 0.02, 0.05, t); mallet(3200, 0.10, t); },
    marimba: (f, t) => { f /= 2; partial(f, 0.24, 0.45, t); partial(f * 4, 0.05, 0.14, t); partial(f * 10, 0.012, 0.05, t); mallet(1400, 0.06, t, 0.018); },
    glock: (f, t) => { f *= 2; partial(f, 0.11, 0.9, t); partial(f * 2.76, 0.045, 0.5, t); partial(f * 5.4, 0.018, 0.25, t); mallet(6000, 0.04, t, 0.006); },
    block: (f, t) => { partial(f * 1.5, 0.16, 0.045, t); partial(f * 2.42, 0.08, 0.03, t); mallet(1800, 0.14, t, 0.02); },
    triangle: (f, t) => { for (const [m, g] of [[1, 0.035], [1.33, 0.03], [1.78, 0.026], [2.31, 0.02], [2.9, 0.014]]) partial(4186 * m, g, 1.1, t); mallet(8000, 0.03, t, 0.005); },
  };
  function strike(instr = 'xylophone', note = 0, delay = 0) {
    if (!soundsOn) return;
    try { const a = audio(); INSTR[instr](SCALE[((note % SCALE.length) + SCALE.length) % SCALE.length], a.currentTime + delay); } catch {}
  }
  function figure(instr, notes, gap = 0.075) { notes.forEach((n, i) => strike(instr, n, i * gap)); }
  function blip(up = true) { figure('glock', up ? [2, 4] : [4, 2], 0.09); }   // the switch sound, also used when the Sounds setting itself is flipped
  const noteOf = (el) => { let h = 0; for (const ch of (el.getAttribute('aria-label') || el.textContent || '').trim().slice(0, 40)) h = (h * 31 + ch.charCodeAt(0)) >>> 0; return h % 6; };
  const rowIndex = (el, sel) => { const all = $$(sel, el.closest('ul, ol, nav, .k-menu-links, .rel-tracklist') || doc); return Math.max(0, all.indexOf(el)); };
  function soundFor(b) {
    if (b.matches('[role="switch"], .fx-toggle')) return blip(b.getAttribute('aria-checked') !== 'true' && b.getAttribute('aria-pressed') !== 'true');
    if (b.matches('.k-palette-close, .lb-close, .np-close, .fs-collapse, .lb-arrow')) return figure('block', [0, 0], 0.09);
    if (b.matches('.nav-toggle, .k-settings-btn')) return b.getAttribute('aria-expanded') === 'true' ? figure('marimba', [4, 2, 0]) : figure('marimba', [0, 2, 4]);
    if (b.matches('.rel-dl, .btn-epk, [download]')) return strike('triangle');
    if (b.matches('.nav-platform, .k-menu-plat, .f-btn, a.rel-btn, .vid-yt, .contact-email-link')) return strike('glock', noteOf(b));
    if (b.matches('.fs-play, .np-play, .np-ctrl, .fs-ctrl, .vid-card')) return strike('block', 2);
    if (b.matches('.nav-links a, .k-menu-link')) return strike('xylophone', rowIndex(b, '.nav-links a, .k-menu-link'));
    if (b.matches('.rel-tl-toggle')) return b.getAttribute('aria-expanded') === 'true' ? figure('xylophone', [4, 2, 0], 0.06) : figure('xylophone', [0, 2, 4], 0.06);
    const row = b.closest('.rel-track, .track-row, [data-track]');
    if (row) return strike('xylophone', rowIndex(row, '.rel-track, .track-row, [data-track]'));
    strike('xylophone', noteOf(b));
  }
  doc.addEventListener('pointerdown', (e) => {
    const b = e.target.closest?.('button, .btn, [role="button"], [role="switch"], a[href]');
    if (!b) return;
    if (e.pointerType === 'touch' && navigator.vibrate && motionOK() && !b.matches('a[href]')) navigator.vibrate(6);
    soundFor(b);
  }, { passive: true });

  // Settings live in their own panel (the gear in the page footer), not in the search palette: settingsList() is what
  // that panel shows. Each entry says what it is (label), whether it is on, and how to flip it (run).
  function settingsList() {
    const list = [];
    if (hasKeys) list.push({ group: 'Settings', label: 'Single-key shortcuts', on: keysOn, title: keysOn ? 'Turn off single-key shortcuts' : 'Turn on single-key shortcuts', sub: 'Press G, then the first letter of a section, to jump to it. Press / to search.', run: () => { keysOn = !keysOn; store.set('k-keys', keysOn ? 'on' : 'off'); announce(`Single-key shortcuts ${keysOn ? 'on' : 'off'}`); } });
    list.push({ group: 'Settings', label: 'Interface sounds', on: soundsOn, title: soundsOn ? 'Turn off interface sounds' : 'Turn on interface sounds', sub: 'Plays a short note when you press a button', run: () => { soundsOn = !soundsOn; store.set('k-sounds', soundsOn ? 'on' : 'off'); announce(`Interface sounds ${soundsOn ? 'on' : 'off'}`); blip(true); } });
    // Page-specific settings (the homepage's psyche.js adds effects).
    if (typeof window.kineticItems === 'function') { try { list.push(...window.kineticItems().filter((it) => it.group === 'Settings')); } catch {} }
    return list;
  }
  // Extra palette entries from the page (the homepage's psyche.js adds the oracle's suggestions up top). Settings are left out.
  const _gather = gatherItems;
  gatherItems = function () {   // eslint-disable-line no-func-assign
    const items = _gather();
    if (typeof window.kineticItems === 'function') {
      try { items.unshift(...window.kineticItems().filter((it) => it.group !== 'Settings')); } catch {}
    }
    // Settings can be found and switched from the search too.
    for (const st of settingsList()) items.push({ group: 'Settings', tag: 'Setting', title: st.label, sub: st.on ? 'On - turn off' : 'Off - turn on', run: () => { st.run(); } });
    // Shortcut hints for section jumps.
    for (const it of items) if (it.group === 'Go to' && keysOn && hasKeys) it.kbd = ['G', it.title.trim()[0]?.toUpperCase()];
    return items;
  };

  // Search button tooltips: "⌘K" on Apple platforms, "Ctrl+K" elsewhere,
  // and no shortcut at all on touch-only devices (see hasKeys).
  syncKeys();

  // ── Looping animations rest while off screen ──
  // The site has a dozen animations that never end (the name's shimmer and pencil wobble, the wave, a button's
  // glow). Most of them animate things the browser cannot hand to the graphics card (background position, masks,
  // filters), so each one costs style work on every frame, and they used to keep running after being scrolled
  // out of sight. Each is now paused the moment its element leaves the screen and resumed when it returns.
  if ('IntersectionObserver' in window && doc.getAnimations) {
    const watched = new WeakSet();
    // (an inline !important is the one thing certain to outrank the stylesheet's own animation rules; the class covers ::before / ::after)
    const rest1 = (el, off) => { el.classList.toggle('k-rest', off); if (off) el.style.setProperty('animation-play-state', 'paused', 'important'); else el.style.removeProperty('animation-play-state'); };
    // (The first screen's wave is three animations that must stay in step: the section and its two halves. They are
    // paused and resumed together, on the section's say-so; the halves are never judged on their own.)
    const rest = (el, off) => { rest1(el, off); if (el.classList.contains('hero-split')) for (const c of el.children) rest1(c, off); };
    const io = new IntersectionObserver((list) => { for (const en of list) rest(en.target, !en.isIntersecting); }, { rootMargin: '120px 0px' });
    const scan = () => {
      let all = []; try { all = doc.getAnimations(); } catch {}
      for (const an of all) {
        const fx = an.effect, el = fx && fx.target;
        if (!el || watched.has(el) || !(an instanceof CSSAnimation)) continue;
        if (an.animationName === 'wave-down') continue;
        let endless = false; try { endless = fx.getComputedTiming().iterations === Infinity; } catch {}
        if (!endless || getComputedStyle(el).position === 'fixed') continue;   // (fixed things are always on screen)
        watched.add(el); io.observe(el);
      }
      // Stepped loops (the name's pencil wobble: 3 drawings a second; its colour drift: 6 steps a second) only LOOK
      // different a few times a second, but while they run the browser re-examines them on every one of its sixty
      // frames, which kept an otherwise still page working flat out. Each is held paused and moved on by the clock
      // below, nine times a second: the picture is the same, the browser gets to rest in between.
      for (const an of all) {
        if (stepped.has(an) || !(an instanceof CSSAnimation) || an.playState !== 'running') continue;
        let ok = false;
        try { const kf = an.effect.getKeyframes(); ok = an.effect.getComputedTiming().iterations === Infinity && kf.length > 1 && kf.slice(0, -1).every((k) => /^step/.test(k.easing)); } catch {}
        if (!ok) continue;
        try { an.pause(); stepped.add(an); } catch {}
      }
      if (stepped.size && !clock) beat();
    };
    const stepped = new Set(); let clock = 0;
    // (On the same 111 ms beat as the haze and the stars in psyche.js, counted from the page's clock, so all three land in one frame.)
    const beat = () => { const n = performance.now(); clock = setTimeout(() => { clock = 0; tick(); if (stepped.size) beat(); }, Math.max(8, Math.ceil((n + 4) / 111) * 111 - n)); };
    // An animation paused from script is no longer ended by the browser when the stylesheet stops asking for it
    // (Effects switched off, reduced motion chosen). So that is checked here: any stepped animation the styles no
    // longer name is cancelled. Run when the page's classes or the motion setting change, and once a second.
    const prune = () => {
      for (const an of stepped) {
        const el = an.effect && an.effect.target;
        // (an animation on ::before or ::after is named in that pseudo-element's styles, not the element's)
        if (!el || !el.isConnected || !getComputedStyle(el, an.effect.pseudoElement || null).animationName.split(/,\s*/).includes(an.animationName)) { try { an.cancel(); } catch {} stepped.delete(an); }
      }
    };
    let ticks = 0;
    const tick = () => {
      if (doc.hidden) return;
      if (++ticks % 9 === 0) prune();
      const now = doc.timeline.currentTime ?? performance.now();
      for (const an of stepped) {
        const el = an.effect && an.effect.target;
        if (an.playState === 'idle' || !el || !el.isConnected) { stepped.delete(an); continue; }   // switched off (effects off, reduced motion) or gone
        if (el.classList.contains('k-rest')) continue;                                              // off screen: resting
        try { an.currentTime = now; } catch {}
      }
    };
    // (Effects switched back on, or motion allowed again: the animations are made afresh, so look again.)
    new MutationObserver(() => { setTimeout(prune, 30); setTimeout(scan, 300); }).observe(root, { attributes: true, attributeFilter: ['class'] });
    matchMedia('(prefers-reduced-motion: reduce)').addEventListener?.('change', () => { setTimeout(prune, 30); setTimeout(scan, 300); });
    for (const ms of [600, 2500, 7000, 16000]) setTimeout(scan, ms);
    let st = 0; addEventListener('scroll', () => { clearTimeout(st); st = setTimeout(scan, 500); }, { passive: true });   // animations that start later (on reveal) are picked up once scrolling settles
  }

  // ── Links that open a new tab say so ──
  // PATTERN: every link with target="_blank" (the streaming and YouTube buttons) has "(opens in a new tab)" added to
  // its spoken name, so a screen-reader user is not moved to another site and tab without warning. The words are
  // added to the aria-label where there is one (after the existing words, so the visible label still comes first),
  // otherwise as visually hidden text inside the link. Cards are drawn by script after load, so this is re-run
  // (cheaply, at most twice a second) whenever links are added.
  {
    const NOTE = ' (opens in a new tab)';
    const mark = () => {
      for (const a of doc.querySelectorAll('a[target="_blank"]:not([data-newtab])')) {
        a.dataset.newtab = '1';
        const l = a.getAttribute('aria-label');
        if (l != null) { if (!/new tab/i.test(l)) a.setAttribute('aria-label', l + NOTE); }
        else if (!/new tab/i.test(a.textContent)) { const sp = doc.createElement('span'); sp.className = 'sr-only'; sp.textContent = NOTE; a.append(sp); }
      }
    };
    let mt = 0; mark();
    new MutationObserver(() => { if (!mt) mt = setTimeout(() => { mt = 0; mark(); }, 500); }).observe(doc.body, { childList: true, subtree: true });
  }

  // PATTERN (a word on every button): every button shows a picture AND a word (the owner's rule: assume a visitor may not
  // understand pictures, and may not read; so always both). Buttons that were a picture alone get a short word, taken
  // from the button's own spoken name ("Play My Anima" -> "Play", "Show lyrics for VCR" -> "Lyrics") and kept in step
  // whenever that name changes (Play -> Pause, Mute -> Unmute). The word is aria-hidden: the spoken name already says it.
  // A button that already has its word in the markup (class="btn-word" with text) is left as it is.
  {
    const PICTURE_ONLY = '.nav .nav-platform, .k-menu-plat, .k-settings-btn, .rel-play-overlay, .featured-play-overlay, .rel-dl, .rel-lyrics-toggle, .vid-card, .lb-arrow, .lb-dot, .lb-close, #np-play, .np-ctrl, .np-close, .fs-ctrl, .fs-play';
    const RULES = [
      [/^listen on (.+?)(?:: | \(|$)/i, (m) => m[1]], [/^watch on (.+?)(?:: | \(|$)/i, (m) => m[1]],
      [/^(?:show|hide) lyrics/i, 'Lyrics'], [/^lyrics/i, 'Lyrics'], [/^download/i, 'Download'],
      [/^pause/i, 'Pause'], [/^play/i, 'Play'], [/^previous/i, 'Previous'], [/^next/i, 'Next'], [/^close/i, 'Close'],
      [/^(?:go to )?video (\d+)/i, (m) => m[1]], [/^unmute/i, 'Unmute'], [/^mute/i, 'Mute'], [/^shuffle/i, 'Shuffle'],
      [/^repeat/i, 'Repeat'], [/^settings/i, 'Settings'], [/^search/i, 'Search'],
    ];
    const wordFor = (b) => {
      const name = (b.getAttribute('aria-label') || b.getAttribute('title') || '').trim();
      for (const [re, w] of RULES) { const m = name.match(re); if (m) return typeof w === 'function' ? w(m) : w; }
      return name.split(/\s+/)[0] || '';
    };
    const fit = (b) => {
      // (a play button whose picture is a round "play" bubble gets its word inside that bubble)
      const host = b.querySelector('[class*="play-circle"]') || b;
      let sp = host.querySelector(':scope > .btn-word');
      if (sp && sp.dataset.auto !== '1') return;   // (a word written in the markup)
      if (!sp) { sp = doc.createElement('span'); sp.className = 'btn-word'; sp.dataset.auto = '1'; sp.setAttribute('aria-hidden', 'true'); host.append(sp); }
      const w = wordFor(b); if (sp.textContent !== w) sp.textContent = w;
    };
    const all = () => $$(PICTURE_ONLY).forEach(fit);
    all();
    let t = 0;
    new MutationObserver((recs) => {
      for (const r of recs) if (r.type === 'attributes' && r.target.matches && r.target.matches(PICTURE_ONLY)) fit(r.target);
      if (recs.some((r) => r.type === 'childList' && r.addedNodes.length) && !t) t = setTimeout(() => { t = 0; all(); }, 120);
    }).observe(doc.body, { childList: true, subtree: true, attributes: true, attributeFilter: ['aria-label'] });
  }

  window.kinetic = { announce, swapLabel, openPalette, settings: settingsList };
  }
})();
