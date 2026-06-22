# Taiwan Tender Dashboard

臺灣政府公開標案的簡易搜尋展示頁。

## 功能

- 標案類型：勞務案、財物案、工程案
- 關鍵字搜尋：例如「系統建置」、「系統維護」
- 日期固定為 `Asia/Taipei` 當日
- GitHub Pages 靜態展示，不需要後端資料庫

## 現行資料取得方式

瀏覽器直接呼叫 OpenFun API：

```text
https://pcc-api.openfun.app/api/listbydate?date=YYYYMMDD
```

這是第三方社群 API，不是政府官方 API。原始資料源自政府電子採購網。

GitHub Actions 雲端 IP 會被 Cloudflare 以 403 拒絕，因此不再由 Actions 抓資料。使用者開啟頁面時，由一般瀏覽器直接讀取 API，再在本機進行類型與關鍵字篩選。

## 失敗備援

- 成功取得資料後，會存入瀏覽器 `localStorage`
- 同一天再次開啟時，如果 API 暫時失敗，會顯示瀏覽器快取
- 若沒有快取，才使用 `docs/data/tenders.json` 備援
- 頁面提供「重新讀取」按鈕

## 分類方式

API 若直接帶有「勞務、財物、工程」字樣，優先採用；否則依標案名稱中的明確詞彙輔助分類：

- 系統建置、系統維護、委外服務 → 勞務
- 設備採購、器材採購、硬體採購 → 財物
- 新建工程、修繕工程、改善工程 → 工程

無法可靠分類的公告不會強行歸類。

## GitHub Actions

`.github/workflows/update-tenders.yml` 現在只做靜態檔案與 Python 語法檢查，不再連線 OpenFun API。

## 本機查看

```bash
python -m http.server 8000 --directory docs
```

開啟：

```text
http://localhost:8000
```

## GitHub Pages

Settings → Pages：

- Source：Deploy from a branch
- Branch：main
- Folder：/docs
