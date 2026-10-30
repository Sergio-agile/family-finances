from urllib.parse import urlsplit

from fastapi import Depends, FastAPI, Request, status
from fastapi.responses import JSONResponse
from fastapi.routing import APIRoute
from pydantic import BaseModel
from sqlalchemy import text

from app.auth import current_user
from app.db import SessionDep
from app.routers import auth, categories, expenses, spending_types


def operation_id(route: APIRoute) -> str:
    """Name each OpenAPI operation after its function, so the generated client reads
    `listExpenses()` instead of `listExpensesApiExpensesGet()`."""
    return route.name


app = FastAPI(title="Family Finances API", generate_unique_id_function=operation_id)
app.include_router(auth.router)
# Everything else needs a logged-in user. Declared here, once, so no router can forget it.
for router in (categories.router, expenses.router, spending_types.router):
    app.include_router(router, dependencies=[Depends(current_user)])


SAFE_METHODS = {"GET", "HEAD", "OPTIONS"}


@app.middleware("http")
async def check_origin(request: Request, call_next):
    """CSRF defense on top of SameSite: browsers send `Origin` on every unsafe request, and a
    page on another site cannot fake it. Requests without it come from non-browser clients
    (curl, n8n), which have no victim's cookies to ride on, so they pass."""
    origin = request.headers.get("origin")
    if (
        request.method not in SAFE_METHODS
        and origin is not None
        and urlsplit(origin).netloc != request.headers.get("host")
    ):
        return JSONResponse({"detail": "Cross-origin request"}, status.HTTP_403_FORBIDDEN)
    return await call_next(request)


class Health(BaseModel):
    status: str
    database: str


@app.get("/api/health")
def health(session: SessionDep) -> Health:
    session.execute(text("SELECT 1"))
    return Health(status="ok", database="ok")
