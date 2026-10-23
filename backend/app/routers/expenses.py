from datetime import date
from typing import Annotated

from fastapi import APIRouter, HTTPException, Query, status
from sqlalchemy import select
from sqlalchemy.orm import selectinload

from app.db import SessionDep
from app.models import Category, Expense
from app.schemas import ExpenseCreate, ExpenseRead

router = APIRouter(prefix="/api/expenses", tags=["expenses"])

Month = Annotated[str | None, Query(pattern=r"^\d{4}-(0[1-9]|1[0-2])$", examples=["2026-10"])]


@router.get("", response_model=list[ExpenseRead])
def list_expenses(session: SessionDep, month: Month = None) -> list[Expense]:
    """Expenses, newest first. Optionally only those of one month (YYYY-MM)."""
    query = (
        select(Expense)
        .options(selectinload(Expense.category))
        .order_by(Expense.spent_on.desc(), Expense.id.desc())
    )
    if month:
        year, month_number = map(int, month.split("-"))
        start = date(year, month_number, 1)
        end = date(year + month_number // 12, month_number % 12 + 1, 1)
        query = query.where(Expense.spent_on >= start, Expense.spent_on < end)
    return list(session.scalars(query))


@router.post("", response_model=ExpenseRead, status_code=status.HTTP_201_CREATED)
def create_expense(payload: ExpenseCreate, session: SessionDep) -> Expense:
    if session.get(Category, payload.category_id) is None:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_CONTENT, "Category does not exist")

    expense = Expense(**payload.model_dump())
    session.add(expense)
    session.commit()
    session.refresh(expense)
    return expense
