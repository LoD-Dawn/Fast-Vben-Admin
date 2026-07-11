from collections.abc import Generator
from typing import Annotated

import jwt
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from jwt.exceptions import InvalidTokenError
from pydantic import ValidationError
from sqlmodel import Session, select

from app.core import security
from app.core.config import settings
from app.core.db import engine
from app.models import (
    Menu,
    Role,
    RoleMenu,
    TokenPayload,
    User,
    UserRole,
    UserSession,
    get_datetime_utc,
)

reusable_oauth2 = OAuth2PasswordBearer(
    tokenUrl=f"{settings.API_V1_STR}/login/access-token"
)
optional_oauth2 = OAuth2PasswordBearer(
    tokenUrl=f"{settings.API_V1_STR}/login/access-token",
    auto_error=False,
)


def get_db() -> Generator[Session]:
    with Session(engine) as session:
        yield session


SessionDep = Annotated[Session, Depends(get_db)]
TokenDep = Annotated[str, Depends(reusable_oauth2)]
OptionalTokenDep = Annotated[str | None, Depends(optional_oauth2)]


def get_token_payload(token: TokenDep) -> TokenPayload:
    try:
        payload = jwt.decode(
            token, settings.SECRET_KEY, algorithms=[security.ALGORITHM]
        )
        return TokenPayload(**payload)
    except (InvalidTokenError, ValidationError):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Could not validate credentials",
        )


CurrentTokenPayload = Annotated[TokenPayload, Depends(get_token_payload)]


def get_current_user(
    session: SessionDep, token_data: CurrentTokenPayload
) -> User:
    return get_user_from_token_payload(session=session, token_data=token_data)


def get_user_from_token_payload(*, session: Session, token_data: TokenPayload) -> User:
    if not token_data.sub or not token_data.jti:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Could not validate credentials",
        )
    user = session.get(User, token_data.sub)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    if not user.is_active:
        raise HTTPException(status_code=403, detail="Inactive user")

    now = get_datetime_utc()
    user_session = session.exec(
        select(UserSession).where(
            UserSession.user_id == user.id,
            UserSession.token_jti == token_data.jti,
            UserSession.revoked_at.is_(None),
            UserSession.expires_at > now,
        )
    ).first()
    if not user_session:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Could not validate credentials",
        )

    user_session.last_active_at = now
    session.add(user_session)
    session.commit()
    return user


CurrentUser = Annotated[User, Depends(get_current_user)]


def get_optional_current_user(
    session: SessionDep, token: OptionalTokenDep
) -> User | None:
    if not token:
        return None
    try:
        token_data = TokenPayload(
            **jwt.decode(
                token, settings.SECRET_KEY, algorithms=[security.ALGORITHM]
            )
        )
    except (InvalidTokenError, ValidationError):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Could not validate credentials",
        )
    return get_user_from_token_payload(session=session, token_data=token_data)


OptionalCurrentUser = Annotated[User | None, Depends(get_optional_current_user)]


def normalize_pagination(
    *, page: int, page_size: int, max_page_size: int = 100
) -> tuple[int, int]:
    if page < 1:
        raise HTTPException(status_code=422, detail="page must be greater than 0")
    if page_size < 1:
        raise HTTPException(status_code=422, detail="page_size must be greater than 0")
    return page, min(page_size, max_page_size)


def get_current_active_superuser(current_user: CurrentUser) -> User:
    if not current_user.is_superuser:
        raise HTTPException(
            status_code=403, detail="The user doesn't have enough privileges"
        )
    return current_user


def user_has_permission(
    *, session: Session, current_user: User, permission_code: str
) -> bool:
    if current_user.is_superuser:
        return True

    statement = (
        select(Menu)
        .join(RoleMenu, RoleMenu.menu_id == Menu.id)
        .join(Role, Role.id == RoleMenu.role_id)
        .join(UserRole, UserRole.role_id == RoleMenu.role_id)
        .where(
            UserRole.user_id == current_user.id,
            Menu.permission_code == permission_code,
            Menu.is_active,
            Role.is_active,
        )
    )
    return session.exec(statement).first() is not None


def require_permission(permission_code: str):
    def dependency(session: SessionDep, current_user: CurrentUser) -> User:
        if user_has_permission(
            session=session,
            current_user=current_user,
            permission_code=permission_code,
        ):
            return current_user

        raise HTTPException(
            status_code=403, detail="The user doesn't have enough privileges"
        )

    return dependency
