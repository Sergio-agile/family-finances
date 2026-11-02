from fastapi import APIRouter, HTTPException, Request, Response, status
from sqlalchemy import exists, select

from app.auth import (
    CurrentUser,
    SessionToken,
    authenticate,
    end_session,
    password_hash,
    start_session,
)
from app.db import SessionDep
from app.invitations import accept_invitation
from app.models import Membership, User
from app.schemas import LogIn, SignUp, UserRead
from app.throttling import clear_failures, client_ip, ensure_not_throttled, record_failure

router = APIRouter(prefix="/api/auth", tags=["auth"])


@router.post("/signup", response_model=UserRead, status_code=status.HTTP_201_CREATED)
def sign_up(payload: SignUp, session: SessionDep, request: Request, response: Response) -> User:
    """Create an account in the household that sent the invitation, and log in with it."""
    ip = client_ip(request)
    ensure_not_throttled(session, ip)
    # The invitation first: without a valid one, nobody can ask whether an email has an account.
    household_id = accept_invitation(session, payload.invitation_token)
    if household_id is None:
        record_failure(session, ip)
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Invalid or expired invitation")
    # Raising here rolls back the transaction, so the invitation is not used up.
    if session.scalar(select(exists().where(User.email == payload.email))):
        raise HTTPException(status.HTTP_409_CONFLICT, "An account with this email already exists")

    user = User(
        name=payload.name,
        email=payload.email,
        password_hash=password_hash.hash(payload.password),
    )
    session.add(user)
    session.flush()
    session.add(Membership(user_id=user.id, household_id=household_id))
    start_session(session, response, user)
    return user


@router.post("/login", response_model=UserRead)
def log_in(payload: LogIn, session: SessionDep, request: Request, response: Response) -> User:
    ip = client_ip(request)
    # Checked before the password, so a throttled attacker learns nothing and costs no Argon2.
    ensure_not_throttled(session, ip, payload.email)
    user = authenticate(session, payload.email, payload.password)
    if user is None:
        record_failure(session, ip, payload.email)
        # Same answer for unknown email and wrong password.
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Wrong email or password")

    clear_failures(session, user.email)
    start_session(session, response, user)
    return user


@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT)
def log_out(session: SessionDep, response: Response, token: SessionToken) -> None:
    end_session(session, response, token)


@router.get("/me", response_model=UserRead)
def get_current_user(user: CurrentUser) -> User:
    return user
