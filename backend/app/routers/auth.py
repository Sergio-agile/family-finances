from fastapi import APIRouter, HTTPException, Response, status
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
from app.models import Household, User
from app.schemas import LogIn, SignUp, UserRead

router = APIRouter(prefix="/api/auth", tags=["auth"])


@router.post("/signup", response_model=UserRead, status_code=status.HTTP_201_CREATED)
def sign_up(payload: SignUp, session: SessionDep, response: Response) -> User:
    """Create an account, with a new household of its own, and log in with it."""
    if session.scalar(select(exists().where(User.email == payload.email))):
        raise HTTPException(status.HTTP_409_CONFLICT, "An account with this email already exists")

    user = User(
        email=payload.email,
        password_hash=password_hash.hash(payload.password),
        # Through the `memberships` table, so this also makes the user a member.
        households=[Household(name="Mi hogar")],
    )
    session.add(user)
    session.flush()
    start_session(session, response, user)
    return user


@router.post("/login", response_model=UserRead)
def log_in(payload: LogIn, session: SessionDep, response: Response) -> User:
    user = authenticate(session, payload.email, payload.password)
    if user is None:
        # Same answer for unknown email and wrong password.
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Wrong email or password")

    start_session(session, response, user)
    return user


@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT)
def log_out(session: SessionDep, response: Response, token: SessionToken) -> None:
    end_session(session, response, token)


@router.get("/me", response_model=UserRead)
def get_current_user(user: CurrentUser) -> User:
    return user
