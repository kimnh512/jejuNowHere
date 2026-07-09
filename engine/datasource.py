"""DB에서 지역별 '지금' 날씨 스냅샷을 조립.

우선순위: 초단기실황(지금) > 초단기예보(+6h: POP·LGT·SKY) > 단기예보(WAV·보완)
+ 자외선(시 단위) + 미세먼지(최근접 측정소).
결측은 None 으로 두고 scoring 이 가중치 재정규화로 흡수합니다.
"""
from datetime import datetime, timedelta

import psycopg2.extras

import db

from . import derived


def _fetch(sql: str, params: tuple = ()) -> list[dict]:
    with db.get_conn() as conn:
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute(sql, params)
            return [dict(r) for r in cur.fetchall()]


def fetch_raw(now: datetime) -> dict:
    h6 = now + timedelta(hours=6)
    return {
        "nowcast": _fetch(
            """SELECT DISTINCT ON (region_id) *
               FROM ultra_nowcast ORDER BY region_id, observed_at DESC"""),
        "ultra": _fetch(
            """SELECT * FROM ultra_forecast
               WHERE fcst_at > %s AND fcst_at <= %s
               ORDER BY region_id, fcst_at""", (now - timedelta(minutes=30), h6)),
        "village": _fetch(
            """SELECT * FROM village_forecast
               WHERE fcst_at > %s AND fcst_at <= %s
               ORDER BY region_id, fcst_at""", (now - timedelta(minutes=30), h6)),
        "minmax": _fetch(
            """SELECT region_id, MAX(tmn) AS tmn, MAX(tmx) AS tmx
               FROM village_forecast
               WHERE fcst_at::date = %s GROUP BY region_id""", (now.date(),)),
        "uv": _fetch(
            """SELECT DISTINCT ON (area_no) area_no, uv_value
               FROM uv_index WHERE fcst_date = %s
               ORDER BY area_no, base_at DESC""", (now.date(),)),
        "air": _fetch(
            """SELECT DISTINCT ON (station) station, pm10, pm25, measured_at
               FROM jeju_air ORDER BY station, measured_at DESC"""),
    }


def build_snapshots(regions: list[dict], raw: dict, now: datetime) -> dict[int, dict]:
    """region_id → 스냅샷. 순수 함수 (DB 접근 없음, 테스트 가능)."""
    now_by = {r["region_id"]: r for r in raw["nowcast"]}
    mm_by = {r["region_id"]: r for r in raw["minmax"]}
    uv_by = {r["area_no"]: r["uv_value"] for r in raw["uv"]}
    air_by = {r["station"]: r for r in raw["air"]}

    ultra_by, village_by = {}, {}
    for r in raw["ultra"]:
        ultra_by.setdefault(r["region_id"], []).append(r)
    for r in raw["village"]:
        village_by.setdefault(r["region_id"], []).append(r)

    out = {}
    for reg in regions:
        rid = reg["region_id"]
        nc = now_by.get(rid) or {}
        ult = ultra_by.get(rid, [])
        vil = village_by.get(rid, [])
        missing = []

        # 현재값 (실황이 2시간 이상 오래됐으면 스킵하고 예보로 대체)
        stale = nc and (now - nc["observed_at"]) > timedelta(hours=2)
        cur_src = None if (not nc or stale) else nc
        first_fc = ult[0] if ult else (vil[0] if vil else {})
        tmp = cur_src["t1h"] if cur_src else first_fc.get("t1h", first_fc.get("tmp"))
        reh = cur_src["reh"] if cur_src else first_fc.get("reh")
        wsd = cur_src["wsd"] if cur_src else first_fc.get("wsd")
        vec = cur_src["vec"] if cur_src else first_fc.get("vec")
        pty_now = cur_src["pty"] if cur_src else first_fc.get("pty")
        rain_now = cur_src["rn1_mm"] if cur_src else first_fc.get("rn1_mm")

        # 집계 창(시작 시각 기준): 강수확률 +3h, 강수 veto용 +1h, 낙뢰 +6h
        h1, h3 = now + timedelta(hours=1), now + timedelta(hours=3)
        u3 = [r for r in ult if r["fcst_at"] <= h3]
        v3 = [r for r in vil if r["fcst_at"] <= h3]
        pops = [r["pop"] for r in u3 + v3 if r.get("pop") is not None]
        pop3 = max(pops) if pops else None
        lgts = [r["lgt"] for r in ult if r.get("lgt") is not None]
        lgt6 = max(lgts) if lgts else None
        pty3s = [r["pty"] for r in u3 + v3 if r["fcst_at"] <= h1 and r.get("pty")]
        pty3 = max(pty3s) if pty3s else 0
        skys = [r.get("sky") for r in ult + vil if r.get("sky") is not None]
        sky = skys[0] if skys else None
        wavs = [r["wav"] for r in vil if r.get("wav") is not None]
        wav = wavs[0] if wavs else None

        uv = uv_by.get(reg.get("area_no"))
        air = air_by.get(reg.get("air_station")) or {}
        pm10, pm25 = air.get("pm10"), air.get("pm25")
        air_stale = bool(air) and (now - air["measured_at"]) > timedelta(hours=3)
        if air_stale:
            pm10 = pm25 = None

        for key, val in [("실황", tmp), ("강수확률", pop3), ("자외선", uv),
                         ("미세먼지", pm25), ("파고", wav)]:
            if val is None:
                missing.append(key)

        feel = derived.feels_like(tmp, wsd, reh)
        mm = mm_by.get(rid) or {}
        snap = {
            "region_id": rid, "name": reg["name"], "city": reg["city"],
            "tmp": tmp, "reh": reh, "wsd": wsd, "vec": vec,
            "pty_now": pty_now, "rain_now": rain_now,
            "observed_at": nc.get("observed_at"), "stale": bool(stale),
            "sky": sky, "pop3": pop3, "lgt6": lgt6, "pty3": pty3,
            "wav": wav, "tmn": mm.get("tmn"), "tmx": mm.get("tmx"),
            "uv": uv, "pm10": pm10, "pm25": pm25,
            "feel": feel,
            "offshore": derived.offshore_state(reg["name"], vec),
            "missing": missing,
        }
        snap["hours"] = _timeline(snap, reg, ult, vil, now)
        out[rid] = snap
    return out


