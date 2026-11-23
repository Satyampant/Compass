# Phase 2 acceptance

Automated checks: `make test` (includes `tests/test_acceptance_p2.py`) and `make e2e`.
The checks below need real Google, the phone or a week of use, so they are done by hand.

## Once: connect Google Calendar

1. Open https://console.cloud.google.com and create a project named Compass.
2. APIs and services, Library: enable **Google Calendar API**.
3. Google Auth Platform, Branding: app name Compass, your email as support and developer contact. Audience: External, and add your Google account as a test user.
4. Data access, Add scopes: `.../auth/calendar.readonly` and `.../auth/calendar.app.created`.
5. Audience: **Publish app**. While an app is in testing, Google expires its refresh tokens after 7 days. Published but unverified is fine for one person; you click through one warning at sign-in.
6. Clients, Create client, type **Desktop app**. Copy the client ID and secret into `~/.config/compass/secrets.env`:
   ```
   GOOGLE_CLIENT_ID=...
   GOOGLE_CLIENT_SECRET=...
   ```
7. Run `make google-signin`, approve in the browser, then `make restart`.

## Checks

| # | Check | Pass when |
|---|-------|-----------|
| 1 | Restart the Mac and log in. Open Compass. | No calendar banner. Sign-in was not asked for again. |
| 2 | Add a meeting for today in Google Calendar. | Within ten minutes it is in Today's time blocks. Delete it: within ten minutes it is gone. |
| 3 | Look at Google Calendar. | A calendar named Compass holds this week's and next week's learning blocks, each with an item if the queue has enough that fit. |
| 4 | Hide the Compass calendar in Google Calendar. | Every block Compass made disappears, and nothing else does. |
| 5 | Put a meeting on a learning slot. | Within ten minutes the slot moves to the next free 45 minutes that day. |
| 6 | Wait for a learning block. | Fifteen minutes before, the phone gets the reminder with the item's title and link. |
| 7 | Plan tomorrow and commit. | Tomorrow's task blocks are in the Compass calendar. |
| 8 | Leave the day open past 19:30. | The shutdown nudge arrives. Close the day first on another evening: no nudge. |
| 9 | Run `make google-signout`, then open every screen. | Everything works and the calendar banner shows. Sign in again afterwards. |

## A week of protected blocks

Use the learning blocks for a week. At least two must be kept (started).

| Block | Item | Kept |
|-------|------|------|
| Mon 16:00 | | |
| Wed 16:00 | | |
| Fri 16:00 | | |
| Sat 10:00 | | |
