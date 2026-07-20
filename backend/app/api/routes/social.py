import uuid
from typing import Any

from fastapi import APIRouter, Depends, HTTPException
from sqlmodel import col, func, or_, select

from app.api.deps import (
    CurrentTenant,
    CurrentUser,
    SessionDep,
    normalize_pagination,
    require_permission,
)
from app.core.clock import get_datetime_utc
from app.core.mfa import encrypt_secret
from app.core.security import verify_password
from app.platform.core.identity_models import (
    SocialClient,
    SocialClientCreate,
    SocialClientPublic,
    SocialClientsPublic,
    SocialClientUpdate,
    SocialUser,
    SocialUserBind,
    SocialUserPublic,
    SocialUsersPublic,
    User,
)
from app.platform.core.tenancy_models import TenantMembership

router = APIRouter(prefix="/social", tags=["social"])


def mask_social_client(client: SocialClient) -> SocialClientPublic:
    data = SocialClientPublic.model_validate(client)
    if data.client_secret:
        data.client_secret = "******"
    return data


def ensure_social_client_unique(
    *,
    session: SessionDep,
    tenant_id: uuid.UUID,
    social_type: str,
    user_type: str,
    exclude_id: uuid.UUID | None = None,
) -> None:
    statement = select(SocialClient).where(
        SocialClient.tenant_id == tenant_id,
        SocialClient.social_type == social_type,
        SocialClient.user_type == user_type,
    )
    if exclude_id:
        statement = statement.where(SocialClient.id != exclude_id)
    if session.exec(statement).first():
        raise HTTPException(
            status_code=409,
            detail="Social client for this platform and user type already exists",
        )


def get_social_client_or_404(
    *, session: SessionDep, tenant_id: uuid.UUID, client_id: uuid.UUID
) -> SocialClient:
    client = session.exec(
        select(SocialClient).where(
            SocialClient.id == client_id,
            SocialClient.tenant_id == tenant_id,
        )
    ).first()
    if not client:
        raise HTTPException(status_code=404, detail="Social client not found")
    return client


def get_social_user_or_404(
    *, session: SessionDep, tenant_id: uuid.UUID, social_user_id: uuid.UUID
) -> SocialUser:
    social_user = session.exec(
        select(SocialUser).where(
            SocialUser.id == social_user_id,
            SocialUser.tenant_id == tenant_id,
        )
    ).first()
    if not social_user:
        raise HTTPException(status_code=404, detail="Social user not found")
    return social_user


def to_social_user_public(
    *, session: SessionDep, social_user: SocialUser
) -> SocialUserPublic:
    data = SocialUserPublic.model_validate(social_user)
    if social_user.user_id:
        user = session.get(User, social_user.user_id)
        if user:
            data.user_email = user.email
            data.user_full_name = user.full_name
    return data


