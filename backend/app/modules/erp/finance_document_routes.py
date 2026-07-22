"""Payment and receipt settlement-document HTTP contracts."""

import uuid
from datetime import datetime
from typing import Any

from fastapi import APIRouter, Depends, Header, HTTPException, Response
from sqlmodel import col, func, select

from app.core.clock import get_datetime_utc
from app.modules.erp.application.action_log import record_action
from app.modules.erp.application.business_time import resolve_business_at
from app.modules.erp.application.document_listing import financial_document_filters
from app.modules.erp.application.document_numbers import allocate_document_no
from app.modules.erp.application.events import enqueue_document_lifecycle_event
from app.modules.erp.application.idempotency import (
    CommandReceiptClaim,
    IdempotencyConflictError,
    IdempotencyInProgressError,
    claim_command,
    complete_command,
)
from app.modules.erp.application.idempotency import (
    request_sha256 as command_request_sha256,
)
from app.modules.erp.application.settlement import (
    PlannedSettlementLine,
    SettlementConflictError,
    SettlementLine,
    SettlementService,
)
from app.modules.erp.infrastructure.models import (
    Customer,
    DocumentAction,
    DocumentStatus,
    FinancePayment,
    FinancePaymentItem,
    FinanceReceipt,
    FinanceReceiptItem,
    SettlementAccount,
    SettlementSourceType,
    Supplier,
)
from app.modules.erp.infrastructure.tenant_uow import ErpTenantUowDep
from app.modules.erp.observability import ErpDocumentCommandMetricRoute
from app.modules.erp.public_api.dto import (
    DocumentCommand,
    DocumentReverseCommand,
    FinancePaymentCreate,
    FinancePaymentItemPublic,
    FinancePaymentPublic,
    FinancePaymentsPublic,
    FinancePaymentUpdate,
    FinanceReceiptCreate,
    FinanceReceiptItemPublic,
    FinanceReceiptPublic,
    FinanceReceiptsPublic,
    FinanceReceiptUpdate,
    SettlementLineCreate,
)
from app.platform.web_api import (
    CurrentPrincipal,
    CurrentTenant,
    build_owner_data_scope_filter,
    normalize_pagination,
    require_module_access,
)

router = APIRouter(
    prefix="/erp",
    tags=["erp-finance-documents"],
    route_class=ErpDocumentCommandMetricRoute,
)


def document_scope(*, uow: ErpTenantUowDep, principal: CurrentPrincipal, owner_column: Any) -> Any:
    return build_owner_data_scope_filter(
        session=uow.session,
        current_principal=principal,
        tenant_id=uow.tenant_id,
        owner_id_column=owner_column,
    )


def payment_public(uow: ErpTenantUowDep, document: FinancePayment) -> FinancePaymentPublic:
    items = uow.session.exec(
        select(FinancePaymentItem)
        .where(FinancePaymentItem.finance_payment_id == document.id)
        .order_by(FinancePaymentItem.source_type, FinancePaymentItem.source_document_id)
    ).all()
    return FinancePaymentPublic.model_validate(document).model_copy(
        update={"items": [FinancePaymentItemPublic.model_validate(item) for item in items]}
    )


def receipt_public(uow: ErpTenantUowDep, document: FinanceReceipt) -> FinanceReceiptPublic:
    items = uow.session.exec(
        select(FinanceReceiptItem)
        .where(FinanceReceiptItem.finance_receipt_id == document.id)
        .order_by(FinanceReceiptItem.source_type, FinanceReceiptItem.source_document_id)
    ).all()
    return FinanceReceiptPublic.model_validate(document).model_copy(
        update={"items": [FinanceReceiptItemPublic.model_validate(item) for item in items]}
    )


def settlement_lines(items: list[SettlementLineCreate]) -> tuple[SettlementLine, ...]:
    try:
        return tuple(
            SettlementLine(
                source_type=SettlementSourceType(item.source_type),
                source_document_id=item.source_document_id,
                settlement_amount=item.settlement_amount,
                remark=item.remark,
            )
            for item in items
        )
    except ValueError as exc:
        raise HTTPException(status_code=422, detail="Settlement source type is invalid") from exc


def payment_planned_items(items: list[FinancePaymentItem]) -> tuple[PlannedSettlementLine, ...]:
    return tuple(
        PlannedSettlementLine(
            source_type=SettlementSourceType(item.source_type),
            source_document_id=item.source_document_id,
            source_document_no=item.source_document_no,
            source_total_signed=item.source_total_signed,
            settled_before_signed=item.settled_before_signed,
            settlement_signed=item.settlement_signed,
            discount_allocated=item.discount_allocated,
            remark=item.remark,
        )
        for item in items
    )


