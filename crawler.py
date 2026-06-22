from __future__ import annotations

import argparse
import os
import sys
import time
from pathlib import Path
from urllib import robotparser

import requests

from app.db import connect, upsert_tenders
from app.parser import parse_search_results

DEFAULT_URL = "https://web.pcc.gov.tw/prkms/tender/common/basic/indexTenderBasic"


def robots_allowed(url: str, user_agent: str, timeout: int) -> bool:
    from urllib.parse import urlsplit

    parts = urlsplit(url)
    robots_url = f"{parts.scheme}://{parts.netloc}/robots.txt"
    rp = robotparser.RobotFileParser()
    rp.set_url(robots_url)
    try:
        response = requests.get(robots_url, timeout=timeout, headers={"User-Agent": user_agent})
        if response.status_code == 404:
            return True
        response.raise_for_status()
        rp.parse(response.text.splitlines())
        return rp.can_fetch(user_agent, url)
    except requests.RequestException as exc:
        print(f"[warning] 無法確認 robots.txt：{exc}", file=sys.stderr)
        return False


def main() -> int:
    parser = argparse.ArgumentParser(description="擷取臺灣政府公開標案資料")
    parser.add_argument("--url", default=os.getenv("TENDER_SOURCE_URL", DEFAULT_URL))
    parser.add_argument("--db", default="data/tenders.db")
    parser.add_argument("--html-file", help="以本機 HTML 測試解析器，不連線")
    parser.add_argument("--force", action="store_true", help="robots.txt 無法確認時仍執行")
    parser.add_argument("--timeout", type=int, default=30)
    args = parser.parse_args()

    user_agent = os.getenv(
        "USER_AGENT",
        "TaiwanTenderDashboard/0.1 (public-data demo; contact: gbarmanss@gmail.com)",
    )
    delay = max(float(os.getenv("REQUEST_DELAY_SECONDS", "2")), 2.0)

    if args.html_file:
        html = Path(args.html_file).read_text(encoding="utf-8")
        base_url = args.url
    else:
        if not robots_allowed(args.url, user_agent, args.timeout) and not args.force:
            print("停止：robots.txt 不允許或無法確認。請優先改用官方開放資料或 API。", file=sys.stderr)
            return 2

        time.sleep(delay)
        response = requests.get(
            args.url,
            timeout=args.timeout,
            headers={
                "User-Agent": user_agent,
                "Accept-Language": "zh-TW,zh;q=0.9,en;q=0.6",
            },
        )
        response.raise_for_status()
        response.encoding = response.apparent_encoding or "utf-8"
        html = response.text
        base_url = response.url

    rows = parse_search_results(html, base_url)
    conn = connect(args.db)
    count = upsert_tenders(conn, rows)
    print(f"完成：解析 {len(rows)} 筆，寫入或更新 {count} 筆。")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
