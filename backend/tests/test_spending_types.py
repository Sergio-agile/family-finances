from app.models import SpendingType


def test_lists_spending_types_in_creation_order(client, session):
    session.add_all([SpendingType(name="Lujos"), SpendingType(name="Gasto hormiga")])
    session.flush()

    response = client.get("/api/spending-types")

    assert response.status_code == 200
    assert [t["name"] for t in response.json()] == ["Lujos", "Gasto hormiga"]