def receipt_planned_items(items: list[FinanceReceiptItem]) -> tuple[PlannedSettlementLine, ...]:
    return tuple(
        PlannedSettlementLine(
            source_type=SettlementSourceType(item.source_type),
            source_document_id=item.source_document_id,
            source_document_no=item.source_document_no,
            source_total_signed=item.source_total_signed,
            settled_before_signed=item.settled_before_signed,
            settlement_signed=item.settlement_signed,
            discount_allocated=item.discount_allocated,
            remark=item.remark,
        )
        for item in items
    )


def ensure_active_account(*, uow: ErpTenantUowDep, account_id: uuid.UUID, lock: bool = False) -> SettlementAccount:
    statement = select(SettlementAccount).where(SettlementAccount.id == account_id)
    if lock:
        statement = statement.with_for_update()
    account = uow.session.exec(statement).first()
    if account is None or not account.is_active:
        raise HTTPException(status_code=409, detail="Settlement account is unavailable")
    return account


def conflict(exc: SettlementConflictError) -> HTTPException:
    return HTTPException(status_code=409, detail=str(exc))


def command_claim(
    *,
    uow: ErpTenantUowDep,
    command_name: str,
    idempotency_key: str,
    principal: CurrentPrincipal,
    payload: dict[str, Any],
    resource_id: uuid.UUID | None = None,
) -> CommandReceiptClaim:
    try:
        return claim_command(
            uow=uow,
            command_name=command_name,
            idempotency_key=idempotency_key,
            request_hash=command_request_sha256(
                command_name=command_name,
                actor_id=principal.id,
                payload=payload,
                resource_id=resource_id,
            ),
        )
    except (IdempotencyConflictError, IdempotencyInProgressError) as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc


def replay_payment(uow: ErpTenantUowDep, claim: CommandReceiptClaim) -> FinancePaymentPublic:
    if claim.receipt.resource_type != "finance_payment" or claim.receipt.resource_id is None:
        raise HTTPException(status_code=409, detail="Idempotency receipt has no payment resource")
    document = uow.session.get(FinancePayment, claim.receipt.resource_id)
    if document is None:
        raise HTTPException(status_code=409, detail="Idempotency receipt payment is unavailable")
    return payment_public(uow, document)


def replay_receipt(uow: ErpTenantUowDep, claim: CommandReceiptClaim) -> FinanceReceiptPublic:
    if claim.receipt.resource_type != "finance_receipt" or claim.receipt.resource_id is None:
        raise HTTPException(status_code=409, detail="Idempotency receipt has no receipt resource")
    document = uow.session.get(FinanceReceipt, claim.receipt.resource_id)
    if document is None:
        raise HTTPException(status_code=409, detail="Idempotency receipt receipt is unavailable")
    return receipt_public(uow, document)


def mark_approved(document: FinancePayment | FinanceReceipt, principal: CurrentPrincipal) -> None:
    document.status = DocumentStatus.APPROVED
    document.version += 1
    document.approved_by = principal.id
    document.approved_at = get_datetime_utc()
    document.updated_by = principal.id
    document.updated_at = get_datetime_utc()


def mark_reversed(document: FinancePayment | FinanceReceipt, principal: CurrentPrincipal) -> None:
    document.status = DocumentStatus.DRAFT
    document.version += 1
    document.reversed_by = principal.id
    document.reversed_at = get_datetime_utc()
    document.updated_by = principal.id
    document.updated_at = get_datetime_utc()


@router.get(
    "/finance-payments",
    dependencies=[Depends(require_module_access("erp", "erp:finance-payment:list"))],
    response_model=FinancePaymentsPublic,
)
def read_finance_payments(
    uow: ErpTenantUowDep, principal: CurrentPrincipal, page: int = 1, page_size: int = 20,
    keyword: str | None = None, supplier_id: uuid.UUID | None = None, owner_id: uuid.UUID | None = None,
    status: str | None = None, remark: str | None = None, business_from: datetime | None = None, business_to: datetime | None = None,
) -> FinancePaymentsPublic:
    page, page_size = normalize_pagination(page=page, page_size=page_size)
    try:
        filters = financial_document_filters(model=FinancePayment, counterparty_id_column=FinancePayment.supplier_id, counterparty_name_column=FinancePayment.supplier_name, scope=document_scope(uow=uow, principal=principal, owner_column=FinancePayment.owner_id), keyword=keyword, counterparty_id=supplier_id, owner_id=owner_id, status=status, remark=remark, business_from=business_from, business_to=business_to)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    total = int(uow.session.exec(select(func.count()).select_from(FinancePayment).where(*filters)).one())
    documents = uow.session.exec(
        select(FinancePayment).where(*filters).order_by(col(FinancePayment.business_at).desc()).offset((page - 1) * page_size).limit(page_size)
    ).all()
    return FinancePaymentsPublic(items=[payment_public(uow, document) for document in documents], total=total, page=page, page_size=page_size)


