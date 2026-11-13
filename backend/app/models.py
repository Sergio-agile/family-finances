from datetime import date, datetime

from sqlalchemy import (
    ARRAY,
    DateTime,
    ForeignKey,
    Index,
    LargeBinary,
    MetaData,
    String,
    UniqueConstraint,
    func,
)
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
    # Every query filters by household and then by date: one composite index serves both.
    __table_args__ = (Index("ix_expenses_household_id_spent_on", "household_id", "spent_on"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    household_id: Mapped[int] = mapped_column(ForeignKey("households.id", ondelete="CASCADE"))
    # Money is stored as integer cents to avoid floating-point rounding errors.
    amount_cents: Mapped[int]
    concept: Mapped[str] = mapped_column(String(200))
    category_id: Mapped[int] = mapped_column(ForeignKey("categories.id"), index=True)
    # Optional: an expense can be classified when created or later on.
    spending_type_id: Mapped[int | None] = mapped_column(
        ForeignKey("spending_types.id"), index=True
    )
    spent_on: Mapped[date]
    # Who wrote it down: set by the API from the session, never editable.
    created_by_id: Mapped[int] = mapped_column(ForeignKey("users.id"))
    # Whose money paid it, whoever it was for. None: not assigned yet (the app flags it).
    paid_by_id: Mapped[int | None] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    category: Mapped[Category] = relationship()
    spending_type: Mapped[SpendingType | None] = relationship()
    # Two foreign keys to users, so each relationship says which one it follows.
    created_by: Mapped["User"] = relationship(foreign_keys=[created_by_id])
    paid_by: Mapped["User | None"] = relationship(foreign_keys=[paid_by_id])


class Income(Base):
    """Money coming into the household: a salary, a refund, a sale... Kept apart from expenses,
    which carry fields an income has no use for (ADR 0013)."""

    __tablename__ = "incomes"
    # Same access pattern as expenses: by household, then by month.
    __table_args__ = (Index("ix_incomes_household_id_received_on", "household_id", "received_on"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    household_id: Mapped[int] = mapped_column(ForeignKey("households.id", ondelete="CASCADE"))
    amount_cents: Mapped[int]
    concept: Mapped[str] = mapped_column(String(200))
    received_on: Mapped[date]
    created_by_id: Mapped[int] = mapped_column(ForeignKey("users.id"))
    # Who received it, to compare each member's income with what they paid. None: not assigned yet.
    received_by_id: Mapped[int | None] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    created_by: Mapped["User"] = relationship(foreign_keys=[created_by_id])
    received_by: Mapped["User | None"] = relationship(foreign_keys=[received_by_id])


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(primary_key=True)
    # Stored lowercased (see schemas.Email), so the unique constraint is case-insensitive.
    email: Mapped[str] = mapped_column(String(254), unique=True)
    # How the household sees this person ("Ana"): the email is never shown to other members.
    name: Mapped[str] = mapped_column(String(50))
    # Argon2id hash in PHC format: algorithm, parameters and salt travel with the hash.
    password_hash: Mapped[str] = mapped_column(String(200))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    households: Mapped[list["Household"]] = relationship(
        secondary="memberships", order_by="Household.id"
    )


class UserSession(Base):
    """A logged-in browser. The cookie holds a random token; only its SHA-256 is stored, so a
    leaked database cannot be replayed as cookies."""

    __tablename__ = "sessions"

    id: Mapped[int] = mapped_column(primary_key=True)
    token_hash: Mapped[bytes] = mapped_column(LargeBinary(32), unique=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))


class ApiToken(Base):
    """A personal access token for scripts and integrations (n8n), sent as `Authorization: Bearer
    ff_…`. It acts as its user, limited to its scopes. As with sessions, only its SHA-256 is
    stored; the token itself is shown once, when it is created."""

    __tablename__ = "api_tokens"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    # What it is for ("n8n bank import"), so the user knows which one to revoke.
    name: Mapped[str] = mapped_column(String(50))
    token_hash: Mapped[bytes] = mapped_column(LargeBinary(32), unique=True)
    scopes: Mapped[list[str]] = mapped_column(ARRAY(String(30)))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    # A token unused for months can go; one used when it shouldn't be is a warning sign.
    last_used_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    user: Mapped[User] = relationship()


class Household(Base):
    """A family: its members share every expense in it. A user can belong to several."""

    __tablename__ = "households"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(100))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class Membership(Base):
    __tablename__ = "memberships"
    # Also the index for "is this user a member of this household?" and "this user's households".
    __table_args__ = (UniqueConstraint("user_id", "household_id"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"))
    household_id: Mapped[int] = mapped_column(ForeignKey("households.id", ondelete="CASCADE"))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class Invitation(Base):
    """A one-time link to join a household. As with sessions, only the token's hash is stored."""

    __tablename__ = "invitations"

    id: Mapped[int] = mapped_column(primary_key=True)
    household_id: Mapped[int] = mapped_column(
        ForeignKey("households.id", ondelete="CASCADE"), index=True
    )
    token_hash: Mapped[bytes] = mapped_column(LargeBinary(32), unique=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))


class AuthFailure(Base):
    """A failed login or sign-up, kept for a few minutes to throttle password guessing."""

    __tablename__ = "auth_failures"
    # The two lookups: recent failures of one account, and of one address.
    __table_args__ = (
        Index("ix_auth_failures_email_created_at", "email", "created_at"),
        Index("ix_auth_failures_ip_created_at", "ip", "created_at"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    # None for sign-up failures: they count against the address only.
    email: Mapped[str | None] = mapped_column(String(254))
    ip: Mapped[str] = mapped_column(String(45))  # long enough for IPv6
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
