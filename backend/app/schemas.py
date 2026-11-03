from datetime import date, datetime
from typing import Annotated, Literal

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
PersonName = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=50)]
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


class MemberRead(BaseModel):
    """A household member as other members see them: name only, never the email."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str


class ExpenseCreate(BaseModel):
    amount_cents: int = Field(gt=0, description="Amount in cents: 12.50 € is 1250")
    concept: Concept
    category_id: int
    spending_type_id: int | None = None
    paid_by_id: int | None = Field(
        default=None, description="The member who paid; null: not assigned yet"
    )
    # Fallback only: the client should send the date in the user's own timezone.
    spent_on: date = Field(default_factory=date.today)


class ExpenseUpdate(BaseModel):
    """Partial update: only the fields sent are changed. `null` unassigns the optional
    `spending_type_id` and `paid_by_id`."""

    amount_cents: int | None = Field(default=None, gt=0)
    concept: Concept | None = None
    category_id: int | None = None
    spending_type_id: int | None = None
    paid_by_id: int | None = None
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
    paid_by: MemberRead | None
    created_by: MemberRead
    created_at: datetime


class SignUp(BaseModel):
    name: PersonName
    email: Email
    # Length is what makes a password strong; no composition rules (NIST SP 800-63B).
    password: str = Field(min_length=12, max_length=128)
    # Sign-up is by invitation only: the new account joins the household that invited it.
    invitation_token: str = Field(max_length=100)


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
    name: str
    email: str
    households: list[HouseholdRead]


class InvitationRead(BaseModel):
    url: str
    expires_at: datetime


# What an API token may do. `expenses:write` implies `expenses:read` (see app.auth).
Scope = Literal["expenses:read", "expenses:write"]
TokenName = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=50)]


class ApiTokenCreate(BaseModel):
    name: TokenName = Field(examples=["n8n bank import"])
    # A set: the same scope twice is the same permission.
    scopes: set[Scope] = Field(min_length=1, examples=[["expenses:write"]])


class ApiTokenRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    scopes: list[Scope]
    created_at: datetime
    last_used_at: datetime | None


class ApiTokenCreated(ApiTokenRead):
    token: str = Field(description="Shown only now: store it, it cannot be retrieved again")
