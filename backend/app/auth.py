"""Passwords, server-side sessions and the `CurrentUser` dependency."""

import hashlib
import secrets
from datetime import UTC, datetime, timedelta
from typing import Annotated

from fastapi import Depends, HTTPException, Response, status
from fastapi.security import APIKeyCookie
from pwdlib import PasswordHash
from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from app.config import settings
from app.db import SessionDep
from app.models import User, UserSession

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
    token = secrets.token_urlsafe(32)
    session.add(
        UserSession(
            token_hash=hash_token(token),
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


def current_user(session: SessionDep, token: SessionToken) -> User:
    """FastAPI dependency: the logged-in user, or 401."""
    if token is None:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Not logged in")
    user = session.scalar(
        select(User)
        .join(UserSession)
        .where(
            UserSession.token_hash == hash_token(token),
            UserSession.expires_at > datetime.now(UTC),
        )
    )
    if user is None:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Not logged in")
    return user


CurrentUser = Annotated[User, Depends(current_user)]
