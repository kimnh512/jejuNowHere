# Azure Windows Server VM 배포 가이드

지금 PC에서 했던 것(Python + PostgreSQL + 작업 스케줄러)을 서버에 반복하고,
방화벽을 여는 것이 전부입니다. 소요 시간 약 40분.

## 0. 서버 접속 (RDP, 원격 데스크톱)

1. [portal.azure.com](https://portal.azure.com) → Virtual Machines → 내 VM 클릭 → **시작**(꺼져 있으면)
2. VM 화면 상단 **연결** → RDP → **RDP 파일 다운로드** → 더블클릭
3. VM 만들 때 정한 관리자 계정/비밀번호로 로그인 → 서버 바탕화면이 열림
4. **시간대를 한국으로** (수집 스케줄이 한국시각 기준): 서버에서 PowerShell(관리자) 열고

```powershell
Set-TimeZone "Korea Standard Time"
```

## 1. 프로그램 설치 (서버 안에서)

서버의 브라우저(Edge)로 3개를 내려받아 설치:

| 프로그램 | 주소 | 설치 시 주의 |
|---|---|---|
| Python 3.12+ | python.org/downloads | 첫 화면에서 **"Add python.exe to PATH" 체크** 필수 |
| PostgreSQL 17 | postgresql.org/download/windows | 설치 중 정한 **비밀번호 기억** |
| Git | git-scm.com/download/win | 기본값으로 계속 Next |

## 2. 코드 받기 + 설정

서버에서 PowerShell 열고:

```powershell
cd C:\
git clone https://github.com/kimnh512/jejuNowHere.git
cd jejuNowHere
python -m pip install -r requirements.txt
```

`.env` 만들기:

```powershell
copy .env.example .env
notepad .env
```

메모장에서 채우고 저장:
- `DATA_GO_KR_KEY` = 기존 공공데이터포털 키 (PC의 .env에서 복사)
- `DATABASE_URL` = `postgresql://postgres:서버PG비밀번호@localhost:5432/jejunowhere`
- `KAKAO_REST_KEY` = 카카오 REST 키

## 3. DB 초기화 + 수집 테스트

```powershell
& "C:\Program Files\PostgreSQL\17\bin\psql.exe" -U postgres -c "CREATE DATABASE jejunowhere;"
& "C:\Program Files\PostgreSQL\17\bin\psql.exe" -U postgres -d jejunowhere -f schema.sql
python seed_locations.py
python run.py all
```

`성공 — N행 적재`가 나오면 데이터 계층 완료.
(uv는 활용신청된 키여야 하고, jeju_air는 키 없이 됩니다.)

## 4. 자동 수집 + API 서버 등록 (한 줄)

PowerShell을 **관리자 권한**으로 열고:

```powershell
cd C:\jejuNowHere
powershell -ExecutionPolicy Bypass -File register_tasks.ps1 -WithApi
```

이것으로 ① 매시 수집 3종 ② API 서버(부팅 시 자동 시작 + 지금 즉시 시작 + 죽으면 1분 내 재시작)
③ Windows 방화벽 8000 포트 개방까지 끝. 확인:

```powershell
Start-Sleep 5; Invoke-RestMethod http://localhost:8000/health
```

## 5. Azure 방화벽(NSG) 열기 — 바깥세상에 공개

Azure Portal → 내 VM → **네트워킹**(네트워크 설정) → **인바운드 포트 규칙 추가**:
- 대상 포트 범위: `8000`, 프로토콜: `TCP`, 이름: `api-8000` → 추가

그다음 **아무 기기의 브라우저**(폰 LTE로 테스트하면 확실)에서:

```
http://VM공인IP:8000/docs
```

Swagger 문서가 열리면 배포 완료. 이 주소(`http://공인IP:8000`)가 플러터 앱이 바라볼 API 주소입니다.

## 6. 이후 코드 업데이트가 있을 때

```powershell
cd C:\jejuNowHere
git pull
Stop-ScheduledTask -TaskName JejuNowHere-API; Start-ScheduledTask -TaskName JejuNowHere-API
```

## 문제 해결

- `/health`가 안 열림 → `Get-Content logs\api.log -Tail 20` (uvicorn 에러 확인)
- 밖에서만 안 열림 → 5번 NSG 규칙 + `register_tasks.ps1 -WithApi`를 관리자로 실행했는지 확인
- 수집이 안 쌓임 → `Get-Content logs\collect.log -Tail 20`, 서버 시간대가 KST인지 확인
- VM 공인 IP가 재부팅마다 바뀜 → Azure Portal → VM → 공용 IP → 구성에서 **고정(Static)** 으로 변경

## 다음 단계 (선택)

- **도메인 + HTTPS**: 앱 스토어 출시 전엔 필요합니다. 도메인 연결 후 Caddy/nginx로
  리버스 프록시 + 인증서 자동 발급 (원하면 가이드 추가 요청)
- **VM 자동 시작**: 학생 크레딧 절약으로 VM을 꺼두는 경우, Azure 자동화로 시간대별 시작/중지 설정 가능
