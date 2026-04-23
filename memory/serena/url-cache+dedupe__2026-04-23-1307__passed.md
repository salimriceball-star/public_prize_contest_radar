# url-cache+dedupe__2026-04-23-1307__passed

- 일시: 2026-04-23 13:07 UTC.
- 목표: 이미 확인한 공모전 링크를 기억하고 중복 상세확인/알림 방지.
- 수정: `/home/vboxuser/public_prize_contest_radar/src/contest_radar/{pipeline.py,collectors.py,browseros_collectors.py,storage.py}`, `tests/{test_pipeline.py,test_browseros_parsing.py}`, `README.md`, `docs/ops-plan.md`, `progress.md`.
- 핵심: SQLite `contests.url`에서 known URL 캐시 로드, collector에 전달, cached URL은 listing 이후 detail fetch/score/upsert/notify skip. 현재 cron은 매일 22:00 KST(`0 13 * * *`) 1회.
- 검증: unittest discover 35 OK; Thinkcontest `--new-only` smoke -> 새 후보 없음; cache rows 46.
- 다음: source별 신규 false positive와 WebSocketConnectionClosedException 빈도 관찰.
