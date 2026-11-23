"""Compass: one process serving the API, the web app and the scheduler."""

import logging
import os
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

import app.handlers  # noqa: F401
from app.kernel import config, migrate, scheduler
from app.kernel.db import ROOT
from app.modules.capture.router import router as capture_router
from app.modules.day.router import router as day_router
from app.modules.day.today import router as today_router
from app.modules.integrations.telegram import Telegram
from app.modules.learning.router import router as learning_router
from app.modules.notify.bot import Poller
from app.modules.planning.router import router as planning_router

WEB = ROOT / "web" / "dist"
log = logging.getLogger("compass")


@asynccontextmanager
async def lifespan(_: FastAPI):
    """Migrate, then start the scheduler and the Telegram poller unless switched off."""
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s %(message)s")
    logging.getLogger("httpx").setLevel(logging.WARNING)  # request URLs carry the bot token
    migrate.upgrade()
    scheduler.startup()
    threads = []
    if os.environ.get("COMPASS_BACKGROUND", "1") == "1":
        threads.append(scheduler.Scheduler())
        token = config.secret("TELEGRAM_BOT_TOKEN")
        if token:
            threads.append(Poller(Telegram(token)))
        else:
            log.warning("no TELEGRAM_BOT_TOKEN, the bot is off")
    for t in threads:
        t.start()
    yield
    for t in threads:
        t.stop()


app = FastAPI(title="Compass", lifespan=lifespan)
app.include_router(capture_router)
app.include_router(learning_router)
app.include_router(day_router)
app.include_router(today_router)
app.include_router(planning_router)


@app.get("/healthz")
def healthz() -> dict[str, str]:
    """Report that the process is up."""
    return {"status": "ok"}


if WEB.exists():
    app.mount("/assets", StaticFiles(directory=WEB / "assets"), name="assets")

    @app.get("/{path:path}", include_in_schema=False)
    def web(path: str) -> FileResponse:
        """Serve the built web app. Unknown paths get index.html, unknown API paths a 404."""
        if path.startswith("v1/"):
            raise HTTPException(404, "not found")
        file = WEB / path
        return FileResponse(file if path and file.is_file() else WEB / "index.html")
