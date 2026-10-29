from fastapi import FastAPI
from fastapi.routing import APIRoute
from pydantic import BaseModel
from sqlalchemy import text

from app.db import SessionDep
from app.routers import categories, expenses, spending_types


def operation_id(route: APIRoute) -> str:
    """Name each OpenAPI operation after its function, so the generated client reads
    `listExpenses()` instead of `listExpensesApiExpensesGet()`."""
    return route.name


app = FastAPI(title="Family Finances API", generate_unique_id_function=operation_id)
app.include_router(categories.router)
app.include_router(expenses.router)
app.include_router(spending_types.router)


class Health(BaseModel):
    status: str
    database: str


@app.get("/api/health", response_model=Health)
def health(session: SessionDep) -> Health:
    session.execute(text("SELECT 1"))
    return Health(status="ok", database="ok")
