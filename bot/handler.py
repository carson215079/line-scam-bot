from flask import Blueprint, request, abort
from linebot.v3.webhooks import MessageEvent, TextMessageContent, FollowEvent
from linebot.v3.messaging import TextMessage, ReplyMessageRequest
from db.database import save_user, search_articles, save_message, get_conversation_history
from ai.summarizer import answer_keyword_query

def distribute_paragraphs(paragraphs: list, max_chars: int = 300, max_buckets: int = 2) -> list:
    """將段落依序填入每個 bucket（≤max_chars），回傳最多 max_buckets 個字串"""
    buckets = []
    current_parts = []
    current_len = 0

    for p in paragraphs:
        if len(buckets) >= max_buckets - 1 and current_parts:
            # 已達最後一個 bucket，剩下全塞進來
            current_parts.append(p)
        elif current_len + len(p) + 2 <= max_chars:
            current_parts.append(p)
            current_len += len(p) + 2
        else:
            if current_parts:
                buckets.append("\n\n".join(current_parts))
            current_parts = [p]
            current_len = len(p) + 2

    if current_parts:
        buckets.append("\n\n".join(current_parts))

    return buckets

def build_messages(reply_text: str, articles: list, keyword: str = "") -> list:
    """
    最多 3 則訊息：
    - 訊息一、二：AI 回覆段落（每則 ≤300字）
    - 訊息三：新聞連結（DB 有結果用真實連結；否則附 Google 新聞搜尋）
    """
    paragraphs = [p.strip() for p in reply_text.strip().split("\n\n") if p.strip()]
    ai_messages = distribute_paragraphs(paragraphs, max_chars=300, max_buckets=2)
    messages = list(ai_messages)

    # 建立連結訊息
    if articles:
        links = "\n\n".join([
            f"🔗 {a['title']}\n{a['url']}"
            for a in articles[:3]
        ])
        link_msg = f"📰 相關新聞連結：\n\n{links}"
    else:
        import urllib.parse
        query = urllib.parse.quote(keyword or "詐騙")
        search_url = f"https://news.google.com/search?q={query}&hl=zh-TW&gl=TW&ceid=TW:zh-Hant"
        link_msg = f"📰 目前資料庫尚無相關新聞，可至 Google 新聞搜尋最新資訊：\n\n{search_url}"

    if len(link_msg) > 300:
        link_msg = link_msg[:297] + "..."
    messages.append(link_msg)

    return messages

def create_handler(line_bot_api, parser):
    bp = Blueprint("handler", __name__)

    @bp.route("/callback", methods=["POST"])
    def callback():
        signature = request.headers.get("X-Line-Signature", "")
        body = request.get_data(as_text=True)
        try:
            events = parser.parse(body, signature)
        except Exception:
            abort(400)

        for event in events:
            if isinstance(event, FollowEvent):
                save_user(event.source.user_id)

            elif isinstance(event, MessageEvent) and isinstance(event.message, TextMessageContent):
                user_id = event.source.user_id
                user_message = event.message.text.strip()

                save_user(user_id)

                # 取得對話歷史
                history = get_conversation_history(user_id, limit=6)

                # 搜尋資料庫
                articles = search_articles(user_message)

                # 產生 AI 回覆
                reply_text = answer_keyword_query(user_message, articles, history=history)

                # 儲存這輪對話
                save_message(user_id, "user", user_message)
                save_message(user_id, "assistant", reply_text)

                # 最多 3 則：AI 回覆（最多 2 則）+ 新聞連結（第 3 則）
                messages = build_messages(reply_text, articles, keyword=user_message)
                line_bot_api.reply_message(ReplyMessageRequest(
                    reply_token=event.reply_token,
                    messages=[TextMessage(text=m) for m in messages]
                ))

        return "OK"

    return bp
