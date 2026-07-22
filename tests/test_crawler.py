import pytest
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from crawler.base import BaseCrawler, RssKeywordCrawler, run_all_crawlers, is_scam_article

@pytest.mark.parametrize("title", [
    "新北人事處遭LINE帳號盜用 詐騙親友借錢",
    "假檢警詐騙老婦 車手落網",
    "解除分期付款詐騙 民眾遭騙60萬",
    "投資詐騙損失184萬 25人被害",
])
def test_is_scam_article_keeps_real_scam(title):
    assert is_scam_article(title) is True

@pytest.mark.parametrize("title", [
    # 回歸測試：防詐宣導類新聞曾被排除詞「貪瀆」誤殺，且漏收「防詐」一詞
    "屏東縣警局長率隊啟動反詐宣導防詐反貪瀆",
    "台灣導入GSMA國際標準 電信偵測預防詐騙",
    "嘉義縣警察局長宣導防詐 提醒民眾勿上當",
    "台灣旅遊被騙900萬 專家警示免費最貴",
])
def test_is_scam_article_keeps_prevention_news(title):
    """防詐宣導、民眾受騙類新聞須保留，不得被排除詞誤殺"""
    assert is_scam_article(title) is True

@pytest.mark.parametrize("title", [
    # 貪瀆虛報類：非民眾受害的詐騙
    "台中議員涉詐領助理費 移送法辦",
    "診所詐領健保費 遭判刑",
    # 完全無關（曾因 description 圖檔名含 165 而誤收）
    "台軍工廠RDX火藥無法國內自製 兵工署負責生產",
    "通緝犯拒捕撞警 強制猥褻遭起訴",
])
def test_is_scam_article_excludes_non_scam(title):
    assert is_scam_article(title) is False

def test_filter_ignores_description_to_avoid_false_positive(mocker):
    """description 內的圖片網址（如 c8838165.jpg 含 165）不得造成誤收"""
    rss = """<?xml version="1.0" encoding="UTF-8"?>
    <rss version="2.0"><channel><item>
      <title>RDX火藥無法國內自製</title>
      <link>https://www.ettoday.net/news/1.htm</link>
      <description>&lt;img src="https://cdn2.ettoday.net/images/8838/c8838165.jpg" /&gt;軍工新聞</description>
    </item></channel></rss>"""
    mock_response = mocker.MagicMock()
    mock_response.content = rss.encode("utf-8")
    mocker.patch("requests.get", return_value=mock_response)
    results = RssKeywordCrawler("測試", "http://example.com/rss").fetch()
    assert results == []

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
