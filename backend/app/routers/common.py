"""Helpers shared by the routers of household money: expenses and incomes."""

from datetime import date
from typing import Annotated

from fastapi import HTTPException, Query, status
from sqlalchemy import exists, select
from sqlalchemy.orm import Session

from app.models import Membership

# Required: the month bounds the list, so the response never grows with the whole history.
Month = Annotated[str, Query(pattern=r"^\d{4}-(0[1-9]|1[0-2])$", examples=["2026-10"])]


def month_bounds(month: str) -> tuple[date, date]:
    """ "2026-10" → (2026-10-01, 2026-11-01): the first day, and the first day after the month."""
    year, month_number = map(int, month.split("-"))
    return date(year, month_number, 1), date(year + month_number // 12, month_number % 12 + 1, 1)


def ensure_member(session: Session, household_id: int, user_id: int | None, label: str) -> None:
    """Reject, with a clear 422, a person who is not in the household. None is not checked."""
    is_member = exists().where(
        Membership.user_id == user_id, Membership.household_id == household_id
    )
    if user_id is not None and not session.scalar(select(is_member)):
        raise HTTPException(
            status.HTTP_422_UNPROCESSABLE_CONTENT, f"{label} does not belong to this household"
        )
