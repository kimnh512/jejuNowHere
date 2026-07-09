"""자외선지수 수집기 — 기상청 생활기상지수 조회서비스 (V5 대응).

발표: 일 2회 (06, 18시) -> cron은 06:40, 18:40 실행.

응답 형식이 버전마다 달라 둘 다 지원한다:
  * V3~V5: h0, h3, h6 ... h75 (발표시각 기준 +N시간의 3시간 단위 지수)
           -> 날짜별 '최대값'으로 집계해 저장 (야외활동 추천엔 일 최대가 기준)
  * V2:    today / tomorrow / dayaftertomorrow / twodaysaftertomorrow (일 단위)
"""
import re
from datetime import datetime, timedelta

import config
import db
from collectors.common import fetch_items, num

SQL = """
INSERT INTO uv_index (area_no, fcst_date, uv_value, base_at)
VALUES (%s, %s, %s, %s)
ON CONFLICT (area_no, fcst_date)
DO UPDATE SET uv_value = EXCLUDED.uv_value, base_at = EXCLUDED.base_at
"""

HOUR_KEY = re.compile(r"^h(\d{1,2})$")

# V2 형식: 응답 필드명 -> 발표일 기준 +N일
DAY_FIELDS = {
    "today": 0,
    "tomorrow": 1,
    "dayaftertomorrow": 2,
    "twodaysaftertomorrow": 3,
}


def latest_base(now: datetime | None = None) -> datetime:
    now = now or datetime.now()
    if now.hour >= 18:
        return now.replace(hour=18, minute=0, second=0, microsecond=0)
    if now.hour >= 6:
        return now.replace(hour=6, minute=0, second=0, microsecond=0)
    return (now - timedelta(days=1)).replace(hour=18, minute=0, second=0, microsecond=0)


def parse_item(item: dict, base_at: datetime) -> dict:
    """응답 1건 -> {날짜: 일 최대 지수}. hN(신형)과 일 단위(구형) 모두 지원."""
    daily: dict = {}

    for key, raw in item.items():
        m = HOUR_KEY.match(key)
        if not m:
            continue
        value = num(raw, int)
        if value is None:
            continue
        d = (base_at + timedelta(hours=int(m.group(1)))).date()
        daily[d] = max(daily.get(d, 0), value)

    if not daily:  # 구형(V2) 일 단위 형식
        for field, offset in DAY_FIELDS.items():
            value = num(item.get(field), int)
            if value is None:
                continue
            daily[(base_at + timedelta(days=offset)).date()] = value

    return daily


def collect() -> int:
    base_at = latest_base()
    rows = []
    for _city, area_no in config.AREA_NO.items():
        items = fetch_items(config.UV_URL, {
            "areaNo": area_no,
            "time": base_at.strftime("%Y%m%d%H"),
        })
        if not items:
            continue
        for fcst_date, value in parse_item(items[0], base_at).items():
            rows.append((area_no, fcst_date, value, base_at))
    return db.executemany(SQL, rows)