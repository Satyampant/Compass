"""HTTP API for the status page."""

from fastapi import APIRouter

from app.kernel.db import SessionDep
from app.modules.system import status as status_module

router = APIRouter(prefix="/v1", tags=["system"])


@router.get("/status")
def status(session: SessionDep) -> status_module.Status:
    return status_module.status(session)
