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
from app.invitations import accept_invitation
from app.models import Membership, User
from app.schemas import LogIn, SignUp, UserRead

router = APIRouter(prefix="/api/auth", tags=["auth"])


@router.post("/signup", response_model=UserRead, status_code=status.HTTP_201_CREATED)
def sign_up(payload: SignUp, session: SessionDep, response: Response) -> User:
    """Create an account in the household that sent the invitation, and log in with it."""
    if session.scalar(select(exists().where(User.email == payload.email))):
        raise HTTPException(status.HTTP_409_CONFLICT, "An account with this email already exists")
    household_id = accept_invitation(session, payload.invitation_token)
    if household_id is None:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Invalid or expired invitation")

    user = User(email=payload.email, password_hash=password_hash.hash(payload.password))
    session.add(user)
    session.flush()
    session.add(Membership(user_id=user.id, household_id=household_id))
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
