#!/bin/zsh
# Start Compass on 127.0.0.1:8000. launchd runs this at login and restarts it if it exits.
export PATH="/opt/homebrew/bin:/usr/local/bin:/usr/bin:/bin"
cd "${0:A:h}/.."
exec uv run uvicorn app.main:app --host 127.0.0.1 --port 8000
