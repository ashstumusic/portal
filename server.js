'use strict';
/**
 * ashstu.art: optional Node back-end.
 *
 * The public site is static (GitHub Pages). This server adds what static
 * hosting can't: the contact/subscribe form API and the admin inbox. Run it
 * locally or on any Node host; the front-end detects it via GET /api/health
 * and only shows the contact form when it answers.
 *
 *   ADMIN_KEY=$(openssl rand -hex 32) npm start
 *
 * Environment: ADMIN_KEY (required), PORT (3000), DB_PATH (./data.db),
 * TRUST_PROXY (set to "1" behind one reverse proxy so rate limits see real IPs).
 */
const express = require('express');
const helmet = require('helmet');
const compression = require('compression');
const crypto = require('crypto');
const rateLimit = require('express-rate-limit');
const path = require('path');
const db = require('./db');

const PORT = Number(process.env.PORT) || 3000;
const ADMIN_KEY = process.env.ADMIN_KEY;
if (!ADMIN_KEY || ADMIN_KEY.length < 16) {
  console.error('FATAL: set ADMIN_KEY (16+ characters). Example: export ADMIN_KEY="$(openssl rand -hex 32)"');
  process.exit(1);
}
const ADMIN_KEY_HASH = crypto.createHash('sha256').update(ADMIN_KEY).digest();

const app = express();
app.disable('x-powered-by');
if (process.env.TRUST_PROXY) app.set('trust proxy', Number(process.env.TRUST_PROXY) || 1);

app.use(helmet({
  contentSecurityPolicy: {
    directives: {
      defaultSrc: ["'self'"],
      scriptSrc: ["'self'", "'unsafe-inline'", 'https://gc.zgo.at'],   // pages ship inline scripts; GoatCounter analytics
      styleSrc: ["'self'", "'unsafe-inline'"],
      fontSrc: ["'self'", 'data:'],
      imgSrc: ["'self'", 'data:'],
      mediaSrc: ["'self'"],
      connectSrc: ["'self'", 'https://ashstu.goatcounter.com'],
      frameSrc: ['https://docs.google.com'],                           // resume viewer
    },
  },
  crossOriginEmbedderPolicy: false,
}));
app.use(compression());   // gzip/deflate via the standard middleware (handles streams, HEAD and ranges)
app.use(express.json({ limit: '16kb' }));

// ── PUBLIC FILES: allowlist, never the project root wholesale ──────────
// Only these are web-visible. Everything else (data.db, .git, server code,
// node_modules, scripts, package files, .env) is a 404.
const PUBLIC_DIRS = ['Audio', 'Videos', 'Images', 'Icons', 'Fonts', 'Journal', 'redesign', 'redesign-2', 'redesign-3', 'lyrics'];
const PUBLIC_ROOT_FILE = /^\/(?:index|resume|google[\w-]+)\.html$|^\/(?:(?:main|kinetic|psyche)\.[0-9a-f]+\.js|styles(?:\.[0-9a-f]+\.min)?\.css)$|^\/(?:releases|videos|lyrics)\.json$|^\/(?:favicon\.(?:png|webp)|robots\.txt|sitemap\.xml|ash-stu-press-kit\.zip|Ashton[._]Stubblefield_Resume\.pdf)$/;
const BLOCKED_IN_DIRS = /(?:^|\/)\.|\.(?:md|py|sh)$|\/facts\.json$|\/index\.template\.html$/i;
const staticOpts = {
  index: 'index.html',
  dotfiles: 'deny',
  setHeaders(res, filePath) {
    const ext = path.extname(filePath).toLowerCase();
    if (['.mp3', '.mp4', '.zip', '.png', '.jpg', '.webp', '.pdf'].includes(ext)) res.setHeader('Cache-Control', 'public, max-age=604800');
    else if (['.woff2', '.woff', '.ttf', '.otf'].includes(ext)) res.setHeader('Cache-Control', 'public, max-age=2592000, immutable');
    else res.setHeader('Cache-Control', 'public, max-age=300');
  },
};
// The redesign is static HTML. When THIS server serves it, add a marker
// so the page knows the contact API exists. (On GitHub Pages there's no
// marker, so the page never makes a doomed request to /api.)
const fs = require('fs');
const pageCache = {};
for (const site of ['redesign', 'redesign-2']) {
  app.get([`/${site}`, `/${site}/`, `/${site}/index.html`], (req, res, next) => {
    if (req.path === `/${site}`) return res.redirect(301, `/${site}/`);
    const file = path.join(__dirname, site, 'index.html');
    fs.stat(file, (err, st) => {
      if (err) return next();
      if (pageCache[site]?.mtime !== st.mtimeMs) {
        pageCache[site] = { mtime: st.mtimeMs, html: fs.readFileSync(file, 'utf8').replace('<head>', '<head><meta name="contact-api" content="/api/contact">') };
      }
      res.set('Cache-Control', 'no-cache').type('html').send(pageCache[site].html);
    });
  });
}
for (const dir of PUBLIC_DIRS) {
  app.use(`/${dir}`, (req, res, next) => (BLOCKED_IN_DIRS.test(req.path) ? res.status(404).end() : next()),
    express.static(path.join(__dirname, dir), staticOpts));
}
const rootStatic = express.static(__dirname, { ...staticOpts, index: false });
app.get('/', (req, res) => res.sendFile(path.join(__dirname, 'index.html')));
app.use((req, res, next) => (PUBLIC_ROOT_FILE.test(req.path) ? rootStatic(req, res, next) : next()));

