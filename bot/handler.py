import base64
from flask import Blueprint, request, abort
from linebot.v3.webhooks import (
    MessageEvent, TextMessageContent, ImageMessageContent,
    FollowEvent, GroupSource
)
from linebot.v3.messaging import TextMessage, ReplyMessageRequest, PushMessageRequest, MessagingApiBlob
from db.database import save_user, search_articles, save_message, get_conversation_history, get_db_stats
from ai.summarizer import answer_keyword_query, analyze_image_for_scam, extract_scam_keyword

def is_bot_mentioned(message, bot_user_id: str = None) -> bool:
    """
    檢查訊息是否有 @TAG 到機器人。
    判斷順序：is_self=True → mentionee.user_id 比對 → fallback（無法判斷時放行）
    """
    mention = getattr(message, "mention", None)
    if not mention:
        return False
    mentionees = getattr(mention, "mentionees", None) or []
    for m in mentionees:
        if getattr(m, "is_self", None) is True:
            return True
        # 比對機器人自己的 user_id，避免 tag 別人也觸發
        m_user_id = getattr(m, "user_id", None)
        if bot_user_id and m_user_id == bot_user_id:
            return True
        # SDK 無法判斷（is_self=None 且拿不到比對資訊）時放行
        if getattr(m, "is_self", None) is None and not bot_user_id and not m_user_id:
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

    # 取得機器人自己的 user_id，供群組 @TAG 比對
    try:
        bot_user_id = line_bot_api.get_bot_info().user_id
    except Exception:
        bot_user_id = None

    def safe_reply(event, messages: list):
        """優先用 reply（免費）；reply token 逾時失效則改用 push 補送"""
        try:
            line_bot_api.reply_message(ReplyMessageRequest(
                reply_token=event.reply_token,
                messages=messages
            ))
        except Exception as e:
            print(f"[handler] reply 失敗，改用 push: {e}")
            target_id = (
                getattr(event.source, "group_id", None)
                or getattr(event.source, "user_id", None)
            )
            if target_id:
                line_bot_api.push_message(PushMessageRequest(
                    to=target_id,
                    messages=messages
                ))

    def handle_text(event):
        is_group = isinstance(event.source, GroupSource)
        # 群組中未加好友的成員 user_id 會是 None
        user_id = getattr(event.source, "user_id", None)
        if user_id:
            save_user(user_id)

        # 群組模式：只有 @TAG 才回應
        if is_group:
            if not is_bot_mentioned(event.message, bot_user_id):
                return
            user_message = strip_mentions(event.message)
            if not user_message:
                return
        else:
            user_message = event.message.text.strip()

        # 統計指令
        if user_message == "統計":
            stats = get_db_stats()
            reply_text = (
                f"📊 資料庫統計\n\n"
                f"📰 新聞文章：{stats['article_count']} 筆\n"
                f"👤 使用者：{stats['user_count']} 人\n"
                f"🕐 最新入庫：{stats['latest_crawl']}"
            )
            safe_reply(event, [TextMessage(text=reply_text)])
            return

        history = get_conversation_history(user_id, limit=6) if user_id else []

        # 先用原句搜尋；落空時讓 AI 萃取關鍵詞再搜一次
        # （例：「請問什麼是投資詐騙」→「投資詐騙」）
        search_keyword = user_message
        articles = search_articles(user_message)
        if not articles:
            extracted = extract_scam_keyword(user_message)
            if extracted and extracted != user_message:
                search_keyword = extracted
                articles = search_articles(extracted)

        reply_text = answer_keyword_query(user_message, articles, history=history)

        if user_id:
            save_message(user_id, "user", user_message)
            save_message(user_id, "assistant", reply_text)

        messages = build_messages(reply_text, articles, keyword=search_keyword)
        safe_reply(event, [TextMessage(text=m) for m in messages])

    def handle_image(event):
        # 群組圖片不處理，避免干擾群組聊天
        if isinstance(event.source, GroupSource):
            return

        user_id = getattr(event.source, "user_id", None)
        if user_id:
            save_user(user_id)

        try:
            content = blob_api.get_message_content(event.message.id)
            image_b64 = base64.standard_b64encode(content).decode("utf-8")
            analysis, keyword = analyze_image_for_scam(image_b64)
        except Exception:
            analysis = "抱歉，圖片讀取失敗，請重新傳送或改用文字描述。"
            keyword = "詐騙"

        articles = search_articles(keyword)

        if user_id:
            save_message(user_id, "user", "[圖片]")
            save_message(user_id, "assistant", analysis)

        messages = build_messages(analysis, articles, keyword=keyword)
        safe_reply(event, [TextMessage(text=m) for m in messages])

    @bp.route("/callback", methods=["POST"])
    def callback():
        signature = request.headers.get("X-Line-Signature", "")
        body = request.get_data(as_text=True)
        try:
            events = parser.parse(body, signature)
        except Exception:
            abort(400)

        for event in events:
            # 單一事件失敗不影響其他事件處理
            try:
                if isinstance(event, FollowEvent):
                    save_user(event.source.user_id)
                elif isinstance(event, MessageEvent) and isinstance(event.message, TextMessageContent):
                    handle_text(event)
                elif isinstance(event, MessageEvent) and isinstance(event.message, ImageMessageContent):
                    handle_image(event)
            except Exception as e:
                print(f"[handler] 處理事件失敗: {e}")

        return "OK"

    return bp
