from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import quote

import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

API_BASE = "https://pcc-api.openfun.app"
VIEWER_BASE = "https://openfunltd.github.io/pcc-viewer"


def _session(user_agent: str) -> requests.Session:
    retry = Retry(
        total=3,
        connect=3,
        read=3,
        backoff_factor=1.2,
        status_forcelist=(429, 500, 502, 503, 504),
        allowed_methods=frozenset({"GET"}),
    )
    session = requests.Session()
    session.mount("https://", HTTPAdapter(max_retries=retry))
    session.headers.update({
        "User-Agent": user_agent,
        "Accept": "application/json",
        "Accept-Language": "zh-TW,zh;q=0.9,en;q=0.6",
    })
    return session


def _text_values(value: object) -> list[str]:
    values: list[str] = []
    if isinstance(value, dict):
        for item in value.values():
            values.extend(_text_values(item))
    elif isinstance(value, list):
        for item in value:
            values.extend(_text_values(item))
    elif value is not None:
        values.append(str(value))
    return values


def normalize_category(record: dict) -> str:
    text = " ".join(_text_values(record))
    title = str((record.get("brief") or {}).get("title") or record.get("title") or "")

    if "勞務" in text:
        return "勞務"
    if "財物" in text or "財務" in text:
        return "財物"
    if "工程" in text:
        return "工程"

    service_terms = (
        "系統建置", "系統維護", "維護服務", "委託服務", "委外服務",
        "顧問服務", "資訊服務", "規劃設計", "研究計畫", "教育訓練",
    )
    goods_terms = (
        "設備採購", "器材採購", "物品採購", "硬體採購", "軟體採購",
        "車輛採購", "藥品採購", "耗材採購", "財物採購",
    )
    works_terms = (
        "新建工程", "修繕工程", "整建工程", "改善工程", "裝修工程",
        "水電工程", "道路工程", "營繕工程", "工程採購",
    )

    if any(term in title for term in works_terms):
        return "工程"
    if any(term in title for term in service_terms):
        return "勞務"
    if any(term in title for term in goods_terms):
        return "財物"
    return ""


def _source_key(unit_id: str, job_number: str, title: str) -> str:
    raw = f"{unit_id}|{job_number}|{title}".encode("utf-8")
    return hashlib.sha256(raw).hexdigest()[:24]


def normalize_record(record: dict, notice_date: str) -> dict:
    brief = record.get("brief") or {}
    title = str(brief.get("title") or record.get("title") or "").strip()
    agency = str(record.get("unit_name") or record.get("agency") or "").strip()
    unit_id = str(record.get("unit_id") or "").strip()
    job_number = str(record.get("job_number") or "").strip()
    category = normalize_category(record)

    source_url = (
        f"{VIEWER_BASE}/tender.html?unit_id={quote(unit_id)}"
        f"&job_number={quote(job_number)}"
    )

    return {
        "source_key": _source_key(unit_id, job_number, title),
        "title": title,
        "agency": agency,
        "notice_date": notice_date,
        "deadline": None,
        "budget": None,
        "category": category,
        "source_url": source_url,
        "fetched_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
    }


def fetch_by_date(
    yyyymmdd: str,
    user_agent: str,
    timeout: int = 35,
    diagnostics_dir: str | Path = "diagnostics",
) -> list[dict]:
    url = f"{API_BASE}/api/listbydate"
    directory = Path(diagnostics_dir)
    directory.mkdir(parents=True, exist_ok=True)

    session = _session(user_agent)
    response = session.get(url, params={"date": yyyymmdd}, timeout=timeout)
    response.raise_for_status()
    payload = response.json()

    records = payload.get("records")
    if not isinstance(records, list):
        raise RuntimeError("OpenFun API response does not contain a records list")

    notice_date = datetime.strptime(yyyymmdd, "%Y%m%d").date().isoformat()
    rows = [normalize_record(record, notice_date) for record in records if isinstance(record, dict)]
    rows = [row for row in rows if row["title"]]

    (directory / "openfun-response-meta.json").write_text(
        json.dumps({
            "request_url": response.url,
            "status_code": response.status_code,
            "content_type": response.headers.get("content-type"),
            "record_count": len(records),
            "normalized_count": len(rows),
            "classified_count": sum(1 for row in rows if row["category"]),
        }, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    return rows
