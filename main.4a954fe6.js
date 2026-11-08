var _navToggle = document.getElementById('nav-toggle');
var _navDrawer = document.getElementById('nav-drawer');
var _navDebounce = 0;
function toggleNav() {
var now = Date.now();
if (now - _navDebounce < 200) return;
_navDebounce = now;
var open = _navDrawer.classList.toggle('open');
_navToggle.setAttribute('aria-expanded', open);
_navDrawer.setAttribute('aria-hidden', !open);
_navToggle.setAttribute('aria-label', open ? 'Close menu' : 'Open menu');
}
function closeNav() {
_navDrawer.classList.remove('open');
_navDrawer.setAttribute('aria-hidden', 'true');
_navToggle.setAttribute('aria-expanded','false');
_navToggle.setAttribute('aria-label', 'Open menu');
}
_navToggle.addEventListener('click', toggleNav);
var _desktopMq = window.matchMedia('(min-width: 901px)');
_desktopMq.addEventListener('change', function(e) { if (e.matches) closeNav(); });
_navDrawer.querySelectorAll('a, .drawer-search').forEach(function(a) { a.addEventListener('click', closeNav); });
document.addEventListener('keydown', e => {
if (e.key === 'Escape') {
closeNav();
if (document.getElementById('vid-lightbox').classList.contains('open')) closeLightbox();
_navToggle.focus();
}
if (document.getElementById('vid-lightbox').classList.contains('open')) {
if (e.key === 'ArrowLeft') lbNav(-1);
if (e.key === 'ArrowRight') lbNav(1);
}
});
(function() {
const ids = ['epk','contact','music','videos'];
const links = {};
ids.forEach(id => { links[id] = document.querySelector(`.nav-links a[href="#${id}"]`); });
const nav = document.querySelector('.nav');
const navLogo = nav.querySelector('.nav-logo');
const heroBrand = document.getElementById('hero-brand');
const heroSection = document.querySelector('.hero-split-left');
let offsets = [], ticking = false, heroH = 400;
function cacheOffsets() {
offsets = ids.map(id => ({ id, top: (document.getElementById(id) || {}).offsetTop || 0 }));
heroH = heroSection ? heroSection.offsetHeight : 400;
}
cacheOffsets();
var _resizeTimer;
window.addEventListener('resize', function() { clearTimeout(_resizeTimer); _resizeTimer = setTimeout(cacheOffsets, 150); }, { passive: true });
let _lastHeroOut = -1, _lastNavIn = -1, _lastCur = null, _lastScrolled = false;
function updateNav() {
let cur = '';
if (window.innerHeight + window.scrollY >= document.body.scrollHeight - 2) {
cur = ids[ids.length - 1];
} else {
for (let i = 0; i < offsets.length; i++) { if (scrollY >= offsets[i].top - 100) cur = offsets[i].id; }
}
if (cur !== _lastCur) {
ids.forEach(id => { if (links[id]) links[id].removeAttribute('aria-current'); });
if (cur && links[cur]) links[cur].setAttribute('aria-current','page');
_lastCur = cur;
}
const h = heroH;
const heroOut = Math.min(1, Math.max(0, (scrollY - h * 0.15) / (h * 0.2)));
const navIn = Math.min(1, Math.max(0, (scrollY - h * 0.25) / (h * 0.2)));
if (heroBrand && heroOut !== _lastHeroOut) { heroBrand.style.opacity = 1 - heroOut; _lastHeroOut = heroOut; }
if (navLogo && navIn !== _lastNavIn) { navLogo.style.opacity = navIn; _lastNavIn = navIn; }
const scrolled = navIn > 0.5;
if (scrolled !== _lastScrolled) { nav.classList.toggle('scrolled', scrolled); _lastScrolled = scrolled; }
}
window.addEventListener('scroll', () => {
if (ticking) return;
ticking = true;
requestAnimationFrame(() => { updateNav(); ticking = false; });
}, { passive: true });
updateNav();
var _heroImg = document.querySelector('.hero-split-photo');
if (_heroImg) _heroImg.addEventListener('load', function() { cacheOffsets(); updateNav(); });
})();
const npAudio = document.getElementById('np-audio');
const npBar = document.getElementById('player-bar');
let _src = '';
function _safeAudioSrc(p){return p.split('/').map(encodeURIComponent).join('/');}
var _everPlayed = false;
npAudio.addEventListener('playing', function() { _everPlayed = true; });
npAudio.addEventListener('error', function() {
if (!npAudio.src || !npAudio.error) return;
var msg = "Couldn't load this song. Check your connection and try again.";
_npTrackEl.dataset.label = msg; _npTrackEl.textContent = msg;
if (_srAnnounce) _srAnnounce.textContent = msg;
if (typeof npSetPlaying === 'function') npSetPlaying(false);
});
var _seekDragging = false;
const PLAY = '<polygon points="5,3 19,12 5,21"/>';
const PAUSE = '<rect x="6" y="4" width="4" height="16"/><rect x="14" y="4" width="4" height="16"/>';
function fmtT(s) {
if (!isFinite(s)) return '·';
const m = Math.floor(s/60), sec = Math.floor(s%60);
return m + ':' + (sec<10?'0':'') + sec;
}
const _fabMusic = document.getElementById('fab-music');
const _npIcon = document.getElementById('np-icon');
const _npPlayBtn = document.getElementById('np-play');
const _npTrackEl = document.getElementById('np-track');
const _npAlbumEl = document.getElementById('np-album');
const _srAnnounce = document.getElementById('sr-announce');
function npShow() { npBar.classList.add('show'); document.body.classList.add('player-active'); if(_fabMusic) _fabMusic.classList.add('hidden'); }
function npHide() { npBar.classList.remove('show'); document.body.classList.remove('player-active'); if(_fabMusic) _fabMusic.classList.remove('hidden'); }
function npSetPlaying(p) {
_npIcon.innerHTML = p ? PAUSE : PLAY;
_npPlayBtn.setAttribute('aria-label', p ? 'Pause' : 'Play');
if (typeof updatePlayUI === 'function') updatePlayUI();
}
function npGetArt() {
if (pState.releaseIdx >= 0 && RELEASE_LIST[pState.releaseIdx]) return RELEASE_LIST[pState.releaseIdx].art;
return '';
}
function npTrackLabel() {
if (pState.releaseIdx >= 0 && RELEASE_LIST[pState.releaseIdx] && RELEASE_LIST[pState.releaseIdx].type === 'Single') return '';
return (pState.plIdx >= 0 ? (pState.plIdx + 1) + '. ' : '') ;
}
var _npMarqueeToken = 0;
var _npMarqueeTokens = new WeakMap();
function npMarquee(el) {
var t = el.dataset.label || el.textContent;
var token = ++_npMarqueeToken;
_npMarqueeTokens.set(el, token);
el.classList.remove('marquee');
el.textContent = t;
function check() {
if (_npMarqueeTokens.get(el) !== token) return;
if (el.scrollWidth > el.clientWidth + 2) {
el.classList.add('marquee');
el.style.setProperty('--marquee-duration', Math.max(6, t.length * 0.35) + 's');
el.innerHTML = '<span>' + t + '   •   ' + t + '</span>';
}
}
requestAnimationFrame(function() { requestAnimationFrame(check); });
if (document.fonts && document.fonts.ready) { document.fonts.ready.then(check); }
}
if (navigator.maxTouchPoints > 0 && window.innerWidth < 900) {
var lockPortrait = function() {
var so = screen.orientation || screen.webkitOrientation || screen.msOrientation || screen.mozOrientation;
if (so && so.lock) {
try { so.lock('portrait').catch(function() {}); } catch (e) {}
}
};
lockPortrait();
document.addEventListener('visibilitychange', function() {
if (!document.hidden) lockPortrait();
});
}
function npArtwork() {
var src = npGetArt();
if (!src) return [];
var abs = new URL(src, location.href).href;
return [96, 128, 192, 256, 384, 512].map(function(s) {
return { src: abs, sizes: s + 'x' + s, type: 'image/webp' };
});
}
function npSyncMediaState() {
if (!('mediaSession' in navigator)) return;
navigator.mediaSession.playbackState = npAudio.paused ? 'paused' : 'playing';
try {
navigator.mediaSession.setPositionState({ duration: npAudio.duration || 0, playbackRate: 1, position: npAudio.currentTime || 0 });
} catch (err) {}
}
function npUpdateMediaSession(track, album, art) {
if (!('mediaSession' in navigator)) return;
var ms = navigator.mediaSession;
ms.metadata = new MediaMetadata({
title: npTrackLabel() + track,
artist: 'Ash Stu',
album: album || '',
artwork: art ? npArtwork() : []
});
ms.setActionHandler('play', function() { npToggle(); });
ms.setActionHandler('pause', function() { npToggle(); });
ms.setActionHandler('previoustrack', function() { npPrev(); });
ms.setActionHandler('nexttrack', function() { npNext(); });
ms.setActionHandler('seekbackward', function() { npAudio.currentTime = Math.max(0, npAudio.currentTime - 10); });
ms.setActionHandler('seekforward', function() { if (npAudio.duration) npAudio.currentTime = Math.min(npAudio.duration, npAudio.currentTime + 10); });
ms.setActionHandler('seekto', function(details) { if (npAudio.duration) npAudio.currentTime = details.seekTime; });
ms.setActionHandler('stop', function() { npClose(); });
npSyncMediaState();
}
function npLoad(track, album, src, autoplay) {
var label = npTrackLabel() + track;
_npTrackEl.dataset.label = label;
_npAlbumEl.textContent = album || '';
npMarquee(_npTrackEl);
if (_srAnnounce) _srAnnounce.textContent = 'Now playing: ' + track + (album ? ' from ' + album : '');
_playIntent++;
npAudio.pause();
npAudio.preload = 'auto';
npAudio.src = _safeAudioSrc(src); _src = src;
_npFill.style.transform = 'scaleX(0)';
if (_npThumb) _npThumb.style.transform = 'translateX(0)';
_npCur.textContent = '0:00';
_npDur.textContent = '·';
var art = npGetArt();
if (_npArt) { _npArt.src = art ? encodeURI(art) : ''; _npArt.hidden = !art; }
npUpdateMediaSession(track, album, art);
try { sessionStorage.setItem('ash_track',track); sessionStorage.setItem('ash_album',album||''); sessionStorage.setItem('ash_src',src); } catch(e){}
npShow();
if (autoplay) { var intent = ++_playIntent; npAudio.play().then(function() { if (intent === _playIntent) npSetPlaying(true); }).catch(function(){}); }
preloadNextTrack();
}
var _npResizeTimer;
window.addEventListener('resize', function() {
clearTimeout(_npResizeTimer);
_npResizeTimer = setTimeout(function() { if (npBar.classList.contains('show')) npMarquee(_npTrackEl); }, 150);
}, { passive: true });
var _playIntent = 0;
var _preAudio = new Audio();
_preAudio.preload = 'auto';
_preAudio.setAttribute('playsinline', '');
function preloadNextTrack() {
if (!pState.playlist.length || pState.shuffle) return;
var n = pState.plIdx + 1;
if (n >= pState.playlist.length) return;
var item = pState.playlist[n];
var rel = RELEASE_LIST[item.releaseIdx];
if (rel && rel.tracks[item.trackIdx]) _preAudio.src = _safeAudioSrc(rel.tracks[item.trackIdx].file);
}
function npToggle() {
var intent = ++_playIntent;
if (npAudio.paused) {
npAudio.play().then(function() { if (intent === _playIntent) npSetPlaying(true); }).catch(function(){});
} else {
npAudio.pause(); npSetPlaying(false);
}
}
function npClose() {
npAudio.pause(); npSetPlaying(false); npHide();
}
function playTrack(rIdx, tIdx) {
var rel = RELEASE_LIST[rIdx];
if (!rel || !rel.tracks[tIdx]) return;
pState.releaseIdx = rIdx;
pState.playlist = rel.tracks.map(function(t, i) { return { title: t.title, file: t.file, releaseIdx: rIdx, trackIdx: i }; });
pState.plIdx = tIdx;
var t = rel.tracks[tIdx];
npLoad(t.title, rel.name, t.file, true);
updatePlayUI();
}
function playRelease(rIdx) { playTrack(rIdx, 0); }
function toggleRelease(rIdx) {
if (pState.releaseIdx === rIdx && pState.playlist.length && npAudio.src) {
if (npAudio.paused) npShow();
npToggle();
return;
}
playRelease(rIdx);
}
function npNext() {
if (!pState.playlist.length) return;
if (!pState.shuffle && pState.plIdx >= pState.playlist.length - 1) return;
var nextIdx = pState.shuffle ? Math.floor(Math.random() * pState.playlist.length) : pState.plIdx + 1;
pState.plIdx = nextIdx;
var item = pState.playlist[nextIdx];
var rel = RELEASE_LIST[item.releaseIdx];
npLoad(item.title, rel ? rel.name : '', item.file, true);
updatePlayUI();
}
function npPrev() {
if (!pState.playlist.length) return;
if (npAudio.currentTime > 3) { npAudio.currentTime = 0; return; }
var prevIdx = (pState.plIdx - 1 + pState.playlist.length) % pState.playlist.length;
pState.plIdx = prevIdx;
var item = pState.playlist[prevIdx];
var rel = RELEASE_LIST[item.releaseIdx];
npLoad(item.title, rel ? rel.name : '', item.file, true);
updatePlayUI();
}
function npShuffleToggle() {
pState.shuffle = !pState.shuffle;
if (pState.shuffle && pState.repeat) { pState.repeat = false; }
var btn = document.getElementById('np-shuffle');
if (btn) btn.classList.toggle('active', pState.shuffle);
var fsBtn = document.getElementById('fs-shuffle');
if (fsBtn) fsBtn.classList.toggle('active', pState.shuffle);
if (pState.repeat === false) {
var rBtn = document.getElementById('np-repeat');
if (rBtn) rBtn.classList.remove('active');
var fsRBtn = document.getElementById('fs-repeat');
if (fsRBtn) fsRBtn.classList.remove('active');
}
}
function npRepeatToggle() {
pState.repeat = !pState.repeat;
if (pState.repeat && pState.shuffle) { pState.shuffle = false; }
var btn = document.getElementById('np-repeat');
if (btn) btn.classList.toggle('active', pState.repeat);
var fsBtn = document.getElementById('fs-repeat');
if (fsBtn) fsBtn.classList.toggle('active', pState.repeat);
if (pState.shuffle === false) {
var sBtn = document.getElementById('np-shuffle');
if (sBtn) sBtn.classList.remove('active');
var fsSBtn = document.getElementById('fs-shuffle');
if (fsSBtn) fsSBtn.classList.remove('active');
}
}
var VOL_ON = '<polygon points="11 5 6 9 2 9 2 15 6 15 11 19 11 5" stroke="none"/><path d="M15.54 8.46a5 5 0 0 1 0 7.07" fill="none"/><path d="M19.07 4.93a10 10 0 0 1 0 14.14" fill="none"/>';
var VOL_OFF = '<polygon points="11 5 6 9 2 9 2 15 6 15 11 19 11 5" stroke="none"/><line x1="23" y1="9" x2="17" y2="15"/><line x1="17" y1="9" x2="23" y2="15"/>';
var _volSets = [
{ slider: document.getElementById('np-vol-slider'), icon: document.getElementById('np-vol-icon'), mute: document.getElementById('np-mute') },
{ slider: document.getElementById('fs-vol-slider'), icon: document.getElementById('fs-vol-icon'), mute: document.getElementById('fs-mute') }
].filter(function(s) { return s.slider && s.icon && s.mute; });
function updateVolUI() {
var muted = npAudio.muted || npAudio.volume === 0;
var pct = (muted ? 0 : npAudio.volume) * 100;
_volSets.forEach(function(s) {
s.icon.innerHTML = muted ? VOL_OFF : VOL_ON;
s.mute.setAttribute('aria-label', muted ? 'Unmute' : 'Mute');
s.slider.value = muted ? 0 : npAudio.volume;
s.slider.style.setProperty('--vol', pct + '%');
});
}
_volSets.forEach(function(s) {
s.slider.addEventListener('input', function() {
npAudio.muted = false;
npAudio.volume = parseFloat(this.value);
try { localStorage.setItem('ash_vol', npAudio.volume); } catch(e){}
});
s.mute.addEventListener('click', function() { npAudio.muted = !npAudio.muted; });
});
npAudio.addEventListener('volumechange', updateVolUI);
try {
var _sv = localStorage.getItem('ash_vol');
if (_sv !== null) npAudio.volume = Math.min(1, Math.max(0, parseFloat(_sv)));
} catch(e){}
updateVolUI();
_npPlayBtn.addEventListener('click', npToggle);
document.getElementById('np-prev').addEventListener('click', npPrev);
document.getElementById('np-next').addEventListener('click', npNext);
document.getElementById('np-close').addEventListener('click', npClose);
document.getElementById('np-shuffle').addEventListener('click', npShuffleToggle);
document.getElementById('np-repeat').addEventListener('click', npRepeatToggle);
if (_fabMusic) _fabMusic.addEventListener('click', fabClick);
var _featuredPlay = document.getElementById('featured-play');
if (_featuredPlay) {
_featuredPlay.addEventListener('click', function() { toggleRelease(FEATURED_IDX); });
_featuredPlay.addEventListener('keydown', function(e) { if(e.key==='Enter'||e.key===' ') { e.preventDefault(); toggleRelease(FEATURED_IDX); } });
}
var _npArt = document.createElement('img');
_npArt.id = 'np-art'; _npArt.className = 'np-art'; _npArt.alt = 'Now playing'; _npArt.hidden = true;
document.getElementById('np-expand').insertBefore(_npArt, document.getElementById('np-expand').firstChild);
let _lastTimeStore = 0;
const _npFill = document.getElementById('np-fill');
const _npThumb = document.getElementById('np-thumb');
const _npCur = document.getElementById('np-cur');
const _npDur = document.getElementById('np-dur');
npAudio.addEventListener('timeupdate', () => {
if (!npAudio.duration) return;
const pct = npAudio.currentTime / npAudio.duration;
if (!_seekDragging) {
_npFill.style.transform = 'scaleX(' + pct + ')';
_npThumb.style.transform = 'translateX(' + (pct * 100) + '%)';
}
const txt = fmtT(npAudio.currentTime);
if (_npCur.textContent !== txt) _npCur.textContent = txt;
const now = Date.now();
if (now - _lastTimeStore > 1000) {
try { sessionStorage.setItem('ash_time', npAudio.currentTime); } catch(e){}
_lastTimeStore = now;
}
});
npAudio.addEventListener('ended', () => {
if (pState.repeat) { npAudio.currentTime = 0; npAudio.play(); }
else if (pState.playlist.length > 0 && (pState.shuffle || pState.plIdx < pState.playlist.length - 1)) { npNext(); }
else { npSetPlaying(false); }
});
npAudio.addEventListener('loadedmetadata', () => { _npDur.textContent = fmtT(npAudio.duration); });
function wireSeekBar(el) {
var fill = el.querySelector('#np-fill, .fs-fill');
var thumb = el.querySelector('.seek-thumb');
var dragging = false, pendingPct = -1, rafId = null, lastSeek = 0, rect = null;
function paint() {
if (pendingPct < 0) return;
fill.style.transform = 'scaleX(' + pendingPct + ')';
if (thumb) thumb.style.transform = 'translateX(' + (pendingPct * 100) + '%)';
}
function apply() {
rafId = null;
paint();
var now = performance.now();
if (npAudio.duration && now - lastSeek > 160) {
lastSeek = now;
npAudio.currentTime = pendingPct * npAudio.duration;
}
}
function seek(e) {
var r = rect || el.getBoundingClientRect();
pendingPct = Math.max(0, Math.min(1, (e.clientX - r.left) / r.width));
if (rafId === null) rafId = requestAnimationFrame(apply);
}
function end() {
dragging = false; _seekDragging = false; el.classList.remove('seeking');
if (pendingPct >= 0 && npAudio.duration) npAudio.currentTime = pendingPct * npAudio.duration;
}
el.addEventListener('pointerdown', function(e) { dragging = true; _seekDragging = true; el.classList.add('seeking'); rect = el.getBoundingClientRect(); el.setPointerCapture(e.pointerId); seek(e); }, { passive: true });
el.addEventListener('pointermove', function(e) { if (dragging) seek(e); }, { passive: true });
el.addEventListener('pointerup', end, { passive: true });
el.addEventListener('pointercancel', end, { passive: true });
}
wireSeekBar(document.getElementById('np-bar-track'));
if ('mediaSession' in navigator) {
npAudio.addEventListener('play', npSyncMediaState);
npAudio.addEventListener('pause', npSyncMediaState);
npAudio.addEventListener('loadedmetadata', npSyncMediaState);
npAudio.addEventListener('seeked', npSyncMediaState);
}
(function() {
var fs = document.getElementById('fs-player');
var fsArt = document.createElement('img');
fsArt.id = 'fs-art'; fsArt.className = 'fs-art'; fsArt.alt = 'Now playing'; fsArt.hidden = true;
document.getElementById('fs-art-wrap').appendChild(fsArt);
var fsTrack = document.getElementById('fs-track');
var fsAlbum = document.getElementById('fs-album');
var fsFill = document.getElementById('fs-fill');
var fsThumb = document.getElementById('fs-thumb');
var fsCur = document.getElementById('fs-cur');
var fsDur = document.getElementById('fs-dur');
var fsPlayIcon = document.getElementById('fs-play-icon');
var fsPlatforms = document.getElementById('fs-platforms');
var fsApple = document.getElementById('fs-apple');
var fsSpotify = document.getElementById('fs-spotify');
var _fsOpen = false;
function fsUpdateArt() {
var art = npGetArt();
var ph = document.getElementById('fs-art-placeholder');
if (art) {
var encoded = encodeURI(art);
fsArt.style.opacity = '0';
fsArt.onload = function() { fsArt.style.opacity = '1'; };
fsArt.src = encoded;
fsArt.hidden = false;
if (ph) ph.style.display = 'none';
} else {
fsArt.hidden = true;
if (ph) ph.style.display = '';
}
}
function fsUpdatePlatforms() {
var rel = RELEASE_LIST[pState.releaseIdx];
var hasLinks = !!(rel && (rel.apple || rel.spotify));
if (fsPlatforms) fsPlatforms.style.display = hasLinks ? 'flex' : 'none';
if (rel && rel.apple) { fsApple.href = rel.apple; fsApple.style.display = ''; } else if (fsApple) { fsApple.style.display = 'none'; }
if (rel && rel.spotify) { fsSpotify.href = rel.spotify; fsSpotify.style.display = ''; } else if (fsSpotify) { fsSpotify.style.display = 'none'; }
}
function fsSync() {
fsRenderLyrics();
fsLyricsKick();
fsTrack.textContent = _npTrackEl.dataset.label || _npTrackEl.textContent;
npMarquee(fsTrack);
fsAlbum.textContent = _npAlbumEl.textContent;
npMarquee(fsAlbum);
fsUpdateArt();
fsUpdatePlatforms();
fsPlayIcon.innerHTML = npAudio.paused ? PLAY : PAUSE;
document.getElementById('fs-play').setAttribute('aria-label', npAudio.paused ? 'Play' : 'Pause');
var fsRepeatBtn = document.getElementById('fs-repeat');
if (fsRepeatBtn) fsRepeatBtn.classList.toggle('active', pState.repeat);
if (npAudio.duration) {
var syncPct = npAudio.currentTime / npAudio.duration;
fsFill.style.transform = 'scaleX(' + syncPct + ')';
fsThumb.style.transform = 'translateX(' + (syncPct * 100) + '%)';
fsCur.textContent = fmtT(npAudio.currentTime);
fsDur.textContent = fmtT(npAudio.duration);
} else {
fsFill.style.transform = 'scaleX(0)';
if (fsThumb) fsThumb.style.transform = 'translateX(0)';
fsCur.textContent = '0:00';
fsDur.textContent = '·';
}
}
var fsLyr = document.getElementById('fs-lyrics');
var fsLyrList = document.getElementById('fs-lyrics-list');
var fsLyrToggle = document.getElementById('fs-lyrics-toggle');
var _lyr = { file: null, times: [], btns: [], cur: -2, holdUntil: 0, raf: 0 };
var _lyrShow = true;
try { _lyrShow = localStorage.getItem('fs-lyrics') !== 'off'; } catch (e) {}
var _lyrReduce = window.matchMedia('(prefers-reduced-motion: reduce)');
var LYRIC_LEAD = 0.2; // highlight a hair early, like reading along
function fsCurrentFile() { var p = pState.playlist[pState.plIdx]; return p ? p.file : null; }
function fsRenderLyrics() {
var file = fsCurrentFile();
if (file === _lyr.file) return;
_lyr.file = file; _lyr.cur = -2; _lyr.times = []; _lyr.btns = [];
fsLyrList.textContent = '';
var entry = file && LYRICS[file];
var has = !!(entry && entry.lines && entry.lines.length);
fsLyrToggle.hidden = !has;
fsLyr.hidden = !has || !_lyrShow;
fsLyrToggle.setAttribute('aria-expanded', String(has && _lyrShow));
document.querySelector('.fs-content').classList.toggle('lyrics-on', has && _lyrShow);
fsLyrList.classList.toggle('is-plain', has && entry.synced === false);
if (has && entry.synced === false) fsLyr.setAttribute('tabindex', '0'); else fsLyr.removeAttribute('tabindex');
if (has && entry.synced === false) {
var pf = document.createDocumentFragment();
entry.lines.forEach(function(l) { var li = document.createElement('li'); li.className = 'fs-lyric fs-lyric--plain'; li.textContent = l[1]; pf.appendChild(li); });
fsLyrList.appendChild(pf);
fsLyr.scrollTop = 0;
} else if (has) {
var frag = document.createDocumentFragment();
entry.lines.forEach(function(l, i) {
var li = document.createElement('li');
li.className = 'fs-lyric';
var b = document.createElement('button');
b.type = 'button';
b.textContent = l[1];
b.dataset.i = i;
b.tabIndex = i === 0 ? 0 : -1; // roving tabindex: the list is one Tab stop
li.appendChild(b);
frag.appendChild(li);
_lyr.times.push(l[0]); _lyr.btns.push(b);
});
fsLyrList.appendChild(frag);
fsLyr.scrollTop = 0;
}
if (_fsOpen) fitFsArt();
}
function fsLyricIndex(t) {
var a = _lyr.times, lo = 0, hi = a.length - 1, idx = -1;
while (lo <= hi) { var mid = (lo + hi) >> 1; if (a[mid] <= t) { idx = mid; lo = mid + 1; } else hi = mid - 1; }
return idx;
}
function fsSetLyric(idx) {
var old = _lyr.btns[_lyr.cur];
if (old) { old.parentNode.classList.remove('is-current'); old.removeAttribute('aria-current'); }
for (var i = 0; i < _lyr.btns.length; i++) _lyr.btns[i].parentNode.classList.toggle('is-past', i < idx);
_lyr.cur = idx;
var b = _lyr.btns[idx];
if (!b) return;
b.parentNode.classList.add('is-current');
b.setAttribute('aria-current', 'true');
if (!fsLyrList.contains(document.activeElement)) {
_lyr.btns.forEach(function(x) { x.tabIndex = -1; });
b.tabIndex = 0;
}
if (Date.now() > _lyr.holdUntil) {
var top = b.parentNode.offsetTop - fsLyr.clientHeight * 0.32;
fsLyr.scrollTo({ top: Math.max(0, top), behavior: _lyrReduce.matches ? 'auto' : 'smooth' });
}
}
function fsLyricsTick() {
_lyr.raf = 0;
if (!_fsOpen || fsLyr.hidden || !_lyr.times.length) return;
var idx = fsLyricIndex(npAudio.currentTime + LYRIC_LEAD);
if (idx !== _lyr.cur) fsSetLyric(idx);
if (!npAudio.paused) _lyr.raf = requestAnimationFrame(fsLyricsTick);
}
function fsLyricsKick() { if (!_lyr.raf) _lyr.raf = requestAnimationFrame(fsLyricsTick); }
['play', 'seeked', 'loadedmetadata'].forEach(function(ev) {
npAudio.addEventListener(ev, function() { if (_fsOpen) { fsRenderLyrics(); fsLyricsKick(); } });
});
['wheel', 'touchstart', 'pointerdown'].forEach(function(ev) {
fsLyr.addEventListener(ev, function() { _lyr.holdUntil = Date.now() + 4000; }, { passive: true });
});
fsLyrList.addEventListener('click', function(e) {
var b = e.target.closest('button');
if (!b) return;
npAudio.currentTime = _lyr.times[+b.dataset.i];
_lyr.holdUntil = 0;
if (npAudio.paused) npToggle();
fsSync();
});
fsLyrList.addEventListener('keydown', function(e) {
var i = _lyr.btns.indexOf(document.activeElement);
if (i < 0) return;
var n = { ArrowDown: i + 1, ArrowUp: i - 1, Home: 0, End: _lyr.btns.length - 1 }[e.key];
if (n === undefined) return;
e.preventDefault();
n = Math.max(0, Math.min(_lyr.btns.length - 1, n));
_lyr.btns[i].tabIndex = -1;
_lyr.btns[n].tabIndex = 0;
_lyr.btns[n].focus();
_lyr.holdUntil = Date.now() + 4000;
});
fsLyrToggle.addEventListener('click', function() {
_lyrShow = fsLyr.hidden;
fsLyr.hidden = !_lyrShow;
fsLyrToggle.setAttribute('aria-expanded', String(_lyrShow));
document.querySelector('.fs-content').classList.toggle('lyrics-on', _lyrShow);
try { localStorage.setItem('fs-lyrics', _lyrShow ? 'on' : 'off'); } catch (e) {}
_lyr.cur = -2;
fitFsArt();
fsLyricsKick();
});
var _fsOpener = null, _fsInerted = [];
function fsOpen() {
if (_fsOpen) return;   // two gestures can both fire; a second open would lose the inert list
_fsOpener = document.activeElement;
fsSync();
fs.classList.add('open');
fs.setAttribute('aria-hidden', 'false');
fs.inert = false;
npBar.inert = true; // can't keyboard-tab behind the maximized player
_fsInerted = [].filter.call(document.body.children, function(el) {
return el !== fs && !el.contains(fs) && !el.inert && el.getAttribute('aria-live') == null && el.tagName !== 'SCRIPT';
});
_fsInerted.forEach(function(el) { el.inert = true; });
_fsOpen = true;
document.documentElement.classList.add('fs-locked');
fitFsArt();
setTimeout(function() { document.getElementById('fs-collapse').focus({ preventScroll: true }); }, 60);
}
function fsClose() {
if (!_fsOpen) return;
fs.classList.remove('open');
fs.setAttribute('aria-hidden', 'true');
fs.inert = true;
npBar.inert = false;
_fsInerted.forEach(function(el) { el.inert = false; });
_fsInerted = [];
_fsOpen = false;
document.documentElement.classList.remove('fs-locked');
var back = (_fsOpener && _fsOpener.isConnected && !fs.contains(_fsOpener)) ? _fsOpener : document.getElementById('np-expand');
if (back) back.focus({ preventScroll: true });
}
function fitFsArt() {
var wrap = document.getElementById('fs-art-wrap');
if (!wrap || !_fsContentEl) return;
if (window.matchMedia('(orientation: landscape) and (max-height: 520px)').matches) {
wrap.style.width = '';
wrap.style.display = '';
return;
}
var c = _fsContentEl;
wrap.style.display = '';
if (c.classList.contains('lyrics-on')) { wrap.style.width = Math.min(c.clientWidth, 340) + 'px'; return; }
wrap.style.width = Math.min(c.clientWidth, 340) + 'px';
for (var i = 0; i < 2; i++) {
var nonArt = c.scrollHeight - wrap.offsetHeight;
var avail = c.clientHeight - nonArt;
if (avail <= 0) { wrap.style.display = 'none'; return; }
wrap.style.width = Math.min(c.clientWidth, 340, avail) + 'px';
}
}
window.addEventListener('resize', function() {
if (_fsOpen) fitFsArt();
}, { passive: true });
if (document.fonts && document.fonts.ready) {
document.fonts.ready.then(function() { if (_fsOpen) fitFsArt(); });
}
var _swipe = null;
var _swipeConsumed = false;
var _fsContentEl = document.querySelector('.fs-content');
npBar.addEventListener('pointerdown', function(e) {
_swipeConsumed = false;
if (e.pointerType === 'touch') return; // touch path below owns touch
if (e.target.closest('button, input, a, .np-bar-track')) return;
_swipe = { y: e.clientY, x: e.clientX, target: npBar, dir: null };
}, { passive: true });
npBar.addEventListener('pointermove', function(e) {
if (!_swipe || _swipe.target !== npBar) return;
var dx = e.clientX - _swipe.x;
var dy = e.clientY - _swipe.y;
if (!_swipe.dir) {
if (Math.abs(dx) < 6 && Math.abs(dy) < 6) return;
_swipe.dir = Math.abs(dx) > Math.abs(dy) ? 'x' : 'y';
}
if (_swipe.dir === 'y' && dy < -40) { _swipe = null; fsOpen(); }
}, { passive: true });
npBar.addEventListener('pointerup', function(e) {
if (_swipe && _swipe.target === npBar) {
var dx = e.clientX - _swipe.x;
if (_swipe.dir === 'x' && Math.abs(dx) > 60) {
_swipe = null;
_swipeConsumed = true;
if (dx < 0) { npNext(); fsSync(); } else { npPrev(); fsSync(); }
}
}
_swipe = null;
}, { passive: true });
npBar.addEventListener('pointercancel', function() { _swipe = null; }, { passive: true });
var _npBarTouch = null;
npBar.addEventListener('touchstart', function(e) {
_swipeConsumed = false;
if (e.target.closest('button, input, a, .np-bar-track')) return;
var t = e.touches[0];
_npBarTouch = { y: t.clientY, x: t.clientX, active: false, dir: null };
}, { passive: true });
npBar.addEventListener('touchmove', function(e) {
if (!_npBarTouch) return;
var t = e.touches[0];
var dy = t.clientY - _npBarTouch.y;
var dx = t.clientX - _npBarTouch.x;
if (_npBarTouch.active) { e.preventDefault(); return; }
if (!_npBarTouch.dir) {
if (Math.abs(dx) < 8 && Math.abs(dy) < 8) return;
_npBarTouch.dir = Math.abs(dx) > Math.abs(dy) ? 'x' : 'y';
}
if (_npBarTouch.dir === 'x') {
if (Math.abs(dx) > 10) { _npBarTouch.active = true; e.preventDefault(); }
return;
}
if (dy < -40) { _npBarTouch = null; fsOpen(); }
}, { passive: false });
npBar.addEventListener('touchend', function(e) {
if (_npBarTouch && _npBarTouch.active && _npBarTouch.dir === 'x') {
var dx = e.changedTouches[0].clientX - _npBarTouch.x;
if (Math.abs(dx) > 60) {
_npBarTouch = null;
_swipeConsumed = true;
if (dx < 0) { npNext(); fsSync(); } else { npPrev(); fsSync(); }
}
}
_npBarTouch = null;
}, { passive: true });
npBar.addEventListener('touchcancel', function() { _npBarTouch = null; }, { passive: true });
fs.addEventListener('pointerdown', function(e) {
if (e.pointerType === 'touch') return; // touch path handles touch below
if (e.target.closest('button, input, a, .fs-bar, .fs-lyrics')) return; // the lyrics panel scrolls; it never closes the player
_swipe = { y: e.clientY, x: e.clientX, target: fs, dir: null };
}, { passive: true });
fs.addEventListener('pointermove', function(e) {
if (!_swipe || _swipe.target !== fs || !_fsOpen) return;
if (e.pointerType === 'touch') return;
if (_fsContentEl && _fsContentEl.scrollTop > 0) return;
var dx = e.clientX - _swipe.x;
var dy = e.clientY - _swipe.y;
if (!_swipe.dir) {
if (Math.abs(dx) < 6 && Math.abs(dy) < 6) return;
_swipe.dir = Math.abs(dx) > Math.abs(dy) ? 'x' : 'y';
}
if (_swipe.dir === 'y') {
if (dy > 48) { _swipe = null; fsClose(); }
} else if (Math.abs(dx) > 60) {
_swipe = null;
if (dx < 0) { npNext(); fsSync(); } else { npPrev(); fsSync(); }
}
}, { passive: true });
fs.addEventListener('pointerup', function() { _swipe = null; }, { passive: true });
fs.addEventListener('pointercancel', function() { _swipe = null; }, { passive: true });
var _fsTouch = null;
fs.addEventListener('touchstart', function(e) {
if (!_fsOpen) return;
if (e.target.closest('button, input, a, .fs-bar, .fs-lyrics')) return;
var t = e.touches[0];
_fsTouch = { y: t.clientY, x: t.clientX, active: false, dir: null };
}, { passive: true });
fs.addEventListener('touchmove', function(e) {
if (!_fsTouch || !_fsOpen) return;
var t = e.touches[0];
var dy = t.clientY - _fsTouch.y;
var dx = t.clientX - _fsTouch.x;
if (_fsTouch.active) { e.preventDefault(); return; }
if (!_fsTouch.dir) {
if (Math.abs(dx) < 8 && Math.abs(dy) < 8) return;
_fsTouch.dir = Math.abs(dx) > Math.abs(dy) ? 'x' : 'y';
}
if (_fsTouch.dir === 'x') {
if (Math.abs(dx) > 10) { _fsTouch.active = true; e.preventDefault(); }
return;
}
if (_fsContentEl && _fsContentEl.scrollTop > 0) {
if (dy < 0) { _fsTouch = null; }
return;
}
if (dy > 8) {
_fsTouch.active = true;
e.preventDefault();
if (dy > 48) { _fsTouch = null; fsClose(); }
}
}, { passive: false });
fs.addEventListener('touchend', function(e) {
if (_fsTouch) {
if (_fsTouch.active) {
if (_fsTouch.dir === 'x') {
var dx = e.changedTouches[0].clientX - _fsTouch.x;
if (dx < -60) { _fsTouch = null; npNext(); fsSync(); }
else if (dx > 60) { _fsTouch = null; npPrev(); fsSync(); }
} else {
_fsTouch = null; fsClose();
}
} else {
_fsTouch = null;
}
}
_fsTouch = null;
}, { passive: true });
fs.addEventListener('touchcancel', function() { _fsTouch = null; }, { passive: true });
document.addEventListener('keydown', function(e) {
if (e.key === 'Escape' && _fsOpen) fsClose();
});
npBar.addEventListener('click', function(e) {
if (_swipeConsumed) { _swipeConsumed = false; return; }
if (e.target.closest('button, input, a, .np-bar-track')) return;
fsOpen();
});
document.getElementById('np-expand').addEventListener('keydown', function(e) {
if (e.key === 'Enter' || e.key === ' ') { e.preventDefault(); fsOpen(); }
});
document.getElementById('fs-collapse').addEventListener('click', fsClose);
document.getElementById('fs-play').addEventListener('click', function() { npToggle(); fsSync(); });
document.getElementById('fs-prev').addEventListener('click', function() { npPrev(); fsSync(); });
document.getElementById('fs-next').addEventListener('click', function() { npNext(); fsSync(); });
document.getElementById('fs-shuffle').addEventListener('click', npShuffleToggle);
document.getElementById('fs-repeat').addEventListener('click', npRepeatToggle);
var _fsBar = document.getElementById('fs-bar');
wireSeekBar(_fsBar);
npAudio.addEventListener('timeupdate', function() {
if (!_fsOpen || !npAudio.duration) return;
var tuPct = npAudio.currentTime / npAudio.duration;
if (!_seekDragging) {
fsFill.style.transform = 'scaleX(' + tuPct + ')';
fsThumb.style.transform = 'translateX(' + (tuPct * 100) + '%)';
}
var txt = fmtT(npAudio.currentTime);
if (fsCur.textContent !== txt) fsCur.textContent = txt;
});
npAudio.addEventListener('loadedmetadata', function() {
if (_fsOpen) fsDur.textContent = fmtT(npAudio.duration);
});
npAudio.addEventListener('play', function() { if (_fsOpen) { fsPlayIcon.innerHTML = PAUSE; document.getElementById('fs-play').setAttribute('aria-label', 'Pause'); } });
npAudio.addEventListener('pause', function() { if (_fsOpen) { fsPlayIcon.innerHTML = PLAY; document.getElementById('fs-play').setAttribute('aria-label', 'Play'); } });
var _origNpLoad = npLoad;
npLoad = function(track, album, src, autoplay, opts) {
_origNpLoad(track, album, src, autoplay, opts);
if (_fsOpen) setTimeout(fsSync, 50);
};
})();
const PLAY_SVG = '<svg width="16" height="16" viewBox="0 0 24 24" fill="currentColor" aria-hidden="true"><polygon points="5,3 19,12 5,21"/></svg>';
function escHtml(s) {
return (s == null ? '' : String(s))
.replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;')
.replace(/"/g, '&quot;').replace(/'/g, '&#39;');
}
var RELEASE_LIST = [];
var FEATURED_IDX = 0;
var _dodgeEls = null;
var pState = {
playlist: [],
plIdx: -1,
shuffle: false,
repeat: false,
releaseIdx: -1
};
var _discCache = {};
function initDefaultTrack() {
var rel = RELEASE_LIST[FEATURED_IDX];
if (!rel) return;
pState.releaseIdx = FEATURED_IDX;
pState.playlist = rel.tracks.map(function(t,i) { return { title: t.title, file: t.file, releaseIdx: FEATURED_IDX, trackIdx: i }; });
pState.plIdx = 0;
var t = rel.tracks[0];
_npTrackEl.dataset.label = '1. ' + t.title;
npMarquee(_npTrackEl);
_npAlbumEl.textContent = rel.name;
var art = npGetArt();
if (_npArt && art) { _npArt.src = encodeURI(art); _npArt.hidden = false; }
npAudio.src = _safeAudioSrc(t.file); _src = t.file;
npUpdateMediaSession(t.title, rel.name, art);
}
var _tracklistDebounce = 0;
function onRelOverlay(e, rIdx) {
if (RELEASE_LIST[rIdx].type === 'Single') {
closeAllTracklists();
toggleRelease(rIdx);
} else if (e.target.closest('.rel-play-circle')) {
closeAllTracklists();
toggleRelease(rIdx);
} else {
var now = Date.now();
if (now - _tracklistDebounce < 400) return;
_tracklistDebounce = now;
setTracklist(rIdx, false);
}
}
var _partyPlayingIdx = -1;
function updatePlayUI() {
var _nowIdx = !npAudio.paused ? pState.releaseIdx : -1;
if (_nowIdx >= 0 && _nowIdx !== _partyPlayingIdx && window.partyCardBurst) window.partyCardBurst(_nowIdx);
_partyPlayingIdx = _nowIdx;
document.querySelectorAll('.rel-card.now-playing').forEach(function(c) { c.classList.remove('now-playing'); });
Object.keys(_discCache).forEach(function(rIdx) {
var svg = _discCache[rIdx];
var isPlaying = parseInt(rIdx) === pState.releaseIdx && !npAudio.paused;
svg.innerHTML = isPlaying ? PAUSE : PLAY;
svg.style.marginLeft = isPlaying ? '0' : '3px';
if (isPlaying) {
var card = svg.closest('.rel-card');
if (card) card.classList.add('now-playing');
}
});
var fp = document.querySelector('#featured-play .rel-play-circle svg');
if (fp) {
var fpPlaying = pState.releaseIdx === FEATURED_IDX && !npAudio.paused;
var party = document.getElementById('party');
if (party) {
if (fpPlaying && !party.classList.contains('is-playing') && window.partyBurst) window.partyBurst();
party.classList.toggle('is-playing', fpPlaying);
}
fp.innerHTML = fpPlaying ? PAUSE : PLAY;
fp.style.marginLeft = fpPlaying ? '0' : '3px';
}
}
function setTracklist(rIdx, autoPlay) {
var cards = document.querySelectorAll('.rel-card');
var targetCard = null;
cards.forEach(function(c) {
if (parseInt(c.dataset.release) === rIdx) targetCard = c;
});
if (!targetCard) return;
var tl = targetCard.querySelector('.rel-tracklist');
if (!tl) return;
var wasOpen = targetCard.classList.contains('tracks-open');
document.querySelectorAll('.rel-card.tracks-open').forEach(function(c) {
c.classList.remove('tracks-open');
var otl = c.querySelector('.rel-tracklist');
if (otl) otl.style.maxHeight = '0';
});
syncTracklistExpanded();
if (!wasOpen) {
targetCard.classList.add('tracks-open');
var tw = targetCard.querySelector('.rel-art-wrap[aria-expanded]'); if (tw) tw.setAttribute('aria-expanded', 'true');
recalcTracklistHeight(tl);
if (autoPlay) playRelease(rIdx);
}
}
var LYRICS = {};
function closeAllTracklists() {
document.querySelectorAll('.rel-card.tracks-open').forEach(function(c) {
c.classList.remove('tracks-open');
var otl = c.querySelector('.rel-tracklist');
if (otl) otl.style.maxHeight = '0';
});
syncTracklistExpanded();
}
function syncTracklistExpanded() {
document.querySelectorAll('.rel-card .rel-art-wrap[aria-expanded]').forEach(function(w) {
w.setAttribute('aria-expanded', String(w.closest('.rel-card').classList.contains('tracks-open')));
});
}
function setupCardListeners() {
document.querySelectorAll('.rel-card').forEach(function(card, rIdx) {
card.dataset.release = rIdx;
var wrap = card.querySelector('.rel-art-wrap');
if (!wrap) return;
wrap.setAttribute('role', 'button');
wrap.setAttribute('tabindex', '0');
var relName = RELEASE_LIST[rIdx] ? RELEASE_LIST[rIdx].name : '';
if (RELEASE_LIST[rIdx] && RELEASE_LIST[rIdx].type === 'Single') { wrap.setAttribute('aria-label', 'Play ' + relName); }
else { wrap.setAttribute('aria-label', 'Show tracks for ' + relName); wrap.setAttribute('aria-expanded', 'false'); wrap.setAttribute('aria-controls', 'tracklist-' + rIdx); }
var overlay = document.createElement('div');
overlay.className = 'rel-play-overlay';
overlay.innerHTML = '<div class="rel-play-circle">' + PLAY_SVG + '</div>';
wrap.appendChild(overlay);
_discCache[rIdx] = overlay.querySelector('svg');
var circle = overlay.querySelector('.rel-play-circle');
circle.addEventListener('click', function(e) { e.stopPropagation(); closeAllTracklists(); toggleRelease(rIdx); });
wrap.addEventListener('click', function(e) { onRelOverlay(e, rIdx); });
wrap.addEventListener('keydown', function(e) { if (e.key === 'Enter' || e.key === ' ') { e.preventDefault(); onRelOverlay(e, rIdx); } });
});
}
function makeLyricsBtn(title) {
var b = document.createElement('button');
b.type = 'button';
b.className = 'rel-lyrics-toggle';
b.setAttribute('aria-label', 'Show lyrics for ' + title);
b.setAttribute('aria-expanded', 'false');
b.innerHTML = '<span aria-hidden="true">Lyrics</span><svg aria-hidden="true" width="10" height="10" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><polyline points="6 9 12 15 18 9"/></svg>';
b.addEventListener('click', function(e) { e.stopPropagation(); toggleTrackLyrics(this); });
return b;
}
function buildSingleLyrics(rel, rIdx) {
var card = document.querySelectorAll('.rel-card')[rIdx];
var t = rel.tracks[0];
var entry = t && LYRICS[t.file];
if (!card || card.querySelector('.rel-single-lyrics') || !(entry && entry.lines && entry.lines.length)) return;
var wrap = document.createElement('div');
wrap.className = 'rel-track-wrap rel-single-lyrics';
var btn = makeLyricsBtn(t.title);
var lDiv = document.createElement('div');
lDiv.className = 'rel-lyrics';
var lInner = document.createElement('div');
lInner.className = 'rel-lyrics-inner';
fillCardLyrics(lInner, entry, t.file);
lDiv.appendChild(lInner);
wrap.appendChild(btn);
wrap.appendChild(lDiv);
var btns = card.querySelector('.rel-btns');
if (btns) btns.after(wrap); else card.appendChild(wrap);
}
function buildTracklists() {
RELEASE_LIST.forEach(function(rel, rIdx) {
if (rel.tracks.length === 1) { buildSingleLyrics(rel, rIdx); return; }
var container = document.getElementById('tracklist-' + rIdx);
if (!container) return;
var frag = document.createDocumentFragment();
rel.tracks.forEach(function(t, tIdx) {
var lyricsEntry = LYRICS[t.file];
var hasLyrics = !!(lyricsEntry && lyricsEntry.lines && lyricsEntry.lines.length);
var wrap = document.createElement('div');
wrap.className = 'rel-track-wrap';
var row = document.createElement('div');
row.className = 'rel-track';
row.dataset.release = rIdx;
row.dataset.track = tIdx;
row.setAttribute('role', 'button');
row.setAttribute('tabindex', '0');
row.innerHTML =
'<span class="rel-track-num">' + (tIdx + 1) + '</span>' +
'<svg class="rel-track-eq" viewBox="0 0 24 24" fill="currentColor" aria-hidden="true"><rect x="4" y="10" width="3" height="10" rx="1"/><rect x="10.5" y="4" width="3" height="16" rx="1"/><rect x="17" y="7" width="3" height="13" rx="1"/></svg>' +
'<span class="rel-track-title">' + t.title + '</span>' +
'';
var lyrBtn = null;
if (hasLyrics) {
lyrBtn = makeLyricsBtn(t.title);
}
row.addEventListener('click', function() { playTrack(rIdx, tIdx); });
row.addEventListener('keydown', function(e) { if(e.key==='Enter'||e.key===' ') { e.preventDefault(); playTrack(rIdx, tIdx); } });
wrap.appendChild(row);
if (lyrBtn) wrap.appendChild(lyrBtn);
if (hasLyrics) {
var lDiv = document.createElement('div');
lDiv.className = 'rel-lyrics';
var lInner = document.createElement('div');
lInner.className = 'rel-lyrics-inner';
fillCardLyrics(lInner, lyricsEntry, t.file);
lDiv.appendChild(lInner);
wrap.appendChild(lDiv);
}
frag.appendChild(wrap);
});
container.innerHTML = '';
container.appendChild(frag);
});
}
function initMarquees() {
var els = document.querySelectorAll('.rel-track-title:not(.marquee)');
var overflowed = [];
els.forEach(function(el) {
if (el.scrollWidth > el.clientWidth) overflowed.push({ el: el, text: el.textContent });
});
overflowed.forEach(function(o) {
o.el.classList.add('marquee');
var dur = Math.max(4, o.text.length * 0.3);
o.el.style.setProperty('--marquee-duration', dur + 's');
o.el.innerHTML = '<span>' + o.text + '   •   ' + o.text + '</span>';
});
}
var _relGrid = document.querySelector('.releases-grid');
if (_relGrid) {
new MutationObserver(function(mutations) {
mutations.forEach(function(m) {
if (m.target.classList && m.target.classList.contains('rel-card') && m.target.classList.contains('tracks-open')) {
setTimeout(initMarquees, 50);
}
});
}).observe(_relGrid, { attributes: true, subtree: true, attributeFilter: ['class'] });
}
function fillCardLyrics(inner, entry, file) {
inner.textContent = '';
inner.dataset.file = file;
entry.lines.forEach(function(l) {
var sp = document.createElement('span');
sp.className = 'rel-lyric-line';
sp.textContent = l[1] || '\u00a0';
if (entry.synced !== false && typeof l[0] === 'number') sp.dataset.t = l[0];
inner.appendChild(sp);
});
}
var _cardLyrRaf = 0;
function cardLyricsTick() {
_cardLyrRaf = 0;
var pl = pState.playlist[pState.plIdx], file = pl ? pl.file : null, live = false;
document.querySelectorAll('.rel-lyrics-inner[data-file]').forEach(function(inner) {
var open = inner.parentNode.style.maxHeight && inner.parentNode.style.maxHeight !== '0px' && inner.parentNode.style.maxHeight !== '0';
var cur = inner.querySelector('.rel-lyric-line.is-current');
var want = null;
if (open && inner.dataset.file === file && npAudio.src) {
var t = npAudio.currentTime + 0.2;   // a hair early, like the full-screen lyrics
inner.querySelectorAll('.rel-lyric-line[data-t]').forEach(function(sp) { if (parseFloat(sp.dataset.t) <= t) want = sp; });
live = true;
}
if (cur !== want) {
if (cur) { cur.classList.remove('is-current'); cur.removeAttribute('aria-current'); }
if (want) { want.classList.add('is-current'); want.setAttribute('aria-current', 'true'); }
}
});
if (live && !npAudio.paused) _cardLyrRaf = requestAnimationFrame(cardLyricsTick);
}
function cardLyricsKick() { if (!_cardLyrRaf) _cardLyrRaf = requestAnimationFrame(cardLyricsTick); }
['play', 'seeked', 'loadedmetadata', 'pause', 'emptied'].forEach(function(ev) { npAudio.addEventListener(ev, cardLyricsKick); });
function recalcTracklistHeight(tl) {
if (tl) tl.style.maxHeight = 'none';
}
function toggleTrackLyrics(btn) {
var wrap = btn.closest('.rel-track-wrap');
var lyrics = wrap.querySelector('.rel-lyrics');
if (!lyrics) return;
var inner = lyrics.querySelector('.rel-lyrics-inner');
var tl = btn.closest('.rel-tracklist');
var opening = !btn.classList.contains('open');
btn.classList.toggle('open');
var songTitle = (btn.getAttribute('aria-label') || '').replace(/^(Show|Hide) lyrics for /, '');
btn.setAttribute('aria-label', (opening ? 'Hide lyrics for ' : 'Show lyrics for ') + songTitle);
btn.setAttribute('aria-expanded', String(opening));
lyrics.style.maxHeight = opening ? 'none' : '0';
recalcTracklistHeight(tl);
cardLyricsKick();
}
function fabClick() {
if (!_src) {
var rel = RELEASE_LIST[FEATURED_IDX];
var t = rel.tracks[0];
pState.releaseIdx = FEATURED_IDX;
pState.playlist = rel.tracks.map(function(tk,i) { return { title: tk.title, file: tk.file, releaseIdx: FEATURED_IDX, trackIdx: i }; });
pState.plIdx = 0;
npLoad(t.title, rel.name, t.file, false);
return;
}
npMarquee(_npTrackEl);
npShow();
}
var VIDEO_LIST = [];
function encPath(p) { return p.replace(/"/g, '%22'); }
function wireVideos() {
const grid = document.getElementById('video-grid');
if (!grid || !VIDEO_LIST.length) return;
grid.querySelectorAll('.vid-card').forEach(card => {
const v = VIDEO_LIST[parseInt(card.dataset.videoIndex, 10)];
if (!v) return;
card.addEventListener('click', () => openLightbox(v));
card.addEventListener('keydown', e => { if(e.key==='Enter'||e.key===' ') { e.preventDefault(); openLightbox(v); } });
var thumbVideo = card.querySelector('.vid-thumb video');
if (thumbVideo) {
var p = thumbVideo.play();
if (p && p.then) p.then(function() { thumbVideo.pause(); }).catch(function() {});
}
});
}
/* ── Dynamic content: releases/videos are fetched from JSON
(generated from Audio/, Videos/ by scripts/generate_content.py,
auto-regenerated by the update-content GitHub Action) rather than
hardcoded here, so adding/removing a project needs no code edit. ── */
function renderReleaseCard(rel, rIdx) {
var kindWord = rel.type === 'Single' ? 'Single cover: ' : rel.type === 'EP' ? 'EP cover: ' : 'Album cover: ';
var btns = '';
if (rel.apple) btns += '<a href="' + escHtml(rel.apple) + '" target="_blank" rel="noopener noreferrer" class="rel-btn" aria-label="Listen to ' + escHtml(rel.name) + ' on Apple Music" itemprop="url"><span class="pt pt--apple" aria-hidden="true"></span> Apple Music</a>';
if (rel.spotify) btns += '<a href="' + escHtml(rel.spotify) + '" target="_blank" rel="noopener noreferrer" class="rel-btn" aria-label="Listen to ' + escHtml(rel.name) + ' on Spotify"><span class="pt pt--spotify" aria-hidden="true"></span> Spotify</a>';
if (!btns) btns = '<span class="rel-btn rel-btn--label">Distributing Soon</span>';
var tracklist = rel.tracks.length > 1
? '<div class="rel-tracklist" id="tracklist-' + rIdx + '"><ol aria-label="Tracklist for ' + escHtml(rel.name) + '"></ol></div>'
: '';
return '<article class="rel-card" aria-label="' + escHtml(rel.name) + ' - ' + escHtml(rel.type) + ' by Ash Stu" itemscope itemtype="https://schema.org/MusicAlbum">' +
'<div class="rel-art-wrap">' +
'<img src="' + escHtml(rel.art) + '" alt="' + escHtml(kindWord + rel.name) + '" class="rel-art" width="560" height="560" itemprop="image"/>' +
'<div class="rel-overlay"><div class="rel-overlay-inner"><p class="rel-cat">' + escHtml(rel.type) + '</p><h3 class="rel-name" itemprop="name">' + escHtml(rel.name) + '</h3></div></div>' +
'</div>' +
'<div class="rel-btns">' + btns + '</div>' +
tracklist +
'</article>';
}
function renderVideoCard(v, vIdx) {
var ytBtn = v.youtube
? '<a class="vid-yt" href="' + escHtml(v.youtube) + '" target="_blank" rel="noopener noreferrer" aria-label="Watch &quot;' + escHtml(v.title) + '&quot; on YouTube"><span class="pt pt--youtube" aria-hidden="true"></span>YouTube</a>'
: '';
var thumbEl = v.thumb
? '<img src="' + escHtml(v.thumb) + '" alt="Music video: ' + escHtml(v.title) + ' by Ash Stu" width="640" height="360"/>'
: '<video src="' + encPath(v.file) + '" preload="metadata" muted playsinline aria-label="Video thumbnail" alt="Video thumbnail"></video>';
return '<div class="vid-card-wrap">' +
'<div class="vid-card" tabindex="0" role="button" aria-label="Play &quot;' + escHtml(v.title) + '&quot;" data-video-index="' + vIdx + '">' +
'<div class="vid-thumb">' +
thumbEl +
'<div class="vid-play-overlay"><div class="vid-play-circle"><svg width="16" height="16" viewBox="0 0 24 24" fill="currentColor" aria-hidden="true"><polygon points="5,3 19,12 5,21"/></svg></div></div>' +
'</div>' +
'</div>' +
'<div class="vid-info">' +
'<h3 class="vid-title">' + escHtml(v.title) + '</h3>' +
ytBtn +
'</div>' +
'</div>';
}
function renderFeatured(rel) {
if (!rel) return;
var img = document.querySelector('.featured-art-hero .featured-art');
if (img) { img.src = rel.art; img.alt = rel.name; }
var vl = document.querySelector('.party-vinyl-label');
if (vl) vl.style.backgroundImage = 'url("' + encodeURI(rel.art) + '")';
var play = document.getElementById('featured-play');
if (play) { play.setAttribute('aria-label', 'Play ' + rel.name); play.setAttribute('title', 'Play ' + rel.name); }
var kicker = document.querySelector('.featured-kicker');
if (kicker) kicker.textContent = rel.type;
var title = document.querySelector('.featured-title');
if (title) title.textContent = rel.name;
var btnsEl = document.querySelector('.featured-btns');
if (btnsEl) {
var h = '';
if (rel.apple) h += '<a href="' + escHtml(rel.apple) + '" target="_blank" rel="noopener noreferrer" class="f-btn" aria-label="Apple Music"><span class="pt pt--apple" aria-hidden="true"></span> Apple Music</a>';
if (rel.spotify) h += '<a href="' + escHtml(rel.spotify) + '" target="_blank" rel="noopener noreferrer" class="f-btn" aria-label="Spotify"><span class="pt pt--spotify" aria-hidden="true"></span> Spotify</a>';
btnsEl.innerHTML = h;
}
var badgeEl = document.getElementById('featured-badge');
if (badgeEl) {
var hasLinks = !!(rel.apple || rel.spotify);
badgeEl.innerHTML = hasLinks ? '<span class="party-dot" aria-hidden="true"></span> Latest Release' : 'Distributing Soon';
badgeEl.classList.toggle('soon', !hasLinks);
var partyEl = document.getElementById('party');
if (partyEl) partyEl.classList.toggle('is-soon', !hasLinks);
}
}
function readEmbedded(id) {
var el = document.getElementById(id);
if (!el) return null;
try { return JSON.parse(el.textContent); } catch(e) { return null; }
}
function renderAllContent(results, isRefresh) {
_dodgeEls = null; // cards/entries below are about to be replaced
RELEASE_LIST = results[0] || [];
FEATURED_IDX = Math.max(0, RELEASE_LIST.findIndex(function(r) { return r.featured; }));
VIDEO_LIST = results[1] || [];
LYRICS = results[2] || {};
var relGrid = document.getElementById('releases-grid');
if (relGrid) relGrid.innerHTML = RELEASE_LIST.map(renderReleaseCard).join('');
var vidGrid = document.getElementById('video-grid');
if (vidGrid) vidGrid.innerHTML = VIDEO_LIST.map(renderVideoCard).join('');
renderFeatured(RELEASE_LIST[FEATURED_IDX]);
if (!isRefresh || !_src || !_everPlayed) initDefaultTrack();
buildTracklists();
setupCardListeners();
wireVideos();
if (typeof initMarquees === 'function') setTimeout(initMarquees, 50);
}
function loadDynamicContent() {
var dataAll = readEmbedded('data-all');
var embedded = dataAll ? [dataAll.releases, dataAll.videos, dataAll.lyrics] : [null];
if (embedded[0]) renderAllContent(embedded, false);
Promise.all([
fetch('releases.json', { cache: 'no-store' }).then(function(r) { return r.json(); }).catch(function() { return null; }),
fetch('videos.json', { cache: 'no-store' }).then(function(r) { return r.json(); }).catch(function() { return null; }),
fetch('lyrics.json', { cache: 'no-store' }).then(function(r) { return r.json(); }).catch(function() { return null; })
]).then(function(results) {
if (results[0] === null) results[0] = embedded[0] ? embedded[0] : [];
if (results[1] === null) results[1] = embedded[1] ? embedded[1] : [];
if (results[2] === null) results[2] = embedded[2] ? embedded[2] : {};
if (!embedded[0]) { renderAllContent(results, false); return; }
if (JSON.stringify(results) !== JSON.stringify(embedded)) renderAllContent(results, true);
});
}
loadDynamicContent();
let _lbIdx = 0;
var _lbPrevFocus = null;
var _lbOpen = false;
function openLightbox(v) {
if (_lbOpen) return;
_lbOpen = true;
if (!npAudio.paused) { npAudio.pause(); npSetPlaying(false); }
_lbPrevFocus = document.activeElement;
_lbIdx = VIDEO_LIST.indexOf(v);
if (_lbIdx < 0) _lbIdx = 0;
_lbShow(_lbIdx);
const lb = document.getElementById('vid-lightbox');
lb.classList.add('open');
lb.setAttribute('aria-hidden', 'false');
lb.inert = false;
document.body.style.overflow = 'hidden';
setTimeout(function() { document.querySelector('.lb-close').focus(); }, 100);
}
function _lbShow(idx) {
const v = VIDEO_LIST[idx];
const vid = document.getElementById('lb-video');
vid.pause();
document.getElementById('lb-title').textContent = v.title;
const yt = document.getElementById('lb-yt');
if (v.youtube) { yt.href = v.youtube; yt.style.display = 'inline-flex'; }
else { yt.style.display = 'none'; }
const dotsEl = document.getElementById('lb-dots');
if (dotsEl) {
if (!dotsEl.children.length) {
VIDEO_LIST.forEach((_,i) => {
const d = document.createElement('button');
d.className = 'lb-dot'; d.setAttribute('aria-label', 'Go to video '+(i+1));
d.onclick = () => { _lbIdx = i; _lbShow(i); };
dotsEl.appendChild(d);
});
}
Array.from(dotsEl.children).forEach((d,i) => d.classList.toggle('active', i===idx));
}
document.getElementById('lb-prev').disabled = (idx === 0);
document.getElementById('lb-next').disabled = (idx === VIDEO_LIST.length - 1);
Array.from(vid.querySelectorAll('track')).forEach(function(t) { t.remove(); });
if (v.captions) {
var tr = document.createElement('track');
tr.kind = 'captions'; tr.srclang = 'en'; tr.label = 'English'; tr.default = true;
tr.src = encPath(v.captions);
vid.appendChild(tr);
}
vid.src = encPath(v.file);
vid.play().catch(function(err) { if (err.name !== 'NotAllowedError') console.warn('[video]', err); });
}
var _lbNavDebounce = 0;
function lbNav(dir) {
var now = Date.now();
if (now - _lbNavDebounce < 300) return;
_lbNavDebounce = now;
const next = _lbIdx + dir;
if (next < 0 || next >= VIDEO_LIST.length) return;
_lbIdx = next;
_lbShow(_lbIdx);
}
function closeLightbox() {
if (!_lbOpen) return;
_lbOpen = false;
const lb = document.getElementById('vid-lightbox');
const vid = document.getElementById('lb-video');
vid.pause(); vid.src = '';
lb.classList.remove('open');
lb.setAttribute('aria-hidden', 'true');
lb.inert = true;
document.body.style.overflow = '';
if (_lbPrevFocus) { _lbPrevFocus.focus(); _lbPrevFocus = null; }
}
document.getElementById('lb-close').addEventListener('click', closeLightbox);
document.getElementById('lb-prev').addEventListener('click', function() { lbNav(-1); });
document.getElementById('lb-next').addEventListener('click', function() { lbNav(1); });
document.getElementById('vid-lightbox').addEventListener('click', function(e) {
if (e.target === this) closeLightbox();
});
(function() {
var arrow = document.getElementById('hero-scroll');
if (!arrow) return;
var SECTIONS = ['epk','contact','music','videos','about'];
function nextTarget() {
var y = scrollY + 80;
for (var i = 0; i < SECTIONS.length; i++) {
var el = document.getElementById(SECTIONS[i]);
if (el && el.offsetTop > y) return SECTIONS[i];
}
return null;
}
var _arrowTick = false;
/* This arrow is position:fixed and persists across the whole page, not
just the hero - it can end up hovering over a release/video card's
play button, a streaming link, anywhere, as the user scrolls. The
list is cached (renderAllContent nulls _dodgeEls whenever it replaces
cards/entries) - re-running an 8-selector querySelectorAll on every
scroll frame was pure waste. */
function getDodgeEls() {
if (_dodgeEls === null) {
_dodgeEls = Array.prototype.slice.call(document.querySelectorAll(
'.hero-split-right > *:not(canvas), .rel-play-circle, .vid-play-circle, ' +
'.rel-btn, .vid-yt, .f-btn, .btn-epk-dl, .contact-email-link'
));
}
return _dodgeEls;
}
var _lastHref = '';
function updateArrow() {
var atBottom = innerHeight + scrollY >= document.body.scrollHeight - 40;
var t = nextTarget();
/* A hint for the first screen only: past the hero it just sat on top of
cards and buttons, and the nav already jumps between sections. */
if (!t || atBottom || scrollY > innerHeight * .5) {
arrow.classList.add('hidden');
return;
}
arrow.classList.remove('hidden');
if (t !== _lastHref) { arrow.setAttribute('href', '#' + t); _lastHref = t; }
var a = arrow.getBoundingClientRect();
var els = getDodgeEls();
var covering = false;
for (var i = 0; i < els.length; i++) {
var b = els[i].getBoundingClientRect();
if (!b.width || !b.height) continue;
if (b.bottom > a.top - 2 && b.top < a.bottom + 2 && b.right > a.left && b.left < a.right) { covering = true; break; }
}
arrow.classList.toggle('soft', covering);
}
window.addEventListener('scroll', function() {
if (_arrowTick) return;
_arrowTick = true;
requestAnimationFrame(function() { updateArrow(); _arrowTick = false; });
}, { passive: true });
window.addEventListener('resize', function() { setTimeout(updateArrow, 160); }, { passive: true });
new MutationObserver(function() { setTimeout(updateArrow, 420); setTimeout(updateArrow, 900); }).observe(document.body, { attributes: true, attributeFilter: ['class'] });
updateArrow();
})();
document.getElementById('vid-lightbox').addEventListener('keydown', function(e) {
if (e.key !== 'Tab') return;
var focusable = this.querySelectorAll('button:not([disabled]), a[href], video, [tabindex]:not([tabindex="-1"])');
if (!focusable.length) return;
var first = focusable[0], last = focusable[focusable.length - 1];
if (e.shiftKey && document.activeElement === first) { e.preventDefault(); last.focus(); }
else if (!e.shiftKey && document.activeElement === last) { e.preventDefault(); first.focus(); }
});
(function() {
const cvs = document.getElementById('confetti-canvas');
if (!cvs || window.matchMedia('(prefers-reduced-motion: reduce)').matches) return;
const COLORS = ['#F7C549','#DF2B2C','#4E97AD','#FFFFFF','#9FBFCB'];
const COUNT = window.matchMedia('(min-width: 601px)').matches ? 45 : 20;
const ctx = cvs.getContext('2d', { desynchronized: true, alpha: true });
const TWO_PI = Math.PI * 2, DEG2RAD = Math.PI / 180;
const pieces = [];
let cw, ch;
function resize() { const r = cvs.parentElement.getBoundingClientRect(); cw = cvs.width = r.width; ch = cvs.height = r.height; }
resize();
let resizeTimer;
window.addEventListener('resize', function() { clearTimeout(resizeTimer); resizeTimer = setTimeout(resize, 150); }, { passive: true });
for (let i = 0; i < COUNT; i++) pieces.push({ x: Math.random()*cw, y: Math.random()*ch, w: 3+Math.random()*4, h: 8+Math.random()*14, rot: Math.random()*TWO_PI, dx: (Math.random()-.5)*.5, dy: .5+Math.random()*1.2, dr: (Math.random()-.5)*3*DEG2RAD, wobble: Math.random()*TWO_PI, wobbleSpeed: .02+Math.random()*.03, flex: Math.random()*TWO_PI, flexSpeed: .03+Math.random()*.04, color: COLORS[Math.floor(Math.random()*COLORS.length)], opacity: .2+Math.random()*.35 });
const bursts = [];
window.partyBurst = function() {
if (!running) return;
const art = document.querySelector('.featured-art-hero'), pr = cvs.getBoundingClientRect();
if (!art) return;
const a = art.getBoundingClientRect(), ox = a.left + a.width / 2 - pr.left, oy = a.top + 4 - pr.top;   /* from the sleeve's top edge: the canvas sits behind the cover */
const N = window.matchMedia('(min-width: 601px)').matches ? 90 : 50;
for (let i = 0; i < N; i++) {
const ang = -Math.PI / 2 + (Math.random() - .5) * Math.PI * .95, sp = 6 + Math.random() * 8;
bursts.push({ x: ox + (Math.random() - .5) * a.width * .7, y: oy, vx: Math.cos(ang) * sp, vy: Math.sin(ang) * sp, w: 4 + Math.random() * 4, h: 7 + Math.random() * 9, rot: Math.random() * TWO_PI, dr: (Math.random() - .5) * 18 * DEG2RAD, flex: Math.random() * TWO_PI, color: COLORS[i % COLORS.length], life: 1, round: Math.random() < .3 });
}
};
let running = false, lastT = null, rafId = null;
function draw(t) {
if (!running) { lastT = null; rafId = null; return; }
if (lastT === null) { lastT = t; rafId = requestAnimationFrame(draw); return; }
const dt = Math.min(t - lastT, 50) / 16.667;
lastT = t;
ctx.clearRect(0, 0, cw, ch);
for (let i = 0; i < pieces.length; i++) {
const p = pieces[i];
p.x += (p.dx + Math.sin(p.wobble) * .5) * dt;
p.y += p.dy * dt;
p.rot += p.dr * dt;
p.wobble += p.wobbleSpeed * dt;
p.flex += p.flexSpeed * dt;
if (p.y > ch + 20) { p.y = -20; p.x = Math.random() * cw; }
const c = Math.cos(p.rot), s = Math.sin(p.rot), sx = .4 + Math.abs(Math.sin(p.flex)) * .6;
ctx.globalAlpha = p.opacity;
ctx.fillStyle = p.color;
ctx.setTransform(sx * c, sx * s, -s, c, p.x, p.y);
ctx.fillRect(-p.w / 2, -p.h / 2, p.w, p.h);
}
for (let i = bursts.length - 1; i >= 0; i--) {
const b = bursts[i];
b.vy += .32 * dt; b.vx *= Math.pow(.985, dt); b.vy *= Math.pow(.985, dt);
b.x += b.vx * dt; b.y += b.vy * dt; b.rot += b.dr * dt; b.flex += .12 * dt;
b.life -= .008 * dt;
if (b.life <= 0 || b.y > ch + 30) { bursts.splice(i, 1); continue; }
const c = Math.cos(b.rot), s = Math.sin(b.rot), sx = .35 + Math.abs(Math.sin(b.flex)) * .65;
ctx.globalAlpha = Math.min(1, b.life * 1.6);
ctx.fillStyle = b.color;
ctx.setTransform(sx * c, sx * s, -s, c, b.x, b.y);
if (b.round) { ctx.beginPath(); ctx.arc(0, 0, b.w * .6, 0, TWO_PI); ctx.fill(); }
else ctx.fillRect(-b.w / 2, -b.h / 2, b.w, b.h);
}
ctx.setTransform(1, 0, 0, 1, 0, 0);
ctx.globalAlpha = 1;
rafId = requestAnimationFrame(draw);
}
function start() { if (!running) { running = true; rafId = requestAnimationFrame(draw); } }
function stop() { running = false; if (rafId) { cancelAnimationFrame(rafId); rafId = null; } }
start();
if ('IntersectionObserver' in window) { new IntersectionObserver(function(entries) { entries[0].isIntersecting ? start() : stop(); }).observe(cvs); }
document.addEventListener('visibilitychange', function() { document.hidden ? stop() : start(); });
})();
(function() {
/* Release cards get the same party kit as the hero: a record tucked in the
sleeve (peeks out on hover, slides out spinning while that release plays),
a glare, a now-playing chip, a lean toward the pointer, and a confetti pop
on play. Decor is aria-hidden and added here (not in the prerendered HTML)
so there is one copy of it; re-applied whenever the grid re-renders. */
var grid = document.getElementById('releases-grid');
if (!grid) return;
var reduce = matchMedia('(prefers-reduced-motion: reduce)').matches;
function decorate() {
grid.querySelectorAll('.rel-card').forEach(function(card) {
var wrap = card.querySelector('.rel-art-wrap'), img = wrap && wrap.querySelector('.rel-art');
if (!wrap || !img || wrap.querySelector('.rel-vinyl')) return;
var v = document.createElement('div'); v.className = 'party-vinyl rel-vinyl'; v.setAttribute('aria-hidden', 'true');
var l = document.createElement('span'); l.className = 'party-vinyl-label'; l.style.backgroundImage = 'url("' + img.getAttribute('src') + '")';
v.appendChild(l); wrap.insertBefore(v, img);
var g = document.createElement('span'); g.className = 'party-glare'; g.setAttribute('aria-hidden', 'true'); wrap.appendChild(g);
var e = document.createElement('span'); e.className = 'party-eq rel-eq'; e.setAttribute('aria-hidden', 'true');
e.innerHTML = '<i></i><i></i><i></i><i></i> Now playing'; wrap.appendChild(e);
});
}
decorate();
new MutationObserver(decorate).observe(grid, { childList: true, subtree: false });
/* Confetti pop from a card when its release starts (skips release 0 while
the hero panel, which pops its own, is on screen). One fixed canvas,
created on first use, drawn only while pieces are alive. */
var cv = null, cx = null, pieces = [], raf = 0, last = 0;
var COLORS = ['#F7C549', '#DF2B2C', '#4E97AD', '#FFFFFF', '#FF5FA2', '#7AE7FF'];
function frame(t) {
var dt = last ? Math.min(t - last, 50) / 16.667 : 1; last = t;
var dpr = cv.width / innerWidth;
cx.setTransform(1, 0, 0, 1, 0, 0); cx.clearRect(0, 0, cv.width, cv.height);
for (var i = pieces.length - 1; i >= 0; i--) {
var b = pieces[i];
b.vy += .3 * dt; b.vx *= Math.pow(.985, dt); b.vy *= Math.pow(.985, dt);
b.x += b.vx * dt; b.y += b.vy * dt; b.rot += b.dr * dt; b.flex += .12 * dt; b.life -= .009 * dt;
if (b.life <= 0 || b.y > innerHeight + 30) { pieces.splice(i, 1); continue; }
var c = Math.cos(b.rot), s = Math.sin(b.rot), sx = .35 + Math.abs(Math.sin(b.flex)) * .65;
cx.globalAlpha = Math.min(1, b.life * 1.6); cx.fillStyle = b.color;
cx.setTransform(sx * c * dpr, sx * s * dpr, -s * dpr, c * dpr, b.x * dpr, b.y * dpr);
if (b.round) { cx.beginPath(); cx.arc(0, 0, b.w * .6, 0, Math.PI * 2); cx.fill(); } else cx.fillRect(-b.w / 2, -b.h / 2, b.w, b.h);
}
if (pieces.length) raf = requestAnimationFrame(frame);
else { raf = 0; last = 0; cv.hidden = true; }
}
window.partyCardBurst = function(idx) {
if (reduce) return;
var party = document.getElementById('party');
if (idx === FEATURED_IDX && party && !party.classList.contains('party-off')) return;
var card = grid.querySelector('.rel-card[data-release="' + idx + '"]') || grid.querySelectorAll('.rel-card')[idx];
if (!card) return;
var r = card.querySelector('.rel-art-wrap').getBoundingClientRect();
if (r.bottom < 0 || r.top > innerHeight) return;
if (!cv) {
cv = document.createElement('canvas'); cv.className = 'party-overlay'; cv.setAttribute('aria-hidden', 'true');
document.body.appendChild(cv); cx = cv.getContext('2d');
}
var dpr = Math.min(devicePixelRatio || 1, 2);
cv.width = innerWidth * dpr; cv.height = innerHeight * dpr; cv.hidden = false;
for (var i = 0; i < 70; i++) {
var ang = -Math.PI / 2 + (Math.random() - .5) * Math.PI * .95, sp = 6 + Math.random() * 8;
pieces.push({ x: r.left + r.width * (.15 + Math.random() * .7), y: r.top + r.height * .5, vx: Math.cos(ang) * sp, vy: Math.sin(ang) * sp, w: 4 + Math.random() * 4, h: 7 + Math.random() * 9, rot: Math.random() * 6.28, dr: (Math.random() - .5) * .3, flex: Math.random() * 6.28, color: COLORS[i % COLORS.length], life: 1, round: Math.random() < .3 });
}
if (!raf) raf = requestAnimationFrame(frame);
};
if (reduce || !matchMedia('(pointer: fine)').matches) return;
/* Lean toward the pointer on a spring (real frame time), per card. */
var springs = new WeakMap();
function spring(card) {
var st = springs.get(card);
if (!st) { st = { tx: 0, ty: 0, x: 0, y: 0, vx: 0, vy: 0, raf: 0, last: 0 }; springs.set(card, st); }
return st;
}
function run(card, st) {
function step(t) {
var dt = st.last ? Math.min(t - st.last, 50) / 1000 : 1 / 60; st.last = t;
st.vx += ((st.tx - st.x) * 170 - st.vx * 16) * dt; st.vy += ((st.ty - st.y) * 170 - st.vy * 16) * dt;
st.x += st.vx * dt; st.y += st.vy * dt;
card.style.setProperty('--rx', (-st.y * 6).toFixed(2) + 'deg');
card.style.setProperty('--ry', (st.x * 8).toFixed(2) + 'deg');
card.style.setProperty('--gx', (50 + st.x * 60).toFixed(1) + '%');
card.style.setProperty('--gy', (50 + st.y * 60).toFixed(1) + '%');
if (Math.abs(st.tx - st.x) + Math.abs(st.ty - st.y) + Math.abs(st.vx) + Math.abs(st.vy) > .002) st.raf = requestAnimationFrame(step);
else { st.raf = 0; st.last = 0; }
}
if (!st.raf) st.raf = requestAnimationFrame(step);
}
grid.addEventListener('pointermove', function(e) {
var card = e.target.closest && e.target.closest('.rel-card'); if (!card) return;
var wrap = card.querySelector('.rel-art-wrap'), r = wrap.getBoundingClientRect(), st = spring(card);
var over = e.clientY <= r.bottom;   /* lean only while over the art, not the tracklist */
st.tx = over ? Math.max(-1, Math.min(1, (e.clientX - r.left - r.width / 2) / (r.width / 2))) * .5 : 0;
st.ty = over ? Math.max(-1, Math.min(1, (e.clientY - r.top - r.height / 2) / (r.height / 2))) * .5 : 0;
card.classList.toggle('party-hot', over); run(card, st);
});
grid.addEventListener('pointerout', function(e) {
var card = e.target.closest && e.target.closest('.rel-card');
if (!card || card.contains(e.relatedTarget)) return;
var st = spring(card); st.tx = 0; st.ty = 0; card.classList.remove('party-hot'); run(card, st);
});
})();
(function() {
/* Featured "party" panel: the cover leans toward the pointer on a spring
(real frame time), with a glare that tracks it. Fine pointers only, off
for reduced motion; animations pause while the panel is off screen. */
var party = document.getElementById('party');
if (!party) return;
if ('IntersectionObserver' in window) new IntersectionObserver(function(e) { party.classList.toggle('party-off', !e[0].isIntersecting); }).observe(party);
var art = party.querySelector('.featured-art-hero');
if (!art || !matchMedia('(pointer: fine)').matches || matchMedia('(prefers-reduced-motion: reduce)').matches) return;
var tx = 0, ty = 0, x = 0, y = 0, vx = 0, vy = 0, raf = 0, last = 0;
function step(t) {
var dt = last ? Math.min(t - last, 50) / 1000 : 1 / 60; last = t;
var k = 170, d = 16;
vx += ((tx - x) * k - vx * d) * dt; vy += ((ty - y) * k - vy * d) * dt;
x += vx * dt; y += vy * dt;
art.style.setProperty('--rx', (-y * 9).toFixed(2) + 'deg');
art.style.setProperty('--ry', (x * 11).toFixed(2) + 'deg');
art.style.setProperty('--gx', (50 + x * 60).toFixed(1) + '%');
art.style.setProperty('--gy', (50 + y * 60).toFixed(1) + '%');
if (Math.abs(tx - x) + Math.abs(ty - y) + Math.abs(vx) + Math.abs(vy) > .002) raf = requestAnimationFrame(step); else { raf = 0; last = 0; }
}
function kick() { if (!raf) raf = requestAnimationFrame(step); }
party.addEventListener('pointermove', function(e) {
var r = art.getBoundingClientRect();
tx = Math.max(-1, Math.min(1, (e.clientX - r.left - r.width / 2) / (r.width / 2))) * .5;
ty = Math.max(-1, Math.min(1, (e.clientY - r.top - r.height / 2) / (r.height / 2))) * .5;
art.classList.add('party-hot'); kick();
});
party.addEventListener('pointerleave', function() { tx = 0; ty = 0; art.classList.remove('party-hot'); kick(); });
})();
(function() {
var WARHOL_BG = ['#FF0055','#00B8D9','#FFE600','#FF5400','#E7000B','#0055FF','#7FFF00','#9B5CFF','#00E5FF','#00C853','#FF0080','#FF9F00','#FFD500','#1E40FF','#00FF9D','#FF3D5A'];
function hexToLab(hex) {
var r = parseInt(hex.slice(1,3),16)/255, g = parseInt(hex.slice(3,5),16)/255, b = parseInt(hex.slice(5,7),16)/255;
r = r > .04045 ? Math.pow((r+.055)/1.055, 2.4) : r/12.92;
g = g > .04045 ? Math.pow((g+.055)/1.055, 2.4) : g/12.92;
b = b > .04045 ? Math.pow((b+.055)/1.055, 2.4) : b/12.92;
var X = (r*.4124+g*.3576+b*.1805)/.95047;
var Y = (r*.2126+g*.7152+b*.0722);
var Z = (r*.0193+g*.1192+b*.9505)/1.08883;
var f = function(t){ return t > .008856 ? Math.cbrt(t) : 7.787*t+16/116; };
var fx = f(X), fy = f(Y), fz = f(Z);
return [116*fy-16, 500*(fx-fy), 200*(fy-fz)];
}
function deltaE(a, b) {
return Math.sqrt(Math.pow(a[0]-b[0],2) + Math.pow(a[1]-b[1],2) + Math.pow(a[2]-b[2],2));
}
function cellAt(grid, r, c, dr, dc, COLS, ROWS) {
var rr = r + dr;
if (rr < 0 || rr >= ROWS) return null;
var cc = (c + dc + COLS) % COLS;
return grid.children[rr*COLS + cc];
}
function pickBg(grid, r, c, COLS, ROWS, minDist) {
var pool = WARHOL_BG.slice();
for (var i = pool.length-1; i > 0; i--) { var j = Math.floor(Math.random()*(i+1)); var t = pool[i]; pool[i] = pool[j]; pool[j] = t; }
for (var i = 0; i < pool.length; i++) {
var ok = true;
for (var dr = -1; dr <= 1; dr++) {
for (var dc = -1; dc <= 1; dc++) {
if (dr === 0 && dc === 0) continue;
var n = cellAt(grid, r, c, dr, dc, COLS, ROWS);
if (n && deltaE(hexToLab(pool[i]), hexToLab(n.getAttribute('data-bg'))) < minDist) { ok = false; break; }
}
if (!ok) break;
}
if (ok) return pool[i];
}
return pool[Math.floor(Math.random()*pool.length)];
}
var heroIcon = document.getElementById('hero-icon');
var heroTrack = document.getElementById('hero-photo-track');
if (!heroIcon || !heroTrack) return;
var swapped = false;
function randHue(near) {
for (var t = 0; t < 64; t++) {
var h = Math.floor(Math.random() * 360);
var ok = true;
for (var i = 0; i < near.length; i++) {
var d = Math.abs(h - near[i]);
if (d > 180) d = 360 - d;
if (d < 55) { ok = false; break; }
}
if (ok) return h;
}
return Math.floor(Math.random() * 360);
}
function gridValid(grid) {
var COLS = 4, ROWS = 3;
for (var r = 0; r < ROWS; r++) {
for (var c = 0; c < COLS; c++) {
var cell = grid.children[r*COLS+c];
var hue = parseInt(cell.getAttribute('data-hue'), 10);
for (var dr = -1; dr <= 1; dr++) {
for (var dc = -1; dc <= 1; dc++) {
if (dr === 0 && dc === 0) continue;
var n = cellAt(grid, r, c, dr, dc, COLS, ROWS);
if (!n) continue;
if (deltaE(hexToLab(cell.getAttribute('data-bg')), hexToLab(n.getAttribute('data-bg'))) < 55) return false;
var dh = Math.abs(hue - parseInt(n.getAttribute('data-hue'), 10));
if (dh > 180) dh = 360 - dh;
if (dh < 55) return false;
}
}
}
}
return true;
}
function buildWarholGrid() {
var COLS = 4, ROWS = 3;
var grid = null;
for (var attempt = 0; attempt < 40; attempt++) {
grid = document.createElement('div');
grid.className = 'warhol-grid';
for (var r = 0; r < ROWS; r++) {
for (var c = 0; c < COLS; c++) {
var bg = pickBg(grid, r, c, COLS, ROWS, 55);
var hue = randHue([]);
var nearHue = [];
for (var dr = -1; dr <= 1; dr++) {
for (var dc = -1; dc <= 1; dc++) {
if (dr === 0 && dc === 0) continue;
var n = cellAt(grid, r, c, dr, dc, COLS, ROWS);
if (n) nearHue.push(parseInt(n.getAttribute('data-hue'), 10));
}
}
hue = randHue(nearHue);
var tilt = (Math.random() * 8 - 4).toFixed(2);
var cell = document.createElement('div');
cell.className = 'warhol-cell';
cell.setAttribute('data-bg', bg);
cell.setAttribute('data-hue', hue);
cell.style.background = bg;
cell.innerHTML = '<img src="Images/Cat_pop.webp" alt="" draggable="false" style="filter:sepia(1) saturate(7) hue-rotate(' + hue + 'deg) contrast(1.0);--tilt:' + tilt + 'deg">';
grid.appendChild(cell);
}
}
if (gridValid(grid)) return grid;
}
return grid;
}
function revealWarhol() {
if (swapped) return;
swapped = true;
var img = heroTrack.querySelector('.hero-split-photo');
var frame = heroTrack.querySelector('.hero-photo-frame');
var grid = buildWarholGrid();
frame.innerHTML = '';
frame.appendChild(grid);
var heroLeft = heroTrack.parentNode;
if (heroLeft) heroLeft.classList.add('warhol-on');
frame.setAttribute('aria-label', 'A pop-art cat by Ash Stu');
function finishReveal() {
var left = document.createElement('div');
left.className = 'warhol-half';
left.appendChild(grid.cloneNode(true));
heroTrack.insertBefore(left, img);
heroTrack.classList.add('warhol');
heroTrack.classList.add('pan');
}
var reduced = window.matchMedia && window.matchMedia('(prefers-reduced-motion: reduce)').matches;
if (reduced) {
finishReveal();
return;
}
if (heroTrack.animate) {
var revealAnim = heroTrack.animate(
[{ transform: 'translateX(0)' }, { transform: 'translateX(-50%)' }],
{ duration: 2250, easing: 'linear', fill: 'forwards' }
);
revealAnim.onfinish = function() { revealAnim.cancel(); finishReveal(); };
} else {
heroTrack.classList.add('reveal');
heroTrack.addEventListener('animationend', function done(e) {
if (e.target !== heroTrack) return;
heroTrack.removeEventListener('animationend', done);
heroTrack.classList.remove('reveal');
finishReveal();
});
}
}
var footerLogo = document.querySelector('.footer-logo');
if (footerLogo) {
footerLogo.addEventListener('click', function(e) {
e.preventDefault();
var reducedScroll = window.matchMedia && window.matchMedia('(prefers-reduced-motion: reduce)').matches;
window.scrollTo({ top: 0, behavior: reducedScroll ? 'auto' : 'smooth' });
var fired = false;
function go() { if (fired) return; fired = true; revealWarhol(); }
window.addEventListener('scrollend', function onEnd() {
window.removeEventListener('scrollend', onEnd);
go();
});
setTimeout(go, 1200);
});
}
})();
/* About-section childhood shots are grayscale at rest, color on hover -
a click/tap toggles each photo to color and back, so touch devices
(which have no hover) get the same reveal. Each shot toggles only its
own state - the two images never affect each other. */
(function() {
var shots = document.querySelectorAll('.bio-card-media img:not(.bio-media-main)');
for (var i = 0; i < shots.length; i++) {
shots[i].addEventListener('click', function() { this.classList.toggle('bio-revealed'); });
}
})();