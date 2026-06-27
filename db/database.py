import os
import sqlite3
from contextlib import contextmanager

DB_DEFAULT = "data/scam_bot.db"


def _get_db_path() -> str:
    return os.environ.get("DB_PATH", DB_DEFAULT)


@contextmanager
def _get_conn():
    db_path = _get_db_path()
    os.makedirs(os.path.dirname(db_path), exist_ok=True)
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    try:
        yield conn
        conn.commit()
    finally:
        conn.close()


def init_db() -> None:
    with _get_conn() as conn:
        conn.executescript("""
            CREATE TABLE IF NOT EXISTS articles (
                id          INTEGER PRIMARY KEY AUTOINCREMENT,
                title       TEXT NOT NULL,
                content     TEXT,
                summary     TEXT,
                url         TEXT UNIQUE NOT NULL,
                source      TEXT,
                published_at TEXT,
                created_at  TEXT DEFAULT (datetime('now'))
            );
            CREATE TABLE IF NOT EXISTS users (
                line_user_id TEXT PRIMARY KEY,
                created_at   TEXT DEFAULT (datetime('now'))
            );
        """)


def save_article(title: str, content: str, summary: str, url: str, source: str, published_at: str) -> bool:
    try:
        with _get_conn() as conn:
            conn.execute(
                "INSERT INTO articles (title, content, summary, url, source, published_at) VALUES (?, ?, ?, ?, ?, ?)",
                (title, content, summary, url, source, published_at),
            )
        return True
    except sqlite3.IntegrityError:
        return False


def search_articles(keyword: str) -> list[dict]:
    with _get_conn() as conn:
        rows = conn.execute(
            """
            SELECT id, title, summary, url, source, published_at
            FROM articles
            WHERE title LIKE ? OR content LIKE ?
            ORDER BY created_at DESC
            LIMIT 5
            """,
            (f"%{keyword}%", f"%{keyword}%"),
        ).fetchall()
    return [dict(row) for row in rows]


def get_all_user_ids() -> list[str]:
    with _get_conn() as conn:
        rows = conn.execute("SELECT line_user_id FROM users").fetchall()
    return [row["line_user_id"] for row in rows]


def save_user(line_user_id: str) -> None:
    with _get_conn() as conn:
        conn.execute(
            "INSERT OR IGNORE INTO users (line_user_id) VALUES (?)",
            (line_user_id,),
        )


def get_latest_articles(limit: int = 3) -> list[dict]:
    with _get_conn() as conn:
        rows = conn.execute(
            """
            SELECT id, title, summary, url, source, published_at
            FROM articles
            ORDER BY created_at DESC
            LIMIT ?
            """,
            (limit,),
        ).fetchall()
    return [dict(row) for row in rows]
