"""Compass: one process serving the API, the web app and the scheduler."""

from fastapi import FastAPI

from app.modules.capture.router import router as capture_router
from app.modules.day.router import router as day_router
from app.modules.learning.router import router as learning_router

app = FastAPI(title="Compass")
app.include_router(capture_router)
app.include_router(learning_router)
app.include_router(day_router)


@app.get("/healthz")
def healthz() -> dict[str, str]:
    """Report that the process is up."""
    return {"status": "ok"}
