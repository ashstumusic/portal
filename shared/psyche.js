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
  function syncFx() { root.classList.toggle('psy-calm', !fxOn()); field.redraw(); stars.redraw(); }
  reduce.addEventListener?.('change', () => syncFx());

  root.classList.add('psy');
  // the saved choice applies from the first frame, not only after a toggle
  root.classList.toggle('psy-calm', !fxOn());

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
    const soft = 'filter' in ctx, src = soft ? doc.createElement('canvas') : null, sctx = soft ? src.getContext('2d') : null;
    if (!soft) cv.classList.add('psy-field--cssblur');   // a browser whose canvas cannot blur keeps the CSS blur
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
      if (soft) { src.width = w; src.height = h; }
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
      // The haze is softened here, on the tiny picture (a 2-dot blur of ~72x45 dots costs nothing), not by a CSS blur
      // of the whole screen, which the browser had to recompute on every repaint. Drawn slightly oversize so the blur
      // has picture, not empty edge, to pull from.
      if (soft) { sctx.putImageData(img, 0, 0); ctx.filter = 'blur(2px) saturate(.9)'; ctx.drawImage(src, -2, -2, w + 4, h + 4); }
      else ctx.putImageData(img, 0, 0);
    }
    function frame(now) {
      raf = 0;
      if (doc.hidden || !fxOn()) return;   // effects off: the haze holds still
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
    return;   // ripple on presses switched off (Nov 2026)
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

  // ── STARS: hand-drawn in white chalk, boiling like stop motion ──
  // Six basic hollow stars drawn in chalk, each drawn three times with fresh
  // hand wobble and grain (Images/chalk-stars.webp, made by
  // scripts/make_chalk_stars.py: rows are designs, columns the three
  // frames). Cycling the frames makes the lines "boil" the way hand-drawn
  // stop motion does. They're scattered over the space-black page.
  //
  // Placement: the page is measured on every layout (text, cards, photos,
  // buttons become no-go areas). Each star tries a few hundred spots and
  // takes the one with the most room, furthest from the others, so the
  // sky fills evenly. Redone when the layout changes.
  //
  // Animation is shot "on threes" (8 frames a second), no smooth tweens:
  // the stars on screen boil and jitter a pixel or so every frame; while
  // you scroll they also turn in hard clicks and swell in steps; a fast
  // scroll knocks them about. Every star is there from the start (no
  // pop-in), and stars added later are only ever placed off screen. Still under reduced motion or with effects off.
  const stars = (() => {
    const FRAMES = 3, DESIGNS = 6;   // six hand-drawn hollow stars
    // Each star is chalked in a faint version of one of these colours
    // (#FBB669 #F88FA8 #F37C78 #E7AD8B #E1D0C4 #A9CBC4 #6B2222, each 40% of the way to white).
    const COLORS = ['#FDD3A5', '#FBBCCB', '#F8B0AE', '#F1CEB9', '#EDE3DC', '#CBE0DC', '#A67A7A'];
    let seed = 11;   // fixed seed: the same sky on every visit
    const rnd = () => { seed = (seed + 0x6D2B79F5) | 0; let t = Math.imul(seed ^ (seed >>> 15), 1 | seed); t = (t + Math.imul(t ^ (t >>> 7), 61 | t)) ^ t; return ((t ^ (t >>> 14)) >>> 0) / 4294967296; };
    const snap = (v, s) => Math.round(v / s) * s;
    const layer = doc.createElement('div');
    layer.className = 'cut-stars'; layer.setAttribute('aria-hidden', 'true');
    doc.body.append(layer);
    let placed = [];

    // ── measuring the page ──
    // An occupancy grid (8px cells): content is marked with a margin; a
    // summed-area table answers "is this box clear?" at once, and each
    // column knows the nearest content above every row (thread anchors).
    const G = 8, M = 12;
    // (psyche.css lays out every section up front while the stars are on:
    // sections that only laid out when scrolled near changed the page's
    // height mid-scroll and the sky had to be re-placed.)
    function measure() {
      layer.style.height = '0px';   // don't let the layer's own height count as page (it would only ever grow)
      const W = doc.documentElement.clientWidth, H = doc.documentElement.scrollHeight, sy = scrollY;
      const cols = Math.ceil(W / G), rows = Math.ceil(H / G), occ = new Uint8Array(cols * rows);
      const mark = (x0, y0, x1, y1, m = M) => {
        const c0 = Math.max(0, Math.floor((x0 - m) / G)), c1 = Math.min(cols - 1, Math.floor((x1 + m) / G));
        const r0 = Math.max(0, Math.floor((y0 - m) / G)), r1 = Math.min(rows - 1, Math.floor((y1 + m) / G));
        for (let r = r0; r <= r1; r++) occ.fill(1, r * cols + c0, r * cols + c1 + 1);
      };
      const hero = $('.hero-split');
      if (hero) mark(0, 0, W, hero.getBoundingClientRect().bottom + sy, 0);   // the hero (and above) is off limits
      const rg = doc.createRange();
      for (const reg of [...$$('main > section:not(.hero-split)'), $('footer')]) {
        if (!reg) continue;
        // A section with its own background: don't let a star straddle its edges.
        const rcs = getComputedStyle(reg), rr = reg.getBoundingClientRect();
        if (!/rgba\(0, 0, 0, 0\)|transparent/.test(rcs.backgroundColor)) { mark(0, rr.top + sy, W, rr.top + sy); mark(0, rr.bottom + sy, W, rr.bottom + sy); }
        for (const band of reg.querySelectorAll(':scope > *')) {   // full-width coloured bands inside it (the footer's bar)
          const br = band.getBoundingClientRect(), bcs = getComputedStyle(band);
          if (br.width >= W * 0.92 && br.height > 0 && !/rgba\(0, 0, 0, 0\)|transparent/.test(bcs.backgroundColor)) { mark(0, br.top + sy, W, br.top + sy); mark(0, br.bottom + sy, W, br.bottom + sy); }
        }
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
      mark(0, 0, 4, H, 0); mark(W - 4, 0, W, H, 0);   // keep off the very edges
      const sat = new Int32Array((cols + 1) * (rows + 1));
      for (let r = 0; r < rows; r++) { let run = 0; for (let c = 0; c < cols; c++) { run += occ[r * cols + c]; sat[(r + 1) * (cols + 1) + c + 1] = sat[r * (cols + 1) + c + 1] + run; } }
      const above = new Int32Array(cols * rows).fill(-1);   // row index of the nearest content cell above
      for (let c = 0; c < cols; c++) { let last = -1; for (let r = 0; r < rows; r++) { if (occ[r * cols + c]) last = r; else above[r * cols + c] = last; } }
      const free = (x0, y0, x1, y1) => {
        const c0 = Math.floor(x0 / G), c1 = Math.ceil(x1 / G), r0 = Math.floor(y0 / G), r1 = Math.ceil(y1 / G);
        if (c0 < 0 || r0 < 0 || c1 > cols || r1 > rows) return false;
        return sat[r1 * (cols + 1) + c1] - sat[r0 * (cols + 1) + c1] - sat[r1 * (cols + 1) + c0] + sat[r0 * (cols + 1) + c0] === 0;
      };
      const ceiling = (x, y) => { const c = Math.floor(x / G), r = Math.floor(y / G); if (c < 0 || c >= cols || r < 0 || r >= rows) return null; const a = above[r * cols + c]; return a < 0 ? null : (a + 1) * G - M + 2; };
      const top = hero ? hero.getBoundingClientRect().bottom + sy : 0;
      return { W, H, top, free, ceiling };
    }

    let rt = 0;   // pending repair timer
    // ── placing the sky ──
    // Each star belongs to a section, at an offset from its top, so when
    // content above it grows or shrinks (a tracklist opens, the player
    // docks, a phone's address bar slides away) it moves with its section
    // instead of the whole sky being thrown away and re-placed.
    const SIZES = [[56, 72, 1.3], [32, 46, 3.6], [16, 24, 5]];   // [min px, max px, stars per million px²]
    const regions = () => [...$$('main > section:not(.hero-split)'), $('footer')].filter(Boolean);
    function place(map, s, cls, count, avoidView) {
      const [lo, hi] = SIZES[cls], secs = regions().map((el) => { const r = el.getBoundingClientRect(); return { el, top: r.top + scrollY, bottom: r.bottom + scrollY }; });
      for (let k = 0; k < count; k++) {
        const d = Math.floor(rnd() * DESIGNS);
        const size = (lo + rnd() * (hi - lo)) * s, R = size / 2, gap = size * 1.4 + 18 * s;
        let best = null;
        for (let tries = 0; tries < 260; tries++) {
          const x = R + 8 + rnd() * (map.W - 2 * R - 16), cy = map.top + R + 8 + rnd() * (map.H - map.top - 2 * R - 16);
          const pad = R * 0.2 + 4;   // room to jitter and swell
          // When topping up, never add a star where you're looking (it would pop in).
          if (avoidView && cy + R > scrollY - 50 && cy - R < scrollY + innerHeight + 50) continue;
          if (!map.free(x - R - pad, cy - R - pad, x + R + pad, cy + R + pad)) continue;
          let near = 1e9;
          for (const p of placed) near = Math.min(near, Math.hypot(p.cx - x, p.cy - cy) - p.R);
          if (near < gap) continue;
          let score = Math.min(near, gap * 3) / gap * 10 + rnd() * 5;
          for (const m of [16, 36]) if (map.free(x - R - pad - m, cy - R - pad - m, x + R + pad + m, cy + R + pad + m)) score += 6;
          if (!best || score > best.score) best = { x, cy, score };
        }
        if (!best) continue;
        const sec = secs.find((q) => best.cy >= q.top && best.cy < q.bottom) || secs[secs.length - 1];
        const o0base = Math.floor((rnd() - 0.5) * 50);
        const el = doc.createElement('i');
        el.className = 'chalk-star';
        // Always there from the start (no pop-in): a star never appears late.
        el.style.cssText = `left:${(best.x - R).toFixed(1)}px;top:${(best.cy - R).toFixed(1)}px;width:${size.toFixed(1)}px;height:${size.toFixed(1)}px;transform:rotate(${o0base}deg);background-color:${COLORS[Math.floor(rnd() * COLORS.length)]}`;
        layer.append(el);
        const o = { el, d, cls, sec: sec.el, off: best.cy - sec.top, cx: best.x, cy: best.cy, R, base: o0base, spin: (rnd() < 0.5 ? -1 : 1) * (0.04 + rnd() * 0.08), ph: rnd() * 6, f: Math.floor(rnd() * FRAMES) };
        setFrame(o); placed.push(o);
      }
    }
    // Fill the sky up to its quota for the page's size (phones get fewer).
    function fill(map, avoidView = false) {
      const s = Math.max(0.7, Math.min(1.05, innerWidth / 1300)), area = (map.W * (map.H - map.top)) / 1e6;
      SIZES.forEach(([, , per], cls) => place(map, s, cls, Math.max(0, Math.round(area * per) - placed.filter((o) => o.cls === cls).length), avoidView));
      layer.style.height = map.H + 'px';
    }
    // From scratch: on first load and when the page's width changes.
    function layout() {
      seed = 11;
      for (const o of placed) o.el.remove();
      placed = [];
      fill(measure());
      draw();
    }
    // Cheap: move every star with its section (no measuring).
    function follow() {
      const tops = new Map(regions().map((el) => [el, el.getBoundingClientRect().top + scrollY]));
      for (const o of placed) {
        const t = tops.get(o.sec); if (t == null) continue;
        const cy = t + o.off; if (Math.abs(cy - o.cy) < 0.5) continue;
        o.cy = cy; o.el.style.top = (cy - o.R).toFixed(1) + 'px';
      }
      layer.style.height = '0px';
      layer.style.height = doc.documentElement.scrollHeight + 'px';   // the page's real height, without the layer
    }
    // When things settle: drop any star now sitting on content, top up gaps.
    function repair() {
      rt = 0;
      const map = measure(), keep = [];
      for (const o of placed) {
        const pad = o.R * 0.2 + 4;
        if (map.free(o.cx - o.R - pad, o.cy - o.R - pad, o.cx + o.R + pad, o.cy + o.R + pad)) keep.push(o); else o.el.remove();
      }
      placed = keep;
      fill(map, true);
    }

    // The chalk sheet is a stencil (mask): show this star's design and boil frame.
    function setFrame(o) { const p = `${(o.f / (FRAMES - 1)) * 100}% ${(o.d / (DESIGNS - 1)) * 100}%`; o.el.style.webkitMaskPosition = p; o.el.style.maskPosition = p; }

    // ── stop motion: 8 frames a second ("on threes") ──
    let raf = 0, lastT = 0, shake = 0;
    function draw() {
      const vh = innerHeight, sy = scrollY, moving = fxOn();
      // Knocked about only by a genuinely fast flick, not ordinary scrolling.
      shake = Math.min(6, shake * 0.6 + Math.max(0, Math.abs(scrollVel) - 1.5) * 3);
      for (const o of placed) {
        const vy = o.cy - sy;
        if (vy < -500 || vy > vh + 500) continue;
        if (!moving) { o.f = 0; setFrame(o); o.el.style.transform = `rotate(${o.base}deg)`; continue; }
        // The line boils: the next of its three drawings, never the same twice running.
        o.f = (o.f + 1 + Math.floor(rnd() * (FRAMES - 1))) % FRAMES; setFrame(o);
        // A pixel of jitter every frame, more when a fast scroll knocks it.
        const jx = Math.round((rnd() - 0.5) * (1.6 + shake)), jy = Math.round((rnd() - 0.5) * (1.6 + shake));
        const rot = o.base + snap(sy * o.spin, 15) + (shake > 2 ? Math.round((rnd() - 0.5) * shake * 2) : 0);
        const sc = snap(1 + Math.sin(sy * 0.006 + o.ph) * 0.1, 0.05);
        o.el.style.transform = `translate(${jx}px,${jy}px) rotate(${rot}deg) scale(${sc})`;
      }
    }
    // Runs while effects are on and the page is visible (requestAnimationFrame
    // stops in background tabs); only the stars on screen are touched.
    function loop(t) {
      raf = 0;
      if (!fxOn()) { draw(); return; }
      if (t - lastT >= 1000 / 8 - 4) { lastT = t; draw(); }
      raf = requestAnimationFrame(loop);
    }
    const kick = () => { if (!raf) raf = requestAnimationFrame(loop); };
    addEventListener('scroll', kick, { passive: true });
    // Width changed: re-place from scratch. Only the height: stars follow
    // their sections now, and a repair runs once scrolling has stopped.
    let lt = 0, lastW = 0, lastH = 0;
    const scheduleRepair = () => { clearTimeout(rt); rt = setTimeout(repair, 900); };
    addEventListener('scroll', () => { if (rt) scheduleRepair(); }, { passive: true });
    const relayout = () => { clearTimeout(lt); lt = setTimeout(() => {
      // The page's own height: measured with the star layer collapsed, so a
      // page that shrinks (lyrics closed) is noticed and the layer shrinks too.
      const keep = layer.style.height; layer.style.height = '0px';
      const w = doc.documentElement.clientWidth, h = doc.documentElement.scrollHeight;
      layer.style.height = keep;
      if (w !== lastW) { lastW = w; lastH = h; clearTimeout(rt); rt = 0; layout(); kick(); return; }
      if (Math.abs(h - lastH) < 2) return;
      lastH = h; follow(); scheduleRepair();
    }, 120); };
    new ResizeObserver(relayout).observe(doc.body);
    addEventListener('resize', relayout, { passive: true });
    (doc.fonts?.ready || Promise.resolve()).then(() => setTimeout(relayout, 300));
    return { redraw: () => { draw(); kick(); } };
  })();

  // Settings for the footer's settings panel (kinetic.js picks these up).
  window.kineticItems = () => [
    { group: 'Settings', label: 'Background effects', on: fxPref, title: fxPref ? 'Turn background effects off' : 'Turn background effects on', sub: 'Haze, stars, confetti and fireworks', run: () => { fxPref = !fxPref; store.set('psy-fx', fxPref ? 'on' : 'off'); syncFx(); announce(`Background effects ${fxPref ? 'on' : 'off'}`); } },
  ];

  syncFx();
  }
})();
