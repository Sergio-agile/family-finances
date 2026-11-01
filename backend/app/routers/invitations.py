from fastapi import APIRouter, Request, status

from app.auth import CurrentHousehold
from app.db import SessionDep
from app.invitations import create_invitation, invitation_url
from app.schemas import InvitationRead

router = APIRouter(prefix="/api/households/{household_id}/invitations", tags=["invitations"])


@router.post("", status_code=status.HTTP_201_CREATED)
def invite_to_household(
    household: CurrentHousehold, session: SessionDep, request: Request
) -> InvitationRead:
    """A one-time sign-up link that joins this household. Any member can create one."""
    invitation, token = create_invitation(session, household.id)
    # The URL the browser used, so a link made from a phone on the LAN works from that LAN.
    return InvitationRead(
        url=invitation_url(str(request.base_url), token), expires_at=invitation.expires_at
    )
