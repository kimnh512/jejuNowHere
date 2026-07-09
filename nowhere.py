"""제주나우히어 — 실시간 위치 기반 활동 적합도 & 추천 (터미널).

사용법:
  python nowhere.py                  위치 자동 인식 → 10분마다 갱신 (q 종료, r 평가)
  python nowhere.py --once           1회 출력
  python nowhere.py --region 애월읍  지역 직접 지정
  python nowhere.py --lat 33.46 --lon 126.33   좌표 직접 입력 (앱 GPS 시뮬레이션)
  python nowhere.py rate             지금 추천 평가 남기기 (ML 학습 데이터)
  python nowhere.py train            쌓인 평가로 ML 모델 학습
"""
import argparse
import json
import os
import sys
import time
from datetime import datetime

import db
from engine import boundaries, datasource, geo, ml, render, scoring


def compute(region: dict, snaps: dict, params: dict):
    snap = snaps[region["region_id"]]
    results = scoring.score_all(snap)
    ml_used = set()
    for act, r in results.items():
        blended, used = ml.blend(act, r["score"], snap, params)
        if used:
            r["score"] = blended
            ml_used.add(act)
    all_results = {rid: scoring.score_all(s) for rid, s in snaps.items()}
    return snap, results, all_results, ml_used


def show(region, source, params):
    snaps = datasource.load(db.fetch_regions())
    snap, results, all_results, ml_used = compute(region, snaps, params)
    print(render.render(region, snap, results, source, snaps, all_results, ml_used))
    return snap, results


def cmd_rate(region, source):
    snaps = datasource.load(db.fetch_regions())
    snap = snaps[region["region_id"]]
    results = scoring.score_all(snap)
    print(f"\n{region['name']} 기준, 오늘 해본 활동을 평가해주세요:")
    acts = boundaries.ACTIVITIES
    for i, a in enumerate(acts, 1):
        s = results[a]["score"]
        print(f"  {i}. {a} (현재 점수 {s if s is not None else '─'})")
    raw = input("활동 번호 > ").strip()
    if not (raw.isdigit() and 1 <= int(raw) <= len(acts)):
        print("취소했습니다.")
        return
    act = acts[int(raw) - 1]
    ans = input(f"'{act}' 실제로 어땠나요? 좋았으면 y, 별로였으면 n > ").strip().lower()
    if ans not in ("y", "n"):
        print("취소했습니다.")
        return
    feats = json.dumps(ml.extract_features(snap), ensure_ascii=False)
    datasource.save_feedback(region["region_id"], act, results[act]["score"],
                             feats, 1 if ans == "y" else 0)
    rows = datasource.fetch_feedback()
    n = sum(1 for r in rows if r["activity"] == act)
    print(f"저장했습니다. '{act}' 평가 누적 {n}건"
          f" (30건부터 ML 학습 가능 — python nowhere.py train)")


def cmd_train():
    rows = datasource.fetch_feedback()
    if not rows:
        print("아직 평가 데이터가 없습니다. 먼저 'python nowhere.py rate' 로 평가를 남겨주세요.")
        return
    report = ml.train_all(rows)
    print(f"피드백 총 {len(rows)}건")
    for act, msg in report.items():
        print(f"  {act}: {msg}")
    if any("학습 완료" in m for m in report.values()):
        print("다음 실행부터 [ML] 표시와 함께 블렌딩된 점수가 나옵니다.")


def watch_loop(region, source, params, interval):
    try:
        import msvcrt
        has_kb = True
    except ImportError:
        has_kb = False
    while True:
        os.system("cls" if os.name == "nt" else "clear")
        try:
            show(region, source, params)
        except Exception as e:
            print(f"데이터 조회 실패: {e}\nDB와 .env 설정을 확인하세요.")
        print(f"\n\033[2m{interval // 60}분마다 갱신 · q 종료 · r 평가 남기기\033[0m")
        deadline = time.time() + interval
        while time.time() < deadline:
            if has_kb and msvcrt.kbhit():
                key = msvcrt.getwch().lower()
                if key == "q":
                    return
                if key == "r":
                    cmd_rate(region, source)
                    input("계속하려면 Enter...")
                    break
            time.sleep(0.2)


def main():
    os.system("")  # Windows 콘솔 ANSI 활성화
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("command", nargs="?", default="live",
                   choices=["live", "rate", "train"])
    p.add_argument("--once", action="store_true", help="1회 출력 후 종료")
    p.add_argument("--region", help="읍면 직접 지정 (예: 애월읍)")
    p.add_argument("--lat", type=float)
    p.add_argument("--lon", type=float)
    p.add_argument("--interval", type=int, default=600, help="갱신 주기(초)")
    args = p.parse_args()

    if args.command == "train":
        cmd_train()
        return

    regions = db.fetch_regions()
    if not regions:
        sys.exit("locations 테이블이 비어 있습니다. 먼저 python seed_locations.py 실행.")
    region, source = geo.resolve(regions, args.region, args.lat, args.lon)

    if args.command == "rate":
        cmd_rate(region, source)
        return

    params = ml.load_params()
    if args.once:
        show(region, source, params)
    else:
        watch_loop(region, source, params, args.interval)


if __name__ == "__main__":
    main()
