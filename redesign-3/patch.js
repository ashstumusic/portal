/* ════════════════════════════════════════════════════════════════════
   THE PATCH: concept behavior (decoration only; the page is complete
   without it). Shared player/video/form behavior lives in
   redesign/redesign.js.

   1. Theme switch: felt (dark) or muslin (light). A saved choice wins
      over the system setting; the head script applies it before paint.
   2. The sung line: while a song plays, the player shows the lyric line
      being sung (timings from ../lyrics.json, fetched on first play so
      it never costs anything for visitors who don't press play).
   ════════════════════════════════════════════════════════════════════ */
(() => {
  'use strict';
  const root = document.documentElement;

  // ── 1. THEME ──────────────────────────────────────────────────────
  const btn = document.getElementById('theme-btn');
  const label = () => {
    const light = root.dataset.theme === 'light';
    btn.setAttribute('aria-label', light ? 'Switch to dark theme' : 'Switch to light theme');
  };
  if (btn) {
    label();
    btn.addEventListener('click', () => {
      root.dataset.theme = root.dataset.theme === 'light' ? 'dark' : 'light';
      try { localStorage.setItem('patch-theme', root.dataset.theme); } catch {}
      label();
    });
  }

  // ── 2. THE SUNG LINE ──────────────────────────────────────────────
  const audio = document.getElementById('audio');
  const out = document.getElementById('player-lyric');
  if (!audio || !out) return;
  let lyrics = null, loading = null, lines = null, idx = -2, swapT = 0;

  const load = () => loading ??= fetch('../lyrics.json')
    .then((r) => (r.ok ? r.json() : {}))
    .catch(() => ({}))
    .then((d) => { lyrics = d; });

  // lyrics.json is keyed by the file path ("Audio/<release>/<file>.mp3").
  const keyFor = (src) => {
    try { return decodeURIComponent(new URL(src).pathname).replace(/^\/+/, ''); } catch { return ''; }
  };
  const pick = () => {
    const e = lyrics && lyrics[keyFor(audio.currentSrc || audio.src)];
    lines = e && e.synced && e.lines && e.lines.length ? e.lines : null;
    idx = -2;
    show('');
  };
  // Fade out, swap, fade in: a hard cut every few seconds is jarring.
  const show = (text) => {
    if (out.textContent === text) return;
    clearTimeout(swapT);
    if (!text || !root.classList.contains('motion')) { out.textContent = text; return; }
    out.classList.add('is-changing');
    swapT = setTimeout(() => { out.textContent = text; out.classList.remove('is-changing'); }, 180);
  };
  const tick = () => {
    if (!lines) return;
    const t = audio.currentTime + 0.2;   // show a line just before it's sung
    let i = -1;
    // Binary search: last line whose start time is <= t.
    let lo = 0, hi = lines.length - 1;
    while (lo <= hi) { const m = (lo + hi) >> 1; if (lines[m][0] <= t) { i = m; lo = m + 1; } else hi = m - 1; }
    if (i === idx) return;
    idx = i;
    show(i >= 0 ? lines[i][1] : '');
  };

  audio.addEventListener('loadstart', () => { show(''); lines = null; load().then(pick); });
  audio.addEventListener('timeupdate', tick);
  audio.addEventListener('seeked', tick);
  audio.addEventListener('emptied', () => { lines = null; show(''); });
})();
