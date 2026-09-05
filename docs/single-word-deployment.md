# 한 단어 저장 운영 배포

2026-09-06 KST, `https://yangyag4.duckdns.org`에 반영 완료.

## 버전과 실행 구성

- 앱 코드: `5e84750` — 한 단어씩 저장하고 신규 학습과 복습 평가를 구분한다.
- 이전 코드: `95c3333`. 이전 프론트 이미지 `english-front:calendar-20260905` 보존.
- 새 프론트: `english-front:single-word-20260906`, 실행 이미지 ID `sha256:b22283c6369acd66d556f2d78d2e86b9eb35762657d9136961e5e754049bfc8e`.
- 로컬 `nuxt generate`와 `docker build --platform linux/amd64` 후 tar 전송·EC2 `docker load`. EC2에서는 빌드하지 않았다.
- EC2 `/home/ubuntu/english`에서 `git pull --ff-only`, 호스트 venv의 FastAPI 시작, 기존 compose의 프론트 이미지 태그 교체 및 컨테이너 재생성.
- `english-back.service` active, 단일 uvicorn worker, MemoryMax 192MiB. 프론트 컨테이너 healthy, 64MiB 제한 유지.
- 실제 기존 PostgreSQL 컨테이너는 `yangyag-postgres`다. 문서의 과거 `auto-postgres` 표기를 현재 상태에 맞췄다. DB 컨테이너를 추가하지 않았다.

## 백업과 기록 보존

영어 서비스의 쓰기를 중단한 상태에서 `english` 스키마만 custom-format pg_dump로 백업했다. 위치는 EC2 `/home/ubuntu/english/backups/single-word-20260906/`이며 디렉터리는 700, dump는 600 권한이다. DB 덤프, 이전 compose, 코드 리비전, 이전 이미지 ID와 변경 전후 체크섬을 보관한다. `backups/`는 Git에서 제외한다.

백업을 별도 임시 로컬 DB로 복원하고 새 `init_db`를 두 번 실행했다. 복원 전후 및 반복 이전 후의 6개 테이블 전체 행 체크섬과 next_rank가 모두 같았다. 운영에서도 nullable 변경 직후 같은 검사를 통과했다.

| 항목 | 변경 전후 |
| --- | --- |
| word | 6,000행, 내용 동일 |
| study_state | 1행, 내용 동일 |
| study_session | 5행, 내용 동일 |
| word_result | 60행, 내용 동일 |
| study_batch | 5행, 내용 동일 |
| batch_result | 70행, 내용 동일 |
| 다음 신규 순위 | 51 유지 |
| 누적 신규 / 공부한 날 | 50개 / 3일 유지 |

`batch_result.known`은 NULL 허용으로 전환했으며 기존 true/false 값은 변경하지 않았다. 백업 복원용 임시 로컬 DB는 검증 종료 후 제거했다.

## 검증

- 배포 전 백엔드 29개, Playwright 3개, 타입 검사와 정적 생성 통과. [로컬 검증](single-word-verification.md).
- EC2에서 앱 Python 컴파일 및 실제 백업 기준 스키마 이전·체크섬 검증 통과.
- 공개 HTTPS의 `/v1/health` 정상, `/v1/progress`의 50개·다음 순위 51 확인.
- 실제 HTTPS 사이트를 Chromium 1440×1100 및 375×812로 열어 신규 `학습 완료`, 복습 `기억나요 / 기억 안 나요`, 달력 복귀와 진도 화면을 확인했다. 가로 넘침 없음, 브라우저 pageerror 0건.
- 운영 브라우저 검증은 GET만 허용하여 학습 기록을 만들지 않았다. 한 단어 저장과 중복 재시도는 임시 DB 통합 테스트에서 검증했다.

## 복구 시 유의점

기존 이미지와 DB 백업은 남겨 두었다. 새 버전에서 학습한 뒤에는 신규 NULL 결과와 전진한 진도를 보존해야 하므로 이전 코드나 DB를 단순 덮어쓰지 않는다. 현재 상태를 별도 백업하고 [이전·복구 절차](calendar-migration.md)에 따라 처리한다.
