/* ════════════════════════════════════════════════════════════════════
   PSYCHE: the homepage's psychedelic layer. Pairs with shared/psyche.css.

     field      liquid-chrome / acid-wash gradient behind the page, warped
                by scroll velocity and pointer acceleration (the frosted
                glass panels in psyche.css refract it)
     trail      iridescent ribbon behind the cursor (mouse/trackpad only)
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
  function syncFx() { root.classList.toggle('psy-calm', !fxOn()); field.redraw(); }
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
      const warp = 0.85 + ptr.energy * 0.4, px = (mx - 0.5) * 2.2, py = (my - 0.5) * 2.2;
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
      if (now - last >= 33) {   // ~30 fps is plenty for a slow liquid
        const dt = Math.min(0.1, (now - (last || now)) / 1000);
        last = now;
        const v = Math.min(3, Math.abs(scrollVel));
        t += dt * (0.08 + v * 0.3);                 // fast scrolling stirs the liquid
        phase += scrollVel * dt * 0.8;              // ...and rolls the colour bands with it
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
    const LIFE = 160;
    function frame(now) {
      raf = 0;
      ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
      ctx.clearRect(0, 0, innerWidth, innerHeight);
      while (pts.length && now - pts[0].t > LIFE) pts.shift();
      ctx.lineCap = 'round'; ctx.lineJoin = 'round';
      for (let i = 1; i < pts.length; i++) {
        const a = pts[i - 1], b = pts[i], age = (now - b.t) / LIFE, k = i / pts.length;
        ctx.strokeStyle = `hsla(${(b.t * 0.25 + i * 9) % 360}, 100%, 66%, ${(1 - age) * 0.3 * k})`;
        ctx.lineWidth = 1 + 2.5 * k * (1 - age);
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
        if (false) dust.push({ x, y, vx: (Math.random() - 0.5) * 2, vy: (Math.random() - 0.5) * 2, life: 1, h: (now * 0.25) % 360 });
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
    const t0 = performance.now(), D = 600;
    (function step(now) {
      const p = Math.min(1, (now - t0) / D), ease = 1 - Math.pow(1 - p, 3);
      rp.style.setProperty('--r', (ease * max).toFixed(1) + 'px');
      rp.style.opacity = String(1 - p * p);
      if (p < 1) requestAnimationFrame(step); else rp.remove();
    })(t0);
  }, { capture: true, passive: true });

  // Palette setting to switch the effects off (kinetic.js picks this up).
  window.kineticItems = () => [{ group: 'Settings', title: fxPref ? 'Turn background effects off' : 'Turn background effects on', sub: 'Liquid background, cursor trail, ripples', run: () => { fxPref = !fxPref; store.set('psy-fx', fxPref ? 'on' : 'off'); syncFx(); announce(`Background effects ${fxPref ? 'on' : 'off'}`); } }];

  syncFx();
  }
})();
