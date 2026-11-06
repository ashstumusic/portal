/* ════════════════════════════════════════════════════════════════════
   ASH STU REDESIGN: progressive enhancement only
   ────────────────────────────────────────────────────────────────────
   All content is already in the static HTML (built by
   scripts/build_redesign.py). This script renders NOTHING. It only:
   • turns song links (<a href="...mp3" data-play="r:t">) into an
     in-page player that keeps playing while you browse,
   • turns video links (<a href="...mp4" data-video>) into a <dialog>
     viewer,
   • adds the Copy button and the "you are here" nav marker.
   With JavaScript off, every link still works: it opens the file.
   ════════════════════════════════════════════════════════════════════ */
(() => {
  'use strict';
  const $ = (sel, el = document) => el.querySelector(sel);
  const $$ = (sel, el = document) => [...el.querySelectorAll(sel)];

  const fmt = (s) => {
    if (!isFinite(s)) return '0:00';
    return `${Math.floor(s / 60)}:${String(Math.floor(s % 60)).padStart(2, '0')}`;
  };

  // ── BUILD THE QUEUE FROM THE PAGE ─────────────────────────────────
  // releases[r] = { name, art, tracks: [{ title, src, link }] }
  const releases = [];
  $$('a.track[data-play]').forEach((a) => {
    const [r, t] = a.dataset.play.split(':').map(Number);
    const record = a.closest('.record');
    releases[r] ??= {
      name: $('.record-title', record).textContent.trim(),
      art: $('.record-art', record).currentSrc || $('.record-art', record).src,
      tracks: [],
    };
    releases[r].tracks[t] = { title: a.textContent.trim(), src: a.href, link: a };
  });

  // ── PLAYER ────────────────────────────────────────────────────────
  const audio = $('#audio');
  const player = $('#player');
  const seek = $('#seek');
  const toggleBtn = $('#toggle');
  const PATH_PLAY = 'M7 4.5v15l12-7.5z';
  const PATH_PAUSE = 'M7 5h4v14H7zM13 5h4v14h-4z';
  let current = { r: -1, t: -1 };
  let lastTrigger = null;
  let seeking = false;

  function play(r, t) {
    const rel = releases[r];
    const trk = rel && rel.tracks[t];
    if (!trk) return;
    current = { r, t };
    audio.src = trk.src;
    audio.play().catch(() => {});
    $('#player-title').textContent = trk.title;
    $('#player-release').textContent = rel.name;
    $('#player-art').src = rel.art;
    $('#player-art').alt = `Cover of ${rel.name}`;
    if (player.hidden) {
      player.hidden = false;
      document.body.classList.add('has-player');
    }
    markCurrent();
    if ('mediaSession' in navigator) {
      navigator.mediaSession.metadata = new MediaMetadata({
        title: trk.title, artist: 'Ash Stu', album: rel.name,
        artwork: [{ src: rel.art, sizes: '512x512', type: 'image/webp' }],
      });
    }
  }

  // The playing song is marked with aria-current (for screen readers
  // and AI agents reading the live DOM) and styled from that attribute.
  function markCurrent() {
    $$('a.track[aria-current]').forEach((a) => a.removeAttribute('aria-current'));
    const trk = releases[current.r]?.tracks[current.t];
    if (trk) trk.link.setAttribute('aria-current', 'true');
  }

  function step(dir) {
    if (current.r < 0) return;
    if (dir < 0 && audio.currentTime > 3) { audio.currentTime = 0; return; }
    const t = current.t + dir;
    if (t >= 0 && t < releases[current.r].tracks.length) play(current.r, t);
    else if (dir > 0) setPlaying(false);
  }

  function setPlaying(on) {
    document.body.classList.toggle('is-playing', on);
    toggleBtn.setAttribute('aria-label', on ? 'Pause' : 'Play');
    $('#toggle-icon').setAttribute('d', on ? PATH_PAUSE : PATH_PLAY);
  }

  function closePlayer() {
    audio.pause();
    audio.removeAttribute('src');
    audio.load();
    player.hidden = true;
    document.body.classList.remove('has-player', 'is-playing');
    current = { r: -1, t: -1 };
    markCurrent();
    (lastTrigger && document.contains(lastTrigger) ? lastTrigger : $('#main')).focus();
  }

  function updateSeekUI(time) {
    seek.style.setProperty('--pct', `${seek.value}%`);
    $('#time-cur').textContent = fmt(time);
    seek.setAttribute('aria-valuetext', `${fmt(time)} of ${fmt(audio.duration)}`);
  }

  audio.addEventListener('play', () => setPlaying(true));
  audio.addEventListener('pause', () => setPlaying(false));
  audio.addEventListener('ended', () => step(1));
  audio.addEventListener('error', () => {
    if (!audio.getAttribute('src')) return;
    $('#player-title').textContent = 'This song could not be loaded';
    setPlaying(false);
  });
  audio.addEventListener('loadedmetadata', () => { $('#time-dur').textContent = fmt(audio.duration); });
  audio.addEventListener('timeupdate', () => {
    if (seeking) return;
    seek.value = audio.duration ? (audio.currentTime / audio.duration) * 100 : 0;
    updateSeekUI(audio.currentTime);
  });
  seek.addEventListener('input', () => {
    seeking = true;
    updateSeekUI((seek.value / 100) * (audio.duration || 0));
  });
  seek.addEventListener('change', () => {
    if (audio.duration) audio.currentTime = (seek.value / 100) * audio.duration;
    seeking = false;
  });

  toggleBtn.addEventListener('click', () => (audio.paused ? audio.play() : audio.pause()));
  $('#prev').addEventListener('click', () => step(-1));
  $('#next').addEventListener('click', () => step(1));
  $('#close-player').addEventListener('click', closePlayer);

  if ('mediaSession' in navigator) {
    navigator.mediaSession.setActionHandler('play', () => audio.play());
    navigator.mediaSession.setActionHandler('pause', () => audio.pause());
    navigator.mediaSession.setActionHandler('previoustrack', () => step(-1));
    navigator.mediaSession.setActionHandler('nexttrack', () => step(1));
  }

  // ── VIDEO DIALOG ──────────────────────────────────────────────────
  const dialog = $('#video-dialog');
  const video = $('#video');
  function openVideo(link) {
    const card = link.closest('.video');
    const yt = $('.video-yt-link', card);
    audio.pause();
    $('#video-title').textContent = $('.video-name', card).textContent.trim();
    $('#video-yt').hidden = !yt;
    if (yt) $('#video-yt').href = yt.href;
    video.poster = $('img', link).currentSrc || $('img', link).src;
    video.src = link.href;
    dialog.showModal();
    video.play().catch(() => {});
  }
  $('#video-close').addEventListener('click', () => dialog.close());
  dialog.addEventListener('click', (e) => { if (e.target === dialog) dialog.close(); });
  dialog.addEventListener('close', () => {
    video.pause();
    video.removeAttribute('src');
    video.load();
  });

  // ── ONE CLICK HANDLER FOR EVERY ENHANCED LINK ─────────────────────
  // Modified clicks (Ctrl/Cmd/Shift, middle button) are left alone, so
  // "open in new tab" and "save link as" keep working.
  document.addEventListener('click', (e) => {
    if (e.defaultPrevented || e.button !== 0 || e.metaKey || e.ctrlKey || e.shiftKey || e.altKey) return;
    const playLink = e.target.closest('a[data-play]');
    const videoLink = e.target.closest('a[data-video]');
    if (playLink) {
      e.preventDefault();
      lastTrigger = playLink;
      const [r, t] = playLink.dataset.play.split(':').map(Number);
      const isTrack = playLink.classList.contains('track');
      if (isTrack && r === current.r && t === current.t) audio.paused ? audio.play() : audio.pause();
      else play(r, t);
    } else if (videoLink) {
      e.preventDefault();
      openVideo(videoLink);
    }
  });

  // ── COPY EMAIL (button only exists when JS can make it work) ──────
  const copyBtn = $('#copy-email');
  if (copyBtn && navigator.clipboard) {
    copyBtn.hidden = false;
    copyBtn.addEventListener('click', async () => {
      const status = $('#copy-status');
      const address = $('#email-address').textContent.trim();
      try {
        await navigator.clipboard.writeText(address);
        status.textContent = `Copied ${address} to the clipboard.`;
      } catch {
        status.textContent = 'Could not copy automatically. Select the address above instead.';
      }
    });
  }

  // ── NAV: "YOU ARE HERE" ───────────────────────────────────────────
  const navLinks = $$('.nav-list a');
  if ('IntersectionObserver' in window) {
    const io = new IntersectionObserver((entries) => {
      for (const en of entries) {
        if (!en.isIntersecting) continue;
        for (const a of navLinks) {
          if (a.getAttribute('href') === `#${en.target.id}`) a.setAttribute('aria-current', 'true');
          else a.removeAttribute('aria-current');
        }
      }
    }, { rootMargin: '-45% 0px -50% 0px' });
    [$('#top'), ...navLinks.map((a) => $(a.getAttribute('href')))].forEach((s) => s && io.observe(s));
  }
})();
