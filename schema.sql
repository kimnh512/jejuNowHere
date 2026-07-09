-- 제주나우히어 스키마 v3
-- 소스: ① 기상청 단기예보(VilageFcstInfoService_2.0)
--       ② 기상청 생활기상지수 자외선(LivingWthrIdxServiceV2/getUVIdxV2)
--       ③ 제주보건환경연구원 대기환경정보(PM10/PM2.5)
-- v2에서 업그레이드 시: 아래 ALTER + 신규 테이블 2개만 실행해도 됨.
--   ALTER TABLE locations ADD COLUMN air_station TEXT, ADD COLUMN area_no TEXT;

-- ── 지역 마스터 ─────────────────────────────────────────
CREATE TABLE IF NOT EXISTS locations (
    region_id   SERIAL PRIMARY KEY,
    name        TEXT UNIQUE NOT NULL,      -- 읍면명 (예: 애월읍)
    city        TEXT NOT NULL,             -- 제주시 / 서귀포시
    lat         DOUBLE PRECISION,
    lon         DOUBLE PRECISION,
    nx          INT NOT NULL,              -- 기상청 예보지점 X 좌표
    ny          INT NOT NULL,              -- 기상청 예보지점 Y 좌표
    air_station TEXT,                      -- 최근접 제주 대기측정소 (12곳 중)
    area_no     TEXT                       -- 생활기상지수 지점코드 (시 단위)
);

-- ── 1) 초단기실황 (getUltraSrtNcst) — "지금" 날씨 ────────
CREATE TABLE IF NOT EXISTS ultra_nowcast (
    region_id   INT NOT NULL REFERENCES locations(region_id),
    observed_at TIMESTAMP NOT NULL,
    t1h         REAL,                      -- 기온 (C)
    rn1_mm      REAL,                      -- 1시간 강수량 (mm)
    reh         SMALLINT,                  -- 습도 (%)
    pty         SMALLINT,                  -- 강수형태: 0없음 1비 2비/눈 3눈 4소나기 5빗방울 6빗방울눈날림 7눈날림
    vec         SMALLINT,                  -- 풍향 (deg)
    wsd         REAL,                      -- 풍속 (m/s)
    PRIMARY KEY (region_id, observed_at)
);

-- ── 2) 초단기예보 (getUltraSrtFcst) — 향후 6시간 ─────────
CREATE TABLE IF NOT EXISTS ultra_forecast (
    region_id INT NOT NULL REFERENCES locations(region_id),
    fcst_at   TIMESTAMP NOT NULL,
    base_at   TIMESTAMP NOT NULL,
    t1h       REAL,
    rn1_text  TEXT,                        -- 강수량 범주 원문
    rn1_mm    REAL,
    sky       SMALLINT,                    -- 1맑음 3구름많음 4흐림
    reh       SMALLINT,
    pty       SMALLINT,
    pop       SMALLINT,                    -- 강수확률 (%)
    lgt       REAL,                        -- 낙뢰 (kA)
    vec       SMALLINT,
    wsd       REAL,
    PRIMARY KEY (region_id, fcst_at)
);

-- ── 3) 단기예보 (getVilageFcst) — 오늘~+4일, 추천의 메인 소스 ──
CREATE TABLE IF NOT EXISTS village_forecast (
    region_id   INT NOT NULL REFERENCES locations(region_id),
    fcst_at     TIMESTAMP NOT NULL,
    base_at     TIMESTAMP NOT NULL,
    is_extended BOOLEAN NOT NULL DEFAULT FALSE,
    tmp  REAL,                             -- 1시간 기온 (C)
    tmn  REAL,                             -- 일 최저기온
    tmx  REAL,                             -- 일 최고기온
    sky  SMALLINT,                         -- 1맑음 3구름많음 4흐림
    pty  SMALLINT,                         -- 0없음 1비 2비/눈 3눈 4소나기
    pop  SMALLINT,                         -- 강수확률 (%)
    pcp_text TEXT,
    pcp_mm   REAL,
    pcp_code SMALLINT,                     -- 연장기간 정성코드: 1약한비 2보통비 3강한비
    sno_text TEXT,
    sno_cm   REAL,
    sno_code SMALLINT,
    reh  SMALLINT,                         -- 습도 (%)
    wsd  REAL,                             -- 풍속 (m/s)
    wsd_code SMALLINT,
    vec  SMALLINT,
    wav  REAL,                             -- 파고 (m)
    PRIMARY KEY (region_id, fcst_at)
);
CREATE INDEX IF NOT EXISTS idx_vf_time ON village_forecast (fcst_at);

-- ── 4) 자외선지수 (LivingWthrIdxServiceV2/getUVIdxV2) ────
-- 발표: 일 2회 (06, 18시). 응답은 오늘/내일/모레/글피 일 단위 예측값.
-- (오늘값은 06시 발표에만, 글피값은 18시 발표에만 포함)
CREATE TABLE IF NOT EXISTS uv_index (
    area_no   TEXT NOT NULL,               -- 지점코드 (제주 5011000000 / 서귀포 5013000000)
    fcst_date DATE NOT NULL,               -- 예측 대상 날짜
    uv_value  SMALLINT,                    -- 0-2 낮음 / 3-5 보통 / 6-7 높음 / 8-10 매우높음 / 11+ 위험
    base_at   TIMESTAMP NOT NULL,          -- 발표 일시
    PRIMARY KEY (area_no, fcst_date)
);

-- ── 5) 제주 대기환경 (제주보건환경연구원 getJejuAirList, 매시·인증키 불필요) ───
-- 측정소 12곳 (SITE 코드 매핑은 config.JEJU_AIR_SITES)
-- ※ 예보 정책: 실시간 중심으로 village/ultra 모두 +6시간 이내만 보관 (db.purge_future)
CREATE TABLE IF NOT EXISTS jeju_air (
    station     TEXT NOT NULL,
    measured_at TIMESTAMP NOT NULL,
    pm10        SMALLINT,                  -- 미세먼지 (ug/m3)
    pm25        SMALLINT,                  -- 초미세먼지 (ug/m3)
    PRIMARY KEY (station, measured_at)
);

-- ── 수집 이력 ───────────────────────────────────────────
CREATE TABLE IF NOT EXISTS collect_log (
    id            SERIAL PRIMARY KEY,
    source        TEXT NOT NULL,           -- village / nowcast / ultra / uv / jeju_air
    started_at    TIMESTAMP NOT NULL,
    finished_at   TIMESTAMP,
    status        TEXT NOT NULL,
    rows_upserted INT DEFAULT 0,
    error         TEXT
);

-- 참고:
--  * fcstValue의 +900 이상 / -900 이하는 결측(Missing) → NULL.
--  * PM 등급 기준(추천 엔진용): PM10 좋음~30 보통~80 나쁨~150 / PM2.5 좋음~15 보통~35 나쁨~75.
--  * 자외선 8 이상이면 "한낮 야외활동 자제 + 자외선차단제" 추천 트리거로 활용.
