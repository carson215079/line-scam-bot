import pytest
import os
import sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from db.database import (
    init_db, save_article, search_articles, get_all_user_ids,
    save_user, get_latest_articles, _get_conn
)

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

def test_get_latest_articles():
    save_article("文章1PYTEST", "內容1", "摘要1", TEST_URL_PREFIX + "3", "165", "2026-06-25")
    save_article("文章2PYTEST", "內容2", "摘要2", TEST_URL_PREFIX + "4", "165", "2026-06-26")
    results = get_latest_articles(limit=2)
    assert len(results) == 2
