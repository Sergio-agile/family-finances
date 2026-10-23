from pathlib import Path

import pytest
from alembic import command
from alembic.config import Config
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, text
from sqlalchemy.engine import make_url
from sqlalchemy.orm import Session

from app.config import settings
from app.db import get_session
from app.main import app
from app.models import Category

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


@pytest.fixture
def session(engine):
    """Each test runs inside a transaction that is rolled back afterwards."""
    with engine.connect() as connection:
        transaction = connection.begin()
        session = Session(bind=connection, join_transaction_mode="create_savepoint")
        yield session
        session.close()
        transaction.rollback()


@pytest.fixture
def client(session):
    """HTTP client whose requests use the test session instead of the real database."""
    app.dependency_overrides[get_session] = lambda: session
    yield TestClient(app)
    app.dependency_overrides.clear()


@pytest.fixture
def groceries(session) -> Category:
    category = Category(name="Supermercado")
    session.add(category)
    session.flush()
    return category
