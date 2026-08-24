import requests
import xml.etree.ElementTree as ET
from abc import ABC, abstractmethod

UA_HEADERS = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"}

# 詐騙關鍵字（僅比對「標題」，且用完整詞彙）
# 註：不可使用「詐」「騙」單字或「165」裸數字——
#     「詐」會誤中「詐領」(貪瀆非詐騙)、「165」會誤中圖檔名如 c8838165.jpg
SCAM_KEYWORDS = [
    "詐騙", "詐欺", "詐團", "詐財", "詐轉", "反詐", "防詐", "車手",
    "假冒", "假客服", "假投資", "假交友", "假檢警", "假買家", "假賣家",
    "釣魚簡訊", "釣魚網站", "解除分期", "人頭帳戶", "盜刷", "165專線",
    "網購詐", "投資詐", "感情詐", "電信詐", "金融詐", "被騙", "遭騙", "騙走",
]

# 排除詞：公務虛報請領類（非民眾受害的詐騙）
# 注意：僅在標題「沒有」任何 SCAM_KEYWORDS 時才需要它們把關；
#      有強訊號（如「反詐」「防詐」）的宣導新聞不受此清單影響。
EXCLUDE_KEYWORDS = ["詐領", "助理費", "浮報", "溢領"]

def is_scam_article(title: str) -> bool:
    """
    判斷標題是否為民眾受害／防詐宣導的新聞。
    規則：有 SCAM_KEYWORDS 即收錄；沒有時，若含 EXCLUDE_KEYWORDS 也一律不收。
    （「詐領」等詞不在 SCAM_KEYWORDS 中，故貪瀆虛報案自然落選；
      排除清單僅作雙重保險，不會誤殺含「反詐/防詐」的宣導新聞。）
    """
    if any(k in title for k in SCAM_KEYWORDS):
        return True
    return False

# 台灣媒體 RSS 來源（提供真實文章網址，免解碼）
TAIWAN_FEEDS = [
    ("中央社", "https://feeds.feedburner.com/rsscna/social"),
    ("自由時報", "https://news.ltn.com.tw/rss/society.xml"),
    ("ETtoday", "https://feeds.feedburner.com/ettoday/news"),
]

def fetch_article_text(url: str, max_chars: int = 2000) -> str:
    """
    抓取文章頁面並萃取內文（供 AI 摘要用）。
    抓不到（防爬、逾時、非 HTML）就回傳空字串，由呼叫端 fallback 標題。
    """
    try:
        from bs4 import BeautifulSoup
        resp = requests.get(url, timeout=8, headers=UA_HEADERS, stream=True)
        resp.raise_for_status()
        # 只處理 HTML；非網頁內容（PDF、圖片等）直接放棄
        if "text/html" not in resp.headers.get("Content-Type", "text/html"):
            return ""
        # 最多讀 2 MB，防止惡意巨型回應吃光記憶體
        raw = b""
        for chunk in resp.iter_content(chunk_size=65536):
            raw += chunk
            if len(raw) > 2 * 1024 * 1024:
                break
        resp.close()
        html = raw.decode(resp.encoding or "utf-8", errors="ignore")
        soup = BeautifulSoup(html, "html.parser")
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

class RssKeywordCrawler(BaseCrawler):
    """通用 RSS 爬蟲：抓取媒體 RSS，僅收錄標題/摘要含詐騙關鍵字的文章。"""
    def __init__(self, name: str, feed_url: str):
        self.name = name
        self.feed_url = feed_url

    def fetch(self) -> list:
        articles = []
        try:
            resp = requests.get(self.feed_url, timeout=10, headers=UA_HEADERS)
            root = ET.fromstring(resp.content)
            for item in root.findall(".//item"):
                title = (item.findtext("title") or "").strip()
                url = (item.findtext("link") or "").strip()
                pub_date = (item.findtext("pubDate") or "").strip()
                if not title or not url:
                    continue
                # 僅比對標題：description 含 HTML 與圖片網址，會造成誤判
                if not is_scam_article(title):
                    continue
                articles.append({
                    "title": title,
                    "content": title,
                    "url": url,
                    "source": self.name,
                    "published_at": pub_date,
                })
        except Exception as e:
            print(f"[{self.name}] 爬取失敗: {e}")
        return articles

def run_all_crawlers() -> list:
    results = []
    for name, feed_url in TAIWAN_FEEDS:
        try:
            results.extend(RssKeywordCrawler(name, feed_url).fetch())
        except Exception as e:
            print(f"[crawler] {name} 爬取失敗: {e}")
    return results
