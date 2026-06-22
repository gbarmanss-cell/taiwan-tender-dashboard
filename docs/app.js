const API_BASE = "https://pcc-api.openfun.app";
const VIEWER_BASE = "https://openfunltd.github.io/pcc-viewer";

const state = { items: [], searchDate: "", source: "" };

const keywordInput = document.querySelector("#q");
const typeSelect = document.querySelector("#type");
const searchButton = document.querySelector("#searchButton");
const retryButton = document.querySelector("#retryButton");
const list = document.querySelector("#list");
const count = document.querySelector("#count");
const updated = document.querySelector("#updated");
const dateLabel = document.querySelector("#dateLabel");
const statusTitle = document.querySelector("#statusTitle");
const statusMessage = document.querySelector("#statusMessage");
const sourceStatus = document.querySelector("#sourceStatus");

const safe = value => String(value ?? "").replace(
  /[&<>"']/g,
  character => ({"&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;","'":"&#039;"})[character],
);

function setStatus(kind, title, message, canRetry = false) {
  sourceStatus.dataset.kind = kind;
  statusTitle.textContent = title;
  statusMessage.textContent = message;
  retryButton.hidden = !canRetry;
}

function taipeiToday() {
  const parts = new Intl.DateTimeFormat("en-CA", {
    timeZone: "Asia/Taipei",
    year: "numeric",
    month: "2-digit",
    day: "2-digit",
  }).formatToParts(new Date());
  const values = Object.fromEntries(parts.map(part => [part.type, part.value]));
  return `${values.year}-${values.month}-${values.day}`;
}

function compactDate(isoDate) {
  return isoDate.replaceAll("-", "");
}

function collectText(value, output = []) {
  if (Array.isArray(value)) value.forEach(item => collectText(item, output));
  else if (value && typeof value === "object") Object.values(value).forEach(item => collectText(item, output));
  else if (value !== null && value !== undefined) output.push(String(value));
  return output;
}

function normalizeCategory(record) {
  const text = collectText(record).join(" ");
  const title = String(record?.brief?.title ?? record?.title ?? "");

  if (text.includes("勞務")) return "勞務";
  if (text.includes("財物") || text.includes("財務")) return "財物";
  if (text.includes("工程")) return "工程";

  const serviceTerms = ["系統建置","系統維護","維護服務","委託服務","委外服務","顧問服務","資訊服務","規劃設計","研究計畫","教育訓練"];
  const goodsTerms = ["設備採購","器材採購","物品採購","硬體採購","軟體採購","車輛採購","藥品採購","耗材採購","財物採購"];
  const worksTerms = ["新建工程","修繕工程","整建工程","改善工程","裝修工程","水電工程","道路工程","營繕工程","工程採購"];

  if (worksTerms.some(term => title.includes(term))) return "工程";
  if (serviceTerms.some(term => title.includes(term))) return "勞務";
  if (goodsTerms.some(term => title.includes(term))) return "財物";
  return "";
}

function normalizeRecord(record, noticeDate) {
  const brief = record?.brief ?? {};
  const unitId = String(record?.unit_id ?? "");
  const jobNumber = String(record?.job_number ?? "");
  return {
    title: String(brief.title ?? record?.title ?? "").trim(),
    agency: String(record?.unit_name ?? record?.agency ?? "").trim(),
    notice_date: noticeDate,
    category: normalizeCategory(record),
    announcement_type: String(brief.type ?? "").trim(),
    job_number: jobNumber,
    source_url: `${VIEWER_BASE}/tender.html?unit_id=${encodeURIComponent(unitId)}&job_number=${encodeURIComponent(jobNumber)}`,
  };
}

function render() {
  const keyword = keywordInput.value.trim().toLowerCase();
  const selectedType = typeSelect.value;
  const rows = state.items.filter(item => {
    const haystack = `${item.title} ${item.agency} ${item.category} ${item.announcement_type} ${item.job_number}`.toLowerCase();
    return (!keyword || haystack.includes(keyword)) && (!selectedType || item.category === selectedType);
  });

  count.textContent = `找到 ${rows.length} 筆`;
  dateLabel.textContent = state.searchDate ? `｜公告日期：${state.searchDate}` : "";

  if (!rows.length) {
    const details = [selectedType ? `${selectedType}案` : "全部類型", keyword ? `關鍵字「${keywordInput.value.trim()}」` : "未指定關鍵字"].join("、");
    list.innerHTML = `<div class="empty">今日沒有符合「${safe(details)}」的標案。</div>`;
    return;
  }

  list.innerHTML = rows.map(item => `
    <article class="card">
      <div class="type-badge">${safe(item.category ? `${item.category}案` : (item.announcement_type || "未分類"))}</div>
      <h2><a href="${safe(item.source_url)}" target="_blank" rel="noopener noreferrer">${safe(item.title)}</a></h2>
      <div class="meta"><span>${safe(item.agency || "未標示機關")}</span><span>公告：${safe(item.notice_date || "—")}</span><span>標案編號：${safe(item.job_number || "—")}</span></div>
    </article>`).join("");
}

function cacheKey(date) {
  return `taiwan-tender-dashboard:${date}`;
}

function saveCache(date, items) {
  try {
    localStorage.setItem(cacheKey(date), JSON.stringify({ savedAt: new Date().toISOString(), items }));
  } catch (error) {
    console.warn("Unable to save tender cache", error);
  }
}

function loadCache(date) {
  try {
    const raw = localStorage.getItem(cacheKey(date));
    return raw ? JSON.parse(raw) : null;
  } catch (error) {
    console.warn("Unable to read tender cache", error);
    return null;
  }
}

async function loadLocalFallback() {
  const response = await fetch("data/tenders.json", { cache: "no-store" });
  if (!response.ok) throw new Error(`local JSON HTTP ${response.status}`);
  const data = await response.json();
  state.items = (data.items ?? []).filter(item => item.title);
  state.searchDate = data.search_date ?? taipeiToday();
  state.source = "網站內建備援資料";
  updated.textContent = `資料來源：${state.source}`;
}

async function loadToday() {
  const today = taipeiToday();
  state.searchDate = today;
  count.textContent = "正在取得今日標案…";
  list.innerHTML = "";
  setStatus("loading", "正在取得今日標案…", "資料由瀏覽器直接向 OpenFun API 讀取。", false);

  try {
    const response = await fetch(`${API_BASE}/api/listbydate?date=${compactDate(today)}`, {
      method: "GET",
      mode: "cors",
      cache: "no-store",
      headers: { Accept: "application/json" },
    });
    if (!response.ok) throw new Error(`OpenFun API HTTP ${response.status}`);
    const payload = await response.json();
    if (!Array.isArray(payload.records)) throw new Error("OpenFun API 回傳格式不正確");

    state.items = payload.records
      .map(record => normalizeRecord(record, today))
      .filter(item => item.title);
    state.source = "OpenFun API 即時資料";
    saveCache(today, state.items);
    updated.textContent = `載入：${new Date().toLocaleString("zh-TW")}`;
    const classified = state.items.filter(item => item.category).length;
    setStatus("success", "今日資料已載入", `共取得 ${state.items.length} 筆公告，其中 ${classified} 筆可判定為勞務、財物或工程。`, false);
  } catch (error) {
    console.warn("OpenFun API failed", error);
    const cached = loadCache(today);
    if (cached?.items?.length) {
      state.items = cached.items;
      state.source = "瀏覽器快取";
      updated.textContent = `快取時間：${new Date(cached.savedAt).toLocaleString("zh-TW")}`;
      setStatus("warning", "即時資料暫時無法取得", `目前顯示今日已快取的 ${state.items.length} 筆資料。`, true);
    } else {
      try {
        await loadLocalFallback();
        setStatus("warning", "即時資料暫時無法取得", "目前顯示網站內建備援資料。", true);
      } catch (fallbackError) {
        count.textContent = "資料讀取失敗";
        list.innerHTML = `<div class="empty">目前無法取得今日標案。<br>${safe(error.message)}</div>`;
        updated.textContent = "";
        setStatus("error", "目前無法取得資料", "OpenFun API 可能拒絕此連線，請稍後再試。", true);
        return;
      }
    }
  }

  render();
}

function search() {
  render();
  keywordInput.focus();
}

searchButton.addEventListener("click", search);
retryButton.addEventListener("click", loadToday);
typeSelect.addEventListener("change", render);
keywordInput.addEventListener("keydown", event => { if (event.key === "Enter") search(); });

loadToday();
