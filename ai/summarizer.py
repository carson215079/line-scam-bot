import os
from anthropic import Anthropic
from dotenv import load_dotenv

load_dotenv()

client = Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))
MODEL = "claude-haiku-4-5-20251001"

def summarize_article(title: str, content: str) -> str:
    try:
        message = client.messages.create(
            model=MODEL,
            max_tokens=300,
            messages=[{
                "role": "user",
                "content": f"請用繁體中文，以100字以內摘要以下詐騙新聞，重點說明詐騙手法與如何防範：\n\n標題：{title}\n內容：{content[:1000]}"
            }]
        )
        return message.content[0].text
    except Exception:
        return content[:150] + "..." if len(content) > 150 else content

def answer_keyword_query(keyword: str, articles: list) -> str:
    if not articles:
        return f"找不到與「{keyword}」相關的詐騙案例。\n\n如有疑問請撥打 165 反詐騙諮詢專線。"

    article_texts = "\n\n".join([
        f"【{a['title']}】\n{a['summary']}\n原文：{a['url']}"
        for a in articles
    ])

    try:
        message = client.messages.create(
            model=MODEL,
            max_tokens=500,
            messages=[{
                "role": "user",
                "content": f"用戶查詢關鍵字：「{keyword}」\n\n以下是相關詐騙案例，請用繁體中文整理成友善易懂的回覆，並提醒用戶防範：\n\n{article_texts}"
            }]
        )
        return message.content[0].text
    except Exception:
        return article_texts
