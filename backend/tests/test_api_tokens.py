import hashlib

import pytest
from sqlalchemy import select

from app.models import ApiToken, Expense, Household
from app.routers.api_tokens import MAX_TOKENS_PER_USER


def bearer(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


def expenses_url(household) -> str:
    return f"/api/households/{household.id}/expenses"


def new_expense(groceries) -> dict:
    return {"amount_cents": 1250, "concept": "Pan", "category_id": groceries.id}


# Managing tokens (browser session)


def test_creates_a_token_shown_only_once_and_stored_hashed(client, session):
    response = client.post(
        "/api/tokens", json={"name": "n8n bank import", "scopes": ["expenses:write"]}
    )

    assert response.status_code == 201
    created = response.json()
    assert created["token"].startswith("ff_")
    assert created["scopes"] == ["expenses:write"]
    assert created["last_used_at"] is None
    stored = session.scalar(select(ApiToken))
    assert stored.token_hash == hashlib.sha256(created["token"].encode()).digest()

    listed = client.get("/api/tokens").json()
    assert [token["name"] for token in listed] == ["n8n bank import"]
    assert "token" not in listed[0]


@pytest.mark.parametrize(
    "payload",
    [
        {"name": "n8n", "scopes": []},
        {"name": "n8n", "scopes": ["admin"]},
        {"name": "  ", "scopes": ["expenses:read"]},
    ],
)
def test_rejects_tokens_without_valid_scopes_or_name(client, payload):
    assert client.post("/api/tokens", json=payload).status_code == 422


def test_limits_the_number_of_tokens(client, make_api_token):
    for _ in range(MAX_TOKENS_PER_USER):
        make_api_token("expenses:read")

    response = client.post("/api/tokens", json={"name": "one more", "scopes": ["expenses:read"]})

    assert response.status_code == 409


def test_revoked_token_stops_working(client, anonymous_client, session, make_api_token, household):
    token = make_api_token("expenses:read")
    token_id = session.scalar(select(ApiToken.id))

    assert client.delete(f"/api/tokens/{token_id}").status_code == 204
    client.cookies.clear()
    response = anonymous_client.get(
        expenses_url(household) + "?month=2026-11", headers=bearer(token)
    )

    assert response.status_code == 401
    assert response.headers["WWW-Authenticate"] == "Bearer"


def test_cannot_revoke_someone_elses_token(client, session, luis):
    token = ApiToken(user_id=luis.id, name="Luis's", scopes=["expenses:read"], token_hash=b"x" * 32)
    session.add(token)
    session.flush()

    assert client.delete(f"/api/tokens/{token.id}").status_code == 404
    assert session.get(ApiToken, token.id) is not None


# Using a token (scripts, n8n)


def test_read_token_lists_expenses_and_reference_data(anonymous_client, make_api_token, household):
    headers = bearer(make_api_token("expenses:read"))

    for path in [
        expenses_url(household) + "?month=2026-11",
        f"/api/households/{household.id}/members",
        "/api/categories",
        "/api/spending-types",
    ]:
        assert anonymous_client.get(path, headers=headers).status_code == 200, path


def test_read_token_cannot_write(anonymous_client, make_api_token, household, groceries):
    response = anonymous_client.post(
        expenses_url(household),
        json=new_expense(groceries),
        headers=bearer(make_api_token("expenses:read")),
    )

    assert response.status_code == 403
    assert response.json() == {"detail": "API token lacks scope: expenses:write"}
    assert 'error="insufficient_scope"' in response.headers["WWW-Authenticate"]


def test_read_token_cannot_delete(anonymous_client, make_api_token, household):
    response = anonymous_client.delete(
        f"{expenses_url(household)}/1", headers=bearer(make_api_token("expenses:read"))
    )

    assert response.status_code == 403


def test_write_token_creates_expenses_as_its_user_and_can_read(
    anonymous_client, session, make_api_token, user, household, groceries
):
    headers = bearer(make_api_token("expenses:write"))

    response = anonymous_client.post(
        expenses_url(household), json=new_expense(groceries), headers=headers
    )

    assert response.status_code == 201
    assert session.get(Expense, response.json()["id"]).created_by_id == user.id
    # Write implies read: an importer needs the categories to create expenses.
    assert anonymous_client.get("/api/categories", headers=headers).status_code == 200


def test_records_when_a_token_was_last_used(anonymous_client, session, make_api_token):
    anonymous_client.get("/api/categories", headers=bearer(make_api_token("expenses:read")))

    assert session.scalar(select(ApiToken.last_used_at)) is not None


@pytest.mark.parametrize(
    ("method", "path"),
    [
        ("get", "/api/auth/me"),
        ("get", "/api/tokens"),
        ("post", "/api/tokens"),
        ("post", "/api/households/{household_id}/invitations"),
        ("get", "/api/households/{household_id}/incomes?month=2026-11"),
        ("post", "/api/households/{household_id}/incomes"),
        ("patch", "/api/households/{household_id}/incomes/1"),
        ("delete", "/api/households/{household_id}/incomes/1"),
    ],
)
def test_session_only_endpoints_refuse_tokens(
    anonymous_client, make_api_token, household, method, path
):
    response = anonymous_client.request(
        method,
        path.format(household_id=household.id),
        json={"name": "more", "scopes": ["expenses:write"]},
        headers=bearer(make_api_token("expenses:write")),
    )

    assert response.status_code == 403
    assert response.json() == {"detail": "Not available with an API token"}


def test_token_cannot_reach_another_household(anonymous_client, session, make_api_token):
    other = Household(name="Casa de otros")
    session.add(other)
    session.flush()

    response = anonymous_client.get(
        expenses_url(other) + "?month=2026-11", headers=bearer(make_api_token("expenses:read"))
    )

    assert response.status_code == 404


def test_unknown_token_is_401(anonymous_client):
    response = anonymous_client.get("/api/categories", headers=bearer("ff_not-a-real-token"))

    assert response.status_code == 401
    assert response.json() == {"detail": "Invalid or revoked API token"}
