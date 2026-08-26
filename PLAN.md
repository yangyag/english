# 프론트 · 배포 계획서

작성일: 2026-08-26 (AGENTS.md 기준)
상태: 승인 대기. 이 문서의 마일스톤 순서대로 진행한다.

## 1. 목표

- Nuxt 3 + TypeScript 프론트를 만들어 하루 학습 플로우를 웹에서 쓸 수 있게 한다.
- EC2 (t3.small)에 nginx(정적, Docker) + FastAPI(호스트 파이썬, 워커 1) 로 배포한다. 포트는 8089.

## 2. 현황 (2026-02 실측)

### EC2 (`43.202.113.123`, t3.small 2GiB)

- 가용 RAM 약 670Mi, swap 928Mi 사용 중. 디스크 `/` 잔여 5.0Gi.
- 실행 컨테이너 7개: video-api/worker/frontend, kafka, llm-front/back, auto-postgres.
- `auto-postgres` 는 `auto_default` 네트워크에 있고 별칭 `postgres` 로 접근 가능.
  호스트에는 `127.0.0.1:5432` 만 공개.
- 8083–8088 사용 중(8084/8085 제외 일부 혼재), **8089 비어 있음**.

### 저장소

- 백엔드 완료: FastAPI + 테스트 통과, 단어 6,000개 로컬/EC2 import 완료.
- 프론트 없음(`front/` 미생성), Dockerfile/compose 없음.
- `.env`, `aws/test-keypair.pem` 로컬에 있음(둘 다 `.gitignore` 커버 확인).

## 3. 아키텍처 결정

### 프론트

- **Nuxt 3 + TypeScript, `ssr: false`**. 배포는 `nuxt generate` 로 정적 파일만 만든다.
- SSR/Node 서버를 띄우지 않는다. 이유: 서버 RAM 여유 부족, 1인용·SEO 불필요.
- 화면 2개: 오늘 학습(`/`), 진도(`/progress`).
- API 호출은 상대 경로 `/v1/...` 로만 한다. URL 분기 없음.

### 운영 토폴로지

```
브라우저 ── :8089 ── nginx:alpine (정적 Nuxt, Docker)
                        └─ /v1 프록시 ── host-gateway:8000
                                           └─ FastAPI (호스트 파이썬 venv, uvicorn 워커 1, systemd)
                                                └─ 127.0.0.1:5432 ── auto-postgres (english 스키마)
```

- **Docker 이미지는 프론트(nginx) 하나만** 만든다. 백엔드는 EC2 호스트에서
  파이썬 venv + systemd 서비스(`english-back.service`)로 돌린다.
- 백엔드는 `127.0.0.1:8000` 에만 바인딩. DB 는 이미 호스트에 공개된 `127.0.0.1:5432` 로 접속.
  `auto_default` 네트워크 연결이나 SSH 터널 불필요.
- 컨테이너 리소스 제한: nginx `mem_limit 64m`. FastAPI 는 호스트 프로세스라 systemd `MemoryMax=192M`.
- 프론트 이미지 빌드는 로컬(WSL). EC2에는 `docker save | ssh docker load` 로만 전달.
- 백엔드 배포는 `rsync` 로 코드 전송 후 `pip install -r requirements.txt` (경량이라 서버 부담 없음).

### 로컬 개발

- `back`: `.venv` uvicorn 8000.
- `front`: `nuxt dev` (3000). `nuxt.config.ts` 의 `routeRules`/dev proxy 로 `/v1` 을 `127.0.0.1:8000` 에 프록시.

## 4. 화면 설계

### 오늘 학습 (`/`)

- 진입 시 `GET /v1/today`. `phase` 로 분기:
  - `review`: 어제(마지막) 구간 10장 복습 → 완료 버튼 → `POST /v1/today/review`
  - `new`: 신규 10장 → `POST /v1/today/new`
  - `done`: 오늘 완료 안내 + 진도 링크
- 카드 UX: 앞면 단어, 뒷면 뜻+예문. 뒤집고 나서 알아요/몰라요 선택.
- 제출은 10장 결과를 모아 **한 번에** POST (구간 순위 전체).
- `POST /v1/today/new` 409(복습 미완료) 처리: 복습 화면으로 되돌린다.
- 제출 성공 후 `GET /v1/today` 재조회로 phase 갱신.

### 진도 (`/progress`)

