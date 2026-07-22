"""Purchase order HTTP contracts."""

import uuid
from datetime import datetime
from typing import Any

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
from app.modules.erp.application.purchase_orders import (
    PurchaseOrderConflictError,
    calculate_purchase_order,
)
from app.modules.erp.application.settlement_accounts import (
    SettlementAccountUnavailableError,
    ensure_active_settlement_account,
)
from app.modules.erp.infrastructure.models import (
    DocumentAction,
    DocumentStatus,
    PurchaseOrder,
    PurchaseOrderItem,
)
from app.modules.erp.infrastructure.tenant_uow import ErpTenantUowDep
from app.modules.erp.observability import ErpDocumentCommandMetricRoute
from app.modules.erp.public_api.dto import (
    DocumentCommand,
    DocumentReverseCommand,
    PurchaseOrderCreate,
    PurchaseOrderItemPublic,
    PurchaseOrderPublic,
    PurchaseOrdersPublic,
    PurchaseOrderUpdate,
)
from app.platform.web_api import (
    CurrentPrincipal,
    CurrentTenant,
    build_owner_data_scope_filter,
    normalize_pagination,
    require_module_access,
)

router = APIRouter(
    prefix="/erp", tags=["erp-purchase"], route_class=ErpDocumentCommandMetricRoute
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
) -> PurchaseOrderPublic:
    if claim.receipt.resource_type != "purchase_order" or claim.receipt.resource_id is None:
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
        owner_id_column=PurchaseOrder.owner_id,
    )


def public_order(uow: ErpTenantUowDep, order: PurchaseOrder) -> PurchaseOrderPublic:
    items = uow.session.exec(
        select(PurchaseOrderItem)
        .where(PurchaseOrderItem.purchase_order_id == order.id)
        .order_by(PurchaseOrderItem.line_no)
    ).all()
    return PurchaseOrderPublic.model_validate(order).model_copy(
        update={"items": [PurchaseOrderItemPublic.model_validate(item) for item in items]}
    )


def fulfillment_status_filter(*, quantity_column: Any, status: str):
    """Filter orders by the aggregate processing state of their lines."""
    processed_orders = PurchaseOrder.id.in_(
        select(PurchaseOrderItem.purchase_order_id).where(quantity_column > 0)
    )
    incomplete_orders = PurchaseOrder.id.in_(
        select(PurchaseOrderItem.purchase_order_id).where(
            quantity_column < PurchaseOrderItem.quantity
        )
    )
    if status == "none":
        return ~processed_orders
    if status == "partial":
        return processed_orders & incomplete_orders
    if status == "completed":
        return ~incomplete_orders
    raise ValueError("Fulfillment status must be none, partial, or completed")


def get_scoped_order(*, order_id: uuid.UUID, uow: ErpTenantUowDep, principal: CurrentPrincipal, lock: bool = False) -> PurchaseOrder:
    statement = select(PurchaseOrder).where(PurchaseOrder.id == order_id, order_scope(uow=uow, principal=principal))
    if lock:
        statement = statement.with_for_update()
    order = uow.session.exec(statement).first()
    if order is None:
        raise HTTPException(status_code=404, detail="Purchase order not found")
    return order


@router.get("/purchase-orders", dependencies=[Depends(require_module_access("erp", "erp:purchase-order:list"))], response_model=PurchaseOrdersPublic)
def read_purchase_orders(
    uow: ErpTenantUowDep,
    principal: CurrentPrincipal,
    page: int = 1,
    page_size: int = 20,
    keyword: str | None = None,
    product_id: uuid.UUID | None = None,
    supplier_id: uuid.UUID | None = None,
    owner_id: uuid.UUID | None = None,
    status: str | None = None,
    receipt_status: str | None = None,
    remark: str | None = None,
    return_status: str | None = None,
    business_from: datetime | None = None,
    business_to: datetime | None = None,
) -> PurchaseOrdersPublic:
    page, page_size = normalize_pagination(page=page, page_size=page_size)
    try:
        filters = document_list_filters(
            model=PurchaseOrder,
            item_model=PurchaseOrderItem,
            item_document_column=PurchaseOrderItem.purchase_order_id,
            counterparty_id_column=PurchaseOrder.supplier_id,
            counterparty_name_column=PurchaseOrder.supplier_name,
            scope=order_scope(uow=uow, principal=principal),
            keyword=keyword,
            product_id=product_id,
            counterparty_id=supplier_id,
            owner_id=owner_id,
            status=status,
            remark=remark,
            business_from=business_from,
            business_to=business_to,
        )
        if receipt_status is not None:
            filters.append(
                fulfillment_status_filter(
                    quantity_column=PurchaseOrderItem.received_quantity,
                    status=receipt_status,
                )
            )
        if return_status is not None:
            filters.append(
                fulfillment_status_filter(
                    quantity_column=PurchaseOrderItem.returned_quantity,
                    status=return_status,
                )
            )
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    total = int(uow.session.exec(select(func.count()).select_from(PurchaseOrder).where(*filters)).one())
    orders = uow.session.exec(select(PurchaseOrder).where(*filters).order_by(col(PurchaseOrder.business_at).desc()).offset((page - 1) * page_size).limit(page_size)).all()
    return PurchaseOrdersPublic(items=[public_order(uow, order) for order in orders], total=total, page=page, page_size=page_size)


