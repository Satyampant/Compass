# Compass

A personal planning system that runs on your Mac. See `docs/md/` for the PRD, architecture and build plan, and `docs/decisions.md` for changes since.

## Run

```
make install     # build the web app, start Compass at login (launchd), open http://localhost:8000
make restart     # restart after pulling changes
make logs        # follow ~/Library/Logs/Compass/compass.log
make uninstall   # stop and remove the login item
```

Secrets live in `~/.config/compass/secrets.env` (`TELEGRAM_BOT_TOKEN=...`). After install, send `/start` to the bot from your phone: the first chat to do so is the only one it will answer.

## Develop

```
make dev     # API on :8001 without the scheduler or bot, so it never clashes with the service
cd web && npm run dev   # web on :5173, proxied to :8001
make test    # unit tests, fake clock, no network
make e2e     # browser checks in Chrome against a throwaway database
make lint    # ruff
```
