"""HTTP API for the status page."""

from fastapi import APIRouter, HTTPException
from fastapi.responses import JSONResponse

from app.kernel.db import SessionDep
from app.modules.system import export, rules
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


@router.get("/settings")
def get_settings(session: SessionDep) -> dict:
    """The rules from PRD section 08 with their current values."""
    return rules.current(session)


@router.put("/settings")
def put_settings(changes: dict, session: SessionDep) -> dict:
    """Change some rules. Every value is checked before any is stored."""
    try:
        values = rules.update(session, changes)
    except rules.RuleError as exc:
        raise HTTPException(422, str(exc)) from exc
    session.commit()
    return values
