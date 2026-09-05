# 오늘 학습 개수 누적 표시 검증

2026-09-06 Windows 로컬. 운영 DB 접근 없이 임시 PostgreSQL DB와 합성 데이터로 확인했다.

## 변경 동작

- `/v1/today` 조회·제출 응답에 `new_count`, `review_count`를 추가한다. 오늘(KST) `study_batch` 완료일 기준으로 저장된 신규·복습 수이며, 없으면 0이다.
- 학습 카드는 `오늘 총 N개 · 신규 X개 · 복습 Y개`를 서버 집계로 표시한다.
- 저장 안내도 서버 집계 합계를 사용한다. 예: `오늘 N개 학습을 저장했어요. 언제든 돌아가도 기록은 남아요.`
- 브라우저에서 개수를 임의로 올리지 않으므로 새로고침, 달력 왕복, 동일 UUID 재시도, 날짜 변경에도 중복 증가하지 않는다.

## 실행 결과

| 확인 | 결과 |
| --- | --- |
| `back`: `.venv/Scripts/python.exe -m pytest -q -p no:cacheprovider` | 44 passed |
| `front`: `npm run typecheck` | 통과 |
| `front`: `npm run generate` | 통과, `.output/public` 생성 |
| 루트: `back/.venv/Scripts/python.exe scripts/verify_browser.py` | Playwright 4 passed |
| `git diff --check` | 통과 |

백엔드는 0개, 한 단어 연속 저장, 묶음 저장, `/extra` 별칭, 신규·복습 분리, 이전 날짜 제외, 당일·자정 이후 동일 재시도, 거절 시 증가 없음, 달력 집계 일치를 검증했다.

브라우저 검증은 실제 로컬 FastAPI와 임시 DB로 신규 15개·복습 20개까지 1→35 누적을 확인했다. 응답 손실 뒤 같은 요청으로 재시도해도 2에서 멈추고, 복습 재개와 달력·날짜별 기록 일치, 새로고침 후에도 숫자가 유지됨을 확인했다. 합성 API 테스트는 1440×1100과 375×812에서 카드 개수와 안내 문구 증가, 재진입, 409 복구, 자정 이후 재시도의 서버 날짜 집계를 검증한다. 가로 넘침이 없음을 확인하고 스크린샷을 직접 검토했다. 임시 DB는 검증 스크립트 종료 시 정리된다.

## 화면

- [모바일 신규 카드](screenshots/single-word-new-375.png)
- [데스크톱 복습 카드](screenshots/single-word-review-1440.png)
- [모바일 누적 기록](screenshots/calendar-mobile.png)

## 운영 반영

이 문서의 테스트는 로컬 검증이다. 이후 2026-09-06 같은 코드로 백엔드와 정적 프론트를 운영에 반영했다. 상세는 [배포 기록](today-count-deployment.md)을 참고한다.

기존 Starlette/httpx·anyio 사용 중단 예정 경고 2건, Nitro cache-driver 경고, Node 색상 환경변수 경고와 Nuxt `#app-manifest` pre-transform 경고가 남아 있지만 최종 테스트와 빌드는 성공했다.
