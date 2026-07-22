"""Sale order HTTP contracts."""

import uuid
from datetime import datetime

from fastapi import APIRouter, Depends, Header, HTTPException, Response
from sqlmodel import col, func, select

from app.core.clock import get_datetime_utc
from app.modules.erp.application.action_log import record_action
from app.modules.erp.application.business_time import resolve_business_at
from app.modules.erp.application.document_listing import document_list_filters
from app.modules.erp.application.document_numbers import allocate_document_no
from app.modules.erp.application.events import enqueue_document_lifecycle_event
from app.modules.erp.application.idempotency import (
    CommandReceiptClaim,
    IdempotencyConflictError,
    IdempotencyInProgressError,
    claim_command,
    complete_command,
    request_sha256,
)
from app.modules.erp.application.sale_orders import (
    SaleOrderConflictError,
    calculate_sale_order,
)
from app.modules.erp.application.settlement_accounts import (
    SettlementAccountUnavailableError,
    ensure_active_settlement_account,
)
from app.modules.erp.infrastructure.models import (
    DocumentAction,
    DocumentStatus,
    SaleOrder,
    SaleOrderItem,
)
from app.modules.erp.infrastructure.tenant_uow import ErpTenantUowDep
from app.modules.erp.observability import ErpDocumentCommandMetricRoute
from app.modules.erp.public_api.dto import (
    DocumentCommand,
    DocumentReverseCommand,
    SaleOrderCreate,
    SaleOrderItemPublic,
    SaleOrderPublic,
    SaleOrdersPublic,
    SaleOrderUpdate,
)
from app.platform.web_api import (
    CurrentPrincipal,
    CurrentTenant,
    build_owner_data_scope_filter,
    normalize_pagination,
    require_module_access,
)

router = APIRouter(
    prefix="/erp", tags=["erp-sale"], route_class=ErpDocumentCommandMetricRoute
)


def command_claim(
    *,
    uow: ErpTenantUowDep,
    command_name: str,
    idempotency_key: str,
    principal: CurrentPrincipal,
    payload: dict[str, object],
    resource_id: uuid.UUID | None = None,
) -> CommandReceiptClaim:
    try:
        return claim_command(
            uow=uow,
            command_name=command_name,
            idempotency_key=idempotency_key,
            request_hash=request_sha256(
                command_name=command_name,
                actor_id=principal.id,
                payload=payload,
                resource_id=resource_id,
            ),
        )
    except (IdempotencyConflictError, IdempotencyInProgressError) as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc


def replay_order(
    uow: ErpTenantUowDep, claim: CommandReceiptClaim, principal: CurrentPrincipal
) -> SaleOrderPublic:
    if claim.receipt.resource_type != "sale_order" or claim.receipt.resource_id is None:
        raise HTTPException(status_code=409, detail="Idempotency receipt is unavailable")
    order = get_scoped_order(
        order_id=claim.receipt.resource_id, uow=uow, principal=principal
    )
    return public_order(uow, order)


def order_scope(*, uow: ErpTenantUowDep, principal: CurrentPrincipal):
    return build_owner_data_scope_filter(
        session=uow.session,
        current_principal=principal,
        tenant_id=uow.tenant_id,
        owner_id_column=SaleOrder.owner_id,
    )


def public_order(uow: ErpTenantUowDep, order: SaleOrder) -> SaleOrderPublic:
    items = uow.session.exec(
        select(SaleOrderItem)
        .where(SaleOrderItem.sale_order_id == order.id)
        .order_by(SaleOrderItem.line_no)
    ).all()
    return SaleOrderPublic.model_validate(order).model_copy(
        update={"items": [SaleOrderItemPublic.model_validate(item) for item in items]}
    )


def get_scoped_order(*, order_id: uuid.UUID, uow: ErpTenantUowDep, principal: CurrentPrincipal, lock: bool = False) -> SaleOrder:
    statement = select(SaleOrder).where(SaleOrder.id == order_id, order_scope(uow=uow, principal=principal))
    if lock:
        statement = statement.with_for_update()
    order = uow.session.exec(statement).first()
    if order is None:
        raise HTTPException(status_code=404, detail="Sale order not found")
    return order


