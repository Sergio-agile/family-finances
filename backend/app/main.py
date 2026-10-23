from typing import Annotated

from fastapi import Depends, FastAPI
from pydantic import BaseModel
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.db import get_session

app = FastAPI(title="Family Finances API")


class Health(BaseModel):
    status: str
    database: str


@app.get("/api/health", response_model=Health)
def health(session: Annotated[Session, Depends(get_session)]) -> Health:
    session.execute(text("SELECT 1"))
    return Health(status="ok", database="ok")
