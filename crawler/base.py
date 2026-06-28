import requests
from abc import ABC, abstractmethod

def resolve_url(url: str) -> str:
    """跟隨 Google News 轉址，取得真實文章 URL"""
    try:
        r = requests.get(
            url, allow_redirects=True, timeout=8,
            headers={"User-Agent": "Mozilla/5.0"}, stream=True
        )
        r.close()
        return r.url
    except Exception:
        return url

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
