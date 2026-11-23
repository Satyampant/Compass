"""HTTP API for the status page."""

from fastapi import APIRouter
from fastapi.responses import JSONResponse

from app.kernel.db import SessionDep
from app.modules.system import export
from app.modules.system import status as status_module

router = APIRouter(prefix="/v1", tags=["system"])


@router.get("/status")
def status(session: SessionDep) -> status_module.Status:
    return status_module.status(session)


@router.get("/export")
def export_all(session: SessionDep) -> JSONResponse:
    """All of your data as one JSON file."""
    data = export.export(session)
    name = f"compass-export-{data['exported_at'][:10]}.json"
    return JSONResponse(data, headers={"Content-Disposition": f'attachment; filename="{name}"'})
