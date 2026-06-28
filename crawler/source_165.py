import requests
import xml.etree.ElementTree as ET
from crawler.base import BaseCrawler

RSS_URL = "https://news.google.com/rss/search?q=165+%E5%8F%8D%E8%A9%90%E9%A8%99+%E8%AD%A6%E5%AF%9F&hl=zh-TW&gl=TW&ceid=TW:zh-Hant"

class Crawler165(BaseCrawler):
    def fetch(self) -> list:
        articles = []
        try:
            resp = requests.get(RSS_URL, timeout=10, headers={"User-Agent": "Mozilla/5.0"})
            resp.encoding = "utf-8"
            root = ET.fromstring(resp.content)
            for item in root.findall(".//item")[:10]:
                title = item.findtext("title", "").strip()
                url = item.findtext("link", "").strip()
                pub_date = item.findtext("pubDate", "").strip()
                if not title or not url:
                    continue
                articles.append({
                    "title": title,
                    "content": title,
                    "url": url,
                    "source": "165",
                    "published_at": pub_date
                })
        except Exception as e:
            print(f"[Crawler165] 爬取失敗: {e}")
        return articles
