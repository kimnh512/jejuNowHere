"""공용: 재시도/백오프 HTTP 호출, 결측·범주값 파싱, 카테고리 피벗."""
import logging
import time
from datetime import datetime

import requests

import config

logger = logging.getLogger(__name__)


def fetch_items(url: str, extra_params: dict) -> list[dict]:
    """단기예보 서비스 공통 호출. 지수 백오프 재시도 포함, items 리스트 반환."""
    params = {
        "serviceKey": config.DATA_GO_KR_KEY,
        "dataType": "JSON",
        "numOfRows": 1000,
        "pageNo": 1,
        **extra_params,
    }
    last_err = None
    for attempt in range(config.RETRIES):
        try:
            resp = requests.get(url, params=params, timeout=config.TIMEOUT)
            resp.raise_for_status()
            data = resp.json()
            header = data.get("response", {}).get("header", {})
            code = str(header.get("resultCode", ""))
            if code not in ("0", "00"):
                raise RuntimeError(f"API 오류 resultCode={code} ({header.get('resultMsg')})")
            body = data.get("response", {}).get("body", {})
            items = body.get("items", {})
            if isinstance(items, dict):
                items = items.get("item", [])
            return items or []
        except (requests.RequestException, ValueError, RuntimeError) as e:
            last_err = e
            wait = 2 ** attempt
            logger.warning("호출 실패 (%d/%d) %s — %ds 후 재시도", attempt + 1, config.RETRIES, e, wait)
            time.sleep(wait)
    raise RuntimeError(f"API 호출 최종 실패: {url} — {last_err}")


def num(raw, cast=float):
    """수치 파싱. 가이드 기준 +900 이상 / -900 이하는 결측(Missing) -> None."""
    if raw is None:
        return None
    s = str(raw).strip()
    if s in ("", "-", "null", "None"):
        return None
    try:
        v = float(s)
    except ValueError:
        return None
    if v >= 900 or v <= -900:
        return None
    return cast(v)


def parse_precip(raw) -> tuple:
    """강수량/신적설 범주 문자열 -> (원문, 하한 수치).

    가이드 표기: '강수없음', '1mm 미만', 실수값+mm(1.0~29.9mm), '30.0~50.0mm',
    '50.0mm 이상' / 눈: '적설없음', '0.5cm 미만', '5.0cm 이상' 등.
    """
    if raw is None:
        return None, None
    s = str(raw).strip()
    if s in ("", "-", "null", "None"):
        return None, None
    if s in ("강수없음", "적설없음") or s == "0":
        return None, 0.0
    if s.endswith("미만"):  # '1mm 미만', '0.5cm 미만' -> 미량으로 취급
        return s, 0.1
    numpart = ""
    for ch in s:
        if ch.isdigit() or ch == ".":
            numpart += ch
        elif numpart:
            break
    try:
        return s, float(numpart)
    except ValueError:
        return s, None


def pivot(items: list[dict], date_key: str, time_key: str) -> dict:
    """카테고리 세로 응답 -> {일시: {category: value}} 피벗."""
    out: dict[datetime, dict] = {}
    for it in items:
        dt = datetime.strptime(it[date_key] + it[time_key], "%Y%m%d%H%M")
        value = it.get("fcstValue", it.get("obsrValue"))
        out.setdefault(dt, {})[it["category"]] = value
    return out
