# Taiwan Tender Dashboard

臺灣政府公開標案的低成本展示型 MVP。

## 目前功能

1. 標案類型篩選
   - 勞務案
   - 財物案
   - 工程案
2. 關鍵字搜尋
   - 例如「系統建置」
   - 例如「系統維護」
3. 日期規則
   - 不提供日期區間
   - 固定使用 `Asia/Taipei` 當日公告日期
   - GitHub Actions 每小時更新一次

> 政府採購正式分類通常使用「財物」，因此介面採用「財物案」，不是「財務案」。

## 資料來源

目前使用 OpenFun 標案 API：

```text
https://pcc-api.openfun.app/api/listbydate?date=YYYYMMDD
```

此 API 是第三方社群服務，資料源自政府電子採購網，不是政府官方 API。程式只在排程時按日期取得一次資料，再由本站本地 JSON 提供搜尋，不會讓每位訪客直接重複呼叫 API。

若 API 暫時失敗，GitHub Actions 會失敗並保留上一版 `docs/data/tenders.json`，避免把正常資料覆寫成空資料。

## 架構

- `crawler.py`：按臺北日期取得 OpenFun API 資料
- `app/openfun_source.py`：API 連線、重試、欄位正規化及類型判斷
- `data/tenders.db`：SQLite，執行後自動建立
- `export_json.py`：只匯出臺北時間當日公告
- `docs/`：不需要後端的搜尋與篩選頁面
- `.github/workflows/update-tenders.yml`：每小時自動更新

## 本機執行

```bash
python -m venv .venv
# Windows
.venv\Scripts\activate
# macOS/Linux
source .venv/bin/activate

pip install -r requirements.txt
python crawler.py
python export_json.py
python -m http.server 8000 --directory docs
```

開啟 `http://localhost:8000`。

## 指定日期測試

```bash
python crawler.py --date 2026-06-22
python export_json.py --date 2026-06-22
```

## 分類方式

API 若直接提供「勞務、財物、工程」字樣，程式會直接採用。若清單資料沒有正式分類欄位，則以標案名稱中的明確關鍵詞輔助分類，例如：

- 系統建置、系統維護、委外服務 → 勞務
- 設備採購、器材採購、硬體採購 → 財物
- 新建工程、修繕工程、改善工程 → 工程

未能可靠分類的公告不會被硬塞進錯誤類型。

## 診斷

每次 Actions 執行都會產生 `tender-fetch-diagnostics` artifact，包含 API 狀態、回傳筆數與分類成功筆數，保存 7 天。

## 免費資料庫選擇

- **SQLite（目前採用）**：完全免費、零設定，適合展示頁。
- **Supabase**：免費 PostgreSQL、管理介面與 REST API，適合日後加入收藏、會員與通知。
- **Neon**：免費 Serverless PostgreSQL，適合需要雲端 SQL 但不需要完整後台。
