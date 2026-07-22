"""Settlement-account master-data HTTP contracts."""

import uuid

from fastapi import APIRouter, Depends, Header, HTTPException, Response
from sqlalchemy.exc import IntegrityError
from sqlmodel import func, select

from app.core.clock import get_datetime_utc
from app.modules.erp.application.action_log import record_action
from app.modules.erp.application.idempotency import (
    IdempotencyConflictError,
    IdempotencyInProgressError,
    claim_command,
    complete_command,
    request_sha256,
)
from app.modules.erp.infrastructure.models import DocumentAction, SettlementAccount
from app.modules.erp.infrastructure.tenant_uow import ErpTenantUowDep
from app.modules.erp.observability import ErpDocumentCommandMetricRoute
from app.modules.erp.public_api.dto import (
    SettlementAccountCreate,
    SettlementAccountPublic,
    SettlementAccountSensitivePublic,
    SettlementAccountsPublic,
    SettlementAccountUpdate,
)
from app.platform.public_api import (
    SensitiveValueProtectionError,
    get_sensitive_value_protector,
)
from app.platform.web_api import (
    CurrentPrincipal,
    CurrentTenant,
    normalize_pagination,
    require_module_access,
)

router = APIRouter(
    prefix="/erp", tags=["erp-finance"], route_class=ErpDocumentCommandMetricRoute
)


def account_public(account: SettlementAccount) -> SettlementAccountPublic:
    return SettlementAccountPublic(
        id=account.id,
        name=account.name,
        account_no_masked=f"****{account.account_no_last4}",
        sort=account.sort,
        is_active=account.is_active,
        is_default=account.is_default,
        remark=account.remark,
        created_at=account.created_at,
        updated_at=account.updated_at,
    )


def get_account(*, uow: ErpTenantUowDep, resource_id: uuid.UUID) -> SettlementAccount:
    account = uow.session.get(SettlementAccount, resource_id)
    if account is None:
        raise HTTPException(status_code=404, detail="Settlement account not found")
    return account


def normalized_account_no(account_no: str) -> str:
    normalized = account_no.strip()
    if not normalized:
        raise HTTPException(status_code=422, detail="Settlement account number is required")
    return normalized


def ensure_unique_account(
    *,
    uow: ErpTenantUowDep,
    name: str | None = None,
    fingerprint: str | None = None,
    resource_id: uuid.UUID | None = None,
) -> None:
    if name is not None:
        statement = select(SettlementAccount.id).where(SettlementAccount.name == name)
        if resource_id is not None:
            statement = statement.where(SettlementAccount.id != resource_id)
        if uow.session.exec(statement).first() is not None:
            raise HTTPException(status_code=409, detail="Settlement account name already exists")
    if fingerprint is not None:
        statement = select(SettlementAccount.id).where(
            SettlementAccount.account_no_fingerprint == fingerprint
        )
        if resource_id is not None:
            statement = statement.where(SettlementAccount.id != resource_id)
        if uow.session.exec(statement).first() is not None:
            raise HTTPException(status_code=409, detail="Settlement account number already exists")


def clear_default_account(*, uow: ErpTenantUowDep, except_id: uuid.UUID | None = None) -> None:
    statement = select(SettlementAccount).where(SettlementAccount.is_default.is_(True)).with_for_update()
    for account in uow.session.exec(statement).all():
        if account.id != except_id:
            account.is_default = False
            account.updated_at = get_datetime_utc()
            uow.session.add(account)


@router.get(
    "/settlement-accounts",
    dependencies=[Depends(require_module_access("erp", "erp:account:list"))],
    response_model=SettlementAccountsPublic,
)
def read_settlement_accounts(
    uow: ErpTenantUowDep,
    page: int = 1,
    page_size: int = 20,
    keyword: str | None = None,
) -> SettlementAccountsPublic:
    page, page_size = normalize_pagination(page=page, page_size=page_size)
    filters = []
    if keyword:
        filters.append(SettlementAccount.name.ilike(f"%{keyword}%"))
    total = int(
        uow.session.exec(
            select(func.count()).select_from(SettlementAccount).where(*filters)
        ).one()
    )
    accounts = uow.session.exec(
        select(SettlementAccount)
        .where(*filters)
        .order_by(SettlementAccount.is_default.desc(), SettlementAccount.sort, SettlementAccount.name)
        .offset((page - 1) * page_size)
        .limit(page_size)
    ).all()
    return SettlementAccountsPublic(
        items=[account_public(account) for account in accounts],
        total=total,
        page=page,
        page_size=page_size,
    )


