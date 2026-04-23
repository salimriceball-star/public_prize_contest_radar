# daily-update+cron__2026-04-23-1127__passed

- 일시: 2026-04-23 11:27 UTC.
- 목표: 공모전 레이더를 매일 22:00 KST 1회 신규 소식 업데이트로 전환.
- 수정: `/home/vboxuser/public_prize_contest_radar/{config/schedule.yaml,scripts/daily_contest_update.sh,src/contest_radar/{schedule.py,cli.py,pipeline.py,storage.py},config/sources.yaml,tests/*,README.md,docs/ops-plan.md,progress.md}`.
- 핵심: cron `0 13 * * *` 단일화, daily script 기본 `--new-only --notify`, run_once `new_records` 추가, DACON/K-Startup generic false positive 필터.
- 검증: unittest discover 32 OK; daily script temp DB smoke OK; crontab managed block 1개/22:00 KST 확인.
- 다음: Thinkyou/K-Startup WebSocketConnectionClosedException 빈도 관찰 및 source별 추가 튜닝.
