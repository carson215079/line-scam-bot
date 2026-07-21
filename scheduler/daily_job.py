from apscheduler.schedulers.background import BackgroundScheduler
from crawler.base import run_all_crawlers, fetch_article_text
from ai.summarizer import summarize_article
from db.database import (
    save_article, article_exists, get_all_user_ids,
    get_articles_for_broadcast, mark_articles_broadcasted,
    cleanup_old_conversations, get_db_size_mb, trim_oldest_articles
)

# 免費方案容量 500 MB，達 80%（400 MB）時自動刪最舊的 20% 文章
DB_SIZE_LIMIT_MB = 400
from linebot.v3.messaging import TextMessage, BroadcastRequest

def run_crawl_job():
    """每 3 小時執行一次，爬取新文章存入資料庫。"""
    print("[crawler] 開始定期爬取詐騙資訊...")
    articles = run_all_crawlers()
    new_count = 0
    for article in articles:
        # 已存在的文章直接跳過，避免重複呼叫 AI 浪費 API 額度
        if article_exists(article["url"]):
            continue
        # 抓取文章內文讓 AI 讀全文摘要；抓不到就 fallback 用標題
        content = fetch_article_text(article["url"]) or article["content"]
        result = summarize_article(article["title"], content)
        saved = save_article(
            title=result["title"],
            content=content,
            summary=result["summary"],
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

    # 只取「尚未推播過」的最新文章，避免每天重複推同幾篇
    latest = get_articles_for_broadcast(limit=5)
    if not latest:
        print("[broadcast] 無新文章可推播（今日略過）")
        return

    # 每篇文章一則訊息，好讀且預覽卡片各歸各（LINE 單次上限 5 則）
    total = len(latest)
    messages = []
    for i, article in enumerate(latest, 1):
        text = f"🚨 今日詐騙資訊宣導【{i}/{total}】\n\n"
        text += f"📌 {article['title']}\n\n"
        text += f"📋 {article['summary']}\n\n"
        text += f"🔗 {article['url']}"
        if i == total:
            text += "\n\n⚠️ 如有疑問請撥打 165 反詐騙諮詢專線"
        messages.append(TextMessage(text=text))

    try:
        line_bot_api.broadcast(BroadcastRequest(messages=messages))
        # 推播成功才標記已推，避免發送失敗卻被記為已推導致漏推
        mark_articles_broadcasted([a["id"] for a in latest])
        print(f"[broadcast] 推播完成（{total} 則）")
    except Exception as e:
        print(f"[broadcast] 推播失敗: {e}")

def run_cleanup_job():
    """每天凌晨 4:00 執行：清除 30 天前舊對話 + 容量超標時刪最舊文章。"""
    try:
        deleted = cleanup_old_conversations(days=30)
        print(f"[cleanup] 清除 {deleted} 筆舊對話")
    except Exception as e:
        print(f"[cleanup] 對話清理失敗: {e}")

    # 容量保護：超過門檻才動作，每次只刪最舊的 20%
    try:
        size_mb = get_db_size_mb()
        if size_mb >= DB_SIZE_LIMIT_MB:
            trimmed = trim_oldest_articles(percent=20)
            print(f"[cleanup] 容量 {size_mb}MB 超標，刪除最舊 {trimmed} 篇文章")
        else:
            print(f"[cleanup] 容量 {size_mb}MB，正常")
    except Exception as e:
        print(f"[cleanup] 容量檢查失敗: {e}")

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

    # 每天凌晨 4:00 清理舊對話
    scheduler.add_job(
        func=run_cleanup_job,
        trigger="cron",
        hour=4,
        minute=0,
        id="cleanup_job"
    )

    return scheduler
