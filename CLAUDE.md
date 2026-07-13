# CLAUDE.md — 專案規範範本
> 此檔案放在專案根目錄（任何專案皆可套用，例如 `你的專案/CLAUDE.md`），每次 Claude Code 在此專案啟動時自動載入。
> 建議進版控（git add + commit + push），讓團隊成員都套用同一套規範。
> 個人語氣/溝通偏好不在此檔，請見全域設定 `~/.claude/CLAUDE.md`。

---

## 本專案（防詐小幫手 LINE Bot）工作守則

**專案設計訴求：好維護、安全。所有決策以此為準。**

1. **進度紀錄**：每次完成一項工作（feat/fix），必須同步更新 `進度紀錄.md`
   —— 記錄做了什麼、為什麼、還剩什麼。開工前先讀此檔掌握現況。
2. **資安提醒**：施作任何功能前，主動評估並向用戶說明潛在資安風險
   （API 額度濫用、密鑰管理、注入攻擊、個資保留等），再開始動工。
3. **重要死線**：Render 免費 PostgreSQL 於 **2026-07-28 到期刪庫**，
   須在此之前完成 Supabase 遷移。

---

## 程式碼規範

**通用原則**
- 優先可讀性，其次效能（除非明確要求最佳化）
- 函式單一職責（SRP），避免魔法數字，錯誤處理明確不吞例外

**命名**
- 變數/函式 `camelCase`　類別/型別 `PascalCase`　常數 `UPPER_SNAKE_CASE`　檔案 `kebab-case`

**Commit 訊息（Conventional Commits）**
```
<type>(<scope>): <subject>
type: feat | fix | refactor | perf | test | docs | chore | ci
```

---

## 架構偏好

- **後端**：分層架構（Controller → Service → Repository），依賴注入
- **前端**：元件化，邏輯與 UI 分離（Custom Hooks / Container-Presenter）
- **API**：RESTful 為主，版本化 `/api/v1/`；GraphQL 視需求採用
- **資料庫**：Schema migration 版本控管，查詢避免 N+1
- **非同步**：明確處理 race condition 與 error boundary

---

## 測試策略

- 單元測試覆蓋核心業務邏輯；整合測試覆蓋 API 合約；E2E 僅覆蓋關鍵用戶路徑
- 測試命名：`should <expected behavior> when <condition>`

---

## 安全意識

- 輸入驗證在邊界層（controller/handler）執行
- 敏感資料不進 log、不寫死在程式碼
- 依賴套件定期審查（`npm audit` / `pip audit`）
- 查詢使用參數化，避免 injection

---

## 常用指令

> 以下為範例，請依實際專案的 package manager / 框架調整：
```bash
npm run dev / build / test / lint / typecheck
git log --oneline -10
git diff --staged
```

---

## Claude Code 使用習慣

- 修改前先讀懂上下文，不過度改動無關程式碼；修改建議附一行理由
- 不確定的需求，提問優先於猜測
- 大型重構拆成多個小 PR，每個 PR 有明確目的
- **寫完程式碼後先自行驗證語法與邏輯，確認無誤才交付**
- **不自動執行 `git commit`**：完成後提出符合 Conventional Commits 格式的建議訊息，待我確認後再 commit
  （若團隊要求「每次完成必須自動 commit」這種不可妥協的規則，建議用 git hook 或 CI 強制，而非僅寫在這份檔案中）

---
*最後更新：2026-06-29*
