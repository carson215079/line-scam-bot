from apscheduler.schedulers.background import BackgroundScheduler
from crawler.base import run_all_crawlers
from ai.summarizer import summarize_article
from db.database import save_article, get_all_user_ids, get_latest_articles
from linebot.v3.messaging import TextMessage, BroadcastRequest

def run_crawl_job():
    """每 3 小時執行一次，爬取新文章存入資料庫。"""
    print("[crawler] 開始定期爬取詐騙資訊...")
    articles = run_all_crawlers()
    new_count = 0
    for article in articles:
        summary = summarize_article(article["title"], article["content"])
        saved = save_article(
            title=article["title"],
            content=article["content"],
            summary=summary,
            url=article["url"],
            source=article.get("source", "news"),
            published_at=article.get("published_at", "")
        )
        if saved:
            new_count += 1
    print(f"[crawler] 新增 {new_count} 篇文章")

def run_broadcast_job(line_bot_api):
    """每天早上 9:00 執行，推播今日詐騙摘要給所有用戶。"""
    print("[broadcast] 開始每日推播...")

    user_ids = get_all_user_ids()
    if not user_ids:
        print("[broadcast] 無用戶，跳過推播")
        return

    latest = get_latest_articles(limit=5)
    if not latest:
        print("[broadcast] 無文章可推播")
        return

    message_text = "🚨 今日詐騙資訊宣導 🚨\n"
    message_text += "═══════════════════\n\n"
    for i, article in enumerate(latest, 1):
        message_text += f"【{i}】{article['title']}\n\n"
        message_text += f"📋 {article['summary']}\n\n"
        message_text += f"🔗 原文連結：\n{article['url']}\n"
        message_text += "───────────────────\n\n"
    message_text += "⚠️ 如有疑問請撥打 165 反詐騙諮詢專線"

    try:
        line_bot_api.broadcast(BroadcastRequest(messages=[TextMessage(text=message_text)]))
        print("[broadcast] 推播完成")
    except Exception as e:
        print(f"[broadcast] 推播失敗: {e}")

def get_scheduler(line_bot_api):
    scheduler = BackgroundScheduler(timezone="Asia/Taipei")

    # 每 3 小時爬取一次
    scheduler.add_job(
        func=run_crawl_job,
        trigger="interval",
        hours=3,
        id="crawl_job"
    )

    # 每天早上 9:00 推播
    scheduler.add_job(
        func=lambda: run_broadcast_job(line_bot_api),
        trigger="cron",
        hour=9,
        minute=0,
        id="broadcast_job"
    )

    return scheduler
