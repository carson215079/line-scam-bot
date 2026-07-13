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
        conn.execute("""
            CREATE TABLE IF NOT EXISTS conversations (
                id SERIAL PRIMARY KEY,
                line_user_id TEXT NOT NULL,
                role TEXT NOT NULL,
                content TEXT NOT NULL,
                created_at TIMESTAMP DEFAULT NOW()
            )
        """)
        conn.commit()

def article_exists(url) -> bool:
    """檢查 URL 是否已存在（爬蟲先查再呼叫 AI，避免重複文章浪費 API）"""
    with _get_conn() as conn:
        row = conn.execute("SELECT 1 FROM articles WHERE url = %s", (url,)).fetchone()
        return row is not None

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

def get_all_articles_raw():
    """取得所有文章的 id、title、content、url（供重新整理用）"""
    with _get_conn() as conn:
        rows = conn.execute(
            "SELECT id, title, content, url FROM articles ORDER BY id"
        ).fetchall()
    return [{"id": row[0], "title": row[1], "content": row[2], "url": row[3]} for row in rows]

def update_article_title_summary(article_id: int, title: str, summary: str, url: str = None, content: str = None):
    """更新文章的標題與摘要；url / content 有傳入才一併更新"""
    sets = ["title=%s", "summary=%s"]
    params = [title, summary]
    if url:
        sets.append("url=%s")
        params.append(url)
    if content:
        sets.append("content=%s")
        params.append(content)
    params.append(article_id)
    with _get_conn() as conn:
        conn.execute(
            f"UPDATE articles SET {', '.join(sets)} WHERE id=%s",
            tuple(params)
        )
        conn.commit()

def get_db_stats() -> dict:
    with _get_conn() as conn:
        article_count = conn.execute("SELECT COUNT(*) FROM articles").fetchone()[0]
        user_count = conn.execute("SELECT COUNT(*) FROM users").fetchone()[0]
        # created_at 以 UTC 儲存，顯示時轉為台灣時間
        latest = conn.execute(
            "SELECT (created_at AT TIME ZONE 'UTC') AT TIME ZONE 'Asia/Taipei' "
            "FROM articles ORDER BY created_at DESC LIMIT 1"
        ).fetchone()
    return {
        "article_count": article_count,
        "user_count": user_count,
        "latest_crawl": latest[0].strftime("%Y-%m-%d %H:%M") if latest else "無資料"
    }

def save_message(line_user_id, role, content):
    with _get_conn() as conn:
        conn.execute(
            "INSERT INTO conversations (line_user_id, role, content) VALUES (%s, %s, %s)",
            (line_user_id, role, content)
        )
        conn.commit()

def count_recent_user_messages(line_user_id, hours: int = 24) -> int:
    """計算用戶在最近 N 小時內傳送的訊息數（防濫用限額用）"""
    with _get_conn() as conn:
        row = conn.execute(
            "SELECT COUNT(*) FROM conversations "
            "WHERE line_user_id = %s AND role = 'user' "
            "AND created_at >= NOW() - make_interval(hours => %s)",
            (line_user_id, hours)
        ).fetchone()
    return row[0]

def cleanup_old_conversations(days: int = 30) -> int:
    """刪除超過 N 天的舊對話紀錄，回傳刪除筆數"""
    with _get_conn() as conn:
        cur = conn.execute(
            "DELETE FROM conversations WHERE created_at < NOW() - INTERVAL '%s days'" % int(days)
        )
        deleted = cur.rowcount
        conn.commit()
    return deleted

def get_conversation_history(line_user_id, limit=6):
    """取得最近 N 則對話（保持偶數，維持 user/assistant 交替）"""
    with _get_conn() as conn:
        rows = conn.execute(
            "SELECT role, content FROM conversations WHERE line_user_id = %s ORDER BY created_at DESC LIMIT %s",
            (line_user_id, limit)
        ).fetchall()
    # 反轉成時間正序
    history = [{"role": row[0], "content": row[1]} for row in reversed(rows)]
    return history
