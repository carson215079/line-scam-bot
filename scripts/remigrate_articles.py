"""
一次性腳本：用新的 AI prompt 重新生成所有文章的標題與摘要。
在 Render Shell 執行：python scripts/remigrate_articles.py
"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from db.database import get_all_articles_raw, update_article_title_summary
from ai.summarizer import summarize_article

def run():
    articles = get_all_articles_raw()
    total = len(articles)
    print(f"共 {total} 筆文章需要重新整理...")

    for i, article in enumerate(articles, 1):
        try:
            result = summarize_article(
                article["title"],
                article["content"] or article["title"]
            )
            update_article_title_summary(article["id"], result["title"], result["summary"])
            print(f"[{i}/{total}] ✓ {result['title'][:30]}")
        except Exception as e:
            print(f"[{i}/{total}] ✗ id={article['id']} 失敗：{e}")

    print("完成！")

if __name__ == "__main__":
    run()
