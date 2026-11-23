# Decisions

Changes and answers on top of the PRD, architecture study and build plan in `docs/md/`.

## 22 November 2026

- Notes: plain-text captures typed as "note" go into a small `notes` table (id, body, created_at).
- Top priorities: no hard limit on ranked tasks in the database. "Top three" remains the default in the UI.
- Decision window: not a setting. "Decide within 48 hours" appears only as wording in the UI.
- Let go: allowed from Inbox and Booked only. An item in Learning is finished or returned first.
- PRD open calls, taken as proposed:
  - Success targets in PRD section 03 stand.
  - Marking an item learned requires a one-line note.
  - Learning slots: Mon, Wed, Fri at 16:00 and Sat at 10:00, 45 minutes.
  - Life goals sit beside work goals in the same tree.
- Secrets live outside the repo in `~/.config/compass/secrets.env`.
- Mockup reference: `docs/html/Compass Planner.html`.

## 23 November 2026 (phase 0 build)

- Revisit list: a resurfaced item gets one day on the list, then leaves until its next step. At most three a day; items that do not fit wait for the next day.
- Catch-up: after a sleep the morning run replays each missed day in order, so the list matches an always-on system (AP-4).
- Booking in phase 0, from a drag or the bot's Book button, takes the next learning slot from settings. The item dialog can also pick a time.
- Marking learned took an optional note in phase 0. From phase 1 it is required (LQ-6).

## 23 November 2026 (phase 1 build)

- Guided setup has four steps, not three: themes, quarter goals, month milestones, then weekly outcomes. A weekly outcome needs a milestone as its parent (GO-2), so the milestone step cannot be skipped.
- Goal limits (3 themes, 5 quarter goals, 3 weekly outcomes) are fixed rules in the planning service, not settings. Month milestones have no limit.
- Quarter goals carry a short label and one of five colours. A task or item shows the label and colour of the quarter goal it sits under.
- Quarter pages show progress only. Pace and the on-track, at-risk and behind labels arrive in phase 3 (GO-7).
- A goal-linked item in the inbox still comes back on days 3, 7 and 14, then waits for a learning block. It gets no last ask and never expires (LQ-7). Removing the goal picks its schedule back up the next morning.
- A capture can carry a goal and a one-line reason. The reason is stored on the item (`learning_items.reason`).
- Plan tomorrow plans the next calendar day. Dropping a task keeps its row with `dropped_at` set, so the weekly review can still count it. Dropped tasks leave Today and the week board.
- Evening shutdown: steps one to three are ticks on the card (step three ticks itself once tomorrow is planned). The fourth step needs the learned line and closes the day in `daily_logs`.
- Learning holds at most two items (LQ-8). A new move, return, takes an item from Learning back to Booked on the next free slot and keeps its start time. Starting a third item asks you to finish or return one. Dragging a card into Learned opens the note dialog.
