"""
一次性腳本：把 DB 中仍為 Google News 長連結的文章，解碼為真實短網址。
只更新 url 欄位，不呼叫 AI、不重寫摘要（零 API 花費）。
本機執行：python scripts/fix_urls.py
（本機 IP 可正常呼叫 Google 解碼 API；Render 資料中心 IP 常被擋）
"""
import sys, os, time
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from dotenv import dotenv_values
import psycopg
from crawler.base import resolve_url

def run():
    url = dotenv_values(os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), ".env"))["DATABASE_URL"]
    conn = psycopg.connect(url)
    rows = conn.execute(
        "SELECT id, url FROM articles WHERE url LIKE '%news.google.com%' ORDER BY id"
    ).fetchall()
    total = len(rows)
    print(f"待解碼：{total} 筆")

    ok = fail = dup = 0
    for i, (aid, old_url) in enumerate(rows, 1):
        real = resolve_url(old_url)
        if "news.google.com" not in real:
            try:
                conn.execute("UPDATE articles SET url=%s WHERE id=%s", (real, aid))
                conn.commit()
                ok += 1
                print(f"[{i}/{total}] [OK] {real[:60]}")
            except psycopg.errors.UniqueViolation:
                # 真實網址已存在（同一篇文章的另一條 Google 連結）→ 刪除本重複筆
                conn.rollback()
                conn.execute("DELETE FROM articles WHERE id=%s", (aid,))
                conn.commit()
                dup += 1
                print(f"[{i}/{total}] [DUP] 重複文章，已刪除")
        else:
            fail += 1
            print(f"[{i}/{total}] [FAIL] 解碼失敗，保留原連結")
        time.sleep(0.3)  # 輕微間隔，避免觸發 Google 限流

    conn.close()
    print(f"\n完成！成功 {ok}／重複刪除 {dup}／失敗 {fail}")

if __name__ == "__main__":
    run()
