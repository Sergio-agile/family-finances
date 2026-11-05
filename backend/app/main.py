from pathlib import Path
from urllib.parse import urlsplit

from fastapi import Depends, FastAPI, Request, Security, status
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from fastapi.responses import JSONResponse
from fastapi.routing import APIRoute
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
from sqlalchemy import text

from app.auth import READ_EXPENSES, current_user
from app.config import settings
from app.db import SessionDep
from app.routers import (
    api_tokens,
    auth,
    categories,
    expenses,
    households,
    invitations,
    spending_types,
)


def operation_id(route: APIRoute) -> str:
    """Name each OpenAPI operation after its function, so the generated client reads
    `listExpenses()` instead of `listExpensesApiExpensesGet()`."""
    return route.name


# No interactive docs nor schema in production: nobody needs a map of the API there. The
# frontend client is generated from `app.openapi()` in development, which is not affected.
docs = {"docs_url": None, "redoc_url": None, "openapi_url": None} if settings.is_production else {}
app = FastAPI(title="Family Finances API", generate_unique_id_function=operation_id, **docs)
app.include_router(auth.router)
# Everything else needs a logged-in user. Declared here, once, so no router can forget it.
# Expenses and the data needed to write them: also open to API tokens with `expenses:read`
# (write endpoints ask for `expenses:write` on top).
for router in (categories.router, expenses.router, households.router, spending_types.router):
    app.include_router(router, dependencies=[Security(current_user, scopes=[READ_EXPENSES])])
# Browser sessions only: a leaked token must not create tokens or invite anyone.
for router in (api_tokens.router, invitations.router):
    app.include_router(router, dependencies=[Depends(current_user)])


# Middleware runs outermost-last-added: security headers, then the Host check, then the Origin
# check, then the endpoint. So even a rejected request gets the security headers.

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


# The Origin check and invitation links trust the Host header: only accept our own domains.
app.add_middleware(TrustedHostMiddleware, allowed_hosts=settings.allowed_hosts)

COMMON_HEADERS = {"X-Content-Type-Options": "nosniff", "Referrer-Policy": "no-referrer"}
if settings.is_production:
    # Browsers will only use HTTPS for this domain for the next two years.
    COMMON_HEADERS["Strict-Transport-Security"] = "max-age=63072000; includeSubDomains"

API_HEADERS = COMMON_HEADERS | {
    # Financial data: no browser or proxy keeps a copy (TanStack Query caches in memory).
    "Cache-Control": "no-store",
    # The API only returns JSON: it may load nothing and be framed by no page.
    "Content-Security-Policy": "default-src 'none'; frame-ancestors 'none'",
}
FRONTEND_HEADERS = COMMON_HEADERS | {
    # index.html holds no data, only links to the current build: revalidate it on every visit.
    "Cache-Control": "no-cache",
    # The page loads scripts, styles and API calls from its own origin only; no inline code.
    "Content-Security-Policy": (
        "default-src 'self'; base-uri 'none'; form-action 'self'; "
        "frame-ancestors 'none'; object-src 'none'"
    ),
}
# Vite puts a content hash in every asset's name, so a file never changes: cache it for a year.
ASSET_HEADERS = FRONTEND_HEADERS | {"Cache-Control": "public, max-age=31536000, immutable"}


def security_headers(path: str) -> dict[str, str]:
    if path.startswith("/api/"):
        return API_HEADERS
    if path.startswith("/assets/"):
        return ASSET_HEADERS
    return FRONTEND_HEADERS


@app.middleware("http")
async def add_security_headers(request: Request, call_next):
    response = await call_next(request)
    # Swagger, only in development, needs scripts and styles from its CDN.
    if not request.url.path.startswith(("/docs", "/redoc")):
        response.headers.update(security_headers(request.url.path))
    return response


class Health(BaseModel):
    status: str
    database: str


@app.get("/api/health")
def health(session: SessionDep) -> Health:
    session.execute(text("SELECT 1"))
    return Health(status="ok", database="ok")


def serve_frontend(app: FastAPI, dist: Path) -> None:
    """Serve the built frontend at `/` (index.html, favicon, hashed assets). Mounted after every
    API route, which match first; an unknown /api/ path still gets the API's JSON 404."""
    app.mount("/", StaticFiles(directory=dist, html=True), name="frontend")


# Keep this last: nothing declared after the mount at `/` would ever be reached.
if settings.frontend_dist:
    serve_frontend(app, settings.frontend_dist)
