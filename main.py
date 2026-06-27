import os
from flask import Flask
from dotenv import load_dotenv
from linebot.v3 import WebhookParser
from linebot.v3.messaging import Configuration, ApiClient, MessagingApi

from db.database import init_db
from bot.handler import create_handler
from scheduler.daily_job import get_scheduler

load_dotenv()

app = Flask(__name__)

configuration = Configuration(access_token=os.getenv("LINE_CHANNEL_ACCESS_TOKEN"))
api_client = ApiClient(configuration)
line_bot_api = MessagingApi(api_client)
parser = WebhookParser(os.getenv("LINE_CHANNEL_SECRET"))

init_db()

handler_bp = create_handler(line_bot_api, parser)
app.register_blueprint(handler_bp)

scheduler = get_scheduler(line_bot_api)
scheduler.start()

if __name__ == "__main__":
    port = int(os.getenv("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
