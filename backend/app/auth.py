"""Passwords, server-side sessions, API tokens, and the `CurrentUser` and `CurrentHousehold`
dependencies."""

import hashlib
import secrets
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from typing import Annotated, get_args

from fastapi import Depends, HTTPException, Response, Security, status
from fastapi.security import (
    APIKeyCookie,
    HTTPAuthorizationCredentials,
    HTTPBearer,
    SecurityScopes,
)
from pwdlib import PasswordHash
from sqlalchemy import delete, select
from sqlalchemy.orm import Session, joinedload

from app.config import settings
from app.db import SessionDep
from app.models import ApiToken, Household, Membership, User, UserSession
from app.schemas import Scope

SESSION_COOKIE = "session"
SESSION_TTL = timedelta(days=30)

# Argon2id with pwdlib's recommended parameters.
password_hash = PasswordHash.recommended()
# Verified when the email does not exist, so a login takes as long for unknown emails as for
# wrong passwords and response times do not reveal which emails have an account.
DUMMY_HASH = password_hash.hash("dummy password")

# Declaring the cookie this way also documents it as the security scheme in Swagger.
session_cookie = APIKeyCookie(name=SESSION_COOKIE, auto_error=False)


def hash_token(token: str) -> bytes:
    # A 256-bit random token does not need a slow hash like a password: SHA-256 is enough.
    return hashlib.sha256(token.encode()).digest()


def new_token() -> tuple[str, bytes]:
    """A 256-bit random token for a cookie or a link, and the hash to store instead of it."""
    token = secrets.token_urlsafe(32)
    return token, hash_token(token)


def authenticate(session: Session, email: str, password: str) -> User | None:
    user = session.scalar(select(User).where(User.email == email))
    if user is None:
        password_hash.verify(password, DUMMY_HASH)
        return None
    return user if password_hash.verify(password, user.password_hash) else None


def start_session(session: Session, response: Response, user: User) -> None:
    """Log the user in: store a new session and send its token in an HttpOnly cookie."""
    # Expired sessions are cleaned up here, so the table does not grow forever.
    session.execute(
        delete(UserSession).where(
            UserSession.user_id == user.id, UserSession.expires_at <= datetime.now(UTC)
        )
    )
    token, token_hash = new_token()
    session.add(
        UserSession(
            token_hash=token_hash,
            user_id=user.id,
            expires_at=datetime.now(UTC) + SESSION_TTL,
        )
    )
    session.commit()
    response.set_cookie(
        SESSION_COOKIE,
        token,
        max_age=int(SESSION_TTL.total_seconds()),
        httponly=True,  # not readable from JavaScript, so an XSS bug cannot steal it
        secure=settings.session_cookie_secure,
        samesite="lax",  # not sent on cross-site POST/PATCH/DELETE: first line against CSRF
    )


def end_session(session: Session, response: Response, token: str | None) -> None:
    if token:
        session.execute(delete(UserSession).where(UserSession.token_hash == hash_token(token)))
        session.commit()
    response.delete_cookie(
        SESSION_COOKIE, httponly=True, secure=settings.session_cookie_secure, samesite="lax"
    )


SessionToken = Annotated[str | None, Depends(session_cookie)]

# API tokens: `Authorization: Bearer ff_…`. Also documents the scheme in Swagger.
API_TOKEN_PREFIX = "ff_"  # noqa: S105 (a public prefix, not a secret)
bearer = HTTPBearer(
    auto_error=False,
    description="Personal access token (`ff_…`), created in the app. Scopes: "
    + ", ".join(f"`{scope}`" for scope in get_args(Scope)),
)
BearerToken = Annotated[HTTPAuthorizationCredentials | None, Depends(bearer)]

READ_EXPENSES: Scope = "expenses:read"
WRITE_EXPENSES: Scope = "expenses:write"
# Like GitHub's "read and write": a token that writes expenses must read categories to do it.
IMPLIED_SCOPES: dict[str, set[str]] = {WRITE_EXPENSES: {READ_EXPENSES}}
# last_used_at is a hint, not an audit log: one write a minute is enough during a bulk import.
LAST_USED_PRECISION = timedelta(minutes=1)


