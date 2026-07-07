"""
一次性腳本：重新生成所有文章的標題、摘要，並修復壞掉的 Google News 轉址連結。
觸發方式：瀏覽器開啟 /admin/remigrate?key=YOUR_ADMIN_KEY
"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from db.database import get_all_articles_raw, update_article_title_summary
from ai.summarizer import summarize_article
from crawler.base import resolve_url

def is_google_redirect(url: str) -> bool:
    return "news.google.com/rss/articles" in url or "news.google.com/articles" in url

def run():
    articles = get_all_articles_raw()
    total = len(articles)
    print(f"共 {total} 筆文章需要重新整理...")

    for i, article in enumerate(articles, 1):
        try:
            # 修復壞掉的 Google News 轉址連結
            url = article.get("url", "")
            if is_google_redirect(url):
                resolved = resolve_url(url)
                print(f"[{i}/{total}] URL 修復：{resolved[:60]}")
            else:
                resolved = url

            # 重新生成標題與摘要
            result = summarize_article(
                article["title"],
                article["content"] or article["title"]
            )
            update_article_title_summary(
                article["id"],
                result["title"],
                result["summary"],
                url=resolved if resolved != url else None
            )
            print(f"[{i}/{total}] ✓ {result['title'][:30]}")
        except Exception as e:
            print(f"[{i}/{total}] ✗ id={article['id']} 失敗：{e}")

    print("完成！")

if __name__ == "__main__":
    run()
