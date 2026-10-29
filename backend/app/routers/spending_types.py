from fastapi import APIRouter
from sqlalchemy import select

from app.db import SessionDep
from app.models import SpendingType
from app.schemas import SpendingTypeRead

router = APIRouter(prefix="/api/spending-types", tags=["spending types"])


@router.get("", response_model=list[SpendingTypeRead])
def list_spending_types(session: SessionDep) -> list[SpendingType]:
    """In seed order, which goes from essential to optional spending, not alphabetically."""
    return list(session.scalars(select(SpendingType).order_by(SpendingType.id)))
