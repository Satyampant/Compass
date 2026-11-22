# Phase 0 acceptance

Automated checks: `make test` (includes `tests/test_acceptance_p0.py`, `tests/test_resurface.py`) and `make e2e`.
The checks below need your phone, the lid or a restart, so they are done by hand.

## Once

1. Open Telegram on the phone, find the Compass bot and send `/start`. It replies "Compass is connected to this chat."
2. Open http://localhost:8000 on the Mac.

## Checks

| # | Check | Pass when |
|---|-------|-----------|
| 1 | Close the lid. From Chrome or YouTube on the phone, share a link to the Compass bot. Open the lid. | Within a minute the link is in the Inbox and the chat shows "Saved". |
| 2 | Share the same link again. | The chat says "Already saved…", and the queue still has one card. |
| 3 | Share plain text, then tap "Task". | The task is on Today. |
| 4 | On the Mac, press C, paste a link, press Enter. | Saved in under five seconds, from any screen. |
| 5 | Restart the Mac and log in. Do nothing. | http://localhost:8000 answers. |
| 6 | Three days after check 1, at the first wake after 06:00. | The link is in "Time to revisit" and in a Telegram brief with Book and Let go. |
| 7 | Tap Let go on a brief item, then reload the web app. | The item is gone from every list. |

Then use it for a week and share at least five real links from the phone.