@router.get("/sale-orders", dependencies=[Depends(require_module_access("erp", "erp:sale-order:list"))], response_model=SaleOrdersPublic)
def read_sale_orders(
    uow: ErpTenantUowDep,
    principal: CurrentPrincipal,
    page: int = 1,
    page_size: int = 20,
    keyword: str | None = None,
    product_id: uuid.UUID | None = None,
    customer_id: uuid.UUID | None = None,
    owner_id: uuid.UUID | None = None,
    status: str | None = None,
    remark: str | None = None,
    business_from: datetime | None = None,
    business_to: datetime | None = None,
) -> SaleOrdersPublic:
    page, page_size = normalize_pagination(page=page, page_size=page_size)
    try:
        filters = document_list_filters(
            model=SaleOrder,
            item_model=SaleOrderItem,
            item_document_column=SaleOrderItem.sale_order_id,
            counterparty_id_column=SaleOrder.customer_id,
            counterparty_name_column=SaleOrder.customer_name,
            scope=order_scope(uow=uow, principal=principal),
            keyword=keyword,
            product_id=product_id,
            counterparty_id=customer_id,
            owner_id=owner_id,
            status=status,
            remark=remark,
            business_from=business_from,
            business_to=business_to,
        )
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    total = int(uow.session.exec(select(func.count()).select_from(SaleOrder).where(*filters)).one())
    orders = uow.session.exec(select(SaleOrder).where(*filters).order_by(col(SaleOrder.business_at).desc()).offset((page - 1) * page_size).limit(page_size)).all()
    return SaleOrdersPublic(items=[public_order(uow, order) for order in orders], total=total, page=page, page_size=page_size)


@router.get("/sale-orders/{order_id}", dependencies=[Depends(require_module_access("erp", "erp:sale-order:list"))], response_model=SaleOrderPublic)
def read_sale_order(order_id: uuid.UUID, uow: ErpTenantUowDep, principal: CurrentPrincipal) -> SaleOrderPublic:
    return public_order(
        uow,
        get_scoped_order(order_id=order_id, uow=uow, principal=principal),
    )


@router.post("/sale-orders", dependencies=[Depends(require_module_access("erp", "erp:sale-order:create"))], response_model=SaleOrderPublic)
def create_sale_order(command: SaleOrderCreate, uow: ErpTenantUowDep, principal: CurrentPrincipal, tenant: CurrentTenant, idempotency_key: str = Header(alias="Idempotency-Key")) -> SaleOrderPublic:
    claim = command_claim(uow=uow, command_name="erp.sale-order.create", idempotency_key=idempotency_key, principal=principal, payload=command.model_dump(mode="json"))
    if claim.replay:
        return replay_order(uow, claim, principal)
    try:
        calculated = calculate_sale_order(uow=uow, command=command)
    except SaleOrderConflictError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    try:
        settlement_account_id = ensure_active_settlement_account(
            uow=uow, account_id=command.settlement_account_id
        )
    except SettlementAccountUnavailableError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    order = SaleOrder(
        tenant_id=tenant.tenant_id, no=allocate_document_no(uow=uow, prefix="XSDD"), customer_id=calculated.customer.id,
        customer_name=calculated.customer.name, settlement_account_id=settlement_account_id, business_at=resolve_business_at(uow=uow, requested_at=command.business_at), owner_id=principal.id,
        total_quantity=calculated.total_quantity, product_amount=calculated.product_amount, tax_amount=calculated.tax_amount,
        discount_rate=command.discount_rate, discount_amount=calculated.discount_amount, deposit_amount=command.deposit_amount,
        total_amount=calculated.total_amount, remark=command.remark, created_by=principal.id, updated_by=principal.id,
    )
    uow.session.add(order)
    uow.session.flush()
    uow.session.add_all([SaleOrderItem(tenant_id=tenant.tenant_id, sale_order_id=order.id, line_no=index, product_id=line.product.id, unit_id=line.unit.id, product_name=line.product.name, product_barcode=line.product.barcode, unit_name=line.unit.name, quantity=line.quantity, unit_price=line.unit_price, product_amount=line.product_amount, tax_rate=line.tax_rate, tax_amount=line.tax_amount, total_amount=line.total_amount, remark=line.remark) for index, line in enumerate(calculated.lines, start=1)])
    complete_command(receipt=claim.receipt, resource_type="sale_order", resource_id=order.id, resource_version=order.version)
    uow.session.commit()
    uow.session.refresh(order)
    return public_order(uow, order)


