"""알고리즘 시각화 (matplotlib) — 규칙 기반 경계값 + 로지스틱 회귀.

사용법 (프로젝트 루트에서):
    python docs/make_figures.py

생성 파일 (docs/):
    fig1_trapezoids.png   활동 × 변수 사다리꼴 소속함수 곡선
    fig2_weights.png      활동 × 변수 가중치 히트맵
    fig3_logistic.png     로지스틱 회귀: 시그모이드 / 결정경계 / 블렌딩 / 가중치

로지스틱 회귀 그림은 reco_feedback에 실제 평가가 30건 이상 쌓이면 실데이터로,
그 전에는 합성 데모 데이터로 그립니다.
"""
import os
import sys

import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib import font_manager

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from engine import boundaries, ml, scoring  # noqa: E402

OUT = os.path.dirname(os.path.abspath(__file__))

# ── 한글 폰트 (Windows: 맑은 고딕 / Linux: Nanum·Noto CJK) ────────
def setup_font():
    want = ["Malgun Gothic", "NanumGothic", "Noto Sans CJK KR", "Noto Sans CJK JP"]
    have = {f.name for f in font_manager.fontManager.ttflist}
    pick = next((n for n in want if n in have), None)
    if pick is None:  # 이름이 다른 CJK 폰트라도 잡기 (Noto CJK는 한글 전체 포함)
        pick = next((n for n in sorted(have) if "CJK" in n or "Nanum" in n), None)
    if pick:
        plt.rcParams["font.family"] = pick
    plt.rcParams["axes.unicode_minus"] = False

setup_font()

UNITS = {"feel": "℃", "reh": "%", "wsd": "m/s", "wsd_alt": "m/s",
         "pop3": "%", "uv": "지수", "pm25": "㎍/㎥", "pm10": "㎍/㎥", "wav": "m"}
LBL = dict(scoring.VAR_LABEL)
BLUE, ORANGE, GREEN, RED = "#3873c4", "#e8853d", "#3d9e58", "#c0392b"


def trap_y(x, a, b, c, d):
    return np.interp(x, [a - 1e-9, a, b, c, d, d + 1e-9], [0, 0, 1, 1, 0, 0])


# ── 그림 1: 사다리꼴 소속함수 그리드 ─────────────────────────────
def fig_trapezoids():
    acts = [a for a in boundaries.ACTIVITIES if a in boundaries.TRAPEZOIDS]
    ncol = max(len(spec) for spec in boundaries.TRAPEZOIDS.values())
    fig, axes = plt.subplots(len(acts), ncol, figsize=(2.6 * ncol, 2.1 * len(acts)))
    fig.suptitle("규칙 기반 점수화 — 활동 × 변수 사다리꼴 소속함수 (0~1)\n"
                 "구간: a→b 상승 · b~c 만점 · c→d 하강  |  괄호 안은 가중치",
                 fontsize=13, y=1.00)
    for i, act in enumerate(acts):
        spec = sorted(boundaries.TRAPEZOIDS[act].items(), key=lambda kv: -kv[1][0])
        for j in range(ncol):
            ax = axes[i][j]
            if j >= len(spec):
                ax.axis("off")
                continue
            var, (w, bound) = spec[j]
            if isinstance(bound, dict):    # 범주형 → 막대
                keys = list(bound)
                names = [{1: "맑음", 3: "구름", 4: "흐림",
                          "offshore": "오프쇼어", "cross": "크로스",
                          "onshore": "온쇼어"}.get(k, str(k)) for k in keys]
                ax.bar(names, [bound[k] for k in keys], color=ORANGE, width=0.5)
                ax.set_ylim(0, 1.15)
            else:
                a, b, c, d = bound
                span = max(d - a, 1e-9)
                x = np.linspace(a - span * 0.2, d + span * 0.2, 200)
                ax.plot(x, trap_y(x, a, b, c, d), color=BLUE, lw=2)
                ax.fill_between(x, trap_y(x, a, b, c, d), color=BLUE, alpha=0.12)
                ax.set_ylim(-0.05, 1.15)
                for v in sorted({a, b, c, d}):
                    ax.axvline(v, color="#aaa", lw=0.5, ls=":")
                ax.set_xlabel(UNITS.get(var, ""), fontsize=7, labelpad=1)
            ax.set_title(f"{LBL.get(var, var)} ({w:.2f})", fontsize=9)
            ax.tick_params(labelsize=7)
            if j == 0:
                ax.set_ylabel(act, fontsize=11, fontweight="bold")
    fig.tight_layout(rect=[0, 0, 1, 0.95])
    fig.savefig(os.path.join(OUT, "fig1_trapezoids.png"), dpi=140,
                bbox_inches="tight")
    plt.close(fig)


