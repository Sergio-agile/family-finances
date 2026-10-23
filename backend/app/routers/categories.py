from fastapi import APIRouter
from sqlalchemy import select

from app.db import SessionDep
from app.models import Category
from app.schemas import CategoryRead

router = APIRouter(prefix="/api/categories", tags=["categories"])


@router.get("", response_model=list[CategoryRead])
def list_categories(session: SessionDep) -> list[Category]:
    return list(session.scalars(select(Category).order_by(Category.name)))
