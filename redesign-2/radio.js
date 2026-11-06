/* ════════════════════════════════════════════════════════════════════
   NIGHT RADIO: concept behavior (decoration only; the page is complete
   without it). Shared player/video/form behavior lives in
   redesign/redesign.js.

   1. Tuner needle: glides along the masthead dial to the section in view,
      interpolating between sections as you scroll (a live progress bar).
   2. Signal meter: the needle in the player swings with the music's
      loudness (Web Audio; desktop only, because routing <audio> through
      Web Audio can stop playback on iOS when the screen locks).

   One rAF loop; reads (layout) first, then writes (transform only).
   Reduced motion: the needle jumps instead of gliding; the meter rests.
   ════════════════════════════════════════════════════════════════════ */
(() => {
  'use strict';
  const $ = (s) => document.querySelector(s);
  const needle = $('.tuner-needle');
  const tuner = $('.tuner');
  const meter = $('#meter-needle');
  const audio = $('#audio');
  if (!needle || !tuner) return;

  const reduce = matchMedia('(prefers-reduced-motion: reduce)');
  const coarse = matchMedia('(pointer: coarse)').matches;
  const links = [...tuner.querySelectorAll('a[href^="#"]')];
  const sections = links.map((a) => document.querySelector(a.getAttribute('href')));

  // Cached geometry, refreshed on resize (no layout reads in normal frames).
  let linkX = [], secTop = [], dirty = true;
  addEventListener('resize', () => { dirty = true; }, { passive: true });
  new ResizeObserver(() => { dirty = true; }).observe(document.body);
  function measure() {
    const t = tuner.getBoundingClientRect();
    linkX = links.map((a) => { const r = a.getBoundingClientRect(); return r.left - t.left + r.width / 2; });
    secTop = sections.map((s) => (s ? s.getBoundingClientRect().top + scrollY : Infinity));
    dirty = false;
  }

  // Web Audio level for the meter.
  let actx = null, analyser = null, bins = null, level = 0;
  function wake() {
    if (coarse) return;
    try { actx ??= new AudioContext(); if (actx.state === 'suspended') actx.resume(); } catch { actx = null; }
  }
  addEventListener('pointerdown', wake, { capture: true, passive: true });
  addEventListener('keydown', wake, { capture: true, passive: true });
  audio?.addEventListener('play', () => {
    if (!actx || analyser || actx.state !== 'running') return;
    try {
      const src = actx.createMediaElementSource(audio);
      analyser = actx.createAnalyser(); analyser.fftSize = 128; analyser.smoothingTimeConstant = 0.8;
      src.connect(analyser); analyser.connect(actx.destination);
      bins = new Uint8Array(analyser.frequencyBinCount);
    } catch { analyser = null; }
  });

  let x = 0, lastNeedle = '', lastMeter = '';
  function frame() {
    requestAnimationFrame(frame);
    if (document.hidden) return;
    // READ
    if (dirty) measure();
    const probe = scrollY + innerHeight * 0.4;
    let target = -40;   // parked left of the dial while in the hero
    for (let i = 0; i < secTop.length; i++) {
      if (probe >= secTop[i]) {
        const next = secTop[i + 1] ?? Infinity;
        const f = next === Infinity ? 0 : Math.min(1, (probe - secTop[i]) / (next - secTop[i]));
        target = linkX[i] + ((linkX[i + 1] ?? linkX[i]) - linkX[i]) * f;
      }
    }
    if (analyser && !audio.paused) {
      analyser.getByteFrequencyData(bins);
      let sum = 0; for (let i = 2; i < 30; i++) sum += bins[i];
      level = level * 0.75 + (sum / (28 * 255)) * 0.25;
    } else level *= 0.9;
    // WRITE
    x = reduce.matches ? target : x + (target - x) * 0.18;
    const tf = `translateX(${x.toFixed(1)}px)`;
    if (tf !== lastNeedle) { needle.style.transform = tf; needle.style.opacity = target < 0 ? '0' : '1'; lastNeedle = tf; }
    if (meter) {
      const deg = reduce.matches ? -50 : -50 + Math.min(1, level * 1.6) * 100;
      const mt = `rotate(${deg.toFixed(1)}deg)`;
      if (mt !== lastMeter) { meter.style.transform = mt; lastMeter = mt; }
    }
  }
  requestAnimationFrame(frame);
})();
