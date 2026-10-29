from datetime import date, datetime
from typing import Annotated

from pydantic import BaseModel, ConfigDict, Field, StringConstraints, field_validator

Concept = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=200)]


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
