"""가상 날씨 시나리오 10개 × 7개 활동 점수 테스트 & 시각화.

사용법 (프로젝트 루트에서):
    python docs/test_scenarios.py

생성 파일:
    docs/fig4_scenarios.png   히트맵 + 막대 차트 + Veto 표
"""
import os
import sys

import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
from matplotlib import font_manager

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from engine import boundaries, scoring  # noqa: E402

OUT = os.path.dirname(os.path.abspath(__file__))

# ── 한글 폰트 ────────────────────────────────────────────────────
def setup_font():
    want = ["Malgun Gothic", "NanumGothic", "Noto Sans CJK KR", "Noto Sans CJK JP"]
    have = {f.name for f in font_manager.fontManager.ttflist}
    pick = next((n for n in want if n in have), None)
    if pick is None:
        pick = next((n for n in sorted(have) if "CJK" in n or "Nanum" in n), None)
    if pick:
        plt.rcParams["font.family"] = pick
    plt.rcParams["axes.unicode_minus"] = False

setup_font()

# ── 가상 시나리오 10개 ────────────────────────────────────────────
# 각 스냅샷은 engine/scoring.py 의 score_activity() 가 기대하는 키를 포함.
# feel: 체감온도(℃), reh: 습도(%), wsd: 풍속(m/s), pop3: 3h 최대 강수확률(%),
# uv: 자외선지수, pm25: 초미세먼지(㎍/㎥), pm10: 미세먼지(㎍/㎥),
# wav: 파고(m), sky: 하늘상태(1맑음/3구름많음/4흐림),
# pty_now: 현재강수코드(0없음), pty3: 3h내 강수코드, lgt6: 6h내 낙뢰(0/1),
# offshore: 서핑 해안 상대풍향, rain_now: 현재강수량(mm), region_id/name(더미)
SCENARIOS = [
    {
        "label": "① 봄 맑은날",
        "desc": "기온18℃ · 습도45% · 바람2m/s\n미세먼지 보통 · 파고0.8m",
        "feel": 17.5, "reh": 45, "wsd": 2.0, "pop3": 5,
        "uv": 5, "pm25": 12, "pm10": 28, "wav": 0.8,
        "sky": 1, "pty_now": 0, "pty3": 0, "lgt6": 0,
        "offshore": "offshore", "rain_now": 0,
    },
    {
        "label": "② 여름 폭염",
        "desc": "기온35℃ · 습도80% · 강한햇살\n자외선8 · 체감 42℃",
        "feel": 42.0, "reh": 80, "wsd": 1.0, "pop3": 10,
        "uv": 8, "pm25": 10, "pm10": 22, "wav": 0.5,
        "sky": 1, "pty_now": 0, "pty3": 0, "lgt6": 0,
        "offshore": "onshore", "rain_now": 0,
    },
    {
        "label": "③ 가을 단풍",
        "desc": "기온16℃ · 습도55% · 바람3m/s\n맑음 · 파고1.2m",
        "feel": 15.0, "reh": 55, "wsd": 3.0, "pop3": 0,
        "uv": 4, "pm25": 8, "pm10": 18, "wav": 1.2,
        "sky": 1, "pty_now": 0, "pty3": 0, "lgt6": 0,
        "offshore": "cross", "rain_now": 0,
    },
    {
        "label": "④ 겨울 강풍",
        "desc": "기온5℃ · 체감-2℃ · 바람15m/s\n흐림 · 강풍주의",
        "feel": -2.0, "reh": 60, "wsd": 15.0, "pop3": 20,
        "uv": 2, "pm25": 5, "pm10": 12, "wav": 2.5,
        "sky": 4, "pty_now": 0, "pty3": 0, "lgt6": 0,
        "offshore": "offshore", "rain_now": 0,
    },
    {
        "label": "⑤ 비오는날",
        "desc": "기온20℃ · 비 · 강수확률90%\n강수코드1(비)",
        "feel": 19.0, "reh": 92, "wsd": 4.0, "pop3": 90,
        "uv": 1, "pm25": 7, "pm10": 15, "wav": 1.0,
        "sky": 4, "pty_now": 1, "pty3": 1, "lgt6": 0,
        "offshore": "onshore", "rain_now": 3.0,
    },
    {
        "label": "⑥ 황사 경보",
        "desc": "기온22℃ · PM10=180 · PM2.5=90\n미세먼지 매우나쁨",
        "feel": 21.0, "reh": 50, "wsd": 3.0, "pop3": 5,
        "uv": 5, "pm25": 90, "pm10": 180, "wav": 0.5,
        "sky": 3, "pty_now": 0, "pty3": 0, "lgt6": 0,
        "offshore": "onshore", "rain_now": 0,
    },
    {
        "label": "⑦ 낙뢰 경보",
        "desc": "기온28℃ · 낙뢰예보=1\n소나기 동반",
        "feel": 30.0, "reh": 75, "wsd": 5.0, "pop3": 60,
        "uv": 3, "pm25": 12, "pm10": 25, "wav": 1.5,
        "sky": 4, "pty_now": 2, "pty3": 2, "lgt6": 1,
        "offshore": "cross", "rain_now": 1.0,
    },
    {
        "label": "⑧ 서핑 최적",
        "desc": "기온26℃ · 파고1.5m · 오프쇼어\n바람8m/s · 맑음",
        "feel": 26.0, "reh": 60, "wsd": 8.0, "pop3": 5,
        "uv": 7, "pm25": 10, "pm10": 20, "wav": 1.5,
        "sky": 1, "pty_now": 0, "pty3": 0, "lgt6": 0,
        "offshore": "offshore", "rain_now": 0,
    },
    {
        "label": "⑨ 드론 최적",
        "desc": "기온20℃ · 바람2m/s · 맑음\n미세먼지 좋음 · 강수확률0%",
        "feel": 19.5, "reh": 40, "wsd": 2.0, "pop3": 0,
        "uv": 4, "pm25": 5, "pm10": 12, "wav": 0.4,
        "sky": 1, "pty_now": 0, "pty3": 0, "lgt6": 0,
        "offshore": "cross", "rain_now": 0,
    },
    {
        "label": "⑩ 흐린 봄비",
        "desc": "기온15℃ · 구름많음 · 강수확률40%\n바람6m/s · 파고0.6m",
        "feel": 13.0, "reh": 72, "wsd": 6.0, "pop3": 40,
        "uv": 2, "pm25": 18, "pm10": 40, "wav": 0.6,
        "sky": 3, "pty_now": 0, "pty3": 0, "lgt6": 0,
        "offshore": "onshore", "rain_now": 0,
    },
]


