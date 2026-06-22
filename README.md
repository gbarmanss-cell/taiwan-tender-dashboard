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
   - 每次更新覆寫 `docs/data/tenders.json`

> 政府採購正式分類通常使用「財物」，因此介面採用「財物案」，不是「財務案」。

## 架構

- `crawler.py`：尊重 robots.txt、限制頻率的公開頁面擷取器
- `data/tenders.db`：SQLite，執行後自動建立
- `export_json.py`：只匯出臺北時間當日公告
- `docs/`：不需要後端的搜尋與篩選頁面
- `.github/workflows/update-tenders.yml`：自動更新

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
python export_json.py --date 2026-06-22
```

## 重要限制

政府電子採購網可能使用動態表單、驗證碼或調整 HTML。本版本刻意不繞過任何限制：

- 先讀取 robots.txt
- 請求間隔至少 2 秒
- robots.txt 無法確認時預設停止
- 不處理登入、驗證碼或封鎖規避

若官方另有開放資料或 API，正式版應優先改接官方資料介面。

## 免費資料庫選擇

- **SQLite（目前採用）**：完全免費、零設定，適合展示頁。
- **Supabase**：免費 PostgreSQL、管理介面與 REST API，適合日後加入收藏、會員與通知。
- **Neon**：免費 Serverless PostgreSQL，適合需要雲端 SQL 但不需要完整後台。
