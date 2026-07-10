"""제주나우히어 REST API — 플러터/안드로이드 앱 연동용 백엔드.

실행:
    pip install fastapi uvicorn
    uvicorn api:app --host 0.0.0.0 --port 8000
    (개발 중 자동 재시작: --reload)

엔드포인트:
    GET /health                       서버·DB·수집 상태
    GET /regions                      읍면 14곳 목록 (앱의 지역 선택 UI용)
    GET /scores?lat=..&lon=..         활동별 적합도 + 지금/+1h/+2h/+3h 타임라인
    GET /scores?region=애월읍         (앱 GPS 대신 지역명으로도 가능)
    GET /recommend?lat=..&lon=..      가면 좋을 곳 5선 (카카오 장소 포함)

앱에서는 기기 GPS의 lat/lon을 그대로 쿼리로 넘기면 됩니다.
스냅샷은 60초 캐시 — 데이터 자체가 매시 갱신이므로 충분합니다.
"""
import time
from datetime import datetime

from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware

import config
import db
import places
from engine import boundaries, datasource, geo, ml, scoring

app = FastAPI(title="제주나우히어 API", version="1.0")
app.add_middleware(  # 앱/웹 개발 편의를 위한 CORS 허용
    CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"],
)

_cache: dict = {"t": 0.0, "snaps": None, "regions": None}
CACHE_SEC = 60


def get_data():
    """지역 목록 + 스냅샷 (60초 캐시)."""
    now = time.time()
    if _cache["snaps"] is None or now - _cache["t"] > CACHE_SEC:
        regions = db.fetch_regions()
        if not regions:
            raise HTTPException(503, "locations 테이블이 비어 있습니다 (seed_locations.py 실행 필요)")
        _cache.update(t=now, regions=regions, snaps=datasource.load(regions))
    return _cache["regions"], _cache["snaps"]


def resolve_region(regions, region: str | None, lat: float | None, lon: float | None):
    """API용 위치 결정 — 대화형 폴백 없이 파라미터만 사용."""
    if region:
        for r in regions:
            if r["name"] == region:
                return r, "지역명"
        raise HTTPException(404, f"'{region}'은 등록된 읍면이 아닙니다")
    if lat is not None and lon is not None:
        if not geo.in_jeju(lat, lon):
            raise HTTPException(422, "좌표가 제주도 범위 밖입니다")
        r, d = geo.nearest_region(lat, lon, regions)
        return r, f"GPS 최근접 ({d}km)"
    raise HTTPException(422, "region 또는 lat+lon 파라미터가 필요합니다")


@app.get("/", include_in_schema=False)
def root():
    from fastapi.responses import RedirectResponse
    return RedirectResponse("/docs")


@app.get("/health")
def health():
    try:
        with db.get_conn() as conn:
            with conn.cursor() as cur:
                cur.execute("""SELECT source, MAX(finished_at) FROM collect_log
                               WHERE status='success' GROUP BY source""")
                last = {r[0]: str(r[1]) for r in cur.fetchall()}
    except Exception as e:
        raise HTTPException(503, f"DB 연결 실패: {e}")
    return {"status": "ok", "time": str(datetime.now()), "last_collect": last}


@app.get("/regions")
def regions_list():
    regions, snaps = get_data()
    return [{"region_id": r["region_id"], "name": r["name"], "city": r["city"],
             "lat": r["lat"], "lon": r["lon"]} for r in regions]


@app.get("/scores")
def scores(region: str | None = None,
           lat: float | None = Query(None, ge=-90, le=90),
           lon: float | None = Query(None, ge=-180, le=180)):
    regions, snaps = get_data()
    reg, source = resolve_region(regions, region, lat, lon)
    snap = snaps[reg["region_id"]]
    params = ml.load_params()

    results = scoring.score_all(snap)
    ml_used = []
    for act, r in results.items():
        blended, used = ml.blend(act, r["score"], snap, params)
        if used:
            r["score"] = blended
            ml_used.append(act)

    hours = snap.get("hours") or []
    timeline = {}
    for act in boundaries.ACTIVITIES:
        cells = [results[act]["score"]]
        for h in hours[1:]:
            cells.append(scoring.score_all(h)[act]["score"] if h else None)
        timeline[act] = cells  # [지금, +1h, +2h, +3h]

    all_results = {rid: scoring.score_all(s) for rid, s in snaps.items()}
    best = {}
    for act in boundaries.ACTIVITIES:
        ranked = sorted(((rid, res[act]["score"]) for rid, res in all_results.items()
                         if res[act]["score"] is not None and not res[act]["veto"]),
                        key=lambda t: -t[1])
        best[act] = [{"region": snaps[rid]["name"], "score": s}
                     for rid, s in ranked[:3]]

    return {
        "location": {"region": reg["name"], "city": reg["city"],
                     "lat": reg["lat"], "lon": reg["lon"], "source": source},
        "weather": {k: snap.get(k) for k in
                    ("tmp", "feel", "tmn", "tmx", "reh", "wsd", "sky",
                     "pop3", "uv", "pm10", "pm25", "wav")},
        "observed_at": str(snap.get("observed_at")),
        "activities": {a: {"score": r["score"], "veto": r["veto"],
                           "phrase": scoring.phrase(a, r),
                           "timeline": timeline[a],
                           "ml": a in ml_used}
                       for a, r in results.items()},
        "best_regions": best,
        "missing": snap.get("missing", []),
    }


@app.get("/recommend")
def recommend(region: str | None = None,
              lat: float | None = Query(None, ge=-90, le=90),
              lon: float | None = Query(None, ge=-180, le=180)):
    if not config.KAKAO_REST_KEY:
        raise HTTPException(503, ".env에 KAKAO_REST_KEY가 없습니다")
    regions, snaps = get_data()
    reg, source = resolve_region(regions, region, lat, lon)
    out = places.recommend(reg, regions)
    out["location"]["source"] = source
    return out
