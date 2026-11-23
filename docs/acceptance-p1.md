# Phase 1 acceptance

Automated checks: `make test` (includes `tests/test_acceptance_p1.py`) and `make e2e`.
The checks below need your goals, your phone or five real days, so they are done by hand.

## Once

1. Install Google Drive for desktop and pick a folder for backups, then run
   `uv run python -m app.kernel.backup set-dir "<that folder>"` and `make restart`.
2. Open http://localhost:8000. On Today, press **Start setup**.

## Checks

| # | Check | Pass when |
|---|-------|-----------|
| 1 | Run guided setup with your real themes, quarter goals, milestones and this week's outcomes. Time it. | Done in 15 minutes or less. |
| 2 | On This quarter, click a key result's number and change it. | The goal's percentage changes at once, and again after a reload. |
| 3 | Open a task on Today that serves a goal. | The trace shows its chain, and one click on the year step opens This year. |
| 4 | On This week, drag a task to another day. | Both day totals change at once. |
| 5 | Plan more than 40 hours into the week. | The total turns into a warning. |
| 6 | Send `/today` and `/queue` to the bot from the phone with the Mac awake. | `/today` lists the top three and the next block. `/queue` gives the inbox count and today's list. |
| 7 | Start a third learning item. | Compass asks you to finish or return one first. |
| 8 | Next morning after a backup, run `make restore BACKUP=<that folder>/compass-<yesterday>.db INTO=/tmp/compass-restore` and open the app on the copy as printed. | Your goals and tasks are there. |

## Five real days

For five days, use **Plan tomorrow** each evening and close the day with the shutdown card.

| Day | Planned the evening before | Closed with a learned line |
|-----|----------------------------|-----------------------------|
| 1 | | |
| 2 | | |
| 3 | | |
| 4 | | |
| 5 | | |