@router.get(
    "/clients",
    dependencies=[Depends(require_permission("system:social-client:list"))],
    response_model=SocialClientsPublic,
)
def read_social_clients(
    session: SessionDep,
    tenant_context: CurrentTenant,
    page: int = 1,
    page_size: int = 20,
    keyword: str | None = None,
    social_type: str | None = None,
    user_type: str | None = None,
    is_active: bool | None = None,
) -> Any:
    page, page_size = normalize_pagination(page=page, page_size=page_size)
    filters = [SocialClient.tenant_id == tenant_context.tenant_id]
    if keyword:
        pattern = f"%{keyword}%"
        filters.append(
            or_(
                col(SocialClient.name).ilike(pattern),
                col(SocialClient.client_id).ilike(pattern),
                col(SocialClient.remark).ilike(pattern),
            )
        )
    if social_type:
        filters.append(SocialClient.social_type == social_type)
    if user_type:
        filters.append(SocialClient.user_type == user_type)
    if is_active is not None:
        filters.append(SocialClient.is_active == is_active)

    count_statement = select(func.count()).select_from(SocialClient)
    if filters:
        count_statement = count_statement.where(*filters)
    count = session.exec(count_statement).one()

    statement = select(SocialClient)
    if filters:
        statement = statement.where(*filters)
    clients = session.exec(
        statement.order_by(col(SocialClient.updated_at).desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
    ).all()
    return SocialClientsPublic(
        items=[mask_social_client(client) for client in clients],
        total=count,
        page=page,
        page_size=page_size,
    )


@router.post(
    "/clients",
    dependencies=[Depends(require_permission("system:social-client:create"))],
    response_model=SocialClientPublic,
)
def create_social_client(
    *,
    session: SessionDep,
    tenant_context: CurrentTenant,
    client_in: SocialClientCreate,
) -> SocialClientPublic:
    ensure_social_client_unique(
        session=session,
        tenant_id=tenant_context.tenant_id,
        social_type=client_in.social_type,
        user_type=client_in.user_type,
    )
    client = SocialClient.model_validate(
        client_in,
        update={"tenant_id": tenant_context.tenant_id},
    )
    if client.client_secret:
        client.client_secret = encrypt_secret(client.client_secret)
    session.add(client)
    session.commit()
    session.refresh(client)
    return mask_social_client(client)


@router.get(
    "/clients/{client_id}",
    dependencies=[Depends(require_permission("system:social-client:list"))],
    response_model=SocialClientPublic,
)
def read_social_client(
    tenant_context: CurrentTenant,
    session: SessionDep,
    client_id: uuid.UUID,
) -> SocialClientPublic:
    client = get_social_client_or_404(
        session=session,
        tenant_id=tenant_context.tenant_id,
        client_id=client_id,
    )
    return mask_social_client(client)


@router.patch(
    "/clients/{client_id}",
    dependencies=[Depends(require_permission("system:social-client:update"))],
    response_model=SocialClientPublic,
)
def update_social_client(
    *,
    session: SessionDep,
    tenant_context: CurrentTenant,
    current_user: CurrentUser,
    client_id: uuid.UUID,
    client_in: SocialClientUpdate,
) -> SocialClientPublic:
    client = get_social_client_or_404(
        session=session,
        tenant_id=tenant_context.tenant_id,
        client_id=client_id,
    )

    update_data = client_in.model_dump(exclude_unset=True)
    current_password = update_data.pop("current_password", None)
    if update_data.get("client_secret") == "******":
        update_data.pop("client_secret")
    elif update_data.get("client_secret"):
        if not current_password:
            raise HTTPException(status_code=400, detail="Current password is required")
        verified, _ = verify_password(current_password, current_user.hashed_password)
        if not verified:
            raise HTTPException(status_code=400, detail="Incorrect password")
        update_data["client_secret"] = encrypt_secret(update_data["client_secret"])
    next_social_type = update_data.get("social_type", client.social_type)
    next_user_type = update_data.get("user_type", client.user_type)
    if next_social_type != client.social_type or next_user_type != client.user_type:
        ensure_social_client_unique(
            session=session,
            tenant_id=tenant_context.tenant_id,
            social_type=next_social_type,
            user_type=next_user_type,
            exclude_id=client.id,
        )
    client.sqlmodel_update(update_data)
    client.updated_at = get_datetime_utc()
    session.add(client)
    session.commit()
    session.refresh(client)
    return mask_social_client(client)


@router.delete(
    "/clients/{client_id}",
    dependencies=[Depends(require_permission("system:social-client:delete"))],
    status_code=204,
)
def delete_social_client(
    tenant_context: CurrentTenant,
    session: SessionDep,
    client_id: uuid.UUID,
) -> None:
    client = get_social_client_or_404(
        session=session,
        tenant_id=tenant_context.tenant_id,
        client_id=client_id,
    )
    if session.exec(
        select(SocialUser).where(
            SocialUser.tenant_id == tenant_context.tenant_id,
            SocialUser.social_client_id == client_id,
        )
    ).first():
        raise HTTPException(status_code=400, detail="Social client is used by users")
    session.delete(client)
    session.commit()
    return None


@router.get(
    "/users",
    dependencies=[Depends(require_permission("system:social-user:list"))],
    response_model=SocialUsersPublic,
)
def read_social_users(
    session: SessionDep,
    tenant_context: CurrentTenant,
    page: int = 1,
    page_size: int = 20,
    keyword: str | None = None,
    type: str | None = None,
    openid: str | None = None,
    user_id: uuid.UUID | None = None,
) -> Any:
    page, page_size = normalize_pagination(page=page, page_size=page_size)
    filters = [SocialUser.tenant_id == tenant_context.tenant_id]
    if keyword:
        pattern = f"%{keyword}%"
        filters.append(
            or_(
                col(SocialUser.nickname).ilike(pattern),
                col(SocialUser.openid).ilike(pattern),
                col(SocialUser.unionid).ilike(pattern),
            )
        )
    if type:
        filters.append(SocialUser.type == type)
    if openid:
        filters.append(col(SocialUser.openid).ilike(f"%{openid}%"))
    if user_id:
        filters.append(SocialUser.user_id == user_id)

    count_statement = select(func.count()).select_from(SocialUser)
    if filters:
        count_statement = count_statement.where(*filters)
    count = session.exec(count_statement).one()

    statement = select(SocialUser)
    if filters:
        statement = statement.where(*filters)
    users = session.exec(
        statement.order_by(col(SocialUser.updated_at).desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
    ).all()
    return SocialUsersPublic(
        items=[
            to_social_user_public(session=session, social_user=user) for user in users
        ],
        total=count,
        page=page,
        page_size=page_size,
    )


@router.get(
    "/users/{social_user_id}",
    dependencies=[Depends(require_permission("system:social-user:list"))],
    response_model=SocialUserPublic,
)
def read_social_user(
    tenant_context: CurrentTenant,
    session: SessionDep,
    social_user_id: uuid.UUID,
) -> SocialUserPublic:
    social_user = get_social_user_or_404(
        session=session,
        tenant_id=tenant_context.tenant_id,
        social_user_id=social_user_id,
    )
    return to_social_user_public(session=session, social_user=social_user)


@router.post(
    "/users/{social_user_id}/bind",
    dependencies=[Depends(require_permission("system:social-user:list"))],
    response_model=SocialUserPublic,
)
def bind_social_user(
    *,
    session: SessionDep,
    tenant_context: CurrentTenant,
    social_user_id: uuid.UUID,
    body: SocialUserBind,
) -> SocialUserPublic:
    social_user = get_social_user_or_404(
        session=session,
        tenant_id=tenant_context.tenant_id,
        social_user_id=social_user_id,
    )
    membership = session.exec(
        select(TenantMembership)
        .join(User, User.id == TenantMembership.user_id)
        .where(
            TenantMembership.user_id == body.user_id,
            TenantMembership.tenant_id == tenant_context.tenant_id,
            TenantMembership.is_active,
            User.is_active,
        )
    ).first()
    if not membership:
        raise HTTPException(status_code=400, detail="Target user is invalid")
    user = session.get(User, body.user_id)
    if not user:
        raise HTTPException(status_code=400, detail="Target user is invalid")
    conflict = session.exec(
        select(SocialUser).where(
            SocialUser.tenant_id == tenant_context.tenant_id,
            SocialUser.type == social_user.type,
            SocialUser.user_id == body.user_id,
            SocialUser.id != social_user.id,
        )
    ).first()
    if conflict:
        raise HTTPException(
            status_code=409,
            detail="Target user already has a social account for this platform",
        )
    social_user.user_id = user.id
    social_user.updated_at = get_datetime_utc()
    session.add(social_user)
    session.commit()
    session.refresh(social_user)
    return to_social_user_public(session=session, social_user=social_user)


@router.post(
    "/users/{social_user_id}/unbind",
    dependencies=[Depends(require_permission("system:social-user:list"))],
    response_model=SocialUserPublic,
)
def unbind_social_user(
    *,
    session: SessionDep,
    tenant_context: CurrentTenant,
    social_user_id: uuid.UUID,
) -> SocialUserPublic:
    social_user = get_social_user_or_404(
        session=session,
        tenant_id=tenant_context.tenant_id,
        social_user_id=social_user_id,
    )
    social_user.user_id = None
    social_user.updated_at = get_datetime_utc()
    session.add(social_user)
    session.commit()
    session.refresh(social_user)
    return to_social_user_public(session=session, social_user=social_user)
