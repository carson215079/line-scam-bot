import pytest
import os
import sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from ai.summarizer import summarize_article, answer_keyword_query

def test_summarize_article_returns_string(mocker):
    mock_message = mocker.MagicMock()
    mock_message.content = [mocker.MagicMock(text="這是一個詐騙摘要。")]
    mock_client = mocker.MagicMock()
    mock_client.messages.create.return_value = mock_message
    mocker.patch("ai.summarizer.client", mock_client)
    result = summarize_article("詐騙標題", "詐騙內容詳情")
    assert isinstance(result, str)
    assert len(result) > 0

def test_summarize_article_returns_fallback_on_error(mocker):
    mocker.patch("ai.summarizer.client.messages.create", side_effect=Exception("API error"))
    result = summarize_article("詐騙標題", "詐騙內容詳情很長" * 10)
    assert isinstance(result, str)
    assert len(result) > 0

def test_answer_keyword_query_with_results(mocker):
    mock_message = mocker.MagicMock()
    mock_message.content = [mocker.MagicMock(text="以下是相關詐騙案例...")]
    mock_client = mocker.MagicMock()
    mock_client.messages.create.return_value = mock_message
    mocker.patch("ai.summarizer.client", mock_client)
    articles = [{"title": "假投資詐騙", "summary": "騙取投資款", "url": "https://example.com/1"}]
    result = answer_keyword_query("投資", articles)
    assert isinstance(result, str)

def test_answer_keyword_query_no_results():
    result = answer_keyword_query("外星人", [])
    assert "找不到" in result
