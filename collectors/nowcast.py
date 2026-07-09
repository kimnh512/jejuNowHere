"""초단기실황(getUltraSrtNcst) 수집기 — "지금" 날씨.

매시 정시 관측값이 +10분 후 제공 -> cron은 매시 15분 실행.
base_date/base_time이 곧 관측 시각이며, 응답 값 필드는 obsrValue.
"""
from datetime import datetime, timedelta

import config
import db
from collectors.common import fetch_items, num

SQL = """
INSERT INTO ultra_nowcast (region_id, observed_at, t1h, rn1_mm, reh, pty, vec, wsd)
VALUES (%s,%s,%s,%s,%s,%s,%s,%s)
ON CONFLICT (region_id, observed_at) DO UPDATE SET
    t1h = EXCLUDED.t1h, rn1_mm = EXCLUDED.rn1_mm, reh = EXCLUDED.reh,
    pty = EXCLUDED.pty, vec = EXCLUDED.vec, wsd = EXCLUDED.wsd
"""


def latest_base(now: datetime | None = None) -> datetime:
    now = now or datetime.now()
    t = now - timedelta(minutes=10)  # 매시각 10분 이후 호출 규칙
    return t.replace(minute=0, second=0, microsecond=0)


def collect() -> int:
    base_at = latest_base()
    rows = []
    for region in db.fetch_regions():
        items = fetch_items(config.NOWCAST_URL, {
            "base_date": base_at.strftime("%Y%m%d"),
            "base_time": base_at.strftime("%H%M"),
            "nx": region["nx"],
            "ny": region["ny"],
        })
        cats = {it["category"]: it.get("obsrValue") for it in items}
        if not cats:
            continue
        rows.append((
            region["region_id"], base_at,
            num(cats.get("T1H")), num(cats.get("RN1")),
            num(cats.get("REH"), int), num(cats.get("PTY"), int),
            num(cats.get("VEC"), int), num(cats.get("WSD")),
        ))
    return db.executemany(SQL, rows)
