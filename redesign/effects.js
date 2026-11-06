/* ════════════════════════════════════════════════════════════════════
   ASH STU REDESIGN: MOTION EFFECTS LAYER
   ────────────────────────────────────────────────────────────────────
   1 Liquid distortion  · 2 RGB split · 3 Particle headline
   4 3D flythrough      · 5 Kinetic, music-reactive type

   Performance rules:
   • One requestAnimationFrame loop. Every frame runs a READ phase for all
     effects (layout reads), then a WRITE phase (style/canvas writes), so
     the browser never has to recalculate layout mid-frame.
   • Only transform and opacity are animated on DOM elements.
   • Pointer/scroll listeners are passive and only record numbers; all
     work happens once per frame in the loop (rAF-throttled).
   • No per-frame allocations in hot loops (typed arrays, reused objects).
   • Effects start one per task after first paint, so no long task blocks
     input (Total Blocking Time stays at zero).

   Accessibility: off by default with "Reduce motion"; the Motion button
   toggles everything; real text stays in the DOM; canvases and the
   flythrough are aria-hidden; the flythrough has a skip link.
   ════════════════════════════════════════════════════════════════════ */
(() => {
  'use strict';
  const $ = (s, el = document) => el.querySelector(s);
  const $$ = (s, el = document) => [...el.querySelectorAll(s)];
  const clamp = (v, a, b) => (v < a ? a : v > b ? b : v);
  const root = document.documentElement;
  const reduceMQ = matchMedia('(prefers-reduced-motion: reduce)');
  const coarse = matchMedia('(pointer: coarse)').matches;
  const STORE = 'ash-motion';
  const nextTask = () => new Promise((r) => setTimeout(r, 0));
  // Resolves just after the next frame has been painted: rAF runs before
  // paint, the timeout fires after it. Effects never delay first paint.
  const afterPaint = () => new Promise((r) => requestAnimationFrame(() => setTimeout(r, 0)));

  // ── SHARED FRAME STATE (written by listeners, read once per frame) ─
  const ptr = { x: -1e4, y: -1e4, vx: 0, vy: 0, speed: 0, active: false };
  const view = { w: innerWidth, h: innerHeight, sy: scrollY, sx: scrollX, scrollVel: 0, lastSy: scrollY };
  addEventListener('pointermove', (e) => {
    if (ptr.active) { ptr.vx += e.clientX - ptr.x; ptr.vy += e.clientY - ptr.y; }
    ptr.x = e.clientX; ptr.y = e.clientY; ptr.active = true;
  }, { passive: true });
  addEventListener('pointerdown', (e) => { ptr.x = e.clientX; ptr.y = e.clientY; ptr.active = true; }, { passive: true });
  document.addEventListener('mouseout', (e) => { if (!e.relatedTarget) ptr.active = false; }, { passive: true });
  let resized = true;
  addEventListener('resize', () => { resized = true; }, { passive: true });

  // ── AUDIO ANALYSIS (effect 5; desktop only, see note) ─────────────
  // On iOS, routing <audio> through Web Audio can stop playback when the
  // screen locks, so touch devices skip the music-reactive part.
  const audio = $('#audio');
  let actx = null, analyser = null, bins = null, level = 0;
  function wakeAudio() {
    if (coarse || !enabled) return;
    try { actx ??= new AudioContext(); if (actx.state === 'suspended') actx.resume(); } catch { actx = null; }
  }
  // Inside the user's gesture, before the player starts playback.
  addEventListener('pointerdown', wakeAudio, { capture: true, passive: true });
  addEventListener('keydown', wakeAudio, { capture: true, passive: true });
  audio?.addEventListener('play', () => {
    if (!actx || analyser || actx.state !== 'running') return;
    try {
      const src = actx.createMediaElementSource(audio);
      analyser = actx.createAnalyser();
      analyser.fftSize = 128;
      analyser.smoothingTimeConstant = 0.75;
      src.connect(analyser); analyser.connect(actx.destination);
      bins = new Uint8Array(analyser.frequencyBinCount);
    } catch { analyser = null; }
  });
  function readAudio() {
    if (!analyser || audio.paused) { level *= 0.9; return; }
    analyser.getByteFrequencyData(bins);
    let sum = 0;
    for (let i = 2; i < 24; i++) sum += bins[i];
    level = level * 0.7 + (sum / (22 * 255)) * 0.3;
  }
  const bin = (i) => (bins && !audio.paused ? bins[2 + (i % 30)] / 255 : 0);

  const visible = new WeakSet();
  const io = new IntersectionObserver((entries) => {
    for (const en of entries) en.isIntersecting ? visible.add(en.target) : visible.delete(en.target);
  }, { rootMargin: '100px' });

  // ══ 3 · PARTICLE HEADLINE ═════════════════════════════════════════
  const particles = (() => {
    const h1 = $('.hero-title');
    const textNode = h1 && [...h1.childNodes].find((n) => n.nodeType === 3 && n.textContent.trim());
    let canvas, ctx, img, buf32, W, H, dpr, N = 0, P, ink, gold, rect = null, dirty = false;

    const rgbInt = (r, g, b) => (255 << 24) | (b << 16) | (g << 8) | r;   // little-endian ABGR
    const cssInt = (css) => { const m = css.match(/\d+/g).map(Number); return rgbInt(m[0], m[1], m[2]); };
    const hexInt = (hex) => { const n = parseInt(hex.replace('#', ''), 16); return rgbInt(n >> 16, (n >> 8) & 255, n & 255); };

    function build() {   // reads layout: only at start and after a resize
      const cs = getComputedStyle(h1);
      const hr = h1.getBoundingClientRect();
      const range = document.createRange();
      range.selectNodeContents(textNode);
      const tr = range.getBoundingClientRect();
      W = Math.ceil(hr.width * 1.24); H = Math.ceil(hr.height * 1.6);
      dpr = Math.min(2, devicePixelRatio || 1);
      const off = new OffscreenCanvas(W, H);
      const o = off.getContext('2d', { willReadFrequently: true });
      o.font = `${cs.fontStyle} ${cs.fontWeight} ${cs.fontSize} ${cs.fontFamily}`;
      if ('letterSpacing' in o) o.letterSpacing = cs.letterSpacing;
      const text = textNode.textContent.replace(/ /g, ' ');
      const m = o.measureText(text);
      const left = hr.left - hr.width * 0.12, top = hr.top - hr.height * 0.3;
      o.fillText(text, tr.left - left, tr.top - top + tr.height / 2 + (m.actualBoundingBoxAscent - m.actualBoundingBoxDescent) / 2);
      const data = o.getImageData(0, 0, W, H).data;
      const max = coarse ? 6500 : 9000;
      // One counting pass, then pick the densest grid that fits the budget
      // (a grid step of g keeps about 1/g² of the filled pixels).
      let filled = 0;
      for (let i = 3; i < data.length; i += 4) if (data[i] > 140) filled++;
      const gap = Math.max(1, Math.ceil(Math.sqrt(filled / max)));
      let count = 0;
      for (let y = 0; y < H; y += gap) for (let x = 0; x < W; x += gap) if (data[(y * W + x) * 4 + 3] > 140) count++;
      // P = [homeX, homeY, x, y, vx, vy]. Particles start AT home, so the
      // first painted frame looks exactly like the text it replaces.
      P = new Float32Array(count * 6); N = count;
      let i = 0;
      for (let y = 0; y < H; y += gap) for (let x = 0; x < W; x += gap) {
        if (data[(y * W + x) * 4 + 3] <= 140) continue;
        P[i] = P[i + 2] = x; P[i + 1] = P[i + 3] = y; i += 6;
      }
      return { cw: W * dpr, ch: H * dpr };
    }

    return {
      start() {
        if (!h1 || !textNode || typeof OffscreenCanvas === 'undefined') return;
        ink = cssInt(getComputedStyle(h1).color);
        gold = hexInt(getComputedStyle(root).getPropertyValue('--daffodil').trim());
        canvas = document.createElement('canvas');
        canvas.className = 'fx-particle-canvas';
        canvas.setAttribute('aria-hidden', 'true');
        ctx = canvas.getContext('2d');
        const { cw, ch } = build();
        canvas.width = cw; canvas.height = ch;
        img = ctx.createImageData(cw, ch); buf32 = new Uint32Array(img.data.buffer);
        h1.append(canvas);
        h1.classList.add('fx-particles');
        io.observe(h1);
      },
      stop() {
        canvas?.remove(); canvas = null; P = null; N = 0;
        h1?.classList.remove('fx-particles'); h1 && io.unobserve(h1);
      },
      read() {
        if (!canvas) return;
        if (resized) dirty = true;
        rect = visible.has(h1) ? canvas.getBoundingClientRect() : null;
      },
      write() {
        if (!canvas) return;
        if (dirty) {   // rebuild after resize (one layout read, then writes)
          dirty = false;
          const { cw, ch } = build();
          canvas.width = cw; canvas.height = ch;
          img = ctx.createImageData(cw, ch); buf32 = new Uint32Array(img.data.buffer);
          return;
        }
        if (!rect) return;
        const sx = rect.width / W;
        const mx = (ptr.x - rect.left) / sx, my = (ptr.y - rect.top) / sx;
        const R = coarse ? 70 : 110, R2 = R * R, jitter = level * 5, on = ptr.active;
        buf32.fill(0);
        const s = Math.max(1, Math.round((coarse ? 1.5 : 2) * dpr)), cw = canvas.width, ch = canvas.height;
        for (let k = 0, n = N * 6; k < n; k += 6) {
          let x = P[k + 2], y = P[k + 3], vx = P[k + 4], vy = P[k + 5];
          if (on) {
            const dx = x - mx, dy = y - my, d2 = dx * dx + dy * dy;
            if (d2 < R2 && d2 > 0.01) {
              const d = Math.sqrt(d2), f = 1 - d / R, ux = dx / d, uy = dy / d;
              vx += ux * f * 5.5 - uy * f * 4;   // push out + swirl (vortex)
              vy += uy * f * 5.5 + ux * f * 4;
            }
          }
          vx += (P[k] - x) * 0.04; vy += (P[k + 1] - y) * 0.04;   // spring home
          if (jitter) { vx += (Math.random() - 0.5) * jitter; vy += (Math.random() - 0.5) * jitter; }
          vx *= 0.86; vy *= 0.86; x += vx; y += vy;
          P[k + 2] = x; P[k + 3] = y; P[k + 4] = vx; P[k + 5] = vy;
          const px = (x * dpr) | 0, py = (y * dpr) | 0;
          if (px < 0 || py < 0 || px + s >= cw || py + s >= ch) continue;
          const color = vx * vx + vy * vy > 6 ? gold : ink;   // fast particles glow daffodil
          for (let a = 0; a < s; a++) { const row = (py + a) * cw + px; for (let b = 0; b < s; b++) buf32[row + b] = color; }
        }
        ctx.putImageData(img, 0, 0);
      },
    };
  })();

  // ══ 5 · KINETIC TYPE  +  2 · RGB SPLIT ON HEADINGS ════════════════
  // Letters scale and lift with transform only. Their centers are measured
  // once (and after resizes) in page coordinates, so normal frames do no
  // layout reads at all. (A remeasure while a letter is mid-swell is off by
  // a pixel or two; not visible.)
  const kinetic = (() => {
    let split = [], letters = [], cx, cy, cur, needMeasure = false, lastRgb = 'x';
    function splitHeading(el) {
      for (const node of [...el.childNodes]) {
        if (node.nodeType !== 3 || !node.textContent.trim()) continue;
        const sr = document.createElement('span');
        sr.className = 'sr-only'; sr.textContent = node.textContent;
        const vis = document.createElement('span');
        vis.className = 'fx-letters'; vis.setAttribute('aria-hidden', 'true');
        vis.dataset.text = node.textContent;   // source for the RGB ghost copies
        for (const part of node.textContent.split(/(\s+)/)) {
          if (!part) continue;
          if (/^\s+$/.test(part)) { vis.append(part); continue; }
          const word = document.createElement('span');
          word.className = 'fx-word';
          for (const ch of part) {
            const span = document.createElement('span');
            span.className = 'fx-letter'; span.textContent = ch;
            word.append(span); letters.push({ span, el, shown: '' });
          }
          vis.append(word);
        }
        node.replaceWith(sr, vis);
        split.push({ node, sr, vis, el });
        io.observe(el);
      }
    }
    return {
      start() {
        $$('.section-head h2, .record-title, .new-record-title').forEach(splitHeading);
        cx = new Float32Array(letters.length); cy = new Float32Array(letters.length); cur = new Float32Array(letters.length);
        needMeasure = true;
      },
      stop() {
        for (const s of split) { s.sr.replaceWith(s.node); s.vis.remove(); io.unobserve(s.el); }
        split = []; letters = [];
        root.style.removeProperty('--rgb'); root.style.removeProperty('--rgbo');
      },
      read() {
        if (!letters.length) return;
        if (resized) needMeasure = true;
        if (!needMeasure) return;
        needMeasure = false;
        for (let i = 0; i < letters.length; i++) {
          const r = letters[i].span.offsetParent ? letters[i].span.getBoundingClientRect() : null;
          cx[i] = r ? r.left + r.width / 2 + view.sx : -1e5;
          cy[i] = r ? r.top + r.height / 2 + view.sy : -1e5;
        }
      },
      write() {
        // RGB split from scroll velocity: two custom properties per frame.
        const v = clamp(view.scrollVel * 0.18, -7, 7);
        const rgb = Math.abs(v) < 0.05 ? '0' : v.toFixed(1);
        if (rgb !== lastRgb) {
          root.style.setProperty('--rgb', rgb);
          root.style.setProperty('--rgbo', rgb === '0' ? '0' : Math.min(0.6, Math.abs(v) / 4).toFixed(2));
          lastRgb = rgb;
        }
        const px = ptr.x + view.sx, py = ptr.y + view.sy;
        for (let i = 0; i < letters.length; i++) {
          const L = letters[i];
          if (!visible.has(L.el)) continue;
          let t = 0;
          if (ptr.active) {
            const dx = px - cx[i], dy = py - cy[i];
            const d2 = dx * dx + dy * dy;
            if (d2 < 36100) { const f = 1 - Math.sqrt(d2) / 190; t = f * f; }   // within 190px
          }
          t += bin(i) * 0.8;   // each letter listens to its own frequency band
          cur[i] += (clamp(t, 0, 1.4) - cur[i]) * 0.25;
          const q = Math.round(cur[i] * 50) / 50;
          const tf = q === 0 ? '' : `translate3d(0,${(-q * 6).toFixed(1)}px,0) scale(${(1 + q * 0.35).toFixed(3)})`;
          if (tf !== L.shown) { L.span.style.transform = tf; L.shown = tf; }
        }
      },
    };
  })();

  // ══ 1 + 2 · LIQUID DISTORTION + CHROMATIC ABERRATION (WebGL) ══════
  const liquid = (() => {
    const TARGETS = '.hero-photo img, .record-art, .new-record-art, .video-link img, .press-photos img';
    let canvas, gl, tex, U = {}, current = null, hover = 0, hoverTarget = 0, rect = null, t0 = performance.now();
    let lastTf = '', lastW = 0, lastH = 0;
    const VERT = 'attribute vec2 p;varying vec2 vUv;void main(){vUv=p*.5+.5;gl_Position=vec4(p,0.,1.);}';
    // Warp texture coordinates around the pointer (ripple ring + magnifying
    // lens), then sample R, G, B at offsets along the movement direction.
    const FRAG = `precision mediump float;
      uniform sampler2D uTex;uniform vec2 uMouse,uDir,uScale,uOffset;uniform float uTime,uHover,uVel,uAspect;varying vec2 vUv;
      vec4 tex(vec2 u){return texture2D(uTex,clamp(u,0.,1.)*uScale+uOffset);}
      void main(){vec2 d=vUv-uMouse;d.x*=uAspect;float dist=length(d);vec2 dir=dist>.0001?d/dist:vec2(0.);dir.x/=uAspect;
      float ripple=sin(dist*34.-uTime*4.5)*exp(-dist*7.)*.010;float lens=exp(-dist*dist*26.)*.11;
      vec2 uv=vUv+dir*ripple*uHover-vec2(d.x/uAspect,d.y)*lens*uHover;vec2 shift=uDir*uVel*.018*(.35+uHover);
      gl_FragColor=vec4(tex(uv+shift).r,tex(uv).g,tex(uv-shift).b,1.);}`;

    function setup() {
      canvas = document.createElement('canvas');
      canvas.className = 'fx-liquid'; canvas.setAttribute('aria-hidden', 'true');
      gl = canvas.getContext('webgl', { premultipliedAlpha: false, antialias: false, alpha: false, powerPreference: 'low-power' });
      if (!gl) return false;
      const prog = gl.createProgram();
      for (const [type, src] of [[gl.VERTEX_SHADER, VERT], [gl.FRAGMENT_SHADER, FRAG]]) {
        const sh = gl.createShader(type); gl.shaderSource(sh, src); gl.compileShader(sh);
        if (!gl.getShaderParameter(sh, gl.COMPILE_STATUS)) return false;
        gl.attachShader(prog, sh);
      }
      gl.linkProgram(prog);
      if (!gl.getProgramParameter(prog, gl.LINK_STATUS)) return false;
      gl.useProgram(prog);
      gl.bindBuffer(gl.ARRAY_BUFFER, gl.createBuffer());
      gl.bufferData(gl.ARRAY_BUFFER, new Float32Array([-1, -1, 1, -1, -1, 1, 1, 1]), gl.STATIC_DRAW);
      const loc = gl.getAttribLocation(prog, 'p');
      gl.enableVertexAttribArray(loc); gl.vertexAttribPointer(loc, 2, gl.FLOAT, false, 0, 0);
      for (const n of ['uTex', 'uMouse', 'uDir', 'uScale', 'uOffset', 'uTime', 'uHover', 'uVel', 'uAspect']) U[n] = gl.getUniformLocation(prog, n);
      tex = gl.createTexture(); gl.bindTexture(gl.TEXTURE_2D, tex);
      gl.texParameteri(gl.TEXTURE_2D, gl.TEXTURE_WRAP_S, gl.CLAMP_TO_EDGE);
      gl.texParameteri(gl.TEXTURE_2D, gl.TEXTURE_WRAP_T, gl.CLAMP_TO_EDGE);
      gl.texParameteri(gl.TEXTURE_2D, gl.TEXTURE_MIN_FILTER, gl.LINEAR);
      gl.texParameteri(gl.TEXTURE_2D, gl.TEXTURE_MAG_FILTER, gl.LINEAR);
      gl.pixelStorei(gl.UNPACK_FLIP_Y_WEBGL, true);
      document.body.append(canvas);
      return true;
    }
    function activate(el) {   // runs on pointerover (an event, not a frame)
      if (!el.complete || !el.naturalWidth) return;
      try { gl.bindTexture(gl.TEXTURE_2D, tex); gl.texImage2D(gl.TEXTURE_2D, 0, gl.RGB, gl.RGB, gl.UNSIGNED_BYTE, el); } catch { return; }
      const cs = getComputedStyle(el);
      canvas.style.borderRadius = cs.borderRadius !== '0px' ? cs.borderRadius : getComputedStyle(el.parentElement).borderRadius;
      el.fxPos = cs.objectPosition.split(' ').map((v) => (v.endsWith('%') ? parseFloat(v) / 100 : 0.5));
      current = el; hoverTarget = 1;
    }
    let failed = false;
    // WebGL (context + shader compile) is set up lazily, the first time a
    // pointer reaches an image: zero cost during page load.
    function ensureGL() {
      if (gl || failed) return !!gl;
      try { if (setup()) return true; } catch {}
      canvas?.remove(); canvas = null; gl = null; failed = true;
      return false;
    }
    const over = (e) => {
      const el = e.target.closest?.(TARGETS);
      if (!el || !ensureGL()) return;
      if (el !== current) activate(el); else hoverTarget = 1;
    };

    return {
      start() { document.addEventListener('pointerover', over, { passive: true }); },
      stop() {
        document.removeEventListener('pointerover', over);
        gl?.getExtension('WEBGL_lose_context')?.loseContext();
        canvas?.remove(); canvas = null; gl = null; current = null; hover = 0; lastTf = ''; lastW = lastH = 0; failed = false;
      },
      read() { rect = current ? current.getBoundingClientRect() : null; },
      write(now) {
        if (!gl || !current || !rect) return;
        const r = rect;
        // Scrolling slides images out from under a still pointer without a
        // pointerout event, so check containment every frame.
        if (!(ptr.active && ptr.x >= r.left && ptr.x <= r.right && ptr.y >= r.top && ptr.y <= r.bottom)) hoverTarget = 0;
        hover += (hoverTarget - hover) * 0.12;
        if (r.width < 2 || r.bottom < 0 || r.top > view.h || (hoverTarget === 0 && hover < 0.02)) {
          canvas.classList.remove('on'); current = null; hover = 0; return;
        }
        const dpr = Math.min(1.5, devicePixelRatio || 1);
        const w = Math.round(r.width * dpr), h = Math.round(r.height * dpr);
        if (w !== lastW || h !== lastH) {
          canvas.width = w; canvas.height = h; gl.viewport(0, 0, w, h);
          canvas.style.width = r.width + 'px'; canvas.style.height = r.height + 'px';
          lastW = w; lastH = h;
        }
        const tf = `translate3d(${r.left}px,${r.top}px,0)`;
        if (tf !== lastTf) { canvas.style.transform = tf; lastTf = tf; }
        canvas.classList.add('on');
        const boxAR = r.width / r.height, imgAR = current.naturalWidth / current.naturalHeight;
        const sx = imgAR > boxAR ? boxAR / imgAR : 1, sy = imgAR > boxAR ? 1 : imgAR / boxAR;
        const [px, py = 0.5] = current.fxPos;
        const vel = clamp(ptr.speed / 60 + Math.abs(view.scrollVel) / 60, 0, 1);
        gl.uniform2f(U.uScale, sx, sy);
        gl.uniform2f(U.uOffset, (1 - sx) * px, (1 - sy) * (1 - py));
        gl.uniform2f(U.uMouse, (ptr.x - r.left) / r.width, 1 - (ptr.y - r.top) / r.height);
        const len = Math.hypot(ptr.vx, ptr.vy);
        if (len > 0.5) gl.uniform2f(U.uDir, ptr.vx / len, -ptr.vy / len);
        else if (Math.abs(view.scrollVel) > 0.5) gl.uniform2f(U.uDir, 0, Math.sign(view.scrollVel));
        gl.uniform1f(U.uVel, vel); gl.uniform1f(U.uHover, hover);
        gl.uniform1f(U.uAspect, boxAR); gl.uniform1f(U.uTime, (now - t0) / 1000);
        gl.drawArrays(gl.TRIANGLE_STRIP, 0, 4);
      },
    };
  })();

  // ══ 4 · SCROLL-TIED 3D FLYTHROUGH ════════════════════════════════
  // Fills the slot that the static HTML already reserves (#fx-crate), so
  // nothing on the page moves when it appears.
  const crate = (() => {
    const GAP = 1500;
    const wrap = $('#fx-crate');
    let scene, stations = [], dots = [], top = 0, total = 1, lastScene = '';
    const smoother = (t) => t * t * t * (t * (t * 6 - 15) + 10);
    return {
      start() {
        const records = $$('.record');
        if (!wrap || records.length < 2) return;
        const spread = Math.min(view.w * 0.22, 320);
        const stage = document.createElement('div'); stage.className = 'fx-stage';
        scene = document.createElement('div'); scene.className = 'fx-scene';
        records.forEach((rec, i) => {
          const fig = document.createElement('figure'); fig.className = 'fx-station';
          const x = i === 0 ? 0 : (i % 2 ? spread : -spread);
          fig.style.transform = `translate3d(${x}px,0,${-i * GAP}px) rotateY(${i === 0 ? 0 : (i % 2 ? -16 : 16)}deg)`;
          const img = document.createElement('img');
          img.src = $('.record-art', rec).src; img.alt = '';
          const cap = document.createElement('figcaption');
          const t = document.createElement('p'); t.className = 'fx-st-title'; t.textContent = $('.record-title', rec).textContent.trim();
          const facts = $$('.record-facts dd', rec).map((d) => d.textContent.trim());
          const m = document.createElement('p'); m.className = 'fx-st-meta'; m.textContent = `${facts[0]} · ${facts[1]} · ${facts[2]}`;
          cap.append(t, m); fig.append(img, cap); scene.append(fig);
          stations.push({ fig, cap, x, z: -i * GAP, op: '', cop: '' });
        });
        for (let i = 0; i < 70; i++) {   // daffodil dust for depth cues
          const d = document.createElement('i'); d.className = 'fx-dust';
          d.style.transform = `translate3d(${(Math.random() - 0.5) * 2400}px,${(Math.random() - 0.5) * 1400}px,${-Math.random() * GAP * records.length + 600}px) rotate(${Math.random() * 90}deg)`;
          scene.append(d);
        }
        const prog = document.createElement('div'); prog.className = 'fx-progress';
        dots = records.map(() => prog.appendChild(document.createElement('i')));
        stage.append(scene, prog); wrap.append(stage);
        total = 1;
        io.observe(wrap);
      },
      stop() { if (wrap) { wrap.replaceChildren(); io.unobserve(wrap); } scene = null; stations = []; dots = []; lastScene = ''; },
      read() {
        if (!scene || !visible.has(wrap)) return;
        if (resized || total === 1) total = Math.max(1, wrap.offsetHeight - view.h);
        top = wrap.getBoundingClientRect().top;
      },
      write() {
        if (!scene || !visible.has(wrap)) return;
        const n = stations.length;
        const raw = clamp(-top / total, 0, 1) * n;
        // Hold still for the first and last quarter of each segment, so the
        // camera visibly stops at every record.
        const s = clamp(raw - 0.5, 0, n - 1);
        const seg = Math.min(n - 2, Math.floor(s)), f = s - seg;
        const e = seg + smoother(clamp((f - 0.25) / 0.5, 0, 1));
        const ai = Math.floor(e), a = stations[ai], b = stations[Math.min(n - 1, ai + 1)], t = e - ai;
        const camX = a.x + (b.x - a.x) * t, camZ = e * GAP;
        const tilt = ptr.active ? (ptr.x / view.w - 0.5) * 6 : 0;
        const tf = `rotateY(${tilt.toFixed(2)}deg) translate3d(${(-camX).toFixed(1)}px,0,${camZ.toFixed(1)}px)`;
        if (tf !== lastScene) { scene.style.transform = tf; lastScene = tf; }
        const near = Math.round(e);
        for (let i = 0; i < n; i++) {
          const st = stations[i], rel = st.z + camZ;
          const op = (rel > 500 ? 0 : rel > 0 ? 1 - rel / 500 : clamp(1 + rel / (GAP * 2.2), 0, 1)).toFixed(2);
          const cop = clamp(1 - Math.abs(rel) / 350, 0, 1).toFixed(2);
          if (op !== st.op) { st.fig.style.opacity = op; st.op = op; }
          if (cop !== st.cop) { st.cap.style.opacity = cop; st.cop = cop; }
          dots[i].classList.toggle('on', near === i);
        }
      },
    };
  })();

  // ── MAIN LOOP: read everything, then write everything ─────────────
  // Order matters on start: the flythrough copies record titles before
  // kinetic type splits them into letters.
  const modules = [crate, kinetic, particles, liquid];
  let enabled = false, raf = 0, starting = null;
  function frame(now) {
    raf = requestAnimationFrame(frame);
    if (document.hidden) return;
    // READ phase
    view.sy = scrollY; view.sx = scrollX;
    if (resized) { view.w = innerWidth; view.h = innerHeight; }
    view.scrollVel = view.scrollVel * 0.8 + (view.sy - view.lastSy) * 0.2; view.lastSy = view.sy;
    ptr.speed = Math.hypot(ptr.vx, ptr.vy);
    readAudio();
    for (let i = 0; i < modules.length; i++) { try { modules[i].read(); } catch (err) { disable(modules[i], err); } }
    // WRITE phase
    for (let i = 0; i < modules.length; i++) { try { modules[i].write(now); } catch (err) { disable(modules[i], err); } }
    resized = false;
    ptr.vx *= 0.8; ptr.vy *= 0.8;
  }
  function disable(m, err) {
    console.warn('effect disabled:', err);
    try { m.stop(); } catch {}
    m.read = m.write = () => {};
  }

  async function setEnabled(on, remember) {
    if (on === enabled) return;
    enabled = on;
    root.classList.toggle('fx', on);
    toggle?.setAttribute('aria-pressed', String(on));
    if (remember) { try { localStorage.setItem(STORE, on ? 'on' : 'off'); } catch {} }
    if (on) {
      const run = (starting = {});
      await afterPaint();
      // One effect per task: no long task, so input is never blocked.
      for (const m of modules) {
        await nextTask();
        if (!enabled || starting !== run) return;
        try { m.start(); } catch (err) { disable(m, err); }
      }
      resized = true;
      view.lastSy = scrollY;
      raf = requestAnimationFrame(frame);
    } else {
      starting = null;
      cancelAnimationFrame(raf);
      for (const m of modules) { try { m.stop(); } catch {} }
    }
  }

  // The Motion button is in the static HTML; just wire it up.
  const toggle = $('.fx-toggle');
  toggle?.addEventListener('click', () => setEnabled(!enabled, true));

  // html.fx was already set (or not) before first paint by the inline head
  // script, using the same rule: saved choice, else the OS setting.
  setEnabled(root.classList.contains('fx'), false);
  reduceMQ.addEventListener?.('change', (e) => {
    let s = null; try { s = localStorage.getItem(STORE); } catch {}
    if (!s) setEnabled(!e.matches, false);
  });
})();
