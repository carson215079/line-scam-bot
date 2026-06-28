from flask import Blueprint, request, abort
from linebot.v3.webhooks import MessageEvent, TextMessageContent, FollowEvent
from linebot.v3.messaging import TextMessage, ReplyMessageRequest
from db.database import save_user, search_articles, save_message, get_conversation_history
from ai.summarizer import answer_keyword_query

def build_messages(reply_text: str, articles: list) -> list:
    """
    將段落逐一分配到訊息一（≤300字），溢出段落 + 新聞連結放訊息二。
    永遠不在段落中間截斷。
    """
    paragraphs = [p.strip() for p in reply_text.strip().split("\n\n") if p.strip()]

    msg1_parts, overflow_parts = [], []
    char_count = 0
    for p in paragraphs:
        # +2 是補回 \n\n 的長度
        if char_count + len(p) + 2 <= 300:
            msg1_parts.append(p)
            char_count += len(p) + 2
        else:
            overflow_parts.append(p)

    messages = []
    if msg1_parts:
        messages.append("\n\n".join(msg1_parts))

    # 訊息二：溢出段落 + 新聞連結
    parts2 = list(overflow_parts)
    if articles:
        links = "\n".join([
            f"🔗 {a['title']}\n{a['url']}"
            for a in articles[:3]
        ])
        parts2.append(f"📰 相關新聞連結：\n{links}")

    if parts2:
        msg2 = "\n\n".join(parts2)
        if len(msg2) > 300:
            msg2 = msg2[:297] + "..."
        messages.append(msg2)

    return messages if messages else [reply_text.strip()]

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
