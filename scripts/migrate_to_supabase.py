"""
一次性腳本：Render PostgreSQL → Supabase 資料遷移。
本機執行：python scripts/migrate_to_supabase.py
需要 .env 內有 OLD_DATABASE_URL（Render External URL）與 NEW_DATABASE_URL（Supabase Session pooler）。
唯讀來源庫、只寫入目標庫，來源資料不會被更動。
"""
import os
import sys
import psycopg
from dotenv import load_dotenv

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
load_dotenv()

OLD_URL = os.getenv("OLD_DATABASE_URL")
NEW_URL = os.getenv("NEW_DATABASE_URL")

TABLES_DDL = """
CREATE TABLE IF NOT EXISTS articles (
    id SERIAL PRIMARY KEY,
    title TEXT NOT NULL,
    content TEXT,
    summary TEXT,
    url TEXT UNIQUE NOT NULL,
    source TEXT,
    published_at TEXT,
    created_at TIMESTAMP DEFAULT NOW()
);
CREATE TABLE IF NOT EXISTS users (
    line_user_id TEXT PRIMARY KEY,
    created_at TIMESTAMP DEFAULT NOW()
);
CREATE TABLE IF NOT EXISTS conversations (
    id SERIAL PRIMARY KEY,
    line_user_id TEXT NOT NULL,
    role TEXT NOT NULL,
    content TEXT NOT NULL,
    created_at TIMESTAMP DEFAULT NOW()
);
"""

def main():
    if not OLD_URL or not NEW_URL:
        print("錯誤：.env 缺少 OLD_DATABASE_URL 或 NEW_DATABASE_URL")
        sys.exit(1)

    print("連線來源庫（Render）...")
    src = psycopg.connect(OLD_URL)
    print("連線目標庫（Supabase）...")
    dst = psycopg.connect(NEW_URL)

    print("在 Supabase 建立資料表...")
    dst.execute(TABLES_DDL)
    dst.commit()

    # --- articles ---
    rows = src.execute(
        "SELECT id, title, content, summary, url, source, published_at, created_at "
        "FROM articles ORDER BY id"
    ).fetchall()
    print(f"搬移 articles：{len(rows)} 筆...")
    for r in rows:
        dst.execute(
            "INSERT INTO articles (id, title, content, summary, url, source, published_at, created_at) "
            "VALUES (%s, %s, %s, %s, %s, %s, %s, %s) ON CONFLICT (url) DO NOTHING",
            r
        )
    # 重設自動編號序列，避免之後新增撞號
    dst.execute("SELECT setval('articles_id_seq', COALESCE((SELECT MAX(id) FROM articles), 1))")

    # --- users ---
    rows = src.execute("SELECT line_user_id, created_at FROM users").fetchall()
    print(f"搬移 users：{len(rows)} 筆...")
    for r in rows:
        dst.execute(
            "INSERT INTO users (line_user_id, created_at) VALUES (%s, %s) ON CONFLICT DO NOTHING",
            r
        )

    # --- conversations ---
    rows = src.execute(
        "SELECT id, line_user_id, role, content, created_at FROM conversations ORDER BY id"
    ).fetchall()
    print(f"搬移 conversations：{len(rows)} 筆...")
    for r in rows:
        dst.execute(
            "INSERT INTO conversations (id, line_user_id, role, content, created_at) "
            "VALUES (%s, %s, %s, %s, %s) ON CONFLICT (id) DO NOTHING",
            r
        )
    dst.execute("SELECT setval('conversations_id_seq', COALESCE((SELECT MAX(id) FROM conversations), 1))")

    dst.commit()

    # --- 筆數核對 ---
    print("\n=== 筆數核對 ===")
    all_match = True
    for table in ["articles", "users", "conversations"]:
        src_n = src.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0]
        dst_n = dst.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0]
        status = "OK" if src_n == dst_n else "不一致！"
        if src_n != dst_n:
            all_match = False
        print(f"{table}: 來源 {src_n} / 目標 {dst_n} → {status}")

    src.close()
    dst.close()
    print("\n遷移完成！" if all_match else "\n⚠️ 筆數不一致，請勿切換，回報錯誤訊息")

if __name__ == "__main__":
    main()
