"""GPT 자연어 생성(NLG) — 추천 문장·복장·장소 소개 한마디.

OpenAI API로 앱 화면에 띄울 3가지 문구를 한 번의 호출로 생성합니다.
  1. recommendation_message: "오늘은 서우봉에서 러닝하는 것을 추천드립니다. 20시 이후에는 ..."
  2. outfit: ["볼캡", "바람막이", "반바지", "러닝화"]
  3. place_intro: 장소를 소개하는 한마디

호출 실패 시 규칙 기반 폴백으로 항상 응답을 보장합니다 (앱이 죽지 않도록).
.env에 OPENAI_API_KEY 필요 (.env.example 참고).
"""
import hashlib
import json
import time

import config

try:
    from openai import OpenAI
except ImportError:  # openai 미설치 환경에서도 파이프라인 나머지는 동작
    OpenAI = None

_client = None
_cache: dict = {}          # 같은 조건 반복 호출 시 LLM 재호출 방지 (비용·지연 절감)
CACHE_TTL_SEC = 900        # 15분 — 날씨 스냅샷 갱신 주기와 비슷하게


def _get_client():
    global _client
    if _client is None:
        if OpenAI is None or not config.OPENAI_API_KEY:
            return None
        # timeout·재시도 제한 — LLM 장애 시 API 응답이 오래 매달리지 않도록
        _client = OpenAI(api_key=config.OPENAI_API_KEY, timeout=10, max_retries=1)
    return _client


SYSTEM_PROMPT = """당신은 제주도 야외활동 추천 앱 '제주나우히어'의 문구 작성 AI입니다.
입력으로 활동 종류, 추천 장소, 현재 날씨, 적합도 점수(경계값 기반), 시간대별 예보가 주어집니다.
아래 3가지를 한국어로 생성하세요.

1. recommendation_message: 오늘의 추천 문장.
   - "오늘은 {장소}에서 {활동}하는 것을 추천드립니다."로 시작
   - hourly 예보에서 습도/기온/강수확률이 좋아지는 시간대가 있으면
     "N시 이후에는 습도가 낮아져 더욱 쾌적해질 예정이에요!"처럼 구체적 팁 1문장 추가
   - 총 2문장, 친근한 존댓말("~예요/~드립니다")
2. outfit: 기온·습도·바람·자외선에 맞는 복장 3~5개. 짧은 명사만.
   (예: 볼캡, 바람막이, 반바지, 러닝화, 얇은 긴팔, 장갑)
   - 기온 기준: 23°C 이상 반팔·반바지 / 15~22°C 얇은 긴팔·바람막이 /
     8~14°C 긴바지·바람막이 / 8°C 미만 방한 레이어
   - 자외선 지수 높으면 볼캡·선글라스, 강수확률 높으면 방수 자켓 포함
3. place_intro: 장소 특징을 살린 매력적인 소개 한마디. 1문장.
   (예: "서우봉은 함덕 바다를 옆에 끼고 달리는, 노을이 아름다운 오름 둘레길이에요.")

과장하거나 입력에 없는 사실을 지어내지 마세요.
적합도가 낮으면(50 미만) 무리하지 않는 톤으로, veto(경보)면 실내 대안을 권하세요."""

RESPONSE_SCHEMA = {
    "type": "json_schema",
    "json_schema": {
        "name": "activity_recommendation",
        "strict": True,
        "schema": {
            "type": "object",
            "properties": {
                "recommendation_message": {"type": "string"},
                "outfit": {"type": "array", "items": {"type": "string"}},
                "place_intro": {"type": "string"},
            },
            "required": ["recommendation_message", "outfit", "place_intro"],
            "additionalProperties": False,
        },
    },
}


def generate(payload: dict) -> dict:
    """3종 문구 생성. payload는 api.py의 /nlg가 조립한 dict.

    반환: {"recommendation_message", "outfit", "place_intro", "llm": bool}
    """
    key = hashlib.md5(
        json.dumps(payload, ensure_ascii=False, sort_keys=True).encode()
    ).hexdigest()
    hit = _cache.get(key)
    if hit and time.time() - hit[0] < CACHE_TTL_SEC:
        return dict(hit[1])

    client = _get_client()
    if client is not None:
        try:
            completion = client.chat.completions.create(
                model=config.OPENAI_MODEL,
                temperature=0.7,
                response_format=RESPONSE_SCHEMA,
                messages=[
                    {"role": "system", "content": SYSTEM_PROMPT},
                    {"role": "user", "content": json.dumps(payload, ensure_ascii=False)},
                ],
            )
            data = json.loads(completion.choices[0].message.content)
            data["llm"] = True
            _cache[key] = (time.time(), dict(data))
            return data
        except Exception:
            pass  # 폴백으로
    out = _fallback(payload)
    _cache[key] = (time.time(), dict(out))
    return out


def _fallback(payload: dict) -> dict:
    """LLM 불가 시 규칙 기반 문구 (키 없음/장애/타임아웃)."""
    place = payload.get("place", {}).get("name", "제주")
    activity = payload.get("activity", "러닝")
    score = payload.get("suitability", {}).get("score")
    t = payload.get("weather", {}).get("temp")

    outfit = ["운동화"]
    if t is not None:
        if t >= 23:
            outfit = ["볼캡", "반팔 티셔츠", "반바지", "러닝화"]
        elif t >= 15:
            outfit = ["볼캡", "바람막이", "반바지", "러닝화"]
        elif t >= 8:
            outfit = ["바람막이", "긴바지", "러닝화"]
        else:
            outfit = ["방한 모자", "기모 상의", "긴바지", "장갑", "러닝화"]

    msg = f"오늘은 {place}에서 {activity}하는 것을 추천드립니다."
    if score is not None:
        msg += f" 현재 적합도는 {score}점이에요!"
    return {
        "recommendation_message": msg,
        "outfit": outfit,
        "place_intro": payload.get("place", {}).get("features")
                       or f"{place}은(는) 제주에서 {activity}하기 좋은 곳이에요.",
        "llm": False,
    }
