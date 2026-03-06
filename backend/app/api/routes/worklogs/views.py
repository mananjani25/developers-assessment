"""WorkLog API views — list all worklogs with filtering."""

from typing import Any

from fastapi import APIRouter, Query

from app.api.deps import CurrentUser, SessionDep
from app.api.routes.worklogs.service import WorkLogService
from app.models import WorkLogListResponse

router = APIRouter(prefix="/worklogs", tags=["worklogs"])


@router.get(
    "/list-all-worklogs",
    response_model=WorkLogListResponse,
    summary="List all worklogs",
    description=(
        "Lists all worklogs with computed amounts and remittance status. "
        "Optionally filter by remittanceStatus=REMITTED or UNREMITTED."
    ),
)
def list_all_worklogs(
    session: SessionDep,
    current_user: CurrentUser,
    remittanceStatus: str | None = Query(
        default=None,
        description="Filter by remittance status: REMITTED or UNREMITTED",
        examples=["REMITTED", "UNREMITTED"],
    ),
) -> Any:
    """List all worklogs with filtering and amount information."""
    return WorkLogService.list_worklogs(session, remittanceStatus)
