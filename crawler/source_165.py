import requests
from bs4 import BeautifulSoup
from crawler.base import BaseCrawler

BASE_URL = "https://165.npa.gov.tw"
LIST_URL = f"{BASE_URL}/web/index-1.html"

class Crawler165(BaseCrawler):
    def fetch(self) -> list:
        try:
            resp = requests.get(LIST_URL, timeout=10, headers={"User-Agent": "Mozilla/5.0"})
            soup = BeautifulSoup(resp.text, "html.parser")
            articles = []
            for item in soup.select(".list-group-item a")[:5]:
                href = item.get("href", "")
                url = href if href.startswith("http") else BASE_URL + href
                title = item.get_text(strip=True)
                if not title:
                    continue
                try:
                    detail = requests.get(url, timeout=10, headers={"User-Agent": "Mozilla/5.0"})
                    detail_soup = BeautifulSoup(detail.text, "html.parser")
                    content = detail_soup.select_one(".article-content, .content, article p")
                    content_text = content.get_text(strip=True) if content else title
                except Exception:
                    content_text = title
                articles.append({
                    "title": title,
                    "content": content_text[:2000],
                    "url": url,
                    "published_at": ""
                })
            return articles
        except Exception as e:
            print(f"[Crawler165] 爬取失敗: {e}")
            return []
