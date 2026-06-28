import os
from flask import Flask
from dotenv import load_dotenv
from linebot.v3 import WebhookParser
from linebot.v3.messaging import Configuration, ApiClient, MessagingApi

from db.database import init_db, save_article
from bot.handler import create_handler
from scheduler.daily_job import get_scheduler
from crawler.base import run_all_crawlers
from ai.summarizer import summarize_article

load_dotenv()

app = Flask(__name__)

configuration = Configuration(access_token=os.getenv("LINE_CHANNEL_ACCESS_TOKEN"))
api_client = ApiClient(configuration)
line_bot_api = MessagingApi(api_client)
parser = WebhookParser(os.getenv("LINE_CHANNEL_SECRET"))

init_db()

# 啟動時爬一次，確保資料庫有資料
def initial_crawl():
    try:
        articles = run_all_crawlers()
        for a in articles:
            summary = summarize_article(a["title"], a["content"])
            save_article(a["title"], a["content"], summary, a["url"], a.get("source", "news"), a.get("published_at", ""))
        print(f"[init] 初始爬取完成，共 {len(articles)} 篇")
    except Exception as e:
        print(f"[init] 初始爬取失敗: {e}")

import threading
threading.Thread(target=initial_crawl, daemon=True).start()

@app.route("/")
def index():
    return "OK", 200

handler_bp = create_handler(line_bot_api, parser)
app.register_blueprint(handler_bp)

scheduler = get_scheduler(line_bot_api)
scheduler.start()

if __name__ == "__main__":
    port = int(os.getenv("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
