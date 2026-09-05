# 한 단어 저장 검증

2026-09-06 Windows 로컬. 운영 DB 접근·배포 없이 임시 PostgreSQL DB와 합성 데이터로 확인했다.

## 변경 동작

- 신규는 뜻·예문을 확인한 뒤 `학습 완료`를 누르면 한 단어 저장. `known=NULL`로 평가 없음 표시.
- 복습은 `기억나요 / 기억 안 나요`를 눌러 한 단어 저장. true/false 응답은 이후 분석에 사용할 수 있도록 보존.
- 저장 성공 후 다음 카드로 이어진다. 한 단어만 완료하고 달력으로 돌아가도 신규·복습 개수와 단어가 표시된다.
- 저장 확인 전 응답은 localStorage에 보관한다. 응답 손실·새로고침 이후 동일 UUID·내용으로 재시도하며 다음 카드 이동은 성공 이후에만 한다. 확인되지 않은 응답이 있을 때는 달력으로 돌아가기 대신 저장 재시도를 제공한다.
- 날짜 또는 다음 학습 순위가 바뀌어 409를 받으면 최신 기록을 불러와 다시 시작할 수 있다.
- API는 다음 목록의 연속된 앞부분 1~10개를 허용한다. 기존 10개 제출도 지원하되 신규 불리언 평가는 NULL로 저장한다.
- 기존 저장 응답은 변경하지 않는다. 시작 시 `batch_result.known`의 NOT NULL 제약만 반복 가능하게 해제한다. [이전 안내](calendar-migration.md).

## 실행 결과

| 확인 | 결과 |
| --- | --- |
| `back`: `.venv/Scripts/python.exe -m pytest -q -p no:cacheprovider` | 29 passed |
| `front`: `npm run typecheck` | 통과 |
| `front`: `npm run generate` | 통과, `.output/public` 생성 |
| 루트: `back/.venv/Scripts/python.exe scripts/verify_browser.py` | Playwright 3 passed |
| `git diff --check` | 통과 |

백엔드는 신규 NULL 저장, 한 단어 달력·진도, 복습 true/false 보존과 이어하기, 평가 없는 복습 거절, 순위 건너뛰기·중복 거절, 동시 제출, 자정 재시도 및 기존 응답을 유지하는 스키마 이전을 검증했다.

브라우저 통합 테스트는 실제 로컬 FastAPI와 임시 DB로 신규 1개 기록, 저장 후 응답 손실·재시도, 복습 1개 후 재개, 신규 15개·복습 20개 완료와 누적 35개를 확인했다. 별도의 합성 API 테스트는 1440×1100 및 375×812에서 버튼 구분, 같은 요청 재시도, 409 복구를 검증한다. 긴 단어·예문과 달력의 가로 넘침이 없음을 확인하고 스크린샷을 직접 검토했다. 임시 DB는 검증 스크립트 종료 시 정리된다.

## 화면

- [모바일 신규 카드](screenshots/single-word-new-375.png)
- [데스크톱 복습 카드](screenshots/single-word-review-1440.png)
- [모바일 한 단어 기록](screenshots/single-word-calendar-375.png)

## 운영 반영

이 문서의 테스트는 로컬 검증이다. 이후 2026-09-06 운영 백업 복원 검증, nullable 이전과 정적 프론트 전환까지 완료했다. 상세는 [배포 기록](single-word-deployment.md)을 참고한다. 구 v2 미제출 묶음은 자동 제출하지 않고 저장된 진도부터 다시 시작하도록 안내한다.

기존 Starlette/httpx·anyio 사용 중단 예정 경고 2건, Nitro cache-driver 경고, Node 색상 환경변수 경고가 남아 있지만 최종 테스트와 빌드는 성공했다.
