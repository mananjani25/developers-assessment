"""Remittance API views — generate remittances for all users."""

from typing import Any

from fastapi import APIRouter

from app.api.deps import CurrentUser, SessionDep
from app.api.routes.remittances.service import RemittanceService
from app.models import RemittanceGenerateResponse

router = APIRouter(prefix="/remittances", tags=["remittances"])


@router.post(
    "/generate-remittances-for-all-users",
    response_model=RemittanceGenerateResponse,
    summary="Generate remittances for all users",
    description=(
        "Runs a settlement pass for all users. Calculates delta amounts "
        "(current worklog value minus previously settled amounts) and creates "
        "remittance records for each user with outstanding balances."
    ),
)
def generate_remittances_for_all_users(
    session: SessionDep,
    current_user: CurrentUser,
) -> Any:
    """Generate remittances for all users based on eligible work."""
    return RemittanceService.generate_remittances(session)