@router.post(
    "/finance-payments",
    dependencies=[Depends(require_module_access("erp", "erp:finance-payment:create"))],
    response_model=FinancePaymentPublic,
)
def create_finance_payment(
    command: FinancePaymentCreate,
    uow: ErpTenantUowDep,
    principal: CurrentPrincipal,
    tenant: CurrentTenant,
    idempotency_key: str = Header(alias="Idempotency-Key"),
) -> FinancePaymentPublic:
    supplier = uow.session.get(Supplier, command.supplier_id)
    if supplier is None or not supplier.is_active:
        raise HTTPException(status_code=409, detail="Supplier is unavailable")
    ensure_active_account(uow=uow, account_id=command.settlement_account_id)
    try:
        planned, total_settlement_amount, payment_amount = SettlementService(uow).plan(
            flow="payment", counterparty_id=supplier.id, lines=settlement_lines(command.items), discount_amount=command.discount_amount
        )
    except SettlementConflictError as exc:
        raise conflict(exc) from exc
    claim = command_claim(
        uow=uow,
        command_name="erp.finance-payment.create",
        idempotency_key=idempotency_key,
        principal=principal,
        payload=command.model_dump(mode="json"),
    )
    if claim.replay:
        return replay_payment(uow, claim)
    document = FinancePayment(
        tenant_id=tenant.tenant_id, no=allocate_document_no(uow=uow, prefix="FKD"), supplier_id=supplier.id,
        supplier_name=supplier.name, settlement_account_id=command.settlement_account_id,
        business_at=resolve_business_at(uow=uow, requested_at=command.business_at), owner_id=principal.id,
        total_settlement_amount=total_settlement_amount, discount_amount=command.discount_amount,
        payment_amount=payment_amount, remark=command.remark, created_by=principal.id, updated_by=principal.id,
    )
    uow.session.add(document)
    uow.session.flush()
    uow.session.add_all([
        FinancePaymentItem(
            tenant_id=tenant.tenant_id, finance_payment_id=document.id, source_type=line.source_type,
            source_document_id=line.source_document_id, source_document_no=line.source_document_no,
            source_total_signed=line.source_total_signed, settled_before_signed=line.settled_before_signed,
            settlement_signed=line.settlement_signed, discount_allocated=line.discount_allocated, remark=line.remark,
        )
        for line in planned
    ])
    record_action(
        uow=uow,
        resource_type="finance_payment",
        resource_id=document.id,
        resource_no=document.no,
        action=DocumentAction.CREATED,
        actor_id=principal.id,
        new_status=str(document.status),
        new_version=document.version,
        metadata={"item_count": len(planned)},
    )
    complete_command(
        receipt=claim.receipt,
        resource_type="finance_payment",
        resource_id=document.id,
        resource_version=document.version,
    )
    uow.session.commit()
    uow.session.refresh(document)
    return payment_public(uow, document)


@router.get("/finance-payments/{document_id}", dependencies=[Depends(require_module_access("erp", "erp:finance-payment:list"))], response_model=FinancePaymentPublic)
def read_finance_payment(document_id: uuid.UUID, uow: ErpTenantUowDep, principal: CurrentPrincipal) -> FinancePaymentPublic:
    document = uow.session.get(FinancePayment, document_id)
    if document is None:
        raise HTTPException(status_code=404, detail="Payment document not found")
    permitted = uow.session.exec(select(FinancePayment.id).where(FinancePayment.id == document.id, document_scope(uow=uow, principal=principal, owner_column=FinancePayment.owner_id))).first()
    if permitted is None:
        raise HTTPException(status_code=403, detail="Not enough permissions")
    return payment_public(uow, document)


