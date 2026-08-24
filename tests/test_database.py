import pytest
import os
import sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from db.database import (
    init_db, save_article, search_articles, get_all_user_ids,
    save_user, title_similarity, get_conversation_history, save_message, _get_conn
)

def test_title_similarity_same_event_high():
    """同一事件、用詞雷同的標題應高相似度"""
    s = title_similarity("台南地檢投資詐騙起訴保全", "台南地檢投資詐騙起訴保全首腦")
    assert s >= 0.45

def test_title_similarity_different_news_low():
    """不同案件的標題應低相似度，不會被誤判為重複"""
    s = title_similarity("假冒工程詐騙判刑", "70歲婦人網戀詐騙被騙")
    assert s < 0.45

# 測試資料一律使用此網址前綴，方便測試後清除，避免污染正式資料庫
TEST_URL_PREFIX = "https://pytest.example/"

@pytest.fixture(autouse=True)
def setup_db():
    init_db()
    yield
    # 清除本測試檔塞入的測試資料（只刪測試前綴，不動真實資料）
    with _get_conn() as conn:
        conn.execute("DELETE FROM articles WHERE url LIKE %s", (TEST_URL_PREFIX + "%",))
        conn.execute("DELETE FROM users WHERE line_user_id LIKE 'PYTEST_%'")
        conn.commit()

def test_save_article_returns_true_on_new():
    result = save_article("詐騙標題", "詐騙內容", "摘要", TEST_URL_PREFIX + "1", "165", "2026-06-27")
    assert result is True

def test_save_article_returns_false_on_duplicate_url():
    save_article("詐騙標題", "詐騙內容", "摘要", TEST_URL_PREFIX + "1", "165", "2026-06-27")
    result = save_article("另一標題", "另一內容", "摘要2", TEST_URL_PREFIX + "1", "165", "2026-06-27")
    assert result is False

def test_search_articles_by_keyword():
    save_article("網路購物詐騙PYTESTMARK", "假冒賣家騙取金錢", "詐騙摘要", TEST_URL_PREFIX + "2", "news", "2026-06-27")
    results = search_articles("購物詐騙PYTESTMARK")
    assert any(r["title"] == "網路購物詐騙PYTESTMARK" for r in results)

def test_search_articles_returns_empty_when_no_match():
    results = search_articles("完全不存在的關鍵字ZZZPYTEST")
    assert results == []

def test_save_and_get_user():
    save_user("PYTEST_U123456789")
    ids = get_all_user_ids()
    assert "PYTEST_U123456789" in ids

def test_conversation_history_starts_with_user():
    """對話歷史須以 user 開頭（去掉開頭多餘的 assistant），符合 Anthropic API 要求"""
    uid = "PYTEST_CONV_USER"
    # 故意先存一則 assistant（模擬孤兒訊息），再存正常一輪
    save_message(uid, "assistant", "孤兒訊息")
    save_message(uid, "user", "問題")
    save_message(uid, "assistant", "回答")
    hist = get_conversation_history(uid, limit=6)
    assert hist and hist[0]["role"] == "user"
    # 清理
    with _get_conn() as conn:
        conn.execute("DELETE FROM conversations WHERE line_user_id = %s", (uid,))
        conn.commit()
