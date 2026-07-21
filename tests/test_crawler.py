import pytest
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from crawler.base import BaseCrawler, RssKeywordCrawler, run_all_crawlers

RSS_SAMPLE = """<?xml version="1.0" encoding="UTF-8"?>
<rss version="2.0"><channel>
  <item>
    <title>假投資詐騙損失百萬</title>
    <link>https://www.cna.com.tw/news/asoc/1.aspx</link>
    <description>民眾遭假投資平台詐騙</description>
    <pubDate>Mon, 21 Jul 2026 08:00:00 +0800</pubDate>
  </item>
  <item>
    <title>颱風假明日停班停課</title>
    <link>https://www.cna.com.tw/news/asoc/2.aspx</link>
    <description>氣象署發布颱風警報</description>
    <pubDate>Mon, 21 Jul 2026 09:00:00 +0800</pubDate>
  </item>
</channel></rss>"""

def test_rss_crawler_returns_list(mocker):
    mock_response = mocker.MagicMock()
    mock_response.content = RSS_SAMPLE.encode("utf-8")
    mocker.patch("requests.get", return_value=mock_response)
    results = RssKeywordCrawler("測試", "http://example.com/rss").fetch()
    assert isinstance(results, list)

def test_rss_crawler_filters_by_scam_keyword(mocker):
    """只收含詐騙關鍵字的文章，過濾掉無關新聞"""
    mock_response = mocker.MagicMock()
    mock_response.content = RSS_SAMPLE.encode("utf-8")
    mocker.patch("requests.get", return_value=mock_response)
    results = RssKeywordCrawler("測試", "http://example.com/rss").fetch()
    assert len(results) == 1
    assert "詐騙" in results[0]["title"]
    assert results[0]["url"] == "https://www.cna.com.tw/news/asoc/1.aspx"

def test_rss_crawler_returns_empty_on_error(mocker):
    mocker.patch("requests.get", side_effect=Exception("Network error"))
    results = RssKeywordCrawler("測試", "http://example.com/rss").fetch()
    assert results == []

def test_run_all_crawlers_merges_results(mocker):
    mocker.patch(
        "crawler.base.RssKeywordCrawler.fetch",
        return_value=[{"title": "詐騙文章", "content": "內容", "url": "https://x/1", "source": "測試", "published_at": ""}]
    )
    results = run_all_crawlers()
    assert isinstance(results, list)
    assert len(results) >= 1
