# Public Prize Contest Radar Ops Plan

일일 루틴
1. 등록된 소스 페이지를 수집한다.
2. anchor/link 기반 후보를 추출한다.
3. 키워드로 트랙을 분류한다.
4. 점수화 규칙으로 우선순위를 계산한다.
5. 중복 공고를 병합한다.
6. 상위 N개만 digest 로 렌더링한다.
7. Telegram 알림 또는 stdout 으로 전달한다.
8. 결과를 SQLite DB 와 CSV export 에 누적한다.

주간 루틴
- seed 기관 목록 갱신
- 과거 수상작/결과 페이지 수집 보강
- 반복 개최 여부 재평가
- 감점 규칙과 제외 규칙 미세 조정

핵심 운영 파일
- `config/categories.yaml`
- `config/sources.yaml`
- `data/seed_institutions.csv`
- `data/past_results.sample.csv`
- `data/contest_radar.sqlite3`

알림 구조
- digest: 매일 상위 후보 3~10개
- due-soon: 마감 7일/3일/1일 전 경보
- manual-review: 약관/저작권/지역제한 확인 필요 항목 표시

Telegram 운영 기준
- 현재 master id: `779460653`
- 식별 기준: private chat `@Rktan6` / display name `낙관적인 비관론자`
- notifier 는 `TELEGRAM_BOT_TOKEN` 과 `TELEGRAM_MASTER_ID=779460653` 조합을 기본 운영값으로 사용한다.
- token 값은 `.local/runtime.env` 또는 실행 환경변수에만 저장하고 문서/로그/커밋에 기록하지 않는다.

BrowserOS/CDP 운영 기준
- 동적/차단성 목록은 `browseros_anchor_scan`으로 수집하고 상세 페이지는 `browseros_detail`로 보강한다.
- `config/runtime.yaml`의 기본값은 `iteration_budget: 9999`, `reuse_existing_tabs: true`, `close_new_tabs_after_use: true`다.
- 새로 연 CDP 탭은 기본적으로 닫아 탭 누적/메모리 압박을 막는다. 기존 탭을 재사용한 경우에는 사용자의 기존 탭을 닫지 않는다.
- `127.0.0.1:9200/health`가 내려가도 `127.0.0.1:9100/json/version`이 응답하면 BrowserOS 사용 가능 상태로 본다.
- CDP websocket 연결은 origin 거절을 피하기 위해 `suppress_origin=True`를 사용한다.

스케줄/cron 운영 기준
- 기준 시간대는 Asia/Seoul이며 `config/schedule.yaml`은 UTC cron 식을 함께 보관한다.
- 공식 반복 작업은 `python3 -m contest_radar.cli render-crontab` 출력 block을 사용자 crontab에 설치한다.
- 현재 작업은 매일 22:00 KST(`0 13 * * *` UTC) 1회 `scripts/daily_contest_update.sh` 실행이다.
- daily script는 기본적으로 `run-once --new-only --top 10 --public-only --min-score 40 --notify`를 호출해 신규로 DB에 들어온 공공형 후보만 Telegram digest로 보낸다.
- 중복 방지는 SQLite `contests.url` 캐시 기준이다. 매 실행 시작 시 기존 URL을 로드하고, 이미 본 URL은 상세 BrowserOS/CDP fetch와 upsert/알림 대상에서 제외한다.
- cron 로그는 `logs/cron/daily-contest-update.log`에 쌓으며 git 추적 대상이 아니다.

미해결 사항
- 일부 공공 사이트는 anti-bot 또는 접속 제한이 있어 source 설정 튜닝이 필요함
