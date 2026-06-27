import pytest
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

def test_search_and_reply_flow(mocker):
    # Patch at module level before importing
    mocker.patch("db.database.search_articles", return_value=[
        {"title": "假投資詐騙", "summary": "騙取投資款", "url": "https://example.com/1"}
    ])
    mock_answer = mocker.patch("ai.summarizer.answer_keyword_query", return_value="相關詐騙案例如下...")

    from db.database import search_articles
    from ai.summarizer import answer_keyword_query

    articles = search_articles("投資")
    reply = answer_keyword_query("投資", articles)

    assert reply == "相關詐騙案例如下..."
    mock_answer.assert_called_once_with("投資", articles)

def test_no_result_reply(mocker):
    # Patch at module level before importing
    mocker.patch("db.database.search_articles", return_value=[])
    mocker.patch("ai.summarizer.answer_keyword_query", return_value="找不到相關案例。")

    from db.database import search_articles
    from ai.summarizer import answer_keyword_query

    articles = search_articles("外星人")
    reply = answer_keyword_query("外星人", articles)
    assert "找不到" in reply
