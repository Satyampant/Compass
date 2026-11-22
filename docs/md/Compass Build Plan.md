Compass

Build plan

[00Summary](#top)[01How to use this plan](#how)[02Roadmap](#roadmap)[03Stack and one-time setup](#setup)[04Phase 0: Core loop](#p0)[05Phase 1: Direction](#p1)[06Phase 2: Time](#p2)[07Phase 3: Reflection](#p3)[08Phase 4: Polish](#p4)[09Tests that matter most](#tests)[10Requirement coverage](#trace)

57 tasks\
Plan draft 1.0\
22 November 2026\
[PRD](https://claude.ai/artifact/PeJiQDsjxR2oFAPJkvnjb7)\
[Architecture study](https://claude.ai/artifact/KAEhFLs2tcLEagVw4KDifJ)\
[Mockup](https://claude.ai/artifact/FxuE9rP8meo8shUycYyyUF)

Task-by-task build plan

# Compass: the order to build it in

57 tasks in five phases, about 24.5 working days in all. Each task names what to build, what it needs first, which requirements it delivers and the check that says it is done.

Plan draft 1.057 tasksabout 24.5 days70 of 70 requirements covered

Ask

### Nothing blocks phase 0

The four product calls from the PRD are still open. The plan uses the answers I proposed, and none of them is needed before phase 1. The first thing only you can do is create the Telegram bot, before T0.10.

Carry

### How the plan is built

- One task is one sitting and ends with a check.
- Rules about time are tested with a fake clock.
- Each phase is used for a week before the next begins.
- Every requirement in the PRD maps to a task.

Risk

### The build becomes the hobby

A planner is a pleasant thing to keep improving and an easy way to avoid the work it was meant to organise. Phase 0 is about eight days. Ship it and use it before touching anything in phase 1.

01

## How to use this plan

The plan has 57 tasks in five phases. Each task is one sitting of focused work and ends with a check you can run. Nothing is left half-built between sittings.

| Rule | Why |
| --- | --- |
| One task at a time, in order of its “needs” | Every task builds on finished, tested ground. |
| A task is done when its check passes | “Done when” is written so there is no judgement call. |
| Anything involving time is tested with a fake clock | Resurfacing takes 23 days in real life and a second in a test. |
| Use each phase for a week before starting the next | A week of real use finds what a plan cannot. It also stops the build outrunning the habit. |
| Hand a task to an AI coding tool as written | Each row names what to build, what it depends on and how to check it. Attach the architecture study and the PRD for context. |

### Sizes

S is up to two hours, M is half a day, L is a full day. These assume you work with an AI coding tool and already know the stack. They are estimates to plan with, and the first phase will tell you how far off they are. The whole plan adds up to about 24.5 working days.

The boxes beside each task can be ticked. Ticks are remembered in this browser only, so treat them as a convenience and keep the real record in git.

02

## Roadmap

**Fig 1.** Five phases with a week of real use between each. The first phase is the largest because it carries the foundations every later phase stands on.

| Phase | Tasks | Effort | Finished when |
| --- | --- | --- | --- |
| P0 Core loop | 18 | 7.75 days | Share a link from your phone with the Mac closed. It is in the inbox when you open the lid, and back on your desk on day 3. |
| P1 Direction | 14 | 6.25 days | Every task on Today shows where it leads. The week board shows an overbooked day. The day can be closed. |
| P2 Time | 11 | 5 days | A learning block shows up in Google Calendar already filled, and Today shows meetings and blocks together. |
| P3 Reflection | 9 | 3.5 days | Sunday’s review opens with the week’s numbers in place, and closing it drafts next week. |
| P4 Polish | 5 | 2 days | Saving a tab takes one click, and you can see at a glance that everything ran. |

If time runs short, stop after any phase. Phase 0 alone fixes the forgetting problem. Phases 0 and 1 together fix both problems by hand, and the later phases automate and measure.

03

## Stack and one-time setup

The stack follows the architecture study. Versions are whatever is current and stable when you start.

| Layer | Choice | Used for |
| --- | --- | --- |
| Language and API | Python, FastAPI | The one process: API, scheduler, static files |
| Database | SQLite in write-ahead mode, SQLAlchemy, Alembic | All data, jobs and events, with migrations |
| Outbound calls | httpx | Telegram and Google Calendar, with no bot framework in between |
| Tests | pytest with a replaceable clock | Every rule that depends on time |
| Web | React, TypeScript, Vite | The seven screens |
| Server data in the client | TanStack Query | Caching and optimistic updates |
| Drag and drop | dnd-kit | The queue board and the week board |
| Secrets | macOS Keychain through the keyring library | The Google refresh token |
| Start at login | launchd LaunchAgent | Keeping the process up |

### Things only you can do

| Step | Before | Takes |
| --- | --- | --- |
| Create the bot with BotFather in Telegram and copy its token into the local settings file | T0.10 | 5 minutes |
| Install Google Drive for desktop and choose the backup folder | T1.13 | 10 minutes |
| Create a Google Cloud project, enable the Calendar API and make a desktop client | T2.1 | 20 minutes |
| Turn on FileVault if it is not already on | T0.17 | 5 minutes |

04

## Phase 0: Core loop

18 tasks7.75 days

**Finished when:** Share a link from your phone with the Mac closed. It is in the inbox when you open the lid, and back on your desk on day 3.

**Fig 2.** Phase 0 in three lanes. An arrow means the task at its tail must be finished first. Once the kernel is done, the Telegram and web lanes can each move as soon as the core task above or below them is finished.

In this phase “book” stores a date and time you pick. Real calendar slots replace that in phase 2, and the screens do not change.

| Task | What to build | Links | Size |
| --- | --- | --- | --- |
| [ ] T0.1 | Repository and toolingCreate the folder layout from the architecture study, the Python project file, lint, tests and one `make dev` command.**Done when**`make dev` serves `/healthz` and `make test` passes with one sample test. | **Needs** nothing | S |
| [ ] T0.2 | Database and migrationsSQLite in write-ahead mode, a session helper and migrations. First tables: captures, learning_items, tasks, events, jobs, settings, daily_logs.**Done when**A fresh checkout builds the database from migrations, and a test writes and reads each table. | **Needs** T0.1 | M |
| [ ] T0.3 | Clock and settingsOne clock that tests can replace, “today” and “this week” in Asia/Kolkata, and a settings store seeded with the PRD defaults.**Done when**A test moves the clock across midnight IST and “today” changes. Every rule in PRD section 08 has a default. | **Covers** SYS-3 **Needs** T0.2 | S |
| [ ] T0.4 | Event logA helper that appends an event in the same transaction as the change that caused it.**Done when**A rolled-back change leaves no event behind. | **Needs** T0.2 | S |
| [ ] T0.5 | Jobs and schedulerEnqueue, claim, retry up to five times, re-queue anything left running at start-up, and recurring jobs with due times that catch up after sleep.**Done when**With a fake clock, a job due at 06:00 runs once when the clock jumps to 09:00, and once only after a simulated crash. | **Covers** AP-4 **Needs** T0.3, T0.4 | M |
| [ ] T0.6 | Learning item lifecycleThe single function that moves an item between states, checks the move is allowed and writes an event. In this phase, booking stores a date and time you choose.**Done when**A table-driven test covers every allowed move and rejects every other one. | **Covers** LQ-2, LQ-4 **Needs** T0.4 | M |
| [ ] T0.7 | Capture serviceStore a capture under an idempotency key, normalise and hash links, and detect a link already open in the queue. Links become items, and plain text waits for a type.**Done when**The same link sent twice leaves one item, moved to the top of the revisit list. | **Covers** CAP-3, CAP-4 **Needs** T0.6 | M |
| [ ] T0.8 | API for captures, items and tasksEndpoints to create a capture, list and edit items, make a transition, and create, edit and tick tasks.**Done when**Every endpoint has a test, and an invalid transition returns a clear error. | **Needs** T0.7 | S |
| [ ] T0.9 | Enrichment without AIA job that fetches the page title, guesses the source type from the address and sets a 20-minute estimate.**Done when**A YouTube link gets its title and type “video”. An unreachable page keeps the raw link and the job does not retry forever. | **Covers** CAP-6 **Needs** T0.5, T0.7 | S |
| [ ] T0.10 | Telegram adapterCreate the bot with BotFather. Long-poll for messages with a stored offset, send messages with buttons, handle button taps, and lock the bot to your chat on first `/start`.**Done when**The bot answers you, ignores a second account, and a button tap reaches a handler. | **Covers** NU-2, NU-4, SYS-2 **Needs** T0.5 | M |
| [ ] T0.11 | Capture by chatA message becomes a capture and gets “Saved”. A duplicate gets the already-saved reply. Plain text gets three buttons. A message is confirmed to Telegram only after it is stored.**Done when**Share three links with the app stopped, start it, and all three arrive in order, each with “Saved”. | **Covers** CAP-2, CAP-3, CAP-5 **Needs** T0.7, T0.10 | M |
| [ ] T0.12 | Resurfacing and expiryThe morning run: surface on days 3, 7 and 14, last ask on day 21, archive two days later. The revisit list returns at most three, last asks first.**Done when**A fake-clock test walks one ignored item from day 0 to day 23. A second test skips five days and gets the same list an on-time run would give. | **Covers** AP-1, AP-2, AP-3, AP-4 **Needs** T0.5, T0.6 | M |
| [ ] T0.13 | Nudge budget and morning briefA budget of three nudges a day with a priority order, and the morning brief with Book and Let go buttons on each item.**Done when**Tapping Let go in Telegram archives the item. A fourth nudge on the same day is held back. | **Covers** NU-1, NU-2, NU-3 **Needs** T0.10, T0.12 | M |
| [ ] T0.14 | Web shellThe React app with the mockup’s tokens, sidebar, routing, toast, light and dark, and quick capture on the `C` key.**Done when**`C`, paste, Enter saves an item from any screen in under five seconds. | **Covers** CAP-1, SYS-4 **Needs** T0.1 | M |
| [ ] T0.15 | Learning queue screenThe four-column board, the card dialog with only the valid moves, drag and drop between columns, and the ageing mark after 14 days.**Done when**Every card can reach every valid state by drag or by two clicks, and the board matches the mockup. | **Covers** LQ-1, LQ-2, LQ-3, LQ-4, LQ-5 **Needs** T0.8, T0.14 | L |
| [ ] T0.16 | Today, basicToday’s tasks with estimates and a done toggle, plus the “Time to revisit” card.**Done when**A task added by quick capture appears and can be ticked. The revisit card shows the same three items as the brief. | **Covers** DAY-1 **Needs** T0.15 | M |
| [ ] T0.17 | One process, started at loginThe API serves the built web app. A launchd entry starts it at login and restarts it if it exits. Logs go to the user log folder.**Done when**Restart the Mac, log in, and `localhost:8000` answers without any action from you. | **Covers** SYS-1 **Needs** T0.13, T0.16 | S |
| [ ] T0.18 | Phase 0 acceptanceRun the PRD’s “accepted when” checks for capture, queue and autopilot as a written script. Then use it for a week.**Done when**All checks pass, and you have shared at least five real links from your phone. | **Needs** T0.17 | S |

05

## Phase 1: Direction

14 tasks6.25 days

**Finished when:** Every task on Today shows where it leads. The week board shows an overbooked day. The day can be closed.

Three open calls from the PRD land here, and the plan assumes the answers I proposed: marking an item learned requires a note (T1.11), and life goals sit beside work goals (T1.1). Say so before T1.1 if either is wrong.

| Task | What to build | Links | Size |
| --- | --- | --- | --- |
| [ ] T1.1 | Goal treeTables and service for goals and key results: four horizons, one parent at the next horizon up, and the limits of three themes, five quarter goals and three weekly outcomes.**Done when**A weekly outcome cannot be saved without a parent. A fourth theme is refused. | **Covers** GO-1, GO-2, GO-3 **Needs** T0.18 | M |
| [ ] T1.2 | Trace and progressThe query that walks from a task to its year theme, and progress rolled up from key results.**Done when**A task four levels down returns its full chain in one call. | **Covers** GO-4 **Needs** T1.1 | S |
| [ ] T1.3 | Goals APIEndpoints to list a horizon, create and edit goals and key results, and fetch a trace.**Done when**Every endpoint has a test. | **Needs** T1.2 | S |
| [ ] T1.4 | Year, quarter and month screensThe three horizon pages from the mockup: themes, quarter goals with editable key results, and the month calendar with its milestone list.**Done when**A key result can be updated in place and the goal’s progress changes at once. | **Covers** GO-3, GO-6 **Needs** T1.3 | L |
| [ ] T1.5 | Guided setupA first-run flow: themes, then quarter goals, then this week’s outcomes.**Done when**Starting with no goals, you finish setup in 15 minutes or less. | **Covers** SYS-5 **Needs** T1.4 | M |
| [ ] T1.6 | Link tasks and items to goalsA goal picker on tasks, items and quick capture. Tasks without a goal are labelled untied. Goal-linked items stop expiring.**Done when**A goal-linked item is still in the inbox on day 30 in the fake-clock test. | **Covers** GO-5, LQ-7, CAP-7 **Needs** T1.3 | M |
| [ ] T1.7 | Top three and daily focusRank up to three tasks. The first one not done becomes the focus card, with its trace. Ranking a fourth asks which it replaces.**Done when**From any task on Today, the year theme is one click away. | **Covers** DAY-2, GO-4 **Needs** T1.6 | M |
| [ ] T1.8 | Week boardSeven day columns, drag to reschedule, planned hours per day and for the week against capacity, and up to three weekly outcomes.**Done when**Dragging a three-hour task from Monday to Thursday updates both totals. A 44-hour week shows a warning. | **Covers** WK-1, WK-2, WK-3 **Needs** T1.6 | L |
| [ ] T1.9 | Plan tomorrowThe flow without the calendar step: decide on each open task, then choose the top three.**Done when**With four open tasks, the flow cannot finish until each has been moved, rescheduled or dropped. | **Covers** DAY-3, AP-5 **Needs** T1.7 | M |
| [ ] T1.10 | Evening shutdownThe four-step checklist, the one line about what you learned, and the record that the day is closed.**Done when**Ticking the fourth step marks the day closed in `daily_logs`. | **Covers** DAY-4, DAY-5 **Needs** T1.9 | S |
| [ ] T1.11 | Learned note and work-in-progress limitMarking an item learned asks for one line. Starting a third item in Learning asks you to finish or return one.**Done when**An item cannot reach Learned without the note. | **Covers** LQ-6, LQ-8 **Needs** T1.6 | S |
| [ ] T1.12 | Bot commands`/today` and `/queue`. The morning brief now leads with the top three.**Done when**Both commands answer correctly with the Mac awake. | **Covers** NU-5 **Needs** T1.7 | S |
| [ ] T1.13 | Daily backup and restoreA daily copy made with SQLite’s backup command into the Drive folder, 30 kept, and a restore script.**Done when**You have restored yesterday’s backup into a scratch folder and opened the app on it. | **Covers** SYS-6 **Needs** T0.5 | S |
| [ ] T1.14 | Phase 1 acceptanceRun the PRD checks for goals, Today and the week. Then plan and close five real days.**Done when**All checks pass and five days were planned the evening before. | **Needs** T1.13 | S |

06

## Phase 2: Time

11 tasks5 days

**Finished when:** A learning block shows up in Google Calendar already filled, and Today shows meetings and blocks together.

The learning slot times from the PRD are used as defaults in T2.5: Monday, Wednesday and Friday at 16:00 and Saturday at 10:00. They are settings, so changing them later costs nothing.

| Task | What to build | Links | Size |
| --- | --- | --- | --- |
| [ ] T2.1 | Google sign-inCreate the Google Cloud project and desktop client by hand. Run the sign-in once and keep the refresh token in the macOS Keychain.**Done when**After a restart the app reads your calendar list without asking you to sign in again. | **Needs** T1.14 | M |
| [ ] T2.2 | Read meetingsPull changes every ten minutes from a saved sync cursor and store meetings as read-only blocks.**Done when**A meeting added in Google Calendar appears in the database within ten minutes, and a deleted one disappears. | **Covers** CAL-1 **Needs** T2.1 | M |
| [ ] T2.3 | Write Compass blocksThe time_blocks table and service. Create a calendar named Compass and write, move and delete only events Compass made.**Done when**A test proves no code path can change an event that lacks the Compass marker. | **Covers** CAL-2, CAL-3 **Needs** T2.2 | M |
| [ ] T2.4 | Time blocks on TodayThe 08:00 to 20:00 list with meetings and blocks, the current one highlighted, and NSE open and close marked.**Done when**Today matches Google Calendar for the day, and the highlight moves as time passes. | **Covers** DAY-6 **Needs** T2.3 | M |
| [ ] T2.5 | Protected learning slotsGenerate the week’s slots from settings. If a meeting lands on one, move it to the next free 45 minutes that day.**Done when**On Sunday evening the next week’s four slots exist. A clashing meeting moves the slot, or marks it not kept if the day is full. | **Covers** AP-6 **Needs** T2.3 | M |
| [ ] T2.6 | Fill the blocksScore open items for each empty slot and book the best. One tap swaps it. Booking now reserves a real slot.**Done when**With a started item, a goal-linked item and an old item in the queue, the started one is booked first. | **Covers** AP-7 **Needs** T2.5 | M |
| [ ] T2.7 | Run a blockStart, save progress, finish. A block that passes without a start returns its item to the top of the revisit list.**Done when**An unfinished item resumes in the next block with its progress. A missed block counts as not kept. | **Covers** AP-8, LQ-9 **Needs** T2.6 | M |
| [ ] T2.8 | Plan tomorrow, with blocksAdd the third step: propose blocks around tomorrow’s meetings, let you adjust, then write them to the calendar.**Done when**Tomorrow’s plan is visible in Google Calendar after you confirm. | **Covers** DAY-3 **Needs** T2.4 | M |
| [ ] T2.9 | RemindersThe block reminder 15 minutes before, the 19:30 shutdown nudge, and one combined brief after a long sleep.**Done when**After a simulated two-day sleep you get one message, not six. | **Covers** NU-6, NU-7, NU-8 **Needs** T2.7 | M |
| [ ] T2.10 | Disconnect and resyncA banner when the calendar is disconnected, and a button that rebuilds calendar data from scratch.**Done when**With the token removed, every non-calendar screen still works. | **Covers** CAL-4 **Needs** T2.2 | S |
| [ ] T2.11 | Phase 2 acceptanceRun the PRD checks for calendar and autopilot. Then use protected blocks for a week.**Done when**All checks pass and at least two learning blocks were kept. | **Needs** T2.10 | S |

07

## Phase 3: Reflection

9 tasks3.5 days

**Finished when:** Sunday’s review opens with the week’s numbers in place, and closing it drafts next week.

| Task | What to build | Links | Size |
| --- | --- | --- | --- |
| [ ] T3.1 | MetricsPure functions for alignment, top-three completion, blocks kept, queue flow and both streaks, each with tests on fixed data.**Done when**Each metric matches a hand-worked example. | **Needs** T2.11 | M |
| [ ] T3.2 | Day rollupThe 23:30 job that stores the day’s numbers, running at next wake if missed.**Done when**Running it twice for the same date leaves one row. | **Needs** T3.1 | S |
| [ ] T3.3 | Direction checkThe card on Today: aligned share of hours, learning blocks kept, planning streak.**Done when**The figures agree with the metrics tests for the same data. | **Covers** DAY-7 **Needs** T3.2 | S |
| [ ] T3.4 | Weekly review screenThe Sunday 18:00 prepare job, the numbers, the four prompts, and the lists of expired and oldest items with one-tap decisions.**Done when**On Sunday evening the review is waiting with numbers filled in, and can be finished in 20 minutes. | **Covers** RV-1, RV-2, RV-5 **Needs** T3.2 | L |
| [ ] T3.5 | Close the weekFreeze the snapshot and turn the fourth answer into next week’s draft outcomes.**Done when**Completing a week-47 task after closing does not change week 47’s numbers. | **Covers** RV-3, RV-4 **Needs** T3.4 | M |
| [ ] T3.6 | Pace on quarter goalsProgress against elapsed time, shown as on track, at risk or behind, with the pace tick.**Done when**On day 54 of 92, 51% reads on track and 35% reads behind. | **Covers** GO-7 **Needs** T3.1 | S |
| [ ] T3.7 | Streak grid and queue flow chartThe 12-week grid of planned and closed days, and items added against closed over eight weeks.**Done when**Both charts match the events table for a seeded dataset. | **Covers** RV-6, LQ-10 **Needs** T3.2 | S |
| [ ] T3.8 | Planning promptsOpen next quarter’s planning a week before it starts, and next year’s from 1 December.**Done when**With the clock set to 24 December, the quarter prompt is showing. | **Covers** GO-8 **Needs** T3.6 | S |
| [ ] T3.9 | Phase 3 acceptanceRun the PRD checks for review. Then close two real weeks.**Done when**Two weeks are closed, and the second was drafted by the first. | **Needs** T3.8 | S |

08

## Phase 4: Polish

5 tasks2 days

**Finished when:** Saving a tab takes one click, and you can see at a glance that everything ran.

| Task | What to build | Links | Size |
| --- | --- | --- | --- |
| [ ] T4.1 | Browser extensionA one-button Chrome extension that sends the current tab to the local API.**Done when**One click on any page puts it in the inbox, with the same duplicate handling as other channels. | **Covers** CAP-8 **Needs** T3.9 | M |
| [ ] T4.2 | Status pageLast run of each job, jobs that gave up, last Telegram check, last backup.**Done when**Stopping the backup for a day turns its row to a warning. | **Covers** SYS-7 **Needs** T3.9 | S |
| [ ] T4.3 | ExportAll data as one JSON file.**Done when**The export loads into an empty database and the app shows the same data. | **Covers** SYS-8 **Needs** T3.9 | S |
| [ ] T4.4 | Settings screenA screen for the rules in PRD section 08, replacing hand edits.**Done when**Changing the learning slot times regenerates next week’s slots. | **Covers** SYS-3 **Needs** T3.9 | M |
| [ ] T4.5 | Edge cases and finishWalk through the eleven situations in PRD section 09, check every action has a keyboard path, and confirm screens load in under half a second.**Done when**Each situation behaves as the PRD says. | **Needs** T4.4 | M |

09

## Tests that matter most

Most of the product’s value sits in rules about time. These scenario tests protect them. Each runs in well under a second with the fake clock.

| Scenario | Proves | Written in |
| --- | --- | --- |
| An ignored link, followed from day 0 to day 23 | It surfaces three times, gets a last ask and is archived | T0.12 |
| The Mac sleeps for five days | The next run gives the same revisit list as an always-on system | T0.12 |
| The same link shared twice | One card, moved to the top | T0.7 |
| Storing a Telegram message fails | The message is not confirmed and arrives again | T0.11 |
| The process is killed in the middle of a job | The job runs again once at start-up | T0.5 |
| Every state move, allowed and not | The lifecycle has no back doors | T0.6 |
| A goal-linked item at day 30 | It has not expired | T1.6 |
| A meeting lands on a learning slot | The slot moves, or is marked not kept | T2.5 |
| An event without the Compass marker | No code path can change it | T2.3 |
| A task finished after its week was closed | The closed week’s numbers do not move | T3.5 |

Each phase also ends with an acceptance task. It runs the PRD’s “accepted when” checks by hand on your real Mac and phone, because a passing test suite does not prove that launchd, Telegram and Google behave.

10

## Requirement coverage

All 70 requirements in the PRD are built by at least one task. This table is generated from the task list, so a requirement with no task would fail the build of this page.

| Area | Requirement and the tasks that build it |
| --- | --- |
| Capture | **CAP-1** T0.14**CAP-2** T0.11**CAP-3** T0.7, T0.11**CAP-4** T0.7**CAP-5** T0.11**CAP-6** T0.9**CAP-7** T1.6**CAP-8** T4.1 |
| Learning queue | **LQ-1** T0.15**LQ-2** T0.6, T0.15**LQ-3** T0.15**LQ-4** T0.6, T0.15**LQ-5** T0.15**LQ-6** T1.11**LQ-7** T1.6**LQ-8** T1.11**LQ-9** T2.7**LQ-10** T3.7 |
| Autopilot | **AP-1** T0.12**AP-2** T0.12**AP-3** T0.12**AP-4** T0.5, T0.12**AP-5** T1.9**AP-6** T2.5**AP-7** T2.6**AP-8** T2.7 |
| Goals | **GO-1** T1.1**GO-2** T1.1**GO-3** T1.1, T1.4**GO-4** T1.2, T1.7**GO-5** T1.6**GO-6** T1.4**GO-7** T3.6**GO-8** T3.8 |
| Today | **DAY-1** T0.16**DAY-2** T1.7**DAY-3** T1.9, T2.8**DAY-4** T1.10**DAY-5** T1.10**DAY-6** T2.4**DAY-7** T3.3 |
| Week | **WK-1** T1.8**WK-2** T1.8**WK-3** T1.8 |
| Review | **RV-1** T3.4**RV-2** T3.4**RV-3** T3.5**RV-4** T3.5**RV-5** T3.4**RV-6** T3.7 |
| Telegram | **NU-1** T0.13**NU-2** T0.10, T0.13**NU-3** T0.13**NU-4** T0.10**NU-5** T1.12**NU-6** T2.9**NU-7** T2.9**NU-8** T2.9 |
| Calendar | **CAL-1** T2.2**CAL-2** T2.3**CAL-3** T2.3**CAL-4** T2.10 |
| System | **SYS-1** T0.17**SYS-2** T0.10**SYS-3** T0.3, T4.4**SYS-4** T0.14**SYS-5** T1.5**SYS-6** T1.13**SYS-7** T4.2**SYS-8** T4.3 |

Compass build plan · draft 1.0 · estimates are rough and assume AI-assisted work