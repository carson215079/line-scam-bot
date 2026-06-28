from flask import Blueprint, request, abort
from linebot.v3.webhooks import MessageEvent, TextMessageContent, FollowEvent
from linebot.v3.messaging import TextMessage, ReplyMessageRequest
from db.database import save_user, search_articles, save_message, get_conversation_history
from ai.summarizer import answer_keyword_query

def smart_truncate(text: str, max_chars: int) -> str:
    """在段落邊界截斷，避免截斷在句子中間"""
    if len(text) <= max_chars:
        return text
    # 優先在空行（段落）邊界截
    cut = text.rfind("\n\n", 0, max_chars)
    if cut == -1:
        # 退而求其次在換行截
        cut = text.rfind("\n", 0, max_chars)
    if cut == -1:
        # 最後才硬切
        cut = max_chars
    return text[:cut].strip()

def build_messages(reply_text: str, articles: list) -> list:
    """訊息一：AI 回覆（≤300字，按段落截斷）；訊息二：新聞連結"""
    msg1 = smart_truncate(reply_text.strip(), 300)
    result = [msg1]

    if articles:
        links = "\n".join([
            f"🔗 {a['title']}\n{a['url']}"
            for a in articles[:3]
        ])
        msg2 = f"📰 相關新聞連結：\n{links}"
        result.append(smart_truncate(msg2, 300))

    return result

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

                # 訊息一：AI 回覆（≤300字），訊息二：新聞連結
                messages = build_messages(reply_text, articles)
                line_bot_api.reply_message(ReplyMessageRequest(
                    reply_token=event.reply_token,
                    messages=[TextMessage(text=m) for m in messages]
                ))

        return "OK"

    return bp
