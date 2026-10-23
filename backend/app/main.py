from fastapi import FastAPI
from pydantic import BaseModel
from sqlalchemy import text

from app.db import SessionDep
from app.routers import categories, expenses

app = FastAPI(title="Family Finances API")
app.include_router(categories.router)
app.include_router(expenses.router)


class Health(BaseModel):
    status: str
    database: str


@app.get("/api/health", response_model=Health)
def health(session: SessionDep) -> Health:
    session.execute(text("SELECT 1"))
    return Health(status="ok", database="ok")
