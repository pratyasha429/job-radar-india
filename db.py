"""SQLite storage. One file (data/jobs.db) holds everything."""
import datetime
import os
import sqlite3

from config import DB_PATH

SCHEMA = """
CREATE TABLE IF NOT EXISTS posts (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    source TEXT, source_id TEXT,
    title TEXT, company TEXT, location_raw TEXT, description TEXT, url TEXT, posted_at TEXT,
    first_seen TEXT, last_seen TEXT,
    role TEXT, city TEXT, is_fresher INTEGER, tagger TEXT, tagged_at TEXT,
    UNIQUE(source, source_id)
);
CREATE TABLE IF NOT EXISTS dupes (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    source TEXT, source_id TEXT, title TEXT, company TEXT, location_raw TEXT,
    duplicate_of INTEGER, reason TEXT, seen TEXT,
    UNIQUE(source, source_id)
);
CREATE TABLE IF NOT EXISTS meta (key TEXT PRIMARY KEY, value INTEGER);
CREATE TABLE IF NOT EXISTS runs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    ts TEXT, fetched INTEGER, already_known INTEGER, new_unique INTEGER,
    dup_same_id INTEGER, dup_exact INTEGER, dup_fuzzy INTEGER,
    tagged INTEGER, tokens_in INTEGER, tokens_out INTEGER, tagger TEXT
);
"""


def now():
    return datetime.datetime.now(datetime.timezone.utc).isoformat(timespec="seconds")


def connect():
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    con = sqlite3.connect(DB_PATH)
    con.row_factory = sqlite3.Row
    con.executescript(SCHEMA)
    return con


def get_meta(con, key):
    row = con.execute("SELECT value FROM meta WHERE key=?", (key,)).fetchone()
    return row["value"] if row else 0


def add_meta(con, key, n=1):
    con.execute("INSERT INTO meta (key, value) VALUES (?, ?) "
                "ON CONFLICT(key) DO UPDATE SET value = value + ?", (key, n, n))
    con.commit()


def all_posts(con):
    return con.execute("SELECT id, company, title, location_raw FROM posts").fetchall()


def known_source_ids(con):
    ids = {(r["source"], r["source_id"]) for r in con.execute("SELECT source, source_id FROM posts")}
    ids |= {(r["source"], r["source_id"]) for r in con.execute("SELECT source, source_id FROM dupes")}
    return ids


def touch(con, sid):
    con.execute("UPDATE posts SET last_seen=? WHERE source=? AND source_id=?", (now(), sid[0], sid[1]))


def insert_post(con, p):
    t = now()
    cur = con.execute(
        "INSERT INTO posts (source, source_id, title, company, location_raw, description, url,"
        " posted_at, first_seen, last_seen) VALUES (?,?,?,?,?,?,?,?,?,?)",
        (p["source"], p["source_id"], p["title"], p["company"], p["location_raw"],
         p["description"], p["url"], p["posted_at"], t, t),
    )
    return cur.lastrowid


def insert_dupe(con, p, dup_of, reason):
    con.execute(
        "INSERT OR IGNORE INTO dupes (source, source_id, title, company, location_raw,"
        " duplicate_of, reason, seen) VALUES (?,?,?,?,?,?,?,?)",
        (p["source"], p["source_id"], p["title"], p["company"], p["location_raw"],
         dup_of, reason, now()),
    )


def untagged(con, limit):
    return con.execute(
        "SELECT id, title, company, location_raw, description FROM posts "
        "WHERE role IS NULL ORDER BY id LIMIT ?", (limit,)
    ).fetchall()


def set_tags(con, post_id, role, city, is_fresher, tagger):
    con.execute(
        "UPDATE posts SET role=?, city=?, is_fresher=?, tagger=?, tagged_at=? WHERE id=?",
        (role, city, int(bool(is_fresher)), tagger, now(), post_id),
    )


def log_run(con, s):
    con.execute(
        "INSERT INTO runs (ts, fetched, already_known, new_unique, dup_same_id, dup_exact,"
        " dup_fuzzy, tagged, tokens_in, tokens_out, tagger) VALUES (?,?,?,?,?,?,?,?,?,?,?)",
        (now(), s["fetched"], s["already_known"], s["new_unique"], s["dup_same_id"],
         s["dup_exact"], s["dup_fuzzy"], s["tagged"], s["tokens_in"], s["tokens_out"], s["tagger"]),
    )
