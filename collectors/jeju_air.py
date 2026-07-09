"""제주보건환경연구원 대기환경(PM10/PM2.5) 수집기.

엔드포인트: https://air.jeju.go.kr/rest/JejuAirService/getJejuAirList/?date=YYYYMMDD
- 인증키 불필요, 당일 시간별 자료 전체를 반환 (측정소 12곳 × 시간).
- 응답 XML 구조: openapi > body > data > list
    SITE(측정소 코드), DT10(YYYYMMDDHH), PM10, PM25, O3, NO2, CO, SO2, *_CAI
- 미세먼지(PM10/PM2.5) 중심으로 저장. 매시 25분 수집 권장.
"""
import logging
import time
import xml.etree.ElementTree as ET
from datetime import datetime, timedelta

import requests

import config
import db
from collectors.common import num

logger = logging.getLogger(__name__)

SQL = """
INSERT INTO jeju_air (station, measured_at, pm10, pm25)
VALUES (%s, %s, %s, %s)
ON CONFLICT (station, measured_at)
DO UPDATE SET pm10 = COALESCE(EXCLUDED.pm10, jeju_air.pm10),
              pm25 = COALESCE(EXCLUDED.pm25, jeju_air.pm25)
"""


def parse_dt10(raw: str | None):
    """DT10 'YYYYMMDDHH' -> datetime. 24시는 익일 00시로 정규화."""
    if not raw or len(raw.strip()) != 10:
        return None
    s = raw.strip()
    try:
        day = datetime.strptime(s[:8], "%Y%m%d")
        hour = int(s[8:])
    except ValueError:
        return None
    if hour == 24:
        return day + timedelta(days=1)
    if not 0 <= hour <= 23:
        return None
    return day.replace(hour=hour)


def fetch_xml(date: datetime) -> ET.Element:
    params = {"date": date.strftime("%Y%m%d")}
    last_err = None
    for attempt in range(config.RETRIES):
        try:
            resp = requests.get(config.JEJU_AIR_URL, params=params, timeout=config.TIMEOUT)
            resp.raise_for_status()
            root = ET.fromstring(resp.content)
            code = root.findtext(".//resultCode", "").strip()
            if code not in ("00", "0", ""):
                raise RuntimeError(
                    f"API 오류 resultCode={code} ({root.findtext('.//resultMsg')})")
            return root
        except (requests.RequestException, ET.ParseError, RuntimeError) as e:
            last_err = e
            wait = 2 ** attempt
            logger.warning("호출 실패 (%d/%d) %s — %ds 후 재시도",
                           attempt + 1, config.RETRIES, e, wait)
            time.sleep(wait)
    raise RuntimeError(f"제주 대기환경 API 최종 실패: {last_err}")


def parse_rows(root: ET.Element) -> list[tuple]:
    rows, skipped = [], set()
    for it in root.iter("list"):
        site = (it.findtext("SITE") or "").strip()
        station = config.JEJU_AIR_SITES.get(site)
        measured_at = parse_dt10(it.findtext("DT10"))
        if not station:
            if site:
                skipped.add(site)
            continue
        if not measured_at:
            continue
        pm10 = num(it.findtext("PM10"), int)
        pm25 = num(it.findtext("PM25"), int)
        if pm10 is None and pm25 is None:
            continue
        rows.append((station, measured_at, pm10, pm25))
    if skipped:
        logger.info("매핑에 없는 SITE 코드 무시: %s", sorted(skipped))
    return rows


def collect() -> int:
    root = fetch_xml(datetime.now())
    rows = parse_rows(root)
    if not rows:
        raise RuntimeError("파싱된 측정값이 없습니다 — 응답 구조 변경 여부를 확인하세요")
    return db.executemany(SQL, rows)
