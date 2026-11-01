from datetime import date
from typing import Annotated

from fastapi import APIRouter, HTTPException, Query, status
from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.auth import CurrentHousehold
from app.db import SessionDep
from app.models import Category, Expense, SpendingType
from app.schemas import ExpenseCreate, ExpenseRead, ExpenseUpdate

router = APIRouter(prefix="/api/households/{household_id}/expenses", tags=["expenses"])

# Required: the month bounds the list, so the response never grows with the whole history.
Month = Annotated[str, Query(pattern=r"^\d{4}-(0[1-9]|1[0-2])$", examples=["2026-10"])]


def ensure_references_exist(
    session: Session, category_id: int | None, spending_type_id: int | None
) -> None:
    """Reject ids of missing categories or spending types with a clear 422 (None: not given)."""
    for model, id_, label in [
        (Category, category_id, "Category"),
        (SpendingType, spending_type_id, "Spending type"),
    ]:
        if id_ is not None and session.get(model, id_) is None:
            raise HTTPException(status.HTTP_422_UNPROCESSABLE_CONTENT, f"{label} does not exist")


@router.get("", response_model=list[ExpenseRead])
def list_expenses(household: CurrentHousehold, session: SessionDep, month: Month) -> list[Expense]:
    """The household's expenses of one month (YYYY-MM), newest first."""
    year, month_number = map(int, month.split("-"))
    start = date(year, month_number, 1)
    end = date(year + month_number // 12, month_number % 12 + 1, 1)
    query = (
        select(Expense)
        .options(selectinload(Expense.category), selectinload(Expense.spending_type))
        .where(
            Expense.household_id == household.id,
            Expense.spent_on >= start,
            Expense.spent_on < end,
        )
        .order_by(Expense.spent_on.desc(), Expense.id.desc())
    )
    return list(session.scalars(query))


@router.post("", response_model=ExpenseRead, status_code=status.HTTP_201_CREATED)
def create_expense(
    payload: ExpenseCreate, household: CurrentHousehold, session: SessionDep
) -> Expense:
    ensure_references_exist(session, payload.category_id, payload.spending_type_id)

    expense = Expense(**payload.model_dump(), household_id=household.id)
    session.add(expense)
    session.commit()
    session.refresh(expense)
    return expense


@router.patch("/{expense_id}", response_model=ExpenseRead)
def update_expense(
    expense_id: int, payload: ExpenseUpdate, household: CurrentHousehold, session: SessionDep
) -> Expense:
    # Looked up inside the household: another household's expense is as missing as a wrong id.
    expense = session.scalar(
        select(Expense).where(Expense.id == expense_id, Expense.household_id == household.id)
    )
    if expense is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Expense not found")

    # Only what the client sent: an omitted field stays as it is.
    changes = payload.model_dump(exclude_unset=True)
    ensure_references_exist(session, changes.get("category_id"), changes.get("spending_type_id"))

    for field, value in changes.items():
        setattr(expense, field, value)
    session.commit()
    session.refresh(expense)
    return expense
