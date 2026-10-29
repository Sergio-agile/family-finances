"""Create the default categories and spending types.

Safe to run repeatedly: `uv run python -m app.seed`.
"""

from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.orm import Session

from app.db import engine
from app.models import Category, SpendingType

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

# Order matters: the API lists them by id, from essential to optional spending.
DEFAULT_SPENDING_TYPES = [
    "Gastos básicos",
    "Educación",
    "Lujos",
    "Gasto hormiga",
    "Ahorro/Inversión",
]


def seed(session: Session) -> None:
    for model, names in [(Category, DEFAULT_CATEGORIES), (SpendingType, DEFAULT_SPENDING_TYPES)]:
        rows = [{"name": name} for name in names]
        session.execute(insert(model).values(rows).on_conflict_do_nothing(index_elements=["name"]))
    session.commit()


if __name__ == "__main__":
    with Session(engine) as session:
        seed(session)
    print(
        f"Seeded {len(DEFAULT_CATEGORIES)} categories "
        f"and {len(DEFAULT_SPENDING_TYPES)} spending types"
    )
