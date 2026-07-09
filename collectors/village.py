"""단기예보(getVilageFcst) 수집기 — 파고(WAV)·일 최저/최고 보조 소스.

발표: 일 8회 (02,05,08,11,14,17,20,23시), 제공은 +10분 -> cron은 +15분 실행.
서비스 방향 전환(실시간 중심)에 따라 **+6시간 이내 예보만 저장**한다.
연장기간 정성코드(*_code) 처리는 스키마 호환을 위해 유지.
"""
from datetime import datetime, timedelta

import config
import db
from collectors.common import fetch_items, num, parse_precip, pivot

BASE_HOURS = [2, 5, 8, 11, 14, 17, 20, 23]

SQL = """
INSERT INTO village_forecast (
    region_id, fcst_at, base_at, is_extended,
    tmp, tmn, tmx, sky, pty, pop,
    pcp_text, pcp_mm, pcp_code, sno_text, sno_cm, sno_code,
    reh, wsd, wsd_code, vec, wav
) VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
ON CONFLICT (region_id, fcst_at) DO UPDATE SET
    base_at = EXCLUDED.base_at, is_extended = EXCLUDED.is_extended,
    tmp = EXCLUDED.tmp,
    tmn = COALESCE(EXCLUDED.tmn, village_forecast.tmn),
    tmx = COALESCE(EXCLUDED.tmx, village_forecast.tmx),
    sky = EXCLUDED.sky, pty = EXCLUDED.pty, pop = EXCLUDED.pop,
    pcp_text = EXCLUDED.pcp_text, pcp_mm = EXCLUDED.pcp_mm, pcp_code = EXCLUDED.pcp_code,
    sno_text = EXCLUDED.sno_text, sno_cm = EXCLUDED.sno_cm, sno_code = EXCLUDED.sno_code,
    reh = EXCLUDED.reh, wsd = EXCLUDED.wsd, wsd_code = EXCLUDED.wsd_code,
    vec = EXCLUDED.vec, wav = EXCLUDED.wav
"""


def latest_base(now: datetime | None = None) -> datetime:
    """지금 시점에 제공 완료된 가장 최근 발표 일시."""
    now = now or datetime.now()
    t = now - timedelta(minutes=10)  # 제공 시각(발표 +10분) 기준
    for h in reversed(BASE_HOURS):
        if t.hour >= h:
            return t.replace(hour=h, minute=0, second=0, microsecond=0)
    prev = t - timedelta(days=1)
    return prev.replace(hour=23, minute=0, second=0, microsecond=0)


def is_extended(base_at: datetime, fcst_at: datetime) -> bool:
    """연장기간 여부: 02~14시 발표는 +3일(글피)부터, 17~23시 발표는 +4일(그글피)부터."""
    days = (fcst_at.date() - base_at.date()).days
    return days >= (3 if base_at.hour <= 14 else 4)


def build_row(region_id: int, fcst_at: datetime, base_at: datetime, cats: dict) -> tuple:
    ext = is_extended(base_at, fcst_at)

    if ext:  # 정성코드(1~3)
        pcp_text, pcp_mm, pcp_code = None, None, num(cats.get("PCP"), int)
        sno_text, sno_cm, sno_code = None, None, num(cats.get("SNO"), int)
        wsd, wsd_code = None, num(cats.get("WSD"), int)
    else:
        pcp_text, pcp_mm = parse_precip(cats.get("PCP"))
        sno_text, sno_cm = parse_precip(cats.get("SNO"))
        pcp_code = sno_code = None
        wsd, wsd_code = num(cats.get("WSD")), None

    return (
        region_id, fcst_at, base_at, ext,
        num(cats.get("TMP")), num(cats.get("TMN")), num(cats.get("TMX")),
        num(cats.get("SKY"), int), num(cats.get("PTY"), int), num(cats.get("POP"), int),
        pcp_text, pcp_mm, pcp_code, sno_text, sno_cm, sno_code,
        num(cats.get("REH"), int), wsd, wsd_code,
        num(cats.get("VEC"), int), num(cats.get("WAV")),
    )


def collect() -> int:
    base_at = latest_base()
    horizon = datetime.now() + timedelta(hours=config.FORECAST_HORIZON_HOURS)
    total = 0
    for region in db.fetch_regions():
        items = fetch_items(config.VILLAGE_URL, {
            "base_date": base_at.strftime("%Y%m%d"),
            "base_time": base_at.strftime("%H%M"),
            "nx": region["nx"],
            "ny": region["ny"],
        })
        rows = [
            build_row(region["region_id"], fcst_at, base_at, cats)
            for fcst_at, cats in pivot(items, "fcstDate", "fcstTime").items()
            if fcst_at <= horizon          # +6시간 이내만 저장
        ]
        total += db.executemany(SQL, rows)
    db.purge_future(config.FORECAST_HORIZON_HOURS)  # 기존 6h 초과분 정리
    return total
