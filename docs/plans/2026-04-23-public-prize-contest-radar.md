# Public Prize Contest Radar Implementation Plan

> **For Hermes:** Use subagent-driven-development skill to implement this plan task-by-task.

**Goal:** Build a working contest-monitoring system that maps high-fit public-sector prize opportunities, scores them, stores them, and sends Telegram digests.

**Architecture:** A lightweight Python package will load source/category config, fetch anchor-heavy listing pages, normalize and classify items, score them with user-fit heuristics, store them in SQLite, and optionally notify via Telegram. The project will also mirror ai_persona-style GitHub and Serena memory discipline.

**Tech Stack:** Python 3.10+, sqlite3, argparse, urllib, BeautifulSoup4, PyYAML, shell scripts.

---

### Task 1: Create project scaffolding and canonical docs

**Objective:** Establish the repo structure, copied rules, and project docs before code work starts.

**Files:**
- Create: `/home/vboxuser/public_prize_contest_radar/agents.md`
- Create: `/home/vboxuser/public_prize_contest_radar/README.md`
- Create: `/home/vboxuser/public_prize_contest_radar/docs/project-brief.md`
- Create: `/home/vboxuser/public_prize_contest_radar/docs/ops-plan.md`
- Create: `/home/vboxuser/public_prize_contest_radar/progress.md`

**Step 1:** Copy the GitHub and Memory rules from `ai_persona/agents.md` and adapt only the project path.
**Step 2:** Record the radar scope, strong tracks, and exclusion logic.
**Step 3:** Add quickstart notes and unresolved master-id caveat.
**Step 4:** Commit the scaffold.

### Task 2: Define configuration and data contracts

**Objective:** Fix the schema for sources, categories, scoring, and seed data.

**Files:**
- Create: `/home/vboxuser/public_prize_contest_radar/config/categories.yaml`
- Create: `/home/vboxuser/public_prize_contest_radar/config/sources.yaml`
- Create: `/home/vboxuser/public_prize_contest_radar/data/seed_institutions.csv`
- Create: `/home/vboxuser/public_prize_contest_radar/data/past_results.sample.csv`
- Create: `/home/vboxuser/public_prize_contest_radar/src/contest_radar/models.py`

**Step 1:** Encode the five user-fit lanes and low-efficiency filter rules.
**Step 2:** Register verified source URLs plus tunable source metadata.
**Step 3:** Create CSV templates for future manual enrichment.
**Step 4:** Define dataclasses for raw listings, normalized contests, score breakdowns, and source specs.

### Task 3: Implement collectors and normalizers

**Objective:** Fetch pages, build stable links, and turn noisy anchors into raw contest candidates.

**Files:**
- Create: `/home/vboxuser/public_prize_contest_radar/src/contest_radar/config_loader.py`
- Create: `/home/vboxuser/public_prize_contest_radar/src/contest_radar/collectors.py`
- Create: `/home/vboxuser/public_prize_contest_radar/src/contest_radar/normalize.py`

**Step 1:** Load YAML config safely.
**Step 2:** Build an anchor-scan collector with source-specific filters.
**Step 3:** Add Thinkgood detail URL reconstruction using `data-contest_pk`.
**Step 4:** Normalize titles, URLs, source hostnames, and snippets.

### Task 4: Implement classification, scoring, storage, and reporting

**Objective:** Turn raw candidates into ranked opportunities with persistence.

**Files:**
- Create: `/home/vboxuser/public_prize_contest_radar/src/contest_radar/scoring.py`
- Create: `/home/vboxuser/public_prize_contest_radar/src/contest_radar/storage.py`
- Create: `/home/vboxuser/public_prize_contest_radar/src/contest_radar/reporting.py`
- Create: `/home/vboxuser/public_prize_contest_radar/src/contest_radar/pipeline.py`

**Step 1:** Encode the score weights from the spec.
**Step 2:** Detect public-sector, AI-fit, user-fit, repeat-host, and burden signals.
**Step 3:** Upsert results into SQLite and preserve raw JSON.
**Step 4:** Render Korean digests with score rationale.

### Task 5: Implement Telegram notification and CLI

**Objective:** Make the system usable from the terminal and ready for cron.

**Files:**
- Create: `/home/vboxuser/public_prize_contest_radar/src/contest_radar/telegram.py`
- Create: `/home/vboxuser/public_prize_contest_radar/src/contest_radar/cli.py`
- Create: `/home/vboxuser/public_prize_contest_radar/scripts/run_radar.sh`

**Step 1:** Add `resolve-master-id`, `send-test`, `init-db`, and `run-once` commands.
**Step 2:** Support `TELEGRAM_BOT_TOKEN` and `TELEGRAM_MASTER_ID` env vars.
**Step 3:** Emit clear warnings when getUpdates is empty.
**Step 4:** Add a cron-friendly shell wrapper.

### Task 6: Verify, commit, and push

**Objective:** Prove the build works, then push it to GitHub promptly.

**Files:**
- Create: `/home/vboxuser/public_prize_contest_radar/tests/test_scoring.py`
- Create: `/home/vboxuser/public_prize_contest_radar/tests/test_collectors.py`
- Create: `/home/vboxuser/public_prize_contest_radar/tests/test_telegram.py`

**Step 1:** Write hermetic unit tests using `unittest`.
**Step 2:** Run the test suite and a live `run-once` smoke test.
**Step 3:** Create a dedicated GitHub repository using the reused PAT.
**Step 4:** Commit and push immediately after verification.
