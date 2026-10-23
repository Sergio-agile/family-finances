from collections.abc import Iterator
from typing import Annotated

from fastapi import Depends
from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from app.config import settings

engine = create_engine(settings.database_url, pool_pre_ping=True)


def get_session() -> Iterator[Session]:
    """FastAPI dependency: one session per request, always closed afterwards."""
    with Session(engine) as session:
        yield session


SessionDep = Annotated[Session, Depends(get_session)]
