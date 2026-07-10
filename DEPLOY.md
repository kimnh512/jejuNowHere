# 클라우드 배포 가이드

현재 운영 구성 (전부 무료):

```
[GitHub Actions]  매시 50분 수집 ──▶  [Supabase]  PostgreSQL (무료)
                                          ▲
[Azure App Service]  FastAPI (F1 무료) ───┘
  https://jejunowhere-....azurewebsites.net
```

## A. App Service 배포 (현재 구성)

레포를 App Service에 연결(GitHub 배포)한 상태에서 아래 4단계를 마치면 작동합니다.

### 1. Supabase — 무료 PostgreSQL 만들기 (10분)

1. [supabase.com](https://supabase.com) 가입 → **New project**
   - Region: `Northeast Asia (Seoul)`, Database Password 정해서 **기억**
2. 프로젝트 열리면 상단 **Connect** 버튼 → **Session pooler** 탭의 URI 복사:
   `postgresql://postgres.xxxx:[YOUR-PASSWORD]@aws-0-ap-northeast-2.pooler.supabase.com:5432/postgres`
3. `[YOUR-PASSWORD]` 자리를 실제 비밀번호로 바꾼 문자열이 이후의 `DATABASE_URL`
   (※ 반드시 Session pooler 주소 — Direct connection은 IPv6 전용이라 안 됨)

### 2. GitHub Secrets — 수집 워크플로에 키 전달

레포(github.com/kimnh512/jejuNowHere) → Settings → **Secrets and variables → Actions**
→ New repository secret 두 개:

| Name | Value |
|---|---|
| `DATABASE_URL` | 1번에서 만든 Supabase 연결 문자열 |
| `DATA_GO_KR_KEY` | 공공데이터포털 인증키 (PC .env의 것) |

### 3. DB 초기화 + 첫 수집 (버튼 2번)

레포 → **Actions** 탭:
1. 왼쪽 `setup-db` → **Run workflow** → 초록 체크 확인 (테이블 + 읍면 14곳)
2. 왼쪽 `collect-weather` → **Run workflow** → 초록 체크 확인 (첫 데이터 적재)

이후 매시 50분마다 자동 수집됩니다 (Actions 탭에서 이력 확인 가능).

### 4. App Service 설정 (Azure Portal)

App Service(jejuNowHere) → **설정 > 환경 변수(구성)** → **앱 설정**에 추가:

| 이름 | 값 |
|---|---|
| `DATABASE_URL` | Supabase 연결 문자열 (Secrets와 동일) |
| `KAKAO_REST_KEY` | 카카오 REST API 키 |
| `TZ` | `Asia/Seoul` |

**구성 > 일반 설정 > 시작 명령**:

```
python -m uvicorn api:app --host 0.0.0.0 --port 8000
```

저장 → **다시 시작** → 1~2분 후 확인:

```
https://jejunowhere-aveeg9b5hgamh7gf.koreacentral-01.azurewebsites.net/health
https://jejunowhere-aveeg9b5hgamh7gf.koreacentral-01.azurewebsites.net/docs
```

`/health`가 `{"status":"ok", ...}`를 주면 배포 완료 — 이 주소가 플러터 앱의 API 주소입니다.
HTTPS가 기본 제공되므로 도메인·인증서 작업이 필요 없습니다.

### F1 무료 요금제 참고

- 20분 미사용 시 잠들어 첫 요청이 30초쯤 걸림 (데이터 수집은 Actions가 하므로 영향 없음)
- 하루 CPU 60분 제한 — 개발·데모엔 충분, 출시 전 B1 요금제로 올리면 상시 가동
- 코드 수정 후 `git push`만 하면 자동 재배포 (Azure가 만든 워크플로)

### 문제 해결

- `/health`가 503/에러 → App Service **로그 스트림**에서 원인 확인.
  대부분 DATABASE_URL 오타 또는 시작 명령 미설정
- Actions 수집 실패(빨간 X) → 해당 실행 로그 확인. `SERVICE_KEY...` 류면 키 문제,
  connection 에러면 DATABASE_URL의 pooler 주소/비밀번호 확인
- 응답이 느림 → F1 슬립에서 깨어나는 중 (정상)

## B. (대안) Windows VM 배포

VM으로 직접 운영하는 경우: RDP 접속 → `Set-TimeZone "Korea Standard Time"` →
Python(PATH 체크)·PostgreSQL·Git 설치 → `git clone` → `.env` 작성 →
`schema.sql`+`seed_locations.py` → 수집은 `python run.py all`, API 서버는
`python -m uvicorn api:app --host 0.0.0.0 --port 8000` 실행 →
Azure NSG 인바운드 TCP 8000 개방 → `http://공인IP:8000/docs` 확인.
