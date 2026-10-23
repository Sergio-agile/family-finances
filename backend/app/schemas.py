from datetime import date, datetime
from typing import Annotated

from pydantic import BaseModel, ConfigDict, Field, StringConstraints

Concept = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=200)]


class CategoryRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str


class ExpenseCreate(BaseModel):
    amount_cents: int = Field(gt=0, description="Amount in cents: 12.50 € is 1250")
    concept: Concept
    category_id: int
    # Fallback only: the client should send the date in the user's own timezone.
    spent_on: date = Field(default_factory=date.today)


class ExpenseRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    amount_cents: int
    concept: str
    spent_on: date
    category: CategoryRead
    created_at: datetime
