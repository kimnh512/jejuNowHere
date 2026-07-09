"""수집 실행 진입점. collect_log에 성공/실패를 기록한다.

사용법:
    python run.py village     # 단기예보 (기온·습도·풍속·강수확률·강수량 등)
    python run.py nowcast     # 초단기실황 (지금 날씨)
    python run.py ultra       # 초단기예보 (향후 6시간)
    python run.py uv          # 자외선지수 (일 2회)
    python run.py jeju_air    # 제주 미세먼지 PM10/PM2.5 (매시)
    python run.py all         # 전체 순차 실행
"""
import argparse
import logging
import sys
from datetime import datetime

import db
from collectors import village, nowcast, ultra, uv, jeju_air

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s: %(message)s",
)
logger = logging.getLogger("run")

SOURCES = {
    "village": village.collect,
    "nowcast": nowcast.collect,
    "ultra": ultra.collect,
    "uv": uv.collect,
    "jeju_air": jeju_air.collect,
}


def run_one(source: str) -> bool:
    fn = SOURCES[source]
    started = datetime.now()
    try:
        rows = fn()
        db.log_run(source, started, datetime.now(), "success", rows)
        logger.info("[%s] 성공 — %d행 적재", source, rows)
        return True
    except Exception as e:
        db.log_run(source, started, datetime.now(), "fail", 0, str(e)[:1000])
        logger.exception("[%s] 실패: %s", source, e)
        return False


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("source", choices=[*SOURCES, "all"])
    args = parser.parse_args()

    targets = list(SOURCES) if args.source == "all" else [args.source]
    ok = all([run_one(s) for s in targets])
    sys.exit(0 if ok else 1)


if __name__ == "__main__":
    main()
