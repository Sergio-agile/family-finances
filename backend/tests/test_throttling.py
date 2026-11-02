from datetime import UTC, datetime, timedelta

import pytest

from app.models import AuthFailure
from app.throttling import MAX_FAILURES_PER_EMAIL, MAX_FAILURES_PER_IP, WINDOW
from tests.conftest import PASSWORD, sign_up

# TestClient connects from this address.
TEST_IP = "testclient"


def log_in(client, email="ana@example.com", password=PASSWORD):
    return client.post("/api/auth/login", json={"email": email, "password": password})


def add_failures(session, count, **fields):
    session.add_all(AuthFailure(**{"ip": "203.0.113.7"} | fields) for _ in range(count))
    session.flush()


@pytest.mark.usefixtures("user")
def test_blocks_an_account_after_too_many_wrong_passwords(anonymous_client):
    for _ in range(MAX_FAILURES_PER_EMAIL):
        assert log_in(anonymous_client, password="wrong password").status_code == 401

    # Even the right password: the attacker must not learn when they guessed it.
    response = log_in(anonymous_client)

    assert response.status_code == 429
    assert response.headers["Retry-After"] == "900"


@pytest.mark.usefixtures("user", "luis")
def test_other_accounts_are_not_blocked(anonymous_client, session):
    add_failures(session, MAX_FAILURES_PER_EMAIL, email="ana@example.com")

    assert log_in(anonymous_client, email="luis@example.com").status_code == 200


@pytest.mark.usefixtures("user")
def test_blocks_an_address_trying_many_accounts(anonymous_client, session):
    add_failures(session, MAX_FAILURES_PER_IP, ip=TEST_IP, email="someone@example.com")

    assert log_in(anonymous_client).status_code == 429


@pytest.mark.usefixtures("user")
def test_failures_older_than_the_window_do_not_count(anonymous_client, session):
    long_ago = datetime.now(UTC) - WINDOW - timedelta(seconds=1)
    add_failures(session, MAX_FAILURES_PER_EMAIL, email="ana@example.com", created_at=long_ago)

    assert log_in(anonymous_client).status_code == 200


@pytest.mark.usefixtures("user")
def test_a_successful_login_forgives_earlier_typos(anonymous_client, session):
    add_failures(session, MAX_FAILURES_PER_EMAIL - 1, email="ana@example.com")
    assert log_in(anonymous_client).status_code == 200

    assert log_in(anonymous_client, password="one more typo").status_code == 401
    assert log_in(anonymous_client).status_code == 200


def test_bad_invitations_count_against_the_address(anonymous_client, session):
    add_failures(session, MAX_FAILURES_PER_IP - 1, ip=TEST_IP)
    assert sign_up(anonymous_client, "made-up-token").status_code == 400

    assert sign_up(anonymous_client, "another-made-up-token").status_code == 429


def test_sign_up_does_not_reveal_emails_without_a_valid_invitation(anonymous_client, user):
    response = sign_up(anonymous_client, "made-up-token", email=user.email)

    assert response.status_code == 400
