import pytest
import os
import sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from ai.summarizer import summarize_article, answer_keyword_query

def test_summarize_article_returns_dict(mocker):
    """summarize_article 回傳 {title, summary} 字典"""
    mock_message = mocker.MagicMock()
    mock_message.content = [mocker.MagicMock(text="標題：詐騙新標題\n摘要：這是一個詐騙摘要。")]
    mock_client = mocker.MagicMock()
    mock_client.messages.create.return_value = mock_message
    mocker.patch("ai.summarizer.client", mock_client)
    result = summarize_article("詐騙標題", "詐騙內容詳情")
    assert isinstance(result, dict)
    assert result["title"] == "詐騙新標題"
    assert result["summary"] == "這是一個詐騙摘要。"

def test_summarize_article_returns_fallback_on_error(mocker):
    """API 失敗時 fallback 仍回傳含 title/summary 的字典"""
    mocker.patch("ai.summarizer.client.messages.create", side_effect=Exception("API error"))
    result = summarize_article("詐騙標題", "詐騙內容詳情很長" * 10)
    assert isinstance(result, dict)
    assert result["title"] == "詐騙標題"
    assert len(result["summary"]) > 0

def test_answer_keyword_query_with_results(mocker):
    mock_message = mocker.MagicMock()
    mock_message.content = [mocker.MagicMock(text="以下是相關詐騙案例...")]
    mock_client = mocker.MagicMock()
    mock_client.messages.create.return_value = mock_message
    mocker.patch("ai.summarizer.client", mock_client)
    articles = [{"title": "假投資詐騙", "summary": "騙取投資款", "url": "https://example.com/1"}]
    result = answer_keyword_query("投資", articles)
    assert isinstance(result, str)

def test_answer_keyword_query_no_results_uses_ai_knowledge(mocker):
    """資料庫無結果時，改用 AI 知識回答（不再回「找不到」）"""
    mock_message = mocker.MagicMock()
    mock_message.content = [mocker.MagicMock(text="這類詐騙的常見手法是...")]
    mock_client = mocker.MagicMock()
    mock_client.messages.create.return_value = mock_message
    mocker.patch("ai.summarizer.client", mock_client)
    result = answer_keyword_query("外星人", [])
    assert isinstance(result, str)
    assert len(result) > 0
