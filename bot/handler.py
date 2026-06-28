from flask import Blueprint, request, abort
from linebot.v3.webhooks import MessageEvent, TextMessageContent, FollowEvent
from linebot.v3.messaging import TextMessage, ReplyMessageRequest
from db.database import save_user, search_articles, save_message, get_conversation_history
from ai.summarizer import answer_keyword_query

def split_message(text: str, max_chars: int = 500, max_parts: int = 5) -> list:
    if len(text) <= max_chars:
        return [text]
    parts = []
    while text and len(parts) < max_parts:
        if len(text) <= max_chars:
            parts.append(text)
            break
        # 在 max_chars 內找最近的換行點切割
        cut = text.rfind("\n", 0, max_chars)
        if cut == -1:
            cut = max_chars
        parts.append(text[:cut].strip())
        text = text[cut:].strip()
    return parts

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

                # 超過 500 字自動拆成多則（Line 最多 5 則）
                messages = split_message(reply_text, max_chars=500, max_parts=5)
                line_bot_api.reply_message(ReplyMessageRequest(
                    reply_token=event.reply_token,
                    messages=[TextMessage(text=m) for m in messages]
                ))

        return "OK"

    return bp
