from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path

from app.db import connect, upsert_tenders
from app.fetcher import acquire
from app.parser import parse_search_results

DEFAULT_URL = "https://web.pcc.gov.tw/prkms/tender/common/basic/indexTenderBasic"


def main() -> int:
    parser = argparse.ArgumentParser(description="擷取臺灣政府公開標案資料")
    parser.add_argument("--url", default=os.getenv("TENDER_SOURCE_URL", DEFAULT_URL))
    parser.add_argument("--fallback-url", action="append", default=[])
    parser.add_argument("--db", default="data/tenders.db")
    parser.add_argument("--html-file", help="以本機 HTML 測試解析器，不連線")
    parser.add_argument("--timeout", type=int, default=35)
    parser.add_argument("--diagnostics-dir", default="diagnostics")
    args = parser.parse_args()

    user_agent = os.getenv(
        "USER_AGENT",
        "TaiwanTenderDashboard/0.2 (+https://github.com/gbarmanss-cell/taiwan-tender-dashboard)",
    )
    delay = max(float(os.getenv("REQUEST_DELAY_SECONDS", "2")), 2.0)

    if args.html_file:
        html = Path(args.html_file).read_text(encoding="utf-8")
        base_url = args.url
    else:
        env_fallbacks = [
            value.strip()
            for value in os.getenv("TENDER_FALLBACK_URLS", "").split(",")
            if value.strip()
        ]
        urls = list(dict.fromkeys([args.url, *args.fallback_url, *env_fallbacks]))
        try:
            html, base_url = acquire(
                urls=urls,
                user_agent=user_agent,
                timeout=args.timeout,
                delay=delay,
                diagnostics_dir=args.diagnostics_dir,
            )
        except Exception as exc:
            print(f"停止：{exc}。請查看 diagnostics/diagnostics.json。", file=sys.stderr)
            return 3

    rows = parse_search_results(html, base_url)
    if not rows:
        print(
            "[warning] 已取得 HTML，但解析為 0 筆；可能是動態表單或網站版面已改版。",
            file=sys.stderr,
        )

    conn = connect(args.db)
    count = upsert_tenders(conn, rows)
    print(f"完成：解析 {len(rows)} 筆，寫入或更新 {count} 筆。")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
