const express = require('express');
const helmet = require('helmet');
const crypto = require('crypto');
const rateLimit = require('express-rate-limit');
const zlib = require('zlib');
const path = require('path');
const db = require('./db');

const app = express();
const PORT = process.env.PORT || 3000;
const ADMIN_KEY = process.env.ADMIN_KEY;

if (!ADMIN_KEY) {
  console.error('FATAL: ADMIN_KEY environment variable not set.');
  console.error('Run: export ADMIN_KEY="$(openssl rand -hex 32)"');
  process.exit(1);
}

const ADMIN_KEY_HASH = crypto.createHash('sha256').update(ADMIN_KEY).digest('hex');

app.use(helmet({
  contentSecurityPolicy: {
    directives: {
      defaultSrc: ["'self'"],
      scriptSrc: ["'self'", "'unsafe-inline'"],
      styleSrc: ["'self'", "'unsafe-inline'", "https://fonts.googleapis.com"],
      fontSrc: ["'self'", "https://fonts.gstatic.com"],
      imgSrc: ["'self'", "data:"],
      mediaSrc: ["'self'"],
      connectSrc: ["'self'"]
    }
  },
  crossOriginEmbedderPolicy: false
}));
app.use(express.json({ limit: '16kb' }));

app.use(function(req, res, next) {
  var ext = path.extname(req.path).toLowerCase();
  if (['.html', '.css', '.js', '.json', '.svg', '.ttf'].indexOf(ext) === -1 && ext !== '') return next();
  var accept = req.headers['accept-encoding'] || '';
  if (!accept.includes('gzip')) return next();
  var origEnd = res.end, origWrite = res.write, chunks = [];
  res.write = function(chunk) { chunks.push(Buffer.isBuffer(chunk) ? chunk : Buffer.from(chunk)); };
  res.end = function(chunk) {
    if (chunk) chunks.push(Buffer.isBuffer(chunk) ? chunk : Buffer.from(chunk));
    var buf = Buffer.concat(chunks);
    zlib.gzip(buf, function(err, compressed) {
      if (err) { origEnd.call(res, buf); return; }
      res.setHeader('Content-Encoding', 'gzip');
      res.setHeader('Content-Length', compressed.length);
      res.removeHeader('Content-Length');
      origWrite.call(res, compressed);
      origEnd.call(res);
    });
  };
  next();
});

app.use(express.static(__dirname, {
  index: 'index.html',
  maxAge: '1h',
  setHeaders: function(res, filePath) {
    var ext = path.extname(filePath).toLowerCase();
    if (ext === '.mp3' || ext === '.mp4' || ext === '.zip') {
      res.setHeader('Cache-Control', 'public, max-age=604800');
    } else if (ext === '.png' || ext === '.jpg' || ext === '.webp') {
      res.setHeader('Cache-Control', 'public, max-age=604800');
    } else if (ext === '.woff2' || ext === '.woff' || ext === '.ttf' || ext === '.otf') {
      res.setHeader('Cache-Control', 'public, max-age=2592000, immutable');
    }
  }
}));

var contactLimiter = rateLimit({
  windowMs: 15 * 60 * 1000,
  max: 5,
  message: { error: 'Too many submissions. Try again in 15 minutes.' },
  standardHeaders: true,
  legacyHeaders: false
});

var adminLimiter = rateLimit({
  windowMs: 15 * 60 * 1000,
  max: 30,
  message: { error: 'Too many requests.' },
  standardHeaders: true,
  legacyHeaders: false
});

