import os
from anthropic import Anthropic
from dotenv import load_dotenv

load_dotenv()

client = Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))
MODEL = "claude-haiku-4-5-20251001"

SYSTEM_PROMPT = """你是「防詐小幫手」，一個親切的詐騙防範助理。

【回覆格式（必須照此結構）】
第一行：一句話說明這類詐騙是什麼

詐騙手法：
• 手法一（15字內）
• 手法二（15字內）

如何防範：
• 防範一（15字內）
• 防範二（15字內）

⚠️ 有疑問請撥 165 反詐騙專線

【規定】
- 嚴格照上面格式，不要改動結構
- 每個段落之間空一行
- 全文控制在 200 字以內
- 不需要附連結"""

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

def analyze_image_for_scam(image_b64: str, media_type: str = "image/jpeg") -> tuple:
    """分析圖片是否涉及詐騙，回傳 (分析文字, 搜尋關鍵字)"""
    try:
        message = client.messages.create(
            model=MODEL,
            max_tokens=500,
            system=SYSTEM_PROMPT,
            messages=[{
                "role": "user",
                "content": [
                    {
                        "type": "image",
                        "source": {
                            "type": "base64",
                            "media_type": media_type,
                            "data": image_b64,
                        },
                    },
                    {
                        "type": "text",
                        "text": (
                            "請分析這張圖片是否涉及詐騙，照以下格式回覆：\n\n"
                            "【判斷】是 / 否 / 無法判斷\n\n"
                            "【說明】詐騙手法與情境描述\n\n"
                            "【防範】具體防範建議\n\n"
                            "⚠️ 有疑問請撥 165 反詐騙專線\n\n"
                            "關鍵字：（填入最符合的詐騙類型，例如：投資詐騙、假交友、釣魚網站）"
                        )
                    }
                ]
            }]
        )
        text = message.content[0].text.strip()

        # 擷取關鍵字並從回覆中移除該行
        keyword = "詐騙"
        lines = text.split("\n")
        filtered = []
        for line in lines:
            if line.startswith("關鍵字："):
                keyword = line.replace("關鍵字：", "").strip() or "詐騙"
            else:
                filtered.append(line)
        text = "\n".join(filtered).strip()
        return text, keyword
    except Exception:
        return "抱歉，無法分析這張圖片，請改用文字描述您看到的內容。", "詐騙"

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
