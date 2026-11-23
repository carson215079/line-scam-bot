import os
from flask import Flask, request, jsonify
from dotenv import load_dotenv
from linebot.v3 import WebhookParser
from linebot.v3.messaging import Configuration, ApiClient, MessagingApi

from db.database import init_db
from bot.handler import create_handler
from scheduler.daily_job import get_scheduler, run_crawl_job, run_broadcast_job, run_cleanup_job

load_dotenv()

app = Flask(__name__)

configuration = Configuration(access_token=os.getenv("LINE_CHANNEL_ACCESS_TOKEN"))
api_client = ApiClient(configuration)
line_bot_api = MessagingApi(api_client)
parser = WebhookParser(os.getenv("LINE_CHANNEL_SECRET"))

init_db()

def _authorized() -> bool:
    """驗證管理端點的存取金鑰（compare_digest 防時序攻擊）"""
    import hmac
    auth = request.headers.get("Authorization", "")
    key = auth[7:] if auth.startswith("Bearer ") else ""
    admin_key = os.getenv("ADMIN_KEY", "")
    return bool(admin_key) and hmac.compare_digest(key, admin_key)

def _run_background(func, *args):
    import threading
    threading.Thread(target=func, args=args, daemon=True).start()

@app.route("/")
def index():
    return "OK", 200

@app.route("/admin/remigrate")
def remigrate():
    if not _authorized():
        return jsonify({"error": "unauthorized"}), 403
    from scripts.remigrate_articles import run
    _run_background(run)
    return jsonify({"status": "started"}), 200

# --- 管理端點（需 Authorization: Bearer <ADMIN_KEY>）---
# 主要排程由 GitHub Actions 負責（.github/workflows/daily.yml）。
# 以下端點為手動觸發備用，呼叫方式：
#   curl -H "Authorization: Bearer $ADMIN_KEY" https://.../tasks/broadcast

@app.route("/tasks/crawl")
def task_crawl():
    if not _authorized():
        return jsonify({"error": "unauthorized"}), 403
    _run_background(run_crawl_job)
    return jsonify({"status": "crawl started"}), 200

@app.route("/tasks/broadcast")
def task_broadcast():
    if not _authorized():
        return jsonify({"error": "unauthorized"}), 403
    _run_background(run_broadcast_job, line_bot_api)
    return jsonify({"status": "broadcast started"}), 200

@app.route("/tasks/cleanup")
def task_cleanup():
    if not _authorized():
        return jsonify({"error": "unauthorized"}), 403
    _run_background(run_cleanup_job)
    return jsonify({"status": "cleanup started"}), 200

handler_bp = create_handler(line_bot_api, parser, api_client)
app.register_blueprint(handler_bp)

scheduler = get_scheduler(line_bot_api)
scheduler.start()

# 啟動時立即執行一次爬蟲
import threading
threading.Thread(target=run_crawl_job, daemon=True).start()

if __name__ == "__main__":
    port = int(os.getenv("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
