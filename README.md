# Public Prize Contest Radar

AI 기반 공공형 상금 공모전 모니터링 시스템.

이 프로젝트는 “플랫폼 나열”이 아니라 “어장 지도”에 초점을 둔다. 목표는 세상의 모든 공모전을 모으는 것이 아니라, 내가 실제로 이길 확률이 높은 공공기관·지자체·공공데이터·AI·영상형 공모전이 어디서 반복적으로 나타나는지 추적하고, 그중 지원 가치가 높은 후보만 Telegram으로 보내는 것이다.

핵심 기능
- 과거 공모전 DB용 SQLite 스키마
- 원문 발생지/재게시 포털/결과 발표 링크 분리 저장
- 키워드 기반 트랙 분류
- 상금/적합도/AI 활용성/반복 개최/공공성/준비 부담 기반 점수화
- 공개투표/저작권 독소조항/오프라인 부담/저효율 유형 감점
- 포털/공식 사이트 anchor scan 기반 수집기
- Telegram digest 전송 및 master id 자동 탐색 도구
- seed 기관/과거 수상 이력 CSV 템플릿

현재 기본 포함 소스
- Thinkgood
- Wevity
- Linkareer
- Thinkyou
- Contest Korea
- DACON
- K-Startup
- 공공 seed 기관용 템플릿 엔트리

빠른 시작
1. Python 경로 설정
   export PYTHONPATH=/home/vboxuser/public_prize_contest_radar/src

2. DB 초기화
   python3 -m contest_radar.cli init-db

3. master id 탐색/확인
   export TELEGRAM_BOT_TOKEN='***'
   python3 -m contest_radar.cli resolve-master-id
   현재 확인된 master id: 779460653

4. 1회 수집 + 점수화 + digest 출력
   python3 -m contest_radar.cli run-once --top 10

5. Telegram 전송
   export TELEGRAM_MASTER_ID='779460653'
   python3 -m contest_radar.cli run-once --top 10 --notify

6. BrowserOS/CDP 수집 1회 검증
   python3 -m contest_radar.cli run-once --source-id thinkcontest-home --top 5 --public-only --min-score 40

7. 운영 스케줄 확인
   python3 -m contest_radar.cli show-schedule
   python3 -m contest_radar.cli render-crontab

운영 설정
- `config/runtime.yaml`: BrowserOS 반복 예산, 기존 탭 재사용, 새 탭 자동 닫기, 공공형/최소점수 기본 운영값을 둔다.
- `config/schedule.yaml`: Asia/Seoul 기준 매일 10:00 KST 1회 업데이트 작업을 UTC cron 식으로 보관한다.
  - 10:00 KST / 01:00 UTC: 신규 공공형 공모전만 추려 digest 알림
- `scripts/run_radar.sh`: 공통 CLI 실행 진입점이며 `.local/runtime.env`가 있으면 로드한다.
- `scripts/daily_contest_update.sh`: cron에서 매일 실행하는 신규 공모전 업데이트 스크립트다. 기본값은 `run-once --new-only --top 10 --public-only --min-score 40 --notify`다.
- 이미 확인한 공모전 URL은 SQLite `contests.url` 캐시로 기억한다. 다음 실행 때는 목록에서 같은 URL을 발견해도 상세 페이지 재방문/재점수화/재알림을 건너뛴다.
- BrowserOS/CDP는 `127.0.0.1:9100`을 기본 사용한다. `127.0.0.1:9200/health`가 내려가도 CDP `/json/version`이 살아 있으면 수집을 계속한다.
- Telegram bot token, GitHub PAT 등 민감값은 `.local/` 또는 환경변수에만 두고 문서/커밋에 기록하지 않는다.

주요 문서
- docs/project-brief.md
- docs/ops-plan.md
- config/categories.yaml
- config/sources.yaml
- data/seed_institutions.csv
- data/past_results.sample.csv

주의
- Bot API는 개인 DM 전송에 chat id가 필요하다. 현재 이 프로젝트의 확인된 Telegram master id 는 `779460653` 이다.
- `resolve-master-id` 명령은 향후 bot 업데이트가 바뀌었는지 점검할 때 계속 사용할 수 있다.
- 프로젝트 규칙은 agents.md를 따른다.
