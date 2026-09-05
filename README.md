# english

필수 영어단어 PDF 6,000개를 나의 속도로 학습하고, 공부한 날을 달력에 기록하는 개인용 사이트.

달력에서 공부한 날짜와 그날의 단어를 확인한다. 하루 개수 제한 없이 한 단어씩 배우고 저장한다. 다시 방문하면 마지막 신규 학습일의 단어를 선택적으로 복습한다. 복습을 건너뛰어도 신규 학습을 할 수 있다.

## 현재 상태

된 것:

- PDF → `vocab/*.md` (뜻 + 예문, 순위 1–6000)
- Postgres `app.english` 스키마, 로컬과 EC2 모두 단어 6,000개 import
- FastAPI 백엔드 (`back/`)와 API 테스트
- Nuxt 프론트 (`front/`, 학습 달력·카드 + 진도)
- 달력 개편, 한 단어 즉시 저장, 신규/복습 버튼 분리 운영 반영 완료(2026-09-06). [검증 기록](docs/single-word-verification.md), [배포 기록](docs/single-word-deployment.md).
- 기존 EC2 구성: nginx `english-front` `:8089` + systemd `english-back` `:8090`

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

- 화면은 한 단어씩 저장하고 다음 카드로 이어진다. 일일 제한 없음. API 조회는 최대 10개, 제출은 다음 목록의 앞에서부터 1~10개를 허용한다.
- 날짜: Asia/Seoul
- 신규 학습은 마지막 진도부터 이어진다. 복습은 선택 사항이다.
- 복습 대상은 오늘 이전 가장 최근 신규 학습일에 배운 단어 전체다. 같은 날 30개를 배우면 다음 방문에 30개를 제안한다.
- 복습도 한 단어씩 완료 순위를 저장한다. 복습만 한 날은 대상 날짜를 바꾸지 않는다. 새 신규 학습일이 생기면 다음날부터 그 날짜가 대상이다.
- 달력에는 제출 완료일을 기록하고 신규·복습 개수를 구분한다. 누적 학습 수에는 신규 고유 단어만 포함한다.
- 신규는 뜻·예문 확인 후 **학습 완료**, 복습은 **기억나요 / 기억 안 나요**를 누르면 즉시 저장한다. 한 단어만 학습하고 달력으로 돌아가도 기록이 남는다.
- 저장이 확인되기 전에는 응답을 브라우저에 보관하고 다음 카드로 넘어가지 않는다. 통신 실패·새로고침 뒤에는 동일 요청으로 재시도한다. 저장된 응답을 되돌리는 이전 카드 버튼은 없다.
- 제출 날짜가 바뀌었으면 다시 시작한다. 이미 성공한 요청의 재시도는 날짜가 바뀌어도 중복 저장하지 않는다.
- 신규 결과는 `known=NULL`(평가 없음), 복습은 `known=true/false`로 저장한다. 과거 신규·복습의 불리언 응답은 그대로 보존하므로 분석할 때 학습 종류를 구분한다. 기억 안 난 단어를 다음번 복습에 자동으로 다시 넣지 않는다.

## API

| 메서드 | 경로 | 역할 |
|--------|------|------|
| `GET` | `/v1/health` | DB ping |
| `GET` | `/v1/today` | 오늘 복습/신규 목록 |
| `POST` | `/v1/today/review` | 다음 복습 단어부터 1~10개 제출, 기억 여부 필수 |
| `POST` | `/v1/today/new` | 다음 신규 단어부터 1~10개 제출, 평가 없음 |
| `GET/POST` | `/v1/today/extra` | today 조회 / 신규 제출의 호환 별칭 |
| `GET` | `/v1/calendar?month=YYYY-MM` | 월별 공부한 날짜와 신규·복습 수 |
| `GET` | `/v1/calendar/YYYY-MM-DD` | 그날 단어와 응답 |
| `GET` | `/v1/progress` | 누적 고유 학습 수, 공부한 날짜 수, 다음 순위 |

제출 본문은 `request_id`(UUID), `study_date`, `source_date`(신규는 null), `results`(rank·known 목록)다. 신규 known은 null 또는 생략, 복습은 불리언 필수다. 요청 번호와 내용이 같으면 성공으로 재처리하고, 같은 번호로 다른 내용이나 다음 목록 앞부분과 다른 순위를 보내면 409다. `GET /today`는 `new`, `review`, `review_source_date`, `review_total`, `review_completed`를 제공한다. 강제 `phase`는 없다. 한 단어 저장 전환 시 백엔드를 먼저 갱신한다. 기존 달력 프론트의 10개 제출도 허용하지만 신규 known은 null로 저장한다.

인증은 없다. 1인 사용.

## DB

Postgres. DB `app`, 스키마 `english`.

| 테이블 | 역할 |
|--------|------|
| `word` | 순위, 철자, 뜻, 예문, 예문 한국어(`example_ko`) |
| `study_state` | 다음 신규 순위, 마지막 학습일 (1행) |
| `study_session` | 보존된 구 날짜별 세션 |
| `word_result` | 보존된 구 응답 원본 |
| `study_batch` | 제출 UUID, 완료일, 신규/복습, 복습 원본 날짜 |
| `batch_result` | 제출별 단어와 평가 없음(NULL)/기억나요(true)/기억 안 나요(false) |

시작 시 SQLAlchemy 모델로 새 테이블을 만들고 기존 응답을 반복 가능한 방식으로 이전한다. 원본 테이블과 진도는 보존한다. 과거 날짜가 없는 진도는 달력 날짜를 만들지 않고 누적 수에만 포함한다. 자세한 [이전·복구 절차](docs/calendar-migration.md)를 배포 전에 확인한다.

환경 변수 키는 `.env_sample` 을 복사해 `.env` 로 쓴다. `.env` 와 PEM은 git에 넣지 않는다.

로컬 Postgres는 기존 컨테이너의 `127.0.0.1:5432`를 사용한다. 테스트는 별도의 임시 데이터베이스를 생성한다.
EC2 Postgres는 `yangyag-postgres` 이고 `127.0.0.1:5432` 만 열려 있다(2026-09-06 운영 확인). 바깥에서 붙을 때는 SSH 터널이 필요하다.

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

## 검증

백엔드 테스트는 `back`에서 가상환경의 `python -m pytest -q`로 실행한다. 로컬 접속을 강제하고 `english_test_<UUID>` DB를 생성하여 종료 시 삭제한다. 로컬 계정에 CREATEDB 권한이 필요하다. `.env`가 없는 이 작업 환경에서는 기존 `yangyag-postgres` 컨테이너를 이용하며 비밀번호를 출력·저장하지 않는다. 필요하면 `ENGLISH_TEST_POSTGRES_CONTAINER`로 컨테이너 이름을 지정한다. 컨테이너 환경에 인증 정보가 없으면 테스트 전용 임시 역할을 생성하고 종료 시 삭제한다.

```powershell
cd front
npm ci
npx playwright install chromium
npm run typecheck
npm run generate
cd ..
.\back\.venv\Scripts\python.exe scripts\verify_browser.py
```

브라우저 검증 스크립트는 별도 임시 DB에 합성 단어 35개를 준비하고 FastAPI `18090`과 Nuxt dev `13000`으로 실행한다. 테스트 후 서버와 임시 DB를 정리한다. `ENGLISH_API_TARGET`은 검증용 dev proxy 주소이며 운영 빌드에 서버 런타임을 추가하지 않는다. 스크린샷은 `docs/screenshots/`에 남는다. [계획](docs/calendar-plan.md), [검증 결과](docs/calendar-verification.md).

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
