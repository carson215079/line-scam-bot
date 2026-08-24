"""
一次性維護腳本：重新整理所有文章的標題與摘要
（抓取文章內文 → 用 AI 讀全文重新生成標題與摘要）。
用途：改了摘要 prompt 後，讓舊文章一併套用新格式。
觸發方式：瀏覽器開啟 /admin/remigrate?key=YOUR_ADMIN_KEY
"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from db.database import get_all_articles_raw, update_article_title_summary
from ai.summarizer import summarize_article
from crawler.base import fetch_article_text

def run():
    articles = get_all_articles_raw()
    total = len(articles)
    print(f"共 {total} 筆文章需要重新整理...")

    for i, article in enumerate(articles, 1):
        try:
            # 抓取內文讓 AI 讀全文；抓不到 fallback 用既有 content 或標題
            fetched = fetch_article_text(article["url"])
            content = fetched or article["content"] or article["title"]

            result = summarize_article(article["title"], content)
            update_article_title_summary(
                article["id"],
                result["title"],
                result["summary"],
                content=fetched or None
            )
            tag = "全文" if fetched else "標題"
            print(f"[{i}/{total}] OK ({tag}) {result['title'][:30]}")
        except Exception as e:
            print(f"[{i}/{total}] FAIL id={article['id']}：{e}")

    print("完成！")

if __name__ == "__main__":
    run()