var stmtInsertSub = db.prepare(
  'INSERT OR IGNORE INTO subscribers (email, name) VALUES (?, ?)'
);
var stmtInsertMsg = db.prepare(
  'INSERT INTO messages (name, email, message, subscribe) VALUES (?, ?, ?, ?)'
);
var stmtGetSubs = db.prepare(
  'SELECT id, email, name, subscribed_at FROM subscribers WHERE active = 1 ORDER BY subscribed_at DESC'
);
var stmtGetMsgs = db.prepare(
  'SELECT id, name, email, message, subscribe, created_at, read FROM messages ORDER BY created_at DESC LIMIT ? OFFSET ?'
);
var stmtMsgCount = db.prepare(
  'SELECT COUNT(*) as total, SUM(CASE WHEN read = 0 THEN 1 ELSE 0 END) as unread FROM messages'
);
var stmtMarkRead = db.prepare(
  'UPDATE messages SET read = 1 WHERE id = ?'
);
var stmtDeleteMsg = db.prepare(
  'DELETE FROM messages WHERE id = ?'
);
var stmtUnsubscribe = db.prepare(
  'UPDATE subscribers SET active = 0 WHERE email = ?'
);
var stmtDeleteSub = db.prepare(
  'DELETE FROM subscribers WHERE email = ?'
);
var stmtDeleteMsgsByEmail = db.prepare(
  'DELETE FROM messages WHERE email = ?'
);
var stmtSearchMsgs = db.prepare(
  'SELECT id, name, email, message, subscribe, created_at, read FROM messages WHERE name LIKE ? OR email LIKE ? OR message LIKE ? ORDER BY created_at DESC LIMIT ? OFFSET ?'
);
var stmtSearchMsgCount = db.prepare(
  "SELECT COUNT(*) as total, SUM(CASE WHEN read = 0 THEN 1 ELSE 0 END) as unread FROM messages WHERE name LIKE ? OR email LIKE ? OR message LIKE ?"
);
var stmtSearchSubs = db.prepare(
  'SELECT id, email, name, subscribed_at FROM subscribers WHERE active = 1 AND (email LIKE ? OR name LIKE ?) ORDER BY subscribed_at DESC'
);
var stmtAdminLog = db.prepare(
  'INSERT INTO admin_log (action, ip) VALUES (?, ?)'
);
var stmtCleanup = db.prepare(
  "DELETE FROM messages WHERE created_at < datetime('now', '-90 days')"
);

function validateEmail(email) {
  return /^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(email);
}

function sanitize(str, maxLen) {
  if (typeof str !== 'string') return '';
  return str.trim().slice(0, maxLen);
}

function getIP(req) {
  return req.headers['x-forwarded-for'] || req.socket.remoteAddress || '';
}

app.post('/api/contact', contactLimiter, function(req, res) {
  var name = sanitize(req.body.name, 200);
  var email = sanitize(req.body.email, 320);
  var message = sanitize(req.body.message, 5000);
  var subscribe = !!req.body.subscribe;

  if (!validateEmail(email)) {
    return res.status(400).json({ error: 'Invalid email address.' });
  }
  if (message && !name) {
    return res.status(400).json({ error: 'Please include your name with your message.' });
  }
  if (!message && !subscribe) {
    return res.status(400).json({ error: 'Please write a message or check "Subscribe to updates".' });
  }

  try {
    if (message) {
      stmtInsertMsg.run(name, email, message, subscribe ? 1 : 0);
    }
    if (subscribe) {
      stmtInsertSub.run(email, name);
    }
    res.json({ ok: true });
  } catch (err) {
    console.error('[contact]', err.message);
    res.status(500).json({ error: 'Something went wrong. Please try again.' });
  }
});

app.post('/api/subscribe', contactLimiter, function(req, res) {
  var email = sanitize(req.body.email, 320);
  var name = sanitize(req.body.name, 200);

  if (!validateEmail(email)) {
    return res.status(400).json({ error: 'Invalid email address.' });
  }

  try {
    stmtInsertSub.run(email, name);
    res.json({ ok: true });
  } catch (err) {
    console.error('[subscribe]', err.message);
    res.status(500).json({ error: 'Something went wrong.' });
  }
});

app.post('/api/unsubscribe', function(req, res) {
  var email = sanitize(req.body.email, 320);
  if (!validateEmail(email)) {
    return res.status(400).json({ error: 'Invalid email.' });
  }
  try {
    stmtUnsubscribe.run(email);
    res.json({ ok: true });
  } catch (err) {
    console.error('[unsubscribe]', err.message);
    res.status(500).json({ error: 'Something went wrong.' });
  }
});

