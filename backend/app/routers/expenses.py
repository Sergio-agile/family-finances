from datetime import date
from typing import Annotated

from fastapi import APIRouter, HTTPException, Query, status
from sqlalchemy import select
from sqlalchemy.orm import selectinload

from app.db import SessionDep
from app.models import Category, Expense, SpendingType
from app.schemas import ExpenseCreate, ExpenseRead

router = APIRouter(prefix="/api/expenses", tags=["expenses"])

# Required: the month bounds the list, so the response never grows with the whole history.
Month = Annotated[str, Query(pattern=r"^\d{4}-(0[1-9]|1[0-2])$", examples=["2026-10"])]


@router.get("", response_model=list[ExpenseRead])
def list_expenses(session: SessionDep, month: Month) -> list[Expense]:
    """Expenses of one month (YYYY-MM), newest first."""
    year, month_number = map(int, month.split("-"))
    start = date(year, month_number, 1)
    end = date(year + month_number // 12, month_number % 12 + 1, 1)
    query = (
        select(Expense)
        .options(selectinload(Expense.category), selectinload(Expense.spending_type))
        .where(Expense.spent_on >= start, Expense.spent_on < end)
        .order_by(Expense.spent_on.desc(), Expense.id.desc())
    )
    return list(session.scalars(query))


@router.post("", response_model=ExpenseRead, status_code=status.HTTP_201_CREATED)
def create_expense(payload: ExpenseCreate, session: SessionDep) -> Expense:
    if session.get(Category, payload.category_id) is None:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_CONTENT, "Category does not exist")
    if (
        payload.spending_type_id is not None
        and session.get(SpendingType, payload.spending_type_id) is None
    ):
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_CONTENT, "Spending type does not exist")

    expense = Expense(**payload.model_dump())
    session.add(expense)
    session.commit()
    session.refresh(expense)
    return expense
