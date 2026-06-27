import requests
from bs4 import BeautifulSoup
from crawler.base import BaseCrawler

SEARCH_URLS = [
    "https://udn.com/search/result/2/%E8%A9%90%E9%A8%99",
    "https://www.ettoday.net/news/news-list.htm?ndayago=1&kind=%E8%A9%90%E9%A8%99",
]

class NewsCrawler(BaseCrawler):
    def fetch(self) -> list:
        articles = []
        for url in SEARCH_URLS:
            try:
                resp = requests.get(url, timeout=10, headers={"User-Agent": "Mozilla/5.0"})
                soup = BeautifulSoup(resp.text, "html.parser")
                for a in soup.select("h2 a, h3 a, .title a")[:3]:
                    title = a.get_text(strip=True)
                    href = a.get("href", "")
                    if not title or not href:
                        continue
                    article_url = href if href.startswith("http") else "https:" + href
                    articles.append({
                        "title": title,
                        "content": title,
                        "url": article_url,
                        "published_at": ""
                    })
            except Exception as e:
                print(f"[NewsCrawler] {url} 爬取失敗: {e}")
        return articles
