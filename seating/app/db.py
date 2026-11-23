"""SQLite storage. One file, no server to run."""
import json
import os
import sqlite3
import threading
import time

_local = threading.local()
_path = None

SCHEMA = """
CREATE TABLE IF NOT EXISTS events (
  id TEXT PRIMARY KEY,
  manage_hash TEXT NOT NULL,
  guest_slug TEXT NOT NULL UNIQUE,
  title TEXT NOT NULL DEFAULT '',
  event_date TEXT,
  venue TEXT NOT NULL DEFAULT '',
  design TEXT NOT NULL DEFAULT 'minimal',
  chart_size TEXT NOT NULL DEFAULT '18x24',
  chart_layout TEXT NOT NULL DEFAULT 'table',
  sort_by TEXT NOT NULL DEFAULT 'last',
  paper TEXT NOT NULL DEFAULT 'letter',
  card_order TEXT NOT NULL DEFAULT 'table',
  region TEXT NOT NULL DEFAULT 'us',
  status TEXT NOT NULL DEFAULT 'draft',
  paid_at REAL,
  customer_email TEXT,
  version INTEGER NOT NULL DEFAULT 1,
  raw_json TEXT,
  mapping_json TEXT,
  dup_ack_json TEXT NOT NULL DEFAULT '[]',
  step TEXT NOT NULL DEFAULT 'map',
  created_at REAL NOT NULL,
  updated_at REAL NOT NULL
);
CREATE TABLE IF NOT EXISTS guests (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  event_id TEXT NOT NULL REFERENCES events(id) ON DELETE CASCADE,
  name TEXT NOT NULL,
  table_label TEXT NOT NULL DEFAULT '',
  last TEXT NOT NULL DEFAULT '',
  position INTEGER NOT NULL
);
CREATE INDEX IF NOT EXISTS guests_event ON guests(event_id, position);
CREATE TABLE IF NOT EXISTS checkout_sessions (
  session_id TEXT PRIMARY KEY,
  event_id TEXT NOT NULL,
  created_at REAL NOT NULL,
  status TEXT NOT NULL DEFAULT 'open'
);
CREATE TABLE IF NOT EXISTS payments (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  event_id TEXT NOT NULL,
  session_id TEXT NOT NULL UNIQUE,
  amount INTEGER NOT NULL,
  currency TEXT NOT NULL,
  duplicate INTEGER NOT NULL DEFAULT 0,
  created_at REAL NOT NULL
);
CREATE TABLE IF NOT EXISTS webhook_events (
  provider_event_id TEXT PRIMARY KEY,
  type TEXT NOT NULL,
  received_at REAL NOT NULL
);
CREATE TABLE IF NOT EXISTS funnel (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  name TEXT NOT NULL,
  event_id TEXT,
  source TEXT,
  created_at REAL NOT NULL
);
CREATE TABLE IF NOT EXISTS meta (k TEXT PRIMARY KEY, v TEXT);
"""


def init(path):
    global _path
    _path = path
    os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
    c = conn()
    c.executescript(SCHEMA)
    c.commit()


def conn():
    c = getattr(_local, "c", None)
    if c is None or getattr(_local, "path", None) != _path:
        c = sqlite3.connect(_path, timeout=10, isolation_level=None)
        c.row_factory = sqlite3.Row
        c.execute("PRAGMA foreign_keys=ON")
        c.execute("PRAGMA journal_mode=WAL")
        _local.c = c
        _local.path = _path
    return c


def q(sql, *args):
    return conn().execute(sql, args).fetchall()


def q1(sql, *args):
    r = conn().execute(sql, args).fetchone()
    return r


def x(sql, *args):
    return conn().execute(sql, args)


def track(name, event_id=None, source=None):
    x("INSERT INTO funnel(name, event_id, source, created_at) VALUES (?,?,?,?)", name, event_id, source, time.time())


def jload(s, default):
    try:
        return json.loads(s) if s else default
    except ValueError:
        return default
