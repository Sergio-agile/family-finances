"""One-time invitation links to join a household.

Sign-up needs an invitation. The first account of a new household gets one from the command
line: `uv run python -m app.invitations "Casa García"`.
"""

import argparse
from datetime import UTC, datetime, timedelta

from sqlalchemy import delete
from sqlalchemy.orm import Session

from app.auth import hash_token, new_token
from app.config import settings
from app.db import engine
from app.models import Household, Invitation

INVITATION_TTL = timedelta(days=7)


def create_invitation(session: Session, household_id: int) -> tuple[Invitation, str]:
    """Store a new invitation and return it with its token, which is only known now."""
    # Expired invitations are cleaned up here, so the table does not grow forever.
    session.execute(
        delete(Invitation).where(
            Invitation.household_id == household_id, Invitation.expires_at <= datetime.now(UTC)
        )
    )
    token, token_hash = new_token()
    invitation = Invitation(
        household_id=household_id,
        token_hash=token_hash,
        expires_at=datetime.now(UTC) + INVITATION_TTL,
    )
    session.add(invitation)
    session.commit()
    return invitation, token


def accept_invitation(session: Session, token: str) -> int | None:
    """Use up a valid invitation and return its household id, or None if it is invalid or has
    expired. A single DELETE … RETURNING, so two sign-ups can never use the same link."""
    return session.scalar(
        delete(Invitation)
        .where(
            Invitation.token_hash == hash_token(token),
            Invitation.expires_at > datetime.now(UTC),
        )
        .returning(Invitation.household_id)
    )


def invitation_url(base_url: str, token: str) -> str:
    # After the #, which browsers never send to servers: the token stays out of access logs.
    return f"{base_url.rstrip('/')}/#invitation={token}"


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Create a household and a link to join it.")
    parser.add_argument("name", help='household name, e.g. "Casa García"')
    args = parser.parse_args()

    with Session(engine) as session:
        household = Household(name=args.name)
        session.add(household)
        session.flush()
        invitation, token = create_invitation(session, household.id)
    print(f"Created {args.name!r}. Sign-up link, valid for {INVITATION_TTL.days} days:")
    print(invitation_url(settings.app_url, token))