def run_scores():
    """모든 시나리오 × 활동 점수 계산."""
    acts = boundaries.ACTIVITIES
    rows = []
    for sc in SCENARIOS:
        res = scoring.score_all(sc)
        row = {}
        for act in acts:
            r = res[act]
            row[act] = {"score": r["score"], "veto": r["veto"]}
        rows.append(row)
    return rows


def display_score(cell: dict) -> float:
    """히트맵용: veto면 -1(별도 표기), None이면 NaN."""
    if cell["veto"]:
        return -1.0
    if cell["score"] is None:
        return float("nan")
    return float(cell["score"])


def fig_scenarios():
    acts = boundaries.ACTIVITIES
    rows = run_scores()

    # ── 점수 행렬 ──────────────────────────────────────────────────
    M = np.array([[display_score(row[a]) for a in acts] for row in rows],
                 dtype=float)  # shape (10, 7)

    labels = [sc["label"] for sc in SCENARIOS]
    descs = [sc["desc"] for sc in SCENARIOS]

    fig = plt.figure(figsize=(18, 14))
    fig.suptitle("제주나우히어 — 가상 날씨 시나리오 10개 × 활동별 적합도 점수 (0~100)",
                 fontsize=15, y=0.99, fontweight="bold")

    # 레이아웃: 왼쪽 히트맵(큰), 오른쪽 상단 막대, 오른쪽 하단 Veto 표
    gs = fig.add_gridspec(2, 2, width_ratios=[1.6, 1], height_ratios=[1.5, 1],
                          hspace=0.45, wspace=0.35)
    ax_heat = fig.add_subplot(gs[:, 0])   # 히트맵 (2행 전체)
    ax_bar = fig.add_subplot(gs[0, 1])    # 시나리오별 막대
    ax_veto = fig.add_subplot(gs[1, 1])   # Veto 요약 표

    # ── 1. 히트맵 ─────────────────────────────────────────────────
    # veto(-1)은 별도 색, 정상값 0~100은 RdYlGn
    masked_veto = np.ma.masked_where(M >= 0, M)   # veto만
    masked_val = np.ma.masked_where(M < 0, M)     # 정상값만

    cmap_main = plt.cm.RdYlGn
    cmap_veto = matplotlib.colors.ListedColormap(["#d0d0d0"])

    im = ax_heat.imshow(masked_val, cmap=cmap_main, vmin=0, vmax=100,
                        aspect="auto", interpolation="nearest")
    ax_heat.imshow(masked_veto, cmap=cmap_veto, vmin=-1, vmax=0,
                   aspect="auto", interpolation="nearest")

    # 셀 텍스트
    for i in range(len(SCENARIOS)):
        for j, act in enumerate(acts):
            cell = rows[i][act]
            if cell["veto"]:
                short_veto = cell["veto"].split("—")[0].strip()[:6]
                ax_heat.text(j, i, f"VETO\n{short_veto}", ha="center", va="center",
                             fontsize=6.5, color="#555", fontweight="bold")
            elif cell["score"] is not None:
                score = cell["score"]
                color = "white" if score < 35 or score > 80 else "#333"
                ax_heat.text(j, i, str(score), ha="center", va="center",
                             fontsize=11, color=color, fontweight="bold")

    ax_heat.set_xticks(range(len(acts)), acts, fontsize=12)
    ax_heat.set_yticks(range(len(SCENARIOS)),
                       [f"{sc['label']}\n{sc['desc']}" for sc in SCENARIOS],
                       fontsize=8.5)
    ax_heat.set_title("활동 × 시나리오 점수 히트맵\n"
                       "초록=좋음 · 빨강=나쁨 · 회색=VETO(절대금지)",
                       fontsize=12, pad=10)
    cbar = fig.colorbar(im, ax=ax_heat, shrink=0.6, pad=0.02)
    cbar.set_label("적합도 점수 (0~100)", fontsize=9)

    veto_patch = mpatches.Patch(color="#d0d0d0", label="VETO (0점, 이유 있음)")
    ax_heat.legend(handles=[veto_patch], loc="lower right", fontsize=8,
                   bbox_to_anchor=(1.0, -0.01))

    # ── 2. 시나리오별 평균 점수 막대 차트 ────────────────────────
    avg_scores = []
    for i, row in enumerate(rows):
        vals = [row[a]["score"] for a in acts
                if row[a]["score"] is not None and not row[a]["veto"]]
        avg_scores.append(round(sum(vals) / len(vals)) if vals else 0)

    colors_bar = [plt.cm.RdYlGn(v / 100) for v in avg_scores]
    bars = ax_bar.barh(range(len(SCENARIOS)), avg_scores, color=colors_bar,
                       edgecolor="#888", linewidth=0.5)
    ax_bar.set_yticks(range(len(SCENARIOS)), [sc["label"] for sc in SCENARIOS],
                      fontsize=9)
    ax_bar.set_xlim(0, 105)
    ax_bar.set_xlabel("활동별 평균 적합도 (VETO 제외)", fontsize=9)
    ax_bar.set_title("시나리오별 평균 점수\n(VETO 걸린 활동 제외)", fontsize=10)
    ax_bar.invert_yaxis()
    ax_bar.axvline(60, color="#3873c4", lw=1, ls="--", alpha=0.6)
    ax_bar.text(61, -0.6, "60점", fontsize=8, color="#3873c4")
    for bar, v in zip(bars, avg_scores):
        ax_bar.text(v + 1, bar.get_y() + bar.get_height() / 2,
                    str(v), va="center", fontsize=9, fontweight="bold")

    # ── 3. Veto 현황 표 ────────────────────────────────────────────
    ax_veto.axis("off")
    col_labels = ["시나리오"] + acts
    table_data = []
    for i, sc in enumerate(SCENARIOS):
        row_data = [sc["label"]]
        for act in acts:
            cell = rows[i][act]
            if cell["veto"]:
                row_data.append("✗")
            elif cell["score"] is not None:
                row_data.append(str(cell["score"]))
            else:
                row_data.append("─")
        table_data.append(row_data)

    tbl = ax_veto.table(
        cellText=table_data,
        colLabels=col_labels,
        cellLoc="center",
        loc="center",
        bbox=[0, 0, 1, 1],
    )
    tbl.auto_set_font_size(False)
    tbl.set_fontsize(8)
    # 헤더 스타일
    for j in range(len(col_labels)):
        tbl[0, j].set_facecolor("#3873c4")
        tbl[0, j].set_text_props(color="white", fontweight="bold")
    # VETO 셀 강조
    for i, row in enumerate(rows, start=1):
        for j, act in enumerate(acts, start=1):
            if row[act]["veto"]:
                tbl[i, j].set_facecolor("#f5b7b1")
                tbl[i, j].set_text_props(color="#c0392b", fontweight="bold")
            elif row[act]["score"] is not None:
                s = row[act]["score"]
                if s >= 70:
                    tbl[i, j].set_facecolor("#d5f5e3")
    ax_veto.set_title("점수 요약표  (✗ = VETO · 초록배경=70점↑)",
                      fontsize=10, pad=6)

    fig.savefig(os.path.join(OUT, "fig4_scenarios.png"), dpi=130,
                bbox_inches="tight")
    plt.close(fig)
    print(f"저장: {os.path.join(OUT, 'fig4_scenarios.png')}")


if __name__ == "__main__":
    fig_scenarios()
    # ── 콘솔 출력 (간단 확인용) ────────────────────────────────────
    acts = boundaries.ACTIVITIES
    rows = run_scores()
    print(f"\n{'시나리오':<18}", "  ".join(f"{a[:4]:>5}" for a in acts))
    print("-" * 65)
    for sc, row in zip(SCENARIOS, rows):
        scores = []
        for act in acts:
            c = row[act]
            scores.append("VETO" if c["veto"] else (str(c["score"]) if c["score"] is not None else "─"))
        print(f"{sc['label']:<18}", "  ".join(f"{s:>5}" for s in scores))
