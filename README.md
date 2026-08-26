# english

필수 영어단어 PDF 6,000개로 매일 10개씩 외우는 학습 사이트.

하루 흐름은 고정이다. 첫날은 신규 10개, 다음날부터는 **어제 배운 10개 복습을 끝낸 뒤** 신규 10개를 연다. 날짜를 건너뛰어도 마지막에 외운 10개를 복습한다.

## 현재 상태

된 것:

- PDF → `vocab/*.md` (뜻 + 예문, 순위 1–6000)
- Postgres `app.english` 스키마, 로컬과 EC2 모두 단어 6,000개 import
- FastAPI 백엔드 (`back/`)와 API 테스트
- Nuxt 프론트 (`front/`, 오늘 학습 + 진도)
- EC2 배포: nginx `english-front` `:8089` + systemd `english-back` `:8090`

## 구성

```
words/      원본 PDF
vocab/      단어 마크다운 (50개씩, 120파일)
data/       PDF에서 뽑은 rank/word JSON
back/       FastAPI
front/      Nuxt 3 (정적 생성)
deploy/     EC2 docker-compose, systemd 유닛
scripts/    PDF 추출, DB import
aws/        EC2 SSH (connect.ps1 / connect.sh)
```

학습 데이터는 런타임에 PDF를 읽지 않는다. 소스 오브 트루스는 Postgres `english.word` 다.

## 학습 규칙

- 배치 크기: 10
- 날짜: Asia/Seoul
- `GET /v1/today` 의 `phase`: `review` → `new` → `done`
- 복습이 남아 있으면 신규 제출은 409
- `done` 이후 `오늘 더 하기` 로 다음 10개를 더 할 수 있다. 다음날 복습은 마지막 10개다.
- 알아/몰라 결과는 기록만 한다. 틀린 단어를 다음날 복습에 다시 넣지는 않는다.

## API

| 메서드 | 경로 | 역할 |
|--------|------|------|
| `GET` | `/v1/health` | DB ping |
| `GET` | `/v1/today` | 오늘 복습/신규 목록 |
| `POST` | `/v1/today/review` | 복습 10개 한 번에 제출 |
| `POST` | `/v1/today/new` | 신규 10개 한 번에 제출 |
| `GET` | `/v1/today/extra` | 오늘 할당이 끝난 뒤 다음 10개 |
| `POST` | `/v1/today/extra` | 추가 10개 한 번에 제출 |
| `GET` | `/v1/progress` | 학습 개수, 다음 순위, 연속일 |

인증은 없다. 1인 사용.

## DB

Postgres. DB `app`, 스키마 `english`.

| 테이블 | 역할 |
|--------|------|
| `word` | 순위, 철자, 뜻, 예문, 예문 한국어(`example_ko`) |
| `study_state` | 다음 신규 순위, 마지막 학습일 (1행) |
| `study_session` | 날짜별 복습/신규 구간과 완료 시각 |
| `word_result` | 세션별 알아/몰라 |

환경 변수 키는 `.env_sample` 을 복사해 `.env` 로 쓴다. `.env` 와 PEM은 git에 넣지 않는다.

로컬 Postgres는 Docker `english-postgres` (`127.0.0.1:5432`).  
EC2 Postgres는 `auto-postgres` 이고 `127.0.0.1:5432` 만 열려 있다. 바깥에서 붙을 때는 SSH 터널이 필요하다.

## 로컬 실행

백엔드:

```powershell
copy .env_sample .env
cd back
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe -m pytest -q
.\.venv\Scripts\python.exe -m uvicorn app.main:app --reload --port 8090
```

프론트 (`/v1` 은 8090으로 프록시):

```powershell
cd front
npm install
npm run dev
```

브라우저: `http://127.0.0.1:3000`

단어 import (이미 넣었으면 같은 rank는 덮어쓴다):

```powershell
.\back\.venv\Scripts\python.exe scripts\import_words.py
.\back\.venv\Scripts\python.exe scripts\import_words.py --ec2
```

EC2 SSH:

```powershell
.\aws\connect.ps1
```

## EC2

