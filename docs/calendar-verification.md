# 달력 개편 검증 기록

2026-09-05, Windows 로컬. 운영 접속·주문·커밋·푸시·배포 없음. 기존 학습 데이터 대신 실행마다 생성하는 별도 PostgreSQL DB와 합성 데이터를 사용했다.

## 완료 근거

| 요구사항 | 구현 및 확인 |
| --- | --- |
| 달력이 메인, 공부한 날 표시·월 이동·날짜 상세 | `front/pages/index.vue`, `/v1/calendar`; Playwright에서 9월→8월→9월 이동, 지난 학습일 단어 및 개수 조회 |
| 하루 제한 없이 10개씩 신규, 마지막 잔여 묶음 | `study._new_words`, `submit`; pytest의 여러 묶음/3개 잔여/빈 DB, 브라우저의 10개+5개 제출 |
| 복습 선택, 최근 신규 학습일 전체가 대상 | `study._review`; pytest 20·30개 대상 및 며칠 쉰 뒤 복귀; 브라우저에서 복습 전에 신규 완료 |
| 복습 재개·완료 유지·복습만 한 날짜 | pytest에서 월을 건너뛰며 30개 이어서 복습, 완료 후 다음날 대상 없음; 브라우저 10개 복습→새로고침→남은 10개 |
| 틀린 단어는 결과만 기록 | pytest에서 틀린 응답이 다음 복습에 다시 삽입되지 않음; 날짜별 detail의 known 값 확인 |
| 제출 전 응답은 기록하지 않음 | 단순 방문의 달력 빈 상태, 브라우저 첫 카드 응답 후 새로고침하여 다음 카드 복구 |
| UUID 중복·동시 제출 | PostgreSQL 실제 두 트랜잭션의 동일/상이 UUID 동시 요청 검증; 브라우저에서 서버 commit 직후 응답을 끊고 재접속·재제출하여 신규 10개만 반영 |
| KST·날짜/월/연도 경계 | `test_clock.py`, `test_today.py`, `test_progress.py`; 날짜 변경 미제출 409, 이미 성공한 전날 요청 재시도 200 |
| 누적 신규 고유 수와 신규/복습 분리 | 복습 후 누적 30 유지; 브라우저 최종 35개·2일, 날짜별 신규 15·복습 20 |
| 기존 기록·진도 보존과 반복 이전 | `test_migration.py`; 기존 21응답, UTC→KST 날짜 분리, known 보존, 반복 0건, 동일 구 세션 추가 후 재이전, 날짜 없는 진도 표시 |
| 모바일·긴 단어/예문 | Chromium 375×812에서 긴 단어와 예문, body 너비 375 검증; 데스크톱 1440×1100 및 모바일 스크린샷 직접 검토 |
| 구조 제약 | FastAPI/SQLAlchemy, Nuxt 3/TS, ssr:false 유지. nginx 정적 + 호스트 FastAPI 1워커 배포 구성 변경 없음 |
| 문서 | `calendar-plan.md`, `calendar-migration.md`, README, AGENTS 갱신 |

## 실행 결과

- `back`: 가상환경 `python -m pytest -q` — 20 passed. 테스트 DB는 실행 종료 후 제거.
- `front`: `npm run typecheck` — 통과.
- `front`: `npm run generate` — 통과, `.output/public`에 `/`, `/progress` 등 정적 페이지 생성.
- 루트: `back/.venv/Scripts/python.exe scripts/verify_browser.py` — Playwright 복합 사용자 흐름 1 passed. 브라우저 pageerror 0건. API 통신은 실제 임시 PostgreSQL을 사용하는 로컬 FastAPI로 진행.
- 임시 DB/역할을 PostgreSQL에서 조회하여 잔존하지 않는 것을 확인.

## 화면

- [데스크톱 달력](screenshots/calendar-desktop.png)
- [모바일 달력](screenshots/calendar-mobile-initial.png)
- [모바일 긴 예문 카드](screenshots/card-mobile.png)
- [학습 완료 후 모바일 전체 기록](screenshots/calendar-mobile.png)

## 한계와 배포 시 확인

- 운영 DB 원본으로 이전·복원을 실행한 것은 아니다. 운영 전환 시 백업 복원과 실제 기록 수를 대조해야 한다. 구 프론트와 새 API는 함께 교체한다.
- 과거 복습 원본 날짜와 응답이 없는 진도의 학습 날짜는 추측하지 않는다. 상세는 이전 문서 참고.
- 브라우저 검증 대상은 Chromium과 Nuxt dev proxy다. 정적 생성은 별도로 검증했으며 EC2 nginx 경유 운영 검증은 배포 범위에 속한다.
- 의존 라이브러리의 Starlette/httpx·anyio 사용 중단 예정 경고 2건과 Nitro 정적 생성의 cache-driver 외부 의존 경고가 출력되었다. 테스트·타입 검사·정적 생성은 성공했다. Node의 색상 환경변수 경고도 있으나 브라우저 앱 오류는 없었다.
