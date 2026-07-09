"""초단기예보(getUltraSrtFcst) 수집기 — 향후 6시간, 1시간 단위.

매시 30분 발표, 실시간 호출은 45분 이후 -> cron은 매시 50분 실행.
LGT(낙뢰)는 야외활동 안전 필터로 활용.
"""
from datetime import datetime, timedelta

import config
import db
from collectors.common import fetch_items, num, parse_precip, pivot

SQL = """
INSERT INTO ultra_forecast (
    region_id, fcst_at, base_at,
    t1h, rn1_text, rn1_mm, sky, reh, pty, pop, lgt, vec, wsd
) VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
ON CONFLICT (region_id, fcst_at) DO UPDATE SET
    base_at = EXCLUDED.base_at,
    t1h = EXCLUDED.t1h, rn1_text = EXCLUDED.rn1_text, rn1_mm = EXCLUDED.rn1_mm,
    sky = EXCLUDED.sky, reh = EXCLUDED.reh, pty = EXCLUDED.pty,
    pop = EXCLUDED.pop, lgt = EXCLUDED.lgt, vec = EXCLUDED.vec, wsd = EXCLUDED.wsd
"""


def latest_base(now: datetime | None = None) -> datetime:
    """매시 30분 발표, 45분 이후 호출 가능 -> 가장 최근 사용 가능한 HH30."""
    now = now or datetime.now()
    t = now - timedelta(minutes=45)
    return t.replace(minute=30, second=0, microsecond=0)


def collect() -> int:
    base_at = latest_base()
    total = 0
    for region in db.fetch_regions():
        items = fetch_items(config.ULTRA_URL, {
            "base_date": base_at.strftime("%Y%m%d"),
            "base_time": base_at.strftime("%H%M"),
            "nx": region["nx"],
            "ny": region["ny"],
        })
        rows = []
        for fcst_at, cats in pivot(items, "fcstDate", "fcstTime").items():
            rn1_text, rn1_mm = parse_precip(cats.get("RN1"))
            rows.append((
                region["region_id"], fcst_at, base_at,
                num(cats.get("T1H")), rn1_text, rn1_mm,
                num(cats.get("SKY"), int), num(cats.get("REH"), int),
                num(cats.get("PTY"), int), num(cats.get("POP"), int),
                num(cats.get("LGT")), num(cats.get("VEC"), int), num(cats.get("WSD")),
            ))
        total += db.executemany(SQL, rows)
    return total
