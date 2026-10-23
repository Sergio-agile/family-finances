"""Create the default categories. Safe to run repeatedly: `uv run python -m app.seed`."""

from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.orm import Session

from app.db import engine
from app.models import Category

DEFAULT_CATEGORIES = [
    "Supermercado",
    "Casa",
    "Suministros",
    "Transporte",
    "Salud",
    "Educación",
    "Ocio",
    "Restaurantes",
    "Ropa",
    "Otros",
]


def seed(session: Session) -> None:
    rows = [{"name": name} for name in DEFAULT_CATEGORIES]
    session.execute(insert(Category).values(rows).on_conflict_do_nothing(index_elements=["name"]))
    session.commit()


if __name__ == "__main__":
    with Session(engine) as session:
        seed(session)
    print(f"Seeded {len(DEFAULT_CATEGORIES)} categories")
