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