@router.patch("/sale-orders/{order_id}", dependencies=[Depends(require_module_access("erp", "erp:sale-order:update"))], response_model=SaleOrderPublic)
def update_sale_order(order_id: uuid.UUID, command: SaleOrderUpdate, uow: ErpTenantUowDep, principal: CurrentPrincipal) -> SaleOrderPublic:
    order = get_scoped_order(order_id=order_id, uow=uow, principal=principal, lock=True)
    if order.status != DocumentStatus.DRAFT or order.version != command.expected_version:
        raise HTTPException(status_code=409, detail="Sale order version conflict")
    existing_items = uow.session.exec(select(SaleOrderItem).where(SaleOrderItem.sale_order_id == order.id)).all()
    if any(item.shipped_quantity > 0 or item.returned_quantity > 0 for item in existing_items):
        raise HTTPException(status_code=409, detail="Sale order has downstream documents")
    try:
        calculated = calculate_sale_order(uow=uow, command=command)
    except SaleOrderConflictError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    try:
        settlement_account_id = ensure_active_settlement_account(
            uow=uow, account_id=command.settlement_account_id
        )
    except SettlementAccountUnavailableError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    old_version = order.version
    for item in existing_items:
        uow.session.delete(item)
    uow.session.flush()
    now = get_datetime_utc()
    order.customer_id = calculated.customer.id
    order.customer_name = calculated.customer.name
    order.settlement_account_id = settlement_account_id
    order.business_at = (
        resolve_business_at(uow=uow, requested_at=command.business_at)
        if command.business_at is not None
        else order.business_at
    )
    order.total_quantity = calculated.total_quantity
    order.product_amount = calculated.product_amount
    order.tax_amount = calculated.tax_amount
    order.discount_rate = command.discount_rate
    order.discount_amount = calculated.discount_amount
    order.deposit_amount = command.deposit_amount
    order.total_amount = calculated.total_amount
    order.remark = command.remark
    order.version += 1
    order.updated_by = principal.id
    order.updated_at = now
    uow.session.add(order)
    uow.session.add_all([SaleOrderItem(tenant_id=uow.tenant_id, sale_order_id=order.id, line_no=index, product_id=line.product.id, unit_id=line.unit.id, product_name=line.product.name, product_barcode=line.product.barcode, unit_name=line.unit.name, quantity=line.quantity, unit_price=line.unit_price, product_amount=line.product_amount, tax_rate=line.tax_rate, tax_amount=line.tax_amount, total_amount=line.total_amount, remark=line.remark) for index, line in enumerate(calculated.lines, start=1)])
    record_action(uow=uow, resource_type="sale_order", resource_id=order.id, resource_no=order.no, action=DocumentAction.UPDATED, actor_id=principal.id, old_version=old_version, new_version=order.version, metadata={"item_count": len(calculated.lines)})
    uow.session.commit()
    uow.session.refresh(order)
    return public_order(uow, order)


@router.delete("/sale-orders/{order_id}", dependencies=[Depends(require_module_access("erp", "erp:sale-order:delete"))], status_code=204)
def delete_sale_order(order_id: uuid.UUID, uow: ErpTenantUowDep, principal: CurrentPrincipal) -> Response:
    order = get_scoped_order(order_id=order_id, uow=uow, principal=principal, lock=True)
    if order.status != DocumentStatus.DRAFT:
        raise HTTPException(status_code=409, detail="Sale order must be draft before deletion")
    items = uow.session.exec(select(SaleOrderItem).where(SaleOrderItem.sale_order_id == order.id)).all()
    if any(item.shipped_quantity > 0 or item.returned_quantity > 0 for item in items):
        raise HTTPException(status_code=409, detail="Sale order has downstream documents")
    record_action(uow=uow, resource_type="sale_order", resource_id=order.id, resource_no=order.no, action=DocumentAction.DELETED, actor_id=principal.id)
    uow.session.delete(order)
    uow.session.commit()
    return Response(status_code=204)


