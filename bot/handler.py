import base64
from flask import Blueprint, request, abort
from linebot.v3.webhooks import (
    MessageEvent, TextMessageContent, ImageMessageContent,
    FollowEvent, GroupSource
)
from linebot.v3.messaging import TextMessage, ReplyMessageRequest, MessagingApiBlob
from db.database import save_user, search_articles, save_message, get_conversation_history
from ai.summarizer import answer_keyword_query, analyze_image_for_scam

def is_bot_mentioned(message) -> bool:
    """
    檢查訊息是否有 @TAG 到機器人。
    優先用 is_self=True；若 SDK 未回傳 is_self（None），
    只要有任何 mentionee 且訊息含 @ 就視為觸發。
    """
    mention = getattr(message, "mention", None)
    if not mention:
        return False
    mentionees = getattr(mention, "mentionees", None) or []
    if not mentionees:
        return False
    for m in mentionees:
        is_self = getattr(m, "is_self", None)
        if is_self is True:
            return True
        if is_self is None and "@" in getattr(message, "text", ""):
            return True
    return False

def strip_mentions(message) -> str:
    """移除訊息中所有 @mention 後回傳純文字"""
    text = message.text
    mentionees = []
    mention = getattr(message, "mention", None)
    if mention:
        mentionees = getattr(mention, "mentionees", None) or []
    for m in sorted(mentionees, key=lambda x: x.index, reverse=True):
        text = text[:m.index] + text[m.index + m.length:]
    return text.strip()

def distribute_paragraphs(paragraphs: list, max_chars: int = 300, max_buckets: int = 2) -> list:
    """將段落依序填入每個 bucket（≤max_chars），回傳最多 max_buckets 個字串"""
    buckets = []
    current_parts = []
    current_len = 0

    for p in paragraphs:
        if len(buckets) >= max_buckets - 1 and current_parts:
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

def create_handler(line_bot_api, parser, api_client):
    blob_api = MessagingApiBlob(api_client)
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
                is_group = isinstance(event.source, GroupSource)
                user_id = event.source.user_id
                save_user(user_id)

                # 群組模式：只有 @TAG 才回應
                if is_group:
                    if not is_bot_mentioned(event.message):
                        continue
                    user_message = strip_mentions(event.message)
                    if not user_message:
                        continue
                else:
                    user_message = event.message.text.strip()

                history = get_conversation_history(user_id, limit=6)
                articles = search_articles(user_message)
                reply_text = answer_keyword_query(user_message, articles, history=history)

                save_message(user_id, "user", user_message)
                save_message(user_id, "assistant", reply_text)

                messages = build_messages(reply_text, articles, keyword=user_message)
                line_bot_api.reply_message(ReplyMessageRequest(
                    reply_token=event.reply_token,
                    messages=[TextMessage(text=m) for m in messages]
                ))

            elif isinstance(event, MessageEvent) and isinstance(event.message, ImageMessageContent):
                # 群組圖片不處理（無法 @TAG 圖片）
                if isinstance(event.source, GroupSource):
                    continue

                user_id = event.source.user_id
                save_user(user_id)

                try:
                    content = blob_api.get_message_content(event.message.id)
                    image_b64 = base64.standard_b64encode(content).decode("utf-8")
                    analysis, keyword = analyze_image_for_scam(image_b64)
                except Exception:
                    analysis = "抱歉，圖片讀取失敗，請重新傳送或改用文字描述。"
                    keyword = "詐騙"

                articles = search_articles(keyword)

                save_message(user_id, "user", "[圖片]")
                save_message(user_id, "assistant", analysis)

                messages = build_messages(analysis, articles, keyword=keyword)
                line_bot_api.reply_message(ReplyMessageRequest(
                    reply_token=event.reply_token,
                    messages=[TextMessage(text=m) for m in messages]
                ))

        return "OK"

    return bp
