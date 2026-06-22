from __future__ import annotations

import argparse
import os
import sys
from datetime import datetime
from zoneinfo import ZoneInfo

from app.db import connect, upsert_tenders
from app.openfun_source import fetch_by_date

TAIPEI = ZoneInfo("Asia/Taipei")


def main() -> int:
    parser = argparse.ArgumentParser(description="取得臺灣政府當日標案資料")
    parser.add_argument("--db", default="data/tenders.db")
    parser.add_argument("--date", help="指定日期 YYYY-MM-DD；省略時使用臺北時間今天")
    parser.add_argument("--timeout", type=int, default=35)
    parser.add_argument("--diagnostics-dir", default="diagnostics")
    args = parser.parse_args()

    target_date = args.date or datetime.now(TAIPEI).date().isoformat()
    yyyymmdd = target_date.replace("-", "")
    user_agent = os.getenv(
        "USER_AGENT",
        "TaiwanTenderDashboard/1.0 (+https://github.com/gbarmanss-cell/taiwan-tender-dashboard)",
    )

    try:
        rows = fetch_by_date(
            yyyymmdd=yyyymmdd,
            user_agent=user_agent,
            timeout=args.timeout,
            diagnostics_dir=args.diagnostics_dir,
        )
    except Exception as exc:
        print(f"OpenFun API 取得失敗：{type(exc).__name__}: {exc}", file=sys.stderr)
        return 3

    conn = connect(args.db)
    count = upsert_tenders(conn, rows)
    classified = sum(1 for row in rows if row["category"] in {"勞務", "財物", "工程"})
    print(f"完成：取得 {len(rows)} 筆，分類成功 {classified} 筆，寫入或更新 {count} 筆。")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
