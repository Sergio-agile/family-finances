from app.models import Category


def test_lists_categories_alphabetically(client, session):
    session.add_all([Category(name="Transporte"), Category(name="Casa")])
    session.flush()

    response = client.get("/api/categories")

    assert response.status_code == 200
    assert [c["name"] for c in response.json()] == ["Casa", "Transporte"]
