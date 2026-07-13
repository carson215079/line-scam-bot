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

def fetch_article_text(url: str, max_chars: int = 2000) -> str:
    """
    抓取文章頁面並萃取內文（供 AI 摘要用）。
    抓不到（防爬、逾時、仍是 Google News 轉址頁）就回傳空字串，由呼叫端 fallback 標題。
    """
    # Google News 頁面是 JS 動態載入，抓不到內文
    if "news.google.com" in url:
        return ""
    try:
        from bs4 import BeautifulSoup
        resp = requests.get(
            url, timeout=8,
            headers={"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"}
        )
        resp.raise_for_status()
        soup = BeautifulSoup(resp.text, "html.parser")
        for tag in soup(["script", "style", "nav", "header", "footer", "aside"]):
            tag.decompose()
        paragraphs = [p.get_text(strip=True) for p in soup.find_all("p")]
        text = "\n".join(p for p in paragraphs if len(p) > 20)
        return text[:max_chars]
    except Exception:
        return ""

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
