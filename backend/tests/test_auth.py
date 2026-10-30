from datetime import UTC, datetime, timedelta

import pytest
from sqlalchemy import select

from app.auth import SESSION_COOKIE, hash_token
from app.models import User, UserSession
from tests.conftest import PASSWORD


def test_signs_up_and_is_logged_in(anonymous_client, session):
    response = anonymous_client.post(
        "/api/auth/signup", json={"email": " Luis@Example.com ", "password": PASSWORD}
    )

    assert response.status_code == 201
    assert response.json()["email"] == "luis@example.com"
    assert anonymous_client.get("/api/auth/me").json()["email"] == "luis@example.com"
    # The password is stored as an Argon2id hash, never in clear.
    user = session.scalar(select(User).where(User.email == "luis@example.com"))
    assert user.password_hash.startswith("$argon2id$")


def test_sign_up_creates_a_household_for_the_new_user(anonymous_client):
    response = anonymous_client.post(
        "/api/auth/signup", json={"email": "luis@example.com", "password": PASSWORD}
    )

    households = response.json()["households"]
    assert [h["name"] for h in households] == ["Mi hogar"]
    expenses_url = f"/api/households/{households[0]['id']}/expenses"
    assert anonymous_client.get(expenses_url, params={"month": "2026-10"}).json() == []


def test_sign_up_rejects_a_taken_email_in_any_case(anonymous_client, user):
    response = anonymous_client.post(
        "/api/auth/signup", json={"email": "ANA@example.com", "password": PASSWORD}
    )

    assert response.status_code == 409


@pytest.mark.parametrize(
    "payload",
    [
        {"email": "luis@example.com", "password": "too short"},
        {"email": "not an email", "password": PASSWORD},
    ],
)
def test_sign_up_rejects_invalid_data(anonymous_client, payload):
    response = anonymous_client.post("/api/auth/signup", json=payload)

    assert response.status_code == 422


def test_logs_in_with_a_secure_cookie(anonymous_client, user, household):
    response = anonymous_client.post(
        "/api/auth/login", json={"email": "Ana@Example.com", "password": PASSWORD}
    )

    assert response.status_code == 200
    assert response.json() == {
        "id": user.id,
        "email": "ana@example.com",
        "households": [{"id": household.id, "name": "Casa de Ana"}],
    }
    cookie = response.headers["set-cookie"]
    assert cookie.startswith(f"{SESSION_COOKIE}=")
    for flag in ["HttpOnly", "Secure", "SameSite=lax", "Max-Age=2592000"]:
        assert flag in cookie


def test_stores_only_the_hash_of_the_session_token(client, session, user):
    token = client.cookies[SESSION_COOKIE]

    stored = session.scalar(select(UserSession).where(UserSession.user_id == user.id))
    assert stored.token_hash == hash_token(token)


@pytest.mark.parametrize(
    "credentials",
    [
        {"email": "ana@example.com", "password": "wrong password"},
        {"email": "nobody@example.com", "password": PASSWORD},
    ],
)
def test_login_gives_the_same_error_for_wrong_password_and_unknown_email(
    anonymous_client, user, credentials
):
    response = anonymous_client.post("/api/auth/login", json=credentials)

    assert response.status_code == 401
    assert response.json()["detail"] == "Wrong email or password"
    assert SESSION_COOKIE not in anonymous_client.cookies


def test_me_requires_a_session(anonymous_client):
    assert anonymous_client.get("/api/auth/me").status_code == 401


def test_rejects_an_unknown_session_token(anonymous_client):
    anonymous_client.cookies.set(SESSION_COOKIE, "made-up-token")

    assert anonymous_client.get("/api/auth/me").status_code == 401


def test_rejects_an_expired_session(client, session):
    for stored in session.scalars(select(UserSession)):
        stored.expires_at = datetime.now(UTC) - timedelta(seconds=1)
    session.flush()

    assert client.get("/api/auth/me").status_code == 401


def test_logout_ends_the_session(client, session):
    token = client.cookies[SESSION_COOKIE]

    response = client.post("/api/auth/logout")

    assert response.status_code == 204
    stored = session.scalar(select(UserSession).where(UserSession.token_hash == hash_token(token)))
    assert stored is None
    # Even if the browser kept the old cookie, it no longer opens a session.
    client.cookies.set(SESSION_COOKIE, token)
    assert client.get("/api/auth/me").status_code == 401


@pytest.mark.parametrize(
    "path", ["/api/categories", "/api/spending-types", "/api/households/1/expenses"]
)
def test_data_endpoints_require_login(anonymous_client, path):
    response = anonymous_client.get(path, params={"month": "2026-10"})

    assert response.status_code == 401


def test_health_is_public(anonymous_client):
    assert anonymous_client.get("/api/health").status_code == 200


def test_rejects_unsafe_requests_from_another_origin(client):
    response = client.post("/api/auth/logout", headers={"Origin": "https://evil.example"})

    assert response.status_code == 403
    assert client.get("/api/auth/me").status_code == 200


def test_accepts_unsafe_requests_from_the_same_origin(client):
    response = client.post("/api/auth/logout", headers={"Origin": "https://testserver"})

    assert response.status_code == 204