- `GET /v1/progress`: 학습 개수/6,000, 다음 순위, 연속일, 마지막 학습일.

### 공통

- API 응답 타입은 `back/app/schemas.py` 와 1:1로 맞춰 `front/types/api.ts` 에 수동 정의.
  (`TodayOut`, `WordOut`, `SubmitIn`, `ProgressOut`)

## 5. 마일스톤

각 마일스톤 완료 시 한글 커밋.

| # | 작업 | 완료 기준 |
|---|------|-----------|
| M1 | Nuxt 스캐폴딩 (`front/`) | `npm run generate` 성공, `ssr:false`, dev proxy 동작 |
| M2 | API 타입/클라이언트 | `types/api.ts` + composables, 목업 없이 실제 API 타입 일치 |
| M3 | 오늘 학습 화면 | review→new→done 전 구간 수동 통과 |
| M4 | 진도 화면 | progress 수치 표시 |
| M5 | 로컬 통합 검증 | `back` pytest 통과 + 프론트-백 실제 연동 시나리오 점검 |
| M6 | 프론트 이미지 빌드 | `front/Dockerfile`(nginx) 로컬 빌드 성공. 백은 이미지화하지 않음 |
| M7 | EC2 배포 | nginx 컨테이너 8089 응답, 백 systemd 기동, DB 연결 확인 |
| M8 | 운영 점검 | 헬스체크, 메모리/스왑 추이, 로그 확인, README 갱신 |

## 6. 배포 상세 (M6–M7)

### 프론트 (Docker)

1. 로컬: `nuxt generate` → `.output/public` 을 nginx:alpine 이미지에 COPY.
2. `docker save english-front | gzip | ssh ... docker load` 로 전달.
3. EC2: `~/english/docker-compose.yml` (서비스 front 하나, 8089 공개, `mem_limit 64m`).
   - 컨테이너에서 호스트의 FastAPI 를 찍기 위해 `extra_hosts: host.docker.internal:host-gateway`.
   - nginx 설정: `/v1` → `proxy_pass http://host.docker.internal:8000` (no-cache), 나머지 정적.

### 백엔드 (호스트 파이썬, Docker 아님)

1. `rsync` 로 `back/` 을 EC2 `~/english/back` 으로 전송.
2. EC2: `python3 -m venv .venv && .venv/bin/pip install -r requirements.txt`.
   (의존성이 가벼워 서버 부담 없음. 빌드 없는 순수 설치.)
3. systemd 유닛 `english-back.service`:
   - `ExecStart=.venv/bin/uvicorn app.main:app --host 127.0.0.1 --port 8000 --workers 1`
   - `EnvironmentFile=/home/ubuntu/english/back/.env` (DB 접속은 `127.0.0.1:5432`)
   - `MemoryMax=192M`, `Restart=always`, 서버 재부팅 시 자동 기동(`enable`).
4. 검증: `curl :8089/`, `curl :8089/v1/today`, `systemctl status english-back`.

### 롤백

- 프론트: 이전 이미지 태그(`english-front:이전`) 를 남겨두고 compose 태그만 바꿔 재생성.
- 백엔드: rsync 전 `~/english/back` 을 `back.bak` 으로 복사해두고 되돌린 뒤 서비스 재시작.

## 7. 리스크와 대응

| 리스크 | 대응 |
|--------|------|
| EC2 메모리 부족 | 서버에서 빌드 전무, Docker 는 nginx 하나(mem_limit 64m), 백은 systemd MemoryMax, swap 모니터 |
| 복습 게이트 우회 시도 | 프론트는 phase 만 따른다. 409 수신 시 review 로 되돌림. 게이트 로직은 백엔드 단독 유지 |
| 날짜 경계(서울 자정) | 모든 날짜 판단은 백엔드(clock.py). 프론트는 표시만 |
| 정적 배포 후 캐시 | nginx 에 `/v1` no-cache, 정적 자산은 hash 파일명이라 긴 캐시 |
| 디스크 5GB | 이미지 태그 최대 2개 유지, 오래된 `docker image prune` |

## 8. 하지 않는 것

- SSR, Node 런타임 서버, Redis, 큐, 인증, 본격 SRS.
- EC2에서의 npm install / docker build / 이미지 빌드.
- 백엔드의 Docker 이미지화. 백은 EC2 호스트 파이썬 + systemd 로만 운영한다.
- 틀린 단어의 자동 재삽입.