@router.patch("/finance-payments/{document_id}", dependencies=[Depends(require_module_access("erp", "erp:finance-payment:update"))], response_model=FinancePaymentPublic)
def update_finance_payment(document_id: uuid.UUID, command: FinancePaymentUpdate, uow: ErpTenantUowDep, principal: CurrentPrincipal) -> FinancePaymentPublic:
    document = uow.session.exec(select(FinancePayment).where(FinancePayment.id == document_id).with_for_update()).first()
    if document is None:
        raise HTTPException(status_code=404, detail="Payment document not found")
    permitted = uow.session.exec(select(FinancePayment.id).where(FinancePayment.id == document.id, document_scope(uow=uow, principal=principal, owner_column=FinancePayment.owner_id))).first()
    if permitted is None:
        raise HTTPException(status_code=403, detail="Not enough permissions")
    if document.status != DocumentStatus.DRAFT or document.version != command.expected_version:
        raise HTTPException(status_code=409, detail="Payment document version conflict")
    supplier = uow.session.get(Supplier, command.supplier_id)
    if supplier is None or not supplier.is_active:
        raise HTTPException(status_code=409, detail="Supplier is unavailable")
    ensure_active_account(uow=uow, account_id=command.settlement_account_id)
    try:
        planned, total_settlement_amount, payment_amount = SettlementService(uow).plan(flow="payment", counterparty_id=supplier.id, lines=settlement_lines(command.items), discount_amount=command.discount_amount)
    except SettlementConflictError as exc:
        raise conflict(exc) from exc
    old_version = document.version
    for item in uow.session.exec(select(FinancePaymentItem).where(FinancePaymentItem.finance_payment_id == document.id)).all():
        uow.session.delete(item)
    uow.session.flush()
    document.supplier_id, document.supplier_name, document.settlement_account_id = supplier.id, supplier.name, command.settlement_account_id
    document.business_at = resolve_business_at(uow=uow, requested_at=command.business_at) if command.business_at is not None else document.business_at
    document.total_settlement_amount, document.discount_amount, document.payment_amount, document.remark = total_settlement_amount, command.discount_amount, payment_amount, command.remark
    document.version += 1
    document.updated_by, document.updated_at = principal.id, get_datetime_utc()
    uow.session.add(document)
    uow.session.add_all([FinancePaymentItem(tenant_id=uow.tenant_id, finance_payment_id=document.id, source_type=line.source_type, source_document_id=line.source_document_id, source_document_no=line.source_document_no, source_total_signed=line.source_total_signed, settled_before_signed=line.settled_before_signed, settlement_signed=line.settlement_signed, discount_allocated=line.discount_allocated, remark=line.remark) for line in planned])
    record_action(uow=uow, resource_type="finance_payment", resource_id=document.id, resource_no=document.no, action=DocumentAction.UPDATED, actor_id=principal.id, old_version=old_version, new_version=document.version, metadata={"item_count": len(planned)})
    uow.session.commit()
    uow.session.refresh(document)
    return payment_public(uow, document)


@router.delete("/finance-payments/{document_id}", dependencies=[Depends(require_module_access("erp", "erp:finance-payment:delete"))], status_code=204)
def delete_finance_payment(document_id: uuid.UUID, uow: ErpTenantUowDep, principal: CurrentPrincipal) -> Response:
    document = uow.session.exec(select(FinancePayment).where(FinancePayment.id == document_id).with_for_update()).first()
    if document is None:
        raise HTTPException(status_code=404, detail="Payment document not found")
    permitted = uow.session.exec(select(FinancePayment.id).where(FinancePayment.id == document.id, document_scope(uow=uow, principal=principal, owner_column=FinancePayment.owner_id))).first()
    if permitted is None:
        raise HTTPException(status_code=403, detail="Not enough permissions")
    if document.status != DocumentStatus.DRAFT:
        raise HTTPException(status_code=409, detail="Payment document must be draft before deletion")
    record_action(uow=uow, resource_type="finance_payment", resource_id=document.id, resource_no=document.no, action=DocumentAction.DELETED, actor_id=principal.id, old_status=str(document.status), old_version=document.version)
    uow.session.delete(document)
    uow.session.commit()
    return Response(status_code=204)


