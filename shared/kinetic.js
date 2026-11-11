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
    root.classList.add('k-scrolling');
    clearTimeout(scrollTimer);
    scrollTimer = setTimeout(() => root.classList.remove('k-scrolling'), 900);
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
  const CARD_SEL = '.rel-card, .vid-card, .record, .book-card, .new-record, .video-link';
  let litCard = null, litRect = null;
  if (finePointer) {
    for (const c of $$(CARD_SEL)) c.classList.add('k-spot');
    doc.addEventListener('pointerover', (e) => {
      const c = e.target.closest?.('.k-spot');
      if (c === litCard) return;
      litCard?.classList.remove('k-lit');
      litCard = c; litRect = null;
      c?.classList.add('k-lit');
    }, { passive: true });
  }

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
    const y = scrollY, dy = y - lastY;
    for (const m of magnets) if (m.el.isConnected) m.rect = m.el.getBoundingClientRect();
    if (litCard && !litRect) litRect = litCard.getBoundingClientRect();
    // WRITE
    if (header) {
      // The toolbar stays on screen at all times: it used to slide away on
      // scroll-down and return on scroll-up (class k-hide). Not any more.
      if (header.classList.contains('k-hide')) header.classList.remove('k-hide');
      if (!timelineCSS) root.style.setProperty('--k-recess', Math.min(1, y / 240).toFixed(3));
    }
    lastY = y;
    for (const m of magnets) {
      const r = m.rect;
      if (!r) continue;
      const cx = r.left + r.width / 2 - m.x, cy = r.top + r.height / 2 - m.y;   // rest position (minus current offset)
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
      litRect = null;   // re-measure next frame (cards can scroll)
    }
    if (moving) kick();
  }

  // ── GRAIN (static banding mitigation) ────────────────────────────
  const grain = doc.createElement('div');
  grain.className = 'k-grain';
  grain.setAttribute('aria-hidden', 'true');
  doc.body.append(grain);

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
      items.push({ group: 'Go to', title: textOf(a), run: () => goTo(target) });
    }
    // Songs: static pages expose a.track links; the homepage exposes RELEASE_LIST + playTrack().
    const tracks = $$('a.track[data-play]');
    if (tracks.length) {
      for (const a of tracks) items.push({ group: 'Play a song', title: a.textContent.trim(), sub: textOf(a.closest('.record')?.querySelector('.record-title')), run: () => a.click() });
    } else if (Array.isArray(window.RELEASE_LIST) && typeof window.playTrack === 'function') {
      window.RELEASE_LIST.forEach((rel, r) => rel.tracks.forEach((t, ti) => items.push({ group: 'Play a song', title: t.title, sub: rel.name, run: () => window.playTrack(r, ti) })));
    }
    for (const v of $$('a.video-link')) items.push({ group: 'Watch a video', title: textOf(v.closest('.video')?.querySelector('.video-name')), run: () => v.click() });
    for (const v of $$('.vid-card')) items.push({ group: 'Watch a video', title: (v.getAttribute('aria-label') || '').replace(/^Play\s*/, '').replace(/^["“]|["”]$/g, ''), run: () => v.click() });
    const fx = $('.fx-toggle');
    if (fx) items.push({ group: 'Actions', title: fx.getAttribute('aria-pressed') === 'true' ? 'Turn motion effects off' : 'Turn motion effects on', run: () => fx.click() });
    const mail = $('a[href^="mailto:"]');
    if (mail && navigator.clipboard) items.push({ group: 'Actions', title: 'Copy booking email address', sub: mail.href.slice(7).split('?')[0], run: () => navigator.clipboard.writeText(mail.href.slice(7).split('?')[0]).then(() => announce('Email address copied')) });
    const kit = $('a[href$=".zip"]');
    if (kit) items.push({ group: 'Actions', title: 'Download the press kit', sub: 'ZIP', run: () => kit.click() });
    return items.filter((i) => i.title);
  }
  function goTo(target) {
    target.scrollIntoView({ behavior: motionOK() ? 'smooth' : 'auto', block: 'start' });
    const focusable = target.matches('h1,h2,h3,[tabindex]') ? target : target.querySelector('h1, h2, h3');
    if (focusable) { if (!focusable.hasAttribute('tabindex')) focusable.setAttribute('tabindex', '-1'); focusable.focus({ preventScroll: true }); }
  }

  const dlg = doc.createElement('dialog');
  dlg.className = 'k-palette';
  dlg.setAttribute('aria-label', 'Search and quick actions');
  dlg.innerHTML = `<div class="k-palette-box">
      <input class="k-palette-input" type="text" role="combobox" aria-expanded="true" aria-autocomplete="list" aria-controls="k-palette-list"
             aria-label="Search songs, videos, sections and actions" placeholder="Search songs, videos, sections…" autocomplete="off" spellcheck="false">
      <ul class="k-palette-list" id="k-palette-list" role="listbox" aria-label="Results"></ul>
      <button type="button" class="k-palette-close">Close</button>
      <p class="k-palette-foot" aria-hidden="true"><span><kbd>↑</kbd> <kbd>↓</kbd> move</span><span><kbd>Enter</kbd> open</span><span><kbd>Esc</kbd> close</span></p>
    </div>`;
  doc.body.append(dlg);
  const input = $('.k-palette-input', dlg), list = $('.k-palette-list', dlg);
  let all = [], shown = [], active = 0, opener = null, countT;
  function render() {
    const q = input.value.toLowerCase().trim().split(/\s+/).filter(Boolean);
    shown = all.filter((i) => { const hay = `${i.title} ${i.sub || ''} ${i.group}`.toLowerCase(); return q.every((w) => hay.includes(w)); });
    if (q.length) shown.sort((a, b) => (b.title.toLowerCase().startsWith(q[0]) ? 1 : 0) - (a.title.toLowerCase().startsWith(q[0]) ? 1 : 0));
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
  function openPalette() {
    if (dlg.open) return;
    opener = doc.activeElement;
    all = gatherItems(); active = 0; input.value = '';
    palette.open = true;
    header?.classList.remove('k-hide');
    dlg.showModal();
    render();
    input.focus();
  }
  function closePalette(restore = true) {
    if (!dlg.open) return;
    dlg.close();
    palette.open = false;
    if (restore && opener?.isConnected) opener.focus();
  }
  input.addEventListener('input', () => { active = 0; render(); });
  input.addEventListener('keydown', (e) => {
    const map = { ArrowDown: active + 1, ArrowUp: active - 1, Home: 0, End: shown.length - 1, PageDown: active + 5, PageUp: active - 5 };
    if (e.key in map) { e.preventDefault(); setActive(map[e.key]); }
    else if (e.key === 'Enter') { e.preventDefault(); choose(active); }
  });
  dlg.addEventListener('click', (e) => { if (e.target === dlg) closePalette(); });
  $('.k-palette-close', dlg).addEventListener('click', () => closePalette());
  dlg.addEventListener('close', () => { palette.open = false; });
  doc.addEventListener('keydown', (e) => {
    const typing = /^(input|textarea|select)$/i.test(doc.activeElement?.tagName || '') || doc.activeElement?.isContentEditable;
    if ((e.key === 'k' || e.key === 'K') && (e.metaKey || e.ctrlKey)) { e.preventDefault(); dlg.open ? closePalette() : openPalette(); }
    else if (e.key === '/' && !typing && !dlg.open && !e.metaKey && !e.ctrlKey && !e.altKey) { e.preventDefault(); openPalette(); }
  });
  for (const b of $$('.k-search-btn')) b.addEventListener('click', openPalette);

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
    return map;
  };
  doc.addEventListener('keydown', (e) => {
    if (!keysOn || dlg.open || e.metaKey || e.ctrlKey || e.altKey) return;
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
  function blip(freq = 880) {
    if (!soundsOn) return;
    try {
      actx ??= new AudioContext();
      const o = actx.createOscillator(), g = actx.createGain(), t = actx.currentTime;
      o.frequency.value = freq; o.type = 'sine';
      g.gain.setValueAtTime(0.0001, t); g.gain.exponentialRampToValueAtTime(0.05, t + 0.005); g.gain.exponentialRampToValueAtTime(0.0001, t + 0.06);
      o.connect(g).connect(actx.destination); o.start(t); o.stop(t + 0.07);
    } catch {}
  }
  doc.addEventListener('pointerdown', (e) => {
    const b = e.target.closest?.('button, .btn, [role="button"]');
    if (!b) return;
    if (e.pointerType === 'touch' && navigator.vibrate && motionOK()) navigator.vibrate(6);
    blip(b.matches('.fx-toggle, .fs-lyrics-toggle') ? 660 : 880);
  }, { passive: true });

  // Extra palette entries for these settings.
  const _gather = gatherItems;
  gatherItems = function () {   // eslint-disable-line no-func-assign
    const items = _gather();
    if (hasKeys) items.push({ group: 'Settings', title: keysOn ? 'Turn off single-key shortcuts' : 'Turn on single-key shortcuts', sub: 'G then L / W / A / B, and /', run: () => { keysOn = !keysOn; store.set('k-keys', keysOn ? 'on' : 'off'); announce(`Single-key shortcuts ${keysOn ? 'on' : 'off'}`); } });
    items.push({ group: 'Settings', title: soundsOn ? 'Turn off interface sounds' : 'Turn on interface sounds', run: () => { soundsOn = !soundsOn; store.set('k-sounds', soundsOn ? 'on' : 'off'); announce(`Interface sounds ${soundsOn ? 'on' : 'off'}`); blip(); } });
    // Page-specific entries (the homepage's psyche.js adds the oracle's
    // suggestions up top and its own settings at the end).
    if (typeof window.kineticItems === 'function') {
      try { const extra = window.kineticItems(); items.unshift(...extra.filter((it) => it.group !== 'Settings')); items.push(...extra.filter((it) => it.group === 'Settings')); } catch {}
    }
    // Shortcut hints for section jumps.
    for (const it of items) if (it.group === 'Go to' && keysOn && hasKeys) it.kbd = ['G', it.title.trim()[0]?.toUpperCase()];
    return items;
  };

  // Search button tooltips: "⌘K" on Apple platforms, "Ctrl+K" elsewhere,
  // and no shortcut at all on touch-only devices (see hasKeys).
  syncKeys();

  window.kinetic = { announce, swapLabel, openPalette };
  }
})();
