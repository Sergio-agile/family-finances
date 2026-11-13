from fastapi import APIRouter, status
from sqlalchemy import select
from sqlalchemy.orm import selectinload

from app.auth import CurrentHousehold, CurrentUser
from app.db import SessionDep
from app.models import Income
from app.routers.common import Month, ensure_member, month_bounds
from app.schemas import IncomeCreate, IncomeRead

router = APIRouter(prefix="/api/households/{household_id}/incomes", tags=["incomes"])


@router.get("", response_model=list[IncomeRead])
def list_incomes(household: CurrentHousehold, session: SessionDep, month: Month) -> list[Income]:
    """The household's incomes of one month (YYYY-MM), newest first."""
    start, end = month_bounds(month)
    query = (
        select(Income)
        .options(selectinload(Income.received_by), selectinload(Income.created_by))
        .where(
            Income.household_id == household.id,
            Income.received_on >= start,
            Income.received_on < end,
        )
        .order_by(Income.received_on.desc(), Income.id.desc())
    )
    return list(session.scalars(query))


@router.post("", response_model=IncomeRead, status_code=status.HTTP_201_CREATED)
def create_income(
    payload: IncomeCreate, household: CurrentHousehold, user: CurrentUser, session: SessionDep
) -> Income:
    ensure_member(session, household.id, payload.received_by_id, "Recipient")

    income = Income(**payload.model_dump(), household_id=household.id, created_by_id=user.id)
    session.add(income)
    session.commit()
    session.refresh(income)
    return income
