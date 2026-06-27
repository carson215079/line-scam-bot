from apscheduler.schedulers.background import BackgroundScheduler
from crawler.base import run_all_crawlers
from ai.summarizer import summarize_article
from db.database import save_article, get_all_user_ids, get_latest_articles
from linebot.v3.messaging import TextMessage, BroadcastRequest

def run_daily_job(line_bot_api):
    print("[scheduler] 開始每日詐騙資訊爬取...")
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

    print(f"[scheduler] 新增 {new_count} 篇文章")

    user_ids = get_all_user_ids()
    if not user_ids:
        print("[scheduler] 無用戶，跳過推播")
        return

    latest = get_latest_articles(limit=3)
    if not latest:
        print("[scheduler] 無文章可推播")
        return

    message_text = "🚨 今日詐騙資訊宣導\n\n"
    for i, article in enumerate(latest, 1):
        message_text += f"{i}. {article['title']}\n{article['summary']}\n🔗 {article['url']}\n\n"
    message_text += "如有疑問請撥打 165 反詐騙諮詢專線"

    try:
        line_bot_api.broadcast(BroadcastRequest(messages=[TextMessage(text=message_text)]))
        print(f"[scheduler] 推播完成")
    except Exception as e:
        print(f"[scheduler] 推播失敗: {e}")

def get_scheduler(line_bot_api):
    scheduler = BackgroundScheduler(timezone="Asia/Taipei")
    scheduler.add_job(
        func=lambda: run_daily_job(line_bot_api),
        trigger="cron",
        hour=9,
        minute=0,
        id="daily_scam_news"
    )
    return scheduler
