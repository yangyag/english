# AGENTS

이 저장소에서 작업할 때 따른다. 사람용 개요는 `README.md`.

## 제품

개인용 영단어 학습. 달력에 공부한 날과 신규·복습 개수를 기록한다. 하루 제한 없이 한 단어씩 학습·저장하고, 마지막 신규 학습일의 단어를 선택적으로 복습한다. 본격 SRS는 넣지 않는다. 인증은 없다.

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
- 복습은 선택 사항이며 신규 학습을 막지 않는다. 신규는 다음 순위부터 하루 제한 없이 진행한다. `/extra`는 `/new`의 호환 별칭이다.
- 화면은 한 단어마다 POST한다. API는 다음 학습 목록의 앞에서부터 빠짐없는 1~10개 제출을 허용한다. 저장한 순위까지만 진도를 전진시킨다.
- 신규 결과의 `known`은 NULL(평가 없음), 복습은 true/false(기억나요/기억 안 나요)다. 구 클라이언트가 신규에 보낸 불리언도 NULL로 저장한다. 과거에 저장된 응답은 변경하지 않는다.
- 복습 대상은 오늘 이전 가장 최근 신규 학습일의 신규 단어 전체다. source_date별 완료 순위를 제외하여 10개씩 이어간다. 복습만 한 날은 대상을 바꾸지 않는다.
- 서버는 강제 `phase` 대신 신규·복습 목록과 복습 진행 상황을 제공한다.
- 요청 UUID와 내용으로 중복 제출을 처리하며 쓰기는 트랜잭션 잠금으로 직렬화한다. 시작일이 지난 미제출 요청은 409, 이미 성공한 요청의 동일 재시도는 성공이다.
- 새 결과는 `study_batch` / `batch_result`에 저장한다. 기존 `study_session` / `word_result`는 보존하며 시작 시 반복 가능한 이전을 수행한다. 틀린 단어를 다음 복습에 자동 재삽입하지 않는다.
- 날짜별 기록은 제출 완료일 KST 기준이다. 누적 신규는 고유 단어 수이며 과거 날짜가 없는 진도는 별도로 안내한다.
- 스키마/테이블은 `english`. SQLAlchemy 모델과 어긋나게 raw SQL 테이블을 만들지 않는다.
- 설정은 저장소 루트 `.env`. 키 목록은 `.env_sample`. 비밀번호를 문서나 샘플에 쓰지 않는다.

## 프론트

- Nuxt 3 + TypeScript, 폴더 `front/`. SSR 없이 정적 생성(`ssr: false`, `nuxt generate`)으로만 배포한다.
- 화면은 학습 달력(카드 학습 포함)과 진도 두 개다. 날짜별 기록과 월 이동을 제공하며 하루 목표나 연속 학습 지표를 넣지 않는다.
- 카드 UX: 앞면 단어, 뒷면 뜻+예문. 신규는 학습 완료, 복습은 기억나요/기억 안 나요. 한 단어 저장 성공 후 다음 카드로 이어간다. 저장된 응답을 이전 카드 버튼으로 취소하지 않는다.
- 복습하기와 새 단어 배우기를 자유롭게 선택한다. 저장 확인 전 응답은 브라우저에 임시 보관하고 동일 UUID·내용으로 재시도한다. 완료 기록은 서버에 저장된 결과만 집계한다.
- UI 변경은 Playwright로 데스크톱·모바일을 확인한다. `scripts/verify_browser.py`는 임시 로컬 DB와 합성 데이터만 사용한다.
- 로컬은 Nuxt dev server의 proxy 로 `/v1` 을 FastAPI에 붙인다. 운영은 nginx 가 `/v1` 을 FastAPI에 프록시한다.

## EC2 / Docker

- 박스: `t3.small` 2GiB. Kafka/video/llm이 이미 떠 있다. 가용 RAM이 적다.
- Postgres는 기존 `yangyag-postgres` 의 `yangyag` / `app` / `english` 를 쓴다(2026-09-06 운영 확인). DB 컨테이너를 추가하지 않는다.
- 호스트 8089가 다음 빈 포트다. 8083–8088은 다른 서비스 것이다.
- 프론트는 nginx 이미지로 만든다. 빌드는 로컬에서만 하고 EC2에는 `docker load` 로 올린다.
- 백엔드는 Docker에 넣지 않는다. EC2 호스트에서 파이썬 venv + systemd(`english-back.service`)로 uvicorn 워커 1개를 돌린다.
- 런타임은 nginx 컨테이너(정적 Nuxt, `mem_limit 64m`) + 호스트 파이썬 FastAPI 워커 1개뿐이다. Redis, 큐, Node 서버 없음. Nuxt SSR 서버도 띄우지 않는다.
- FastAPI는 `0.0.0.0:8090` (컨테이너 host-gateway 접근용). 브라우저 진입은 `https://yangyag4.duckdns.org` (호스트 nginx 443 → `127.0.0.1:8089`). DB는 호스트 `127.0.0.1:5432`.
- EC2 Postgres는 `127.0.0.1:5432` 만 연다. 원격 import는 `scripts/import_words.py --ec2` (SSH 터널).

## Git

- 커밋 메시지는 한글로 쓴다.

## 하지 말 것

- `.env`, `*.pem`, `back/.venv` 커밋.
- 영어 커밋 메시지.
- 학습 API에서 `vocab/` 이나 PDF를 직접 읽기.
- 복습을 강제하거나 하루 신규 제한을 다시 도입하기.
- EC2에 무거운 컨테이너를 더 올리기.
- 프론트를 React로 바꾸기.
