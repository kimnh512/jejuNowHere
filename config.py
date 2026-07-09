"""제주나우히어 파이프라인 설정.

소스: 기상청 단기예보 + 생활기상지수(자외선) + 제주보건환경연구원 대기환경.
API 키는 .env 파일에 넣으세요 (.env.example 참고).
"""
import os

from dotenv import load_dotenv

load_dotenv()

DATA_GO_KR_KEY = os.getenv("DATA_GO_KR_KEY", "")   # 공공데이터포털 인증키 (기상청 2종 공용)
JEJU_AIR_KEY = os.getenv("JEJU_AIR_KEY", "")       # 제주보건환경연구원 발급 인증키
DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://localhost:5432/jejunowhere")

# ── 기상청 단기예보 조회서비스(2.0) ─────────────────────
KMA_BASE = "http://apis.data.go.kr/1360000/VilageFcstInfoService_2.0"
NOWCAST_URL = f"{KMA_BASE}/getUltraSrtNcst"   # 초단기실황 (매시 정시, +10분 후 제공)
ULTRA_URL = f"{KMA_BASE}/getUltraSrtFcst"     # 초단기예보 (매시 30분 발표, 45분 이후 호출)
VILLAGE_URL = f"{KMA_BASE}/getVilageFcst"     # 단기예보 (일 8회 발표)

# ── 기상청 생활기상지수 — 자외선 (활용가이드 3.0판) ──────
UV_URL = "https://apis.data.go.kr/1360000/LivingWthrIdxServiceV5/getUVIdxV5"
UV_BASE_HOURS = [6, 18]                       # 발표: 일 2회
AREA_NO = {                                   # 지점코드 (시 단위; 자외선은 섬 안 편차가 작음)
    "제주시": "5011000000",
    "서귀포시": "5013000000",
}

# ── 제주보건환경연구원 대기환경정보 ─────────────────────
# getJejuAirList: 인증키 불필요, date=YYYYMMDD 파라미터로 당일 시간별 자료 제공.
# 응답 XML: openapi > body > data > list (SITE, DT10, PM10, PM25, O3, ...)
JEJU_AIR_URL = os.getenv(
    "JEJU_AIR_URL",
    "https://air.jeju.go.kr/rest/JejuAirService/getJejuAirList/",
)
# SITE 코드 -> 측정소명 (fix.htm 조회 화면으로 전수 확인, 2026-07)
JEJU_AIR_SITES = {
    "711": "이도동", "712": "연동", "713": "한림읍", "714": "조천읍",
    "715": "화북동", "716": "애월", "721": "동홍동", "722": "성산",
    "723": "대정", "724": "남원", "725": "강정동", "801": "노형동",
}
JEJU_AIR_STATIONS = list(JEJU_AIR_SITES.values())

# ── 제주 읍면 지역 정의 ─────────────────────────────────
# lat/lon은 읍면 중심 근사값 (seed_locations.py가 nx/ny로 변환).
# air는 최근접 대기측정소, 추자면은 측정소가 없어 이도동으로 대체.
REGIONS = [
    # 제주시
    {"name": "제주시내",   "city": "제주시",   "lat": 33.499, "lon": 126.531, "air": "이도동"},
    {"name": "애월읍",     "city": "제주시",   "lat": 33.463, "lon": 126.331, "air": "애월"},
    {"name": "한림읍",     "city": "제주시",   "lat": 33.410, "lon": 126.269, "air": "한림읍"},
    {"name": "한경면",     "city": "제주시",   "lat": 33.345, "lon": 126.175, "air": "한림읍"},
    {"name": "조천읍",     "city": "제주시",   "lat": 33.532, "lon": 126.633, "air": "조천읍"},
    {"name": "구좌읍",     "city": "제주시",   "lat": 33.523, "lon": 126.852, "air": "성산"},
    {"name": "우도면",     "city": "제주시",   "lat": 33.502, "lon": 126.951, "air": "성산"},
    {"name": "추자면",     "city": "제주시",   "lat": 33.952, "lon": 126.300, "air": "이도동"},
    # 서귀포시
    {"name": "서귀포시내", "city": "서귀포시", "lat": 33.253, "lon": 126.560, "air": "동홍동"},
    {"name": "대정읍",     "city": "서귀포시", "lat": 33.223, "lon": 126.251, "air": "대정"},
    {"name": "안덕면",     "city": "서귀포시", "lat": 33.253, "lon": 126.350, "air": "대정"},
    {"name": "남원읍",     "city": "서귀포시", "lat": 33.280, "lon": 126.718, "air": "남원"},
    {"name": "표선면",     "city": "서귀포시", "lat": 33.326, "lon": 126.833, "air": "남원"},
    {"name": "성산읍",     "city": "서귀포시", "lat": 33.437, "lon": 126.913, "air": "성산"},
]

# 예보 보관 지평: 실시간 서비스 방향에 따라 +6시간 이내 예보만 저장·사용
FORECAST_HORIZON_HOURS = 6

# HTTP 설정
RETRIES = 3
TIMEOUT = 10  # seconds