@router.get("/purchase-orders/{order_id}", dependencies=[Depends(require_module_access("erp", "erp:purchase-order:list"))], response_model=PurchaseOrderPublic)
def read_purchase_order(order_id: uuid.UUID, uow: ErpTenantUowDep, principal: CurrentPrincipal) -> PurchaseOrderPublic:
    return public_order(
        uow,
        get_scoped_order(order_id=order_id, uow=uow, principal=principal),
    )


@router.post("/purchase-orders", dependencies=[Depends(require_module_access("erp", "erp:purchase-order:create"))], response_model=PurchaseOrderPublic)
def create_purchase_order(command: PurchaseOrderCreate, uow: ErpTenantUowDep, principal: CurrentPrincipal, tenant: CurrentTenant, idempotency_key: str = Header(alias="Idempotency-Key")) -> PurchaseOrderPublic:
    claim = command_claim(
        uow=uow,
        command_name="erp.purchase-order.create",
        idempotency_key=idempotency_key,
        principal=principal,
        payload=command.model_dump(mode="json"),
    )
    if claim.replay:
        return replay_order(uow, claim, principal)
    try:
        calculated = calculate_purchase_order(uow=uow, command=command)
    except PurchaseOrderConflictError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    try:
        settlement_account_id = ensure_active_settlement_account(
            uow=uow, account_id=command.settlement_account_id
        )
    except SettlementAccountUnavailableError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    order = PurchaseOrder(
        tenant_id=tenant.tenant_id, no=allocate_document_no(uow=uow, prefix="CGDD"), supplier_id=calculated.supplier.id,
        supplier_name=calculated.supplier.name, settlement_account_id=settlement_account_id, business_at=resolve_business_at(uow=uow, requested_at=command.business_at), owner_id=principal.id,
        total_quantity=calculated.total_quantity, product_amount=calculated.product_amount, tax_amount=calculated.tax_amount,
        discount_rate=command.discount_rate, discount_amount=calculated.discount_amount, deposit_amount=command.deposit_amount,
        total_amount=calculated.total_amount, remark=command.remark, created_by=principal.id, updated_by=principal.id,
    )
    uow.session.add(order)
    uow.session.flush()
    uow.session.add_all([PurchaseOrderItem(tenant_id=tenant.tenant_id, purchase_order_id=order.id, line_no=index, product_id=line.product.id, unit_id=line.unit.id, product_name=line.product.name, product_barcode=line.product.barcode, unit_name=line.unit.name, quantity=line.quantity, unit_price=line.unit_price, product_amount=line.product_amount, tax_rate=line.tax_rate, tax_amount=line.tax_amount, total_amount=line.total_amount, remark=line.remark) for index, line in enumerate(calculated.lines, start=1)])
    complete_command(receipt=claim.receipt, resource_type="purchase_order", resource_id=order.id, resource_version=order.version)
    uow.session.commit()
    uow.session.refresh(order)
    return public_order(uow, order)


@router.patch("/purchase-orders/{order_id}", dependencies=[Depends(require_module_access("erp", "erp:purchase-order:update"))], response_model=PurchaseOrderPublic)
def update_purchase_order(order_id: uuid.UUID, command: PurchaseOrderUpdate, uow: ErpTenantUowDep, principal: CurrentPrincipal) -> PurchaseOrderPublic:
    order = get_scoped_order(order_id=order_id, uow=uow, principal=principal, lock=True)
    if order.status != DocumentStatus.DRAFT or order.version != command.expected_version:
        raise HTTPException(status_code=409, detail="Purchase order version conflict")
    existing_items = uow.session.exec(select(PurchaseOrderItem).where(PurchaseOrderItem.purchase_order_id == order.id)).all()
    if any(item.received_quantity > 0 or item.returned_quantity > 0 for item in existing_items):
        raise HTTPException(status_code=409, detail="Purchase order has downstream documents")
    try:
        calculated = calculate_purchase_order(uow=uow, command=command)
    except PurchaseOrderConflictError as exc:
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
    order.supplier_id = calculated.supplier.id
    order.supplier_name = calculated.supplier.name
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
    uow.session.add_all([PurchaseOrderItem(tenant_id=uow.tenant_id, purchase_order_id=order.id, line_no=index, product_id=line.product.id, unit_id=line.unit.id, product_name=line.product.name, product_barcode=line.product.barcode, unit_name=line.unit.name, quantity=line.quantity, unit_price=line.unit_price, product_amount=line.product_amount, tax_rate=line.tax_rate, tax_amount=line.tax_amount, total_amount=line.total_amount, remark=line.remark) for index, line in enumerate(calculated.lines, start=1)])
    record_action(uow=uow, resource_type="purchase_order", resource_id=order.id, resource_no=order.no, action=DocumentAction.UPDATED, actor_id=principal.id, old_version=old_version, new_version=order.version, metadata={"item_count": len(calculated.lines)})
    uow.session.commit()
    uow.session.refresh(order)
    return public_order(uow, order)


