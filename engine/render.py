"""터미널 렌더링 (ANSI 컬러)."""
from datetime import datetime

from . import boundaries, derived, scoring

R, G, Y, DIM, BOLD, END = "\033[31m", "\033[32m", "\033[33m", "\033[2m", "\033[1m", "\033[0m"
CYAN = "\033[36m"
SKY_TEXT = {1: "맑음", 3: "구름많음", 4: "흐림"}
PTY_TEXT = {0: "", 1: "비", 2: "비/눈", 3: "눈", 4: "소나기", 5: "빗방울", 6: "빗방울눈날림", 7: "눈날림"}


def _color(s):
    if s is None:
        return DIM
    return G if s >= 70 else (Y if s >= 40 else R)


def _bar(s, width=20):
    if s is None:
        return DIM + "─" * width + END
    fill = round(s / 100 * width)
    return _color(s) + "█" * fill + DIM + "░" * (width - fill) + END


def _fmt(v, unit="", nd=0):
    if v is None:
        return "─"
    return f"{v:.{nd}f}{unit}" if isinstance(v, float) else f"{v}{unit}"


def _hour_results(snap: dict) -> list:
    """+1h/+2h/+3h 미니 스냅샷별 점수 (지금은 results로 이미 있음)."""
    out = []
    for h in (snap.get("hours") or [None] * 4)[1:]:
        out.append(scoring.score_all(h) if h else None)
    return out


def _timeline_text(act: str, now_score, hour_results: list) -> str:
    nums, future = [], []
    for hr in hour_results:
        s = hr[act]["score"] if hr else None
        future.append(s)
        nums.append(f"{_color(s)}{s:>3}{END}" if s is not None else f"{DIM}  ─{END}")
    trend = ""
    vals = [v for v in future if v is not None]
    if now_score is not None and vals:
        if min(vals) <= now_score - 25:
            trend = f" {Y}▼곧 나빠짐{END}"
        elif max(vals) >= now_score + 25:
            trend = f" {G}▲곧 좋아짐{END}"
    return " →" + " ".join(nums) + trend


def render(region: dict, snap: dict, results: dict, source: str,
           all_snaps: dict, all_results: dict, ml_used: set) -> str:
    L = []
    now = datetime.now().strftime("%m/%d %H:%M")
    L.append(f"{BOLD}{CYAN}◈ 제주나우히어{END}  {BOLD}{region['name']}{END} ({region['city']})  {now}")
    L.append(f"{DIM}위치: {source}{END}")

    # 현재 날씨 요약
    w = []
    if snap.get("tmp") is not None:
        w.append(f"기온 {_fmt(snap['tmp'], '℃', 1)} (체감 {_fmt(snap['feel'], '℃', 1)})")
    if snap.get("tmn") is not None or snap.get("tmx") is not None:
        w.append(f"최저/최고 {_fmt(snap['tmn'], '', 0)}/{_fmt(snap['tmx'], '℃', 0)}")
    if snap.get("reh") is not None:
        w.append(f"습도 {_fmt(snap['reh'], '%')}")
    if snap.get("wsd") is not None:
        w.append(f"바람 {_fmt(snap['wsd'], 'm/s', 1)}")
    if snap.get("sky") is not None:
        w.append(SKY_TEXT.get(snap["sky"], "?"))
    if snap.get("pty_now"):
        w.append(f"{R}{PTY_TEXT.get(snap['pty_now'], '강수')}{END}")
    if snap.get("pop3") is not None:
        w.append(f"강수확률(3h) {_fmt(snap['pop3'], '%')}")
    L.append("  " + " · ".join(w) if w else "  (기상 데이터 없음)")

    e = []
    uv_g = derived.grade(snap.get("uv"), boundaries.UV_GRADE)
    if uv_g:
        e.append(f"자외선 {snap['uv']}({uv_g})")
    pm_g = derived.grade(snap.get("pm25"), boundaries.PM25_GRADE)
    if pm_g:
        e.append(f"PM2.5 {snap['pm25']}({pm_g})")
    pm10_g = derived.grade(snap.get("pm10"), boundaries.PM10_GRADE)
    if pm10_g:
        e.append(f"PM10 {snap['pm10']}({pm10_g})")
    if snap.get("wav") is not None:
        e.append(f"파고 {_fmt(snap['wav'], 'm', 1)}")
    if e:
        L.append("  " + " · ".join(e))
    if snap.get("stale"):
        L.append(f"  {Y}⚠ 실황이 오래됐습니다 — run.py nowcast 를 다시 실행하세요{END}")

    # 활동별 적합도 (지금 → +3h 시간축)
    L.append("")
    L.append(f"{BOLD}── 활동별 적합도  (지금 · +1h · +2h · +3h) ────────────{END}")
    hour_results = _hour_results(snap)
    order = sorted(boundaries.ACTIVITIES,
                   key=lambda a: -(results[a]["score"] or 0))
    for act in order:
        r = results[act]
        s = r["score"]
        tag = f"{CYAN}[ML]{END}" if act in ml_used else "    "
        num = f"{_color(s)}{s:>3}{END}" if s is not None else f"{DIM}  ─{END}"
        tl = _timeline_text(act, s, hour_results)
        L.append(f"  {act:　<5s} {_bar(s)} {num}점{tl} {tag} {scoring.phrase(act, r)}")

    # 의상·준비물
    L.append("")
    L.append(f"{BOLD}── 오늘의 의상·준비물 ─────────────────────────────────{END}")
    cloth = derived.clothing_for(snap.get("feel"))
    if cloth:
        L.append(f"  👕 {cloth}")
    top2 = [a for a in order if results[a]["score"] and not results[a]["veto"]][:2]
    for act in top2:
        gear = boundaries.activity_gear(act, snap.get("feel"), snap.get("tmp"))
        if gear:
            L.append(f"  · {act}: {gear}")
    if snap.get("uv") is not None and snap["uv"] >= 6:
        L.append(f"  ☀ 자외선 {uv_g} — 선크림·모자 필수" +
                 (", 한낮(11~15시) 야외 자제" if snap["uv"] >= 8 else ""))
    if pm_g in ("나쁨", "매우나쁨"):
        L.append(f"  😷 초미세먼지 {pm_g} — 마스크 착용, 격한 야외운동 자제")


    # 활동별 최고 지역
    if all_results:
        L.append("")
        L.append(f"{BOLD}── 지금 활동별 최고의 읍면 ────────────────────────────{END}")
        for act in boundaries.ACTIVITIES:
            if act == "쇼핑":
                continue
            ranked = sorted(
                ((rid, res[act]["score"]) for rid, res in all_results.items()
                 if res[act]["score"] is not None and not res[act]["veto"]),
                key=lambda t: -t[1])
            if not ranked:
                continue
            top = [f"{all_snaps[rid]['name']} {_color(s)}{s}{END}"
                   for rid, s in ranked[:3]]
            L.append(f"  {act:　<5s} {'  '.join(top)}")

    if snap.get("missing"):
        L.append("")
        L.append(f"{DIM}결측 데이터: {', '.join(snap['missing'])} — 해당 변수는 제외하고 계산{END}")
    return "\n".join(L)
