import pytest
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from crawler.base import BaseCrawler
from crawler.source_165 import Crawler165
from crawler.source_news import NewsCrawler
from crawler.base import run_all_crawlers

def test_crawler165_fetch_returns_list(mocker):
    mock_response = mocker.MagicMock()
    mock_response.status_code = 200
    mock_response.text = """
    <html><body>
    <div class="list-group-item">
        <a href="/news/1">假投資詐騙案例</a>
        <p>民眾遭假投資平台詐騙損失百萬</p>
        <small>2026-06-27</small>
    </div>
    </body></html>
    """
    mocker.patch("requests.get", return_value=mock_response)
    crawler = Crawler165()
    results = crawler.fetch()
    assert isinstance(results, list)

def test_crawler165_fetch_returns_empty_on_error(mocker):
    mocker.patch("requests.get", side_effect=Exception("Network error"))
    crawler = Crawler165()
    results = crawler.fetch()
    assert results == []

def test_news_crawler_fetch_returns_list(mocker):
    mock_response = mocker.MagicMock()
    mock_response.status_code = 200
    mock_response.text = """
    <html><body>
    <div class="story-list__news">
        <h3><a href="https://udn.com/news/1">網路詐騙新手法</a></h3>
        <p>詐騙集團以假冒客服手法...</p>
        <time>2026-06-27</time>
    </div>
    </body></html>
    """
    mocker.patch("requests.get", return_value=mock_response)
    crawler = NewsCrawler()
    results = crawler.fetch()
    assert isinstance(results, list)

def test_run_all_crawlers_merges_results(mocker):
    mocker.patch("crawler.source_165.Crawler165.fetch", return_value=[
        {"title": "165文章", "content": "內容", "url": "https://165.npa.gov.tw/1", "published_at": "2026-06-27"}
    ])
    mocker.patch("crawler.source_news.NewsCrawler.fetch", return_value=[
        {"title": "新聞文章", "content": "新聞內容", "url": "https://udn.com/1", "published_at": "2026-06-27"}
    ])
    results = run_all_crawlers()
    assert len(results) == 2