@router.post(
    "/finance-payments/{document_id}/approve",
    dependencies=[Depends(require_module_access("erp", "erp:finance-payment:approve"))],
    response_model=FinancePaymentPublic,
)
def approve_finance_payment(
    document_id: uuid.UUID,
    command: DocumentCommand,
    uow: ErpTenantUowDep,
    principal: CurrentPrincipal,
    idempotency_key: str = Header(alias="Idempotency-Key"),
) -> FinancePaymentPublic:
    document = uow.session.exec(select(FinancePayment).where(FinancePayment.id == document_id).with_for_update()).first()
    if document is None:
        raise HTTPException(status_code=404, detail="Payment document not found")
    permitted = uow.session.exec(select(FinancePayment.id).where(FinancePayment.id == document.id, document_scope(uow=uow, principal=principal, owner_column=FinancePayment.owner_id))).first()
    if permitted is None:
        raise HTTPException(status_code=403, detail="Not enough permissions")
    claim = command_claim(
        uow=uow,
        command_name="erp.finance-payment.approve",
        idempotency_key=idempotency_key,
        principal=principal,
        payload=command.model_dump(mode="json"),
        resource_id=document_id,
    )
    if claim.replay:
        return replay_payment(uow, claim)
    if document.status != DocumentStatus.DRAFT or document.version != command.expected_version:
        raise HTTPException(status_code=409, detail="Payment document version conflict")
    ensure_active_account(uow=uow, account_id=document.settlement_account_id, lock=True)
    items = uow.session.exec(select(FinancePaymentItem).where(FinancePaymentItem.finance_payment_id == document.id)).all()
    try:
        SettlementService(uow).apply(flow="payment", counterparty_id=document.supplier_id, lines=payment_planned_items(items))
    except SettlementConflictError as exc:
        uow.session.rollback()
        raise conflict(exc) from exc
    old_status, old_version = str(document.status), document.version
    mark_approved(document, principal)
    uow.session.add(document)
    enqueue_document_lifecycle_event(
        uow=uow, document=document, document_type="payment", action="approved"
    )
    record_action(
        uow=uow,
        resource_type="finance_payment",
        resource_id=document.id,
        resource_no=document.no,
        action=DocumentAction.APPROVED,
        actor_id=principal.id,
        old_status=old_status,
        new_status=str(document.status),
        old_version=old_version,
        new_version=document.version,
    )
    complete_command(
        receipt=claim.receipt,
        resource_type="finance_payment",
        resource_id=document.id,
        resource_version=document.version,
    )
    uow.session.commit()
    uow.session.refresh(document)
    return payment_public(uow, document)


@router.post(
    "/finance-payments/{document_id}/reverse",
    dependencies=[Depends(require_module_access("erp", "erp:finance-payment:reverse"))],
    response_model=FinancePaymentPublic,
)
def reverse_finance_payment(
    document_id: uuid.UUID,
    command: DocumentReverseCommand,
    uow: ErpTenantUowDep,
    principal: CurrentPrincipal,
    idempotency_key: str = Header(alias="Idempotency-Key"),
) -> FinancePaymentPublic:
    document = uow.session.exec(select(FinancePayment).where(FinancePayment.id == document_id).with_for_update()).first()
    if document is None:
        raise HTTPException(status_code=404, detail="Payment document not found")
    permitted = uow.session.exec(select(FinancePayment.id).where(FinancePayment.id == document.id, document_scope(uow=uow, principal=principal, owner_column=FinancePayment.owner_id))).first()
    if permitted is None:
        raise HTTPException(status_code=403, detail="Not enough permissions")
    claim = command_claim(
        uow=uow,
        command_name="erp.finance-payment.reverse",
        idempotency_key=idempotency_key,
        principal=principal,
        payload=command.model_dump(mode="json"),
        resource_id=document_id,
    )
    if claim.replay:
        return replay_payment(uow, claim)
    if document.status != DocumentStatus.APPROVED or document.version != command.expected_version:
        raise HTTPException(status_code=409, detail="Payment document version conflict")
    items = uow.session.exec(select(FinancePaymentItem).where(FinancePaymentItem.finance_payment_id == document.id)).all()
    try:
        SettlementService(uow).apply(flow="payment", counterparty_id=document.supplier_id, lines=payment_planned_items(items), reverse=True)
    except SettlementConflictError as exc:
        uow.session.rollback()
        raise conflict(exc) from exc
    old_status, old_version = str(document.status), document.version
    mark_reversed(document, principal)
    uow.session.add(document)
    enqueue_document_lifecycle_event(
        uow=uow, document=document, document_type="payment", action="reversed"
    )
    record_action(
        uow=uow,
        resource_type="finance_payment",
        resource_id=document.id,
        resource_no=document.no,
        action=DocumentAction.REVERSED,
        actor_id=principal.id,
        old_status=old_status,
        new_status=str(document.status),
        old_version=old_version,
        new_version=document.version,
        reason=command.reason,
    )
    complete_command(
        receipt=claim.receipt,
        resource_type="finance_payment",
        resource_id=document.id,
        resource_version=document.version,
    )
    uow.session.commit()
    uow.session.refresh(document)
    return payment_public(uow, document)


@router.get(
    "/finance-receipts",
    dependencies=[Depends(require_module_access("erp", "erp:finance-receipt:list"))],
    response_model=FinanceReceiptsPublic,
)
def read_finance_receipts(
    uow: ErpTenantUowDep, principal: CurrentPrincipal, page: int = 1, page_size: int = 20,
    keyword: str | None = None, customer_id: uuid.UUID | None = None, owner_id: uuid.UUID | None = None,
    status: str | None = None, remark: str | None = None, business_from: datetime | None = None, business_to: datetime | None = None,
) -> FinanceReceiptsPublic:
    page, page_size = normalize_pagination(page=page, page_size=page_size)
    try:
        filters = financial_document_filters(model=FinanceReceipt, counterparty_id_column=FinanceReceipt.customer_id, counterparty_name_column=FinanceReceipt.customer_name, scope=document_scope(uow=uow, principal=principal, owner_column=FinanceReceipt.owner_id), keyword=keyword, counterparty_id=customer_id, owner_id=owner_id, status=status, remark=remark, business_from=business_from, business_to=business_to)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    total = int(uow.session.exec(select(func.count()).select_from(FinanceReceipt).where(*filters)).one())
    documents = uow.session.exec(
        select(FinanceReceipt).where(*filters).order_by(col(FinanceReceipt.business_at).desc()).offset((page - 1) * page_size).limit(page_size)
    ).all()
    return FinanceReceiptsPublic(items=[receipt_public(uow, document) for document in documents], total=total, page=page, page_size=page_size)


