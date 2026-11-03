from fastapi import APIRouter
from sqlalchemy import select

from app.auth import ReadableHousehold
from app.db import SessionDep
from app.models import Membership, User
from app.schemas import MemberRead

router = APIRouter(prefix="/api/households/{household_id}", tags=["households"])


@router.get("/members", response_model=list[MemberRead])
def list_members(household: ReadableHousehold, session: SessionDep) -> list[User]:
    """The household's members, by name. Small by nature (a family), so not paginated."""
    query = (
        select(User)
        .join(Membership)
        .where(Membership.household_id == household.id)
        .order_by(User.name, User.id)
    )
    return list(session.scalars(query))
