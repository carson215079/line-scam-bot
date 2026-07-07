import requests
from abc import ABC, abstractmethod

def resolve_url(url: str) -> str:
    """
    嘗試跟隨轉址取得真實文章 URL。
    若 Google News 防爬導致失敗，至少把 RSS 格式轉成可開啟的網頁格式。
    """
    try:
        r = requests.get(
            url, allow_redirects=True, timeout=8,
            headers={"User-Agent": "Mozilla/5.0"}, stream=True
        )
        r.close()
        final = r.url
    except Exception:
        final = url

    # Google News RSS URL → 轉成可開啟的網頁版 URL
    if "news.google.com/rss/articles/" in final:
        final = final.replace("/rss/articles/", "/articles/").split("?")[0]

    return final

class BaseCrawler(ABC):
    @abstractmethod
    def fetch(self) -> list:
        pass

def run_all_crawlers() -> list:
    from crawler.source_165 import Crawler165
    from crawler.source_news import NewsCrawler

    results = []
    for crawler in [Crawler165(), NewsCrawler()]:
        try:
            results.extend(crawler.fetch())
        except Exception as e:
            print(f"[crawler] {crawler.__class__.__name__} 爬取失敗: {e}")
    return results