- 인스턴스: `t3.small` (2 vCPU, RAM 2GiB), 서울, `43.202.113.123`
- 이름: 내 웹 서버 / `i-01a43a81bbb416051`
- Docker는 이미 video / llm / postgres가 떠 있고 메모리가 빠듯하다. Swap을 쓰고 있다.
- 이 서버에서 `npm run build` / `docker build` 하지 않는다. 프론트 이미지는 로컬에서 만들어 올리고, 백엔드는 호스트 파이썬(venv + systemd)으로 돌린다.
- 프론트는 Nuxt 3 + TypeScript. SSR 없이 정적 생성으로 배포한다. 로컬에서 빌드한 nginx 이미지(Docker)를 올린다.
- 백엔드는 Docker 없이 EC2 호스트 파이썬(venv + systemd)로 uvicorn 워커 1개를 돌린다.
- 앱 URL: `https://yangyag4.duckdns.org` (호스트 nginx → `127.0.0.1:8089`). HTTP는 HTTPS로 301.
- nginx 컨테이너 `english-front` (`mem_limit 64m`, 호스트 8089). FastAPI `english-back.service` (`MemoryMax=192M`, `:8090`).
- host-gateway가 `127.0.0.1`에 닿지 않아 FastAPI는 `0.0.0.0:8090`에 연다. 화면은 8089만 쓴다.
- 프론트 이미지는 Docker Hub에 올리지 않는다. 로컬에서 빌드한 뒤 tar로 EC2에 넣어 `docker load` 한다.
- 헬스: `GET /v1/health`. 재기동 확인은 `systemctl status english-back`, `docker compose -f ~/english/docker-compose.yml ps`.

## 프론트 이미지 배포

레지스트리를 쓰지 않는다. EC2에서 `docker build` 하지 않는다.

1. 로컬: `nuxt generate` → `english-front:1.0` 이미지 빌드 (`linux/amd64`)
2. `docker save` 로 tar 작성
3. EC2 `~/english/` 로 scp (홈 디렉터리. snap Docker는 `/tmp` 에서 `docker load` 가 실패한다)
4. EC2: `docker load` 후 `docker compose up -d --force-recreate`

호스트는 `ubuntu@43.202.113.123`, 키는 `aws/test-keypair.pem`.

### PowerShell

```powershell
cd front
npm install
npx nuxi generate
docker build --platform linux/amd64 -t english-front:1.0 .
docker save english-front:1.0 -o $env:TEMP\english-front-1.0.tar

$key = ".\aws\test-keypair.pem"
icacls $key /inheritance:r | Out-Null
icacls $key /grant:r "$($env:USERNAME):R" | Out-Null

scp -i $key -o StrictHostKeyChecking=accept-new `
  $env:TEMP\english-front-1.0.tar `
  ubuntu@43.202.113.123:/home/ubuntu/english/english-front-1.0.tar

.\aws\connect.ps1 "docker load -i /home/ubuntu/english/english-front-1.0.tar; rm -f /home/ubuntu/english/english-front-1.0.tar; cd /home/ubuntu/english; docker compose up -d --force-recreate"
```

PEM 권한은 `.\aws\connect.ps1` 이 잡아 주므로, scp 전에 한 번 접속해 둬도 된다.

### Linux

```bash
cd front
npm install
npx nuxi generate
docker build --platform linux/amd64 -t english-front:1.0 .
docker save english-front:1.0 -o /tmp/english-front-1.0.tar

chmod 600 aws/test-keypair.pem
scp -i aws/test-keypair.pem -o StrictHostKeyChecking=accept-new \
  /tmp/english-front-1.0.tar \
  ubuntu@43.202.113.123:/home/ubuntu/english/english-front-1.0.tar

./aws/connect.sh "docker load -i /home/ubuntu/english/english-front-1.0.tar; rm -f /home/ubuntu/english/english-front-1.0.tar; cd /home/ubuntu/english; docker compose up -d --force-recreate"
```

로컬 `/tmp` 에 tar 를 두는 것은 괜찮다. 막히는 쪽은 EC2 snap Docker 가 `/tmp` 를 읽는 것이다.