app.post('/api/delete-my-data', contactLimiter, function(req, res) {
  var email = sanitize(req.body.email, 320);
  if (!validateEmail(email)) {
    return res.status(400).json({ error: 'Invalid email.' });
  }
  try {
    stmtDeleteSub.run(email);
    stmtDeleteMsgsByEmail.run(email);
    res.json({ ok: true, message: 'All data associated with ' + email + ' has been deleted.' });
  } catch (err) {
    console.error('[delete-data]', err.message);
    res.status(500).json({ error: 'Something went wrong.' });
  }
});

function adminAuth(req, res, next) {
  var key = req.headers['x-admin-key'];
  if (!key) {
    return res.status(401).json({ error: 'Missing authentication.' });
  }
  var keyHash = crypto.createHash('sha256').update(key).digest('hex');
  if (!crypto.timingSafeEqual(Buffer.from(keyHash), Buffer.from(ADMIN_KEY_HASH))) {
    stmtAdminLog.run('auth_failure', getIP(req));
    return res.status(401).json({ error: 'Invalid key.' });
  }
  stmtAdminLog.run(req.method + ' ' + req.path, getIP(req));
  next();
}

app.get('/api/admin/subscribers', adminLimiter, adminAuth, function(req, res) {
  var search = req.query.search ? '%' + req.query.search + '%' : null;
  try {
    var subs;
    if (search) {
      subs = stmtSearchSubs.all(search, search);
    } else {
      subs = stmtGetSubs.all();
    }
    res.json({ count: subs.length, subscribers: subs });
  } catch (err) {
    console.error('[admin/subs]', err.message);
    res.status(500).json({ error: 'Failed to fetch subscribers: ' + err.message });
  }
});

app.get('/api/admin/messages', adminLimiter, adminAuth, function(req, res) {
  var limit = Math.min(parseInt(req.query.limit) || 50, 200);
  var offset = parseInt(req.query.offset) || 0;
  var search = req.query.search ? '%' + req.query.search + '%' : null;
  try {
    var msgs, counts;
    if (search) {
      msgs = stmtSearchMsgs.all(search, search, search, limit, offset);
      counts = stmtSearchMsgCount.get(search, search, search);
    } else {
      msgs = stmtGetMsgs.all(limit, offset);
      counts = stmtMsgCount.get();
    }
    res.json({ total: counts.total || 0, unread: counts.unread || 0, messages: msgs });
  } catch (err) {
    console.error('[admin/msgs]', err.message);
    res.status(500).json({ error: 'Failed to fetch messages: ' + err.message });
  }
});

app.post('/api/admin/messages/:id/read', adminLimiter, adminAuth, function(req, res) {
  try {
    var result = stmtMarkRead.run(parseInt(req.params.id));
    res.json({ ok: true, changed: result.changes });
  } catch (err) {
    console.error('[admin/read]', err.message);
    res.status(500).json({ error: 'Failed to mark read: ' + err.message });
  }
});

app.delete('/api/admin/messages/:id', adminLimiter, adminAuth, function(req, res) {
  try {
    var result = stmtDeleteMsg.run(parseInt(req.params.id));
    res.json({ ok: true, deleted: result.changes });
  } catch (err) {
    console.error('[admin/delete]', err.message);
    res.status(500).json({ error: 'Failed to delete: ' + err.message });
  }
});

app.get('/admin', adminLimiter, function(req, res) {
  res.sendFile(path.join(__dirname, 'admin.html'));
});

app.get('*', function(req, res) {
  res.sendFile(path.join(__dirname, 'index.html'));
});

setInterval(function() {
  try {
    var result = stmtCleanup.run();
    if (result.changes > 0) console.log('[cleanup] Deleted ' + result.changes + ' old messages');
  } catch (err) {
    console.error('[cleanup]', err.message);
  }
}, 24 * 60 * 60 * 1000);

app.listen(PORT, function() {
  console.log('ashstu.com running on http://localhost:' + PORT);
});
