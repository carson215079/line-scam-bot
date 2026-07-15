import re
import json
import requests
from abc import ABC, abstractmethod

UA_HEADERS = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"}

def resolve_url(url: str) -> str:
    """
    將 Google News RSS 連結解碼為真實新聞網址。
    Google 不使用 HTTP 轉址（回 200 的 JS 頁面），必須透過其內部
    batchexecute API 解碼。解碼失敗時保留原始 RSS 連結
    （瀏覽器開啟仍可 JS 跳轉，勿轉成 /articles/ 格式——該格式回 400）。
    """
    if "news.google.com" not in url:
        return url
    m = re.search(r"/articles/([^?/]+)", url)
    if not m:
        return url
    art_id = m.group(1)

    try:
        # 步驟 1：抓文章頁，取得解碼所需的簽章與時間戳
        page = requests.get(
            f"https://news.google.com/rss/articles/{art_id}?oc=5",
            headers=UA_HEADERS, timeout=15
        )
        sg = re.search(r'data-n-a-sg="([^"]+)"', page.text)
        ts = re.search(r'data-n-a-ts="([^"]+)"', page.text)
        if not (sg and ts):
            print(f"[resolve_url] 取不到簽章（HTTP {page.status_code}，頁面 {len(page.text)} 字），保留原連結")
            return url

        # 步驟 2：呼叫解碼 API 取得真實網址
        payload = (
            '["garturlreq",[["X","X",["X","X"],null,null,1,1,"TW:zh-Hant",'
            'null,1,null,null,null,null,null,0,1],"X","X",1,[1,1,1],1,1,null,0,0,null,0],'
            f'"{art_id}",{ts.group(1)},"{sg.group(1)}"]'
        )
        resp = requests.post(
            "https://news.google.com/_/DotsSplashUi/data/batchexecute",
            data={"f.req": json.dumps([[["Fbv4je", payload]]])},
            headers={**UA_HEADERS, "Content-Type": "application/x-www-form-urlencoded;charset=UTF-8"},
            timeout=15
        )
        # 回應中的引號是跳脫格式（\"garturlres\"），比對時不含引號
        m2 = re.search(r'garturlres.*?(https?://[^\\"]+)', resp.text)
        if m2:
            return m2.group(1)
        print(f"[resolve_url] 解碼 API 無有效回應（HTTP {resp.status_code}），保留原連結")
        return url
    except Exception as e:
        print(f"[resolve_url] 解碼例外：{type(e).__name__} {e}，保留原連結")
        return url

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
