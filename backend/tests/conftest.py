from pathlib import Path

import pytest
from alembic import command
from alembic.config import Config
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, text
from sqlalchemy.engine import make_url
from sqlalchemy.orm import Session

from app.auth import password_hash
from app.config import settings
from app.db import get_session
from app.main import app
from app.models import Category, Household, SpendingType, User

# Like Rails: a separate test database, next to the development one.
TEST_DATABASE_URL = make_url(settings.database_url).set(database="family_finances_test")
ALEMBIC_INI = Path(__file__).resolve().parents[1] / "alembic.ini"


@pytest.fixture(scope="session")
def engine():
    """Create the test database if needed and migrate it to the latest schema, once per run."""
    admin = create_engine(settings.database_url, isolation_level="AUTOCOMMIT")
    with admin.connect() as connection:
        exists = connection.scalar(
            text("SELECT 1 FROM pg_database WHERE datname = :name"),
            {"name": TEST_DATABASE_URL.database},
        )
        if not exists:
            connection.execute(text(f'CREATE DATABASE "{TEST_DATABASE_URL.database}"'))
    admin.dispose()

    config = Config(ALEMBIC_INI)
    config.set_main_option(
        "sqlalchemy.url", TEST_DATABASE_URL.render_as_string(hide_password=False)
    )
    command.upgrade(config, "head")

    engine = create_engine(TEST_DATABASE_URL)
    yield engine
    engine.dispose()


@pytest.fixture(autouse=True)
def production_settings(monkeypatch):
    """Tests check production behavior, whatever a developer's local .env relaxes."""
    monkeypatch.setattr(settings, "session_cookie_secure", True)


@pytest.fixture
def session(engine):
    """Each test runs inside a transaction that is rolled back afterwards."""
    with engine.connect() as connection:
        transaction = connection.begin()
        session = Session(bind=connection, join_transaction_mode="create_savepoint")
        yield session
        session.close()
        transaction.rollback()


PASSWORD = "correct horse battery staple"


@pytest.fixture
def anonymous_client(session):
    """HTTP client whose requests use the test session instead of the real database."""
    app.dependency_overrides[get_session] = lambda: session
    # HTTPS, as in production: the session cookie is Secure and would not be sent over HTTP.
    yield TestClient(app, base_url="https://testserver")
    app.dependency_overrides.clear()


@pytest.fixture
def household(session) -> Household:
    household = Household(name="Casa de Ana")
    session.add(household)
    session.flush()
    return household


@pytest.fixture
def user(session, household) -> User:
    """A member of `household`."""
    user = User(
        email="ana@example.com",
        password_hash=password_hash.hash(PASSWORD),
        households=[household],
    )
    session.add(user)
    session.flush()
    return user


@pytest.fixture
def client(anonymous_client, user):
    """HTTP client logged in as `user`, through the real login endpoint."""
    response = anonymous_client.post(
        "/api/auth/login", json={"email": user.email, "password": PASSWORD}
    )
    assert response.status_code == 200
    return anonymous_client


@pytest.fixture
def groceries(session) -> Category:
    category = Category(name="Supermercado")
    session.add(category)
    session.flush()
    return category


@pytest.fixture
def ant_spending(session) -> SpendingType:
    spending_type = SpendingType(name="Gasto hormiga")
    session.add(spending_type)
    session.flush()
    return spending_type