def new_api_token() -> tuple[str, bytes]:
    """Like `new_token`, with a prefix that makes a leaked token recognizable (secret scanners)."""
    token = API_TOKEN_PREFIX + secrets.token_urlsafe(32)
    return token, hash_token(token)


@dataclass(frozen=True)
class Credentials:
    user: User
    # None for a browser session, which may do anything its user can.
    scopes: frozenset[str] | None


def request_credentials(
    session: SessionDep, cookie_token: SessionToken, bearer_token: BearerToken
) -> Credentials:
    """Who is calling: an API token if one is sent, else the session cookie; otherwise 401.
    One lookup per request, whatever scopes each endpoint asks for (FastAPI caches it)."""
    if bearer_token is not None:
        return api_token_credentials(session, bearer_token.credentials)
    if cookie_token is None:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Not logged in")
    user = session.scalar(
        select(User)
        .join(UserSession)
        .where(
            UserSession.token_hash == hash_token(cookie_token),
            UserSession.expires_at > datetime.now(UTC),
        )
    )
    if user is None:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Not logged in")
    return Credentials(user, scopes=None)


def api_token_credentials(session: Session, token: str) -> Credentials:
    api_token = session.scalar(
        select(ApiToken)
        .options(joinedload(ApiToken.user))
        .where(ApiToken.token_hash == hash_token(token))
    )
    if api_token is None:
        raise HTTPException(
            status.HTTP_401_UNAUTHORIZED,
            "Invalid or revoked API token",
            headers={"WWW-Authenticate": "Bearer"},
        )
    now = datetime.now(UTC)
    if api_token.last_used_at is None or api_token.last_used_at < now - LAST_USED_PRECISION:
        api_token.last_used_at = now
        session.commit()
    scopes = set(api_token.scopes)
    for scope in api_token.scopes:
        scopes |= IMPLIED_SCOPES.get(scope, set())
    return Credentials(api_token.user, frozenset(scopes))


def current_user(
    security_scopes: SecurityScopes,
    credentials: Annotated[Credentials, Depends(request_credentials)],
) -> User:
    """FastAPI dependency: the user making the request, or 401.

    Browser sessions pass everywhere. API tokens are denied by default: they only pass where the
    endpoint declares scopes, `Security(current_user, scopes=[…])`, and the token has them all.
    So a leaked token can never create tokens or invitations, nor reach a new endpoint by
    accident."""
    if credentials.scopes is not None:
        if not security_scopes.scopes:
            raise HTTPException(status.HTTP_403_FORBIDDEN, "Not available with an API token")
        missing = set(security_scopes.scopes) - credentials.scopes
        if missing:
            needed = security_scopes.scope_str
            raise HTTPException(
                status.HTTP_403_FORBIDDEN,
                f"API token lacks scope: {', '.join(sorted(missing))}",
                # RFC 6750: tells the client which scopes this endpoint needs.
                headers={
                    "WWW-Authenticate": f'Bearer error="insufficient_scope", scope="{needed}"'
                },
            )
    return credentials.user


CurrentUser = Annotated[User, Depends(current_user)]
# For endpoints that API tokens may use; scopes declared here reach `current_user` through
# `current_household` too.
ExpensesWriter = Annotated[User, Security(current_user, scopes=[WRITE_EXPENSES])]


def current_household(household_id: int, user: CurrentUser, session: SessionDep) -> Household:
    """FastAPI dependency: the household in the URL, if the user is a member. Otherwise 404, not
    403, so nobody can find out which household ids exist."""
    household = session.scalar(
        select(Household)
        .join(Membership)
        .where(Household.id == household_id, Membership.user_id == user.id)
    )
    if household is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Household not found")
    return household


CurrentHousehold = Annotated[Household, Depends(current_household)]
ReadableHousehold = Annotated[Household, Security(current_household, scopes=[READ_EXPENSES])]
WritableHousehold = Annotated[Household, Security(current_household, scopes=[WRITE_EXPENSES])]
