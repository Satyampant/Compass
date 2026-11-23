# Phase 4 acceptance

Automated checks: `make test` (includes `tests/test_speed.py`, `tests/test_status.py`, `tests/test_export.py`, `tests/test_settings.py`) and `make e2e` (includes the extension, settings, status and section 09 situations).

## PRD section 09, situation by situation

| Situation | Where it is checked |
|-----------|---------------------|
| First day, nothing saved: one prompt, no empty charts | e2e `test_edges.py::test_first_day_shows_one_prompt_and_no_goal_fields` |
| No goals yet: goal fields hidden | same test, and quick capture shows no goal picker |
| Mac closed for a weekend: one combined brief | `tests/test_reminders.py::test_two_day_sleep_gives_one_message` |
| Mac closed for more than a day: unsaved links need sharing again | By hand: Telegram keeps messages 24 hours; a message without "Saved" in the chat was not stored |
| Nothing fits a slot: block stays open, reminder suggests the shortest item | `tests/test_reminders.py::test_open_slot_reminder_suggests_the_shortest_inbox_item` |
| A meeting lands on a slot: moves, or not kept and the item returns to the list | `tests/test_protect.py`, `tests/test_fill.py::test_slot_lost_to_a_meeting_returns_its_item_to_the_list` |
| More than three nudges: three by priority | `tests/test_acceptance_p0.py` |
| A fourth task ranked: asked which it replaces | e2e `test_goals.py::test_top_three_focus_and_trace` |
| A goal deleted: tasks untied, children ask for a parent | `tests/test_goals_api.py`, e2e `test_edges.py::test_deleting_a_goal_asks_its_children_for_a_new_parent` |
| Travelling: days stay on Asia/Kolkata until changed | The `timezone` setting on the Settings screen |
| A page title cannot be fetched: raw link, can be renamed | e2e `test_edges.py::test_rename_an_item_whose_title_could_not_be_fetched` |

## By hand

| # | Check | Pass when |
|---|-------|-----------|
| 1 | Load the extension (README), open any article and click the Compass button. | The badge shows SAVE and the article is in the inbox. Click again: DUP, still one card. |
| 2 | Open Status. | Every row is OK the morning after a normal day. |
| 3 | Leave the Mac off for a day and a half, then open Status. | The backup row shows Check until the next morning run. |
| 4 | Status, Download all data. Load it into a scratch database (`COMPASS_DB_URL=sqlite:////tmp/x.db uv run python -m app.modules.system.export load FILE`) and open the app on it. | The same goals, tasks and queue. |
| 5 | Settings: change a learning slot time and save. | Within a minute the Compass calendar shows the new slot times. |
| 6 | Use only the keyboard for a morning: C to capture, Tab and Enter on tasks, the day picker in a task, Space and arrows on the boards. | Every action you need has a keyboard path. |
