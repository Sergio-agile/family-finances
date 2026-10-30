from datetime import date

import pytest

from app.auth import password_hash
from app.models import Category, Expense, Household, User
from tests.conftest import PASSWORD


@pytest.fixture
def expenses_url(household) -> str:
    return f"/api/households/{household.id}/expenses"


@pytest.fixture
def make_expense(session, household, groceries):
    """Factory (like FactoryBot): an expense in `household`, with defaults for every field
    the test does not care about."""

    def make(**fields) -> Expense:
        defaults = {
            "amount_cents": 100,
            "concept": "Gasto",
            "category_id": groceries.id,
            "spent_on": date(2026, 10, 1),
            "household_id": household.id,
        }
        expense = Expense(**defaults | fields)
        session.add(expense)
        session.flush()
        return expense

    return make


def test_creates_an_expense(client, expenses_url, groceries):
    response = client.post(
        expenses_url,
        json={
            "amount_cents": 4250,
            "concept": "  Compra semanal ",
            "category_id": groceries.id,
            "spent_on": "2026-10-20",
        },
    )

    assert response.status_code == 201
    body = response.json()
    assert body["amount_cents"] == 4250
    assert body["concept"] == "Compra semanal"
    assert body["spent_on"] == "2026-10-20"
    assert body["category"] == {"id": groceries.id, "name": "Supermercado"}
    assert body["spending_type"] is None


def test_creates_an_expense_with_a_spending_type(client, expenses_url, groceries, ant_spending):
    response = client.post(
        expenses_url,
        json={
            "amount_cents": 180,
            "concept": "Café",
            "category_id": groceries.id,
            "spending_type_id": ant_spending.id,
        },
    )

    assert response.status_code == 201
    assert response.json()["spending_type"] == {"id": ant_spending.id, "name": "Gasto hormiga"}


def test_rejects_unknown_spending_type(client, expenses_url, groceries):
    response = client.post(
        expenses_url,
        json={
            "amount_cents": 100,
            "concept": "Algo",
            "category_id": groceries.id,
            "spending_type_id": 999_999,
        },
    )

    assert response.status_code == 422
    assert response.json()["detail"] == "Spending type does not exist"


def test_spent_on_defaults_to_today(client, expenses_url, groceries):
    response = client.post(
        expenses_url,
        json={"amount_cents": 300, "concept": "Pan", "category_id": groceries.id},
    )

    assert response.status_code == 201
    assert response.json()["spent_on"] == date.today().isoformat()


def test_rejects_non_positive_amounts(client, expenses_url, groceries):
    response = client.post(
        expenses_url,
        json={"amount_cents": 0, "concept": "Nada", "category_id": groceries.id},
    )

    assert response.status_code == 422


def test_rejects_blank_concept(client, expenses_url, groceries):
    response = client.post(
        expenses_url,
        json={"amount_cents": 100, "concept": "   ", "category_id": groceries.id},
    )

    assert response.status_code == 422


def test_rejects_unknown_category(client, expenses_url):
    response = client.post(
        expenses_url,
        json={"amount_cents": 100, "concept": "Algo", "category_id": 999_999},
    )

    assert response.status_code == 422
    assert response.json()["detail"] == "Category does not exist"


def test_lists_expenses_of_a_month_newest_first(client, expenses_url, make_expense):
    make_expense(concept="Octubre 1", spent_on=date(2026, 10, 5))
    make_expense(concept="Octubre 2", spent_on=date(2026, 10, 20))
    make_expense(concept="Septiembre", spent_on=date(2026, 9, 30))
    make_expense(concept="Noviembre", spent_on=date(2026, 11, 1))

    response = client.get(expenses_url, params={"month": "2026-10"})

    assert response.status_code == 200
    assert [e["concept"] for e in response.json()] == ["Octubre 2", "Octubre 1"]


def test_lists_the_spending_type_of_each_expense(client, expenses_url, make_expense, ant_spending):
    make_expense(spending_type_id=ant_spending.id, spent_on=date(2026, 10, 2))
    make_expense(spent_on=date(2026, 10, 1))

    response = client.get(expenses_url, params={"month": "2026-10"})

    assert [e["spending_type"] for e in response.json()] == [
        {"id": ant_spending.id, "name": "Gasto hormiga"},
        None,
    ]


def test_month_filter_handles_december(client, expenses_url, make_expense):
    make_expense(concept="Nochevieja", spent_on=date(2026, 12, 31))
    make_expense(concept="Año nuevo", spent_on=date(2027, 1, 1))

    response = client.get(expenses_url, params={"month": "2026-12"})

    assert [e["concept"] for e in response.json()] == ["Nochevieja"]


def test_requires_a_month(client, expenses_url):
    response = client.get(expenses_url)

    assert response.status_code == 422


