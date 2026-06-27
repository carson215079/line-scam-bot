import pytest
import os
import sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from db.database import init_db, save_article, search_articles, get_all_user_ids, save_user, get_latest_articles

TEST_DB = "data/test_scam_bot.db"

@pytest.fixture(autouse=True)
def setup_db(monkeypatch):
    monkeypatch.setenv("DB_PATH", TEST_DB)
    init_db()
    yield
    if os.path.exists(TEST_DB):
        os.remove(TEST_DB)

def test_save_article_returns_true_on_new():
    result = save_article("詐騙標題", "詐騙內容", "摘要", "https://example.com/1", "165", "2026-06-27")
    assert result is True

def test_save_article_returns_false_on_duplicate_url():
    save_article("詐騙標題", "詐騙內容", "摘要", "https://example.com/1", "165", "2026-06-27")
    result = save_article("另一標題", "另一內容", "摘要2", "https://example.com/1", "165", "2026-06-27")
    assert result is False

def test_search_articles_by_keyword():
    save_article("網路購物詐騙", "假冒賣家騙取金錢", "詐騙摘要", "https://example.com/2", "news", "2026-06-27")
    results = search_articles("購物")
    assert len(results) == 1
    assert results[0]["title"] == "網路購物詐騙"

def test_search_articles_returns_empty_when_no_match():
    results = search_articles("火星人")
    assert results == []

def test_save_and_get_user():
    save_user("U123456789")
    ids = get_all_user_ids()
    assert "U123456789" in ids

def test_get_latest_articles():
    save_article("文章1", "內容1", "摘要1", "https://example.com/3", "165", "2026-06-25")
    save_article("文章2", "內容2", "摘要2", "https://example.com/4", "165", "2026-06-26")
    save_article("文章3", "內容3", "摘要3", "https://example.com/5", "165", "2026-06-27")
    results = get_latest_articles(limit=2)
    assert len(results) == 2
