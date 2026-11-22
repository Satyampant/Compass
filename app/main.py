"""Compass: one process serving the API, the web app and the scheduler."""

from fastapi import FastAPI

app = FastAPI(title="Compass")


@app.get("/healthz")
def healthz() -> dict[str, str]:
    """Report that the process is up."""
    return {"status": "ok"}
