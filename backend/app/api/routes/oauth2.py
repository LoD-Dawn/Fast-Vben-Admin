import uuid
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Response
from sqlmodel import col, func, or_, select

from app.api.deps import SessionDep, normalize_pagination, require_permission
from app.models import (
    OAuth2AccessToken,
    OAuth2AccessTokenPublic,
    OAuth2AccessTokensPublic,
    OAuth2Client,
    OAuth2ClientCreate,
    OAuth2ClientPublic,
    OAuth2ClientsPublic,
    OAuth2ClientUpdate,
    get_datetime_utc,
)

router = APIRouter(prefix="/oauth2", tags=["oauth2"])


def mask_oauth2_client(client: OAuth2Client) -> OAuth2ClientPublic:
    data = OAuth2ClientPublic.model_validate(client)
    if data.client_secret:
        data.client_secret = "******"
    return data


def ensure_oauth2_client_id_unique(
    *, session: SessionDep, client_id: str, exclude_id: uuid.UUID | None = None
) -> None:
    statement = select(OAuth2Client).where(OAuth2Client.client_id == client_id)
    if exclude_id:
        statement = statement.where(OAuth2Client.id != exclude_id)
    if session.exec(statement).first():
        raise HTTPException(status_code=409, detail="OAuth2 client id already exists")


