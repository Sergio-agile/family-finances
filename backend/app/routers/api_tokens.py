from fastapi import APIRouter, HTTPException, status
from sqlalchemy import delete, func, select

from app.auth import CurrentUser, new_api_token
from app.db import SessionDep
from app.models import ApiToken
from app.schemas import ApiTokenCreate, ApiTokenCreated, ApiTokenRead

# Browser sessions only (see app.main): a token can never create or revoke tokens.
router = APIRouter(prefix="/api/tokens", tags=["api tokens"])

# Bounds the list below; a person needs a handful at most.
MAX_TOKENS_PER_USER = 20


@router.get("", response_model=list[ApiTokenRead])
def list_api_tokens(user: CurrentUser, session: SessionDep) -> list[ApiToken]:
    """Your API tokens, newest first. The tokens themselves are never shown again."""
    query = (
        select(ApiToken)
        .where(ApiToken.user_id == user.id)
        .order_by(ApiToken.created_at.desc(), ApiToken.id.desc())
    )
    return list(session.scalars(query))


@router.post("", response_model=ApiTokenCreated, status_code=status.HTTP_201_CREATED)
def create_api_token(payload: ApiTokenCreate, user: CurrentUser, session: SessionDep) -> dict:
    """A new token acting as you, limited to its scopes. The response is the only time the token
    is shown: only its hash is stored."""
    count = session.scalar(select(func.count()).where(ApiToken.user_id == user.id))
    if count >= MAX_TOKENS_PER_USER:
        raise HTTPException(
            status.HTTP_409_CONFLICT,
            f"You already have {MAX_TOKENS_PER_USER} tokens: revoke one you no longer use",
        )
    token, token_hash = new_api_token()
    api_token = ApiToken(
        user_id=user.id, name=payload.name, scopes=sorted(payload.scopes), token_hash=token_hash
    )
    session.add(api_token)
    session.commit()
    session.refresh(api_token)
    return ApiTokenRead.model_validate(api_token).model_dump() | {"token": token}


@router.delete("/{token_id}", status_code=status.HTTP_204_NO_CONTENT)
def revoke_api_token(token_id: int, user: CurrentUser, session: SessionDep) -> None:
    """Revoke one of your tokens: it stops working at once."""
    # Scoped to the user: someone else's token is as missing as a wrong id.
    deleted = session.execute(
        delete(ApiToken).where(ApiToken.id == token_id, ApiToken.user_id == user.id)
    )
    if deleted.rowcount == 0:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "API token not found")
    session.commit()
