import uuid
from typing import Any

from fastapi import APIRouter, Depends, HTTPException
from sqlmodel import col, func, or_, select

from app.api.deps import (
    CurrentTokenPayload,
    CurrentUser,
    SessionDep,
    normalize_pagination,
    require_permission,
)
from app.models import (
    Message,
    User,
    UserSession,
    UserSessionPublic,
    UserSessionsPublic,
    get_datetime_utc,
)

router = APIRouter(prefix="/sessions", tags=["sessions"])


@router.get(
    "",
    dependencies=[Depends(require_permission("system:session:list"))],
    response_model=UserSessionsPublic,
)
def read_user_sessions(
    session: SessionDep,
    page: int = 1,
    page_size: int = 20,
    keyword: str | None = None,
) -> Any:
    page, page_size = normalize_pagination(page=page, page_size=page_size)
    now = get_datetime_utc()
    filters = [
        UserSession.revoked_at.is_(None),
        UserSession.expires_at > now,
    ]
    if keyword:
        pattern = f"%{keyword}%"
        filters.append(
            or_(
                col(User.email).ilike(pattern),
                col(User.full_name).ilike(pattern),
                col(UserSession.ip).ilike(pattern),
            )
        )

    count = session.exec(
        select(func.count()).select_from(UserSession).join(User).where(*filters)
    ).one()
    rows = session.exec(
        select(UserSession, User)
        .join(User)
        .where(*filters)
        .order_by(col(UserSession.last_active_at).desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
    ).all()
    return UserSessionsPublic(
        items=[
            UserSessionPublic(
                id=user_session.id,
                user_id=user_session.user_id,
                email=user.email,
                full_name=user.full_name,
                ip=user_session.ip,
                user_agent=user_session.user_agent,
                created_at=user_session.created_at,
                last_active_at=user_session.last_active_at,
                expires_at=user_session.expires_at,
            )
            for user_session, user in rows
        ],
        total=count,
        page=page,
        page_size=page_size,
    )


@router.post(
    "/{session_id}/revoke",
    dependencies=[Depends(require_permission("system:session:revoke"))],
    response_model=Message,
)
def revoke_user_session(
    *,
    session: SessionDep,
    session_id: uuid.UUID,
    current_user: CurrentUser,
    token_data: CurrentTokenPayload,
) -> Message:
    user_session = session.get(UserSession, session_id)
    if not user_session or user_session.revoked_at or user_session.expires_at <= get_datetime_utc():
        raise HTTPException(status_code=404, detail="Session not found")
    if (
        user_session.user_id == current_user.id
        and user_session.token_jti == token_data.jti
    ):
        raise HTTPException(status_code=400, detail="Cannot revoke current session")

    user_session.revoked_at = get_datetime_utc()
    session.add(user_session)
    session.commit()
    return Message(message="Session revoked")
