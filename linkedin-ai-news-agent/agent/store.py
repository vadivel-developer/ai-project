import sqlite3

from . import config

SCHEMA = """
CREATE TABLE IF NOT EXISTS videos (
    video_id TEXT PRIMARY KEY,
    title TEXT,
    channel TEXT,
    url TEXT,
    status TEXT DEFAULT 'drafted'  -- drafted | approved | published | skipped
)
"""


def connect(path=None) -> sqlite3.Connection:
    conn = sqlite3.connect(path or config.DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute(SCHEMA)
    return conn


def seen(conn, video_id: str) -> bool:
    return conn.execute("SELECT 1 FROM videos WHERE video_id=?", (video_id,)).fetchone() is not None


def add(conn, video: dict) -> None:
    conn.execute(
        "INSERT OR IGNORE INTO videos (video_id, title, channel, url) VALUES (?,?,?,?)",
        (video["id"], video["title"], video["channel"], video["url"]),
    )
    conn.commit()


def set_status(conn, video_id: str, status: str) -> None:
    conn.execute("UPDATE videos SET status=? WHERE video_id=?", (status, video_id))
    conn.commit()


def list_all(conn):
    return conn.execute("SELECT * FROM videos ORDER BY rowid DESC").fetchall()
