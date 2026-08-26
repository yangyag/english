# 프론트 · 배포 계획서

작성일: 2026-08-26 (AGENTS.md 기준)
상태: M1–M8 완료(2026-08-26). 다음 작업은 M9(예문 한글 DB 적재·화면). 앱은 `https://yangyag4.duckdns.org`.

## 1. 목표

- Nuxt 3 + TypeScript 프론트를 만들어 하루 학습 플로우를 웹에서 쓸 수 있게 한다.
- EC2 (t3.small)에 호스트 nginx(443, `yangyag4.duckdns.org`) + 프론트 컨테이너(8089) + FastAPI(호스트 파이썬, `:8090`) 로 배포한다.

## 2. 현황 (2026-08-26 배포 후)

### EC2 (`43.202.113.123`, t3.small 2GiB)

- 가용 RAM 약 789Mi, swap 1.0Gi 사용 중. 디스크 `/` 잔여 5.0Gi.
- 기존 컨테이너 7개 + `english-front` (3.4Mi / 64Mi). FastAPI RSS 약 70Mi / 192Mi.
- `auto-postgres` 는 `auto_default` 네트워크에 있고 별칭 `postgres` 로 접근 가능.
  호스트에는 `127.0.0.1:5432` 만 공개.
- **8089** = `english-front`. 호스트 nginx `yangyag4.duckdns.org` → `127.0.0.1:8089`.

### 저장소

- 백엔드 완료: FastAPI + 테스트 통과, 단어 6,000개 로컬/EC2 import 완료.
- 프론트: Nuxt 3 정적 생성, `front/Dockerfile` (nginx), `deploy/`.
- `.env`, `aws/test-keypair.pem` 로컬에 있음(둘 다 `.gitignore` 커버 확인).

## 3. 아키텍처 결정

### 프론트

- **Nuxt 3 + TypeScript, `ssr: false`**. 배포는 `nuxt generate` 로 정적 파일만 만든다.
- SSR/Node 서버를 띄우지 않는다. 이유: 서버 RAM 여유 부족, 1인용·SEO 불필요.
- 화면 2개: 오늘 학습(`/`), 진도(`/progress`).
- API 호출은 상대 경로 `/v1/...` 로만 한다. URL 분기 없음.

### 운영 토폴로지

```
브라우저 ── https://yangyag4.duckdns.org (:443)
              └─ 호스트 nginx (다른 duckdns와 동일)
                    └─ 127.0.0.1:8089 ── english-front (nginx:alpine, 정적 Nuxt)
                                            └─ /v1 ── host.docker.internal:8090
                                                       └─ FastAPI (호스트 venv, systemd, 워커 1)
                                                            └─ 127.0.0.1:5432 ── auto-postgres
```

- 공개 포트는 **443**(및 HTTP 301). 8089는 호스트에서 컨테이너로만 연다. Docker Hub는 쓰지 않는다.
- **Docker 이미지는 프론트(nginx) 하나만** 만든다. 백엔드는 EC2 호스트에서
  파이썬 venv + systemd 서비스(`english-back.service`)로 돌린다.
- 백엔드는 `0.0.0.0:8090`. 컨테이너 host-gateway(`172.17.0.1`)는 `127.0.0.1`에 닿지 않는다.
  DB 는 호스트 `127.0.0.1:5432`. `auto_default` 네트워크 연결이나 SSH 터널 불필요.
- 컨테이너 리소스 제한: nginx `mem_limit 64m`. FastAPI 는 호스트 프로세스라 systemd `MemoryMax=192M`.
- 프론트 이미지 빌드는 로컬 Windows/Linux Docker (`linux/amd64`).
  `docker save` tar 를 EC2 `~/english/` 로 scp 한 뒤 `docker load`.
  (EC2 snap Docker는 `/tmp`에서 load 가 실패한다. 파이프 `gzip | ssh docker load` 는 쓰지 않는다.)
- 백엔드 배포는 `back/` 을 scp/rsync 로 보낸 뒤 `pip install -r requirements.txt` (경량이라 서버 부담 없음).

### 로컬 개발

- `back`: `.venv` uvicorn 8090.
- `front`: `nuxt dev` (3000). `nuxt.config.ts` 의 nitro `devProxy` 로 `/v1` 을 `127.0.0.1:8090` 에 프록시.
- 운영과 같게 보려면 로컬 `english-front` 컨테이너 `:8089` + uvicorn `:8090` + `english-postgres` `:5432`.

## 4. 화면 설계

### 오늘 학습 (`/`)

- 진입 시 `GET /v1/today`. `phase` 로 분기:
  - `review`: 어제(마지막) 구간 10장 복습 → 완료 버튼 → `POST /v1/today/review`
  - `new`: 신규 10장 → `POST /v1/today/new`
  - `done`: 오늘 완료 안내 + **오늘 더 하기** + 진도 보기 (둘 다 버튼)
