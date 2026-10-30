from datetime import date, datetime

from sqlalchemy import DateTime, ForeignKey, LargeBinary, MetaData, String, func
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


class Base(DeclarativeBase):
    # The same names Postgres picks by default, so Alembic always knows how to drop a constraint.
    metadata = MetaData(
        naming_convention={
            "ix": "ix_%(column_0_label)s",
            "uq": "%(table_name)s_%(column_0_name)s_key",
            "fk": "%(table_name)s_%(column_0_name)s_fkey",
            "pk": "%(table_name)s_pkey",
        }
    )


class Category(Base):
    __tablename__ = "categories"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(50), unique=True)


class SpendingType(Base):
    """What kind of spending an expense is (basic, luxury...), independent of its category."""

    __tablename__ = "spending_types"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(50), unique=True)


class Expense(Base):
    __tablename__ = "expenses"

    id: Mapped[int] = mapped_column(primary_key=True)
    # Money is stored as integer cents to avoid floating-point rounding errors.
    amount_cents: Mapped[int]
    concept: Mapped[str] = mapped_column(String(200))
    category_id: Mapped[int] = mapped_column(ForeignKey("categories.id"), index=True)
    # Optional: an expense can be classified when created or later on.
    spending_type_id: Mapped[int | None] = mapped_column(
        ForeignKey("spending_types.id"), index=True
    )
    spent_on: Mapped[date] = mapped_column(index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    category: Mapped[Category] = relationship()
    spending_type: Mapped[SpendingType | None] = relationship()


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(primary_key=True)
    # Stored lowercased (see schemas.Email), so the unique constraint is case-insensitive.
    email: Mapped[str] = mapped_column(String(254), unique=True)
    # Argon2id hash in PHC format: algorithm, parameters and salt travel with the hash.
    password_hash: Mapped[str] = mapped_column(String(200))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class UserSession(Base):
    """A logged-in browser. The cookie holds a random token; only its SHA-256 is stored, so a
    leaked database cannot be replayed as cookies."""

    __tablename__ = "sessions"

    id: Mapped[int] = mapped_column(primary_key=True)
    token_hash: Mapped[bytes] = mapped_column(LargeBinary(32), unique=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
