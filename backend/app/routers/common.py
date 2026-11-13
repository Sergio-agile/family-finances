"""Helpers shared by the routers of household money: expenses and incomes."""

from datetime import date
from typing import Annotated

from fastapi import HTTPException, Query, status
from sqlalchemy import delete, exists, select
from sqlalchemy.orm import Session

from app.models import Expense, Income, Membership

# What these helpers work on: rows that belong to a household and are found by id inside it.
type Entry = Expense | Income

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


def get_in_household[E: (Expense, Income)](
    session: Session, model: type[E], id_: int, household_id: int
) -> E:
    """The row with this id, looked up inside the household: another household's row is as
    missing as a wrong id (404, "Expense not found")."""
    entry = session.scalar(select(model).where(model.id == id_, model.household_id == household_id))
    if entry is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, f"{model.__name__} not found")
    return entry


def apply_changes(session: Session, entry: Entry, changes: dict) -> None:
    """Save a partial update: only the fields the client sent."""
    for field, value in changes.items():
        setattr(entry, field, value)
    session.commit()
    session.refresh(entry)


def delete_in_household(session: Session, model: type[Entry], id_: int, household_id: int) -> None:
    """Delete for good (there is no trash). One statement, scoped to the household: nothing is
    loaded just to be deleted, and another household's row is a 404 like a wrong id."""
    deleted = session.execute(
        delete(model).where(model.id == id_, model.household_id == household_id)
    )
    if deleted.rowcount == 0:
        raise HTTPException(status.HTTP_404_NOT_FOUND, f"{model.__name__} not found")
    session.commit()
