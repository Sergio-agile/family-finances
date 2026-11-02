from datetime import UTC, datetime, timedelta

from sqlalchemy import select

from app.auth import hash_token
from app.models import Household, Invitation
from tests.conftest import sign_up


def test_a_member_creates_an_invitation_link(client, session, household):
    response = client.post(f"/api/households/{household.id}/invitations")

    assert response.status_code == 201
    url = response.json()["url"]
    assert url.startswith("https://testserver/#invitation=")
    # Only the hash of the token is stored, as with sessions.
    token = url.split("#invitation=")[1]
    stored = session.scalar(select(Invitation).where(Invitation.token_hash == hash_token(token)))
    assert stored.household_id == household.id


def test_cannot_invite_to_another_household(client, session):
    other = Household(name="Casa de Luis")
    session.add(other)
    session.flush()

    response = client.post(f"/api/households/{other.id}/invitations")

    assert response.status_code == 404


def test_inviting_requires_login(anonymous_client, household):
    response = anonymous_client.post(f"/api/households/{household.id}/invitations")

    assert response.status_code == 401


def test_sign_up_joins_the_inviting_household(anonymous_client, household, invitation_token):
    response = sign_up(anonymous_client, invitation_token)

    assert response.status_code == 201
    assert response.json()["households"] == [{"id": household.id, "name": "Casa de Ana"}]


def test_an_invitation_works_only_once(anonymous_client, invitation_token):
    assert sign_up(anonymous_client, invitation_token).status_code == 201

    response = sign_up(anonymous_client, invitation_token, email="eva@example.com")

    assert response.status_code == 400
    assert response.json()["detail"] == "Invalid or expired invitation"


def test_rejects_an_expired_invitation(anonymous_client, session, invitation_token):
    for invitation in session.scalars(select(Invitation)):
        invitation.expires_at = datetime.now(UTC) - timedelta(seconds=1)
    session.flush()

    assert sign_up(anonymous_client, invitation_token).status_code == 400


def test_rejects_a_made_up_invitation(anonymous_client):
    assert sign_up(anonymous_client, "made-up-token").status_code == 400


def test_a_taken_email_does_not_use_up_the_invitation(anonymous_client, user, invitation_token):
    assert sign_up(anonymous_client, invitation_token, email=user.email).status_code == 409

    assert sign_up(anonymous_client, invitation_token).status_code == 201
