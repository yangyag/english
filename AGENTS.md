# AGENTS

이 저장소에서 작업할 때 따른다. 사람용 개요는 `README.md`.

## 제품

개인용 영단어 학습. 매일 신규 10개. 다음날은 마지막에 배운 10개를 복습한 뒤에만 신규가 열린다. 본격 SRS는 넣지 않는다. 인증은 없다.

## 레이아웃

- `back/` FastAPI. 앱 코드는 `back/app`, 테스트는 `back/tests`.
- `front/` Nuxt 3 + TypeScript. React/Next 쓰지 않는다.
- `deploy/` EC2 compose와 systemd 유닛.
- `vocab/` 생성된 마크다운. `english.word` 의 원본.
- `words/` PDF 원본.
- `scripts/import_words.py` 1회성 import. 학습 경로에서 PDF/MD를 읽지 않는다.
- `aws/` SSH만. `status`/`report` 스크립트는 지웠다. `*.pem` 은 커밋 금지.

## 백엔드 규칙

- API를 바꾸면 `back/tests` 에 테스트를 같이 고친다. `cd back` 후 `python -m pytest -q`.
- 날짜는 `Asia/Seoul` (`app/clock.py`). 테스트는 `get_today` 를 오버라이드한다.
- 복습은 하드 게이트다. `review_from_rank` 가 있는데 복습 미완료면 `POST /v1/today/new` 와 `/v1/today/extra` 는 409.
- review/new/extra 제출은 단어 단위가 아니라 **해당 구간의 순위 전체**다. 프론트는 10장을 모아서 한 번에 POST 한다.
- 오늘 신규가 끝난 뒤에만 `GET/POST /v1/today/extra` 로 다음 10개를 더 한다. 다음날 복습은 마지막에 배운 10개다.
- `phase`: `review` | `new` | `done`.
- 틀린 단어는 `word_result` 에만 남긴다. 다음날 복습 목록에 자동 재삽입하지 않는다.
- 스키마/테이블은 `english`. SQLAlchemy 모델과 어긋나게 raw SQL 테이블을 만들지 않는다.
- 설정은 저장소 루트 `.env`. 키 목록은 `.env_sample`. 비밀번호를 문서나 샘플에 쓰지 않는다.

## 프론트

- Nuxt 3 + TypeScript, 폴더 `front/`. SSR 없이 정적 생성(`ssr: false`, `nuxt generate`)으로만 배포한다.
- 화면은 오늘 학습과 진도 두 개면 충분하다.
- 카드 UX: 앞면 단어, 뒷면 뜻+예문, 알아요/몰라요. 10장 후 일괄 제출.
- `phase` 를 따른다. 복습 중에 신규로 가지 않는다.
- 로컬은 Nuxt dev server의 proxy 로 `/v1` 을 FastAPI에 붙인다. 운영은 nginx 가 `/v1` 을 FastAPI에 프록시한다.

## EC2 / Docker

- 박스: `t3.small` 2GiB. Kafka/video/llm이 이미 떠 있다. 가용 RAM이 적다.
- Postgres는 기존 `auto-postgres` 의 `yangyag` / `app` / `english` 를 쓴다. DB 컨테이너를 추가하지 않는다.
- 호스트 8089가 다음 빈 포트다. 8083–8088은 다른 서비스 것이다.
- 프론트는 nginx 이미지로 만든다. 빌드는 로컬에서만 하고 EC2에는 `docker load` 로 올린다.
- 백엔드는 Docker에 넣지 않는다. EC2 호스트에서 파이썬 venv + systemd(`english-back.service`)로 uvicorn 워커 1개를 돌린다.
- 런타임은 nginx 컨테이너(정적 Nuxt, `mem_limit 64m`) + 호스트 파이썬 FastAPI 워커 1개뿐이다. Redis, 큐, Node 서버 없음. Nuxt SSR 서버도 띄우지 않는다.
- FastAPI는 `0.0.0.0:8090` (nginx host-gateway 접근용). 브라우저 진입은 nginx `8089`. DB는 호스트 `127.0.0.1:5432`.
- EC2 Postgres는 `127.0.0.1:5432` 만 연다. 원격 import는 `scripts/import_words.py --ec2` (SSH 터널).

## Git

- 커밋 메시지는 한글로 쓴다.

## 하지 말 것

- `.env`, `*.pem`, `back/.venv` 커밋.
- 영어 커밋 메시지.
- 학습 API에서 `vocab/` 이나 PDF를 직접 읽기.
- 복습을 건너뛰고 신규를 열게 만들기.
- EC2에 무거운 컨테이너를 더 올리기.
- 프론트를 React로 바꾸기.
