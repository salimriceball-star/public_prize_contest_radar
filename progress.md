# Public Prize Contest Radar Progress

## Milestone 1: Project Foundation

- [x] 프로젝트 디렉터리 생성
- [x] `agents.md` 작성 및 ai_persona 기반 GitHub/Memory 규칙 반영
- [x] `.local/github_pat.txt` 를 기존 ai_persona PAT 파일로 연결
- [x] `docs/project-brief.md` 초안 작성
- [x] `docs/ops-plan.md` 초안 작성
- [x] `docs/plans/2026-04-23-public-prize-contest-radar.md` 작성
- [x] `memory/serena`, `logs`, `config`, `data`, `src`, `tests` 디렉터리 생성

## Milestone 2: Monitoring System Build

- [x] 소스 레지스트리 구성
- [x] 수집기 구현
- [x] 분류/점수화 구현
- [x] SQLite 저장 구현
- [x] Telegram notifier 구현
- [x] CLI 진입점 구현
- [x] 템플릿 CSV/운영 스크립트 작성
- [x] 테스트 및 실데이터 1회 검증
- [x] GitHub 원격 저장소 생성, commit, push

## Validation Snapshot

- [x] `PYTHONPATH=src python3 -m compileall src tests`
- [x] `PYTHONPATH=src python3 -m unittest discover -s tests -v` -> 7 tests OK
- [x] `PYTHONPATH=src python3 -m contest_radar.cli run-once --top 8 --save-output latest-digest.txt`
- [x] `PYTHONPATH=src python3 -m contest_radar.cli resolve-master-id --bot-token ...` -> master id `779460653` 확인

## Milestone 3: BrowserOS/CDP Ops Hardening

- [x] BrowserOS/CDP 기반 `browseros_anchor_scan` 소스 전환
- [x] 상세 페이지 title/date/content/deadline 파싱 및 SQLite 저장 필드 보강
- [x] schedule/runtime 설정 파일 추가
- [x] 새 CDP 탭 자동 닫기 및 `/json/version` health fallback 적용
- [x] D-7/D-3/D-1 마감 알림 렌더링 추가
- [x] cron block 렌더링 추가
- [x] 매일 10:00 KST 1회 신규 공모전 업데이트 스크립트/cron 전환
- [x] SQLite URL 캐시 기반 중복 링크 상세 재확인 skip 적용

## Latest Validation Snapshot

- [x] `PYTHONPATH=src python3 -m unittest discover -s tests -v` -> 35 tests OK
- [x] `PYTHONPATH=src python3 -m contest_radar.cli run-once --source-id thinkcontest-home --top 5 --public-only --min-score 40 --save-output browseros-e2e-thinkcontest-post-review.txt` -> BrowserOS/CDP 실제 수집 OK
- [x] `CONTEST_RADAR_NOTIFY=0 CONTEST_RADAR_DB=/tmp/... ./scripts/daily_contest_update.sh` -> daily script smoke OK
- [x] `crontab -l` -> managed block 1개, 10:00 KST daily-contest-update 설치 확인
