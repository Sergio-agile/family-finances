"""Brute-force protection for login and sign-up: too many recent failures answer 429.

Failures live in Postgres rather than in process memory, so the limits hold across restarts
and across several server processes, with no extra service to run.
"""

from datetime import UTC, datetime, timedelta

from fastapi import HTTPException, Request, status
from sqlalchemy import delete, func, select
from sqlalchemy.orm import Session

from app.models import AuthFailure

WINDOW = timedelta(minutes=15)
# Per account: slows down guessing one person's password to a crawl.
MAX_FAILURES_PER_EMAIL = 5
# Per address: stops one machine from trying many accounts (a family may share one address).
MAX_FAILURES_PER_IP = 20


def client_ip(request: Request) -> str:
    # The direct peer. Behind a reverse proxy, uvicorn's --proxy-headers (with
    # --forwarded-allow-ips set to the proxy) makes this the real client from X-Forwarded-For.
    return request.client.host if request.client else "unknown"


def ensure_not_throttled(session: Session, ip: str, email: str | None = None) -> None:
    """Raise 429 before any password is checked if this address or account failed too often."""
    recent = AuthFailure.created_at > datetime.now(UTC) - WINDOW
    limits = [(AuthFailure.ip == ip, MAX_FAILURES_PER_IP)]
    if email is not None:
        limits.append((AuthFailure.email == email, MAX_FAILURES_PER_EMAIL))

    for condition, maximum in limits:
        if session.scalar(select(func.count()).where(recent, condition)) >= maximum:
            raise HTTPException(
                status.HTTP_429_TOO_MANY_REQUESTS,
                "Too many failed attempts. Try again in 15 minutes.",
                headers={"Retry-After": str(int(WINDOW.total_seconds()))},
            )


def record_failure(session: Session, ip: str, email: str | None = None) -> None:
    """Store a failed attempt. Committed right away: the request is about to fail, and an
    error would otherwise roll it back."""
    # Failures older than the window no longer count, so the table stays small.
    session.execute(delete(AuthFailure).where(AuthFailure.created_at <= datetime.now(UTC) - WINDOW))
    session.add(AuthFailure(ip=ip, email=email))
    session.commit()


def clear_failures(session: Session, email: str) -> None:
    """After a successful login, earlier typos no longer count against the account."""
    session.execute(delete(AuthFailure).where(AuthFailure.email == email))
