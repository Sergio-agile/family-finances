from datetime import date

import pytest

from app.models import Category, Expense


def test_creates_an_expense(client, groceries):
    response = client.post(
        "/api/expenses",
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


def test_creates_an_expense_with_a_spending_type(client, groceries, ant_spending):
    response = client.post(
        "/api/expenses",
        json={
            "amount_cents": 180,
            "concept": "Café",
            "category_id": groceries.id,
            "spending_type_id": ant_spending.id,
        },
    )

    assert response.status_code == 201
    assert response.json()["spending_type"] == {"id": ant_spending.id, "name": "Gasto hormiga"}


def test_rejects_unknown_spending_type(client, groceries):
    response = client.post(
        "/api/expenses",
        json={
            "amount_cents": 100,
            "concept": "Algo",
            "category_id": groceries.id,
            "spending_type_id": 999_999,
        },
    )

    assert response.status_code == 422
    assert response.json()["detail"] == "Spending type does not exist"


def test_spent_on_defaults_to_today(client, groceries):
    response = client.post(
        "/api/expenses",
        json={"amount_cents": 300, "concept": "Pan", "category_id": groceries.id},
    )

    assert response.status_code == 201
    assert response.json()["spent_on"] == date.today().isoformat()


def test_rejects_non_positive_amounts(client, groceries):
    response = client.post(
        "/api/expenses",
        json={"amount_cents": 0, "concept": "Nada", "category_id": groceries.id},
    )

    assert response.status_code == 422


def test_rejects_blank_concept(client, groceries):
    response = client.post(
        "/api/expenses",
        json={"amount_cents": 100, "concept": "   ", "category_id": groceries.id},
    )

    assert response.status_code == 422


def test_rejects_unknown_category(client):
    response = client.post(
        "/api/expenses",
        json={"amount_cents": 100, "concept": "Algo", "category_id": 999_999},
    )

    assert response.status_code == 422
    assert response.json()["detail"] == "Category does not exist"


def test_lists_expenses_of_a_month_newest_first(client, session, groceries):
    for day, concept in [
        (date(2026, 10, 5), "Octubre 1"),
        (date(2026, 10, 20), "Octubre 2"),
        (date(2026, 9, 30), "Septiembre"),
        (date(2026, 11, 1), "Noviembre"),
    ]:
        session.add(
            Expense(amount_cents=100, concept=concept, category_id=groceries.id, spent_on=day)
        )
    session.flush()

    response = client.get("/api/expenses", params={"month": "2026-10"})

    assert response.status_code == 200
    assert [e["concept"] for e in response.json()] == ["Octubre 2", "Octubre 1"]


def test_lists_the_spending_type_of_each_expense(client, session, groceries, ant_spending):
    session.add_all(
        [
            Expense(
                amount_cents=180,
                concept="Café",
                category_id=groceries.id,
                spending_type_id=ant_spending.id,
                spent_on=date(2026, 10, 2),
            ),
            Expense(
                amount_cents=4250,
                concept="Compra",
                category_id=groceries.id,
                spent_on=date(2026, 10, 1),
            ),
        ]
    )
    session.flush()

    response = client.get("/api/expenses", params={"month": "2026-10"})

    assert [e["spending_type"] for e in response.json()] == [
        {"id": ant_spending.id, "name": "Gasto hormiga"},
        None,
    ]


def test_month_filter_handles_december(client, session, groceries):
    session.add_all(
        [
            Expense(
                amount_cents=100,
                concept="Nochevieja",
                category_id=groceries.id,
                spent_on=date(2026, 12, 31),
            ),
            Expense(
                amount_cents=100,
                concept="Año nuevo",
                category_id=groceries.id,
                spent_on=date(2027, 1, 1),
            ),
        ]
    )
    session.flush()

    response = client.get("/api/expenses", params={"month": "2026-12"})

    assert [e["concept"] for e in response.json()] == ["Nochevieja"]


def test_requires_a_month(client):
    response = client.get("/api/expenses")

    assert response.status_code == 422


def test_rejects_malformed_month(client):
    response = client.get("/api/expenses", params={"month": "2026-13"})

    assert response.status_code == 422


@pytest.fixture
def coffee(session, groceries) -> Expense:
    expense = Expense(
        amount_cents=180, concept="Café", category_id=groceries.id, spent_on=date(2026, 10, 2)
    )
    session.add(expense)
    session.flush()
    return expense


def test_classifies_an_expense_later(client, coffee, ant_spending):
    response = client.patch(
        f"/api/expenses/{coffee.id}", json={"spending_type_id": ant_spending.id}
    )

    assert response.status_code == 200
    body = response.json()
    assert body["spending_type"] == {"id": ant_spending.id, "name": "Gasto hormiga"}
    # Fields that were not sent stay as they were.
    assert body["amount_cents"] == 180
    assert body["concept"] == "Café"
    assert body["spent_on"] == "2026-10-02"


def test_unclassifies_an_expense_with_null(client, session, coffee, ant_spending):
    coffee.spending_type_id = ant_spending.id
    session.flush()

    response = client.patch(f"/api/expenses/{coffee.id}", json={"spending_type_id": None})

    assert response.status_code == 200
    assert response.json()["spending_type"] is None


def test_updates_several_fields_at_once(client, session, coffee):
    leisure = Category(name="Ocio")
    session.add(leisure)
    session.flush()

    response = client.patch(
        f"/api/expenses/{coffee.id}",
        json={"amount_cents": 250, "concept": " Café con tostada ", "category_id": leisure.id},
    )

    assert response.status_code == 200
    body = response.json()
    assert body["amount_cents"] == 250
    assert body["concept"] == "Café con tostada"
    assert body["category"] == {"id": leisure.id, "name": "Ocio"}


def test_update_returns_404_for_unknown_expense(client):
    response = client.patch("/api/expenses/999999", json={"concept": "Algo"})

    assert response.status_code == 404


@pytest.mark.parametrize(
    ("changes", "detail"),
    [
        ({"category_id": 999_999}, "Category does not exist"),
        ({"spending_type_id": 999_999}, "Spending type does not exist"),
    ],
)
def test_update_rejects_unknown_references(client, coffee, changes, detail):
    response = client.patch(f"/api/expenses/{coffee.id}", json=changes)

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
def test_update_rejects_invalid_values(client, coffee, changes):
    response = client.patch(f"/api/expenses/{coffee.id}", json=changes)

    assert response.status_code == 422
