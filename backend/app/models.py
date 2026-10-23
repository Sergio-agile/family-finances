from datetime import date, datetime

from sqlalchemy import DateTime, ForeignKey, String, func
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


class Base(DeclarativeBase):
    pass


class Category(Base):
    __tablename__ = "categories"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(50), unique=True)


class Expense(Base):
    __tablename__ = "expenses"

    id: Mapped[int] = mapped_column(primary_key=True)
    # Money is stored as integer cents to avoid floating-point rounding errors.
    amount_cents: Mapped[int]
    concept: Mapped[str] = mapped_column(String(200))
    category_id: Mapped[int] = mapped_column(ForeignKey("categories.id"), index=True)
    spent_on: Mapped[date] = mapped_column(index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    category: Mapped[Category] = relationship()
