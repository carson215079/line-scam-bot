from abc import ABC, abstractmethod

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