# ── 그림 2: 가중치 히트맵 ───────────────────────────────────────
def fig_weights():
    acts = [a for a in boundaries.ACTIVITIES if a in boundaries.TRAPEZOIDS]
    all_vars = sorted({v for s in boundaries.TRAPEZOIDS.values() for v in s},
                      key=lambda v: -sum(boundaries.TRAPEZOIDS[a].get(v, (0,))[0]
                                         for a in acts))
    M = np.array([[boundaries.TRAPEZOIDS[a].get(v, (0, None))[0]
                   for v in all_vars] for a in acts])
    fig, ax = plt.subplots(figsize=(9, 4.4))
    im = ax.imshow(M, cmap="Blues", vmin=0, vmax=0.4, aspect="auto")
    ax.set_xticks(range(len(all_vars)),
                  [LBL.get(v, v) for v in all_vars], fontsize=10)
    ax.set_yticks(range(len(acts)), acts, fontsize=11)
    for i in range(len(acts)):
        for j in range(len(all_vars)):
            if M[i, j] > 0:
                ax.text(j, i, f"{M[i, j]:.2f}", ha="center", va="center",
                        fontsize=9, color="white" if M[i, j] > 0.22 else "#1a355c")
    ax.set_title("활동별 변수 가중치 (행 합계 = 1.00) · 쇼핑은 역방향 로직으로 별도",
                 fontsize=12, pad=12)
    fig.colorbar(im, ax=ax, shrink=0.85, label="가중치")
    fig.tight_layout()
    fig.savefig(os.path.join(OUT, "fig2_weights.png"), dpi=140,
                bbox_inches="tight")
    plt.close(fig)


# ── 그림 3: 로지스틱 회귀 ───────────────────────────────────────
def load_feedback_or_demo():
    """실제 피드백이 충분하면 사용, 아니면 합성 데모 데이터 생성."""
    try:
        from engine import datasource
        rows = datasource.fetch_feedback()
        run = [r for r in rows if r["activity"] == "러닝"]
        if len(run) >= ml.MIN_SAMPLES:
            import json
            X = [[json.loads(r["features"]).get(f) for f in ml.FEATURES]
                 for r in run]
            y = [int(r["label"]) for r in run]
            return X, y, f"실데이터 (러닝 평가 {len(run)}건)"
    except Exception:
        pass
    # 여름철 러닝 데모: 체감온도가 높을수록·강수확률이 높을수록 "별로" (단조 관계)
    rng = np.random.default_rng(7)
    n = 140
    feel = rng.uniform(12, 36, n)
    pop = rng.uniform(0, 90, n)
    logit = 4.2 - 0.22 * (feel - 12) - 0.06 * pop + rng.normal(0, 1.0, n)
    y = (1 / (1 + np.exp(-logit)) > 0.5).astype(int)
    X = [[f, 55.0, 2.5, p, 4.0, 12.0, 28.0, None]  # ml.FEATURES 순서
         for f, p in zip(feel, pop)]
    return X, [int(v) for v in y], "합성 데모 데이터 · 여름철 러닝 (피드백 30건 전까지)"


