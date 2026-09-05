# 오늘 학습 개수 누적 표시 운영 배포

2026-09-06 KST, `https://yangyag4.duckdns.org`에 반영 완료.

## 버전과 실행 구성

- 앱 코드: `25b9cd6` — 오늘 학습 개수를 누적 표시한다.
- 이전 코드: `18a517e`. 이전 프론트 이미지 `english-front:single-word-20260906` 보존.
- 새 프론트: `english-front:today-count-20260906`, 실행 이미지 ID `sha256:28c7dd7fc4da96942c683152e99d9a7be43ee84bd97a5d3da537682f25f92c7c`.
- 로컬 `nuxt generate`와 `docker build --platform linux/amd64` 후 tar 전송·EC2 `docker load`. EC2에서는 빌드하지 않았다.
- EC2 `/home/ubuntu/english`에서 `git pull --ff-only`, 호스트 FastAPI 재시작, 기존 compose의 프론트 이미지 태그 교체 및 컨테이너 재생성. 교체 전 compose는 `docker-compose.yml.today-count-backup-20260906`으로 보관했다.
- `english-back.service` active, 단일 uvicorn worker. 프론트 컨테이너 healthy, 64MiB 제한 유지.

## 데이터 변경

이번 배포는 DB 스키마와 저장 로직을 바꾸지 않았다. 조회·제출 응답에 오늘(KST) 저장 집계 필드만 추가했다.

배포 직후 운영 확인값:

- `GET /v1/today`: `2026-09-06`, 신규 5개, 복습 0개.
- `GET /v1/progress`: 누적 신규 55개, 다음 순위 56, 공부한 날 4일.

## 검증

- 배포 전 백엔드 44개, Playwright 4개, 타입 검사와 정적 생성 통과. [로컬 검증](today-count-verification.md).
- EC2에서 앱 Python 컴파일 통과.
- 공개 HTTPS의 `/v1/health` 정상, `/v1/today`와 `/v1/progress` 정상.
- 운영 브라우저 검증은 학습 기록을 만들지 않는 조회만 사용했다. 실제 저장과 중복 재시도는 임시 DB 통합 테스트에서 검증했다.

## 복구 시 유의점

이전 이미지와 교체 전 compose 백업은 남겨 두었다. 새 버전에서 학습한 뒤에는 진도를 보존해야 하므로 이전 코드나 이미지를 단순 덮어쓰지 않는다. 현재 상태를 별도 백업하고 [이전·복구 절차](calendar-migration.md)에 따라 처리한다.
