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

3. master id 탐색
   export TELEGRAM_BOT_TOKEN='...'
   python3 -m contest_radar.cli resolve-master-id

4. 1회 수집 + 점수화 + digest 출력
   python3 -m contest_radar.cli run-once --top 10

5. Telegram 전송
   export TELEGRAM_MASTER_ID='123456789'
   python3 -m contest_radar.cli run-once --top 10 --notify

주요 문서
- docs/project-brief.md
- docs/ops-plan.md
- config/categories.yaml
- config/sources.yaml
- data/seed_institutions.csv
- data/past_results.sample.csv

주의
- Bot API는 개인 DM 전송에 chat id가 필요하다. 현재 세션에서는 getUpdates 결과가 비어 있어 master id를 자동 확정하지 못했다. bot에 /start 또는 아무 메시지를 보낸 뒤 resolve-master-id 명령을 다시 실행하면 수집 가능하다.
- 프로젝트 규칙은 agents.md를 따른다.
