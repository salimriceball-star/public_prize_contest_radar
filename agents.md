# Public Prize Contest Radar Agent Rules

이 프로젝트에서는 아래 규칙을 항상 따른다.

## Canonical Context

- 프로젝트 핵심 문서는 아래 파일을 기준으로 유지한다.
- `/home/vboxuser/public_prize_contest_radar/docs/project-brief.md`
- `/home/vboxuser/public_prize_contest_radar/docs/ops-plan.md`
- `/home/vboxuser/public_prize_contest_radar/progress.md`
- 사용자가 정의한 핵심 트랙은 공공기관·지자체 정책/아이디어 제안형, 시민참여혁신단·국민평가단·모니터링단, 공공홍보 숏폼/영상/UCC, 공공데이터·AI·창업/경진대회형, 서포터즈/플레이어/선정형 활동이다.
- 상금 획득을 목표로 할 때는 1~4번을 본진, 5번을 보조 트랙으로 유지한다.
- 시스템 설계의 기준은 “모든 공모전 수집”이 아니라 “내가 실제로 이길 확률이 높은 공공형 상금 공모전 레이더”다.

## Scope Discipline

- 이 프로젝트의 현재 범위는 문서만이 아니라 실제 모니터링 코드, 점수화 로직, 중복 제거, SQLite 저장, Telegram 알림, 운영 스크립트까지 포함한다.
- 실제 운영 범위에는 과거 공모전 DB 구조화, 핵심 소스 수집, 일일 digest 생성, 마감 임박 알림, seed 기관 확장, 반복 개최 추적이 포함된다.
- 문서를 수정할 때는 현재 구현된 자동화 플로우와 어긋나지 않게 유지한다.

## Git Discipline

- 주요 작업 단위가 끝나면 즉시 commit 하고 push 한다.
- 커밋 메시지는 변경 목적이 드러나는 conventional-style 요약을 우선한다.
- 문서만 수정한 경우에도 운영 기준이 바뀌면 commit/push 대상에 포함한다.

## Data Rules

- 우선 감시 대상은 공공기관·지자체·정부부처·공공데이터·공공홍보 성격이 강한 공모전이다.
- 저효율 필터는 순수 이벤트형, 상금이 너무 작고 제출물이 무거운 유형, 공개투표 의존형, 저작권 독소조항형, 과도한 오프라인 부담형을 우선 제외한다.
- 원문 발생지, 재게시 포털, 결과 발표 페이지, 수상작 링크를 가능한 한 분리 저장한다.
- 수상작/종료 이력은 현재 모집 공고보다 더 중요한 히스토리 데이터로 취급한다.

## GitHub

- GitHub 원격 저장소를 사용할 경우 전용 저장소를 새로 생성하는 것을 기본안으로 둔다.
- PAT token 로컬 파일 경로는 `/home/vboxuser/public_prize_contest_radar/.local/github_pat.txt` 로 고정한다.
- PAT 값 자체를 문서에 적지 말고 로컬 파일에서 읽어 사용한다.
- PAT 보관 파일과 기타 로컬 비밀 파일은 반드시 gitignore 대상이어야 한다.

## Memory

- memory 루트는 `/home/vboxuser/public_prize_contest_radar/memory` 로 고정한다.
- Serena memory 저장 경로는 `/home/vboxuser/public_prize_contest_radar/memory/serena` 로 고정한다.
- 항상 작업 마지막에 Serena memory를 업데이트한다.
- Serena memory 파일명은 `키워드__YYYY-MM-DD-HHmm__상태.md` 형식을 따른다.
- 키워드는 소문자, 숫자, 하이픈만 사용하고 여러 키워드는 `+` 로 연결한다.
- 상태는 `plan`, `wip`, `passed`, `failed`, `blocked`, `rolledback`, `mixed`, `skipped` 중 하나만 사용한다.
- Serena memory는 300토큰 이내 초압축 형식으로만 기록한다.
- Serena memory에는 아래만 기록한다.
- 작업 일시
- 작업 배경 및 목표
- 수정된 파일 목록(절대경로)
- 주요 변경 사항 상세 설명
- 검증 결과(로그, 테스트 결과)
- 참조 문서/memory
- 다음 단계 또는 known issues