def _timeline(snap: dict, reg: dict, ult: list, vil: list,
              now: datetime) -> list[dict]:
    """지금/+1h/+2h/+3h 시간축 미니 스냅샷 (각각 score_all 입력 형식)."""
    base = now.replace(minute=0, second=0, microsecond=0)
    by_hour = {}
    for r in vil + ult:  # ultra가 village를 덮어씀 (더 정밀)
        by_hour[r["fcst_at"]] = r

    def window(k, key, span):
        vals = [by_hour[base + timedelta(hours=j)].get(key)
                for j in range(k, k + span + 1)
                if base + timedelta(hours=j) in by_hour]
        vals = [v for v in vals if v is not None]
        return max(vals) if vals else None

    hours = [dict(snap, label="지금", offset=0)]
    for k in (1, 2, 3):
        r = by_hour.get(base + timedelta(hours=k))
        if r is None:
            hours.append(None)
            continue
        tmp = r.get("t1h", r.get("tmp"))
        reh, wsd, vec = r.get("reh"), r.get("wsd"), r.get("vec")
        h = {
            "label": f"+{k}h", "offset": k,
            "name": reg["name"], "region_id": reg["region_id"],
            "tmp": tmp, "reh": reh, "wsd": wsd, "vec": vec,
            "feel": derived.feels_like(tmp, wsd, reh),
            "pty_now": r.get("pty"), "pty3": window(k, "pty", 1) or 0,
            "rain_now": r.get("rn1_mm", r.get("pcp_mm")),
            "pop3": window(k, "pop", 3), "lgt6": window(k, "lgt", 3),
            "sky": r.get("sky"),
            "wav": r.get("wav", snap["wav"]),
            "uv": snap["uv"], "pm10": snap["pm10"], "pm25": snap["pm25"],
            "offshore": derived.offshore_state(reg["name"], vec),
        }
        hours.append(h)
    return hours


def load(regions: list[dict], now: datetime | None = None) -> dict[int, dict]:
    now = now or datetime.now()
    return build_snapshots(regions, fetch_raw(now), now)


# ── 피드백 저장 (ML 학습 데이터) ─────────────────────────────────
FEEDBACK_DDL = """
CREATE TABLE IF NOT EXISTS reco_feedback (
    id         SERIAL PRIMARY KEY,
    ts         TIMESTAMP NOT NULL,
    region_id  INT NOT NULL,
    activity   TEXT NOT NULL,
    rule_score REAL,
    features   TEXT NOT NULL,   -- JSON
    label      SMALLINT NOT NULL -- 1 좋았어요 / 0 별로였어요
)"""


def save_feedback(region_id: int, activity: str, rule_score, features_json: str,
                  label: int, ts=None):
    from datetime import datetime as _dt
    with db.get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute(FEEDBACK_DDL)
            cur.execute(
                """INSERT INTO reco_feedback (ts, region_id, activity, rule_score, features, label)
                   VALUES (%s, %s, %s, %s, %s, %s)""",
                (ts or _dt.now(), region_id, activity, rule_score,
                 features_json, label),
            )


def fetch_feedback() -> list[dict]:
    try:
        return _fetch("SELECT * FROM reco_feedback ORDER BY id")
    except Exception:
        return []
