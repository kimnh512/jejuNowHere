"""가면 좋을 곳 5선 — 날씨 점수 × 카카오 로컬 장소 검색.

흐름:
  1. 현재 위치 인식 (Windows 위치서비스 → IP → 수동, engine.geo)
  2. 전 읍면 활동 점수 계산 (engine.scoring)
  3. 점수 상위 활동별로 "지금 가장 좋은 읍면" 주변을 카카오 로컬 API로 검색
  4. 실제 장소 5곳 추천 — 터미널 출력 (--json: 앱 연동용 JSON 출력)

사용법:
  python places.py                  # 위치 자동 인식
  python places.py --region 애월읍
  python places.py --json           # 플러터/안드로이드 연동용 JSON

사전 준비 (.env):
  KAKAO_REST_KEY=REST_API_키       # developers.kakao.com 앱 키
"""
import argparse
import json
import os
import sys

import requests

import config
import db
from engine import boundaries, datasource, geo, scoring

# 활동 → 카카오 키워드 (앞의 것부터 시도, 결과 부족하면 다음 키워드)
KAKAO_QUERY = {
    "러닝": ["공원", "해안도로"],
    "강아지산책": ["공원", "산책로"],
    "등산": ["오름"],
    "드론": ["전망대", "해변"],
    "서핑": ["서핑", "해수욕장"],
    "골프": ["골프장"],
    "쇼핑": ["쇼핑몰", "시장"],
}
MARKER = ["①", "②", "③", "④", "⑤"]


def kakao_search(query: str, lat: float, lon: float, radius=10000, size=5) -> list[dict]:
    """카카오 로컬 키워드 검색 — 좌표 중심 반경 내, 거리순."""
    r = requests.get(
        "https://dapi.kakao.com/v2/local/search/keyword.json",
        headers={"Authorization": f"KakaoAK {config.KAKAO_REST_KEY}"},
        params={"query": query, "x": lon, "y": lat,
                "radius": radius, "sort": "distance", "size": size},
        timeout=config.TIMEOUT,
    )
    if r.status_code == 401:
        sys.exit("카카오 REST 키가 유효하지 않습니다. .env의 KAKAO_REST_KEY를 확인하세요.")
    r.raise_for_status()
    return r.json().get("documents", [])


_image_cache: dict = {}


def kakao_image(place_name: str) -> str | None:
    """카카오 이미지 검색 — 장소 대표 사진 1장 (실패해도 추천은 계속)."""
    if place_name in _image_cache:
        return _image_cache[place_name]
    url = None
    try:
        r = requests.get(
            "https://dapi.kakao.com/v2/search/image",
            headers={"Authorization": f"KakaoAK {config.KAKAO_REST_KEY}"},
            params={"query": f"제주 {place_name}", "size": 1, "sort": "accuracy"},
            timeout=config.TIMEOUT,
        )
        if r.ok:
            docs = r.json().get("documents", [])
            if docs:
                url = docs[0].get("thumbnail_url") or docs[0].get("image_url")
    except requests.RequestException:
        pass
    _image_cache[place_name] = url
    return url


def best_region_for(activity: str, all_results: dict, snaps: dict):
    ranked = [(rid, res[activity]["score"]) for rid, res in all_results.items()
              if res[activity]["score"] is not None and not res[activity]["veto"]]
    if not ranked:
        return None
    rid, score = max(ranked, key=lambda t: t[1])
    return snaps[rid], score


