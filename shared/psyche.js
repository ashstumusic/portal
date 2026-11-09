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
    function pixelate(img) {
      if (!img.complete || !img.naturalWidth || img.dataset.nesOut === img.currentSrc) return;
      if (img.closest('.k-palette')) return;
      const LONG = img.classList.contains('hero-split-photo') ? 160 : 96;   // pixel art, but still recognisable
      const k = LONG / Math.max(img.naturalWidth, img.naturalHeight);
      const w = Math.max(8, Math.round(img.naturalWidth * k)), h = Math.max(8, Math.round(img.naturalHeight * k));
      const c = doc.createElement('canvas'); c.width = w; c.height = h;
      const x = c.getContext('2d', { willReadFrequently: true });
      try {
        x.drawImage(img, 0, 0, w, h);
        const d = x.getImageData(0, 0, w, h), px = d.data;
        for (let i = 0; i < px.length; i += 4) {
          const p = i / 4, t = (BAYER[((p / w | 0) % 4) * 4 + (p % w) % 4] / 16 - 0.5) * 28;
          const r = px[i] + t, g = px[i + 1] + t, b = px[i + 2] + t;
          let best = 0, bd = Infinity;
          for (let j = 0; j < PAL.length; j++) { const q = PAL[j], dd = (r - q[0]) ** 2 * 0.3 + (g - q[1]) ** 2 * 0.59 + (b - q[2]) ** 2 * 0.11; if (dd < bd) { bd = dd; best = j; } }
          px[i] = PAL[best][0]; px[i + 1] = PAL[best][1]; px[i + 2] = PAL[best][2];
        }
        x.putImageData(d, 0, 0);
        // Blow the pixel art back up to the photo's own dimensions (hard
        // square pixels, no smoothing): layouts that size an image from
        // its natural pixels (like the press kit photo columns) would
        // otherwise shrink to the tiny copy.
        const k2 = Math.min(1, 1600 / Math.max(img.naturalWidth, img.naturalHeight));
        const up = doc.createElement('canvas');
        up.width = Math.round(img.naturalWidth * k2); up.height = Math.round(img.naturalHeight * k2);
        const ux = up.getContext('2d'); ux.imageSmoothingEnabled = false;
        ux.drawImage(c, 0, 0, up.width, up.height);
        const out = up.toDataURL('image/png');
        if (!img.dataset.nesOrig) { img.dataset.nesOrig = img.getAttribute('src') || ''; if (img.srcset) { img.dataset.nesSrcset = img.srcset; img.removeAttribute('srcset'); } }
        img.dataset.nesOut = out;
        img.src = out;
        img.classList.add('nes-px');
      } catch { /* a cross-origin image can't be read back; leave it */ }
    }
    function pixelateAll() {
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

    // ── the name as pixel art ──
    // A mosaic filter on big text drops tiles on the GPU (parts of the
    // name vanished), so the name is redrawn instead: painted at full size
    // into a canvas, shrunk to one pixel per ~6 screen pixels with hard
    // (thresholded) edges, then shown scaled up with square pixels in place
    // of the live text. The text itself stays in the page, invisible, for
    // screen readers, search and copying.
    let nameObs = null, nameRaf = 0;
    function pixelName(el) {
      const tn = [...el.childNodes].find((n) => n.nodeType === 3 && n.nodeValue.trim());
      if (!tn) return;
      el.classList.remove('nes-name');            // measure and read colour from the real text
      const box = el.getBoundingClientRect();
      if (box.width < 4 || box.height < 4) return;
      const cs = getComputedStyle(el), fs = parseFloat(cs.fontSize);
      const rg = doc.createRange(); rg.selectNodeContents(tn);
      const tr = rg.getBoundingClientRect();
      // Baseline: where a zero-size inline-block placed after the text sits.
      const probe = doc.createElement('span');
      probe.style.cssText = 'display:inline-block;width:0;height:0;vertical-align:baseline';
      el.insertBefore(probe, tn.nextSibling);
      const base = probe.getBoundingClientRect().top - box.top;
      el.removeChild(probe);
      const B = Math.max(3, Math.round(fs / 22));  // block size in screen pixels
      const W = Math.ceil(box.width), H = Math.ceil(box.height);
      const big = doc.createElement('canvas'); big.width = W; big.height = H;
      const g = big.getContext('2d');
      g.font = `${cs.fontStyle} ${cs.fontWeight} ${fs}px ${cs.fontFamily}`;
      if ('letterSpacing' in g) g.letterSpacing = cs.letterSpacing === 'normal' ? '0px' : cs.letterSpacing;
      g.fillStyle = cs.color; g.textBaseline = 'alphabetic';
      g.fillText(tn.nodeValue.trim(), tr.left - box.left, base);
      const w = Math.ceil(W / B), h = Math.ceil(H / B);
      const sm = doc.createElement('canvas'); sm.width = w; sm.height = h;
      const x = sm.getContext('2d', { willReadFrequently: true });
      x.imageSmoothingQuality = 'high';
      x.drawImage(big, 0, 0, w, h);
      const d = x.getImageData(0, 0, w, h), px = d.data;
      for (let i = 3; i < px.length; i += 4) px[i] = px[i] > 96 ? 255 : 0;   // hard edges, no anti-aliasing
      x.putImageData(d, 0, 0);
      el.style.setProperty('--nes-name', `url(${sm.toDataURL('image/png')})`);
      el.style.setProperty('--nes-name-size', `${w * B}px ${h * B}px`);
      el.classList.add('nes-name');
    }
    const names = () => $$('.hero-name');
    function nameOn() {
      const run = () => { cancelAnimationFrame(nameRaf); nameRaf = requestAnimationFrame(() => on && names().forEach(pixelName)); };
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
