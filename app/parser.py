from __future__ import annotations

import hashlib
import re
from datetime import datetime, timezone
from urllib.parse import urljoin

from bs4 import BeautifulSoup
from dateutil import parser as date_parser

DATE_RE = re.compile(r"(\d{2,4})[./-](\d{1,2})[./-](\d{1,2})")
MONEY_RE = re.compile(r"(?:預算金額|採購金額|金額)\s*[:：]?\s*(?:新臺幣)?\s*([\d,]+)")


def clean(text: str | None) -> str:
    return re.sub(r"\s+", " ", text or "").strip()


def normalize_date(value: str | None) -> str | None:
    text = clean(value)
    if not text:
        return None
    match = DATE_RE.search(text)
    if match:
        year, month, day = map(int, match.groups())
        if year < 1911:
            year += 1911
        try:
            return datetime(year, month, day).date().isoformat()
        except ValueError:
            return None
    try:
        return date_parser.parse(text, fuzzy=True).date().isoformat()
    except (ValueError, OverflowError):
        return None


def parse_budget(text: str | None) -> int | None:
    match = MONEY_RE.search(clean(text))
    return int(match.group(1).replace(",", "")) if match else None


def normalize_category(value: str | None, block_text: str = "") -> str:
    text = f"{clean(value)} {clean(block_text)}"
    if "勞務" in text:
        return "勞務"
    if "財物" in text or "財務" in text:
        return "財物"
    if "工程" in text:
        return "工程"
    return ""


def make_key(url: str, title: str, agency: str) -> str:
    raw = f"{url}|{title}|{agency}".encode("utf-8")
    return hashlib.sha256(raw).hexdigest()[:24]


def _find_value(container, labels: tuple[str, ...]) -> str | None:
    text = clean(container.get_text(" ", strip=True))
    for label in labels:
        pattern = re.compile(rf"{re.escape(label)}\s*[:：]?\s*(.+?)(?=\s+\S{{2,12}}\s*[:：]|$)")
        match = pattern.search(text)
        if match:
            return clean(match.group(1))
    return None


def parse_search_results(html: str, base_url: str) -> list[dict]:
    soup = BeautifulSoup(html, "html.parser")
    results: list[dict] = []
    seen: set[str] = set()

    candidates = soup.select(
        "a[href*='tender'], a[href*='Tender'], "
        "a[href*='prkms'], table a[href], .card a[href], .list-group a[href]"
    )
    fetched_at = datetime.now(timezone.utc).isoformat(timespec="seconds")

    for link in candidates:
        title = clean(link.get_text(" ", strip=True))
        if len(title) < 4:
            continue

        href = clean(link.get("href"))
        if not href or href.startswith(("javascript:", "#", "mailto:")):
            continue

        container = link.find_parent(["tr", "li", "article", "section", "div"]) or link.parent
        block_text = clean(container.get_text(" ", strip=True))
        if not any(word in (title + " " + block_text) for word in ("標案", "採購", "招標", "公告", "工程", "勞務", "財物")):
            continue

        url = urljoin(base_url, href)
        agency = _find_value(container, ("機關名稱", "招標機關", "採購機關", "機關")) or ""
        notice_date = normalize_date(_find_value(container, ("公告日期", "刊登日期", "公告日")))
        deadline = normalize_date(_find_value(container, ("截止投標", "截止日期", "投標截止")))
        raw_category = _find_value(container, ("採購類別", "標的分類", "類別")) or ""
        category = normalize_category(raw_category, block_text)
        budget = parse_budget(block_text)

        key = make_key(url, title, agency)
        if key in seen:
            continue
        seen.add(key)

        results.append({
            "source_key": key,
            "title": title,
            "agency": agency,
            "notice_date": notice_date,
            "deadline": deadline,
            "budget": budget,
            "category": category,
            "source_url": url,
            "fetched_at": fetched_at,
        })

    return results