@router.post(
    "/finance-receipts",
    dependencies=[Depends(require_module_access("erp", "erp:finance-receipt:create"))],
    response_model=FinanceReceiptPublic,
)
def create_finance_receipt(
    command: FinanceReceiptCreate,
    uow: ErpTenantUowDep,
    principal: CurrentPrincipal,
    tenant: CurrentTenant,
    idempotency_key: str = Header(alias="Idempotency-Key"),
) -> FinanceReceiptPublic:
    customer = uow.session.get(Customer, command.customer_id)
    if customer is None or not customer.is_active:
        raise HTTPException(status_code=409, detail="Customer is unavailable")
    ensure_active_account(uow=uow, account_id=command.settlement_account_id)
    try:
        planned, total_settlement_amount, receipt_amount = SettlementService(uow).plan(
            flow="receipt", counterparty_id=customer.id, lines=settlement_lines(command.items), discount_amount=command.discount_amount
        )
    except SettlementConflictError as exc:
        raise conflict(exc) from exc
    claim = command_claim(
        uow=uow,
        command_name="erp.finance-receipt.create",
        idempotency_key=idempotency_key,
        principal=principal,
        payload=command.model_dump(mode="json"),
    )
    if claim.replay:
        return replay_receipt(uow, claim)
    document = FinanceReceipt(
        tenant_id=tenant.tenant_id, no=allocate_document_no(uow=uow, prefix="SKD"), customer_id=customer.id,
        customer_name=customer.name, settlement_account_id=command.settlement_account_id,
        business_at=resolve_business_at(uow=uow, requested_at=command.business_at), owner_id=principal.id,
        total_settlement_amount=total_settlement_amount, discount_amount=command.discount_amount,
        receipt_amount=receipt_amount, remark=command.remark, created_by=principal.id, updated_by=principal.id,
    )
    uow.session.add(document)
    uow.session.flush()
    uow.session.add_all([
        FinanceReceiptItem(
            tenant_id=tenant.tenant_id, finance_receipt_id=document.id, source_type=line.source_type,
            source_document_id=line.source_document_id, source_document_no=line.source_document_no,
            source_total_signed=line.source_total_signed, settled_before_signed=line.settled_before_signed,
            settlement_signed=line.settlement_signed, discount_allocated=line.discount_allocated, remark=line.remark,
        )
        for line in planned
    ])
    record_action(
        uow=uow,
        resource_type="finance_receipt",
        resource_id=document.id,
        resource_no=document.no,
        action=DocumentAction.CREATED,
        actor_id=principal.id,
        new_status=str(document.status),
        new_version=document.version,
        metadata={"item_count": len(planned)},
    )
    complete_command(
        receipt=claim.receipt,
        resource_type="finance_receipt",
        resource_id=document.id,
        resource_version=document.version,
    )
    uow.session.commit()
    uow.session.refresh(document)
    return receipt_public(uow, document)


@router.get("/finance-receipts/{document_id}", dependencies=[Depends(require_module_access("erp", "erp:finance-receipt:list"))], response_model=FinanceReceiptPublic)
def read_finance_receipt(document_id: uuid.UUID, uow: ErpTenantUowDep, principal: CurrentPrincipal) -> FinanceReceiptPublic:
    document = uow.session.get(FinanceReceipt, document_id)
    if document is None:
        raise HTTPException(status_code=404, detail="Receipt document not found")
    permitted = uow.session.exec(select(FinanceReceipt.id).where(FinanceReceipt.id == document.id, document_scope(uow=uow, principal=principal, owner_column=FinanceReceipt.owner_id))).first()
    if permitted is None:
        raise HTTPException(status_code=403, detail="Not enough permissions")
    return receipt_public(uow, document)


