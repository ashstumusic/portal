/* ════════════════════════════════════════════════════════════════════
   PSYCHE: the homepage's psychedelic layer. Pairs with shared/psyche.css.

     field      liquid-chrome / acid-wash gradient behind the page, warped
                by scroll velocity and pointer acceleration (the frosted
                glass panels in psyche.css refract it)
     map        "constellation" site map: sections, releases and videos as
                a node graph over sacred geometry (toolbar button)
     wormhole   folding, tunnelling transition for in-page navigation
     wave       audio-reactive ridgeline waveform + particle bloom in the
                hero panel, cool blue when calm, solar flare on peaks
     trail      iridescent ribbon behind the cursor (mouse/trackpad only)
     ripple     a refraction ring across the viewport on button presses
     oracle     the search palette's iris: dilates while you type, pulses
                when it finds something; offers a song to play

   Everything decorative stops under prefers-reduced-motion and can be
   switched off from the search palette ("Turn psychedelic effects off").
   The site map and search keep working either way.
   ════════════════════════════════════════════════════════════════════ */
(() => {
  'use strict';
  requestAnimationFrame(() => setTimeout(init, 0));
  function init() {
  const doc = document, root = doc.documentElement;
  const $ = (s, el = doc) => el.querySelector(s);
  const $$ = (s, el = doc) => [...el.querySelectorAll(s)];
  const reduce = matchMedia('(prefers-reduced-motion: reduce)');
  const finePointer = matchMedia('(hover: hover) and (pointer: fine)').matches;
  const store = {
    get: (k) => { try { return localStorage.getItem(k); } catch { return null; } },
    set: (k, v) => { try { localStorage.setItem(k, v); } catch {} },
  };
  let fxPref = store.get('psy-fx') !== 'off';
  const fxOn = () => fxPref && !reduce.matches;
  const announce = (m) => window.kinetic?.announce?.(m);
  function syncFx() { root.classList.toggle('psy-calm', !fxOn()); field.redraw(); }
  reduce.addEventListener?.('change', () => syncFx());

  root.classList.add('psy');

  // ── SHARED POINTER + SCROLL STATE ────────────────────────────────
  const ptr = { x: innerWidth / 2, y: innerHeight / 2, vx: 0, vy: 0, t: 0, energy: 0 };
  addEventListener('pointermove', (e) => {
    const now = performance.now(), dt = Math.max(8, now - (ptr.t || now - 16));
    const vx = (e.clientX - ptr.x) / dt, vy = (e.clientY - ptr.y) / dt;
    const acc = Math.hypot(vx - ptr.vx, vy - ptr.vy);   // px/ms change: "acceleration"
    ptr.energy = Math.min(2.2, ptr.energy + acc * 0.35);
    ptr.x = e.clientX; ptr.y = e.clientY; ptr.vx = vx; ptr.vy = vy; ptr.t = now;
    if (e.pointerType === 'mouse' || e.pointerType === 'pen') trail.add(e.clientX, e.clientY);
    field.wake();
  }, { passive: true });
  let scrollVel = 0, lastScrollY = scrollY, lastScrollT = performance.now();
  addEventListener('scroll', () => {
    const now = performance.now(), dt = Math.max(8, now - lastScrollT);
    scrollVel = scrollVel * 0.6 + ((scrollY - lastScrollY) / dt) * 0.4;   // px/ms, smoothed
    lastScrollY = scrollY; lastScrollT = now;
    field.wake();
  }, { passive: true });

  // ── FIELD: liquid chrome + acid wash ─────────────────────────────
  // A low-resolution canvas (1/10 of the viewport) painted per pixel with a
  // domain-warped sine field, mapped through an ultraviolet / magenta /
  // chrome / lime palette with specular "metal" bands, then stretched
  // smooth by the browser. ~15k pixels a frame at 30 fps: cheap.
  const field = (() => {
    const cv = doc.createElement('canvas');
    cv.className = 'psy-field'; cv.setAttribute('aria-hidden', 'true');
    doc.body.prepend(cv);
    const ctx = cv.getContext('2d', { alpha: false });
    const STOPS = [[44, 6, 120], [91, 33, 255], [255, 31, 168], [236, 232, 255], [198, 255, 0], [20, 210, 200], [44, 6, 120]];
    const LUT = new Uint8ClampedArray(256 * 3);
    for (let i = 0; i < 256; i++) {
      const f = (i / 255) * (STOPS.length - 1), k = Math.min(STOPS.length - 2, Math.floor(f)), u = f - k;
      const s = u * u * (3 - 2 * u);   // smoothstep between stops: glossy rather than banded
      for (let c = 0; c < 3; c++) LUT[i * 3 + c] = STOPS[k][c] + (STOPS[k + 1][c] - STOPS[k][c]) * s;
    }
    let img = null, w = 0, h = 0, t = Math.random() * 100, phase = 0, mx = 0.5, my = 0.5, raf = 0, last = 0, idleUntil = 0;
    function size() {
      w = Math.max(32, Math.min(220, Math.ceil(innerWidth / 10)));
      h = Math.max(32, Math.min(160, Math.ceil(innerHeight / 10)));
      cv.width = w; cv.height = h; img = ctx.createImageData(w, h);
    }
    function paint() {
      const d = img.data, sin = Math.sin, cos = Math.cos, ar = w / h;
      const warp = 0.85 + ptr.energy * 0.55, px = (mx - 0.5) * 2.2, py = (my - 0.5) * 2.2;
      let o = 0;
      for (let j = 0; j < h; j++) {
        const y = (j / h) * 3;
        for (let i = 0; i < w; i++) {
          const x = (i / w) * 3 * ar;
          const q1 = sin(x * 1.3 + t * 0.7 + px) + sin(y * 1.7 - t * 0.5);
          const q2 = sin(y * 1.1 + t * 0.6 + py) + cos(x * 1.5 + t * 0.4);
          const f = sin((x + q1 * warp) * 1.4 + (y + q2 * warp) * 1.1 + t * 0.3 + phase);
          let idx = ((f * 0.5 + 0.5) * 255) | 0;
          const L = idx * 3;
          // specular bands: where the fold of the field is steepest, flash chrome
          const spec = sin((q1 + q2) * 2.4 + t);
          const k = spec > 0.82 ? (spec - 0.82) * 4.2 : 0;
          d[o] = LUT[L] + (250 - LUT[L]) * k;
          d[o + 1] = LUT[L + 1] + (248 - LUT[L + 1]) * k;
          d[o + 2] = LUT[L + 2] + (255 - LUT[L + 2]) * k;
          d[o + 3] = 255;
          o += 4;
        }
      }
      ctx.putImageData(img, 0, 0);
    }
    function frame(now) {
      raf = 0;
      if (doc.hidden) return;
      if (now - last >= 33) {   // ~30 fps is plenty for a slow liquid
        const dt = Math.min(0.1, (now - (last || now)) / 1000);
        last = now;
        const v = Math.min(3, Math.abs(scrollVel));
        t += dt * (0.18 + v * 0.9);                 // fast scrolling stirs the liquid
        phase += scrollVel * dt * 2.2;              // ...and rolls the colour bands with it
        scrollVel *= 0.9;
        ptr.energy *= 0.94;                         // pointer acceleration decays
        mx += (ptr.x / innerWidth - mx) * 0.05;
        my += (ptr.y / innerHeight - my) * 0.05;
        paint();
      }
      raf = requestAnimationFrame(frame);
    }
    function wake() {
      if (!fxOn()) return;
      idleUntil = performance.now() + 4000;
      if (!raf) raf = requestAnimationFrame(frame);
    }
    size(); paint();
    addEventListener('resize', () => { size(); paint(); }, { passive: true });
    doc.addEventListener('visibilitychange', () => { if (!doc.hidden && fxOn()) wake(); });
    // It always drifts slowly while effects are on (that's the point); the
    // wake() calls just make sure a sleeping tab picks back up at once.
    if (fxOn()) wake();
    return { wake, redraw() { if (fxOn()) wake(); else { cancelAnimationFrame(raf); raf = 0; paint(); } }, get idle() { return idleUntil; } };
  })();

  // ── WORMHOLE: in-page navigation folds into a tunnel ─────────────
  function headingOf(target) {
    return target.matches('h1,h2,h3') ? target : target.querySelector('h1, h2, h3, .rel-name, .vid-title');
  }
  function land(target) {
    target.scrollIntoView({ behavior: 'instant', block: target.matches('section, #latest') ? 'start' : 'center' });
    const f = target.matches('a, button, [tabindex]') ? target : headingOf(target) || target;
    if (!f.matches('a, button, input, [tabindex]')) f.setAttribute('tabindex', '-1');
    f.focus({ preventScroll: true });
  }
  let warping = false;
  async function wormhole(target, ox = innerWidth / 2, oy = innerHeight / 2, stage = null) {
    if (!target) return;
    const id = target.id || target.closest('[id]')?.id;
    if (id && location.hash !== '#' + id) history.pushState(null, '', '#' + id);
    if (!fxOn() || warping) { stage?.closest('dialog')?.close(); target.scrollIntoView({ behavior: reduce.matches ? 'auto' : 'smooth', block: 'start' }); land(target); return; }
    warping = true;
    const worm = doc.createElement('div');
    worm.className = 'psy-worm'; worm.setAttribute('aria-hidden', 'true');
    worm.style.setProperty('--x', ox + 'px'); worm.style.setProperty('--y', oy + 'px');
    worm.innerHTML = '<i class="psy-worm-rings"></i><i class="psy-worm-core"></i>';
    doc.body.append(worm);
    const origin = `${ox}px ${oy}px`;
    const anims = [worm.animate([{ opacity: 0 }, { opacity: 1 }], { duration: 380, easing: 'ease-in', fill: 'forwards' }),
      worm.firstChild.animate([{ transform: 'scale(.15) rotate(0deg)' }, { transform: 'scale(1.6) rotate(140deg)' }], { duration: 420, easing: 'cubic-bezier(.6,0,.9,.4)', fill: 'forwards' })];
    if (stage) {
      stage.style.transformOrigin = origin;
      anims.push(stage.animate([{ transform: 'none', opacity: 1, filter: 'none' },
        { transform: 'perspective(900px) rotateX(38deg) rotateZ(24deg) scale(3)', opacity: 0, filter: 'blur(6px) hue-rotate(160deg)' }], { duration: 420, easing: 'cubic-bezier(.6,0,.9,.4)', fill: 'forwards' }));
    } else {
      const main = $('main');
      main.style.transformOrigin = `${ox}px ${oy + scrollY}px`;
      anims.push(main.animate([{ transform: 'none', filter: 'none' }, { transform: 'perspective(1200px) rotateX(16deg) rotateY(-12deg) scale(.86)', filter: 'blur(4px) saturate(2.4) hue-rotate(80deg)' }], { duration: 400, easing: 'cubic-bezier(.6,0,.9,.4)' }));
    }
    await Promise.all(anims.map((a) => a.finished.catch(() => {})));
    if (stage) { stage.closest('dialog')?.close(); stage.getAnimations().forEach((a) => a.cancel()); }
    land(target);
    // Emerge: the destination unfolds out of the tunnel.
    const sec = target.closest('section') || target;
    sec.animate([{ transform: 'perspective(1400px) rotateX(-22deg) rotateY(10deg) scale(.8)', filter: 'blur(8px) hue-rotate(-90deg) saturate(2)', opacity: 0.2 },
      { transform: 'none', filter: 'none', opacity: 1 }], { duration: 620, easing: 'cubic-bezier(.16,1,.3,1)' });
    worm.firstChild.animate([{ transform: 'scale(1.6) rotate(140deg)' }, { transform: 'scale(5) rotate(260deg)' }], { duration: 620, easing: 'cubic-bezier(.16,1,.3,1)', fill: 'forwards' });
    await worm.animate([{ opacity: 1 }, { opacity: 0 }], { duration: 560, easing: 'ease-out', fill: 'forwards' }).finished.catch(() => {});
    worm.remove();
    warping = false;
  }
  // Nav links, the mobile drawer, footer logo and the hero scroll cue all
  // travel by wormhole.
  doc.addEventListener('click', (e) => {
    const a = e.target.closest?.('a[href^="#"]');
    if (!a || e.defaultPrevented || e.button !== 0 || e.metaKey || e.ctrlKey || e.shiftKey || e.altKey) return;
    if (!a.matches('.nav a, .nav-drawer a, .footer-logo, .hero-scroll')) return;
    const href = a.getAttribute('href');
    const target = href === '#' ? $('#latest') : doc.getElementById(href.slice(1));
    if (!target) return;
    e.preventDefault();
    const r = a.getBoundingClientRect();
    wormhole(target, r.left + r.width / 2, r.top + r.height / 2);
  });

  // ── MAP: the constellation ───────────────────────────────────────
  const map = (() => {
    const btn = $('.psy-map-btn');
    if (!btn) return null;
    const dlg = doc.createElement('dialog');
    dlg.className = 'psy-map';
    dlg.setAttribute('aria-labelledby', 'psy-map-h');
    dlg.innerHTML = `<div class="psy-map-stage">
        <svg class="psy-map-geo" aria-hidden="true"></svg>
        <h2 class="sr-only" id="psy-map-h">Site map</h2>
        <ul class="psy-map-nodes" role="list"></ul>
        <button type="button" class="psy-map-close" aria-label="Close site map"><svg aria-hidden="true" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round"><path d="M6 6l12 12M18 6L6 18"/></svg></button>
        <p class="psy-map-hint" aria-hidden="true">Pick a star to travel</p>
      </div>`;
    doc.body.append(dlg);
    const stage = $('.psy-map-stage', dlg), svg = $('.psy-map-geo', dlg), list = $('.psy-map-nodes', dlg);
    const NS = 'http://www.w3.org/2000/svg';
    const el = (tag, attrs) => { const n = doc.createElementNS(NS, tag); for (const k in attrs) n.setAttribute(k, attrs[k]); return n; };
    const text = (n) => (n?.textContent || '').replace(/\s+/g, ' ').trim();
    function graph() {
      const sections = [];
      for (const a of $$('.nav-links a[href^="#"]')) {
        const t = doc.getElementById(a.getAttribute('href').slice(1));
        if (t) sections.push({ label: text(a), target: t, kids: [] });
      }
      const about = $('#about');
      if (about && !sections.some((s) => s.target === about)) sections.push({ label: 'About', target: about, kids: [] });
      const music = sections.find((s) => s.target.id === 'music'), videos = sections.find((s) => s.target.id === 'videos');
      if (music) music.kids = $$('.rel-card').map((c) => ({ label: text($('.rel-name', c)), target: c })).filter((k) => k.label);
      if (videos) videos.kids = $$('.vid-card-wrap').map((c) => ({ label: text($('.vid-title', c)), target: c })).filter((k) => k.label);
      return sections;
    }
    function build() {
      const W = innerWidth, H = innerHeight, cx = W / 2, cy = H / 2 + 10;
      const roomy = W >= 720 && H >= 560;
      const r1x = Math.min(W * 0.26, 360), r1y = Math.min(H * (roomy ? 0.27 : 0.3), 250);
      const r2x = Math.min(W / 2 - 130, 600), r2y = Math.min(H / 2 - 70, 380);
      svg.setAttribute('viewBox', `0 0 ${W} ${H}`); svg.replaceChildren(); list.replaceChildren();
      // Sacred geometry: a flower of life and a hexagram, slowly turning.
      const geo = el('g', { class: 'psy-geo-spin', style: `transform-origin:${cx}px ${cy}px` });
      const r0 = Math.min(r1x, r1y) * 0.5;
      geo.append(el('circle', { cx, cy, r: r0, class: 'psy-geo' }));
      for (let i = 0; i < 6; i++) { const a = (i / 6) * Math.PI * 2; geo.append(el('circle', { cx: cx + Math.cos(a) * r0, cy: cy + Math.sin(a) * r0, r: r0, class: 'psy-geo' })); }
      geo.append(el('circle', { cx, cy, r: r0 * 2, class: 'psy-geo psy-geo--outer' }));
      const hex = (rot) => Array.from({ length: 3 }, (_, i) => { const a = rot + (i / 3) * Math.PI * 2; return `${cx + Math.cos(a) * r0 * 2},${cy + Math.sin(a) * r0 * 2}`; }).join(' ');
      geo.append(el('polygon', { points: hex(-Math.PI / 2), class: 'psy-geo' }), el('polygon', { points: hex(Math.PI / 2), class: 'psy-geo' }));
      const geo2 = el('g', { class: 'psy-geo-spin psy-geo-spin--rev', style: `transform-origin:${cx}px ${cy}px` });
      geo2.append(el('ellipse', { cx, cy, rx: r2x * 0.98, ry: r2y * 0.98, class: 'psy-geo psy-geo--orbit' }), el('ellipse', { cx, cy, rx: r1x, ry: r1y, class: 'psy-geo psy-geo--orbit' }));
      svg.append(geo, geo2);
      const edges = el('g', { class: 'psy-edges' }); svg.append(edges);
      const nodes = [];
      const addNode = (label, target, x, y, kind, delay) => {
        const li = doc.createElement('li');
        const a = doc.createElement('a');
        a.className = `psy-node psy-node--${kind}`;
        a.href = target.id ? '#' + target.id : '#' + (target.closest('[id]')?.id || 'main');
        a.textContent = label;
        a.style.left = x + 'px'; a.style.top = y + 'px'; a.style.setProperty('--d', delay + 'ms');
        a.addEventListener('click', (e) => {
          e.preventDefault();
          wormhole(target, x, y, stage);
        });
        li.append(a); list.append(li); nodes.push({ a, x, y });
        return a;
      };
      const sections = graph();
      const core = addNode('Ash Stu', $('#latest') || doc.body, cx, cy, 'core', 0);
      // Sections with children (Music, Videos) take the left and right sides,
      // where there's room to fan their releases and videos out vertically;
      // the rest share the top and bottom.
      const withKids = roomy ? sections.filter((s) => s.kids.length).slice(0, 2) : [];
      const others = sections.filter((s) => !withKids.includes(s));
      const angles = new Map();
      withKids.forEach((s, i) => angles.set(s, i === 0 ? 0 : Math.PI));
      if (withKids.length) {
        const top = others.slice(0, Math.ceil(others.length / 2)), bottom = others.slice(top.length);
        const spread = (list, centre, width) => list.forEach((s, i) => angles.set(s, centre + (list.length === 1 ? 0 : (i / (list.length - 1) - 0.5) * width)));
        spread(top, -Math.PI / 2, 1.2); spread(bottom, Math.PI / 2, 1.2);
      } else others.forEach((s, i) => angles.set(s, -Math.PI / 2 + (i / others.length) * Math.PI * 2));
      sections.forEach((s, i) => {
        const ang = angles.get(s);
        const x = cx + Math.cos(ang) * r1x, y = cy + Math.sin(ang) * r1y;
        const line = el('line', { x1: cx, y1: cy, x2: x, y2: y, class: 'psy-edge' });
        edges.append(line);
        const a = addNode(s.label, s.target, x, y, 'section', 120 + i * 70);
        const lines = [line];
        if (roomy && s.kids.length) {
          const spread = Math.min(2.1, (46 / r2y) * (s.kids.length - 1));   // ~46px between labels
          s.kids.forEach((k, j) => {
            const ka = ang + (s.kids.length === 1 ? 0 : (j / (s.kids.length - 1) - 0.5) * spread);
            const kx = cx + Math.cos(ka) * r2x, ky = cy + Math.sin(ka) * r2y;
            const kl = el('line', { x1: x, y1: y, x2: kx, y2: ky, class: 'psy-edge psy-edge--leaf' });
            edges.append(kl);
            const ka2 = addNode(k.label, k.target, kx, ky, 'leaf', 380 + i * 70 + j * 40);
            ka2.addEventListener('pointerenter', () => kl.classList.add('is-hot'));
            ka2.addEventListener('pointerleave', () => kl.classList.remove('is-hot'));
            ka2.addEventListener('focus', () => kl.classList.add('is-hot'));
            ka2.addEventListener('blur', () => kl.classList.remove('is-hot'));
            lines.push(kl);
          });
        }
        const hot = (on) => lines.forEach((l) => l.classList.toggle('is-hot', on));
        a.addEventListener('pointerenter', () => hot(true)); a.addEventListener('pointerleave', () => hot(false));
        a.addEventListener('focus', () => hot(true)); a.addEventListener('blur', () => hot(false));
      });
      // Faint ring through the sections: the constellation's outline.
      const secs = nodes.filter((n) => n.a.classList.contains('psy-node--section'));
      secs.forEach((n, i) => { const m = secs[(i + 1) % secs.length]; edges.prepend(el('line', { x1: n.x, y1: n.y, x2: m.x, y2: m.y, class: 'psy-edge psy-edge--ring' })); });
      return core;
    }
    let opener = null;
    function open() {
      if (dlg.open) return;
      opener = doc.activeElement;
      build();
      dlg.showModal();
      $('.psy-node--section', list)?.focus();
    }
    btn.addEventListener('click', open);
    $('.psy-map-close', dlg).addEventListener('click', () => dlg.close());
    dlg.addEventListener('click', (e) => { if (e.target === dlg || e.target === stage || e.target === svg) dlg.close(); });
    dlg.addEventListener('close', () => { if (!warping && opener?.isConnected && !list.contains(doc.activeElement)) opener.focus(); });
    addEventListener('resize', () => { if (dlg.open) build(); }, { passive: true });
    // Arrow keys move between stars (Tab works too).
    list.addEventListener('keydown', (e) => {
      const all = $$('.psy-node', list), i = all.indexOf(doc.activeElement);
      if (i < 0) return;
      const d = { ArrowRight: 1, ArrowDown: 1, ArrowLeft: -1, ArrowUp: -1 }[e.key];
      if (d) { e.preventDefault(); all[(i + d + all.length) % all.length].focus(); }
    });
    return { open };
  })();

  // ── WAVE: audio-reactive ridgelines in the hero panel ────────────
  // Real frequency data where it's safe: desktop browsers, analyser
  // created on a click so the audio context is running before the song is
  // routed through it. Phones keep a synthetic, gently breathing wave
  // (routing <audio> through Web Audio stops lock-screen playback on iOS).
  const audio = $('#np-audio');
  let actx = null, analyser = null, bins = null;
  if (finePointer && audio && 'AudioContext' in window) {
    const prime = () => { if (!actx) { try { actx = new AudioContext(); } catch {} } };
    addEventListener('pointerdown', prime, { once: true, capture: true });
    addEventListener('keydown', prime, { once: true, capture: true });
    audio.addEventListener('playing', () => {
      if (!actx || analyser) return;
      const hook = () => {
        if (analyser || actx.state !== 'running') return;
        try {
          const src = actx.createMediaElementSource(audio);
          analyser = actx.createAnalyser(); analyser.fftSize = 256; analyser.smoothingTimeConstant = 0.78;
          src.connect(analyser); analyser.connect(actx.destination);
          bins = new Uint8Array(analyser.frequencyBinCount);
        } catch { analyser = null; }
      };
      if (actx.state === 'running') hook(); else actx.resume().then(hook, () => {});
    });
  }
  const playing = () => audio && !audio.paused && !audio.ended;
  function makeWave(host, { lines = 12, alpha = 1 } = {}) {
    const cv = doc.createElement('canvas');
    cv.className = 'psy-wave'; cv.setAttribute('aria-hidden', 'true');
    host.append(cv);
    const ctx = cv.getContext('2d');
    let W = 0, H = 0, dpr = 1, raf = 0, visible = false, t = 0, last = 0;
    const hover = { x: -1, y: -1, on: false };
    const parts = [];
    const prevE = new Float32Array(48);
    function size() {
      const r = cv.getBoundingClientRect();
      dpr = Math.min(2, devicePixelRatio || 1); W = r.width; H = r.height;
      cv.width = Math.round(W * dpr); cv.height = Math.round(H * dpr);
    }
    // chromatic temperature: 0 calm blue -> violet -> magenta -> solar orange -> white-hot
    const TEMP = [[58, 168, 255], [120, 90, 255], [255, 40, 170], [255, 122, 26], [255, 236, 150]];
    const temp = (e) => {
      const f = Math.max(0, Math.min(0.999, e)) * (TEMP.length - 1), k = Math.floor(f), u = f - k;
      return TEMP[k].map((c, i) => Math.round(c + (TEMP[k + 1][i] - c) * u));
    };
    function frame(now) {
      raf = 0;
      if (!visible || doc.hidden) return;
      const dt = Math.min(0.05, (now - (last || now)) / 1000); last = now; t += dt;
      const live = playing() && analyser && bins;
      if (live) analyser.getByteFrequencyData(bins);
      ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
      ctx.clearRect(0, 0, W, H);
      ctx.globalCompositeOperation = 'lighter';
      const N = 48, gap = H / (lines + 2);
      const motion = fxOn() ? 1 : 0;
      for (let l = 0; l < lines; l++) {
        const base = H - gap * (l + 1.2);
        ctx.beginPath();
        let peak = 0;
        for (let i = 0; i <= N; i++) {
          const x = (i / N) * W;
          const env = Math.sin((i / N) * Math.PI);   // taper to the edges
          let e;
          if (live) {
            const b = bins[Math.min(bins.length - 1, Math.floor(((i / N) * 0.7 + l * 0.012) * bins.length))] / 255;
            e = b * b * (1 - l / (lines * 1.4));
          } else {
            const breathe = playing() ? 0.55 : 0.22;
            e = breathe * (0.5 + 0.5 * Math.sin(i * 0.45 + t * 1.3 * motion + l * 0.6)) * (0.6 + 0.4 * Math.sin(t * 0.7 * motion + l));
          }
          if (hover.on) { const dx = (x - hover.x) / (W * 0.12); e += 0.45 * Math.exp(-dx * dx) * (1 - Math.abs(hover.y - base) / H); }
          const y = base - e * env * gap * 3.2;
          peak = Math.max(peak, e * env);
          if (i === 0) ctx.moveTo(x, y); else ctx.lineTo(x, y);
          if (l === 0 && i < prevE.length) {
            // bloom: a particle cloud where a band spikes upward
            if (motion && e * env - prevE[i] > 0.12 && parts.length < 140) for (let p = 0; p < 3; p++) parts.push({ x, y, vx: (Math.random() - 0.5) * 40, vy: -30 - Math.random() * 70, life: 1, e: e });
            prevE[i] = e * env;
          }
        }
        const [r, g, b] = temp(Math.min(1, peak * 1.35));
        ctx.strokeStyle = `rgba(${r},${g},${b},${(0.25 + 0.6 * (1 - l / lines)) * alpha})`;
        ctx.lineWidth = l === 0 ? 2 : 1.2;
        ctx.stroke();
      }
      for (let i = parts.length - 1; i >= 0; i--) {
        const p = parts[i];
        p.x += p.vx * dt; p.y += p.vy * dt; p.vy += 20 * dt; p.life -= dt * 1.1;
        if (p.life <= 0) { parts.splice(i, 1); continue; }
        const [r, g, b] = temp(Math.min(1, 0.4 + p.e));
        ctx.fillStyle = `rgba(${r},${g},${b},${p.life * 0.9 * alpha})`;
        ctx.beginPath(); ctx.arc(p.x, p.y, 1 + p.life * 2.2, 0, Math.PI * 2); ctx.fill();
      }
      ctx.globalCompositeOperation = 'source-over';
      if (motion || live || parts.length) raf = requestAnimationFrame(frame);
    }
    const kick = () => { if (!raf && visible) raf = requestAnimationFrame(frame); };
    host.addEventListener('pointermove', (e) => { const r = cv.getBoundingClientRect(); hover.x = e.clientX - r.left; hover.y = e.clientY - r.top; hover.on = true; kick(); }, { passive: true });
    host.addEventListener('pointerleave', () => { hover.on = false; kick(); }, { passive: true });
    new IntersectionObserver((es) => { visible = es[0].isIntersecting; if (visible) { size(); kick(); } }).observe(host);
    addEventListener('resize', () => { if (visible) { size(); kick(); } }, { passive: true });
    audio?.addEventListener('play', kick); audio?.addEventListener('pause', kick);
    doc.addEventListener('visibilitychange', kick);
    return { kick };
  }
  const party = $('#party');
  const waves = [];
  if (party) waves.push(makeWave(party, { lines: 12 }));

  // ── TRAIL: iridescent ribbon behind the cursor ───────────────────
  const trail = (() => {
    if (!finePointer) return { add() {} };
    const cv = doc.createElement('canvas');
    cv.className = 'psy-trail'; cv.setAttribute('aria-hidden', 'true');
    doc.body.append(cv);
    const ctx = cv.getContext('2d');
    let dpr = 1, raf = 0;
    const pts = [], dust = [];
    const size = () => { dpr = Math.min(1.5, devicePixelRatio || 1); cv.width = innerWidth * dpr; cv.height = innerHeight * dpr; };
    size(); addEventListener('resize', size, { passive: true });
    const LIFE = 280;
    function frame(now) {
      raf = 0;
      ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
      ctx.clearRect(0, 0, innerWidth, innerHeight);
      while (pts.length && now - pts[0].t > LIFE) pts.shift();
      ctx.lineCap = 'round'; ctx.lineJoin = 'round';
      for (let i = 1; i < pts.length; i++) {
        const a = pts[i - 1], b = pts[i], age = (now - b.t) / LIFE, k = i / pts.length;
        ctx.strokeStyle = `hsla(${(b.t * 0.25 + i * 9) % 360}, 100%, 66%, ${(1 - age) * 0.55 * k})`;
        ctx.lineWidth = 1 + 6 * k * (1 - age);
        ctx.beginPath(); ctx.moveTo(a.x, a.y); ctx.lineTo(b.x, b.y); ctx.stroke();
      }
      for (let i = dust.length - 1; i >= 0; i--) {
        const d = dust[i]; d.life -= 0.035; d.x += d.vx; d.y += d.vy; d.vx *= 0.94; d.vy *= 0.94;
        if (d.life <= 0) { dust.splice(i, 1); continue; }
        ctx.fillStyle = `hsla(${d.h}, 100%, 72%, ${d.life * 0.7})`;
        ctx.fillRect(d.x - 1, d.y - 1, 2, 2);
      }
      if (pts.length > 1 || dust.length) raf = requestAnimationFrame(frame);
      else ctx.clearRect(0, 0, innerWidth, innerHeight);
    }
    return {
      add(x, y) {
        if (!fxOn()) return;
        const now = performance.now();
        pts.push({ x, y, t: now });
        if (pts.length > 40) pts.shift();
        const sp = Math.hypot(ptr.vx, ptr.vy);
        if (sp > 1.2 && dust.length < 80) dust.push({ x, y, vx: (Math.random() - 0.5) * 2, vy: (Math.random() - 0.5) * 2, life: 1, h: (now * 0.25) % 360 });
        if (!raf) raf = requestAnimationFrame(frame);
      },
    };
  })();

  // ── RIPPLE: a refraction ring across the viewport ────────────────
  doc.addEventListener('click', (e) => {
    if (!fxOn() || e.detail === 0) return;   // detail 0 = keyboard "click": no ripple from nowhere
    const b = e.target.closest?.('button, a, [role="button"], .vid-card, .rel-card');
    if (!b) return;
    const rp = doc.createElement('div');
    rp.className = 'psy-ripple'; rp.setAttribute('aria-hidden', 'true');
    rp.style.setProperty('--x', e.clientX + 'px'); rp.style.setProperty('--y', e.clientY + 'px');
    doc.body.append(rp);
    const max = Math.hypot(Math.max(e.clientX, innerWidth - e.clientX), Math.max(e.clientY, innerHeight - e.clientY)) + 60;
    const t0 = performance.now(), D = 820;
    (function step(now) {
      const p = Math.min(1, (now - t0) / D), ease = 1 - Math.pow(1 - p, 3);
      rp.style.setProperty('--r', (ease * max).toFixed(1) + 'px');
      rp.style.opacity = String(1 - p * p);
      if (p < 1) requestAnimationFrame(step); else rp.remove();
    })(t0);
  }, { capture: true, passive: true });

  // ── ORACLE: the search palette's iris ────────────────────────────
  let irisN = 0;
  const IRIS = (cls) => { const gid = `psy-iris-g${++irisN}`; return `<svg class="${cls}" aria-hidden="true" viewBox="0 0 100 100">
      <defs><radialGradient id="${gid}" cx="50%" cy="50%" r="50%"><stop offset="0" stop-color="#C6FF00"/><stop offset=".5" stop-color="#FF1FA8"/><stop offset="1" stop-color="#5B21FF"/></radialGradient></defs>
      <g class="psy-iris-petals">${Array.from({ length: 12 }, (_, i) => `<ellipse cx="50" cy="26" rx="7" ry="22" transform="rotate(${i * 30} 50 50)"/>`).join('')}</g>
      <circle class="psy-iris-ring" cx="50" cy="50" r="30" fill="url(#${gid})"/>
      <circle class="psy-iris-pupil" cx="50" cy="50" r="11"/>
      <circle class="psy-iris-glint" cx="44" cy="44" r="3"/>
    </svg>`; };
  for (const b of $$('.k-search-btn')) { const s = $('svg', b); if (s) s.outerHTML = IRIS('psy-iris psy-iris--btn'); }
  const pal = $('.k-palette-box');
  if (pal) {
    const head = doc.createElement('div');
    head.className = 'psy-oracle'; head.setAttribute('aria-hidden', 'true');
    head.innerHTML = IRIS('psy-iris psy-iris--big') + '<span class="psy-oracle-say">Ask the oracle</span>';
    pal.prepend(head);
    const say = $('.psy-oracle-say', head), inp = $('.k-palette-input', pal), lst = $('.k-palette-list', pal);
    let thinkT;
    inp.addEventListener('input', () => {
      head.classList.add('is-thinking'); head.classList.remove('is-insight', 'is-void');
      say.textContent = 'Seeing…';
      clearTimeout(thinkT);
      thinkT = setTimeout(() => {
        head.classList.remove('is-thinking');
        const n = $$('[role="option"]', lst).length;
        head.classList.add(n ? 'is-insight' : 'is-void');
        say.textContent = !inp.value.trim() ? 'Ask the oracle' : n ? `${n} vision${n === 1 ? '' : 's'}` : 'The oracle sees nothing';
      }, 420);
    });
    $('.k-palette')?.addEventListener('close', () => { head.className = 'psy-oracle'; say.textContent = 'Ask the oracle'; });
  }
  const pick = (a) => a[Math.floor(Math.random() * a.length)];
  window.kineticItems = () => {
    const out = [];
    const rl = (window.RELEASE_LIST || []).map((r, i) => ({ r, i })).filter((x) => x.r.tracks?.length);
    if (rl.length && typeof window.playTrack === 'function') {
      const { r, i } = pick(rl), ti = Math.floor(Math.random() * r.tracks.length);
      out.push({ group: 'The oracle suggests', title: `Play "${r.tracks[ti].title}"`, sub: r.name, run: () => window.playTrack(i, ti) });
    }
    if (map) out.push({ group: 'The oracle suggests', title: 'Open the constellation map', sub: 'Every section, release and video', run: () => map.open() });
    out.push({ group: 'Settings', title: fxPref ? 'Turn psychedelic effects off' : 'Turn psychedelic effects on', sub: 'Liquid background, trails, ripples, wormholes', run: () => { fxPref = !fxPref; store.set('psy-fx', fxPref ? 'on' : 'off'); syncFx(); announce(`Psychedelic effects ${fxPref ? 'on' : 'off'}`); } });
    return out;
  };

  syncFx();
  }
})();
