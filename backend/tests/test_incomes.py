from datetime import date

import pytest

from app.models import Income


@pytest.fixture
def incomes_url(household) -> str:
    return f"/api/households/{household.id}/incomes"


@pytest.fixture
def make_income(session, household, user):
    """Factory: an income in `household`, with defaults for every field the test does not set."""

    def make(**fields) -> Income:
        defaults = {
            "amount_cents": 100_000,
            "concept": "Nómina",
            "received_on": date(2026, 10, 1),
            "household_id": household.id,
            "created_by_id": user.id,
        }
        income = Income(**defaults | fields)
        session.add(income)
        session.flush()
        return income

    return make


def test_creates_an_income(client, incomes_url, user):
    response = client.post(
        incomes_url,
        json={"amount_cents": 185_000, "concept": "  Nómina octubre ", "received_on": "2026-10-28"},
    )

    assert response.status_code == 201
    body = response.json()
    assert body["amount_cents"] == 185_000
    assert body["concept"] == "Nómina octubre"
    assert body["received_on"] == "2026-10-28"
    assert body["received_by"] is None
    assert body["created_by"] == {"id": user.id, "name": "Ana"}


def test_creates_an_income_received_by_a_member(client, incomes_url, luis):
    response = client.post(
        incomes_url, json={"amount_cents": 5000, "concept": "Venta", "received_by_id": luis.id}
    )

    assert response.status_code == 201
    assert response.json()["received_by"] == {"id": luis.id, "name": "Luis"}


def test_rejects_a_recipient_from_another_household(client, incomes_url, outsider):
    response = client.post(
        incomes_url, json={"amount_cents": 5000, "concept": "Venta", "received_by_id": outsider.id}
    )

    assert response.status_code == 422
    assert response.json()["detail"] == "Recipient does not belong to this household"


def test_received_on_defaults_to_today(client, incomes_url):
    response = client.post(incomes_url, json={"amount_cents": 5000, "concept": "Bizum"})

    assert response.json()["received_on"] == date.today().isoformat()


@pytest.mark.parametrize(
    "payload",
    [
        {"amount_cents": 0, "concept": "Nómina"},
        {"amount_cents": -5, "concept": "Nómina"},
        {"amount_cents": 5000, "concept": "   "},
    ],
)
def test_rejects_invalid_values(client, incomes_url, payload):
    assert client.post(incomes_url, json=payload).status_code == 422


def test_lists_incomes_of_a_month_newest_first(client, incomes_url, make_income, luis):
    make_income(concept="Nómina Ana", received_on=date(2026, 10, 1))
    make_income(concept="Nómina Luis", received_on=date(2026, 10, 28), received_by_id=luis.id)
    make_income(concept="Noviembre", received_on=date(2026, 11, 1))

    response = client.get(incomes_url, params={"month": "2026-10"})

    assert response.status_code == 200
    body = response.json()
    assert [i["concept"] for i in body] == ["Nómina Luis", "Nómina Ana"]
    assert body[0]["received_by"] == {"id": luis.id, "name": "Luis"}


def test_requires_a_valid_month(client, incomes_url):
    assert client.get(incomes_url).status_code == 422
    assert client.get(incomes_url, params={"month": "2026-13"}).status_code == 422


def test_does_not_list_another_households_incomes(
    client, incomes_url, make_income, other_household
):
    make_income(concept="Nuestra")
    make_income(concept="De Luis", household_id=other_household.id)

    response = client.get(incomes_url, params={"month": "2026-10"})

    assert [i["concept"] for i in response.json()] == ["Nuestra"]


@pytest.mark.parametrize("method", ["get", "post"])
def test_rejects_a_household_the_user_is_not_a_member_of(client, other_household, method):
    response = client.request(
        method,
        f"/api/households/{other_household.id}/incomes",
        params={"month": "2026-10"},
        json={"amount_cents": 100, "concept": "Intruso"},
    )

    assert response.status_code == 404