// ── RATE LIMITS ─────────────────────────────────────────────────────
const limiter = (max, minutes = 15) => rateLimit({
  windowMs: minutes * 60 * 1000, max, standardHeaders: true, legacyHeaders: false,
  message: { error: 'Too many requests. Please try again in a few minutes.' },
});
const formLimiter = limiter(5);
const accountLimiter = limiter(10);
const adminLimiter = limiter(60);

// ── VALIDATION ──────────────────────────────────────────────────────
// Deliberately strict: no quotes, angle brackets, spaces or control
// characters, so an "email" can never break out of an HTML attribute.
const EMAIL_RE = /^[A-Za-z0-9.!#$%&*+/=?^_`{|}~-]+@[A-Za-z0-9-]+(?:\.[A-Za-z0-9-]+)+$/;
const isEmail = (s) => typeof s === 'string' && s.length <= 254 && EMAIL_RE.test(s);
// Trim, cap length, and strip control characters (keeps newlines in messages).
// Strips control characters and invisible text-direction overrides
// (U+202A-202E, U+2066-2069), which could make a name or email display
// misleadingly in the admin list.
const BIDI = /[\u202A-\u202E\u2066-\u2069]/g;
const clean = (v, max, { multiline = false } = {}) => {
  if (typeof v !== 'string') return '';
  const re = multiline ? /[\u0000-\u0009\u000B\u000C\u000E-\u001F\u007F]/g : /[\u0000-\u001F\u007F]/g;
  return v.replace(re, '').replace(BIDI, '').trim().slice(0, max);
};
// Over-limit text is rejected with a clear message, never silently cut.
const tooLong = (v, max) => typeof v === 'string' && v.trim().length > max;
const LIMITS = { name: 200, email: 254, message: 5000 };
const sendError = (res, status, error) => res.status(status).json({ error });
const isId = (v) => /^\d{1,12}$/.test(v);

// ── STATEMENTS ──────────────────────────────────────────────────────
const q = {
  insertSub: db.prepare('INSERT INTO subscribers (email, name) VALUES (?, ?) ON CONFLICT(email) DO UPDATE SET active = 1'),
  insertMsg: db.prepare('INSERT INTO messages (name, email, message, subscribe) VALUES (?, ?, ?, ?)'),
  unsubscribe: db.prepare('UPDATE subscribers SET active = 0 WHERE email = ?'),
  requestDeletion: db.prepare('INSERT INTO deletion_requests (email) VALUES (?) ON CONFLICT(email) DO UPDATE SET requested_at = datetime(\'now\')'),
  listSubs: db.prepare('SELECT id, email, name, subscribed_at FROM subscribers WHERE active = 1 ORDER BY subscribed_at DESC'),
  searchSubs: db.prepare("SELECT id, email, name, subscribed_at FROM subscribers WHERE active = 1 AND (email LIKE ? ESCAPE '\\' OR name LIKE ? ESCAPE '\\') ORDER BY subscribed_at DESC"),
  listMsgs: db.prepare('SELECT id, name, email, message, subscribe, created_at, read FROM messages ORDER BY created_at DESC LIMIT ? OFFSET ?'),
  searchMsgs: db.prepare("SELECT id, name, email, message, subscribe, created_at, read FROM messages WHERE name LIKE ? ESCAPE '\\' OR email LIKE ? ESCAPE '\\' OR message LIKE ? ESCAPE '\\' ORDER BY created_at DESC LIMIT ? OFFSET ?"),
  countMsgs: db.prepare('SELECT COUNT(*) AS total, COALESCE(SUM(read = 0), 0) AS unread FROM messages'),
  countSearch: db.prepare("SELECT COUNT(*) AS total, COALESCE(SUM(read = 0), 0) AS unread FROM messages WHERE name LIKE ? ESCAPE '\\' OR email LIKE ? ESCAPE '\\' OR message LIKE ? ESCAPE '\\'"),
  markRead: db.prepare('UPDATE messages SET read = 1 WHERE id = ?'),
  deleteMsg: db.prepare('DELETE FROM messages WHERE id = ?'),
  listDeletionRequests: db.prepare('SELECT email, requested_at FROM deletion_requests ORDER BY requested_at'),
  log: db.prepare('INSERT INTO admin_log (action, ip) VALUES (?, ?)'),
  cleanup: db.prepare("DELETE FROM messages WHERE created_at < datetime('now', '-90 days')"),
  cleanupLog: db.prepare("DELETE FROM admin_log WHERE created_at < datetime('now', '-90 days')"),
};
const deleteAllFor = db.transaction((email) => {
  db.prepare('DELETE FROM subscribers WHERE email = ?').run(email);
  db.prepare('DELETE FROM messages WHERE email = ?').run(email);
  db.prepare('DELETE FROM deletion_requests WHERE email = ?').run(email);
});
const likeTerm = (s) => '%' + clean(s, 100).replace(/[\\%_]/g, (c) => '\\' + c) + '%';

// ── PUBLIC API ──────────────────────────────────────────────────────
// The front-end shows the contact form only if this answers.
app.get('/api/health', (req, res) => res.json({ ok: true, contact: true }));

app.post('/api/contact', formLimiter, (req, res) => {
  const body = req.body || {};
  // Honeypot: a hidden field real visitors never fill. Pretend success.
  if (clean(body.website, 200)) return res.json({ ok: true });
  if (tooLong(body.message, LIMITS.message)) return sendError(res, 400, `Please keep your message under ${LIMITS.message.toLocaleString('en-US')} characters (it's ${body.message.trim().length.toLocaleString('en-US')}).`);
  if (tooLong(body.name, LIMITS.name)) return sendError(res, 400, `Please keep your name under ${LIMITS.name} characters.`);
  const name = clean(body.name, LIMITS.name);
  const email = clean(body.email, LIMITS.email).toLowerCase();
  const message = clean(body.message, LIMITS.message, { multiline: true });
  const subscribe = body.subscribe === true;

  if (!isEmail(email)) return sendError(res, 400, 'Please enter a valid email address, like name@example.com.');
  if (!message && !subscribe) return sendError(res, 400, 'Please write a message, or tick "Send me news" to subscribe.');
  if (message && !name) return sendError(res, 400, 'Please add your name to your message.');
  try {
    if (message) q.insertMsg.run(name, email, message, subscribe ? 1 : 0);
    if (subscribe) q.insertSub.run(email, name);
    res.json({ ok: true });
  } catch (err) {
    console.error('[contact]', err);
    sendError(res, 500, 'Something went wrong on our side. Please email ashstumusic@gmail.com instead.');
  }
});

app.post('/api/unsubscribe', accountLimiter, (req, res) => {
  const email = clean(req.body?.email, LIMITS.email).toLowerCase();
  if (!isEmail(email)) return sendError(res, 400, 'Please enter a valid email address.');
  try { q.unsubscribe.run(email); res.json({ ok: true }); } catch (err) { console.error('[unsubscribe]', err); sendError(res, 500, 'Something went wrong.'); }
});

// Deleting by email alone would let anyone erase anyone's data, so this
// records a request; the owner confirms by email and deletes it from /admin.
app.post('/api/delete-my-data', accountLimiter, (req, res) => {
  const email = clean(req.body?.email, LIMITS.email).toLowerCase();
  if (!isEmail(email)) return sendError(res, 400, 'Please enter a valid email address.');
  try {
    q.requestDeletion.run(email);
    res.json({ ok: true, message: 'Request received. We will confirm by email, then delete your data within 30 days.' });
  } catch (err) { console.error('[delete-request]', err); sendError(res, 500, 'Something went wrong.'); }
});

// ── ADMIN API ───────────────────────────────────────────────────────
function adminAuth(req, res, next) {
  const key = req.get('x-admin-key');
  const ok = typeof key === 'string' && crypto.timingSafeEqual(crypto.createHash('sha256').update(key).digest(), ADMIN_KEY_HASH);
  try { q.log.run(ok ? `${req.method} ${req.path}` : 'auth_failure', req.ip); } catch {}
  if (!ok) return sendError(res, 401, 'Invalid or missing admin key.');
  next();
}
const admin = express.Router();
admin.use(adminLimiter, adminAuth);
admin.get('/subscribers', (req, res) => {
  const t = req.query.search ? likeTerm(req.query.search) : null;
  const subs = t ? q.searchSubs.all(t, t) : q.listSubs.all();
  res.json({ count: subs.length, subscribers: subs });
});
admin.get('/messages', (req, res) => {
  const limit = Math.min(Math.max(parseInt(req.query.limit, 10) || 50, 1), 200);
  const offset = Math.max(parseInt(req.query.offset, 10) || 0, 0);
  const t = req.query.search ? likeTerm(req.query.search) : null;
  const msgs = t ? q.searchMsgs.all(t, t, t, limit, offset) : q.listMsgs.all(limit, offset);
  const counts = t ? q.countSearch.get(t, t, t) : q.countMsgs.get();
  res.json({ total: counts.total, unread: counts.unread, messages: msgs });
});
admin.post('/messages/:id/read', (req, res) => {
  if (!isId(req.params.id)) return sendError(res, 400, 'Invalid message id.');
  res.json({ ok: true, changed: q.markRead.run(Number(req.params.id)).changes });
});
admin.delete('/messages/:id', (req, res) => {
  if (!isId(req.params.id)) return sendError(res, 400, 'Invalid message id.');
  res.json({ ok: true, deleted: q.deleteMsg.run(Number(req.params.id)).changes });
});
admin.get('/deletion-requests', (req, res) => res.json({ requests: q.listDeletionRequests.all() }));
admin.post('/delete-data', (req, res) => {
  const email = clean(req.body?.email, LIMITS.email).toLowerCase();
  if (!isEmail(email)) return sendError(res, 400, 'Invalid email.');
  deleteAllFor(email);
  res.json({ ok: true });
});
app.use('/api/admin', admin);
app.get('/admin', adminLimiter, (req, res) => res.sendFile(path.join(__dirname, 'admin.html')));

// ── ERRORS ──────────────────────────────────────────────────────────
app.use('/api', (req, res) => sendError(res, 404, 'Not found.'));
app.use((req, res) => res.status(404).type('text').send('404: page not found. Go to https://ashstu.art/'));
// Malformed JSON, oversized bodies, and anything unexpected: never leak internals.
app.use((err, req, res, next) => {   // eslint-disable-line no-unused-vars
  if (err.type === 'entity.parse.failed') return sendError(res, 400, 'Request body must be valid JSON.');
  if (err.type === 'entity.too.large') return sendError(res, 413, 'Request is too large.');
  console.error('[error]', err);
  sendError(res, 500, 'Something went wrong.');
});

// Retention cleanup (90 days): once at startup, then daily. unref() so the
// timer never keeps the process alive.
try { q.cleanup.run(); q.cleanupLog.run(); } catch (err) { console.error('[cleanup]', err); }
setInterval(() => {
  try { q.cleanup.run(); q.cleanupLog.run(); } catch (err) { console.error('[cleanup]', err); }
}, 24 * 60 * 60 * 1000).unref();

if (require.main === module) {
  const server = app.listen(PORT, () => console.log(`ashstu.art back-end on http://localhost:${PORT}`));
  const shutdown = () => server.close(() => { db.close(); process.exit(0); });
  process.on('SIGINT', shutdown);
  process.on('SIGTERM', shutdown);
}
module.exports = app;
