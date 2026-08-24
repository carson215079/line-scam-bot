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

ARTICLE_SYSTEM_PROMPT = """你是新聞整理助理，專門整理詐騙防範相關資訊。
請根據指示精簡回覆，不要加入多餘內容。"""

# 圖片分析用：親切但不強制固定格式（格式由 user 訊息指定，避免與 SYSTEM_PROMPT 衝突）
IMAGE_SYSTEM_PROMPT = """你是「防詐小幫手」，一個親切、專業的詐騙防範助理。
請用繁體中文、依照使用者指定的格式回覆，語氣溫暖像朋友提醒。"""

def summarize_article(title: str, content: str) -> dict:
    """
    用 AI 生成標題與摘要，回傳 {"title": ..., "summary": ...}。
    標題：20 字以內，清楚易懂。
    摘要：80 字以內，不限形式（詐騙案例、宣導活動皆可）。
    """
    try:
        message = client.messages.create(
            model=MODEL,
            max_tokens=200,
            system=ARTICLE_SYSTEM_PROMPT,
            messages=[{
                "role": "user",
                "content": (
                    f"請根據以下新聞整理出標題與摘要：\n\n"
                    f"原標題：{title}\n內容：{content[:1000]}\n\n"
                    "回覆格式（只輸出這兩行，不要其他文字）：\n"
                    "標題：（20字以內，清楚易懂）\n"
                    "摘要：（80字以內，說明文章重點，不限詐騙手法，宣導類也可摘要宣導內容）"
                )
            }]
        )
        text = message.content[0].text.strip()
        ai_title, ai_summary = title, ""
        for line in text.split("\n"):
            if line.startswith("標題："):
                ai_title = line.replace("標題：", "").strip() or title
            elif line.startswith("摘要："):
                ai_summary = line.replace("摘要：", "").strip()
        return {"title": ai_title, "summary": ai_summary or text}
    except Exception:
        return {"title": title, "summary": content[:150] + "..." if len(content) > 150 else content}

def extract_scam_keyword(text: str) -> str:
    """從整句話萃取適合搜尋的詐騙關鍵詞（例：「請問什麼是投資詐騙」→「投資詐騙」）"""
    try:
        message = client.messages.create(
            model=MODEL,
            max_tokens=30,
            system="你是關鍵字萃取工具。從用戶的句子中萃取最核心的詐騙類型關鍵詞（2-6 個字），只輸出關鍵詞本身，不要標點、不要說明。",
            messages=[{"role": "user", "content": text}]
        )
        keyword = message.content[0].text.strip()
        # 防止 AI 回覆過長或空白
        if keyword and len(keyword) <= 10:
            return keyword
        return ""
    except Exception:
        return ""

def analyze_image_for_scam(image_b64: str, media_type: str = "image/jpeg") -> tuple:
    """分析圖片是否涉及詐騙，回傳 (分析文字, 搜尋關鍵字)"""
    try:
        message = client.messages.create(
            model=MODEL,
            max_tokens=500,
            system=IMAGE_SYSTEM_PROMPT,
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
