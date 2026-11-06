/* ════════════════════════════════════════════════════════════════════
   ASH STU · "GOLDEN HOUR" REDESIGN: behavior
   ────────────────────────────────────────────────────────────────────
   Principles:
   • Native elements first (<button>, <dialog>, <input type=range>): they
     come with keyboard and screen-reader support for free.
   • Content comes from the same releases.json / videos.json the live
     site uses, so adding a folder to Audio/ still "just works".
   • Never move focus unless the visitor asked for something to open or
     close. The page doesn't jump around under anyone's cursor.
   ════════════════════════════════════════════════════════════════════ */
(() => {
  'use strict';

  const ROOT = '../';  // the prototype lives in /redesign; assets in the project root
  const $ = (sel, el = document) => el.querySelector(sel);

  // Paths contain spaces, commas and apostrophes: encode each segment.
  const url = (path) => ROOT + path.split('/').map(encodeURIComponent).join('/');

  // Tiny DOM builder. Always uses textContent, never innerHTML, so a
  // song title can never inject markup.
  function h(tag, attrs = {}, ...children) {
    const el = document.createElement(tag);
    for (const [k, v] of Object.entries(attrs)) {
      if (v == null || v === false) continue;
      if (k === 'class') el.className = v;
      else if (k === 'text') el.textContent = v;
      else if (k.startsWith('data-') || k.startsWith('aria-') || ['type', 'href', 'src', 'alt', 'width', 'height', 'loading', 'role'].includes(k)) el.setAttribute(k, v);
      else el[k] = v;
    }
    for (const c of children) if (c != null) el.append(c);
    return el;
  }
  const svg = (markup) => {
    const t = document.createElement('template');
    t.innerHTML = markup.trim();  // static, author-written icons only
    return t.content.firstChild;
  };
  const ICON_PLAY = '<svg aria-hidden="true" viewBox="0 0 24 24" width="14" height="14"><path d="M7 4.5v15l12-7.5z" fill="currentColor"/></svg>';
  const PATH_PLAY = 'M7 4.5v15l12-7.5z';
  const PATH_PAUSE = 'M7 5h4v14H7zM13 5h4v14h-4z';

  const fmt = (s) => {
    if (!isFinite(s)) return '0:00';
    const m = Math.floor(s / 60);
    return `${m}:${String(Math.floor(s % 60)).padStart(2, '0')}`;
  };
  const pad = (n) => String(n).padStart(2, '0');

  // ── STATE ──────────────────────────────────────────────────────────
  let releases = [];
  let current = { r: -1, t: -1 };
  let lastTrigger = null;  // where focus goes back to when the player closes

  const audio = $('#audio');
  const player = $('#player');
  const seek = $('#seek');
  const toggleBtn = $('#toggle');

  // ── RENDER: RECORDS ────────────────────────────────────────────────
  function renderRecords() {
    const wrap = $('#records');
    wrap.replaceChildren();
    releases.forEach((rel, r) => {
      const count = rel.tracks.length;
      const tracks = h('ol', { class: 'tracks', 'aria-label': `${rel.name} tracklist` });
      rel.tracks.forEach((trk, t) => {
        tracks.append(h('li', {},
          h('button', { type: 'button', class: 'track', 'data-r': r, 'data-t': t },
            h('span', { class: 'track-num', text: pad(t + 1) }),
            h('span', { class: 'track-title', text: trk.title }),
            h('span', { class: 'track-state' },
              svg(ICON_PLAY),
              // Animated "levels": shown on the playing row (see CSS).
              h('span', { class: 'levels', 'aria-hidden': 'true' }, h('i'), h('i'), h('i'))
            )
          )
        ));
      });

      const links = h('p', { class: 'record-links' });
      if (rel.apple) links.append(h('a', { href: rel.apple, text: 'Apple Music' }));
      if (rel.spotify) links.append(h('a', { href: rel.spotify, text: 'Spotify' }));

      wrap.append(h('article', { class: 'record', 'aria-labelledby': `rec-${r}` },
        // alt="" because the title is right beside it: a screen reader
        // shouldn't hear "Only a Baby, Vol. 2" twice in a row.
        h('img', { class: 'record-art', src: url(rel.art), alt: '', width: 352, height: 352, loading: r === 0 ? 'eager' : 'lazy' }),
        h('div', { class: 'record-body' },
          h('p', { class: 'kicker', text: rel.type }),
          h('h3', { class: 'record-title', id: `rec-${r}`, text: rel.name }),
          h('p', { class: 'record-meta', text: `${count} ${count === 1 ? 'song' : 'songs'}` }),
          h('div', { class: 'record-actions' },
            // Secondary style on purpose: the hero keeps the only solid
            // button, so there's always one obvious first move.
            h('button', { type: 'button', class: 'btn btn-secondary', 'data-play-release': r },
              svg(ICON_PLAY), h('span', { text: count === 1 ? 'Play' : 'Play all' }),
              h('span', { class: 'sr-only', text: ` ${rel.name}` })
            ),
            links
          ),
          tracks
        )
      ));
    });
  }

  // The hero card always shows the newest release (releases[0]), so
  // publishing a new album updates the front page automatically.
  function renderHero() {
    const rel = releases[0];
    if (!rel) return;
    const card = $('#new-record');
    $('.new-record-art', card).src = url(rel.art);
    $('.new-record-title', card).textContent = rel.name;
    $('.kicker', card).lastChild.textContent = `New ${rel.type.toLowerCase()}`;
    $('.btn-primary span', card).textContent = rel.tracks.length === 1 ? 'Play the song' : `Play the ${rel.type.toLowerCase()}`;
    const apple = $('[data-link="apple"]', card), spotify = $('[data-link="spotify"]', card);
    if (rel.apple) apple.href = rel.apple;
    if (rel.spotify) spotify.href = rel.spotify;
  }

  // ── RENDER: VIDEOS ─────────────────────────────────────────────────
  let videos = [];
  function renderVideos() {
    const list = $('#videos');
    list.replaceChildren(...videos.map((v, i) => h('li', {},
      h('button', { type: 'button', class: 'video-card', 'data-v': i },
        h('span', { class: 'video-thumb' },
          h('img', { src: url(v.thumb), alt: '', width: 640, height: 360, loading: 'lazy' }),
          h('span', { class: 'video-play', 'aria-hidden': 'true' }, svg(ICON_PLAY), 'Play')
        ),
        // The button's accessible name is just the title + "music video".
        h('span', { class: 'video-name', text: v.title }),
        h('span', { class: 'sr-only', text: ', music video' })
      )
    )));
  }

  // ── PLAYER ─────────────────────────────────────────────────────────
  function play(r, t) {
    const rel = releases[r];
    const trk = rel && rel.tracks[t];
    if (!trk) return;
    current = { r, t };
    audio.src = url(trk.file);
    audio.play().catch(() => {});  // autoplay errors surface via 'error'

    $('#player-title').textContent = trk.title;
    $('#player-release').textContent = rel.name;
    $('#player-art').src = url(rel.art);
    if (player.hidden) {
      player.hidden = false;
      document.body.classList.add('has-player');
    }
    markCurrent();

    // Lock screen / headphone buttons / car stereo controls.
    if ('mediaSession' in navigator) {
      navigator.mediaSession.metadata = new MediaMetadata({
        title: trk.title, artist: 'Ash Stu', album: rel.name,
        artwork: [{ src: new URL(url(rel.art), location.href).href, sizes: '512x512', type: 'image/webp' }],
      });
    }
  }

  function markCurrent() {
    document.querySelectorAll('.track[aria-current]').forEach((b) => b.removeAttribute('aria-current'));
    const btn = $(`.track[data-r="${current.r}"][data-t="${current.t}"]`);
    if (btn) btn.setAttribute('aria-current', 'true');
  }

  function step(dir) {
    if (current.r < 0) return;
    // "Previous" restarts the song if you're more than 3s in; that's
    // the convention every music app trained people to expect.
    if (dir < 0 && audio.currentTime > 3) { audio.currentTime = 0; return; }
    const tracks = releases[current.r].tracks;
    const t = current.t + dir;
    if (t >= 0 && t < tracks.length) play(current.r, t);
    else if (dir > 0) setPlaying(false);  // end of the record: stop, don't jump albums
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
    // The close button just vanished: hand focus back to whatever started
    // the music instead of dropping it on <body>.
    (lastTrigger && document.contains(lastTrigger) ? lastTrigger : $('#main')).focus();
  }

  audio.addEventListener('play', () => setPlaying(true));
  audio.addEventListener('pause', () => setPlaying(false));
  audio.addEventListener('ended', () => step(1));
  audio.addEventListener('error', () => {
    if (!audio.getAttribute('src')) return;
    $('#player-title').textContent = 'Couldn’t load this song';
    setPlaying(false);
  });
  audio.addEventListener('loadedmetadata', () => { $('#time-dur').textContent = fmt(audio.duration); });
  audio.addEventListener('timeupdate', () => {
    if (seeking) return;
    const pct = audio.duration ? (audio.currentTime / audio.duration) * 100 : 0;
    seek.value = pct;
    updateSeekUI(audio.currentTime);
  });

  let seeking = false;
  function updateSeekUI(time) {
    seek.style.setProperty('--pct', `${seek.value}%`);
    $('#time-cur').textContent = fmt(time);
    // Screen readers announce "1:23 of 3:40", not "37.7".
    seek.setAttribute('aria-valuetext', `${fmt(time)} of ${fmt(audio.duration)}`);
  }
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

  // One delegated listener for every play button on the page.
  document.addEventListener('click', (e) => {
    const trackBtn = e.target.closest('.track');
    const relBtn = e.target.closest('[data-play-release]');
    const vidBtn = e.target.closest('.video-card');
    if (trackBtn) {
      lastTrigger = trackBtn;
      const r = +trackBtn.dataset.r, t = +trackBtn.dataset.t;
      // Clicking the song that's already loaded toggles it instead of
      // restarting it from zero.
      if (r === current.r && t === current.t) audio.paused ? audio.play() : audio.pause();
      else play(r, t);
    } else if (relBtn) {
      lastTrigger = relBtn;
      play(+relBtn.dataset.playRelease, 0);
    } else if (vidBtn) {
      openVideo(+vidBtn.dataset.v);
    }
  });

  // ── VIDEO DIALOG ───────────────────────────────────────────────────
  const dialog = $('#video-dialog');
  const video = $('#video');
  function openVideo(i) {
    const v = videos[i];
    if (!v) return;
    audio.pause();  // never two soundtracks at once
    $('#video-title').textContent = v.title;
    const yt = $('#video-yt');
    yt.hidden = !v.youtube;
    if (v.youtube) yt.href = v.youtube;
    video.src = url(v.file);
    video.poster = url(v.thumb);
    dialog.showModal();
    video.play().catch(() => {});
  }
  $('#video-close').addEventListener('click', () => dialog.close());
  // Click on the dimmed backdrop (outside the dialog box) closes it too.
  dialog.addEventListener('click', (e) => { if (e.target === dialog) dialog.close(); });
  dialog.addEventListener('close', () => {
    video.pause();
    video.removeAttribute('src');
    video.load();
  });

  // ── COPY EMAIL ─────────────────────────────────────────────────────
  const copyBtn = $('#copy-email');
  copyBtn.addEventListener('click', async () => {
    const status = $('#copy-status');
    try {
      await navigator.clipboard.writeText(copyBtn.dataset.email);
      status.textContent = 'Copied. Paste it into any email app.';
    } catch {
      status.textContent = 'Couldn’t copy automatically. Select the address above instead.';
    }
  });

  // ── NAV: "YOU ARE HERE" ────────────────────────────────────────────
  // Marks the nav link for the section in view. Orientation lowers
  // cognitive load on a long single page: you always know where you are.
  const navLinks = [...document.querySelectorAll('.nav-list a')];
  const sections = navLinks.map((a) => document.querySelector(a.getAttribute('href')));
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
    // The hero is observed too: it matches no link, so scrolling back to
    // the top clears the marker.
    [$('#top'), ...sections].forEach((s) => s && io.observe(s));
  }

  $('#year').textContent = new Date().getFullYear();

  // ── LOAD CONTENT ───────────────────────────────────────────────────
  Promise.all([
    fetch(ROOT + 'releases.json', { cache: 'no-store' }).then((r) => r.json()),
    fetch(ROOT + 'videos.json', { cache: 'no-store' }).then((r) => r.json()),
  ]).then(([rels, vids]) => {
    releases = rels;
    videos = vids;
    renderHero();
    renderRecords();
    renderVideos();
  }).catch(() => {
    $('#records').replaceChildren(h('p', { class: 'loading', text: 'The records didn’t load. Refresh the page, or listen on Apple Music or Spotify (links at the bottom).' }));
  });
})();
