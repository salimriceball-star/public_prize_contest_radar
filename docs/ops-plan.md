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

미해결 사항
- 일부 공공 사이트는 anti-bot 또는 접속 제한이 있어 source 설정 튜닝이 필요함