@router.patch("/finance-receipts/{document_id}", dependencies=[Depends(require_module_access("erp", "erp:finance-receipt:update"))], response_model=FinanceReceiptPublic)
def update_finance_receipt(document_id: uuid.UUID, command: FinanceReceiptUpdate, uow: ErpTenantUowDep, principal: CurrentPrincipal) -> FinanceReceiptPublic:
    document = uow.session.exec(select(FinanceReceipt).where(FinanceReceipt.id == document_id).with_for_update()).first()
    if document is None:
        raise HTTPException(status_code=404, detail="Receipt document not found")
    permitted = uow.session.exec(select(FinanceReceipt.id).where(FinanceReceipt.id == document.id, document_scope(uow=uow, principal=principal, owner_column=FinanceReceipt.owner_id))).first()
    if permitted is None:
        raise HTTPException(status_code=403, detail="Not enough permissions")
    if document.status != DocumentStatus.DRAFT or document.version != command.expected_version:
        raise HTTPException(status_code=409, detail="Receipt document version conflict")
    customer = uow.session.get(Customer, command.customer_id)
    if customer is None or not customer.is_active:
        raise HTTPException(status_code=409, detail="Customer is unavailable")
    ensure_active_account(uow=uow, account_id=command.settlement_account_id)
    try:
        planned, total_settlement_amount, receipt_amount = SettlementService(uow).plan(flow="receipt", counterparty_id=customer.id, lines=settlement_lines(command.items), discount_amount=command.discount_amount)
    except SettlementConflictError as exc:
        raise conflict(exc) from exc
    old_version = document.version
    for item in uow.session.exec(select(FinanceReceiptItem).where(FinanceReceiptItem.finance_receipt_id == document.id)).all():
        uow.session.delete(item)
    uow.session.flush()
    document.customer_id, document.customer_name, document.settlement_account_id = customer.id, customer.name, command.settlement_account_id
    document.business_at = resolve_business_at(uow=uow, requested_at=command.business_at) if command.business_at is not None else document.business_at
    document.total_settlement_amount, document.discount_amount, document.receipt_amount, document.remark = total_settlement_amount, command.discount_amount, receipt_amount, command.remark
    document.version += 1
    document.updated_by, document.updated_at = principal.id, get_datetime_utc()
    uow.session.add(document)
    uow.session.add_all([FinanceReceiptItem(tenant_id=uow.tenant_id, finance_receipt_id=document.id, source_type=line.source_type, source_document_id=line.source_document_id, source_document_no=line.source_document_no, source_total_signed=line.source_total_signed, settled_before_signed=line.settled_before_signed, settlement_signed=line.settlement_signed, discount_allocated=line.discount_allocated, remark=line.remark) for line in planned])
    record_action(uow=uow, resource_type="finance_receipt", resource_id=document.id, resource_no=document.no, action=DocumentAction.UPDATED, actor_id=principal.id, old_version=old_version, new_version=document.version, metadata={"item_count": len(planned)})
    uow.session.commit()
    uow.session.refresh(document)
    return receipt_public(uow, document)


@router.delete("/finance-receipts/{document_id}", dependencies=[Depends(require_module_access("erp", "erp:finance-receipt:delete"))], status_code=204)
def delete_finance_receipt(document_id: uuid.UUID, uow: ErpTenantUowDep, principal: CurrentPrincipal) -> Response:
    document = uow.session.exec(select(FinanceReceipt).where(FinanceReceipt.id == document_id).with_for_update()).first()
    if document is None:
        raise HTTPException(status_code=404, detail="Receipt document not found")
    permitted = uow.session.exec(select(FinanceReceipt.id).where(FinanceReceipt.id == document.id, document_scope(uow=uow, principal=principal, owner_column=FinanceReceipt.owner_id))).first()
    if permitted is None:
        raise HTTPException(status_code=403, detail="Not enough permissions")
    if document.status != DocumentStatus.DRAFT:
        raise HTTPException(status_code=409, detail="Receipt document must be draft before deletion")
    record_action(uow=uow, resource_type="finance_receipt", resource_id=document.id, resource_no=document.no, action=DocumentAction.DELETED, actor_id=principal.id, old_status=str(document.status), old_version=document.version)
    uow.session.delete(document)
    uow.session.commit()
    return Response(status_code=204)


