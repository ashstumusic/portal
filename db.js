'use strict';
/**
 * Data layer: one SQLite file (better-sqlite3, synchronous and fast).
 * Schema is created/migrated on startup. DB_PATH overrides the location
 * (tests use a temporary file so the real data is never touched).
 */
const Database = require('better-sqlite3');
const path = require('path');

const db = new Database(process.env.DB_PATH || path.join(__dirname, 'data.db'));
db.pragma('journal_mode = WAL');
db.pragma('foreign_keys = ON');
db.pragma('busy_timeout = 5000');   // wait instead of failing if another process holds a lock

db.exec(`
  CREATE TABLE IF NOT EXISTS subscribers (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    email         TEXT UNIQUE NOT NULL CHECK (length(email) <= 254),
    name          TEXT NOT NULL DEFAULT '' CHECK (length(name) <= 200),
    subscribed_at TEXT NOT NULL DEFAULT (datetime('now')),
    active        INTEGER NOT NULL DEFAULT 1 CHECK (active IN (0, 1))
  );
  CREATE TABLE IF NOT EXISTS messages (
    id         INTEGER PRIMARY KEY AUTOINCREMENT,
    name       TEXT NOT NULL CHECK (length(name) <= 200),
    email      TEXT NOT NULL CHECK (length(email) <= 254),
    message    TEXT NOT NULL CHECK (length(message) <= 5000),
    subscribe  INTEGER NOT NULL DEFAULT 0 CHECK (subscribe IN (0, 1)),
    created_at TEXT NOT NULL DEFAULT (datetime('now')),
    read       INTEGER NOT NULL DEFAULT 0 CHECK (read IN (0, 1))
  );
  CREATE TABLE IF NOT EXISTS deletion_requests (
    email        TEXT PRIMARY KEY,
    requested_at TEXT NOT NULL DEFAULT (datetime('now'))
  );
  CREATE TABLE IF NOT EXISTS admin_log (
    id         INTEGER PRIMARY KEY AUTOINCREMENT,
    action     TEXT NOT NULL,
    ip         TEXT,
    created_at TEXT NOT NULL DEFAULT (datetime('now'))
  );
  CREATE INDEX IF NOT EXISTS idx_messages_created   ON messages(created_at DESC);
  CREATE INDEX IF NOT EXISTS idx_messages_read      ON messages(read, created_at DESC);
  CREATE INDEX IF NOT EXISTS idx_messages_email     ON messages(email);
  CREATE INDEX IF NOT EXISTS idx_subscribers_active ON subscribers(active, subscribed_at DESC);
`);
// (subscribers.email is UNIQUE, which already creates its index.)

module.exports = db;