- 카드 UX: 앞면 단어, 뒷면 뜻+예문. 예문 아래 한글은 M9 (`example_ko`). 뒤집고 나서 알아요/몰라요 선택.
- 제출은 10장 결과를 모아 **한 번에** POST (구간 순위 전체).
- `POST /v1/today/new` 409(복습 미완료) 처리: 복습 화면으로 되돌린다.
- `done` 이후 `GET/POST /v1/today/extra` 로 다음 10개를 더 한다. 다음날 복습은 마지막 10개.
- 제출 성공 후 `GET /v1/today` 재조회로 phase 갱신.

### 진도 (`/progress`)

- `GET /v1/progress`: 학습 개수/6,000, 다음 순위, 연속일, 마지막 학습일.

### 공통

- API 응답 타입은 `back/app/schemas.py` 와 1:1로 맞춰 `front/types/api.ts` 에 수동 정의.
  (`TodayOut`, `WordOut`, `SubmitIn`, `ProgressOut`). `TodayOut.can_extra`, `WordOut.example_ko` 포함.

## 5. 마일스톤

각 마일스톤 완료 시 한글 커밋.

| # | 작업 | 완료 기준 |
|---|------|-----------|
| M1 | ~~Nuxt 스캐폴딩 (`front/`)~~ ✅ | `npm run generate` 성공, `ssr:false`, dev proxy 동작 — Nuxt 3.21.11 |
| M2 | ~~API 타입/클라이언트~~ ✅ | `front/types/api.ts` + `useEnglishApi` |
| M3 | ~~오늘 학습 화면~~ ✅ | 카드 뒤집기, 10장 일괄 제출, 409 시 재조회 |
| M4 | ~~진도 화면~~ ✅ | `/progress` 수치 표시 |
| M5 | ~~로컬 통합 검증~~ ✅ | pytest 통과, nginx `:8089` → FastAPI `:8090` |
| M6 | ~~프론트 이미지 빌드~~ ✅ | `english-front:1.0` linux/amd64 |
| M7 | ~~EC2 배포~~ ✅ | `english-front` 8089, `english-back.service`, DB 6,000 |
| M8 | ~~운영 점검~~ ✅ | `/v1/health`, 메모리, 로그, README |
| M9 | 예문 한글 적재·표시 | `vocab/*.md` 예문번역이 끝난 **다음날**. import 로컬+EC2, 카드 예문 아래 한글 표시, 프론트 이미지 재배포 |

선행: 워크플로 `example-ko` 의 vocab 번역(Translate)이 끝나야 한다. 번역 파일만 있고 DB/화면이 비어 있으면 M9를 한다. 코드에 `example_ko` 필드가 있어도 **적재와 운영 화면 반영은 M9**.

M9 순서:

1. `vocab/*.md` 에 `- 예문번역:` 6,000개 있는지 확인.
2. `scripts/import_words.py` 로 로컬 `english.word.example_ko` upsert, 이어서 `--ec2`.
3. 카드 뒷면: 영어 예문 아래 한글 (`example_ko` 있을 때만).
4. pytest, `nuxt generate`, `english-front:1.0` 다시 올려 `yangyag4` 에서 확인.

## 6. 배포 상세 (M6–M7)

### 프론트 (Docker)

1. 로컬: `nuxt generate` → `.output/public` 을 nginx:alpine 이미지에 COPY. 태그 `english-front:1.0`, `--platform linux/amd64`.
2. `docker save` 로 tar 를 만들고 EC2 `~/english/english-front-1.0.tar` 로 scp.
3. EC2: `docker load` 후 `~/english/docker-compose.yml` (`english-front`, 8089 공개, `mem_limit 64m`).
   - `extra_hosts: host.docker.internal:host-gateway`.
   - 컨테이너 nginx: `/v1` → `proxy_pass http://host.docker.internal:8090` (no-cache), 나머지 정적.
4. 호스트 nginx `yangyag4.duckdns.org` → `127.0.0.1:8089`. HTTPS는 certbot. 설정은 `deploy/nginx-yangyag4-english.conf`.
   명령 전문은 README 「프론트 이미지 배포」.

### 백엔드 (호스트 파이썬, Docker 아님)

1. `back/` 을 EC2 `~/english/back` 으로 scp/rsync.
2. EC2: `python3 -m venv .venv && .venv/bin/pip install -r requirements.txt`.
   (의존성이 가벼워 서버 부담 없음. 빌드 없는 순수 설치.)
3. systemd 유닛 `english-back.service`:
   - `ExecStart=.venv/bin/uvicorn app.main:app --host 0.0.0.0 --port 8090 --workers 1`
   - `EnvironmentFile=/home/ubuntu/english/.env` (DB 접속은 `127.0.0.1:5432`)
   - `MemoryMax=192M`, `Restart=always`, 서버 재부팅 시 자동 기동(`enable`).
4. 검증: `curl https://yangyag4.duckdns.org/`, `curl https://yangyag4.duckdns.org/v1/today`,
   `curl https://yangyag4.duckdns.org/v1/health`, `systemctl status english-back`.

### 롤백

- 프론트: 이전 이미지 태그(`english-front:이전`) 를 남겨두고 compose 태그만 바꿔 재생성.
- 백엔드: 덮어쓰기 전 `~/english/back` 을 `back.bak` 으로 복사해두고 되돌린 뒤 서비스 재시작.

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