def test_rejects_malformed_month(client, expenses_url):
    response = client.get(expenses_url, params={"month": "2026-13"})

    assert response.status_code == 422


@pytest.fixture
def coffee(make_expense) -> Expense:
    return make_expense(amount_cents=180, concept="Café", spent_on=date(2026, 10, 2))


def test_classifies_an_expense_later(client, expenses_url, coffee, ant_spending):
    response = client.patch(
        f"{expenses_url}/{coffee.id}", json={"spending_type_id": ant_spending.id}
    )

    assert response.status_code == 200
    body = response.json()
    assert body["spending_type"] == {"id": ant_spending.id, "name": "Gasto hormiga"}
    # Fields that were not sent stay as they were.
    assert body["amount_cents"] == 180
    assert body["concept"] == "Café"
    assert body["spent_on"] == "2026-10-02"


def test_unclassifies_an_expense_with_null(client, session, expenses_url, coffee, ant_spending):
    coffee.spending_type_id = ant_spending.id
    session.flush()

    response = client.patch(f"{expenses_url}/{coffee.id}", json={"spending_type_id": None})

    assert response.status_code == 200
    assert response.json()["spending_type"] is None


def test_updates_several_fields_at_once(client, session, expenses_url, coffee):
    leisure = Category(name="Ocio")
    session.add(leisure)
    session.flush()

    response = client.patch(
        f"{expenses_url}/{coffee.id}",
        json={"amount_cents": 250, "concept": " Café con tostada ", "category_id": leisure.id},
    )

    assert response.status_code == 200
    body = response.json()
    assert body["amount_cents"] == 250
    assert body["concept"] == "Café con tostada"
    assert body["category"] == {"id": leisure.id, "name": "Ocio"}


def test_update_returns_404_for_unknown_expense(client, expenses_url):
    response = client.patch(f"{expenses_url}/999999", json={"concept": "Algo"})

    assert response.status_code == 404


@pytest.mark.parametrize(
    ("changes", "detail"),
    [
        ({"category_id": 999_999}, "Category does not exist"),
        ({"spending_type_id": 999_999}, "Spending type does not exist"),
    ],
)
def test_update_rejects_unknown_references(client, expenses_url, coffee, changes, detail):
    response = client.patch(f"{expenses_url}/{coffee.id}", json=changes)

    assert response.status_code == 422
    assert response.json()["detail"] == detail


@pytest.mark.parametrize(
    "changes",
    [
        {"amount_cents": None},
        {"concept": None},
        {"category_id": None},
        {"spent_on": None},
        {"amount_cents": 0},
        {"concept": "   "},
    ],
)
def test_update_rejects_invalid_values(client, expenses_url, coffee, changes):
    response = client.patch(f"{expenses_url}/{coffee.id}", json=changes)

    assert response.status_code == 422


# Another family's data: every route answers 404, as if it did not exist.


@pytest.fixture
def other_household(session) -> Household:
    household = Household(name="Casa de Luis")
    session.add(household)
    session.flush()
    return household


def test_does_not_list_another_households_expenses(
    client, expenses_url, make_expense, other_household
):
    make_expense(concept="Nuestro")
    make_expense(concept="De Luis", household_id=other_household.id)

    response = client.get(expenses_url, params={"month": "2026-10"})

    assert [e["concept"] for e in response.json()] == ["Nuestro"]


@pytest.mark.parametrize("method", ["get", "post"])
def test_rejects_a_household_the_user_is_not_a_member_of(
    client, other_household, groceries, method
):
    response = client.request(
        method,
        f"/api/households/{other_household.id}/expenses",
        params={"month": "2026-10"},
        json={"amount_cents": 100, "concept": "Intruso", "category_id": groceries.id},
    )

    assert response.status_code == 404
    assert response.json()["detail"] == "Household not found"


def test_cannot_edit_another_households_expense_through_own_household(
    client, expenses_url, make_expense, other_household
):
    theirs = make_expense(concept="De Luis", household_id=other_household.id)

    response = client.patch(f"{expenses_url}/{theirs.id}", json={"concept": "Hackeado"})

    assert response.status_code == 404
    assert theirs.concept == "De Luis"


def test_members_of_the_same_household_share_expenses(
    anonymous_client, session, household, expenses_url, make_expense
):
    make_expense(concept="Compartido")
    session.add(
        User(
            email="luis@example.com",
            password_hash=password_hash.hash(PASSWORD),
            households=[household],
        )
    )
    session.flush()
    anonymous_client.post(
        "/api/auth/login", json={"email": "luis@example.com", "password": PASSWORD}
    )

    response = anonymous_client.get(expenses_url, params={"month": "2026-10"})

    assert [e["concept"] for e in response.json()] == ["Compartido"]
