import os
import psycopg
from dotenv import load_dotenv

load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL")

def _get_conn():
    return psycopg.connect(DATABASE_URL)

def init_db():
    with _get_conn() as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS articles (
                id SERIAL PRIMARY KEY,
                title TEXT NOT NULL,
                content TEXT,
                summary TEXT,
                url TEXT UNIQUE NOT NULL,
                source TEXT,
                published_at TEXT,
                created_at TIMESTAMP DEFAULT NOW()
            )
        """)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS users (
                line_user_id TEXT PRIMARY KEY,
                created_at TIMESTAMP DEFAULT NOW()
            )
        """)
        conn.commit()

def save_article(title, content, summary, url, source, published_at):
    try:
        with _get_conn() as conn:
            conn.execute(
                "INSERT INTO articles (title, content, summary, url, source, published_at) VALUES (%s, %s, %s, %s, %s, %s)",
                (title, content, summary, url, source, published_at)
            )
            conn.commit()
            return True
    except Exception:
        return False

def search_articles(keyword):
    with _get_conn() as conn:
        rows = conn.execute(
            "SELECT id, title, summary, url, source, published_at FROM articles WHERE title ILIKE %s OR content ILIKE %s ORDER BY created_at DESC LIMIT 5",
            (f"%{keyword}%", f"%{keyword}%")
        ).fetchall()
        cols = ["id", "title", "summary", "url", "source", "published_at"]
        return [dict(zip(cols, row)) for row in rows]

def get_all_user_ids():
    with _get_conn() as conn:
        rows = conn.execute("SELECT line_user_id FROM users").fetchall()
        return [row[0] for row in rows]

def save_user(line_user_id):
    with _get_conn() as conn:
        conn.execute(
            "INSERT INTO users (line_user_id) VALUES (%s) ON CONFLICT DO NOTHING",
            (line_user_id,)
        )
        conn.commit()

def get_latest_articles(limit=3):
    with _get_conn() as conn:
        rows = conn.execute(
            "SELECT id, title, summary, url, source, published_at FROM articles ORDER BY created_at DESC LIMIT %s",
            (limit,)
        ).fetchall()
        cols = ["id", "title", "summary", "url", "source", "published_at"]
        return [dict(zip(cols, row)) for row in rows]
