/* ════════════════════════════════════════════════════════════════════
   PSYCHE: the homepage's psychedelic layer. Pairs with shared/psyche.css.

     field      liquid-chrome / acid-wash gradient behind the page, warped
                by scroll velocity and pointer acceleration (the frosted
                glass panels in psyche.css refract it)
     ripple     a refraction ring across the viewport on button presses

   Everything decorative stops under prefers-reduced-motion and can be
   switched off from the search palette ("Turn background effects off").
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
  function syncFx() { root.classList.toggle('psy-calm', !fxOn()); field.redraw(); cosmos.redraw(); }
  reduce.addEventListener?.('change', () => syncFx());

  root.classList.add('psy');

  // ── SHARED POINTER + SCROLL STATE ────────────────────────────────
  const ptr = { x: innerWidth / 2, y: innerHeight / 2, vx: 0, vy: 0, t: 0, energy: 0 };
  addEventListener('pointermove', (e) => {
    const now = performance.now(), dt = Math.max(8, now - (ptr.t || now - 16));
    const vx = (e.clientX - ptr.x) / dt, vy = (e.clientY - ptr.y) / dt;
    const acc = Math.hypot(vx - ptr.vx, vy - ptr.vy);   // px/ms change: "acceleration"
    ptr.energy = Math.min(0.8, ptr.energy + acc * 0.12);
    ptr.x = e.clientX; ptr.y = e.clientY; ptr.vx = vx; ptr.vy = vy; ptr.t = now;
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
  // A low-resolution canvas (1/20 of the viewport) painted per pixel with a
  // domain-warped sine field, mapped through an ultraviolet / magenta /
  // chrome / lime palette with specular "metal" bands, then stretched
  // smooth by the browser. ~4k pixels a frame at 20 fps: cheap.
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
      // 1/20 of the viewport: the field sits faint and blurred behind the page,
      // so a quarter of the old pixel count looks identical and costs far less.
      w = Math.max(24, Math.min(110, Math.ceil(innerWidth / 20)));
      h = Math.max(24, Math.min(80, Math.ceil(innerHeight / 20)));
      cv.width = w; cv.height = h; img = ctx.createImageData(w, h);
    }
    function paint() {
      const d = img.data, sin = Math.sin, cos = Math.cos, ar = w / h;
      const warp = 0.85 + ptr.energy * 0.15, px = (mx - 0.5) * 2.2, py = (my - 0.5) * 2.2;
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
          const k = spec > 0.88 ? (spec - 0.88) * 3 : 0;
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
      if (now - last >= 50) {   // 20 fps is plenty for a slow, blurred liquid
        const dt = Math.min(0.1, (now - (last || now)) / 1000);
        last = now;
        const v = Math.min(3, Math.abs(scrollVel));
        t += dt * (0.04 + v * 0.12);                 // fast scrolling stirs the liquid
        phase += scrollVel * dt * 0.3;              // ...and rolls the colour bands with it
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
    const t0 = performance.now(), D = 600;
    (function step(now) {
      const p = Math.min(1, (now - t0) / D), ease = 1 - Math.pow(1 - p, 3);
      rp.style.setProperty('--r', (ease * max).toFixed(1) + 'px');
      rp.style.opacity = String(0.3 * (1 - p * p));
      if (p < 1) requestAnimationFrame(step); else rp.remove();
    })(t0);
  }, { capture: true, passive: true });

  // ── COSMOS: a vintage paper stage set of planets, moons and stars ──
  // Every piece is cut with straight scissor snips from E. L. Trouvelot's
  // 1880s astronomical plates (Images/cutouts/cosmos.webp, credits in
  // Images/cutouts/CREDITS.md), given a cream paper border and a hard
  // shadow, and joined with paper fasteners. Each object hangs on a thread
  // from the underside of whatever is above it (a card, a heading, the
  // hero), like scenery lowered onto a theatre stage, or floats when
  // nothing is near.
  //
  // Placement: the page is measured on every layout (text, cards, photos,
  // buttons become no-go areas) and each object goes only where its whole
  // swing stays clear of content, preferring roomy spots, spread out.
  //
  // Moving parts, worked by scrolling (12 updates a second, angles
  // snapped, like hand-moved cutouts): everything swings on its thread;
  // Saturn's ring tilts around the globe; Jupiter's moon orbits on a wire;
  // the moon's shadow slides across it (phases); the sun turns and each
  // ray flaps; the comet's jointed tail whips; stars twinkle. A fast
  // scroll shakes the lot. Still under reduced motion or with effects off.
  const cosmos = (() => {
    const NS = 'http://www.w3.org/2000/svg', SHEET = 'Images/cutouts/cosmos.webp', SWID = 1024, SHGT = 768, C = 256;
    const T = {
      jupiter: { x: 0, y: 0, w: C, h: C }, globe: { x: C, y: 0, w: C, h: C }, moon: { x: 2 * C, y: 0, w: C, h: C },
      eclipse: { x: 3 * C, y: 0, w: C, h: C }, ring: { x: 0, y: C, w: 2 * C, h: C }, spots: { x: 2 * C, y: C, w: C, h: C },
      flare: { x: 3 * C, y: C, w: C, h: C }, tail: { x: 0, y: 2 * C, w: C / 2, h: C }, head: { x: C / 2, y: 2 * C, w: C / 2, h: C / 2 },
      meteors: { x: C, y: 2 * C, w: C, h: C }, flare2: { x: 2 * C, y: 2 * C, w: C, h: C }, spots2: { x: 3 * C, y: 2 * C, w: C, h: C },
    };
    const PAPER = '#FBF5E6', INK = '#2B2420';
    let seed = 11, uid = 0;   // fixed seed: the same sky on every visit
    const rnd = () => { seed = (seed + 0x6D2B79F5) | 0; let t = Math.imul(seed ^ (seed >>> 15), 1 | seed); t = (t + Math.imul(t ^ (t >>> 7), 61 | t)) ^ t; return ((t ^ (t >>> 14)) >>> 0) / 4294967296; };
    const j = (n) => (rnd() - 0.5) * n;   // scissor wobble
    const snap = (v, s) => Math.round(v / s) * s;
    const pts = (a) => a.map((p) => p[0].toFixed(1) + ',' + p[1].toFixed(1)).join(' ');
    function el(tag, attrs, parent) { const e = doc.createElementNS(NS, tag); for (const k in attrs) e.setAttribute(k, attrs[k]); parent?.append(e); return e; }
    // Shapes (straight cuts).
    const disc = (r, n = 13) => Array.from({ length: n }, (_, i) => { const a = (i / n) * Math.PI * 2 + j(0.12); const rr = r + j(r * 0.05); return [Math.cos(a) * rr, Math.sin(a) * rr]; });
    function spike(len, wid) { return [[-wid / 2 + j(1), 1], [-wid * 0.22 + j(1.2), -len * 0.5 + j(1.5)], [j(1.5), -len + j(1)], [wid * 0.22 + j(1.2), -len * 0.5 + j(1.5)], [wid / 2 + j(1), 1]]; }
    function star(R, n = 5) { const a = []; for (let i = 0; i < n * 2; i++) { const r = i % 2 ? R * (0.42 + j(0.08)) : R + j(R * 0.1), t = (i / (n * 2)) * Math.PI * 2 - Math.PI / 2; a.push([Math.cos(t) * r, Math.sin(t) * r]); } return a; }
    function band(rx, ry, w, from, to) {   // half of a flattened ring: outer arc there, inner arc back
      const o = [], i = [], n = 9;
      for (let k = 0; k <= n; k++) { const t = from + (to - from) * (k / n); o.push([Math.cos(t) * (rx + j(1.2)), Math.sin(t) * (ry + j(0.8))]); i.unshift([Math.cos(t) * (rx - w + j(1)), Math.sin(t) * (ry - w * ry / rx + j(0.6))]); }
      return [...o, ...i];
    }
    // One cut piece: paper backing, the print clipped to the shape, a tint.
    // win: which part of the tile shows ('full', or a fixed sub-window).
    function piece(parent, defs, shape, tile, o = {}) {
      const id = 'cosp' + (++uid);
      const xs = shape.map((p) => p[0]), ys = shape.map((p) => p[1]);
      const bx = Math.min(...xs), by = Math.min(...ys), bw = Math.max(...xs) - bx, bh = Math.max(...ys) - by;
      el('polygon', { points: pts(shape) }, el('clipPath', { id }, defs));
      el('polygon', { points: pts(shape), fill: PAPER, stroke: PAPER, 'stroke-width': o.border ?? 3, 'stroke-linejoin': 'miter' }, parent);
      let w = o.win;
      if (!w) { const fw = tile.w * (0.5 + rnd() * 0.45), fh = Math.min(tile.h, fw * bh / Math.max(1, bw)); w = { x: tile.x + rnd() * (tile.w - fw), y: tile.y + rnd() * Math.max(0, tile.h - fh), w: fw, h: fh }; }
      if (w === 'full') w = tile;
      const clip = el('g', { 'clip-path': `url(#${id})` }, parent);
      const win = el('svg', { x: bx, y: by, width: bw, height: bh, viewBox: `${w.x.toFixed(1)} ${w.y.toFixed(1)} ${w.w.toFixed(1)} ${w.h.toFixed(1)}`, preserveAspectRatio: o.fit || 'xMidYMid slice', overflow: 'hidden' }, clip);
      el('image', { href: SHEET, width: SWID, height: SHGT }, win);
      if (o.tint) el('polygon', { points: pts(shape), fill: o.tint, opacity: o.alpha ?? 0.5, style: 'mix-blend-mode:multiply' }, parent);
      return clip;
    }
    const pin = (parent, x, y, r = 2.4) => { el('circle', { cx: x, cy: y, r, fill: PAPER }, parent); el('circle', { cx: x, cy: y, r: r * 0.55, fill: '#6B5A3A' }, parent); };

    // ── the objects: each builds into g (centred on 0,0) and returns its
    // half-size and an animate(t, moving) for its own moving parts.
    const MAKERS = {
      saturn(g, defs) {
        const rx = 70, ry = 21, rw = 15, R = 29;
        const ring = el('g', {}, g), back = el('g', {}, ring);
        piece(back, defs, band(rx, ry, rw, Math.PI, Math.PI * 2), T.ring, { win: 'full', fit: 'none' });
        const globe = el('g', {}, g);
        piece(globe, defs, disc(R, 15), T.globe, { win: 'full' });
        const front = el('g', {}, g);
        piece(front, defs, band(rx, ry, rw, 0, Math.PI), T.ring, { win: 'full', fit: 'none' });
        const base = -14 + j(10), ph = rnd() * 6;
        return { hw: rx + 4, hh: 34, animate(t, m) {
          const tilt = m ? base + snap(Math.sin(t * 0.004 + ph) * 9, 3) : base, sq = m ? snap(1 + Math.sin(t * 0.005 + ph) * 0.28, 0.07) : 1;
          const tr = `rotate(${tilt}) scale(1 ${sq})`;
          ring.setAttribute('transform', tr); front.setAttribute('transform', tr);
          globe.setAttribute('transform', `rotate(${m ? snap(Math.sin(t * 0.003 + ph) * 6, 2) : 0})`);
        } };
      },
      jupiter(g, defs) {
        const R = 40, body = el('g', {}, g);
        piece(body, defs, disc(R, 16), T.jupiter, { win: 'full' });
        const arm = el('g', {}, g), ph = rnd() * 6, dir = rnd() < 0.5 ? -1 : 1;
        el('line', { x1: 0, y1: 0, x2: R + 15, y2: 0, stroke: INK, 'stroke-width': 1, opacity: 0.6 }, arm);
        const moonlet = el('g', { transform: `translate(${R + 15} 0)` }, arm);
        piece(moonlet, defs, disc(7, 9), T.moon, { border: 2.4 });
        pin(g, 0, 0, 2.6);
        return { hw: R + 24, hh: R + 24, animate(t, m) {
          body.setAttribute('transform', `rotate(${m ? snap(Math.sin(t * 0.003 + ph) * 8, 2) : 0})`);
          arm.setAttribute('transform', `rotate(${m ? snap(dir * t * 0.22 + ph * 57, 12) : -30})`);
        } };
      },
      moon(g, defs) {
        const R = 32, copper = rnd() < 0.35, shape = disc(R, 15), cid = 'cosm' + (++uid);
        piece(g, defs, shape, copper ? T.eclipse : T.moon, copper ? { win: 'full' } : {});
        el('polygon', { points: pts(shape) }, el('clipPath', { id: cid }, defs));
        const shade = el('g', {}, el('g', { 'clip-path': `url(#${cid})` }, g));
        piece(shade, defs, disc(R + 2, 13), T.eclipse, { tint: '#2A2438', alpha: 0.5, border: 0 });
        const ph = rnd() * 6;
        return { hw: R + 3, hh: R + 3, animate(t, m) {
          // From a thin crescent (0.55R) to nearly full (2.3R), either side: never fully dark.
          const d = R * (1.42 + 0.88 * Math.sin(t * 0.0022 + ph)) * (Math.cos(t * 0.0011 + ph) < 0 ? -1 : 1);
          shade.setAttribute('transform', `translate(${m ? snap(d, R * 0.18).toFixed(1) : R * 1.1} 0)`);
        } };
      },
      sun(g, defs) {
        const R = 25, rays = el('g', {}, g), list = [], n = 12;
        for (let i = 0; i < n; i++) {
          const a = el('g', { transform: `rotate(${(i / n) * 360 + j(6)}) translate(0 ${-R + 4})` }, rays), flap = el('g', {}, a);
          piece(flap, defs, spike(18 + rnd() * 9, 11 + j(3)), i % 2 ? T.flare : T.flare2);
          list.push({ flap, ph: rnd() * 6 });
        }
        const face = el('g', {}, g);
        piece(face, defs, disc(R, 15), T.spots, { tint: '#F2B33D', alpha: 0.6 });
        pin(g, 0, 0);
        const ph = rnd() * 6;
        return { hw: R + 26, hh: R + 26, animate(t, m) {
          rays.setAttribute('transform', `rotate(${m ? snap(-t * 0.04 + ph * 57, 6) : 0})`);
          face.setAttribute('transform', `rotate(${m ? snap(t * 0.06, 8) : 0})`);
          for (const r of list) r.flap.setAttribute('transform', m ? `rotate(${snap(Math.sin(t * 0.012 + r.ph) * 9, 3)}) scale(1 ${snap(1 + Math.sin(t * 0.01 + r.ph * 2) * 0.2, 0.07)})` : '');
        } };
      },
      // Hung by the tip of its tail; the head dangles at the bottom.
      comet(g, defs) {
        const segs = [], n = 4, L = 30, top = -62;
        let parent = el('g', { transform: `translate(0 ${top})` }, g);
        for (let i = 0; i < n; i++) {
          const sg = el('g', {}, parent), w0 = 24 - i * 4.5, w1 = 24 - (i + 1) * 4.5;
          const win = { x: T.tail.x, y: T.tail.y + (T.tail.h * i) / n, w: T.tail.w, h: T.tail.h / n };
          piece(sg, defs, [[-w0 / 2 + j(1), -1], [w0 / 2 + j(1), -1], [w1 / 2 + j(1), L + 2], [-w1 / 2 + j(1), L + 2]], T.tail, { win, fit: 'none', tint: '#CFE3E8', alpha: 0.35 });
          if (i) pin(sg, 0, 0, 2);
          segs.push(sg); parent = el('g', { transform: `translate(0 ${L})` }, sg);
        }
        const head = el('g', {}, parent);
        for (let i = 0; i < 6; i++) piece(el('g', { transform: `rotate(${i * 60 + j(10)})` }, head), defs, spike(14 + rnd() * 6, 5), T.head, { border: 2, tint: '#F4EBD0', alpha: 0.4 });
        piece(head, defs, disc(8.5, 10), T.head, { win: 'full', tint: '#FFF6D8', alpha: 0.35 });
        const ph = rnd() * 6;
        return { hw: 30, hh: 70, hangAt: top, animate(t, m) {
          segs.forEach((sg, i) => sg.setAttribute('transform', `rotate(${m ? snap(Math.sin(t * 0.006 + ph - i * 0.8) * (5 + i * 3), 3) : 0})`));
          head.setAttribute('transform', `rotate(${m ? snap(t * 0.1, 15) : 0})`);
        } };
      },
      star(g, defs) {
        const R = 11 + rnd() * 6, body = el('g', {}, g);
        piece(body, defs, star(R, rnd() < 0.25 ? 4 : 5), rnd() < 0.5 ? T.spots2 : T.moon, { tint: rnd() < 0.7 ? '#F2B33D' : '#FFF1B8', alpha: 0.7, border: 2.6 });
        const ph = rnd() * 6;
        return { hw: R + 2, hh: R + 2, small: true, animate(t, m) {
          body.setAttribute('transform', m ? `rotate(${snap(Math.sin(t * 0.005 + ph) * 18, 6)}) scale(${snap(1 + Math.sin(t * 0.012 + ph) * 0.18, 0.06)})` : '');
        } };
      },
    };

    // ── the stage: build an object, hang it ──
    function build(kind) {
      const svg = el('svg', { 'aria-hidden': 'true', focusable: 'false', class: 'cos-obj cos-' + kind });
      const defs = el('defs', {}, svg), root = el('g', {}, svg), swing = el('g', {}, root);
      const thread = el('line', { x1: 0, y1: 0, x2: 0, y2: 0, stroke: INK, 'stroke-width': 1.1, opacity: 0.75 }, swing);
      const holder = el('g', {}, swing), body = el('g', {}, holder);
      const o = MAKERS[kind](body, defs);
      const anchorPin = el('g', {}, root); pin(anchorPin, 0, 0, 2.6);
      return { kind, svg, root, swing, thread, holder, anchorPin, ...o, ph: rnd() * 6, popAt: 0, seen: false };
    }

    const layer = doc.createElement('div');
    layer.className = 'cut-cosmos'; layer.setAttribute('aria-hidden', 'true');
    doc.body.append(layer);
    let placed = [];

    // ── placement ──
    // An occupancy grid of the page (10px cells): content is marked, with
    // a margin; a summed-area table answers "is this box clear?" at once.
    const G = 10, M = 14;
    function measure() {
      // Sections below the fold skip layout until they're near
      // (content-visibility: auto): lay them all out for the measurement.
      // The browser then remembers their real sizes.
      root.classList.add('cos-measure');
      try { return measureNow(); } finally { root.classList.remove('cos-measure'); }
    }
    function measureNow() {
      const W = doc.documentElement.clientWidth, H = doc.documentElement.scrollHeight;
      const cols = Math.ceil(W / G), rows = Math.ceil(H / G), occ = new Uint8Array(cols * rows), sy = scrollY;
      const mark = (x0, y0, x1, y1, m = M) => {
        const c0 = Math.max(0, Math.floor((x0 - m) / G)), c1 = Math.min(cols - 1, Math.floor((x1 + m) / G));
        const r0 = Math.max(0, Math.floor((y0 - m) / G)), r1 = Math.min(rows - 1, Math.floor((y1 + m) / G));
        for (let r = r0; r <= r1; r++) occ.fill(1, r * cols + c0, r * cols + c1 + 1);
      };
      const regions = [...$$('main > section:not(.hero-split)'), $('footer')].filter(Boolean);
      const hero = $('.hero-split');
      if (hero) { const r = hero.getBoundingClientRect(); mark(0, 0, W, r.bottom + sy, 0); }   // the hero (and above) is off limits
      const rg = doc.createRange();
      for (const reg of regions) {
        for (const e of reg.querySelectorAll('*')) {
          const r = e.getBoundingClientRect();
          if (r.width < 1 || r.height < 1) continue;
          const cs = getComputedStyle(e);
          // (Faded-out elements still count: they fade in as you scroll to them.)
          if (cs.visibility === 'hidden' || cs.display === 'none') continue;
          const box = /^(IMG|VIDEO|CANVAS|IFRAME|INPUT|BUTTON|TEXTAREA|SELECT|svg)$/.test(e.tagName)
            || (r.width < W * 0.92 && (!/rgba\(0, 0, 0, 0\)|transparent/.test(cs.backgroundColor) || cs.backgroundImage !== 'none' || parseFloat(cs.borderTopWidth) > 0 || cs.boxShadow !== 'none'));
          if (box) { mark(r.left, r.top + sy, r.right, r.bottom + sy); continue; }
          for (const n of e.childNodes) {
            if (n.nodeType !== 3 || !n.nodeValue.trim()) continue;
            rg.selectNodeContents(n);
            for (const q of rg.getClientRects()) if (q.width) mark(q.left, q.top + sy, q.right, q.bottom + sy);
          }
        }
      }
      mark(0, 0, 6, H, 0); mark(W - 6, 0, W, H, 0);   // keep off the very edges
      const sat = new Int32Array((cols + 1) * (rows + 1));
      for (let r = 0; r < rows; r++) { let run = 0; for (let c = 0; c < cols; c++) { run += occ[r * cols + c]; sat[(r + 1) * (cols + 1) + c + 1] = sat[r * (cols + 1) + c + 1] + run; } }
      const free = (x0, y0, x1, y1) => {
        const c0 = Math.floor(x0 / G), c1 = Math.ceil(x1 / G), r0 = Math.floor(y0 / G), r1 = Math.ceil(y1 / G);
        if (c0 < 0 || r0 < 0 || c1 > cols || r1 > rows) return false;
        return sat[r1 * (cols + 1) + c1] - sat[r0 * (cols + 1) + c1] - sat[r1 * (cols + 1) + c0] + sat[r0 * (cols + 1) + c0] === 0;
      };
      // Nearest thing above a point (a card's underside, a heading...).
      const ceiling = (x, y, max) => {
        const c = Math.floor(x / G);
        for (let r = Math.floor(y / G) - 1, k = 0; r >= 0 && k * G < max; r--, k++) if (occ[r * cols + c]) return (r + 1) * G - M + 2;
        return null;
      };
      return { W, H, free, ceiling, regions: regions.map((e) => { const r = e.getBoundingClientRect(); return { top: r.top + sy, bottom: r.bottom + sy }; }) };
    }

    function layout() {
      seed = 11; uid = 0;
      for (const o of placed) o.svg.remove();
      placed = [];
      const map = measure(), s = Math.max(0.62, Math.min(1.05, innerWidth / 1300)), phone = innerWidth < 700;
      const BIG = ['saturn', 'moon', 'jupiter', 'sun', 'comet', 'moon', 'saturn', 'sun'];
      let next = 0;
      // Too near another object, or its thread (threads shouldn't bunch up).
      const tooClose = (x, y, top, d) => placed.some((o) => Math.hypot(o.cx - x, o.cy - y) < d
        || (o.hung && Math.abs(o.ax - x) < 70 * s && top < o.cy && y > o.ay));
      function place(kind, reg) {
        const o = build(kind), hw = o.hw * s, hh = o.hh * s, hang = (o.hangAt ?? -o.hh) * s;
        let best = null;
        for (let y = reg.top + 8; y + 2 * hh < reg.bottom - 4; y += 20) {
          for (let x = hw + 10; x < map.W - hw - 10; x += 20) {
            const top = y, cy = y + hh;
            const anchor = map.ceiling(x, top + (hang + hh), 280);
            const L = anchor == null ? 0 : (cy + hang) - anchor;
            if (anchor != null && L < 12) continue;
            const sw = Math.min(40, (L + hh) * 0.16) + 4;
            if (!map.free(x - hw - sw, top - 4, x + hw + sw, top + 2 * hh + 4)) continue;
            if (tooClose(x, cy, anchor ?? top, (o.small ? 170 : 300) * s)) continue;
            let score = rnd() * 6;
            for (const m of [24, 48, 80]) if (map.free(x - hw - sw - m, top - m, x + hw + sw + m, top + 2 * hh + m)) score += 10;
            if (anchor != null) score += L > 30 && L < 170 ? 14 : L < 240 ? 6 : 0;
            if (!best || score > best.score) best = { x, cy, anchor, L, score };
          }
        }
        if (!best) return false;
        Object.assign(o, { cx: best.x, cy: best.cy, L: best.L, hung: best.anchor != null, s, ax: best.x, ay: best.anchor ?? best.cy });
        o.thread.style.display = o.hung ? '' : 'none'; o.anchorPin.style.display = o.hung ? '' : 'none';
        const ay = o.hung ? best.anchor : best.cy + hang;
        o.thread.setAttribute('y2', o.L.toFixed(1));
        o.holder.setAttribute('transform', `translate(0 ${(o.L - hang).toFixed(1)}) scale(${s})`);
        o.svg.setAttribute('width', 2); o.svg.setAttribute('height', 2);
        o.svg.style.left = best.x + 'px'; o.svg.style.top = ay + 'px';
        o.root.setAttribute('transform', 'translate(1 1)');
        layer.append(o.svg); placed.push(o);
        return true;
      }
      for (const reg of map.regions) {
        let bigs = 0;
        for (let tries = 0; tries < BIG.length && bigs < (phone ? 1 : 2); tries++) if (place(BIG[next++ % BIG.length], reg)) bigs++;
        for (let k = 0; k < (phone ? 1 : 2); k++) place('star', reg);
      }
      layer.style.height = map.H + 'px';
      draw();
    }

    // ── the show: 12 updates a second while there's motion ──
    let raf = 0, lastT = 0, settleUntil = 0, shake = 0;
    function draw() {
      const vh = innerHeight, sy = scrollY, moving = fxOn(), now = performance.now();
      shake = Math.min(14, shake * 0.7 + Math.abs(scrollVel) * 4);
      for (const o of placed) {
        const vy = o.cy - sy;
        if (vy < -400 || vy > vh + 400) continue;
        if (!o.seen && vy < vh * 0.9) { o.seen = true; if (moving) { o.popAt = now; settleUntil = Math.max(settleUntil, now + 600); } }
        // Lowered in on its thread the first time it's seen (three jerks).
        const drop = o.popAt && now - o.popAt < 450 ? (1 - Math.ceil(((now - o.popAt) / 450) * 3) / 3) * -(o.L + o.hh * o.s + 30) : 0;
        const sw = moving ? snap(Math.sin(sy * 0.0035 + o.ph) * (o.hung ? 6 : 3) + Math.sin(now * 0.02 + o.ph) * shake * 0.5, 2) : 0;
        o.swing.setAttribute('transform', `rotate(${sw})`);
        o.holder.setAttribute('transform', `translate(0 ${(o.L - (o.hangAt ?? -o.hh) * o.s + drop).toFixed(1)}) scale(${o.s})`);
        if (o.hung) o.thread.setAttribute('y2', Math.max(0, o.L + drop).toFixed(1));
        o.animate(sy, moving);
      }
    }
    function loop(t) {
      raf = 0;
      if (t - lastT >= 1000 / 12 - 4) { lastT = t; draw(); }
      if (performance.now() < settleUntil || shake > 0.5) raf = requestAnimationFrame(loop);
    }
    const kick = () => { settleUntil = Math.max(settleUntil, performance.now() + 400); if (!raf) raf = requestAnimationFrame(loop); };
    addEventListener('scroll', kick, { passive: true });
    let lt = 0, lastW = 0, lastH = 0;
    const relayout = () => { clearTimeout(lt); lt = setTimeout(() => {
      const w = doc.documentElement.clientWidth, h = doc.documentElement.scrollHeight;
      if (w === lastW && Math.abs(h - lastH) < 4) return;   // nothing moved
      lastW = w; lastH = h; layout(); kick();
    }, 200); };
    new ResizeObserver(relayout).observe(doc.body);
    addEventListener('resize', relayout, { passive: true });
    (doc.fonts?.ready || Promise.resolve()).then(() => setTimeout(relayout, 300));
    return { redraw: draw };
  })();

  // ── 8-BIT MODE (easter egg): five quick taps on the home logo ────
  // The page turns into an NES game: everything (its own fonts and colours
  // included) rendered at low resolution, photos redrawn as tiny
  // palette-limited pixel art, square corners, stepped motion, square-wave
  // blips, and the music run through a bit-crusher.
  // Five more taps (or the search palette entry) switch it back.
  const nes = (() => {
    // The NES's master palette (the 54 distinct colours).
    const PAL = ['7c7c7c', '0000fc', '0000bc', '4428bc', '940084', 'a80020', 'a81000', '881400', '503000', '007800', '006800', '005800', '004058', '000000',
      'bcbcbc', '0078f8', '0058f8', '6844fc', 'd800cc', 'e40058', 'f83800', 'e45c10', 'ac7c00', '00b800', '00a800', '00a844', '008888',
      'f8f8f8', '3cbcfc', '6888fc', '9878f8', 'f878f8', 'f85898', 'f87858', 'fca044', 'f8b800', 'b8f818', '58d854', '58f898', '00e8d8', '787878',
      'fcfcfc', 'a4e4fc', 'b8b8f8', 'd8b8f8', 'f8b8f8', 'f8a4c0', 'f0d0b0', 'fce0a8', 'f8d878', 'd8f878', 'b8f8b8', 'b8f8d8', '00fcfc', 'd8d8d8']
      .map((h) => [parseInt(h.slice(0, 2), 16), parseInt(h.slice(2, 4), 16), parseInt(h.slice(4, 6), 16)]);
    const BAYER = [0, 8, 2, 10, 12, 4, 14, 6, 3, 11, 1, 9, 15, 7, 13, 5];
    let on = false, taps = [], actx = null, crushNode = null, worklet = null, imgObs = null, textObs = null, textT = 0;
    const routed = new Map();   // media element -> its MediaElementSource

    // ── pixel art: downscale, ordered-dither, snap to the palette ──
    // Sprites (logo, streaming icons) get hard on/off transparency too.
    function toPixels(src, sw, sh, LONG) {
      const k = LONG / Math.max(sw, sh);
      const w = Math.max(8, Math.round(sw * k)), h = Math.max(8, Math.round(sh * k));
      const c = doc.createElement('canvas'); c.width = w; c.height = h;
      const x = c.getContext('2d', { willReadFrequently: true });
      x.imageSmoothingQuality = 'high';
      x.drawImage(src, 0, 0, w, h);
      const d = x.getImageData(0, 0, w, h), px = d.data;
      for (let i = 0; i < px.length; i += 4) {
        const p = i / 4, t = (BAYER[((p / w | 0) % 4) * 4 + (p % w) % 4] / 16 - 0.5) * 28;
        const r = px[i] + t, g = px[i + 1] + t, b = px[i + 2] + t;
        let best = 0, bd = Infinity;
        for (let j = 0; j < PAL.length; j++) { const q = PAL[j], dd = (r - q[0]) ** 2 * 0.3 + (g - q[1]) ** 2 * 0.59 + (b - q[2]) ** 2 * 0.11; if (dd < bd) { bd = dd; best = j; } }
        px[i] = PAL[best][0]; px[i + 1] = PAL[best][1]; px[i + 2] = PAL[best][2];
        px[i + 3] = px[i + 3] > 110 ? 255 : 0;
      }
      x.putImageData(d, 0, 0);
      return c;
    }
    const SPRITE = 16;   // the logo: a 16×16 sprite
    function pixelate(img) {
      if (!img.complete || !img.naturalWidth || img.dataset.nesOut === img.currentSrc) return;
      if (img.closest('.k-palette')) return;
      const LONG = img.matches('.hero-icon, .footer-logo img') ? SPRITE
        : img.classList.contains('hero-split-photo') ? 160 : 96;   // pixel art, but still recognisable
      try {
        const c = toPixels(img, img.naturalWidth, img.naturalHeight, LONG);
        // Blow the pixel art back up to the photo's own dimensions (hard
        // square pixels, no smoothing): layouts that size an image from
        // its natural pixels (like the press kit photo columns) would
        // otherwise shrink to the tiny copy.
        // Sprites scale by a whole number so every pixel is the same size.
        const up = doc.createElement('canvas');
        if (LONG === SPRITE) { const n = Math.ceil(Math.max(img.naturalWidth, img.naturalHeight) / Math.max(c.width, c.height)); up.width = c.width * n; up.height = c.height * n; }
        else { const k2 = Math.min(1, 1600 / Math.max(img.naturalWidth, img.naturalHeight)); up.width = Math.round(img.naturalWidth * k2); up.height = Math.round(img.naturalHeight * k2); }
        const ux = up.getContext('2d'); ux.imageSmoothingEnabled = false;
        ux.drawImage(c, 0, 0, up.width, up.height);
        const out = up.toDataURL('image/png');
        if (!img.dataset.nesOrig) { img.dataset.nesOrig = img.getAttribute('src') || ''; if (img.srcset) { img.dataset.nesSrcset = img.srcset; img.removeAttribute('srcset'); } }
        img.dataset.nesOut = out;
        img.src = out;
        img.classList.add('nes-px');
      } catch { /* a cross-origin image can't be read back; leave it */ }
    }
    // Streaming icons are CSS backgrounds (.pt--apple etc.), not <img>s:
    // redraw each as a 16×16 sprite and swap it in with one style sheet.
    let ptCss = '';
    async function pixelIcons() {
      if (!ptCss) {
        const rules = [];
        for (const name of ['apple', 'spotify', 'youtube']) {
          const probe = doc.createElement('span'); probe.className = 'pt pt--' + name; probe.hidden = true;
          doc.body.append(probe);
          const url = (getComputedStyle(probe).backgroundImage.match(/url\(["']?(.*?)["']?\)/) || [])[1];
          probe.remove();
          if (!url) continue;
          try {
            const im = new Image(); im.src = url; await im.decode();
            rules.push(`html.nes .pt--${name}{background-image:url(${toPixels(im, im.naturalWidth, im.naturalHeight, 16).toDataURL('image/png')})!important}`);
          } catch { /* leave the normal icon */ }
        }
        ptCss = rules.join('') + 'html.nes .pt{image-rendering:pixelated}';
      }
      if (on && !$('#nes-pt')) { const st = doc.createElement('style'); st.id = 'nes-pt'; st.textContent = ptCss; doc.head.append(st); }
    }
    function pixelateAll() {
      pixelIcons();
      for (const img of $$('img')) {
        if (img.complete) pixelate(img); else img.addEventListener('load', () => on && pixelate(img), { once: true });
      }
    }
    function restoreAll() {
      for (const img of $$('img[data-nes-orig]')) {
        img.src = img.dataset.nesOrig;
        if (img.dataset.nesSrcset) img.srcset = img.dataset.nesSrcset;
        delete img.dataset.nesOrig; delete img.dataset.nesOut; delete img.dataset.nesSrcset;
        img.classList.remove('nes-px');
      }
    }

    // ── one NES frame rate (12 fps) for everything that moves ──
    // Scripted animation (confetti, the field, the players, the video
    // canvases) all runs off requestAnimationFrame: in 8-bit mode its
    // callbacks are held and released together 12 times a second. CSS
    // animations and transitions are paused and stepped forward by hand on
    // the same beat, then finished normally so their end events still fire.
    const FPS = 12, STEP = 1000 / FPS;
    const nativeRaf = window.requestAnimationFrame.bind(window), nativeCaf = window.cancelAnimationFrame.bind(window);
    const held = new Map(), stepped = new Set();
    let heldId = 1e9, beat = 0, lastBeat = 0;
    window.requestAnimationFrame = (cb) => { if (!on) return nativeRaf(cb); const id = ++heldId; held.set(id, cb); if (!beat) beat = nativeRaf(tick); return id; };
    window.cancelAnimationFrame = (id) => { if (!held.delete(id)) nativeCaf(id); };
    function tick(t) {
      beat = 0;
      if (!on) return;
      if (t - lastBeat < STEP - 4) { beat = nativeRaf(tick); return; }
      const dt = lastBeat ? Math.min(t - lastBeat, 250) : STEP;
      lastBeat = t;
      // CSS animations and transitions: catch new ones, step the rest.
      // (Scroll-driven animations follow the scroll, not the clock: left alone.)
      if (doc.getAnimations) for (const a of doc.getAnimations()) if (a.playState === 'running' && a.timeline === doc.timeline && typeof a.currentTime === 'number') { a.pause(); stepped.add(a); }
      for (const a of stepped) {
        try {
          if (a.playState === 'idle' || a.playState === 'finished' || typeof a.currentTime !== 'number') { stepped.delete(a); continue; }
          const now = a.currentTime + dt * a.playbackRate, end = a.effect?.getComputedTiming().endTime;
          if (typeof end === 'number' && now >= end) { stepped.delete(a); a.finish(); } else a.currentTime = now;
        } catch { stepped.delete(a); }
      }
      const cbs = [...held.values()]; held.clear();
      for (const cb of cbs) { try { cb(t); } catch (e) { console.error(e); } }
      beat = nativeRaf(tick);   // keep beating while CSS animations are being stepped or callbacks wait
    }
    function frameOn() { lastBeat = 0; if (!beat) beat = nativeRaf(tick); }
    function frameOff() {
      nativeCaf(beat); beat = 0;
      for (const a of stepped) { try { a.play(); } catch { /* gone */ } }
      stepped.clear();
      const cbs = [...held.values()]; held.clear();
      for (const cb of cbs) nativeRaf(cb);   // hand waiting callbacks back to the normal frame rate
    }

    // ── videos as pixel art ──
    // A canvas laid over each video redraws every frame at 128 pixels
    // across, dithered and snapped to the NES palette, and shown with
    // square pixels. It ignores the pointer, and lifts off the bottom strip
    // (the player's controls) while the video is paused or being pointed at.
    // (Full screen shows the video itself: the canvas can't follow it there.)
    const VW = 128;
    const palCache = new Int16Array(32768).fill(-1);   // 5-bit RGB -> palette index
    function nearest(r, g, b) {
      const key = ((r < 0 ? 0 : r > 255 ? 255 : r) >> 3) << 10 | ((g < 0 ? 0 : g > 255 ? 255 : g) >> 3) << 5 | ((b < 0 ? 0 : b > 255 ? 255 : b) >> 3);
      let best = palCache[key];
      if (best < 0) {
        let bd = Infinity;
        for (let j = 0; j < PAL.length; j++) { const q = PAL[j], dd = (r - q[0]) ** 2 * 0.3 + (g - q[1]) ** 2 * 0.59 + (b - q[2]) ** 2 * 0.11; if (dd < bd) { bd = dd; best = j; } }
        palCache[key] = best;
      }
      return PAL[best];
    }
    const vids = new Map();   // video -> { cv, x, last, poke }
    let vidRaf = 0;
    function vidAttach(v) {
      if (vids.has(v)) return;
      const cv = doc.createElement('canvas');
      cv.className = 'nes-vid'; cv.setAttribute('aria-hidden', 'true');
      v.after(cv);
      const st = { cv, x: cv.getContext('2d', { willReadFrequently: true }), last: -1, poke: 0, key: '' };
      const host = v.parentElement;
      st.move = () => { st.poke = performance.now(); };
      host.addEventListener('pointermove', st.move, { passive: true });
      host.addEventListener('pointerdown', st.move, { passive: true });
      st.host = host;
      vids.set(v, st);
    }
    function vidFrame() {
      if (!on) return;
      vidRaf = requestAnimationFrame(vidFrame);
      for (const v of $$('video')) vidAttach(v);
      for (const [v, st] of vids) {
        if (!v.isConnected) { st.cv.remove(); vids.delete(v); continue; }
        const cv = st.cv;
        const vw = v.videoWidth, vh = v.videoHeight;
        if (v.readyState < 2 || !vw || !v.offsetWidth || doc.fullscreenElement === v) { cv.style.display = 'none'; continue; }
        // The picture's own box inside the element (object-fit: contain letterboxing).
        const ew = v.offsetWidth, eh = v.offsetHeight, k = (getComputedStyle(v).objectFit === 'cover' ? Math.max : Math.min)(ew / vw, eh / vh);
        const pw = vw * k, ph = vh * k, pl = v.offsetLeft + (ew - pw) / 2, pt = v.offsetTop + (eh - ph) / 2;
        const key = `${pl}|${pt}|${pw}|${ph}`;
        if (key !== st.key) {
          st.key = key;
          Object.assign(cv.style, { position: 'absolute', left: pl + 'px', top: pt + 'px', width: pw + 'px', height: ph + 'px', pointerEvents: 'none', imageRendering: 'pixelated', zIndex: '1' });
        }
        cv.style.display = '';
        // Controls: show the real video along the bottom strip when they're up.
        const ctl = v.controls && (v.paused || performance.now() - st.poke < 2500);
        const strip = Math.max(0, (eh - 56) - (pt - v.offsetTop));   // controls sit in the element's bottom 56px
        cv.style.clipPath = ctl ? `inset(0 0 ${Math.max(0, ph - strip)}px 0)` : '';
        if (v.currentTime === st.last && cv.width) continue;
        st.last = v.currentTime;
        const w = VW, h = Math.max(8, Math.round(VW * vh / vw));
        if (cv.width !== w || cv.height !== h) { cv.width = w; cv.height = h; }
        const x = st.x;
        try {
          x.imageSmoothingQuality = 'high';
          x.drawImage(v, 0, 0, w, h);
          const d = x.getImageData(0, 0, w, h), px = d.data;
          for (let i = 0; i < px.length; i += 4) {
            const p = i / 4, t = (BAYER[((p / w | 0) % 4) * 4 + (p % w) % 4] / 16 - 0.5) * 28;
            const q = nearest(px[i] + t, px[i + 1] + t, px[i + 2] + t);
            px[i] = q[0]; px[i + 1] = q[1]; px[i + 2] = q[2];
          }
          x.putImageData(d, 0, 0);
        } catch { cv.style.display = 'none'; }   // a cross-origin video can't be read back
      }
    }
    function vidOn() { cancelAnimationFrame(vidRaf); vidFrame(); }
    function vidOff() {
      cancelAnimationFrame(vidRaf);
      for (const [, st] of vids) { st.cv.remove(); st.host.removeEventListener('pointermove', st.move); st.host.removeEventListener('pointerdown', st.move); }
      vids.clear();
    }

    // ── the name as pixel art ──
    // A mosaic filter on big text drops tiles on the GPU (parts of the
    // name vanished), so the name is redrawn instead: painted at full size
    // into a canvas, shrunk to one pixel per ~6 screen pixels with hard
    // (thresholded) edges, then shown scaled up with square pixels in place
    // of the live text. The text itself stays in the page, invisible, for
    // screen readers, search and copying.
    let nameObs = null, nameRaf = 0;
    // Draws every line of an element's own text (not its child elements',
    // which are redrawn separately), word by word at the positions the
    // browser laid them out, so multi-line text like the quote works too.
    function pixelName(el) {
      const tns = [...el.childNodes].filter((n) => n.nodeType === 3 && n.nodeValue.trim());
      if (!tns.length) return;
      const box = el.getBoundingClientRect();
      if (box.width < 4 || box.height < 4) return;
      const cs = getComputedStyle(el), fs = parseFloat(cs.fontSize);
      // Block size in screen pixels: chunky, NES-title sized (the name a touch finer than the quote).
      const B = Math.max(2, Math.round(fs / (el.classList.contains('hero-name') ? 14 : 11)));
      const W = Math.ceil(box.width), H = Math.ceil(box.height);
      const big = doc.createElement('canvas'); big.width = W; big.height = H;
      const g = big.getContext('2d');
      g.font = `${cs.fontStyle} ${cs.fontWeight} ${fs}px ${cs.fontFamily}`;
      if ('letterSpacing' in g) g.letterSpacing = cs.letterSpacing === 'normal' ? '0px' : cs.letterSpacing;
      g.fillStyle = cs.color; g.textBaseline = 'alphabetic';
      const m = g.measureText('Hg'), asc = m.fontBoundingBoxAscent ?? fs * 0.8, desc = m.fontBoundingBoxDescent ?? fs * 0.2;
      const tt = (t) => cs.textTransform === 'uppercase' ? t.toUpperCase() : cs.textTransform === 'lowercase' ? t.toLowerCase() : t;
      const rg = doc.createRange();
      for (const tn of tns) {
        for (const w of tn.nodeValue.matchAll(/\S+/g)) {
          rg.setStart(tn, w.index); rg.setEnd(tn, w.index + w[0].length);
          const r = rg.getBoundingClientRect();
          if (!r.width) continue;
          g.fillText(tt(w[0]), r.left - box.left, r.top - box.top + (r.height - asc - desc) / 2 + asc);
        }
      }
      const w = Math.ceil(W / B), h = Math.ceil(H / B);
      const sm = doc.createElement('canvas'); sm.width = w; sm.height = h;
      const x = sm.getContext('2d', { willReadFrequently: true });
      x.imageSmoothingQuality = 'high';
      x.drawImage(big, 0, 0, w, h);
      const d = x.getImageData(0, 0, w, h), px = d.data;
      let top = 0; for (let i = 3; i < px.length; i += 4) if (px[i] > top) top = px[i];   // the text colour's own opacity
      for (let i = 3; i < px.length; i += 4) px[i] = px[i] > top * 0.4 ? top : 0;   // hard edges, no anti-aliasing
      x.putImageData(d, 0, 0);
      return () => {
        el.style.setProperty('--nes-name', `url(${sm.toDataURL('image/png')})`);
        el.style.setProperty('--nes-name-size', `${w * B}px ${h * B}px`);
        el.classList.add('nes-name');
      };
    }
    const names = () => $$('.hero-name, .disc-quote, .disc-quote cite');
    function nameOn() {
      // Measure everything with the live text showing (a child like the
      // quote's credit would otherwise inherit the hidden colour), then swap.
      const all = () => { const els = names(); els.forEach((el) => el.classList.remove('nes-name')); els.map(pixelName).forEach((f) => f?.()); };
      const run = () => { cancelAnimationFrame(nameRaf); nameRaf = requestAnimationFrame(() => on && all()); };
      (doc.fonts?.ready || Promise.resolve()).then(() => {
        if (!on) return;
        run();
        // Re-draw when a name changes size (window resize) or first
        // appears (the nav logo is hidden until you scroll).
        nameObs = new ResizeObserver(run);
        names().forEach((el) => nameObs.observe(el));
      });
    }
    function nameOff() {
      nameObs?.disconnect(); nameObs = null; cancelAnimationFrame(nameRaf);
      for (const el of names()) { el.classList.toggle('nes-name', false); el.style.removeProperty('--nes-name'); el.style.removeProperty('--nes-name-size'); }
    }

    // ── sound: square-wave blips and an NES-style bit-crusher ──
    function ctx() {
      if (!actx) { try { actx = new AudioContext(); } catch { return null; } }
      if (actx.state === 'suspended') actx.resume().catch(() => {});
      return actx;
    }
    function tone(seq, type = 'square', vol = 0.06) {   // seq: [[freq, ms], ...]
      const a = ctx(); if (!a) return;
      let t = a.currentTime + 0.01;
      for (const [f, ms] of seq) {
        const o = a.createOscillator(), g = a.createGain();
        o.type = type; o.frequency.value = f;
        g.gain.setValueAtTime(vol, t); g.gain.setValueAtTime(0, t + ms / 1000 - 0.005);
        o.connect(g).connect(a.destination); o.start(t); o.stop(t + ms / 1000);
        t += ms / 1000;
      }
    }
    const WORKLET = `class NesCrush extends AudioWorkletProcessor {
      constructor() { super(); this.ph = 0; this.last = []; }
      process(ins, outs) {
        const inp = ins[0], out = outs[0];
        if (!inp || !inp.length) return true;
        const HOLD = 4, STEP = 32;   // ~11 kHz sample rate, 6-bit samples
        let ph = this.ph;
        for (let c = 0; c < out.length; c++) {
          const x = inp[c] || inp[0], y = out[c];
          let l = this.last[c] || 0; ph = this.ph;
          for (let n = 0; n < y.length; n++) { if (ph++ % HOLD === 0) l = Math.round(x[n] * STEP) / STEP; y[n] = l; }
          this.last[c] = l;
        }
        this.ph = ph % HOLD;
        return true;
      }
    }
    registerProcessor('nes-crush', NesCrush);`;
    async function crusher() {
      const a = ctx(); if (!a) return null;
      if (crushNode) return crushNode;
      const hp = a.createBiquadFilter(); hp.type = 'highpass'; hp.frequency.value = 90;
      let crush;
      try {
        if (!worklet) { const url = URL.createObjectURL(new Blob([WORKLET], { type: 'text/javascript' })); worklet = a.audioWorklet.addModule(url); }
        await worklet;
        crush = new AudioWorkletNode(a, 'nes-crush', { outputChannelCount: [2] });
      } catch {
        crush = a.createWaveShaper();   // fallback: bit depth only
        const curve = new Float32Array(4096);
        for (let i = 0; i < curve.length; i++) { const v = i / 2047.5 - 1; curve[i] = Math.round(v * 32) / 32; }
        crush.curve = curve;
      }
      hp.connect(crush).connect(a.destination);
      crushNode = hp;
      return crushNode;
    }
    // Routing a media element through Web Audio is one-way (it can never be
    // un-routed), so it only happens once someone turns 8-bit mode on; when
    // it's switched off the element goes straight to the speakers again.
    async function route(el) {
      const a = ctx(); if (!a || !el) return;
      let src = routed.get(el);
      if (!src) { try { src = a.createMediaElementSource(el); routed.set(el, src); } catch { return; } }
      src.disconnect();
      if (on) src.connect(await crusher()); else src.connect(a.destination);
    }
    const routeAll = () => { route($('#np-audio')); for (const v of $$('video')) if (!v.paused || routed.has(v)) route(v); };
    doc.addEventListener('play', (e) => { if (on && e.target instanceof HTMLMediaElement) route(e.target); }, true);
    doc.addEventListener('pointerdown', (e) => {
      if (!on) return;
      const b = e.target.closest?.('button, a, [role="button"], input[type="range"]');
      if (!b) return;
      if (b.matches('#featured-play, #np-play, .fs-play, .rel-play-circle, .rel-art-wrap')) tone([[988, 70], [1319, 260]]);   // coin
      else tone([[1760, 35]], 'square', 0.04);   // menu blip
    }, { passive: true, capture: true });

    // Every element with its own text gets hard pixel edges at full
    // resolution, so it all stays readable.
    function tagText() {
      for (const el of $$('body *:not(script):not(style):not(svg *)')) {
        if (el.dataset.nesText || el.closest('#nes-svg')) continue;
        const hasText = [...el.childNodes].some((n) => n.nodeType === 3 && n.nodeValue.trim());
        if (!hasText) continue;
        el.dataset.nesText = parseFloat(getComputedStyle(el).fontSize) >= 22 ? 'big' : 'small';
      }
    }
    async function set(next) {
      on = next;
      if (on) {
        if (!$('#nes-svg')) {
          // nes-crisp: hard pixel edges at full resolution (text and icons
          // stay readable and render reliably on the GPU). nes-poster:
          // a limited retro colour range for whole regions.
          const box = doc.createElement('div');
          box.innerHTML = '<svg id="nes-svg" aria-hidden="true" focusable="false" width="0" height="0" style="position:absolute;width:0;height:0">'
            + '<filter id="nes-crisp" color-interpolation-filters="sRGB"><feComponentTransfer><feFuncA type="discrete" tableValues="0 1 1 1 1 1 1 1"/></feComponentTransfer></filter>'
            + '<filter id="nes-poster" color-interpolation-filters="sRGB"><feComponentTransfer>'
            + '<feFuncR type="discrete" tableValues="0 .125 .25 .375 .5 .625 .75 .875 1"/><feFuncG type="discrete" tableValues="0 .125 .25 .375 .5 .625 .75 .875 1"/><feFuncB type="discrete" tableValues="0 .125 .25 .375 .5 .625 .75 .875 1"/>'
            + '</feComponentTransfer></filter></svg>';
          doc.body.append(box.firstChild);
        }
        root.classList.add('nes');
        tagText();
        textObs = new MutationObserver(() => { clearTimeout(textT); textT = setTimeout(() => on && tagText(), 150); });
        textObs.observe(doc.body, { subtree: true, childList: true });
        pixelateAll();
        nameOn();
        vidOn();
        frameOn();
        imgObs = new MutationObserver((ms) => { for (const m of ms) if (m.target.tagName === 'IMG' && m.target.src !== m.target.dataset.nesOut) { delete m.target.dataset.nesOrig; m.target.complete ? pixelate(m.target) : m.target.addEventListener('load', () => on && pixelate(m.target), { once: true }); } });
        imgObs.observe(doc.body, { subtree: true, attributes: true, attributeFilter: ['src'] });
        tone([[523, 70], [659, 70], [784, 70], [1047, 70], [784, 70], [1047, 220]]);   // power-on jingle
        announce('8-bit mode on. Tap the logo five times to switch back.');
      } else {
        imgObs?.disconnect(); imgObs = null;
        textObs?.disconnect(); textObs = null; clearTimeout(textT);
        root.classList.remove('nes');
        for (const el of $$('[data-nes-text]')) delete el.dataset.nesText;
        restoreAll();
        nameOff();
        frameOff();
        vidOff();
        tone([[784, 70], [523, 70], [392, 70], [262, 200]]);
        announce('8-bit mode off.');
      }
      routeAll();
      field.redraw();
    }
    const brand = $('#hero-brand');
    brand?.addEventListener('click', () => {
      const now = performance.now();
      if (taps.length && now - taps[taps.length - 1] > 1000) taps = [];   // five in a row, each within a second
      taps.push(now);
      if (taps.length >= 5) { taps = []; set(!on); }
    });
    return { get on() { return on; }, toggle: () => set(!on) };
  })();

  // Palette settings (kinetic.js picks these up).
  window.kineticItems = () => [
    { group: 'Settings', title: fxPref ? 'Turn background effects off' : 'Turn background effects on', sub: 'Liquid background and click ripples', run: () => { fxPref = !fxPref; store.set('psy-fx', fxPref ? 'on' : 'off'); syncFx(); announce(`Background effects ${fxPref ? 'on' : 'off'}`); } },
    { group: 'Settings', title: nes.on ? 'Turn 8-bit mode off' : 'Turn 8-bit mode on', sub: 'NES look and sound (or tap the logo five times)', run: () => nes.toggle() },
  ];

  syncFx();
  }
})();