@router.post(
    "/settlement-accounts",
    dependencies=[Depends(require_module_access("erp", "erp:account:create"))],
    response_model=SettlementAccountPublic,
)
def create_settlement_account(
    command: SettlementAccountCreate,
    uow: ErpTenantUowDep,
    tenant: CurrentTenant,
    principal: CurrentPrincipal,
    idempotency_key: str = Header(alias="Idempotency-Key"),
) -> SettlementAccountPublic:
    command_name = "erp.settlement-account.create"
    try:
        claim = claim_command(
            uow=uow,
            command_name=command_name,
            idempotency_key=idempotency_key,
            request_hash=request_sha256(
                command_name=command_name,
                actor_id=principal.id,
                payload=command.model_dump(mode="json"),
            ),
        )
    except (IdempotencyConflictError, IdempotencyInProgressError) as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    if claim.replay:
        if (
            claim.receipt.resource_type != "settlement_account"
            or claim.receipt.resource_id is None
        ):
            raise HTTPException(status_code=409, detail="Idempotency receipt is unavailable")
        account = get_account(uow=uow, resource_id=claim.receipt.resource_id)
        return account_public(account)
    protector = get_sensitive_value_protector()
    account_no = normalized_account_no(command.account_no)
    fingerprint = protector.fingerprint(account_no)
    ensure_unique_account(uow=uow, name=command.name, fingerprint=fingerprint)
    if command.is_default:
        clear_default_account(uow=uow)
    account = SettlementAccount(
        tenant_id=tenant.tenant_id,
        name=command.name,
        account_no_encrypted=protector.encrypt(account_no),
        account_no_fingerprint=fingerprint,
        account_no_last4=account_no[-4:],
        sort=command.sort,
        is_active=command.is_active,
        is_default=command.is_default,
        remark=command.remark,
    )
    uow.session.add(account)
    record_action(
        uow=uow,
        resource_type="settlement_account",
        resource_id=account.id,
        action=DocumentAction.CREATED,
        actor_id=principal.id,
        metadata={"fields": ["account_no", "is_active", "is_default", "name", "sort"]},
    )
    complete_command(
        receipt=claim.receipt,
        resource_type="settlement_account",
        resource_id=account.id,
        resource_version=1,
    )
    try:
        uow.session.commit()
    except IntegrityError as exc:
        uow.session.rollback()
        raise HTTPException(status_code=409, detail="Settlement account already exists") from exc
    uow.session.refresh(account)
    return account_public(account)


@router.get(
    "/settlement-accounts/{resource_id}",
    dependencies=[Depends(require_module_access("erp", "erp:account:list"))],
    response_model=SettlementAccountPublic,
)
def read_settlement_account(
    resource_id: uuid.UUID, uow: ErpTenantUowDep
) -> SettlementAccountPublic:
    return account_public(get_account(uow=uow, resource_id=resource_id))


@router.get(
    "/settlement-accounts/{resource_id}/sensitive",
    dependencies=[Depends(require_module_access("erp", "erp:finance-sensitive:read"))],
    response_model=SettlementAccountSensitivePublic,
)
def read_settlement_account_sensitive(
    resource_id: uuid.UUID, uow: ErpTenantUowDep, principal: CurrentPrincipal
) -> SettlementAccountSensitivePublic:
    account = get_account(uow=uow, resource_id=resource_id)
    try:
        account_no = get_sensitive_value_protector().decrypt(account.account_no_encrypted)
    except SensitiveValueProtectionError as exc:
        raise HTTPException(status_code=409, detail="Settlement account cannot be decrypted") from exc
    record_action(
        uow=uow,
        resource_type="settlement_account",
        resource_id=account.id,
        action=DocumentAction.SENSITIVE_VIEWED,
        actor_id=principal.id,
        metadata={"field": "account_no"},
    )
    uow.session.commit()
    return SettlementAccountSensitivePublic(id=account.id, account_no=account_no)


@router.patch(
    "/settlement-accounts/{resource_id}",
    dependencies=[Depends(require_module_access("erp", "erp:account:update"))],
    response_model=SettlementAccountPublic,
)
def update_settlement_account(
    resource_id: uuid.UUID,
    command: SettlementAccountUpdate,
    uow: ErpTenantUowDep,
    principal: CurrentPrincipal,
) -> SettlementAccountPublic:
    account = get_account(uow=uow, resource_id=resource_id)
    values = command.model_dump(exclude_unset=True)
    protector = get_sensitive_value_protector()
    if "name" in values:
        ensure_unique_account(uow=uow, name=values["name"], resource_id=account.id)
    if "account_no" in values:
        account_no = normalized_account_no(values.pop("account_no"))
        fingerprint = protector.fingerprint(account_no)
        ensure_unique_account(
            uow=uow, fingerprint=fingerprint, resource_id=account.id
        )
        values.update(
            account_no_encrypted=protector.encrypt(account_no),
            account_no_fingerprint=fingerprint,
            account_no_last4=account_no[-4:],
        )
    if values.get("is_default") is True:
        clear_default_account(uow=uow, except_id=account.id)
    for field, value in values.items():
        setattr(account, field, value)
    account.updated_at = get_datetime_utc()
    uow.session.add(account)
    record_action(
        uow=uow,
        resource_type="settlement_account",
        resource_id=account.id,
        action=DocumentAction.UPDATED,
        actor_id=principal.id,
        metadata={"fields": sorted(values)},
    )
    try:
        uow.session.commit()
    except IntegrityError as exc:
        uow.session.rollback()
        raise HTTPException(status_code=409, detail="Settlement account already exists") from exc
    uow.session.refresh(account)
    return account_public(account)


@router.delete(
    "/settlement-accounts/{resource_id}",
    dependencies=[Depends(require_module_access("erp", "erp:account:delete"))],
    status_code=204,
)
def delete_settlement_account(
    resource_id: uuid.UUID, uow: ErpTenantUowDep, principal: CurrentPrincipal
) -> Response:
    account = get_account(uow=uow, resource_id=resource_id)
    record_action(
        uow=uow,
        resource_type="settlement_account",
        resource_id=account.id,
        action=DocumentAction.DELETED,
        actor_id=principal.id,
        metadata={"name": account.name},
    )
    uow.session.delete(account)
    uow.session.commit()
    return Response(status_code=204)
