from __future__ import annotations

import argparse
import json
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

from app.db import connect

TAIPEI = ZoneInfo("Asia/Taipei")


def main() -> int:
    parser = argparse.ArgumentParser(description="匯出臺北時間當日最新政府標案資料")
    parser.add_argument("--db", default="data/tenders.db")
    parser.add_argument("--output", default="docs/data/tenders.json")
    parser.add_argument("--limit", type=int, default=1000)
    parser.add_argument("--date", help="指定公告日期 YYYY-MM-DD；省略時使用臺北時間今天")
    args = parser.parse_args()

    target_date = args.date or datetime.now(TAIPEI).date().isoformat()
    conn = connect(args.db)
    rows = conn.execute(
        """
        SELECT title, agency, notice_date, deadline, budget,
               category, source_url, fetched_at
        FROM tenders
        WHERE notice_date = ?
          AND category IN ('勞務', '財物', '工程')
        ORDER BY id DESC
        LIMIT ?
        """,
        (target_date, args.limit),
    ).fetchall()

    payload = {
        "search_date": target_date,
        "timezone": "Asia/Taipei",
        "generated_at": datetime.now(TAIPEI).isoformat(timespec="seconds"),
        "count": len(rows),
        "items": [dict(row) for row in rows],
    }

    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"已匯出 {target_date} 的 {len(rows)} 筆標案至 {output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
