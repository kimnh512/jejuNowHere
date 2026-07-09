# 제주나우히어 — 수집 파이프라인 v3

제주 읍면 14곳 기준으로 3개 소스를 주기 수집해 PostgreSQL에 적재합니다.

| 소스 | 테이블 | 내용 | 주기 |
|---|---|---|---|
| 기상청 단기예보 (getVilageFcst) | `village_forecast` | 기온·습도·풍속·강수확률·강수량·파고 등, 오늘~+4일 | 일 8회 |
| 기상청 초단기실황 (getUltraSrtNcst) | `ultra_nowcast` | "지금" 날씨 | 매시 |
| 기상청 초단기예보 (getUltraSrtFcst) | `ultra_forecast` | 향후 6시간 (낙뢰 포함) | 매시 |
| 생활기상지수 자외선 (getUVIdxV2) | `uv_index` | 오늘~글피 자외선지수 | 일 2회 (06, 18시) |
| 제주보건환경연구원 대기환경 | `jeju_air` | PM10·PM2.5 (측정소 12곳) | 매시 |

## API 키 준비

1. **data.go.kr** 키 1개로 2개 서비스 활용신청:
   - 기상청_단기예보 ((구)동네예보) 조회서비스
   - 기상청_생활기상지수 조회서비스(3.0)
2. **제주보건환경연구원**: air.jeju.go.kr > 자료실 > Open API 가이드의 hwp 문서
   (OpenAPI활용가이드(대기환경정보)_v1.2) 안내에 따라 인증키 발급 (문의 064-710-7543).

## 설치

```bash
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt

cp .env.example .env          # 키·DB 접속정보 입력
createdb jejunowhere
psql jejunowhere < schema.sql
python seed_locations.py      # 읍면 14곳: 격자 변환 + 측정소/지점코드 매핑
mkdir -p logs
```

## 실행

```bash
python run.py village | nowcast | ultra | uv | jeju_air | all
```

이력 확인: `SELECT * FROM collect_log ORDER BY id DESC LIMIT 10;`
스케줄 등록: `crontab.txt` 내용을 `crontab -e`에 추가.

## 추천 엔진 (nowhere.py)

수집된 데이터로 현재 위치의 활동별 적합도(0~100)와 추천 문구를 터미널에 표시합니다.

```bash
python nowhere.py                  # 위치 자동 인식, 10분마다 갱신 (q 종료, r 평가)
python nowhere.py --once           # 1회 출력
python nowhere.py --region 애월읍  # 지역 직접 지정
python nowhere.py --lat 33.46 --lon 126.33   # 좌표 직접 입력
python nowhere.py rate             # 추천 평가 남기기 (ML 학습 데이터 수집)
python nowhere.py train            # 평가 30건부터 활동별 ML 모델 학습
```

- 위치: Windows 위치서비스 → IP 추정 → 수동 선택 3단계 폴백, 최근접 읍면 매핑
- 시간축: 활동별 점수를 **지금 · +1h · +2h · +3h**로 표시. 각 셀은 "그 시각에
  활동을 시작하면"의 적합도 (강수 veto는 시작~1시간, 강수확률은 시작 후 3시간 창)
- 점수: Veto(낙뢰·강수·미세먼지·강풍) → 사다리꼴 소프트 점수 → 가중합.
  경계값·가중치는 `engine/boundaries.py` (튜닝 대상).
- 알고리즘 시각화 (matplotlib): `python docs/make_figures.py` →
  `docs/fig1_trapezoids.png`(사다리꼴 소속함수), `fig2_weights.png`(가중치 히트맵),
  `fig3_logistic.png`(로지스틱 회귀 — 피드백 30건부터 실데이터로 그림).
  인터랙티브 버전은 `docs/boundaries_viz.html`.
- ML: 피드백이 쌓이면 로지스틱 회귀 학습 → 규칙 점수와 블렌딩 (`engine/ml.py`)

### 장소 추천 (places.py) — 카카오 로컬 API

활동 점수를 바탕으로 **실제 장소 5곳**을 카카오 로컬 API로 찾아 추천합니다.
지도 표시는 추후 플러터/안드로이드 앱에서 카카오맵 SDK로 처리할 예정이라
여기서는 데이터만 만듭니다.

```bash
python places.py                  # 터미널 5선 출력
python places.py --json           # 앱 연동용 JSON (위치+날씨+점수+장소 5곳)
```

준비: developers.kakao.com에서 앱 생성 → `.env`에 `KAKAO_REST_KEY` 입력.

### REST API 서버 (api.py) — 플러터/안드로이드 연동

```bash
pip install fastapi uvicorn
uvicorn api:app --host 0.0.0.0 --port 8000      # 개발 중엔 --reload 추가
```

| 엔드포인트 | 설명 |
|---|---|
| `GET /health` | 서버·DB·소스별 마지막 수집 시각 |
| `GET /regions` | 읍면 14곳 목록 (지역 선택 UI용) |
| `GET /scores?lat=..&lon=..` | 활동별 점수·문구·지금/+1h/+2h/+3h 타임라인·활동별 최고 읍면 |
| `GET /recommend?lat=..&lon=..` | 가면 좋을 곳 5선 (카카오 장소, 좌표 포함) |

앱은 기기 GPS의 lat/lon을 쿼리로 넘기면 됩니다 (`region=애월읍`도 가능).
자동 문서: 서버 실행 후 `http://localhost:8000/docs` (Swagger).
스냅샷은 60초 캐시. 같은 PC의 에뮬레이터에서는 `http://10.0.2.2:8000` 사용.
```
engine/
  boundaries.py       # 경계값·가중치·Veto·의상 테이블
  derived.py          # 체감온도, 해안 상대풍향(오프쇼어) 등 파생변수
  scoring.py          # 점수 엔진 (0~100)
  geo.py              # 위치 폴백 + 최근접 읍면
  datasource.py       # DB → 지역별 스냅샷 + 피드백 저장
  ml.py               # 피드백 학습 + 블렌딩
  render.py           # 터미널 렌더링
nowhere.py            # 추천 CLI 진입점
```

## 소스별 반영 사항

**단기예보** (활용가이드 2026.06.23판)
- 발표 +10분 제공 → +15분 수집. ±900 결측 → NULL.
- 강수량 범주 문자열은 원문+하한 수치 이중 저장.
- 연장예보 구간(+3~4일)의 PCP/SNO/WSD 정성코드(1~3)는 `*_code` 컬럼 분리.

**자외선** (생활기상지수 3.0 가이드)
- `areaNo`(제주 5011000000 / 서귀포 5013000000) + `time`(YYYYMMDDHH)으로 호출.
- 응답은 오늘/내일/모레/글피 **일 단위** 지수. 오늘값은 06시 발표에만,
  글피값은 18시 발표에만 옴 → 빈 값은 정상 처리(skip).
- 지수 해석: 0-2 낮음 / 3-5 보통 / 6-7 높음 / 8-1