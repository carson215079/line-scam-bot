# 防詐小幫手 LINE Bot

一個結合 AI 與新聞爬蟲的 LINE 防詐騙機器人。每日自動抓取詐騙相關新聞、用 AI 整理重點推播給用戶，並支援關鍵字問答與圖片詐騙判斷。

---

## 功能特色

| 功能 | 說明 |
|---|---|
| 🔍 **關鍵字問答** | 傳入詐騙關鍵字，AI 從資料庫整理相關案例並提供防範建議 |
| 🖼️ **圖片判斷** | 傳送可疑截圖，Claude Vision 判斷是否為詐騙（限私訊） |
| 📰 **每日推播** | 每天早上 9:00 自動推播最新詐騙資訊給所有用戶 |
| 🕷️ **自動爬蟲** | 每 3 小時從 Google News 抓取最新詐騙新聞 |
| 🤖 **AI 摘要** | 自動為每篇新聞生成易懂的標題與摘要 |
| 💬 **多輪對話** | 儲存對話歷史，支援上下文延續 |
| 👥 **群組支援** | 加入群組後，@TAG 機器人即可查詢 |

---

## 技術棧

| 項目 | 技術 |
|---|---|
| 語言 | Python 3.14 |
| Web Framework | Flask |
| LINE SDK | line-bot-sdk v3 |
| AI 模型 | Claude Haiku (`claude-haiku-4-5-20251001`) |
| 資料庫 | PostgreSQL (psycopg3) |
| 排程 | APScheduler |
| 部署 | Render |
| 保活 | cron-job.org（每 10 分鐘 ping）|

---

## 專案結構

```
Linebot/
├── main.py                      # 入口，Flask app + 排程啟動
├── requirements.txt
├── .env                         # 環境變數（不進版控）
│
├── bot/
│   └── handler.py               # LINE Webhook 處理
│
├── ai/
│   └── summarizer.py            # AI 功能（摘要 / 問答 / 圖片分析）
│
├── db/
│   └── database.py              # 資料庫操作
│
├── crawler/
│   ├── base.py                  # 爬蟲基底 + resolve_url
│   ├── source_165.py            # Google News RSS（165 反詐騙）
│   └── source_news.py           # Google News RSS（詐騙台灣）
│
├── scheduler/
│   └── daily_job.py             # 定時爬蟲 + 每日推播
│
└── scripts/
    └── remigrate_articles.py    # 一次性舊資料更新腳本
```

---

## 資料庫 Tables

| Table | 說明 |
|---|---|
| `articles` | 爬蟲文章（標題、摘要、URL、來源）|
| `users` | LINE 用戶 ID |
| `conversations` | 對話歷史（支援多輪對話）|

---

## 核心流程

### 爬蟲（每 3 小時）
```
Google News RSS → 解析文章 → resolve_url 取得真實連結
→ AI 生成標題 + 摘要 → 存入 DB（URL 唯一，自動擋重複）
```

### 用戶傳文字
```
LINE Webhook → 搜尋 DB → AI 整理回覆
→ 最多 3 則訊息（AI 內容 + 新聞連結）
```

### 用戶傳圖片（私訊限定）
```
LINE Webhook → 下載圖片 → Claude Vision 分析
→ 判斷是否詐騙 + 萃取關鍵字 → 搜尋 DB → 回覆
```

### 每日推播（早上 9:00）
```
取最新 5 篇文章 → 廣播給所有用戶
格式：標題 + AI 摘要 + 原文連結
```

---

## 環境變數

於 Render Dashboard → Environment 設定：

```
LINE_CHANNEL_ACCESS_TOKEN    # LINE Messaging API Token
LINE_CHANNEL_SECRET          # LINE Channel Secret
ANTHROPIC_API_KEY            # Anthropic API Key
DATABASE_URL                 # PostgreSQL 連線字串
ADMIN_KEY                    # 管理端點的存取密碼
```

---

## 本機開發

```bash
# 安裝依賴
pip install -r requirements.txt

# 建立 .env 並填入環境變數（見上方）

# 啟動
python main.py
```

---

## 特殊指令

| 指令 | 說明 |
|---|---|
| `統計` | 查詢資料庫文章數、用戶數、最新入庫時間 |
| `GET /admin/remigrate?key=ADMIN_KEY` | 觸發舊資料重新整理（標題、摘要、URL）|

---

## 部署

專案透過 GitHub 連接 Render，`git push` 後 Render 自動重新部署。

```
本機修改 → git push → GitHub → Render 自動部署 → 上線
```
