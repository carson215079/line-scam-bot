import os
from anthropic import Anthropic
from dotenv import load_dotenv

load_dotenv()

client = Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))
MODEL = "claude-haiku-4-5-20251001"

SYSTEM_PROMPT = """你是「防詐小幫手」，一個親切的詐騙防範助理。
回覆規則（必須嚴格遵守）：
- 使用繁體中文
- 語氣像朋友提醒，不要像公文
- 條列重點，每點一行，簡短有力
- 嚴格控制在 200 字以內，寧可少說也不超字
- 結尾一定要提醒撥打 165 專線
- 不需要附連結，系統會自動附上"""

def summarize_article(title: str, content: str) -> str:
    try:
        message = client.messages.create(
            model=MODEL,
            max_tokens=300,
            system=SYSTEM_PROMPT,
            messages=[{
                "role": "user",
                "content": f"請用 100 字以內摘要這則詐騙新聞，重點說明詐騙手法與防範方式：\n\n標題：{title}\n內容：{content[:1000]}"
            }]
        )
        return message.content[0].text
    except Exception:
        return content[:150] + "..." if len(content) > 150 else content

def answer_keyword_query(keyword: str, articles: list, history: list = None) -> str:
    messages = []

    # 加入對話歷史
    if history:
        messages.extend(history)

    if not articles:
        # 資料庫沒有時，讓 AI 用本身知識回答
        messages.append({
            "role": "user",
            "content": f"我想了解「{keyword}」相關的詐騙手法，請根據你的知識幫我說明這類詐騙的常見手法、受害情境與防範方式。"
        })
    else:
        article_texts = "\n\n".join([
            f"【{a['title']}】\n{a['summary']}"
            for a in articles
        ])
        messages.append({
            "role": "user",
            "content": f"我想查詢「{keyword}」相關詐騙資訊。以下是最新相關新聞摘要，請用條列式整理重點與防範方式，嚴格限制 200 字以內：\n\n{article_texts}"
        })

    try:
        message = client.messages.create(
            model=MODEL,
            max_tokens=500,
            system=SYSTEM_PROMPT,
            messages=messages
        )
        return message.content[0].text
    except Exception:
        if articles:
            return "\n\n".join([f"【{a['title']}】\n{a['summary']}\n🔗 {a['url']}" for a in articles])
        return f"抱歉，目前無法查詢「{keyword}」的相關資訊，請稍後再試，或直接撥打 165 反詐騙諮詢專線。"