def pick_places(region: dict, regions: list[dict], snaps: dict,
                all_results: dict, want=5) -> list[dict]:
    """점수 상위 활동 순회 → 활동별 최적 읍면 주변 검색 → 총 want곳."""
    my_results = all_results[region["region_id"]]
    acts = sorted(
        (a for a in boundaries.ACTIVITIES
         if my_results[a]["score"] is not None and not my_results[a]["veto"]),
        key=lambda a: -my_results[a]["score"])

    picks, seen = [], set()
    for act in acts:
        if len(picks) >= want:
            break
        spot = best_region_for(act, all_results, snaps)
        if spot is None:
            continue
        best_snap, best_score = spot
        reg_meta = next(r for r in regions
                        if r["region_id"] == best_snap["region_id"])
        for query in KAKAO_QUERY.get(act, []):
            docs = kakao_search(query, reg_meta["lat"], reg_meta["lon"])
            for d in docs:
                if d["id"] in seen:
                    continue
                seen.add(d["id"])
                plat, plon = float(d["y"]), float(d["x"])
                picks.append({
                    "name": d["place_name"],
                    "activity": act,
                    "score": best_score,
                    "region": best_snap["name"],
                    "address": d.get("road_address_name") or d.get("address_name", ""),
                    "category": d.get("category_name", "").split(">")[-1].strip(),
                    "url": d.get("place_url", ""),
                    "image": kakao_image(d["place_name"]),   # 대표 사진 (카카오 이미지 검색)
                    "lat": plat, "lon": plon,
                    "dist_km": round(geo.haversine_km(
                        region["lat"], region["lon"], plat, plon), 1),
                })
                if len(picks) >= want or len([p for p in picks if p["activity"] == act]) >= 2:
                    break
            if len(picks) >= want or len([p for p in picks if p["activity"] == act]) >= 2:
                break
    return picks[:want]


def print_picks(region: dict, source: str, picks: list[dict]):
    os.system("")
    B, C, D, E = "\033[1m", "\033[36m", "\033[2m", "\033[0m"
    print(f"\n{B}{C}◈ 지금 가면 좋을 곳 5선{E}  — 현재 위치: {B}{region['name']}{E} {D}({source}){E}\n")
    for i, p in enumerate(picks):
        print(f" {MARKER[i]} {B}{p['name']}{E}  {D}{p['category']}{E}")
        print(f"    {p['activity']} {p['score']}점 · {p['region']} · "
              f"현위치에서 {p['dist_km']}km")
        print(f"    {D}{p['address']} · {p['url']}{E}")
    if not picks:
        print("  추천할 장소가 없습니다 (모든 활동 veto 또는 검색 결과 없음).")


def recommend(region: dict, regions: list[dict]) -> dict:
    """앱/API에서 그대로 쓸 수 있는 추천 결과 구조.

    플러터/안드로이드 연동 시 이 함수를 REST API(FastAPI 등)로 감싸면 됩니다.
    """
    snaps = datasource.load(regions)
    all_results = {rid: scoring.score_all(s) for rid, s in snaps.items()}
    picks = pick_places(region, regions, snaps, all_results)
    me = snaps[region["region_id"]]
    return {
        "location": {"region": region["name"], "city": region["city"],
                     "lat": region["lat"], "lon": region["lon"]},
        "weather": {k: me.get(k) for k in
                    ("tmp", "feel", "reh", "wsd", "sky", "pop3",
                     "uv", "pm10", "pm25", "wav")},
        "scores": {a: {"score": r["score"], "veto": r["veto"]}
                   for a, r in all_results[region["region_id"]].items()},
        "places": picks,
    }


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--region")
    p.add_argument("--lat", type=float)
    p.add_argument("--lon", type=float)
    p.add_argument("--json", action="store_true",
                   help="사람용 출력 대신 JSON (앱 연동용)")
    args = p.parse_args()

    if not config.KAKAO_REST_KEY:
        sys.exit(".env에 KAKAO_REST_KEY가 없습니다. developers.kakao.com에서 "
                 "앱을 만들고 REST API 키를 넣어주세요.")

    regions = db.fetch_regions()
    region, source = geo.resolve(regions, args.region, args.lat, args.lon)
    result = recommend(region, regions)

    if args.json:
        print(json.dumps(result, ensure_ascii=False, indent=2, default=str))
    else:
        print_picks(region, source, result["places"])


if __name__ == "__main__":
    main()