def fig_logistic():
    X, y, src = load_feedback_or_demo()
    Xs, mu, sigma = ml._standardize(X)
    w, b = ml.train_one(Xs, y)

    def predict(feel, pop):
        raw = [feel, 55.0, 2.5, pop, 4.0, 12.0, 28.0, None]
        xs, _, _ = ml._standardize([raw], mu, sigma)
        return ml._sigmoid(sum(wi * xi for wi, xi in zip(w, xs[0])) + b)

    fig, axes = plt.subplots(2, 2, figsize=(11.5, 8.6))
    fig.suptitle(f"ML 레이어 — 피드백 기반 로지스틱 회귀 · {src}",
                 fontsize=14, y=0.99)

    # (a) 시그모이드
    ax = axes[0][0]
    z = np.linspace(-6, 6, 200)
    ax.plot(z, 1 / (1 + np.exp(-z)), color=BLUE, lw=2.5)
    ax.axhline(0.5, color="#999", ls="--", lw=1)
    ax.axvline(0, color="#999", ls="--", lw=1)
    ax.set_title("(a) 시그모이드: z = w·x + b → 만족 확률", fontsize=11)
    ax.set_xlabel("z (가중합)")
    ax.set_ylabel("P(좋았어요)")
    ax.annotate("0.5 경계", xy=(2.5, 0.52), fontsize=9, color="#666")

    # (b) 결정경계 (체감온도 × 강수확률)
    ax = axes[0][1]
    feel_all = [r[0] for r in X]
    gf = np.linspace(min(feel_all), max(feel_all), 90)
    gp = np.linspace(0, 90, 90)
    P = np.array([[predict(f, p) for f in gf] for p in gp])
    cs = ax.contourf(gf, gp, P, levels=20, cmap="RdYlGn")
    ax.contour(gf, gp, P, levels=[0.5], colors="k", linewidths=1.5)
    feel_v = np.array([r[0] for r in X], dtype=float)
    pop_v = np.array([r[3] for r in X], dtype=float)
    yv = np.array(y)
    ax.scatter(feel_v[yv == 1], pop_v[yv == 1], s=16, color=GREEN,
               edgecolor="k", linewidth=0.3, label="좋았어요 (1)")
    ax.scatter(feel_v[yv == 0], pop_v[yv == 0], s=16, color=RED,
               edgecolor="k", linewidth=0.3, label="별로였어요 (0)")
    ax.set_title("(b) 결정경계 — 러닝: 체감온도 × 강수확률", fontsize=11)
    ax.set_xlabel("체감온도 (℃)")
    ax.set_ylabel("3시간 내 최대 강수확률 (%)")
    ax.legend(fontsize=8, loc="upper right")
    fig.colorbar(cs, ax=ax, shrink=0.9, label="P(만족)")

    # (c) 블렌딩: 최종점수 = (1-α)·규칙 + α·ML, α = min(0.5, n/200)
    ax = axes[1][0]
    n = np.arange(0, 401)
    alpha = np.minimum(0.5, n / 200)
    ax.plot(n, 1 - alpha, color=BLUE, lw=2.5, label="규칙 기반 비중 (1-α)")
    ax.plot(n, alpha, color=ORANGE, lw=2.5, label="ML 비중 (α)")
    ax.axvline(ml.MIN_SAMPLES, color="#999", ls="--", lw=1)
    ax.text(ml.MIN_SAMPLES + 5, 0.9, f"학습 시작\n(n={ml.MIN_SAMPLES})",
            fontsize=9, color="#666")
    ax.axvline(200, color="#999", ls=":", lw=1)
    ax.text(205, 0.56, "α 상한 0.5\n(규칙 = 안전망)", fontsize=9, color="#666")
    ax.set_ylim(0, 1.05)
    ax.set_title("(c) 점수 블렌딩 — 피드백이 쌓일수록 ML 비중 증가", fontsize=11)
    ax.set_xlabel("활동별 누적 피드백 수 (n)")
    ax.set_ylabel("최종 점수 기여 비중")
    ax.legend(fontsize=9)

    # (d) 학습된 가중치
    ax = axes[1][1]
    names = [LBL.get(f, f) for f in ml.FEATURES]
    colors = [GREEN if wi >= 0 else RED for wi in w]
    ax.barh(names, w, color=colors)
    ax.axvline(0, color="#333", lw=1)
    ax.set_title("(d) 학습된 가중치 w (표준화 입력 기준)\n"
                 "양수 = 값이 클수록 만족↑ · 음수 = 클수록 만족↓", fontsize=11)
    ax.set_xlabel("가중치")
    ax.invert_yaxis()

    fig.tight_layout(rect=[0, 0, 1, 0.96])
    fig.savefig(os.path.join(OUT, "fig3_logistic.png"), dpi=140,
                bbox_inches="tight")
    plt.close(fig)


if __name__ == "__main__":
    fig_trapezoids()
