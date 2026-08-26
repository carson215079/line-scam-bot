"""
GitHub Actions 獨立任務腳本。
不依賴 Flask / Render，直接連 Supabase + LINE API 執行排程任務。
用法：python scripts/run_tasks.py [crawl|broadcast|cleanup]
"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from dotenv import load_dotenv
load_dotenv()

from db.database import init_db
from scheduler.daily_job import run_crawl_job, run_broadcast_job, run_cleanup_job

def main():
    task = sys.argv[1] if len(sys.argv) > 1 else ""
    init_db()

    if task == "crawl":
        run_crawl_job()
    elif task == "broadcast":
        from linebot.v3.messaging import Configuration, ApiClient, MessagingApi
        config = Configuration(access_token=os.getenv("LINE_CHANNEL_ACCESS_TOKEN"))
        with ApiClient(config) as api_client:
            line_bot_api = MessagingApi(api_client)
            run_crawl_job()
            run_broadcast_job(line_bot_api)
    elif task == "cleanup":
        run_cleanup_job()
    else:
        print(f"Unknown task: {task}")
        print("Usage: python scripts/run_tasks.py [crawl|broadcast|cleanup]")
        sys.exit(1)

if __name__ == "__main__":
    main()
