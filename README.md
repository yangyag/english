# english

필수 영어단어 PDF 6,000개로 매일 10개씩 외우는 학습 사이트.

하루 흐름은 고정이다. 첫날은 신규 10개, 다음날부터는 **어제 배운 10개 복습을 끝낸 뒤** 신규 10개를 연다. 날짜를 건너뛰어도 마지막에 외운 10개를 복습한다.

## 현재 상태

된 것:

- PDF → `vocab/*.md` (뜻 + 예문, 순위 1–6000)
- Postgres `app.english` 스키마, 로컬과 EC2 모두 단어 6,000개 import
- FastAPI 백엔드 (`back/`)와 API 테스트

아직인 것:

- Nuxt 프론트 (`front/`)
- EC2 Docker 배포 (호스트 포트는 8089가 비어 있음)

## 구성

```
words/      원본 PDF
vocab/      단어 마크다운 (50개씩, 120파일)
data/       PDF에서 뽑은 rank/word JSON
back/       FastAPI
scripts/    PDF 추출, DB import
aws/        EC2 SSH (connect.ps1 / connect.sh)
```

학습 데이터는 런타임에 PDF를 읽지 않는다. 소스 오브 트루스는 Postgres `english.word` 다.

## 학습 규칙

- 배치 크기: 10
- 날짜: Asia/Seoul
- `GET /v1/today` 의 `phase`: `review` → `new` → `done`
- 복습이 남아 있으면 신규 제출은 409
- 알아/몰라 결과는 기록만 한다. 틀린 단어를 다음날 복습에 다시 넣지는 않는다.

## API

| 메서드 | 경로 | 역할 |
|--------|------|------|
| `GET` | `/v1/today` | 오늘 복습/신규 목록 |
| `POST` | `/v1/today/review` | 복습 10개 한 번에 제출 |
| `POST` | `/v1/today/new` | 신규 10개 한 번에 제출 |
| `GET` | `/v1/progress` | 학습 개수, 다음 순위, 연속일 |

인증은 없다. 1인 사용.

## DB

Postgres. DB `app`, 스키마 `english`.

| 테이블 | 역할 |
|--------|------|
| `word` | 순위, 철자, 뜻, 예문 |
| `study_state` | 다음 신규 순위, 마지막 학습일 (1행) |
| `study_session` | 날짜별 복습/신규 구간과 완료 시각 |
| `word_result` | 세션별 알아/몰라 |

환경 변수 키는 `.env_sample` 을 복사해 `.env` 로 쓴다. `.env` 와 PEM은 git에 넣지 않는다.

로컬 Postgres는 WSL Docker `postgres17` (`127.0.0.1:5432`).  
EC2 Postgres는 `auto-postgres` 이고 `127.0.0.1:5432` 만 열려 있다. 바깥에서 붙을 때는 SSH 터널이 필요하다.

## 로컬 실행

```powershell
copy .env_sample .env
cd back
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe -m pytest -q
.\.venv\Scripts\python.exe -m uvicorn app.main:app --reload --port 8000
```

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
- 이 서버에서 `npm run build` / `docker build` 하지 않는다. 이미지는 로컬에서 만든다.
- 프론트는 Nuxt 3 + TypeScript. SSR 없이 정적 생성으로 배포한다. 로컬에서 빌드한 nginx 정적 파일 + FastAPI 워커 1개가 목표다.