@router.post("/sale-orders/{order_id}/approve", dependencies=[Depends(require_module_access("erp", "erp:sale-order:approve"))], response_model=SaleOrderPublic)
def approve_sale_order(order_id: uuid.UUID, command: DocumentCommand, uow: ErpTenantUowDep, principal: CurrentPrincipal, idempotency_key: str = Header(alias="Idempotency-Key")) -> SaleOrderPublic:
    claim = command_claim(uow=uow, command_name="erp.sale-order.approve", idempotency_key=idempotency_key, principal=principal, payload=command.model_dump(mode="json"), resource_id=order_id)
    if claim.replay:
        return replay_order(uow, claim, principal)
    order = get_scoped_order(order_id=order_id, uow=uow, principal=principal, lock=True)
    if order.status != DocumentStatus.DRAFT or order.version != command.expected_version:
        raise HTTPException(status_code=409, detail="Sale order version conflict")
    order.status = DocumentStatus.APPROVED
    order.version += 1
    order.approved_by = principal.id
    order.approved_at = get_datetime_utc()
    order.updated_by = principal.id
    order.updated_at = get_datetime_utc()
    uow.session.add(order)
    enqueue_document_lifecycle_event(
        uow=uow, document=order, document_type="sale_order", action="approved"
    )
    complete_command(receipt=claim.receipt, resource_type="sale_order", resource_id=order.id, resource_version=order.version)
    uow.session.commit()
    uow.session.refresh(order)
    return public_order(uow, order)


@router.post("/sale-orders/{order_id}/reverse", dependencies=[Depends(require_module_access("erp", "erp:sale-order:reverse"))], response_model=SaleOrderPublic)
def reverse_sale_order(order_id: uuid.UUID, command: DocumentReverseCommand, uow: ErpTenantUowDep, principal: CurrentPrincipal, idempotency_key: str = Header(alias="Idempotency-Key")) -> SaleOrderPublic:
    claim = command_claim(uow=uow, command_name="erp.sale-order.reverse", idempotency_key=idempotency_key, principal=principal, payload=command.model_dump(mode="json"), resource_id=order_id)
    if claim.replay:
        return replay_order(uow, claim, principal)
    order = get_scoped_order(order_id=order_id, uow=uow, principal=principal, lock=True)
    if order.status != DocumentStatus.APPROVED or order.version != command.expected_version:
        raise HTTPException(status_code=409, detail="Sale order version conflict")
    items = uow.session.exec(select(SaleOrderItem).where(SaleOrderItem.sale_order_id == order.id)).all()
    if any(item.shipped_quantity > 0 or item.returned_quantity > 0 for item in items):
        raise HTTPException(status_code=409, detail="Sale order has downstream documents")
    old_status, old_version = str(order.status), order.version
    order.status = DocumentStatus.DRAFT
    order.version += 1
    order.reversed_by = principal.id
    order.reversed_at = get_datetime_utc()
    order.updated_by = principal.id
    order.updated_at = get_datetime_utc()
    uow.session.add(order)
    record_action(uow=uow, resource_type="sale_order", resource_id=order.id, resource_no=order.no, action=DocumentAction.REVERSED, actor_id=principal.id, old_status=old_status, new_status=str(order.status), old_version=old_version, new_version=order.version, reason=command.reason)
    enqueue_document_lifecycle_event(
        uow=uow, document=order, document_type="sale_order", action="reversed"
    )
    complete_command(receipt=claim.receipt, resource_type="sale_order", resource_id=order.id, resource_version=order.version)
    uow.session.commit()
    uow.session.refresh(order)
    return public_order(uow, order)

