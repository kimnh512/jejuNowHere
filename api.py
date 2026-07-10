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
    GET /nlg?activity=러닝&region=..&lang=ko|en|zh   GPT 문구 3종 (다국어)
    POST /feedback                    "좋았어요/별로" 수집 → 30건부터 자동 재학습

앱에서는 기기 GPS의 lat/lon을 그대로 쿼리로 넘기면 됩니다.
스냅샷은 60초 캐시 — 데이터 자체가 매시 갱신이므로 충분합니다.
"""
import json
import time
from datetime import datetime

from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

import config
import db
import places
from engine import boundaries, datasource, geo, ml, nlg, scoring

app = FastAPI(title="제주나우히어 API", version="1.0")
app.add_middleware(  # 앱/웹 개발 편의를 위한 CORS 허용
    CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"],
)

_cache: dict = {"t": 0.0, "snaps": None, "regions": None, "ml": {}}
CACHE_SEC = 60


def get_data():
    """지역 목록 + 스냅샷 + ML 모델 (60초 캐시)."""
    now = time.time()
    if _cache["snaps"] is None or now - _cache["t"] > CACHE_SEC:
        regions = db.fetch_regions()
        if not regions:
            raise HTTPException(503, "locations 테이블이 비어 있습니다 (seed_locations.py 실행 필요)")
        # 모델: 파일(로컬 CLI 학습분) < DB(서버 자동학습분) 우선
        ml_params = {**ml.load_params(), **datasource.load_ml_params()}
        _cache.update(t=now, regions=regions,
                      snaps=datasource.load(regions), ml=ml_params)
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
    params = _cache["ml"]

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


@app.get("/nlg")
def nlg_message(activity: str = "러닝",
                place: str | None = Query(None, description="추천 장소명 (예: 서우봉). 없으면 지역명 사용"),
                place_features: str | None = Query(None, description="장소 특징 (소개 문구 근거)"),
                lang: str = Query("ko", pattern="^(ko|en|zh)$",
                                  description="문구 언어: ko 한국어 / en 영어 / zh 중국어"),
                region: str | None = None,
                lat: float | None = Query(None, ge=-90, le=90),
                lon: float | None = Query(None, ge=-180, le=180)):
    """GPT 문구 3종 — 앱 홈 화면용 (한국어/영어/중국어).

    응답: recommendation_message(추천 문장), outfit(복장 리스트),
          place_intro(장소 소개 한마디), llm(GPT 사용 여부), lang(언어)
    """
    regions, snaps = get_data()
    reg, source = resolve_region(regions, region, lat, lon)
    snap = snaps[reg["region_id"]]

    results = scoring.score_all(snap)
    if activity not in results:
        raise HTTPException(404, f"'{activity}'은 지원 활동이 아닙니다: {list(results)}")
    r = results[activity]

    # 시간대별 예보 — "N시 이후 쾌적해져요" 팁의 근거 (지금, +1h, +2h, +3h)
    base_hour = datetime.now().hour
    hourly = []
    for i, h in enumerate(snap.get("hours") or []):
        if h:
            hourly.append({"hour": (base_hour + i) % 24, "temp": h.get("tmp"),
                           "humidity": h.get("reh"), "precip_prob": h.get("pop3")})

    payload = {
        "activity": activity,
        "place": {"name": place or reg["name"], "features": place_features},
        "weather": {"temp": snap.get("tmp"), "feels_like": snap.get("feel"),
                    "humidity": snap.get("reh"), "wind_speed": snap.get("wsd"),
                    "sky": snap.get("sky"), "precip_prob": snap.get("pop3"),
                    "uv": snap.get("uv"), "pm10": snap.get("pm10")},
        "suitability": {"score": r["score"], "veto": r["veto"],
                        "reason": scoring.phrase(activity, r)},
        "hourly": hourly,
        "time_of_day": ("아침" if 5 <= base_hour < 11 else "낮" if 11 <= base_hour < 17
                        else "저녁" if 17 <= base_hour < 21 else "밤"),
    }
    out = nlg.generate(payload, lang)
    out["location"] = {"region": reg["name"], "city": reg["city"], "source": source}
    out["suitability"] = payload["suitability"]
    return out


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


# ── ML 피드백 수집 ───────────────────────────────────────────────
class FeedbackIn(BaseModel):
    """앱의 '좋았어요/별로였어요' 평가 한 건."""
    activity: str = Field(examples=["러닝"])
    good: bool = Field(description="True=좋았어요(1) / False=별로였어요(0)")
    region: str | None = None
    lat: float | None = Field(None, ge=-90, le=90)
    lon: float | None = Field(None, ge=-180, le=180)


@app.post("/feedback")
def feedback(body: FeedbackIn):
    """평가 저장 → 그 시각의 날씨 특성과 함께 학습 데이터로 축적.

    활동별 30건(양/음 라벨 포함)부터 자동 재학습되어 /scores 점수에
    블렌딩됩니다 (응답의 ml_active로 확인).
    """
    if body.activity not in boundaries.ACTIVITIES:
        raise HTTPException(404, f"'{body.activity}'은 지원 활동이 아닙니다: {boundaries.ACTIVITIES}")
    regions, snaps = get_data()
    reg, source = resolve_region(regions, body.region, body.lat, body.lon)
    snap = snaps[reg["region_id"]]

    results = scoring.score_all(snap)
    rule_score = results[body.activity]["score"]
    features = json.dumps(ml.extract_features(snap), ensure_ascii=False)
    datasource.save_feedback(reg["region_id"], body.activity, rule_score,
                             features, 1 if body.good else 0)

    # 자동 재학습 (해당 활동만 재계산 — 데이터가 작아 수십 ms 수준)
    rows = datasource.fetch_feedback()
    act_rows = [r for r in rows if r["activity"] == body.activity]
    trained = False
    if len(act_rows) >= ml.MIN_SAMPLES:
        params, report = ml.train_from_rows(act_rows)
        if body.activity in params:
            datasource.save_ml_params({body.activity: params[body.activity]})
            _cache["t"] = 0.0          # 다음 요청에서 새 모델 반영
            trained = True

    return {
        "saved": True,
        "activity": body.activity,
        "region": reg["name"],
        "label": 1 if body.good else 0,
        "total_for_activity": len(act_rows),
        "needed_for_ml": max(0, ml.MIN_SAMPLES - len(act_rows)),
        "retrained": trained,
    }
