Compass

Architecture study

[00Summary](#top)[01Scope and assumptions](#scope)[02From mockup to mechanism](#mechanisms)[03High-level design](#hld)[04How it moves](#loops)[05Low-level design](#lld)[06Privacy, time and reliability](#crosscutting)[07Build order](#build)[08Risks](#risks)

Draft 0.3 · Mac edition\
22 November 2026\
8 figures · 13 tables

Architecture study · high-level and low-level design

# Compass: how to build it

The mockup has three loops: capture what you want to learn, plan from the year down to the day, and review what happened. This study turns them into a system that runs entirely on your laptop: one process, one database file, no hosting and no bill.

Draft 0.3Personal useRuns on your MacPython · FastAPI · SQLite · React

Ask

### Nothing open

All seven questions are answered. The next step is phase 0: the Telegram bot, the learning queue and the catch-up run. Tell me when you want it broken into a task-by-task build plan.

Carry

### Settled on 22 November

- For you alone, on your MacBook. No hosting.
- Android phone: share to a Telegram bot.
- Meetings come from Google Calendar.
- AI enrichment stays off for now.
- The four rules from the mockup hold.

Risk

### The failure to design against

A closed lid. Nothing runs while the laptop sleeps, and Telegram keeps a waiting message for about 24 hours. The design catches up at wake, and section 06 covers longer absences.

01

## Scope and assumptions

Compass has one user, you, and runs on one machine, your laptop. Its job is to keep you pointed at your goals and to make sure nothing you saved to learn is forgotten by accident. Everything below is sized for that.

| Assumption | What it lets us skip | If it turns out wrong |
| --- | --- | --- |
| One user, on one laptop | Hosting, sign-in, tenancy, a monthly bill | The same code runs on a server. Add a login and move the database file. |
| The laptop is awake on most working days | An always-on server | Jobs catch up at wake. Phone captures wait in Telegram for up to 24 hours. |
| Thousands of rows, not millions | A database server | Nothing. SQLite is comfortable well beyond this size. |
| The phone only needs capture and nudges | A phone app and a public address | Planning stays a laptop activity. Opening the full app on the phone would need a private network tool, added later. |
| The calendar holds meetings, Compass holds intent | Building a calendar | Meetings stay read-only here. Compass writes only its own blocks. |

### Why the laptop and not a free cloud tier

Your rule was to host only where it is free now and stays free. No provider makes that promise. A free tier is a marketing budget, and budgets get cut: Heroku, Railway, PlanetScale and Fly.io have all withdrawn free plans since 2022. The options that remain each fail the rule in a specific way.

| Option | What is free today | Where it fails the rule |
| --- | --- | --- |
| Oracle Cloud Always Free | Small virtual machines with no end date | Sign-up needs a credit card, and Oracle reclaims free machines it judges idle. A personal planner is idle most of the day. |
| Fly.io, Railway | A trial credit | Free plans withdrawn. New accounts pay almost from the first deploy. |
| Render | A free web service | It sleeps after 15 minutes without traffic, and a sleeping service cannot run the morning job. |
| Supabase, Neon | A free Postgres database | A database only, so the app still needs a host. Supabase pauses a project after a week without activity. |
| Your laptop | Everything | It only runs while the laptop is awake. Section 06 designs for that. |

Checked on 22 November 2026: [Oracle Free Tier](https://docs.oracle.com/iaas/Content/FreeTier/freetier.htm), [Oracle Always Free resources](https://docs.oracle.com/en-us/iaas/Content/FreeTier/resourceref.htm), [Render on free tiers in 2026](https://render.com/articles/platforms-with-a-real-free-tier-for-developers-in-2026), [a 2026 free-tier survey](https://dev.to/pickuma/best-free-tiers-for-developers-in-2026-saas-paas-iaas-tools-54og), [Telegram Bots FAQ](https://core.telegram.org/bots/faq).

### Out of scope

Hosting, team features, a notes app or second brain, a built-in reader for saved content, and native mobile apps. None of them fixes the two problems you described.

02

## From mockup to mechanism

Each thing you saw in the mockup needs something specific from the system. This table is the bridge between the screens and the design.

| On screen | What the system has to do | Module |
| --- | --- | --- |
| Quick capture, from anywhere | Accept a capture from the web app, the extension or Telegram, never lose one, never store the same link twice | Capture |
| Time to revisit | Work out each morning which saved items are due back on your desk | Autopilot |
| Learning block marked “from queue” | Fill every protected slot with the best item that fits its length | Autopilot, Day |
| The trace line in the focus card | Walk from a task up to the year theme | Planning |
| Direction check, 71% | Divide goal-linked minutes by all planned minutes for the day | Review |
| Week board hours turning rust | Sum estimates per day and compare with capacity | Day |
| Evening shutdown and its streak | Record when each day was planned and when it was closed | Day |
| Weekly review numbers | Freeze a snapshot when the week closes, so history never shifts | Review |
| Pace tick on quarter goals | Compare key-result progress with the share of the quarter already gone | Planning |

03

## High-level design

Compass is one process and one database file on your laptop. It reaches out to Telegram and Google Calendar, and nothing on the internet can reach in. That one property removes the public address, the login, the hosting and the bill.

**Fig 1.** System context. Arrows show who starts the conversation, and every one that leaves the laptop starts there. Your phone talks to Telegram, and Telegram holds the message until the laptop asks for it.

### What runs on the laptop

One process starts when you log in. It serves the web app, answers the API and runs the scheduler. The data is a single SQLite file, and a copy goes to a Drive-synced folder every night.

**Fig 2.** Runtime. The scheduler lives in the same process as the API, so there is one thing to start and one log to read.

### Modules

Inside the codebase there are eight modules with strict ownership. A module owns its tables, and other modules go through its functions, never its tables. That keeps the code easy to change, and easy to move to a server one day if you ever want to.

**Fig 3.** Module map. Autopilot holds the rules that act on your behalf: it resurfaces queue items, fills learning blocks and carries unfinished tasks forward.

| Module | Owns | Responsible for | Never does |
| --- | --- | --- | --- |
| Capture | `captures` | Accepting input fast, removing duplicates, turning a capture into an item, a task or a note | Decide priority |
| Learning queue | `learning_items` | The item lifecycle and every state change | Touch the calendar directly |
| Planning | `goals`, `key_results` | The goal tree, progress roll-up, pace, the trace | Schedule time |
| Day | `tasks`, `time_blocks`, `daily_logs` | Today, the week board, top three, shutdown | Invent tasks |
| Autopilot | its settings only | Resurfacing, expiry, block filling, carry-over | Store its own state. It is rules over other modules’ data. |
| Review | `reviews` | Metrics, streaks, weekly snapshots | Change live data |
| Notify | `notifications` | At most three nudges a day, sent to Telegram | Decide what is important |
| Integrations | tokens, sync cursors | Telegram, calendar and LLM adapters | Hold business rules |

### Decisions

The choices that shape everything else, with what was turned down and why.

| Decision | Choice | Turned down | Why |
| --- | --- | --- | --- |
| Where it runs | Your laptop | A free cloud tier | The only option whose price cannot change. See section 01. |
| Shape | One process with eight modules | Separate services | One thing to start, one log, one place to look when something is off. |
| Database | SQLite, one file | Postgres | No server to install or keep running. A backup is a copy of one file. |
| Inbound traffic | Polling: the laptop asks Telegram and Calendar for changes | Webhooks | A webhook needs a public address. Polling needs none. |
| Phone | Telegram is the phone interface, for capture and nudges | The web app on the phone | The app lives on localhost. Telegram is already on your phone and in the Android share sheet. |
| Background work | A jobs table and a scheduler loop in the same process | A separate queue and worker | A job is written in the same transaction as the change that needs it, and overdue jobs are simply still in the table at wake. |
| Backend and client | Python and FastAPI, serving a React and TypeScript app | A new stack | It is what you already use, and the mockup carries straight over. |
| History | Current-state tables plus an append-only event log | Full event sourcing | Review needs history. Rebuilding all state from events is not worth it at this size. |
| AI | Off for now, behind one interface | A model call inside the request | It is the only part of the design that costs money, and a capture has to succeed without it. |

04

## How it moves

Two flows carry most of the product: a capture arriving, and the daily cycle that brings things back to you.

### A capture arrives from the phone

On Android you share a link to the Compass bot from any app’s share sheet. If the laptop is closed, the message waits on Telegram’s servers. When the laptop wakes, Compass asks for everything it missed, stores each message and replies “Saved”. Fetching the page title and estimating its length happen after that, and are retried if they fail.

**Fig 4.** Capture from the phone. The “Saved” reply is your receipt. A message without one has not reached the laptop yet.

On the laptop, the web app and the browser extension write straight to the local API, so a capture is stored at once. Duplicates are handled at the door. If a link is already in your queue, Compass does not add a second card. It moves the existing one to the top of today’s revisit list and tells you when you first saved it.

### A day in the system

Each job has a due time, and runs at the first moment the laptop is awake after it. If you open the lid at 09:00, the 06:00 run happens at 09:00. The schedule for each saved item is stored on the item, so a late run surfaces exactly what an on-time run would have.

**Fig 5.** The daily cycle on a laptop. After a long sleep the overdue jobs run oldest first, and you get one combined brief, not a burst of old nudges. The Sunday review is prepared the same way.

### Plan tomorrow

1. **Draft.** Compass collects today’s open tasks, this week’s outcomes, tomorrow’s meetings from the calendar and the protected learning slot.
2. **Choose.** You pick the top three. Open tasks you do not pick are moved, rescheduled or dropped, one decision each.
3. **Place.** Compass proposes blocks: the first task into the longest free morning gap, the rest around meetings, the learning item into its slot.
4. **Commit.** You adjust and confirm. Blocks are written, calendar events are created, and the day is marked as planned.

05

## Low-level design

### Data model

Nine tables hold the product. Two of them carry most of the logic: `goals`, because it is a tree, and `learning_items`, because it has a lifecycle.

**Fig 6.** Core tables. Arrows point from the row that holds the reference to the row it points at. A capture becomes a learning item, a task or a note.

| Table | Notes that matter when you build it |
| --- | --- |
| `goals` | One table for all four horizons. A row’s parent must sit at a longer horizon, checked in the service. `period_start` and `period_end` are dates. |
| `key_results` | Only quarter goals have them. Progress is `current / target`, averaged per goal. |
| `tasks` | `planned_date` is a date, not a timestamp. `top_rank` is unique per user and date, which enforces exactly three. |
| `time_blocks` | Holds a task or a learning item, never both. Blocks read from the calendar have `source = calendar` and are read-only. |
| `learning_items` | `url_hash` is unique per user among open items. State changes only through the transition function in 5.3. |
| `captures` | Raw input, kept for 90 days. `idempotency_key` is unique. |
| `daily_logs` | One row per day. Streaks are computed from it. |
| `reviews` | The metrics snapshot is written once, when the period is closed. |
| `events` | Append-only. Every state change writes one row in the same transaction. |

### The goal tree and the trace

The trace line in the mockup is a walk up one chain of parent links. Because all four horizons share a table, it is one query.

**Fig 7.** One chain, read right to left. A task links to the lowest goal available, ideally a weekly outcome.

```
-- From a task up to the year theme
WITH RECURSIVE up AS (
  SELECT g.id, g.parent_id, g.horizon, g.title
  FROM tasks t JOIN goals g ON g.id = t.goal_id
  WHERE t.id = :task_id
  UNION ALL
  SELECT p.id, p.parent_id, p.horizon, p.title
  FROM goals p JOIN up ON up.parent_id = p.id
)
SELECT horizon, title FROM up;
```

Pace compares progress with elapsed time. With `pace = days gone / days in period`, a goal is on track when its progress is within 10 points of pace, at risk within 20, and behind beyond that. On day 54 of 92 pace is 59%, which is why 51% reads as on track and 35% as behind.

### The life of a learning item

An item is always in exactly one state. All changes go through one function, which checks the move is allowed, applies it and writes an event. No other code sets the state column.

**Fig 8.** Learning item states. Every path out of the inbox is a decision, either yours or, after day 21, the system’s.

| From | Action | To | What else happens |
| --- | --- | --- | --- |
| none | capture | Inbox | First resurface set for day 3 |
| Inbox | book | Booked | A learning block is reserved and written to Google Calendar |
| Booked | start | Learning | Started time recorded. Counts as a kept block. |
| Learning | finish | Learned | Asks for one line: a note or an action taken |
| Learning | block ends | Booked | Progress saved. Next free block is reserved. |
| Booked | unbook, or block missed | Inbox | Block released. Item returns to the top of the revisit list. |
| Inbox, Booked | let go | Let go | Archived for good. Counted as a decision, not a failure. |
| Inbox | no answer by day 23 | Expired | Archived. Listed in the weekly review. |

### Resurfacing and expiry

The schedule is stored on each item as `next_resurface_at`, so a run that is late or skipped catches up on the next one. Today’s revisit list shows at most three items: last asks first, then the oldest.

```
STEPS = [3, 7, 14, 21]                       # days after capture

def morning_run(now):
    for item in inbox_items(next_resurface_at__lte=now):
        n = item.resurface_count
        if n < 3:                             # day 3, 7, 14
            surface(item)
            item.resurface_count = n + 1
            item.next_resurface_at = item.captured_at + days(STEPS[n + 1])
        elif item.last_ask_at is None:        # day 21
            surface(item, last_ask=True)
            item.last_ask_at = now
            item.next_resurface_at = now + days(2)
        else:                                 # day 23, still no answer
            transition(item, "expire")
```

Linking an item to a goal counts as a decision. A goal-linked item stops expiring and moves ahead of unlinked items when blocks are filled.

### Filling a learning block

Each protected slot is filled by a score, not by age alone. The weights are settings, and the choice can be swapped with one tap.

```
def fill(slot):                               # a protected block with no item yet
    pool = [i for i in open_items()
            if i.state == "learning" or i.remaining_min <= slot.minutes + 10]

    def score(i):
        return (40 * (i.state == "learning")              # finish what you started
              + 30 * links_to_active_quarter_goal(i)      # goals before curiosity
              + 20 * min(i.age_days, 21) / 21             # older items rise before they expire
              + 10 * fit(i.remaining_min, slot.minutes))  # fills the block well

    best = max(pool, key=score, default=None)
    if best:
        transition(best, "book", slot=slot)
```

### Metrics

| Metric | Definition | Source |
| --- | --- | --- |
| Alignment | Minutes in blocks whose task links to a goal, divided by all planned minutes between 08:00 and 20:00 | `time_blocks` |
| Top-three completion | Ranked tasks done, divided by ranked tasks planned | `tasks` |
| Learning blocks kept | Learning blocks that were started, divided by protected slots that week | `events` |
| Queue flow | Items captured against items closed (learned, let go or expired), per week | `events` |
| Planning streak | Consecutive days planned before 09:00 | `daily_logs` |
| Shutdown streak | Consecutive days with a shutdown | `daily_logs` |

### API

Plain JSON over HTTP on localhost, used by the web app and the extension. Every write accepts an `Idempotency-Key` header, and updates carry a `version` so two open tabs cannot overwrite each other.

| Endpoint | Purpose |
| --- | --- |
| `POST /v1/captures` | Any channel. Returns 202 as soon as the capture is stored. |
| `GET /v1/today` | Everything the Today screen needs in one response: focus, tasks, blocks, revisit list, direction check |
| `POST /v1/tasks` · `PATCH /v1/tasks/{id}` | Create, complete, re-estimate, move to another day (the week board drag) |
| `PUT /v1/days/{date}/top-three` | Set the ranked three |
| `POST /v1/days/{date}/plan` | Commit the proposed blocks from Plan tomorrow |
| `POST /v1/days/{date}/shutdown` | Close the day. Triggers carry-over. |
| `GET /v1/learning-items?state=` | The queue board |
| `POST /v1/learning-items/{id}/transitions` | `{action: book \| start \| finish \| let_go \| unbook}`. The only way an item changes state. |
| `GET /v1/goals?horizon=&period=` | One horizon page, with progress and pace |
| `GET /v1/goals/{id}/trace` | The chain up to the year theme |
| `PATCH /v1/key-results/{id}` | Update the current value |
| `GET /v1/reviews/{week}` · `POST …/close` | Review numbers and answers. Closing freezes the snapshot. |
| `GET /v1/export` | All of your data as JSON |

### Jobs

Every job can run twice without doing damage, and every job can run late. Those two properties are what make a laptop a workable host.

| Job | Due | Safe to re-run or run late because |
| --- | --- | --- |
| `telegram_poll` | Continuously while awake | Each message is confirmed to Telegram only after it is stored |
| `morning_run` | 06:00, or first wake after | It only touches items whose resurface time has passed, and moves that time forward |
| `morning_brief` | Right after the morning run | One brief per date |
| `calendar_pull` | Every 10 minutes while awake | It resumes from a sync cursor |
| `block_reminder` | 15 minutes before a learning block | One per block, dropped if the block has already passed |
| `shutdown_nudge` | 19:30 | One per date, skipped if the day is closed or already over |
| `day_rollup` | 23:30, or next wake | Writes by date, replacing the same row |
| `enrich_capture` | On each capture | Writes by capture id |
| `review_prepare` | Sunday 18:00, or next wake | Writes by week |
| `backup` | Once a day | A new file per date |

```
-- One scheduler loop claims the oldest due job. Works in SQLite as written.
UPDATE jobs
SET status = 'running', started_at = CURRENT_TIMESTAMP, attempts = attempts + 1
WHERE id = (
  SELECT id FROM jobs
  WHERE status = 'queued' AND run_at <= CURRENT_TIMESTAMP
  ORDER BY run_at
  LIMIT 1)
RETURNING *;

-- At start-up, anything a crash or a closed lid left half done goes back in the queue.
UPDATE jobs SET status = 'queued' WHERE status = 'running';
```

### Code layout

```
compass/
  app/
    main.py           # one process: API, web app, scheduler
    modules/
      capture/        router.py  service.py  models.py
      learning/       router.py  service.py  lifecycle.py     # the state machine
      planning/       router.py  service.py  trace.py  pace.py
      day/            router.py  service.py  planner.py
      autopilot/      resurface.py  fill_blocks.py  carry_over.py
      review/         router.py  metrics.py  snapshot.py
      notify/         service.py  budget.py                   # max three a day
      integrations/   telegram.py  calendar.py  llm.py
    kernel/           clock.py  events.py  jobs.py  scheduler.py  db.py
  web/                React + TypeScript, built to static files
  extension/          one button: save this tab
  run/                start.sh  com.compass.app.plist  backup.py      # plist = launchd entry
  data/               compass.db                              # not in git
```

### Web client

The client has one route per screen in the mockup and is served by the same process at `localhost:8000`. Server data sits in a query cache and is updated optimistically, so ticking a task or dragging a card responds at once and rolls back if the server refuses. The mockup’s colours, type and spacing become the client’s design tokens unchanged.

06

## Privacy, time and reliability

Running on a laptop removes most security work and adds one new concern, which is the lid being closed. This section covers both.

| Concern | Design |
| --- | --- |
| Network exposure | Compass listens on `127.0.0.1` only. Nothing else on the Wi-Fi can reach it, so there is no sign-in to build. |
| Starting and staying up | A launchd LaunchAgent starts Compass when you log in and restarts it if it exits. Sleep does not end it: the process pauses with the Mac and carries on at wake. Logs go to `~/Library/Logs/Compass`. |
| Telegram bot | The bot accepts messages from your chat id and ignores everyone else. Its token lives in a local settings file outside the repository. |
| Calendar access | Google sign-in for a desktop app, done once. The refresh token is kept in the macOS Keychain. Google may expire tokens for projects left in testing mode, so check the consent-screen status when you set it up. |
| Time | Timestamps are stored in UTC. Dates such as `planned_date` are stored as dates. “Today” and “this week” are computed in Asia/Kolkata, with weeks starting on Monday. |
| Laptop asleep | Jobs carry a due time and stay in the table. At wake the scheduler runs what is overdue, oldest first, and sends one combined brief. |
| Away for more than a day | Telegram keeps undelivered messages for about 24 hours. Every stored capture gets a “Saved” reply, so anything in the chat without one should be shared again. |
| Crash or forced restart | SQLite runs in write-ahead mode, which survives a sudden stop. Half-finished jobs are queued again at start-up. |
| Backups | A daily copy of the database, taken with SQLite’s backup command, into a Google Drive for desktop folder. Thirty copies are kept. A lost laptop then costs at most one day. |
| Disk | Turn on FileVault. The file holds your goals and plans in plain form. |
| Seeing what happened | A status page at `/status` shows the last run of each job, any job that gave up, the last Telegram poll and the last backup. |

07

## Build order

Each phase ends with something you can use, and a test that says it works. Phase 0 is the smallest loop that fixes the forgetting problem by itself.

| Phase | Ships | Done when | Size |
| --- | --- | --- | --- |
| P0 Core loop | Start at login through launchd, capture from the web app and Telegram, the queue and its lifecycle, the catch-up morning run, a basic Today | You share a link from your phone with the laptop closed, and it is in your inbox when you open the lid, then back on your desk on day 3 | M |
| P1 Direction | Goal tree, key results, the trace, top three, week board, shutdown | Every task on Today shows where it leads, and the week board shows an overbooked day | M |
| P2 Time | Calendar polling, time blocks, protected slots, block filling, nudges | A learning block shows up in Google Calendar already filled | L |
| P3 Reflection | Weekly review, metrics, streaks, quarter pace | Sunday’s review opens with the week’s numbers in place | M |
| P4 Polish | Browser extension, backups to the synced folder, status page, export, optional AI enrichment | Saving a tab takes one click, and you have restored the database from a backup once | S |

08

## Risks

| Risk | Why it matters | What the design does about it |
| --- | --- | --- |
| High The laptop stays closed for days | Nothing runs, and Telegram drops messages after about 24 hours | Catch-up at wake, and the “Saved” receipt shows exactly which shares to send again |
| High The habit does not form | No architecture fixes an unopened app | It starts with the laptop, so there is nothing to remember to open. Nudges arrive in Telegram, where you already are. |
| Medium The laptop is lost or its disk fails | The only copy of your plans goes with it | Daily backup to a synced folder, and a restore you have practised once |
| Medium Too many nudges | You mute the bot and lose the loop | A hard budget of three a day, and one combined brief after a long sleep |
| Medium Telegram or Google changes its terms | Both are free services outside your control | Each sits behind one adapter. The web app and the queue keep working without either. |
| Medium Calendar sync edge cases | Recurring events and deletions are where sync code goes wrong | Meetings are read-only. Compass edits only events it created. A full resync is one button. |
| Low It grows into a notes app | Scope doubles and the core loop stalls | Notes stay plain text. The out-of-scope list in section 01 is the guard. |

Compass architecture study · draft 0.3 · the sample goals and tasks in the figures come from the mockup and are illustrative