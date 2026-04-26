# 2026-04-26 18:39 UTC — BrowserOS tab cleanup passed

- 목표: BrowserOS/CDP 사용 후 공모전 탭이 남아 메모리를 점유하는 문제 수정 + 현재 열린 공모전 탭 정리.
- 수정:
  - `/home/vboxuser/public_prize_contest_radar/src/contest_radar/browseros_cdp.py`
  - `/home/vboxuser/public_prize_contest_radar/tests/test_browseros_cdp.py`
- 핵심: `CDPPageSession.close()`가 기본적으로 reused 탭도 `/json/close/<id>`로 닫음. `close_tabs_after_use`/기존 `close_new_tabs_after_use` false면 비활성, `preserve_reused_tabs_after_use` true면 reused 보존.
- 정리: BrowserOS 공모전 관련 탭 36개 닫음. Instagram/Threads 보존. 최종 `remaining_contest_related_tabs=0`.
- 검증: reused 수동 탭 `matching_before=1 -> after=0`; unittest 44 OK; compileall OK; diff check OK; 보안 스캔 무 findings; 독립 리뷰 approve.
- 커밋: `f99ddee fix: close reused BrowserOS tabs after use` pushed to `origin/main`.
