"""ML 레이어: 피드백 기반 로지스틱 회귀 + 규칙 점수 블렌딩.

왜 이렇게 하나:
  - 지금은 정답 라벨이 없어 규칙 기반이 유일한 선택지.
  - 이 모듈이 피드백(좋았어요/별로)을 라벨로 수집 → 활동별로 30건 이상
    쌓이면 자동 학습 → 최종점수 = (1-α)·규칙 + α·ML예측.
  - α = min(0.5, n/200): 데이터가 쌓일수록 ML 비중이 커지되 절반을 넘지 않음
    (규칙이 안전망 역할). 수천 건이 되면 LightGBM 랭킹으로 교체 권장.
외부 라이브러리 없이 동작합니다 (경사하강 직접 구현).
"""
import json
import math
import os
from collections import defaultdict

FEATURES = ["feel", "reh", "wsd", "pop3", "uv", "pm25", "pm10", "wav"]
MIN_SAMPLES = 30
PARAMS_PATH = os.path.join(os.path.dirname(__file__), "..", "ml_params.json")


def extract_features(snapshot: dict) -> dict:
    return {f: snapshot.get(f) for f in FEATURES}


def _standardize(rows: list[list], mu=None, sigma=None):
    n, k = len(rows), len(FEATURES)
    if mu is None:
        mu = [sum(r[j] for r in rows if r[j] is not None) /
              max(1, sum(1 for r in rows if r[j] is not None)) for j in range(k)]
        sigma = []
        for j in range(k):
            vals = [r[j] for r in rows if r[j] is not None]
            m = mu[j]
            var = sum((v - m) ** 2 for v in vals) / max(1, len(vals))
            sigma.append(math.sqrt(var) or 1.0)
    out = []
    for r in rows:
        out.append([0.0 if r[j] is None else (r[j] - mu[j]) / sigma[j]
                    for j in range(k)])
    return out, mu, sigma


def _sigmoid(z: float) -> float:
    return 1 / (1 + math.exp(-max(-30, min(30, z))))


def train_one(X: list[list], y: list[int], epochs=400, lr=0.1, l2=0.01):
    k = len(FEATURES)
    w, b = [0.0] * k, 0.0
    n = len(X)
    for _ in range(epochs):
        gw, gb = [0.0] * k, 0.0
        for xi, yi in zip(X, y):
            p = _sigmoid(sum(wj * xj for wj, xj in zip(w, xi)) + b)
            err = p - yi
            for j in range(k):
                gw[j] += err * xi[j]
            gb += err
        for j in range(k):
            w[j] -= lr * (gw[j] / n + l2 * w[j])
        b -= lr * gb / n
    return w, b


def train_all(feedback_rows: list[dict]) -> dict:
    """reco_feedback 행들로 활동별 모델 학습 → ml_params.json 저장."""
    by_act = defaultdict(list)
    for row in feedback_rows:
        feats = json.loads(row["features"])
        by_act[row["activity"]].append(
            ([feats.get(f) for f in FEATURES], int(row["label"])))

    params, report = {}, {}
    for act, samples in by_act.items():
        n = len(samples)
        labels = {s[1] for s in samples}
        if n < MIN_SAMPLES or len(labels) < 2:
            report[act] = f"보류 (n={n}, 최소 {MIN_SAMPLES}건 + 양/음 라벨 필요)"
            continue
        rows = [s[0] for s in samples]
        y = [s[1] for s in samples]
        X, mu, sigma = _standardize(rows)
        w, b = train_one(X, y)
        correct = sum(1 for xi, yi in zip(X, y)
                      if (_sigmoid(sum(a * c for a, c in zip(w, xi)) + b) >= 0.5) == bool(yi))
        params[act] = {"w": w, "b": b, "mu": mu, "sigma": sigma, "n": n}
        report[act] = f"학습 완료 (n={n}, 학습정확도 {correct / n:.0%})"

    if params:
        existing = load_params()
        existing.update(params)
        with open(PARAMS_PATH, "w", encoding="utf-8") as f:
            json.dump(existing, f, ensure_ascii=False, indent=1)
    return report


def load_params() -> dict:
    try:
        with open(PARAMS_PATH, encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {}


def blend(activity: str, rule_score, snapshot: dict, params: dict):
    """(최종점수, ml_사용여부). 모델 없으면 규칙 점수 그대로."""
    m = params.get(activity)
    if not m or rule_score is None or rule_score == 0:
        return rule_score, False
    raw = [snapshot.get(f) for f in FEATURES]
    X, _, _ = _standardize([raw], m["mu"], m["sigma"])
    p = _sigmoid(sum(w * x for w, x in zip(m["w"], X[0])) + m["b"])
    alpha = min(0.5, m["n"] / 200)
    return round((1 - alpha) * rule_score + alpha * p * 100), True
