import os
from flask import Flask, request, jsonify
from dotenv import load_dotenv
from linebot.v3 import WebhookParser
from linebot.v3.messaging import Configuration, ApiClient, MessagingApi

from db.database import init_db
from bot.handler import create_handler
from scheduler.daily_job import get_scheduler, run_crawl_job

load_dotenv()

app = Flask(__name__)

configuration = Configuration(access_token=os.getenv("LINE_CHANNEL_ACCESS_TOKEN"))
api_client = ApiClient(configuration)
line_bot_api = MessagingApi(api_client)
parser = WebhookParser(os.getenv("LINE_CHANNEL_SECRET"))

init_db()

@app.route("/")
def index():
    return "OK", 200

@app.route("/admin/remigrate")
def remigrate():
    key = request.args.get("key", "")
    admin_key = os.getenv("ADMIN_KEY", "")
    # ADMIN_KEY 未設定時一律拒絕，避免空字串比對通過
    if not admin_key or key != admin_key:
        return jsonify({"error": "unauthorized"}), 403
    import threading
    from scripts.remigrate_articles import run
    threading.Thread(target=run, daemon=True).start()
    return jsonify({"status": "started"}), 200

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
