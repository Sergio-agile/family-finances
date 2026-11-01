from datetime import date, datetime
from typing import Annotated

from pydantic import (
    AfterValidator,
    BaseModel,
    ConfigDict,
    EmailStr,
    Field,
    StringConstraints,
    field_validator,
)

Concept = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=200)]
# Lowercased so "Ana@Example.com" and "ana@example.com" are the same account.
Email = Annotated[EmailStr, AfterValidator(str.lower)]


class CategoryRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str


class SpendingTypeRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str


class ExpenseCreate(BaseModel):
    amount_cents: int = Field(gt=0, description="Amount in cents: 12.50 € is 1250")
    concept: Concept
    category_id: int
    spending_type_id: int | None = None
    # Fallback only: the client should send the date in the user's own timezone.
    spent_on: date = Field(default_factory=date.today)


class ExpenseUpdate(BaseModel):
    """Partial update: only the fields sent are changed. `spending_type_id: null` unclassifies."""

    amount_cents: int | None = Field(default=None, gt=0)
    concept: Concept | None = None
    category_id: int | None = None
    spending_type_id: int | None = None
    spent_on: date | None = None

    @field_validator("amount_cents", "concept", "category_id", "spent_on")
    @classmethod
    def reject_null(cls, value: object) -> object:
        # Omitting these fields is fine; sending them as null is not, their columns are NOT NULL.
        if value is None:
            raise ValueError("cannot be null")
        return value


class ExpenseRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    amount_cents: int
    concept: str
    spent_on: date
    category: CategoryRead
    spending_type: SpendingTypeRead | None
    created_at: datetime


class SignUp(BaseModel):
    email: Email
    # Length is what makes a password strong; no composition rules (NIST SP 800-63B).
    password: str = Field(min_length=12, max_length=128)


class LogIn(BaseModel):
    email: Email
    # No min_length: logging in checks the stored hash, not today's password policy.
    password: str = Field(max_length=128)


class HouseholdRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str


class UserRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    email: str
    households: list[HouseholdRead]
