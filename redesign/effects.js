/* ════════════════════════════════════════════════════════════════════
   ASH STU REDESIGN: MOTION EFFECTS LAYER
   ────────────────────────────────────────────────────────────────────
   Five effects, all optional decoration on top of a complete static page:
     1. Liquid distortion   images ripple and bulge under the pointer (WebGL shader)
     2. RGB split           color channels tear apart with pointer/scroll speed
     3. Particle headline   "Ash Stu" drawn as thousands of particles that
                            swirl away from the pointer and reassemble
     4. 3D flythrough       scroll flies a camera through the record covers,
                            holding still at each one
     5. Kinetic type        headings swell in weight near the pointer and
                            pulse to the music while a song plays

   Accessibility rules this file follows:
   • Off by default when the OS asks for reduced motion; a Motion button in
     the masthead turns everything on or off for anyone, and the choice is
     remembered (WCAG 2.2.2 Pause, Stop, Hide).
   • Effects never carry information. Real text stays in the DOM; every
     canvas and the flythrough are aria-hidden; the flythrough has a skip link.
   • No libraries: raw WebGL and Canvas 2D, so nothing extra to download.
   • Loops pause when their element is off screen or the tab is hidden.
   ════════════════════════════════════════════════════════════════════ */
(() => {
  'use strict';
  const $ = (s, el = document) => el.querySelector(s);
  const $$ = (s, el = document) => [...el.querySelectorAll(s)];
  const clamp = (v, a, b) => Math.min(b, Math.max(a, v));
  const root = document.documentElement;
  const reduceMQ = matchMedia('(prefers-reduced-motion: reduce)');
  const coarse = matchMedia('(pointer: coarse)').matches;
  const STORE = 'ash-motion';

  // ── SHARED INPUT STATE ────────────────────────────────────────────
  const ptr = { x: -1e4, y: -1e4, vx: 0, vy: 0, speed: 0, active: false };
  addEventListener('pointermove', (e) => {
    if (ptr.active) { ptr.vx += e.clientX - ptr.x; ptr.vy += e.clientY - ptr.y; }
    ptr.x = e.clientX; ptr.y = e.clientY; ptr.active = true;
  }, { passive: true });
  addEventListener('pointerdown', (e) => { ptr.x = e.clientX; ptr.y = e.clientY; ptr.active = true; }, { passive: true });
  document.addEventListener('mouseout', (e) => { if (!e.relatedTarget) ptr.active = false; });
  let lastScroll = scrollY, scrollVel = 0;

  // ── AUDIO ANALYSIS (for effect 5) ─────────────────────────────────
  // Web Audio reads the levels of the <audio> element the player uses.
  // Desktop only: on iOS, routing an <audio> element through Web Audio can
  // stop playback when the screen locks, so phones skip this part.
  const audio = $('#audio');
  let actx = null, analyser = null, bins = null, level = 0;
  function wakeAudio() {
    if (coarse || !enabled) return;
    try {
      actx ??= new AudioContext();
      if (actx.state === 'suspended') actx.resume();
    } catch { actx = null; }
  }
  // Create/resume the AudioContext inside a real user gesture, before the
  // player's own click handler starts playback, so audio is never muted.
  addEventListener('pointerdown', wakeAudio, { capture: true });
  addEventListener('keydown', wakeAudio, { capture: true });
  audio?.addEventListener('play', () => {
    if (!actx || analyser || actx.state !== 'running') return;
    try {
      const src = actx.createMediaElementSource(audio);
      analyser = actx.createAnalyser();
      analyser.fftSize = 128;
      analyser.smoothingTimeConstant = 0.75;
      src.connect(analyser);
      analyser.connect(actx.destination);
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

  // Pause work for elements that are off screen.
  const visible = new WeakSet();
  const io = new IntersectionObserver((entries) => {
    for (const en of entries) en.isIntersecting ? visible.add(en.target) : visible.delete(en.target);
  }, { rootMargin: '100px' });

  // ══ 3 · PARTICLE HEADLINE ═════════════════════════════════════════
  const particles = (() => {
    const h1 = $('.hero-title');
    let canvas, ctx, img, buf32, W, H, dpr, N = 0, P, ink, gold, resizeT;
    const textNode = h1 && [...h1.childNodes].find((n) => n.nodeType === 3 && n.textContent.trim());

    function rgbInt(css) {
      const m = css.match(/\d+(\.\d+)?/g).map(Number);
      return (255 << 24) | (m[2] << 16) | (m[1] << 8) | m[0];  // little-endian ABGR
    }

    function build() {
      const cs = getComputedStyle(h1);
      const hr = h1.getBoundingClientRect();
      const range = document.createRange();
      range.selectNodeContents(textNode);
      const tr = range.getBoundingClientRect();
      W = Math.ceil(hr.width * 1.24); H = Math.ceil(hr.height * 1.6);
      dpr = Math.min(2, devicePixelRatio || 1);
      canvas.width = W * dpr; canvas.height = H * dpr;
      img = ctx.createImageData(canvas.width, canvas.height);
      buf32 = new Uint32Array(img.data.buffer);

      // Rasterize the heading in the same font, then sample its pixels.
      const off = document.createElement('canvas');
      off.width = W; off.height = H;
      const o = off.getContext('2d', { willReadFrequently: true });
      o.font = `${cs.fontStyle} ${cs.fontWeight} ${cs.fontSize} ${cs.fontFamily}`;
      if ('letterSpacing' in o) o.letterSpacing = cs.letterSpacing;
      const text = textNode.textContent.replace(/ /g, ' ');
      const m = o.measureText(text);
      const left = hr.left - hr.width * 0.12, top = hr.top - hr.height * 0.3;
      const baseline = tr.top - top + tr.height / 2 + (m.actualBoundingBoxAscent - m.actualBoundingBoxDescent) / 2;
      o.fillStyle = '#000';
      o.fillText(text, tr.left - left, baseline);
      const data = o.getImageData(0, 0, W, H).data;

      const max = coarse ? 6500 : 9000;
      let gap = 1, pts;   // densest sampling that stays under the particle budget
      do {
        pts = [];
        for (let y = 0; y < H; y += gap) for (let x = 0; x < W; x += gap) {
          if (data[(y * W + x) * 4 + 3] > 140) pts.push(x, y);
        }
        gap++;
      } while (pts.length / 2 > max);

      // P = [homeX, homeY, x, y, vx, vy] per particle. Existing particles
      // keep their positions on rebuild; new ones start scattered and
      // assemble, which doubles as the intro animation.
      const n = pts.length / 2, next = new Float32Array(n * 6);
      for (let i = 0; i < n; i++) {
        const k = i * 6;
        next[k] = pts[i * 2]; next[k + 1] = pts[i * 2 + 1];
        if (P && i < N) { next[k + 2] = P[i * 6 + 2]; next[k + 3] = P[i * 6 + 3]; }
        else { next[k + 2] = Math.random() * W; next[k + 3] = Math.random() * H; }
      }
      P = next; N = n;
    }

    function tick() {
      if (!canvas || !visible.has(h1)) return;
      const cr = canvas.getBoundingClientRect();
      const sx = cr.width / W;  // CSS scale (canvas box vs. buffer)
      const mx = (ptr.x - cr.left) / sx, my = (ptr.y - cr.top) / sx;
      const R = (coarse ? 70 : 110), R2 = R * R;
      const jitter = level * 5;
      buf32.fill(0);
      const s = Math.max(1, Math.round((coarse ? 1.5 : 2) * dpr)), cw = canvas.width, ch = canvas.height;
      for (let i = 0; i < N; i++) {
        const k = i * 6;
        let x = P[k + 2], y = P[k + 3], vx = P[k + 4], vy = P[k + 5];
        if (ptr.active) {
          const dx = x - mx, dy = y - my, d2 = dx * dx + dy * dy;
          if (d2 < R2 && d2 > 0.01) {
            const d = Math.sqrt(d2), f = 1 - d / R;
            vx += (dx / d) * f * 5.5 - (dy / d) * f * 4;   // push out + swirl (vortex)
            vy += (dy / d) * f * 5.5 + (dx / d) * f * 4;
          }
        }
        vx += (P[k] - x) * 0.04 + (jitter ? (Math.random() - 0.5) * jitter : 0);  // spring home
        vy += (P[k + 1] - y) * 0.04 + (jitter ? (Math.random() - 0.5) * jitter : 0);
        vx *= 0.86; vy *= 0.86;
        x += vx; y += vy;
        P[k + 2] = x; P[k + 3] = y; P[k + 4] = vx; P[k + 5] = vy;
        const color = vx * vx + vy * vy > 6 ? gold : ink;  // fast particles glow daffodil
        const px = (x * dpr) | 0, py = (y * dpr) | 0;
        if (px < 0 || py < 0 || px + s >= cw || py + s >= ch) continue;
        for (let a = 0; a < s; a++) {
          const row = (py + a) * cw + px;
          for (let b = 0; b < s; b++) buf32[row + b] = color;
        }
      }
      ctx.putImageData(img, 0, 0);
    }

    function onResize() { clearTimeout(resizeT); resizeT = setTimeout(() => canvas && build(), 150); }

    return {
      async start() {
        if (!h1 || !textNode) return;
        await document.fonts.ready;
        if (!enabled) return;
        ink = rgbInt(getComputedStyle(h1).color);
        gold = rgbInt(getComputedStyle(root).getPropertyValue('--daffodil').trim().replace(/^#(..)(..)(..)$/, (_, r, g, b) => `rgb(${parseInt(r, 16)},${parseInt(g, 16)},${parseInt(b, 16)})`));
        canvas = document.createElement('canvas');
        canvas.className = 'fx-particle-canvas';
        canvas.setAttribute('aria-hidden', 'true');
        ctx = canvas.getContext('2d');
        build();
        h1.append(canvas);
        h1.classList.add('fx-particles');
        io.observe(h1);
        addEventListener('resize', onResize);
      },
      stop() {
        canvas?.remove(); canvas = null; P = null; N = 0;
        h1?.classList.remove('fx-particles');
        h1 && io.unobserve(h1);
        removeEventListener('resize', onResize);
      },
      tick,
    };
  })();

  // ══ 5 · KINETIC VARIABLE TYPE ═════════════════════════════════════
  const kinetic = (() => {
    let split = [];   // { node, sr, vis, el, letters: [{span, w}] }
    function splitHeading(el) {
      for (const node of [...el.childNodes]) {
        if (node.nodeType !== 3 || !node.textContent.trim()) continue;
        const sr = document.createElement('span');
        sr.className = 'sr-only';
        sr.textContent = node.textContent;
        const vis = document.createElement('span');
        vis.className = 'fx-letters';
        vis.setAttribute('aria-hidden', 'true');
        const letters = [];
        for (const part of node.textContent.split(/(\s+)/)) {
          if (!part) continue;
          if (/^\s+$/.test(part)) { vis.append(part); continue; }
          const word = document.createElement('span');
          word.className = 'fx-word';
          for (const ch of part) {
            const span = document.createElement('span');
            span.className = 'fx-letter';
            span.textContent = ch;
            word.append(span);
            letters.push({ span, w: 400 });
          }
          vis.append(word);
        }
        node.replaceWith(sr, vis);
        split.push({ node, sr, vis, el, letters });
        io.observe(el);
      }
    }
    return {
      start() { $$('.section-head h2, .record-title, .new-record-title').forEach(splitHeading); },
      stop() {
        for (const s of split) { s.sr.replaceWith(s.node); s.vis.remove(); io.unobserve(s.el); }
        split = [];
      },
      tick() {
        let idx = 0;
        for (const s of split) {
          if (!visible.has(s.el)) { idx += s.letters.length; continue; }
          for (const L of s.letters) {
            let target = 400;
            if (ptr.active) {
              const r = L.span.getBoundingClientRect();
              const d = Math.hypot(ptr.x - (r.left + r.width / 2), ptr.y - (r.top + r.height / 2));
              const f = Math.max(0, 1 - d / 190);
              target += 500 * f * f;
            }
            target += bin(idx++) * 380;  // each letter listens to its own frequency band
            target = clamp(target, 400, 900);
            L.w += (target - L.w) * 0.25;
            const rounded = Math.round(L.w / 10) * 10;
            if (rounded !== L.shown) { L.span.style.fontWeight = rounded; L.shown = rounded; }
          }
        }
      },
    };
  })();

  // ══ 2 · RGB SPLIT ON HEADINGS (scroll velocity) ═══════════════════
  const rgbScroll = {
    start() {},
    stop() { root.style.removeProperty('--rgb'); },
    tick() {
      const v = clamp(scrollVel * 0.18, -7, 7);
      root.style.setProperty('--rgb', Math.abs(v) < 0.05 ? 0 : v.toFixed(2));
    },
  };

  // ══ 1 + 2 · LIQUID DISTORTION + CHROMATIC ABERRATION (WebGL) ══════
  const liquid = (() => {
    const TARGETS = '.hero-photo img, .record-art, .new-record-art, .video-link img, .press-photos img';
    let canvas, gl, prog, tex, U = {}, current = null, hover = 0, hoverTarget = 0, t0 = performance.now();

    const VERT = `attribute vec2 p; varying vec2 vUv;
      void main(){ vUv = p * 0.5 + 0.5; gl_Position = vec4(p, 0.0, 1.0); }`;
    // The shader warps texture coordinates around the pointer (a ripple
    // ring plus a magnifying "lens"), then samples R, G and B at offsets
    // along the movement direction: liquid glass with a chromatic tear.
    const FRAG = `precision mediump float;
      uniform sampler2D uTex;
      uniform vec2 uMouse, uDir, uScale, uOffset;
      uniform float uTime, uHover, uVel, uAspect;
      varying vec2 vUv;
      vec4 tex(vec2 u){ return texture2D(uTex, clamp(u, 0.0, 1.0) * uScale + uOffset); }
      void main(){
        vec2 d = vUv - uMouse; d.x *= uAspect;
        float dist = length(d);
        vec2 dir = dist > 0.0001 ? d / dist : vec2(0.0);
        dir.x /= uAspect;
        float ripple = sin(dist * 34.0 - uTime * 4.5) * exp(-dist * 7.0) * 0.010;
        float lens = exp(-dist * dist * 26.0) * 0.11;
        vec2 uv = vUv + dir * ripple * uHover - vec2(d.x / uAspect, d.y) * lens * uHover;
        vec2 shift = uDir * uVel * 0.018 * (0.35 + uHover);
        gl_FragColor = vec4(tex(uv + shift).r, tex(uv).g, tex(uv - shift).b, 1.0);
      }`;

    function compile(type, src) {
      const s = gl.createShader(type);
      gl.shaderSource(s, src); gl.compileShader(s);
      if (!gl.getShaderParameter(s, gl.COMPILE_STATUS)) throw new Error(gl.getShaderInfoLog(s));
      return s;
    }

    function setup() {
      canvas = document.createElement('canvas');
      canvas.className = 'fx-liquid';
      canvas.setAttribute('aria-hidden', 'true');
      gl = canvas.getContext('webgl', { premultipliedAlpha: false, antialias: false, alpha: false });
      if (!gl) return false;
      prog = gl.createProgram();
      gl.attachShader(prog, compile(gl.VERTEX_SHADER, VERT));
      gl.attachShader(prog, compile(gl.FRAGMENT_SHADER, FRAG));
      gl.linkProgram(prog);
      if (!gl.getProgramParameter(prog, gl.LINK_STATUS)) return false;
      gl.useProgram(prog);
      const buf = gl.createBuffer();
      gl.bindBuffer(gl.ARRAY_BUFFER, buf);
      gl.bufferData(gl.ARRAY_BUFFER, new Float32Array([-1, -1, 1, -1, -1, 1, 1, 1]), gl.STATIC_DRAW);
      const loc = gl.getAttribLocation(prog, 'p');
      gl.enableVertexAttribArray(loc);
      gl.vertexAttribPointer(loc, 2, gl.FLOAT, false, 0, 0);
      for (const n of ['uTex', 'uMouse', 'uDir', 'uScale', 'uOffset', 'uTime', 'uHover', 'uVel', 'uAspect']) U[n] = gl.getUniformLocation(prog, n);
      tex = gl.createTexture();
      gl.bindTexture(gl.TEXTURE_2D, tex);
      // Non-power-of-two textures in WebGL 1 need clamp + no mipmaps.
      gl.texParameteri(gl.TEXTURE_2D, gl.TEXTURE_WRAP_S, gl.CLAMP_TO_EDGE);
      gl.texParameteri(gl.TEXTURE_2D, gl.TEXTURE_WRAP_T, gl.CLAMP_TO_EDGE);
      gl.texParameteri(gl.TEXTURE_2D, gl.TEXTURE_MIN_FILTER, gl.LINEAR);
      gl.texParameteri(gl.TEXTURE_2D, gl.TEXTURE_MAG_FILTER, gl.LINEAR);
      gl.pixelStorei(gl.UNPACK_FLIP_Y_WEBGL, true);
      document.body.append(canvas);
      return true;
    }

    function activate(el) {
      if (!el.complete || !el.naturalWidth) return;
      try {
        gl.bindTexture(gl.TEXTURE_2D, tex);
        gl.texImage2D(gl.TEXTURE_2D, 0, gl.RGB, gl.RGB, gl.UNSIGNED_BYTE, el);
      } catch { return; }
      current = el; hoverTarget = 1;
      const cs = getComputedStyle(el);
      const radius = cs.borderRadius !== '0px' ? cs.borderRadius : getComputedStyle(el.parentElement).borderRadius;
      canvas.style.borderRadius = radius;
      // object-fit: cover crop, honoring object-position (e.g. 30% on phones).
      const [px, py] = cs.objectPosition.split(' ').map((v) => (v.endsWith('%') ? parseFloat(v) / 100 : 0.5));
      current.fx = { px, py: py ?? 0.5 };
    }

    function over(e) {
      const el = e.target.closest?.(TARGETS);
      if (el && el !== current) activate(el);
      else if (el === current) hoverTarget = 1;
    }
    function out(e) {
      if (current && e.target === current && !current.contains(e.relatedTarget)) hoverTarget = 0;
    }

    return {
      start() {
        try { if (!setup()) { canvas?.remove(); canvas = null; return; } } catch { canvas?.remove(); canvas = null; return; }
        document.addEventListener('pointerover', over);
        document.addEventListener('pointerout', out);
      },
      stop() {
        document.removeEventListener('pointerover', over);
        document.removeEventListener('pointerout', out);
        gl?.getExtension('WEBGL_lose_context')?.loseContext();
        canvas?.remove(); canvas = null; gl = null; current = null; hover = 0;
      },
      tick(now) {
        if (!gl || !current) return;
        const r = current.getBoundingClientRect();
        // Scrolling moves images out from under a still pointer without
        // firing pointerout, so check containment every frame.
        const inside = ptr.active && ptr.x >= r.left && ptr.x <= r.right && ptr.y >= r.top && ptr.y <= r.bottom;
        if (!inside) hoverTarget = 0;
        hover += (hoverTarget - hover) * 0.12;
        const vel = clamp(ptr.speed / 60 + Math.abs(scrollVel) / 60, 0, 1);
        const offscreen = r.width < 2 || r.bottom < 0 || r.top > innerHeight;
        if (offscreen || (hoverTarget === 0 && hover < 0.02)) {
          canvas.classList.remove('on'); current = null; hover = 0; return;
        }
        const dpr = Math.min(1.5, devicePixelRatio || 1);
        const w = Math.round(r.width * dpr), h = Math.round(r.height * dpr);
        if (canvas.width !== w || canvas.height !== h) { canvas.width = w; canvas.height = h; gl.viewport(0, 0, w, h); }
        Object.assign(canvas.style, { left: r.left + 'px', top: r.top + 'px', width: r.width + 'px', height: r.height + 'px' });
        canvas.classList.add('on');

        const boxAR = r.width / r.height, imgAR = current.naturalWidth / current.naturalHeight;
        let sx = 1, sy = 1;
        if (imgAR > boxAR) sx = boxAR / imgAR; else sy = imgAR / boxAR;
        const { px, py } = current.fx;
        gl.uniform2f(U.uScale, sx, sy);
        gl.uniform2f(U.uOffset, (1 - sx) * px, (1 - sy) * (1 - py));
        gl.uniform2f(U.uMouse, (ptr.x - r.left) / r.width, 1 - (ptr.y - r.top) / r.height);
        const len = Math.hypot(ptr.vx, ptr.vy);
        if (len > 0.5) gl.uniform2f(U.uDir, ptr.vx / len, -ptr.vy / len);
        else if (Math.abs(scrollVel) > 0.5) gl.uniform2f(U.uDir, 0, Math.sign(scrollVel));
        gl.uniform1f(U.uVel, vel);
        gl.uniform1f(U.uHover, hover);
        gl.uniform1f(U.uAspect, boxAR);
        gl.uniform1f(U.uTime, (now - t0) / 1000);
        gl.drawArrays(gl.TRIANGLE_STRIP, 0, 4);
      },
    };
  })();

  // ══ 4 · SCROLL-TIED 3D FLYTHROUGH ════════════════════════════════
  const crate = (() => {
    const GAP = 1500;
    let skip, wrap, scene, stations = [], dots = [];
    const smoother = (t) => t * t * t * (t * (t * 6 - 15) + 10);

    return {
      start() {
        const records = $$('.record');
        const hero = $('.hero');
        if (records.length < 2 || !hero) return;
        const spread = Math.min(innerWidth * 0.22, 320);

        skip = document.createElement('a');
        skip.className = 'fx-skip';
        skip.href = '#listen';
        skip.textContent = 'Skip the 3D tour of the records';

        wrap = document.createElement('div');
        wrap.className = 'fx-crate';
        wrap.setAttribute('aria-hidden', 'true');   // repeats the Listen section; decorative
        wrap.style.height = `${(records.length + 1) * 100}vh`;
        const stage = document.createElement('div');
        stage.className = 'fx-stage';
        scene = document.createElement('div');
        scene.className = 'fx-scene';

        records.forEach((rec, i) => {
          const fig = document.createElement('figure');
          fig.className = 'fx-station';
          const x = i === 0 ? 0 : (i % 2 ? spread : -spread);
          const rot = i === 0 ? 0 : (i % 2 ? -16 : 16);
          fig.style.transform = `translate3d(${x}px, 0, ${-i * GAP}px) rotateY(${rot}deg)`;
          const img = document.createElement('img');
          img.src = $('.record-art', rec).currentSrc || $('.record-art', rec).src;
          img.alt = '';
          const cap = document.createElement('figcaption');
          const facts = $$('.record-facts dd', rec).map((d) => d.textContent.trim());
          cap.innerHTML = '<p class="fx-st-title"></p><p class="fx-st-meta"></p>';
          cap.firstChild.textContent = $('.record-title', rec).textContent.trim();
          cap.lastChild.textContent = `${facts[0]} · ${facts[1]} · ${facts[2]}`;
          fig.append(img, cap);
          scene.append(fig);
          stations.push({ fig, cap, x, z: -i * GAP });
        });
        // Daffodil "dust" for depth cues while flying.
        for (let i = 0; i < 70; i++) {
          const d = document.createElement('i');
          d.className = 'fx-dust';
          d.style.transform = `translate3d(${(Math.random() - 0.5) * 2400}px, ${(Math.random() - 0.5) * 1400}px, ${-Math.random() * GAP * records.length + 600}px) rotate(${Math.random() * 90}deg)`;
          scene.append(d);
        }
        const prog = document.createElement('div');
        prog.className = 'fx-progress';
        dots = records.map(() => prog.appendChild(document.createElement('i')));
        stage.append(scene, prog);
        wrap.append(stage);
        hero.after(skip, wrap);
        io.observe(wrap);
      },
      stop() {
        skip?.remove(); wrap?.remove();
        skip = wrap = scene = null; stations = []; dots = [];
      },
      tick() {
        if (!wrap || !visible.has(wrap)) return;
        const n = stations.length;
        const total = wrap.offsetHeight - innerHeight;
        const raw = clamp(-wrap.getBoundingClientRect().top / total, 0, 1) * n;
        // Hold still for the first and last quarter of each segment, so
        // the camera visibly "stops" at every record.
        const s = clamp(raw - 0.5, 0, n - 1);
        const seg = Math.min(n - 2, Math.floor(s)), f = s - seg;
        const e = seg + smoother(clamp((f - 0.25) / 0.5, 0, 1));
        const a = stations[Math.floor(e)], b = stations[Math.min(n - 1, Math.floor(e) + 1)];
        const t = e - Math.floor(e);
        const camX = a.x + (b.x - a.x) * t;
        const camZ = e * GAP;
        const tilt = ptr.active ? (ptr.x / innerWidth - 0.5) * 6 : 0;
        scene.style.transform = `rotateY(${tilt}deg) translate3d(${-camX}px, 0, ${camZ}px)`;
        stations.forEach((st, i) => {
          const rel = st.z + camZ;   // > 0: behind the camera
          st.fig.style.opacity = rel > 500 ? 0 : rel > 0 ? 1 - rel / 500 : clamp(1 + rel / (GAP * 2.2), 0, 1);
          st.cap.style.opacity = clamp(1 - Math.abs(rel) / 350, 0, 1);
          dots[i].classList.toggle('on', Math.round(e) === i);
        });
      },
    };
  })();

  // ── MAIN LOOP ─────────────────────────────────────────────────────
  // Order matters: the flythrough copies record titles, so it must start
  // before kinetic type splits those titles into letters.
  const modules = [rgbScroll, crate, kinetic, particles, liquid];
  let enabled = false, raf = 0;
  function frame(now) {
    raf = requestAnimationFrame(frame);
    if (document.hidden) return;
    const dy = scrollY - lastScroll; lastScroll = scrollY;
    scrollVel = scrollVel * 0.8 + dy * 0.2;
    ptr.speed = Math.hypot(ptr.vx, ptr.vy);
    readAudio();
    for (const m of modules) { try { m.tick(now); } catch (err) { console.warn('effect disabled:', err); m.stop(); m.tick = () => {}; } }
    ptr.vx *= 0.8; ptr.vy *= 0.8;
  }

  function setEnabled(on, remember) {
    if (on === enabled) return;
    enabled = on;
    root.classList.toggle('fx', on);
    toggle.setAttribute('aria-pressed', String(on));
    toggle.title = on ? 'Motion effects: on (select to turn off)' : 'Motion effects: off (select to turn on)';
    if (remember) { try { localStorage.setItem(STORE, on ? 'on' : 'off'); } catch {} }
    if (on) {
      for (const m of modules) { try { m.start(); } catch (err) { console.warn(err); } }
      lastScroll = scrollY;
      raf = requestAnimationFrame(frame);
    } else {
      cancelAnimationFrame(raf);
      for (const m of modules) { try { m.stop(); } catch {} }
    }
  }

  // The Motion button: always visible, in the masthead.
  const toggle = document.createElement('button');
  toggle.type = 'button';
  toggle.className = 'fx-toggle';
  toggle.setAttribute('aria-label', 'Motion effects');
  toggle.setAttribute('aria-pressed', 'false');
  toggle.innerHTML = '<svg aria-hidden="true" viewBox="0 0 24 24" width="20" height="20" fill="currentColor"><path d="M12 2l1.8 5.2L19 9l-5.2 1.8L12 16l-1.8-5.2L5 9l5.2-1.8zM19 14l.9 2.6 2.6.9-2.6.9L19 21l-.9-2.6-2.6-.9 2.6-.9zM5 15l.7 1.8 1.8.7-1.8.7L5 20l-.7-1.8-1.8-.7 1.8-.7z"/></svg>';
  toggle.addEventListener('click', () => setEnabled(!enabled, true));
  $('.masthead')?.append(toggle);

  let saved = null;
  try { saved = localStorage.getItem(STORE); } catch {}
  setEnabled(saved ? saved === 'on' : !reduceMQ.matches, false);
  // Follow the OS setting live, unless the visitor made their own choice.
  reduceMQ.addEventListener?.('change', (e) => {
    let s = null; try { s = localStorage.getItem(STORE); } catch {}
    if (!s) setEnabled(!e.matches, false);
  });
})();