@router.get(
    "/clients",
    dependencies=[Depends(require_permission("system:oauth2-client:list"))],
    response_model=OAuth2ClientsPublic,
)
def read_oauth2_clients(
    session: SessionDep,
    page: int = 1,
    page_size: int = 20,
    keyword: str | None = None,
    is_active: bool | None = None,
) -> Any:
    page, page_size = normalize_pagination(page=page, page_size=page_size)
    filters = []
    if keyword:
        pattern = f"%{keyword}%"
        filters.append(
            or_(
                col(OAuth2Client.client_id).ilike(pattern),
                col(OAuth2Client.name).ilike(pattern),
                col(OAuth2Client.description).ilike(pattern),
            )
        )
    if is_active is not None:
        filters.append(OAuth2Client.is_active == is_active)

    count_statement = select(func.count()).select_from(OAuth2Client)
    if filters:
        count_statement = count_statement.where(*filters)
    count = session.exec(count_statement).one()

    statement = select(OAuth2Client)
    if filters:
        statement = statement.where(*filters)
    clients = session.exec(
        statement.order_by(col(OAuth2Client.updated_at).desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
    ).all()
    return OAuth2ClientsPublic(
        items=[mask_oauth2_client(client) for client in clients],
        total=count,
        page=page,
        page_size=page_size,
    )


@router.post(
    "/clients",
    dependencies=[Depends(require_permission("system:oauth2-client:create"))],
    response_model=OAuth2ClientPublic,
)
def create_oauth2_client(
    *, session: SessionDep, client_in: OAuth2ClientCreate
) -> OAuth2ClientPublic:
    ensure_oauth2_client_id_unique(session=session, client_id=client_in.client_id)
    client = OAuth2Client.model_validate(client_in)
    session.add(client)
    session.commit()
    session.refresh(client)
    return mask_oauth2_client(client)


@router.get(
    "/clients/{client_id}",
    dependencies=[Depends(require_permission("system:oauth2-client:list"))],
    response_model=OAuth2ClientPublic,
)
def read_oauth2_client(session: SessionDep, client_id: uuid.UUID) -> OAuth2ClientPublic:
    client = session.get(OAuth2Client, client_id)
    if not client:
        raise HTTPException(status_code=404, detail="OAuth2 client not found")
    return mask_oauth2_client(client)


@router.patch(
    "/clients/{client_id}",
    dependencies=[Depends(require_permission("system:oauth2-client:update"))],
    response_model=OAuth2ClientPublic,
)
def update_oauth2_client(
    *,
    session: SessionDep,
    client_id: uuid.UUID,
    client_in: OAuth2ClientUpdate,
) -> OAuth2ClientPublic:
    client = session.get(OAuth2Client, client_id)
    if not client:
        raise HTTPException(status_code=404, detail="OAuth2 client not found")

    update_data = client_in.model_dump(exclude_unset=True)
    if "client_id" in update_data and update_data["client_id"] != client.client_id:
        ensure_oauth2_client_id_unique(
            session=session,
            client_id=update_data["client_id"],
            exclude_id=client.id,
        )
    if update_data.get("client_secret") == "******":
        update_data.pop("client_secret")

    client.sqlmodel_update(update_data)
    client.updated_at = get_datetime_utc()
    session.add(client)
    session.commit()
    session.refresh(client)
    return mask_oauth2_client(client)


@router.delete(
    "/clients/{client_id}",
    dependencies=[Depends(require_permission("system:oauth2-client:delete"))],
    status_code=204,
)
def delete_oauth2_client(session: SessionDep, client_id: uuid.UUID) -> None:
    client = session.get(OAuth2Client, client_id)
    if not client:
        raise HTTPException(status_code=404, detail="OAuth2 client not found")
    active_token = session.exec(
        select(OAuth2AccessToken).where(
            OAuth2AccessToken.client_id == client.client_id,
            OAuth2AccessToken.revoked_at.is_(None),
            OAuth2AccessToken.expires_at > get_datetime_utc(),
        )
    ).first()
    if active_token:
        raise HTTPException(
            status_code=400,
            detail="OAuth2 client has active access tokens",
        )
    session.delete(client)
    session.commit()
    return None


@router.get(
    "/tokens",
    dependencies=[Depends(require_permission("system:oauth2-token:list"))],
    response_model=OAuth2AccessTokensPublic,
)
def read_oauth2_tokens(
    session: SessionDep,
    page: int = 1,
    page_size: int = 20,
    keyword: str | None = None,
    client_id: str | None = None,
    user_id: uuid.UUID | None = None,
    revoked: bool | None = None,
) -> Any:
    page, page_size = normalize_pagination(page=page, page_size=page_size)
    filters = []
    if keyword:
        pattern = f"%{keyword}%"
        filters.append(
            or_(
                col(OAuth2AccessToken.access_token).ilike(pattern),
                col(OAuth2AccessToken.refresh_token).ilike(pattern),
                col(OAuth2AccessToken.user_email).ilike(pattern),
                col(OAuth2AccessToken.user_full_name).ilike(pattern),
            )
        )
    if client_id:
        filters.append(col(OAuth2AccessToken.client_id).ilike(f"%{client_id}%"))
    if user_id:
        filters.append(OAuth2AccessToken.user_id == user_id)
    if revoked is not None:
        filters.append(
            OAuth2AccessToken.revoked_at.is_not(None)
            if revoked
            else OAuth2AccessToken.revoked_at.is_(None)
        )

    count_statement = select(func.count()).select_from(OAuth2AccessToken)
    if filters:
        count_statement = count_statement.where(*filters)
    count = session.exec(count_statement).one()

    statement = select(OAuth2AccessToken)
    if filters:
        statement = statement.where(*filters)
    tokens = session.exec(
        statement.order_by(col(OAuth2AccessToken.created_at).desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
    ).all()
    return OAuth2AccessTokensPublic(
        items=[OAuth2AccessTokenPublic.model_validate(token) for token in tokens],
        total=count,
        page=page,
        page_size=page_size,
    )


@router.delete(
    "/tokens/{token_id}",
    dependencies=[Depends(require_permission("system:oauth2-token:delete"))],
    status_code=204,
)
def revoke_oauth2_token(session: SessionDep, token_id: uuid.UUID) -> Response:
    token = session.get(OAuth2AccessToken, token_id)
    if not token:
        raise HTTPException(status_code=404, detail="OAuth2 access token not found")
    if token.revoked_at is None:
        token.revoked_at = get_datetime_utc()
        session.add(token)
        session.commit()
    return Response(status_code=204)
