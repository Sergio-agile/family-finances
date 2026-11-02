from app.models import Household


def test_lists_members_by_name_without_emails(client, household, user, luis):
    response = client.get(f"/api/households/{household.id}/members")

    assert response.status_code == 200
    assert response.json() == [{"id": user.id, "name": "Ana"}, {"id": luis.id, "name": "Luis"}]


def test_cannot_list_members_of_another_household(client, session):
    other = Household(name="Casa de Eva")
    session.add(other)
    session.flush()

    response = client.get(f"/api/households/{other.id}/members")

    assert response.status_code == 404