@router.post(
    "/finance-receipts/{document_id}/approve",
    dependencies=[Depends(require_module_access("erp", "erp:finance-receipt:approve"))],
    response_model=FinanceReceiptPublic,
)
def approve_finance_receipt(
    document_id: uuid.UUID,
    command: DocumentCommand,
    uow: ErpTenantUowDep,
    principal: CurrentPrincipal,
    idempotency_key: str = Header(alias="Idempotency-Key"),
) -> FinanceReceiptPublic:
    document = uow.session.exec(select(FinanceReceipt).where(FinanceReceipt.id == document_id).with_for_update()).first()
    if document is None:
        raise HTTPException(status_code=404, detail="Receipt document not found")
    permitted = uow.session.exec(select(FinanceReceipt.id).where(FinanceReceipt.id == document.id, document_scope(uow=uow, principal=principal, owner_column=FinanceReceipt.owner_id))).first()
    if permitted is None:
        raise HTTPException(status_code=403, detail="Not enough permissions")
    claim = command_claim(
        uow=uow,
        command_name="erp.finance-receipt.approve",
        idempotency_key=idempotency_key,
        principal=principal,
        payload=command.model_dump(mode="json"),
        resource_id=document_id,
    )
    if claim.replay:
        return replay_receipt(uow, claim)
    if document.status != DocumentStatus.DRAFT or document.version != command.expected_version:
        raise HTTPException(status_code=409, detail="Receipt document version conflict")
    ensure_active_account(uow=uow, account_id=document.settlement_account_id, lock=True)
    items = uow.session.exec(select(FinanceReceiptItem).where(FinanceReceiptItem.finance_receipt_id == document.id)).all()
    try:
        SettlementService(uow).apply(flow="receipt", counterparty_id=document.customer_id, lines=receipt_planned_items(items))
    except SettlementConflictError as exc:
        uow.session.rollback()
        raise conflict(exc) from exc
    old_status, old_version = str(document.status), document.version
    mark_approved(document, principal)
    uow.session.add(document)
    enqueue_document_lifecycle_event(
        uow=uow, document=document, document_type="receipt", action="approved"
    )
    record_action(
        uow=uow,
        resource_type="finance_receipt",
        resource_id=document.id,
        resource_no=document.no,
        action=DocumentAction.APPROVED,
        actor_id=principal.id,
        old_status=old_status,
        new_status=str(document.status),
        old_version=old_version,
        new_version=document.version,
    )
    complete_command(
        receipt=claim.receipt,
        resource_type="finance_receipt",
        resource_id=document.id,
        resource_version=document.version,
    )
    uow.session.commit()
    uow.session.refresh(document)
    return receipt_public(uow, document)


@router.post(
    "/finance-receipts/{document_id}/reverse",
    dependencies=[Depends(require_module_access("erp", "erp:finance-receipt:reverse"))],
    response_model=FinanceReceiptPublic,
)
def reverse_finance_receipt(
    document_id: uuid.UUID,
    command: DocumentReverseCommand,
    uow: ErpTenantUowDep,
    principal: CurrentPrincipal,
    idempotency_key: str = Header(alias="Idempotency-Key"),
) -> FinanceReceiptPublic:
    document = uow.session.exec(select(FinanceReceipt).where(FinanceReceipt.id == document_id).with_for_update()).first()
    if document is None:
        raise HTTPException(status_code=404, detail="Receipt document not found")
    permitted = uow.session.exec(select(FinanceReceipt.id).where(FinanceReceipt.id == document.id, document_scope(uow=uow, principal=principal, owner_column=FinanceReceipt.owner_id))).first()
    if permitted is None:
        raise HTTPException(status_code=403, detail="Not enough permissions")
    claim = command_claim(
        uow=uow,
        command_name="erp.finance-receipt.reverse",
        idempotency_key=idempotency_key,
        principal=principal,
        payload=command.model_dump(mode="json"),
        resource_id=document_id,
    )
    if claim.replay:
        return replay_receipt(uow, claim)
    if document.status != DocumentStatus.APPROVED or document.version != command.expected_version:
        raise HTTPException(status_code=409, detail="Receipt document version conflict")
    items = uow.session.exec(select(FinanceReceiptItem).where(FinanceReceiptItem.finance_receipt_id == document.id)).all()
    try:
        SettlementService(uow).apply(flow="receipt", counterparty_id=document.customer_id, lines=receipt_planned_items(items), reverse=True)
    except SettlementConflictError as exc:
        uow.session.rollback()
        raise conflict(exc) from exc
    old_status, old_version = str(document.status), document.version
    mark_reversed(document, principal)
    uow.session.add(document)
    enqueue_document_lifecycle_event(
        uow=uow, document=document, document_type="receipt", action="reversed"
    )
    record_action(
        uow=uow,
        resource_type="finance_receipt",
        resource_id=document.id,
        resource_no=document.no,
        action=DocumentAction.REVERSED,
        actor_id=principal.id,
        old_status=old_status,
        new_status=str(document.status),
        old_version=old_version,
        new_version=document.version,
        reason=command.reason,
    )
    complete_command(
        receipt=claim.receipt,
        resource_type="finance_receipt",
        resource_id=document.id,
        resource_version=document.version,
    )
    uow.session.commit()
    uow.session.refresh(document)
    return receipt_public(uow, document)