@router.delete("/purchase-orders/{order_id}", dependencies=[Depends(require_module_access("erp", "erp:purchase-order:delete"))], status_code=204)
def delete_purchase_order(order_id: uuid.UUID, uow: ErpTenantUowDep, principal: CurrentPrincipal) -> Response:
    order = get_scoped_order(order_id=order_id, uow=uow, principal=principal, lock=True)
    if order.status != DocumentStatus.DRAFT:
        raise HTTPException(status_code=409, detail="Purchase order must be draft before deletion")
    items = uow.session.exec(select(PurchaseOrderItem).where(PurchaseOrderItem.purchase_order_id == order.id)).all()
    if any(item.received_quantity > 0 or item.returned_quantity > 0 for item in items):
        raise HTTPException(status_code=409, detail="Purchase order has downstream documents")
    record_action(uow=uow, resource_type="purchase_order", resource_id=order.id, resource_no=order.no, action=DocumentAction.DELETED, actor_id=principal.id)
    uow.session.delete(order)
    uow.session.commit()
    return Response(status_code=204)


@router.post("/purchase-orders/{order_id}/approve", dependencies=[Depends(require_module_access("erp", "erp:purchase-order:approve"))], response_model=PurchaseOrderPublic)
def approve_purchase_order(order_id: uuid.UUID, command: DocumentCommand, uow: ErpTenantUowDep, principal: CurrentPrincipal, idempotency_key: str = Header(alias="Idempotency-Key")) -> PurchaseOrderPublic:
    claim = command_claim(uow=uow, command_name="erp.purchase-order.approve", idempotency_key=idempotency_key, principal=principal, payload=command.model_dump(mode="json"), resource_id=order_id)
    if claim.replay:
        return replay_order(uow, claim, principal)
    order = get_scoped_order(order_id=order_id, uow=uow, principal=principal, lock=True)
    if order.status != DocumentStatus.DRAFT or order.version != command.expected_version:
        raise HTTPException(status_code=409, detail="Purchase order version conflict")
    order.status = DocumentStatus.APPROVED
    order.version += 1
    order.approved_by = principal.id
    order.approved_at = get_datetime_utc()
    order.updated_by = principal.id
    order.updated_at = get_datetime_utc()
    uow.session.add(order)
    enqueue_document_lifecycle_event(
        uow=uow, document=order, document_type="purchase_order", action="approved"
    )
    complete_command(receipt=claim.receipt, resource_type="purchase_order", resource_id=order.id, resource_version=order.version)
    uow.session.commit()
    uow.session.refresh(order)
    return public_order(uow, order)


@router.post("/purchase-orders/{order_id}/reverse", dependencies=[Depends(require_module_access("erp", "erp:purchase-order:reverse"))], response_model=PurchaseOrderPublic)
def reverse_purchase_order(order_id: uuid.UUID, command: DocumentReverseCommand, uow: ErpTenantUowDep, principal: CurrentPrincipal, idempotency_key: str = Header(alias="Idempotency-Key")) -> PurchaseOrderPublic:
    claim = command_claim(uow=uow, command_name="erp.purchase-order.reverse", idempotency_key=idempotency_key, principal=principal, payload=command.model_dump(mode="json"), resource_id=order_id)
    if claim.replay:
        return replay_order(uow, claim, principal)
    order = get_scoped_order(order_id=order_id, uow=uow, principal=principal, lock=True)
    if order.status != DocumentStatus.APPROVED or order.version != command.expected_version:
        raise HTTPException(status_code=409, detail="Purchase order version conflict")
    items = uow.session.exec(select(PurchaseOrderItem).where(PurchaseOrderItem.purchase_order_id == order.id)).all()
    if any(item.received_quantity > 0 or item.returned_quantity > 0 for item in items):
        raise HTTPException(status_code=409, detail="Purchase order has downstream documents")
    old_status, old_version = str(order.status), order.version
    order.status = DocumentStatus.DRAFT
    order.version += 1
    order.reversed_by = principal.id
    order.reversed_at = get_datetime_utc()
    order.updated_by = principal.id
    order.updated_at = get_datetime_utc()
    uow.session.add(order)
    record_action(uow=uow, resource_type="purchase_order", resource_id=order.id, resource_no=order.no, action=DocumentAction.REVERSED, actor_id=principal.id, old_status=old_status, new_status=str(order.status), old_version=old_version, new_version=order.version, reason=command.reason)
    enqueue_document_lifecycle_event(
        uow=uow, document=order, document_type="purchase_order", action="reversed"
    )
    complete_command(receipt=claim.receipt, resource_type="purchase_order", resource_id=order.id, resource_version=order.version)
    uow.session.commit()
    uow.session.refresh(order)
    return public_order(uow, order)
