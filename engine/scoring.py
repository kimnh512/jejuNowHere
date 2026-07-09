"""점수 엔진: Veto → 사다리꼴 소프트 점수 → 가중합 (0~100점).

결측 변수는 제외하고 남은 가중치를 재정규화합니다.
"""
from . import boundaries

VAR_LABEL = {
    "feel": "체감온도", "reh": "습도", "wsd": "바람", "wsd_alt": "바람(고지대)",
    "pop3": "강수확률", "uv": "자외선", "pm25": "초미세먼지", "pm10": "미세먼지",
    "wav": "파고", "sky": "하늘상태", "offshore": "바람방향",
}

RAIN_PTY = {1, 2, 4, 5, 6}  # 비 계열
SNOW_PTY = {2, 3, 6, 7}


def trapezoid(x: float, a: float, b: float, c: float, d: float) -> float:
    if b <= x <= c:
        return 1.0
    if x <= a or x >= d:
        return 0.0
    if x < b:
        return (x - a) / (b - a)
    return (d - x) / (d - c)


# ── Veto 체크 (조건 id → (판정 함수, 사유 문구)) ─────────────────
VETO_CHECKS = {
    "lightning":  (lambda s: (s.get("lgt6") or 0) > 0,
                   "낙뢰 예보 — 야외활동 위험"),
    "precip_now": (lambda s: (s.get("pty_now") or 0) != 0 or (s.get("pty3") or 0) != 0,
                   "비/눈 (현재 또는 3시간 내)"),
    "heavy_rain": (lambda s: (s.get("pty_now") or 0) != 0 and (s.get("rain_now") or 0) >= 2,
                   "강한 비"),
    "pm_bad":     (lambda s: (s.get("pm25") or 0) > 75 or (s.get("pm10") or 0) > 150,
                   "미세먼지 매우나쁨"),
    "gale":       (lambda s: (s.get("wsd") or 0) >= 14,
                   "강풍 (14m/s 이상)"),
    "drone_wind": (lambda s: (s.get("wsd") or 0) > 5,
                   "풍속 5m/s 초과 — 드론 비행 부적합"),
    "surf_wave_high": (lambda s: s.get("wav") is not None and s["wav"] > 3.0,
                       "파고 3m 초과 — 위험"),
    "surf_flat":  (lambda s: s.get("wav") is not None and s["wav"] < 0.2,
                   "파도가 거의 없음"),
}


def _var_value(snapshot: dict, var: str):
    if var == "wsd_alt":
        w = snapshot.get("wsd")
        return None if w is None else w * 1.6
    return snapshot.get(var)


def score_activity(activity: str, snapshot: dict) -> dict:
    """반환: {score, veto(사유|None), parts: {변수: (개별점수, 실효가중치)}}"""
    # 1) Veto
    for vid in boundaries.VETOES.get(activity, []):
        check, reason = VETO_CHECKS[vid]
        if check(snapshot):
            return {"score": 0, "veto": reason, "parts": {}}

    # 2) 쇼핑 역방향: 야외 조건이 나쁠수록 점수↑ (최저 50점 보장)
    if activity == "쇼핑":
        comfort = []
        feel = snapshot.get("feel")
        if feel is not None:
            comfort.append(trapezoid(feel, 0, 10, 26, 34))
        pop3 = snapshot.get("pop3")
        if pop3 is not None:
            comfort.append(trapezoid(pop3, -1, 0, 20, 60))
        badness = 1 - (sum(comfort) / len(comfort)) if comfort else 0.3
        return {"score": round(50 + 50 * badness), "veto": None, "parts": {}}

    # 3) 사다리꼴 가중합 + 결측 재정규화
    spec = boundaries.TRAPEZOIDS[activity]
    parts, total_w, acc = {}, 0.0, 0.0
    for var, (w, bound) in spec.items():
        val = _var_value(snapshot, var)
        if val is None:
            continue
        if isinstance(bound, dict):          # 범주형
            sub = bound.get(val)
            if sub is None:
                continue
        else:
            sub = trapezoid(float(val), *bound)
        parts[var] = (sub, w)
        acc += sub * w
        total_w += w
    if total_w == 0:
        return {"score": None, "veto": None, "parts": {}}
    return {"score": round(100 * acc / total_w), "veto": None, "parts": parts}


def worst_factor(parts: dict) -> str | None:
    """감점이 가장 큰 변수 → 문구 재료."""
    worst, loss = None, 0.0
    for var, (sub, w) in parts.items():
        this_loss = (1 - sub) * w
        if this_loss > loss:
            worst, loss = var, this_loss
    return worst if loss >= 0.05 else None


def phrase(activity: str, result: dict) -> str:
    if result["veto"]:
        return f"금지: {result['veto']}"
    s = result["score"]
    if s is None:
        return "데이터 부족"
    bad = worst_factor(result["parts"])
    tail = f" ({VAR_LABEL[bad]} 감점)" if bad else ""
    if activity == "쇼핑":
        return "야외가 아쉬운 날, 실내 코스 추천" if s >= 75 else "무난한 실내 대안"
    if s >= 80:
        return "최적입니다, 지금 나가세요" + tail
    if s >= 60:
        return "좋은 편" + tail
    if s >= 40:
        return "무난하지만 아쉬움" + tail
    return "오늘은 비추천" + tail


def score_all(snapshot: dict) -> dict:
    return {act: score_activity(act, snapshot) for act in boundaries.ACTIVITIES}


def _validate_weights():
    for act, spec in boundaries.TRAPEZOIDS.items():
        total = sum(w for w, _ in spec.values())
        assert abs(total - 1.0) < 1e-6, f"{act} 가중치 합 {total} != 1.0"


_validate_weights()
