Compass

Product requirements

[00Summary](#top)[01The problem](#problem)[02User and context](#user)[03Goals and success measures](#goals)[04Product principles](#principles)[05Scope and releases](#scope)[06Requirements](#requirements)[07Rituals and time budget](#rituals)[08Rules and defaults](#rules)[09Edge cases and empty states](#edges)[10Quality requirements](#quality)[11Risks and open questions](#risks)

PRD draft 1.0\
22 November 2026\
70 requirements · 51 must\
[Architecture study](https://claude.ai/artifact/KAEhFLs2tcLEagVw4KDifJ)\
[Mockup](https://claude.ai/artifact/FxuE9rP8meo8shUycYyyUF)

Product requirements document

# Compass: what it must do

A personal planning system for one person. It makes sure that what you save to learn comes back until you decide on it, and that each day’s work traces to a goal you chose.

PRD draft 1.0One userMac · Android · Telegram70 requirements

Ask

### Four product calls for you

1. Are the targets in section 03 the right bar?
2. Should “learned” require a one-line note? I have said yes.
3. Learning slots: Mon, Wed, Fri at 16:00 and Sat at 10:00. Right for you?
4. Do life goals sit beside work goals? I have assumed yes, as in the mockup.

Carry

### Already decided

- For you alone, on your Mac, at no cost.
- The phone side is a Telegram bot.
- Meetings come from Google Calendar.
- AI features stay off for now.
- The approved mockup is the design reference.

Risk

### What would make this fail

Overhead. The product asks for about an hour and a half of planning a week. If that feels like work about work, it gets dropped. So the first release asks for nothing: you share links, and it brings them back.

01

## The problem

Two problems, in your words, and they feed each other.

| Problem | What happens today | What it costs |
| --- | --- | --- |
| Saved, then forgotten | You meet something worth learning almost every day and mean to come back to it. There is no place it goes and nothing brings it back, so by your account almost none of it gets looked at again. | The learning does not happen, and the list of things you meant to learn becomes a source of guilt. |
| No plan, so no direction | Days, weeks, months and the year are not planned. Without a plan there is nothing to set goals against and nothing to measure a day by. | Work fills the time that is available. Effort is high, and it is hard to say what it added up to. |

They are one problem seen from two sides. Learning never gets time because time is never allocated on purpose, and time is never allocated on purpose because there are no goals to allocate it to.

### Why a custom tool

Task apps store tasks and read-later apps store links. Both are good at holding things and neither makes you decide. The gap is a system that forces a decision on every saved item and connects each day’s work to a goal. That behaviour is the product. Everything else is plumbing.

02

## User and context

There is one user. The product is built around how you already work, and it does not have to suit anyone else.

| Fact | What it means for the product |
| --- | --- |
| Founder and engineer, mostly working alone | Nobody else assigns priorities. The product has to supply the structure a manager or a team would. |
| Mac at the desk, Android phone away from it | Planning and review happen on the Mac. The phone is for capture and short answers. |
| Telegram is already on the phone | The phone side is a Telegram chat. There is nothing new to install or open. |
| Meetings live in Google Calendar | Compass plans around meetings and does not try to own them. |
| Trading hours shape the day | The day view marks the NSE open and close, since deep work and market attention compete. |
| Interesting links arrive all day, from many apps | Capture has to work from any app in two taps and must never ask a question first. |

### The jobs it is hired for

1. When I come across something worth learning, I want to save it in seconds, so that I can get back to what I was doing without losing it.
2. When I have saved something, I want it to come back to me until I decide, so that forgetting is never the outcome.
3. When I start a day, I want to know the three things that matter and why, so that the day adds up to something.
4. When a week ends, I want to see where the time went against what I intended, so that next week is better aimed.

03

## Goals and success measures

The product succeeds if two things become true. Saved items end in a decision, and days are spent on purpose. The measures below test exactly that.

**Fig 1.** The product model. Two loops share one calendar: a booked learning block is part of the day’s plan, and goals decide which saved item gets the next block.

### Outcome measures

Each is read four weeks after the release that enables it. The targets are proposals for you to confirm.

| Measure | Definition | Today | Target |
| --- | --- | --- | --- |
| Deliberate endings | Share of saved items that end as learned or let go, not expired | No system, so close to none | 80% or more |
| Items learned | Saved items finished with a note or an action, per week | Close to none | 3 or more a week |
| Days planned | Days that open with a top three already chosen | None | 5 of 7 |
| Aligned time | Share of planned hours that link to a goal | Not measurable | 60% or more |
| Weeks reviewed | Weekly reviews closed, out of the last four | None | 3 of 4 |

### Habit measures

| Measure | Target | Why it matters |
| --- | --- | --- |
| Captures a week | 5 or more | Shows that capture is easy enough to use without thinking |
| Learning blocks kept | 3 of 4 a week | This is the time that turns a saved link into something learned |
| Shutdowns done | 4 or more a week | The shutdown is what plans the next day |

### Guardrails

These must hold even if the measures above look good.

| Guardrail | Limit |
| --- | --- |
| Time spent planning and reviewing | Two hours a week at most, all rituals together |
| Nudges | Three a day at most |
| Effort to capture | Two taps on the phone, one key on the Mac, no required fields beyond the thing itself |
| Lost captures | None, as long as the Mac is opened within 24 hours |
| Running cost | Zero |

### Not goals

Working for other people. Replacing the calendar. Storing notes or documents. Reading saved content inside the app. Tracking habits in general. Summaries or suggestions from AI, which stay off for now.

04

## Product principles

When a requirement is unclear or two of them pull apart, these decide.

| Principle | What it means in practice |
| --- | --- |
| Capture is free, decisions are forced | Saving asks for nothing. After that the system keeps asking until you book it, link it or let it go. |
| The system does the remembering | You never have to recall that something exists. If it matters today, it is on your desk today. |
| Every task has a why | Wherever a task appears, the goal it serves is one glance away. Untied work is allowed and is counted. |
| Letting go is a success | Dropping an item on purpose is a decision made. Only silent expiry counts against you. |
| Few things at once | Three priorities a day, three outcomes a week, three themes a year, three nudges a day. |
| Calm by default | One quiet colour, attention colour only where something needs you, detail on click. |
| Plans are cheap to change | Moving a task is one drag. A plan that is hard to change is one that gets ignored. |

05

## Scope and releases

Five releases. Each one is usable by itself, and the first asks nothing of you except to share links. This table says what you can do after each. The requirements in section 06 carry the release they belong to.

| Release | After it, you can | Problem it addresses |
| --- | --- | --- |
| P0 Core loop | Share a link from your phone or Mac, see it in a queue, and have it come back on days 3, 7 and 14 until you decide. Get a morning brief in Telegram. | Forgetting |
| P1 Direction | Set themes, goals and weekly outcomes. Pick a top three each day and see what each task leads to. Plan the week on a board. Close the day. | Direction |
| P2 Time | See meetings and blocks in one day view. Have four learning blocks a week appear on your calendar already filled. Get reminders. | Both |
| P3 Reflection | Open Sunday’s review with the numbers filled in. See pace on quarter goals and your streaks. | Direction |
| P4 Polish | Save a browser tab in one click. Check system status. Export everything. | Comfort |

Two changes from the build order in the architecture study, both deliberate. The morning brief moves to P0, because the bot already exists there and the brief is what makes resurfacing visible on the phone. The daily backup moves to P1, because from that release the file holds goals you would not want to retype.

**Fig 2.** The screens. The top row is one chain: every task on Today traces rightward to a year theme. Telegram is the eighth surface and the only one on the phone.

06

## Requirements

Ten areas. Each has the need it serves, numbered requirements with a priority and a release, and the tests that say it is done. Must means the release is not finished without it.

### A. Capture

When I see something worth learning, I want to save it without stopping what I am doing.

| ID | Requirement | Priority | Release |
| --- | --- | --- | --- |
| CAP-1 | On the Mac, pressing `C` on any screen opens quick capture. A title or a link alone is enough to save. | Must | P0 |
| CAP-2 | On the phone, sharing a link or text to the Compass bot saves it. The bot replies “Saved” once the Mac has stored it. | Must | P0 |
| CAP-3 | A link becomes a learning item. Plain text gets a one-tap choice: learn later, task or note. | Must | P0 |
| CAP-4 | Saving a link that is already open in the queue does not create a second card. The existing item moves to the top of the revisit list and the reply says when it was first saved. | Must | P0 |
| CAP-5 | Captures sent while the Mac is closed arrive at the next wake, in the order sent, if that is within 24 hours. | Must | P0 |
| CAP-6 | Each learning item gets a title from the page, a source type and a time estimate. The estimate defaults to 20 minutes and can be edited. | Should | P0 |
| CAP-7 | A goal and a one-line reason can be added at capture. Neither is required. | Could | P1 |
| CAP-8 | A browser extension saves the current tab in one click. | Should | P4 |

Accepted when

- With the Mac closed, a link shared from the Android share sheet is in the inbox within a minute of opening the lid, and the chat shows “Saved”.
- Sharing the same link twice leaves one card in the queue.
- From any screen on the Mac, `C`, paste, Enter saves an item in under five seconds.

### B. Learning queue

When I look at what I have saved, I want to see where each thing stands and move it with one action.

| ID | Requirement | Priority | Release |
| --- | --- | --- | --- |
| LQ-1 | A board with four columns: Inbox, Booked, Learning, Learned. Each card shows title, source, length, and age or slot. | Must | P0 |
| LQ-2 | Opening a card offers only the moves that are valid for its state: book, link a goal, let go; start, unbook; mark learned. | Must | P0 |
| LQ-3 | Dragging a card to another column makes the same move as the matching button. | Must | P0 |
| LQ-4 | Let go archives the item for good and counts as a decision. | Must | P0 |
| LQ-5 | Inbox items older than 14 days are visibly marked and ask “still want this?”. | Must | P0 |
| LQ-6 | Marking an item learned asks for one line: what you took from it or what you did with it. | Must | P1 |
| LQ-7 | An item can be linked to a goal. Goal-linked items do not expire and are first in line for learning blocks. | Should | P1 |
| LQ-8 | At most two items can be in Learning at once. Starting a third asks you to finish or return one. | Should | P1 |
| LQ-9 | An unfinished item keeps its progress and resumes in the next block. | Should | P2 |
| LQ-10 | A chart shows items added against items closed for the last eight weeks. | Should | P3 |

Accepted when

- Every card can be moved to any valid state by drag or by two clicks.
- An item cannot reach Learned without the one-line note.
- A let-go item never appears again in any list or nudge.

### C. Autopilot

When I have saved something and done nothing, I want the system to bring it back, and to find time for it without my asking.

**Fig 3.** The life of a saved link that you ignore. It returns three times, asks once more, and only then is archived. Nothing leaves the queue unseen.

| ID | Requirement | Priority | Release |
| --- | --- | --- | --- |
| AP-1 | An inbox item with no decision returns to “Time to revisit” on days 3, 7 and 14 after capture. | Must | P0 |
| AP-2 | On day 21 the item gets a last ask. With no answer in two days it is archived as expired. | Must | P0 |
| AP-3 | The revisit list shows at most three items a day: last asks first, then the oldest. | Must | P0 |
| AP-4 | If the Mac was closed when a run was due, the next run surfaces exactly what the missed one would have. | Must | P0 |
| AP-5 | Open tasks at shutdown each need one decision: move to tomorrow, reschedule or drop. Nothing carries over silently. | Must | P1 |
| AP-6 | Four learning slots a week are protected on the calendar. Days, times and length are settings. | Must | P2 |
| AP-7 | Each empty slot is filled with the best item that fits: one already started, then goal-linked, then older. One tap swaps it. | Must | P2 |
| AP-8 | A learning block that passes without being started returns its item to the top of the revisit list and counts as not kept. | Should | P2 |

Accepted when

- A link saved on a Monday and ignored appears in Thursday’s revisit list without any action from you.
- After five days with the Mac closed, opening it shows the same revisit list an always-on system would show that day.
- On Sunday evening, next week’s four learning blocks are on the calendar with an item in each, if the queue has enough that fit.

### D. Goals and horizons

When I decide what to work on, I want to see how it connects to what I am trying to achieve this year.

| ID | Requirement | Priority | Release |
| --- | --- | --- | --- |
| GO-1 | Four horizons: up to three themes a year, up to five goals a quarter, milestones for the month, up to three outcomes a week. | Must | P1 |
| GO-2 | Every goal below a year theme links to exactly one parent at the next horizon up. | Must | P1 |
| GO-3 | A quarter goal has one to three key results, each with a target and a current value you update. | Must | P1 |
| GO-4 | Wherever a task or the daily focus is shown, its trace up to the year theme is one glance or one click away. | Must | P1 |
| GO-5 | A task without a goal is allowed. It is labelled untied and counted in the day’s alignment. | Must | P1 |
| GO-6 | The month page shows a calendar with dated milestones and a checklist with progress. | Should | P1 |
| GO-7 | Each quarter goal shows progress against pace: on track, at risk or behind. | Must | P3 |
| GO-8 | Planning prompts open on schedule: next quarter one week before it starts, next year from 1 December. | Should | P3 |

Accepted when

- From any task on Today, the year theme it serves can be reached in one click.
- A weekly outcome cannot be saved without a parent milestone.
- On day 54 of 92, a goal at 51% reads on track and one at 35% reads behind.

### E. Today

When I open my Mac in the morning, I want one screen that tells me what to do first and what the day holds.

| ID | Requirement | Priority | Release |
| --- | --- | --- | --- |
| DAY-1 | Today lists the day’s tasks with estimates and a done toggle, and shows the revisit list. | Must | P0 |
| DAY-2 | Up to three tasks are ranked as the top three. The first not yet done is the daily focus, shown with its trace. | Must | P1 |
| DAY-3 | Plan tomorrow is a three-step flow: decide on open tasks, choose the top three, place blocks. It takes five minutes or less. | Must | P1 |
| DAY-4 | The evening shutdown is a four-step checklist. Completing it records the day as closed. | Must | P1 |
| DAY-5 | The shutdown takes one line, “what did I learn today”, and stores it with the day. | Should | P1 |
| DAY-6 | Time blocks show the day from 08:00 to 20:00, with meetings, the current block highlighted, and NSE open and close marked. | Must | P2 |
| DAY-7 | A direction check shows today’s aligned share of hours, learning blocks kept this week and the planning streak. | Should | P3 |

Accepted when

- A day planned the evening before opens with the focus task, the top three and the blocks already in place.
- Ticking the fourth shutdown step marks the day closed and stops the shutdown nudge.
- Today loads in under half a second.

### F. Week

When I plan a week, I want to see whether what I intend fits the time I have.

| ID | Requirement | Priority | Release |
| --- | --- | --- | --- |
| WK-1 | A board with one column per day. Dragging a task to another day reschedules it. | Must | P1 |
| WK-2 | Each day shows planned hours and is flagged when over capacity. The week shows its total against capacity. | Must | P1 |
| WK-3 | Up to three weekly outcomes, each linked to a month milestone, with a done state. | Must | P1 |

Accepted when

- Dragging a three-hour task from Monday to Thursday updates both day totals at once.
- A week planned at 44 hours against 40 shows a warning.

### G. Review

When a week ends, I want an honest picture of it in a few minutes, and next week drafted from it.

| ID | Requirement | Priority | Release |
| --- | --- | --- | --- |
| RV-1 | By Sunday 18:00 the review is ready with the week’s numbers: top three done, hours on goals against plan, learning blocks kept, queue in and out. | Must | P3 |
| RV-2 | Four prompts: what moved a goal, what pulled me off course, which saved items still matter, next week’s top three. | Must | P3 |
| RV-3 | The answer to the fourth prompt becomes next week’s outcomes as a draft. | Must | P3 |
| RV-4 | Closing the week freezes its numbers. Later edits to tasks do not change a closed week. | Must | P3 |
| RV-5 | The review lists items that expired in the week and the five oldest in the inbox, each with a one-tap decision. | Should | P3 |
| RV-6 | A 12-week view shows which days were planned and closed. | Should | P3 |

Accepted when

- The review can be completed in 20 minutes.
- After closing week 47, completing a week-47 task late does not change week 47’s numbers.

### H. Telegram

When I am away from my Mac, I want the few things that need me to reach me where I already am, with the answer one tap away.

| ID | Requirement | Priority | Release |
| --- | --- | --- | --- |
| NU-1 | A morning brief arrives after the Mac’s first wake of the day: up to three items to revisit, and from P1 the top three. | Must | P0 |
| NU-2 | Every nudge carries buttons for its likely answers, such as Book, Let go and Later. | Must | P0 |
| NU-3 | At most three nudges a day. Replies to your own messages do not count. | Must | P0 |
| NU-4 | The bot answers only your chat and ignores everyone else. | Must | P0 |
| NU-5 | `/today` returns the top three and the next block. `/queue` returns the inbox count and the revisit list. | Should | P1 |
| NU-6 | A reminder arrives 15 minutes before a learning block, with the item’s title and link. | Must | P2 |
| NU-7 | A shutdown nudge arrives at 19:30 unless the day is already closed. | Must | P2 |
| NU-8 | After a long sleep you get one combined brief, not a backlog of old nudges. | Should | P2 |

| Moment | The bot says | Buttons |
| --- | --- | --- |
| You share a link | Saved · Raft consensus, visually explained · about 38 min | Link a goal |
| You share a link you already saved | Already saved 9 days ago. It is now top of today’s list. | Book · Let go |
| Morning brief | Today: 1 Split and bonus parity · 2 Investor call · 3 License checklist. Back on your desk: 3 items. | One row per item: Book · Let go |
| Last ask, day 21 | Saved 21 days ago: SVI volatility surface fitting. Keep it or let it go? | Book · Link a goal · Let go |
| Before a learning block | 16:00 learning block: K8s Services and Ingress · 45 min | Open · Swap · Skip today |
| Shutdown | Time to close the day. 2 tasks are still open. | Open shutdown |

Accepted when

- Tapping Let go in the morning brief removes the item, and the web app shows the change on its next load.
- On a day with five possible nudges, only three are sent, chosen by priority: last asks, then block reminders, then the rest.

### I. Calendar

When I plan my day, I want my meetings already there, and my plan visible in the calendar I already use.

| ID | Requirement | Priority | Release |
| --- | --- | --- | --- |
| CAL-1 | Meetings from Google Calendar appear read-only in time blocks and in Plan tomorrow. | Must | P2 |
| CAL-2 | Deep-work and learning blocks are written to a separate calendar named Compass. | Must | P2 |
| CAL-3 | Compass never edits or deletes an event it did not create. | Must | P2 |
| CAL-4 | If the calendar is disconnected the app keeps working and shows a banner. | Should | P2 |

Accepted when

- A meeting added in Google Calendar shows in Today within ten minutes while the Mac is awake.
- Hiding the Compass calendar in Google Calendar hides every block Compass made and nothing else.

### J. System

When I use my Mac, I want Compass simply to be there, and my data to be safe and mine.

| ID | Requirement | Priority | Release |
| --- | --- | --- | --- |
| SYS-1 | Compass starts when you log in and opens at a local address. There is no sign-in. | Must | P0 |
| SYS-2 | First run connects the Telegram bot in under five minutes and locks it to your chat. | Must | P0 |
| SYS-3 | The rules in section 08 are settings with the defaults given there. | Must | P0 |
| SYS-4 | Light and dark follow the Mac’s setting. | Should | P0 |
| SYS-5 | A guided setup of themes, quarter goals and this week’s outcomes takes 15 minutes or less. | Must | P1 |
| SYS-6 | The database is backed up daily to a Drive-synced folder, with 30 copies kept. | Must | P1 |
| SYS-7 | A status page shows the last run of each job, the last Telegram check and the last backup. | Must | P4 |
| SYS-8 | All data can be exported as one JSON file. | Should | P4 |

Accepted when

- After a restart of the Mac, Compass is running without any action from you.
- A backup has been restored once, end to end, before P1 is called done.

07

## Rituals and time budget

The product asks for your time at fixed moments. Together they must stay under two hours a week, or the system becomes the work.

| Ritual | When | Time | What it produces |
| --- | --- | --- | --- |
| Capture | Whenever something catches your eye | 5 seconds | An item in the inbox |
| Morning brief | First wake of the day | 1 minute | Decisions on up to three saved items |
| Learning block | Four times a week | 30 to 45 minutes | One item learned, with a note |
| Evening shutdown | 19:30 | 10 minutes | A closed day and tomorrow’s top three |
| Weekly review | Sunday | 20 minutes | A closed week and next week’s outcomes |
| Month check | Last day of the month | 15 minutes | Next month’s milestones |
| Quarter planning | Last week of the quarter | 60 minutes | Up to five goals with key results |
| Year planning | December | 90 minutes | Three themes and first-quarter goals |

In a normal week that is about 70 minutes of shutdowns, 20 of review and a few of briefs, which comes to roughly an hour and a half. Learning blocks are not counted as overhead. They are the point.

08

## Rules and defaults

Every number that shapes behaviour is a setting. These are the defaults, taken from the mockup.

| Rule | Default | Used by |
| --- | --- | --- |
| Decision window after capture | 48 hours | CAP, AP |
| Resurface days | 3, 7, 14 | AP-1 |
| Last ask, then archive | Day 21, then 2 days | AP-2 |
| Items in the revisit list | 3 a day | AP-3 |
| Learning slots | Mon, Wed, Fri at 16:00 and Sat at 10:00 | AP-6 |
| Learning block length | 45 minutes | AP-6 |
| Default time estimate for a saved item | 20 minutes | CAP-6 |
| Items in Learning at once | 2 | LQ-8 |
| Day window | 08:00 to 20:00 | DAY-6 |
| Daily capacity | 8 hours on weekdays, 3 at weekends | WK-2 |
| Weekly capacity | 40 hours | WK-2 |
| Top priorities a day | 3 | DAY-2 |
| Morning run due | 06:00, or first wake after | AP-4 |
| Shutdown nudge | 19:30 | NU-7 |
| Nudges a day | 3 | NU-3 |
| Pace bands | On track within 10 points of pace, at risk within 20 | GO-7 |
| Time zone and week start | Asia/Kolkata, Monday | All |

09

## Edge cases and empty states

| Situation | What the product does |
| --- | --- |
| First day, nothing saved | Today shows one prompt: share your first link to the bot. No empty charts. |
| No goals set yet (P0) | Tasks and items work without goals. Goal fields stay hidden until P1 setup is done. |
| Mac closed for a weekend | At wake, overdue runs happen in order and one combined brief is sent. |
| Mac closed for more than a day | Links shared in the gap may be lost. Any message in the chat without “Saved” needs sharing again. |
| The queue has nothing that fits a slot | The block stays on the calendar, marked open. The reminder suggests the shortest inbox item. |
| A meeting lands on a learning slot | The block moves to the next free 45 minutes that day. If there is none, it counts as not kept and the item returns to the list. |
| More than three things want to nudge | Three are sent, by priority. The rest wait for the next brief. |
| A fourth task is ranked into the top three | You are asked which one it replaces. |
| A goal is deleted with tasks under it | Its tasks become untied and its child goals ask for a new parent. |
| You are travelling in another time zone | Days stay on Asia/Kolkata until you change the setting. |
| A page title cannot be fetched | The item keeps the raw link as its title and can be renamed. |

10

## Quality requirements

| Area | Requirement |
| --- | --- |
| Speed | Every screen loads in under half a second. A tick or a drag shows its result at once. |
| Capture reliability | No capture is lost if the Mac is opened within 24 hours of sending it. |
| Privacy | All data stays on the Mac. The only outside services contacted are Telegram, Google Calendar and Google Drive for the backup copy. |
| Availability | Works with no internet connection, except for Telegram and calendar features. |
| Recovery | A lost Mac costs at most one day of data. |
| Accessibility | Every action has a keyboard path. Text meets contrast guidelines in light and dark. |
| Cost | No recurring cost of any kind. |
| Design | The approved mockup is the reference for layout, type and colour. |

11

## Risks and open questions

| Risk | Why it matters | Response |
| --- | --- | --- |
| High Planning feels like overhead | The rituals get skipped, then the app | A hard two-hour weekly budget. P0 asks for nothing and only gives things back. |
| High The inbox still piles up | Resurfacing becomes noise you swipe away | Three items a day at most, a last ask, automatic expiry, and queue flow in the weekly review. |
| Medium Nudges get muted | The phone side of the loop is lost | Three a day, each answerable in one tap, one combined brief after a long sleep. |
| Medium Goals are set once and go stale | The trace points at goals that no longer matter | Month, quarter and year planning prompts, and pace shown on every quarter goal. |
| Medium Scope grows into a notes app | The core loop stalls | Notes stay plain text. The not-goals list in section 03 is the guard. |

### Dependencies

Telegram for the phone side, Google Calendar for meetings and blocks, Google Drive for desktop for backups. All three are free services outside your control. The queue, goals and reviews keep working on the Mac without any of them.

### Later, not now

AI titles, summaries and estimates. The full app on the phone. Spaced repetition for what you have learned. Month and quarter reviews in the same form as the weekly one. Each can be added without changing anything above.

Compass PRD · draft 1.0 · sample goals, tasks and links are taken from the mockup and are illustrative