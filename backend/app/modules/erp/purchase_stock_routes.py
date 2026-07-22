"""Purchase receipt and return HTTP contracts with source-order inventory posting."""

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
from app.modules.erp.application.inventory_posting import (
    InventoryConflictError,
    InventoryEffect,
    InventoryPostingService,
)
from app.modules.erp.application.settlement_accounts import (
    SettlementAccountUnavailableError,
    ensure_active_settlement_account,
)
from app.modules.erp.application.trade_document_amounts import (
    TradeDocumentAmountError,
    calculate_trade_document_amounts,
)
from app.modules.erp.infrastructure.models import (
    DocumentAction,
    DocumentStatus,
    FinancePayment,
    FinancePaymentItem,
    PurchaseIn,
    PurchaseInItem,
    PurchaseOrder,
    PurchaseOrderItem,
    PurchaseReturn,
    PurchaseReturnItem,
    SettlementSourceType,
    StockLedger,
    StockLedgerType,
)
from app.modules.erp.infrastructure.tenant_uow import ErpTenantUowDep
from app.modules.erp.observability import ErpDocumentCommandMetricRoute
from app.modules.erp.public_api.dto import (
    DocumentCommand,
    DocumentReverseCommand,
    PurchaseInCreate,
    PurchaseInItemPublic,
    PurchaseInPublic,
    PurchaseInsPublic,
    PurchaseInUpdate,
    PurchaseReturnCreate,
    PurchaseReturnItemPublic,
    PurchaseReturnPublic,
    PurchaseReturnsPublic,
    PurchaseReturnUpdate,
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
    tags=["erp-purchase-stock"],
    route_class=ErpDocumentCommandMetricRoute,
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


def replay_document(
    uow: ErpTenantUowDep, claim: CommandReceiptClaim, principal: CurrentPrincipal
) -> PurchaseInPublic | PurchaseReturnPublic:
    if claim.receipt.resource_id is None:
        raise HTTPException(status_code=409, detail="Idempotency receipt is unavailable")
    if claim.receipt.resource_type == "purchase_in":
        document = uow.session.get(PurchaseIn, claim.receipt.resource_id)
        if document is not None:
            assert_document_scope(uow=uow, principal=principal, document=document)
            return purchase_in_public(uow, document)
    if claim.receipt.resource_type == "purchase_return":
        document = uow.session.get(PurchaseReturn, claim.receipt.resource_id)
        if document is not None:
            assert_document_scope(uow=uow, principal=principal, document=document)
            return purchase_return_public(uow, document)
    raise HTTPException(status_code=409, detail="Idempotency receipt document is unavailable")


def owner_scope(*, uow: ErpTenantUowDep, principal: CurrentPrincipal, owner_column: Any) -> Any:
    return build_owner_data_scope_filter(
        session=uow.session,
        current_principal=principal,
        tenant_id=uow.tenant_id,
        owner_id_column=owner_column,
    )


def assert_document_scope(*, uow: ErpTenantUowDep, principal: CurrentPrincipal, document: PurchaseIn | PurchaseReturn) -> None:
    model = PurchaseIn if isinstance(document, PurchaseIn) else PurchaseReturn
    allowed = uow.session.exec(
        select(model.id).where(
            model.id == document.id,
            owner_scope(uow=uow, principal=principal, owner_column=model.owner_id),
        )
    ).first()
    if allowed is None:
        raise HTTPException(status_code=403, detail="Not enough permissions")


def purchase_in_public(uow: ErpTenantUowDep, document: PurchaseIn) -> PurchaseInPublic:
    items = uow.session.exec(
        select(PurchaseInItem)
        .where(PurchaseInItem.purchase_in_id == document.id)
        .order_by(PurchaseInItem.line_no)
    ).all()
    return PurchaseInPublic.model_validate(document).model_copy(
        update={"items": [PurchaseInItemPublic.model_validate(item) for item in items]}
    )


def purchase_return_public(
    uow: ErpTenantUowDep, document: PurchaseReturn
) -> PurchaseReturnPublic:
    items = uow.session.exec(
        select(PurchaseReturnItem)
        .where(PurchaseReturnItem.purchase_return_id == document.id)
        .order_by(PurchaseReturnItem.line_no)
    ).all()
    return PurchaseReturnPublic.model_validate(document).model_copy(
        update={
            "items": [PurchaseReturnItemPublic.model_validate(item) for item in items]
        }
    )


def receipt_effects(
    document: PurchaseIn, items: list[PurchaseInItem]
) -> tuple[InventoryEffect, ...]:
    return tuple(
        InventoryEffect(
            product_id=item.product_id,
            warehouse_id=item.warehouse_id,
            delta_quantity=item.quantity,
            ledger_type=StockLedgerType.PURCHASE_IN,
            source_document_type="purchase_in",
            source_document_id=document.id,
            source_item_id=item.id,
            source_document_no=document.no,
            source_version=document.version + 1,
        )
        for item in items
    )


def return_effects(
    document: PurchaseReturn, items: list[PurchaseReturnItem]
) -> tuple[InventoryEffect, ...]:
    return tuple(
        InventoryEffect(
            product_id=item.product_id,
            warehouse_id=item.warehouse_id,
            delta_quantity=-item.quantity,
            ledger_type=StockLedgerType.PURCHASE_RETURN,
            source_document_type="purchase_return",
            source_document_id=document.id,
            source_item_id=item.id,
            source_document_no=document.no,
            source_version=document.version + 1,
        )
        for item in items
    )


def reversal_effects(
    *, document_id: uuid.UUID, document_no: str, document_type: str, version: int, ledgers: list[StockLedger]
) -> tuple[InventoryEffect, ...]:
    reversal_types = {
        StockLedgerType.PURCHASE_IN: StockLedgerType.PURCHASE_IN_REVERSAL,
        StockLedgerType.PURCHASE_RETURN: StockLedgerType.PURCHASE_RETURN_REVERSAL,
    }
    return tuple(
        InventoryEffect(
            product_id=ledger.product_id,
            warehouse_id=ledger.warehouse_id,
            delta_quantity=-ledger.delta_quantity,
            ledger_type=reversal_types[ledger.ledger_type],
            source_document_type=document_type,
            source_document_id=document_id,
            source_item_id=ledger.source_item_id,
            source_document_no=document_no,
            source_version=version + 1,
            reversal_of_id=ledger.id,
        )
        for ledger in ledgers
    )


def lock_purchase_order_items(
    *, uow: ErpTenantUowDep, item_ids: set[uuid.UUID]
) -> dict[uuid.UUID, PurchaseOrderItem]:
    items = uow.session.exec(
        select(PurchaseOrderItem)
        .where(PurchaseOrderItem.id.in_(item_ids))
        .order_by(col(PurchaseOrderItem.id))
        .with_for_update()
    ).all()
    if len(items) != len(item_ids):
        raise HTTPException(status_code=409, detail="Purchase order line is unavailable")
    return {item.id: item for item in items}


def set_approved(*, document: PurchaseIn | PurchaseReturn, principal: CurrentPrincipal) -> None:
    document.status = DocumentStatus.APPROVED
    document.version += 1
    document.approved_by = principal.id
    document.approved_at = get_datetime_utc()
    document.updated_by = principal.id
    document.updated_at = get_datetime_utc()


def set_reversed(*, document: PurchaseIn | PurchaseReturn, principal: CurrentPrincipal) -> None:
    document.status = DocumentStatus.DRAFT
    document.version += 1
    document.reversed_by = principal.id
    document.reversed_at = get_datetime_utc()
    document.updated_by = principal.id
    document.updated_at = get_datetime_utc()


def has_approved_payment(*, uow: ErpTenantUowDep, source_type: SettlementSourceType, source_document_id: uuid.UUID) -> bool:
    return uow.session.exec(
        select(FinancePaymentItem.id)
        .join(FinancePayment, FinancePayment.id == FinancePaymentItem.finance_payment_id)
        .where(
            FinancePaymentItem.source_type == source_type,
            FinancePaymentItem.source_document_id == source_document_id,
            FinancePayment.status == DocumentStatus.APPROVED,
        )
    ).first() is not None


@router.get(
    "/purchase-ins",
    dependencies=[Depends(require_module_access("erp", "erp:purchase-in:list"))],
    response_model=PurchaseInsPublic,
)
def read_purchase_ins(
    uow: ErpTenantUowDep, principal: CurrentPrincipal, page: int = 1, page_size: int = 20,
    keyword: str | None = None, product_id: uuid.UUID | None = None, supplier_id: uuid.UUID | None = None,
    owner_id: uuid.UUID | None = None, status: str | None = None, remark: str | None = None,
    business_from: datetime | None = None, business_to: datetime | None = None,
) -> PurchaseInsPublic:
    page, page_size = normalize_pagination(page=page, page_size=page_size)
    try:
        filters = document_list_filters(model=PurchaseIn, item_model=PurchaseInItem, item_document_column=PurchaseInItem.purchase_in_id, counterparty_id_column=PurchaseIn.supplier_id, counterparty_name_column=PurchaseIn.supplier_name, scope=owner_scope(uow=uow, principal=principal, owner_column=PurchaseIn.owner_id), keyword=keyword, product_id=product_id, counterparty_id=supplier_id, owner_id=owner_id, status=status, remark=remark, business_from=business_from, business_to=business_to)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    total = int(uow.session.exec(select(func.count()).select_from(PurchaseIn).where(*filters)).one())
    documents = uow.session.exec(
        select(PurchaseIn)
        .where(*filters)
        .order_by(col(PurchaseIn.business_at).desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
    ).all()
    return PurchaseInsPublic(
        items=[purchase_in_public(uow, document) for document in documents],
        total=total,
        page=page,
        page_size=page_size,
    )


@router.get(
    "/purchase-ins/{document_id}",
    dependencies=[Depends(require_module_access("erp", "erp:purchase-in:list"))],
    response_model=PurchaseInPublic,
)
def read_purchase_in(
    document_id: uuid.UUID, uow: ErpTenantUowDep, principal: CurrentPrincipal
) -> PurchaseInPublic:
    document = uow.session.get(PurchaseIn, document_id)
    if document is None:
        raise HTTPException(status_code=404, detail="Purchase receipt not found")
    assert_document_scope(uow=uow, principal=principal, document=document)
    return purchase_in_public(uow, document)


@router.post(
    "/purchase-ins",
    dependencies=[Depends(require_module_access("erp", "erp:purchase-in:create"))],
    response_model=PurchaseInPublic,
)
def create_purchase_in(
    command: PurchaseInCreate,
    uow: ErpTenantUowDep,
    principal: CurrentPrincipal,
    tenant: CurrentTenant,
    idempotency_key: str = Header(alias="Idempotency-Key"),
) -> PurchaseInPublic:
    claim = command_claim(uow=uow, command_name="erp.purchase-in.create", idempotency_key=idempotency_key, principal=principal, payload=command.model_dump(mode="json"))
    if claim.replay:
        return replay_document(uow, claim, principal)
    order = uow.session.exec(
        select(PurchaseOrder).where(
            PurchaseOrder.id == command.purchase_order_id,
            owner_scope(uow=uow, principal=principal, owner_column=PurchaseOrder.owner_id),
        )
    ).first()
    if order is None:
        raise HTTPException(status_code=404, detail="Purchase order not found")
    if order.status != DocumentStatus.APPROVED:
        raise HTTPException(status_code=409, detail="Purchase order must be approved")
    line_ids = [line.purchase_order_item_id for line in command.items]
    if len(set(line_ids)) != len(line_ids):
        raise HTTPException(status_code=422, detail="Purchase receipt cannot repeat an order line")
    source_items = {
        item.id: item
        for item in uow.session.exec(
            select(PurchaseOrderItem).where(
                PurchaseOrderItem.purchase_order_id == order.id,
                PurchaseOrderItem.id.in_(line_ids),
            )
        ).all()
    }
    if len(source_items) != len(line_ids):
        raise HTTPException(status_code=409, detail="Purchase order line is unavailable")
    for line in command.items:
        source = source_items[line.purchase_order_item_id]
        if line.quantity > source.quantity - source.received_quantity:
            raise HTTPException(status_code=409, detail="Receipt quantity exceeds remaining order quantity")
    try:
        amounts = calculate_trade_document_amounts(
            lines=(
                (line.quantity, source_items[line.purchase_order_item_id].unit_price, source_items[line.purchase_order_item_id].tax_rate)
                for line in command.items
            ),
            discount_rate=command.discount_rate,
            discount_amount=command.discount_amount,
            adjustment=command.other_fee,
            adjustment_sign=1,
        )
        settlement_account_id = ensure_active_settlement_account(
            uow=uow, account_id=command.settlement_account_id
        )
    except (TradeDocumentAmountError, SettlementAccountUnavailableError) as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc

    document = PurchaseIn(
        tenant_id=tenant.tenant_id,
        no=allocate_document_no(uow=uow, prefix="CGRK"),
        purchase_order_id=order.id,
        purchase_order_no=order.no,
        supplier_id=order.supplier_id,
        supplier_name=order.supplier_name,
        settlement_account_id=settlement_account_id or order.settlement_account_id,
        business_at=resolve_business_at(uow=uow, requested_at=command.business_at),
        owner_id=principal.id,
        total_quantity=amounts.total_quantity,
        product_amount=amounts.product_amount,
        tax_amount=amounts.tax_amount,
        discount_rate=command.discount_rate,
        discount_amount=amounts.discount_amount,
        other_fee=command.other_fee,
        total_amount=amounts.total_amount,
        remark=command.remark,
        created_by=principal.id,
        updated_by=principal.id,
    )
    uow.session.add(document)
    uow.session.flush()
    uow.session.add_all(
        [
            PurchaseInItem(
                tenant_id=tenant.tenant_id,
                purchase_in_id=document.id,
                purchase_order_item_id=line.purchase_order_item_id,
                line_no=index,
                product_id=source_items[line.purchase_order_item_id].product_id,
                warehouse_id=line.warehouse_id,
                product_name=source_items[line.purchase_order_item_id].product_name,
                unit_name=source_items[line.purchase_order_item_id].unit_name,
                quantity=amount.quantity,
                reference_price=amount.reference_price,
                tax_rate=amount.tax_rate,
                product_amount=amount.product_amount,
                tax_amount=amount.tax_amount,
                total_amount=amount.total_amount,
                remark=line.remark,
            )
            for index, (line, amount) in enumerate(zip(command.items, amounts.lines, strict=True), start=1)
        ]
    )
    record_action(uow=uow, resource_type="purchase_in", resource_id=document.id, resource_no=document.no, action=DocumentAction.CREATED, actor_id=principal.id, new_status=str(document.status), new_version=document.version, metadata={"item_count": len(command.items)})
    complete_command(receipt=claim.receipt, resource_type="purchase_in", resource_id=document.id, resource_version=document.version)
    uow.session.commit()
    uow.session.refresh(document)
    return purchase_in_public(uow, document)


@router.patch("/purchase-ins/{document_id}", dependencies=[Depends(require_module_access("erp", "erp:purchase-in:update"))], response_model=PurchaseInPublic)
def update_purchase_in(document_id: uuid.UUID, command: PurchaseInUpdate, uow: ErpTenantUowDep, principal: CurrentPrincipal) -> PurchaseInPublic:
    document = uow.session.exec(select(PurchaseIn).where(PurchaseIn.id == document_id).with_for_update()).first()
    if document is None:
        raise HTTPException(status_code=404, detail="Purchase receipt not found")
    assert_document_scope(uow=uow, principal=principal, document=document)
    if document.status != DocumentStatus.DRAFT or document.version != command.expected_version:
        raise HTTPException(status_code=409, detail="Purchase receipt version conflict")
    if command.purchase_order_id != document.purchase_order_id:
        raise HTTPException(status_code=409, detail="Purchase receipt source order cannot change")
    order = uow.session.exec(select(PurchaseOrder).where(PurchaseOrder.id == document.purchase_order_id).with_for_update()).first()
    if order is None or order.status != DocumentStatus.APPROVED:
        raise HTTPException(status_code=409, detail="Purchase order must be approved")
    line_ids = [line.purchase_order_item_id for line in command.items]
    if len(set(line_ids)) != len(line_ids):
        raise HTTPException(status_code=422, detail="Purchase receipt cannot repeat an order line")
    source_items = lock_purchase_order_items(uow=uow, item_ids=set(line_ids))
    if any(item.purchase_order_id != order.id for item in source_items.values()):
        raise HTTPException(status_code=409, detail="Purchase order line is unavailable")
    if any(line.quantity > source_items[line.purchase_order_item_id].quantity - source_items[line.purchase_order_item_id].received_quantity for line in command.items):
        raise HTTPException(status_code=409, detail="Receipt quantity exceeds remaining order quantity")
    try:
        amounts = calculate_trade_document_amounts(lines=((line.quantity, source_items[line.purchase_order_item_id].unit_price, source_items[line.purchase_order_item_id].tax_rate) for line in command.items), discount_rate=command.discount_rate, discount_amount=command.discount_amount, adjustment=command.other_fee, adjustment_sign=1)
        settlement_account_id = ensure_active_settlement_account(uow=uow, account_id=command.settlement_account_id)
    except (TradeDocumentAmountError, SettlementAccountUnavailableError) as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    old_version = document.version
    for item in uow.session.exec(select(PurchaseInItem).where(PurchaseInItem.purchase_in_id == document.id)).all():
        uow.session.delete(item)
    uow.session.flush()
    document.settlement_account_id = settlement_account_id or order.settlement_account_id
    document.business_at = resolve_business_at(uow=uow, requested_at=command.business_at) if command.business_at is not None else document.business_at
    document.total_quantity, document.product_amount, document.tax_amount, document.discount_rate, document.discount_amount, document.other_fee, document.total_amount, document.remark = amounts.total_quantity, amounts.product_amount, amounts.tax_amount, command.discount_rate, amounts.discount_amount, command.other_fee, amounts.total_amount, command.remark
    document.version += 1
    document.updated_by, document.updated_at = principal.id, get_datetime_utc()
    uow.session.add(document)
    uow.session.add_all([PurchaseInItem(tenant_id=uow.tenant_id, purchase_in_id=document.id, purchase_order_item_id=line.purchase_order_item_id, line_no=index, product_id=source_items[line.purchase_order_item_id].product_id, warehouse_id=line.warehouse_id, product_name=source_items[line.purchase_order_item_id].product_name, unit_name=source_items[line.purchase_order_item_id].unit_name, quantity=amount.quantity, reference_price=amount.reference_price, tax_rate=amount.tax_rate, product_amount=amount.product_amount, tax_amount=amount.tax_amount, total_amount=amount.total_amount, remark=line.remark) for index, (line, amount) in enumerate(zip(command.items, amounts.lines, strict=True), start=1)])
    record_action(uow=uow, resource_type="purchase_in", resource_id=document.id, resource_no=document.no, action=DocumentAction.UPDATED, actor_id=principal.id, old_version=old_version, new_version=document.version, metadata={"item_count": len(command.items)})
    uow.session.commit()
    uow.session.refresh(document)
    return purchase_in_public(uow, document)


@router.delete("/purchase-ins/{document_id}", dependencies=[Depends(require_module_access("erp", "erp:purchase-in:delete"))], status_code=204)
def delete_purchase_in(document_id: uuid.UUID, uow: ErpTenantUowDep, principal: CurrentPrincipal) -> Response:
    document = uow.session.exec(select(PurchaseIn).where(PurchaseIn.id == document_id).with_for_update()).first()
    if document is None:
        raise HTTPException(status_code=404, detail="Purchase receipt not found")
    assert_document_scope(uow=uow, principal=principal, document=document)
    if document.status != DocumentStatus.DRAFT:
        raise HTTPException(status_code=409, detail="Purchase receipt must be draft before deletion")
    record_action(uow=uow, resource_type="purchase_in", resource_id=document.id, resource_no=document.no, action=DocumentAction.DELETED, actor_id=principal.id, old_status=str(document.status), old_version=document.version)
    uow.session.delete(document)
    uow.session.commit()
    return Response(status_code=204)


@router.post(
    "/purchase-ins/{document_id}/approve",
    dependencies=[Depends(require_module_access("erp", "erp:purchase-in:approve"))],
    response_model=PurchaseInPublic,
)
def approve_purchase_in(
    document_id: uuid.UUID, command: DocumentCommand, uow: ErpTenantUowDep, principal: CurrentPrincipal, idempotency_key: str = Header(alias="Idempotency-Key")
) -> PurchaseInPublic:
    claim = command_claim(uow=uow, command_name="erp.purchase-in.approve", idempotency_key=idempotency_key, principal=principal, payload=command.model_dump(mode="json"), resource_id=document_id)
    if claim.replay:
        return replay_document(uow, claim, principal)
    document = uow.session.exec(select(PurchaseIn).where(PurchaseIn.id == document_id).with_for_update()).first()
    if document is None:
        raise HTTPException(status_code=404, detail="Purchase receipt not found")
    assert_document_scope(uow=uow, principal=principal, document=document)
    if document.status != DocumentStatus.DRAFT or document.version != command.expected_version:
        raise HTTPException(status_code=409, detail="Purchase receipt version conflict")
    order = uow.session.exec(select(PurchaseOrder).where(PurchaseOrder.id == document.purchase_order_id).with_for_update()).first()
    if order is None or order.status != DocumentStatus.APPROVED:
        raise HTTPException(status_code=409, detail="Purchase order must be approved")
    items = uow.session.exec(select(PurchaseInItem).where(PurchaseInItem.purchase_in_id == document.id).order_by(PurchaseInItem.line_no)).all()
    order_items = lock_purchase_order_items(uow=uow, item_ids={item.purchase_order_item_id for item in items})
    for item in items:
        source = order_items[item.purchase_order_item_id]
        if source.purchase_order_id != order.id or item.quantity > source.quantity - source.received_quantity:
            raise HTTPException(status_code=409, detail="Receipt quantity exceeds remaining order quantity")
    try:
        InventoryPostingService(uow).post(effects=receipt_effects(document, items), operator_id=principal.id)
    except InventoryConflictError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    for item in items:
        source = order_items[item.purchase_order_item_id]
        source.received_quantity += item.quantity
        uow.session.add(source)
    old_status, old_version = str(document.status), document.version
    set_approved(document=document, principal=principal)
    uow.session.add(document)
    enqueue_document_lifecycle_event(
        uow=uow, document=document, document_type="purchase_in", action="approved"
    )
    record_action(uow=uow, resource_type="purchase_in", resource_id=document.id, resource_no=document.no, action=DocumentAction.APPROVED, actor_id=principal.id, old_status=old_status, new_status=str(document.status), old_version=old_version, new_version=document.version)
    complete_command(receipt=claim.receipt, resource_type="purchase_in", resource_id=document.id, resource_version=document.version)
    uow.session.commit()
    uow.session.refresh(document)
    return purchase_in_public(uow, document)


@router.post(
    "/purchase-ins/{document_id}/reverse",
    dependencies=[Depends(require_module_access("erp", "erp:purchase-in:reverse"))],
    response_model=PurchaseInPublic,
)
def reverse_purchase_in(
    document_id: uuid.UUID, command: DocumentReverseCommand, uow: ErpTenantUowDep, principal: CurrentPrincipal, idempotency_key: str = Header(alias="Idempotency-Key")
) -> PurchaseInPublic:
    claim = command_claim(uow=uow, command_name="erp.purchase-in.reverse", idempotency_key=idempotency_key, principal=principal, payload=command.model_dump(mode="json"), resource_id=document_id)
    if claim.replay:
        return replay_document(uow, claim, principal)
    document = uow.session.exec(select(PurchaseIn).where(PurchaseIn.id == document_id).with_for_update()).first()
    if document is None:
        raise HTTPException(status_code=404, detail="Purchase receipt not found")
    assert_document_scope(uow=uow, principal=principal, document=document)
    if document.status != DocumentStatus.APPROVED or document.version != command.expected_version:
        raise HTTPException(status_code=409, detail="Purchase receipt version conflict")
    items = uow.session.exec(select(PurchaseInItem).where(PurchaseInItem.purchase_in_id == document.id).order_by(PurchaseInItem.line_no).with_for_update()).all()
    if any(item.returned_quantity > 0 for item in items):
        raise HTTPException(status_code=409, detail="Purchase receipt has downstream return documents")
    if has_approved_payment(uow=uow, source_type=SettlementSourceType.PURCHASE_IN, source_document_id=document.id):
        raise HTTPException(status_code=409, detail="Purchase receipt has approved settlement documents")
    ledgers = uow.session.exec(
        select(StockLedger).where(
            StockLedger.source_document_type == "purchase_in",
            StockLedger.source_document_id == document.id,
            StockLedger.source_version == document.version,
            StockLedger.ledger_type == StockLedgerType.PURCHASE_IN,
            StockLedger.reversal_of_id.is_(None),
        )
    ).all()
    if len(ledgers) != len(items):
        raise HTTPException(status_code=409, detail="Purchase receipt has no reversible posting")
    order = uow.session.exec(select(PurchaseOrder).where(PurchaseOrder.id == document.purchase_order_id).with_for_update()).first()
    if order is None:
        raise HTTPException(status_code=409, detail="Purchase order is unavailable")
    order_items = lock_purchase_order_items(uow=uow, item_ids={item.purchase_order_item_id for item in items})
    if any(order_items[item.purchase_order_item_id].received_quantity < item.quantity for item in items):
        raise HTTPException(status_code=409, detail="Purchase order receipt quantity is inconsistent")
    try:
        InventoryPostingService(uow).post(
            effects=reversal_effects(document_id=document.id, document_no=document.no, document_type="purchase_in", version=document.version, ledgers=ledgers),
            operator_id=principal.id,
            require_active_references=False,
        )
    except InventoryConflictError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    for item in items:
        source = order_items[item.purchase_order_item_id]
        source.received_quantity -= item.quantity
        uow.session.add(source)
    old_status, old_version = str(document.status), document.version
    set_reversed(document=document, principal=principal)
    uow.session.add(document)
    enqueue_document_lifecycle_event(
        uow=uow, document=document, document_type="purchase_in", action="reversed"
    )
    record_action(uow=uow, resource_type="purchase_in", resource_id=document.id, resource_no=document.no, action=DocumentAction.REVERSED, actor_id=principal.id, old_status=old_status, new_status=str(document.status), old_version=old_version, new_version=document.version, reason=command.reason)
    complete_command(receipt=claim.receipt, resource_type="purchase_in", resource_id=document.id, resource_version=document.version)
    uow.session.commit()
    uow.session.refresh(document)
    return purchase_in_public(uow, document)


@router.get(
    "/purchase-returns",
    dependencies=[Depends(require_module_access("erp", "erp:purchase-return:list"))],
    response_model=PurchaseReturnsPublic,
)
def read_purchase_returns(
    uow: ErpTenantUowDep, principal: CurrentPrincipal, page: int = 1, page_size: int = 20,
    keyword: str | None = None, product_id: uuid.UUID | None = None, supplier_id: uuid.UUID | None = None,
    owner_id: uuid.UUID | None = None, status: str | None = None, remark: str | None = None,
    business_from: datetime | None = None, business_to: datetime | None = None,
) -> PurchaseReturnsPublic:
    page, page_size = normalize_pagination(page=page, page_size=page_size)
    try:
        filters = document_list_filters(model=PurchaseReturn, item_model=PurchaseReturnItem, item_document_column=PurchaseReturnItem.purchase_return_id, counterparty_id_column=PurchaseReturn.supplier_id, counterparty_name_column=PurchaseReturn.supplier_name, scope=owner_scope(uow=uow, principal=principal, owner_column=PurchaseReturn.owner_id), keyword=keyword, product_id=product_id, counterparty_id=supplier_id, owner_id=owner_id, status=status, remark=remark, business_from=business_from, business_to=business_to)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    total = int(uow.session.exec(select(func.count()).select_from(PurchaseReturn).where(*filters)).one())
    documents = uow.session.exec(
        select(PurchaseReturn)
        .where(*filters)
        .order_by(col(PurchaseReturn.business_at).desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
    ).all()
    return PurchaseReturnsPublic(
        items=[purchase_return_public(uow, document) for document in documents],
        total=total,
        page=page,
        page_size=page_size,
    )


@router.get(
    "/purchase-returns/{document_id}",
    dependencies=[Depends(require_module_access("erp", "erp:purchase-return:list"))],
    response_model=PurchaseReturnPublic,
)
def read_purchase_return(
    document_id: uuid.UUID, uow: ErpTenantUowDep, principal: CurrentPrincipal
) -> PurchaseReturnPublic:
    document = uow.session.get(PurchaseReturn, document_id)
    if document is None:
        raise HTTPException(status_code=404, detail="Purchase return not found")
    assert_document_scope(uow=uow, principal=principal, document=document)
    return purchase_return_public(uow, document)


@router.post(
    "/purchase-returns",
    dependencies=[Depends(require_module_access("erp", "erp:purchase-return:create"))],
    response_model=PurchaseReturnPublic,
)
def create_purchase_return(
    command: PurchaseReturnCreate,
    uow: ErpTenantUowDep,
    principal: CurrentPrincipal,
    tenant: CurrentTenant,
    idempotency_key: str = Header(alias="Idempotency-Key"),
) -> PurchaseReturnPublic:
    claim = command_claim(uow=uow, command_name="erp.purchase-return.create", idempotency_key=idempotency_key, principal=principal, payload=command.model_dump(mode="json"))
    if claim.replay:
        return replay_document(uow, claim, principal)
    receipt = uow.session.exec(
        select(PurchaseIn).where(
            PurchaseIn.id == command.purchase_in_id,
            owner_scope(uow=uow, principal=principal, owner_column=PurchaseIn.owner_id),
        )
    ).first()
    if receipt is None:
        raise HTTPException(status_code=404, detail="Purchase receipt not found")
    if receipt.status != DocumentStatus.APPROVED:
        raise HTTPException(status_code=409, detail="Purchase receipt must be approved")
    line_ids = [line.purchase_in_item_id for line in command.items]
    if len(set(line_ids)) != len(line_ids):
        raise HTTPException(status_code=422, detail="Purchase return cannot repeat a receipt line")
    source_items = {
        item.id: item
        for item in uow.session.exec(
            select(PurchaseInItem).where(
                PurchaseInItem.purchase_in_id == receipt.id,
                PurchaseInItem.id.in_(line_ids),
            )
        ).all()
    }
    if len(source_items) != len(line_ids):
        raise HTTPException(status_code=409, detail="Purchase receipt line is unavailable")
    for line in command.items:
        source = source_items[line.purchase_in_item_id]
        if line.quantity > source.quantity - source.returned_quantity:
            raise HTTPException(status_code=409, detail="Return quantity exceeds receipt quantity")
    try:
        amounts = calculate_trade_document_amounts(
            lines=(
                (line.quantity, source_items[line.purchase_in_item_id].reference_price, source_items[line.purchase_in_item_id].tax_rate)
                for line in command.items
            ),
            discount_rate=command.discount_rate,
            discount_amount=command.discount_amount,
            adjustment=command.other_fee,
            adjustment_sign=1,
        )
        settlement_account_id = ensure_active_settlement_account(
            uow=uow, account_id=command.settlement_account_id
        )
    except (TradeDocumentAmountError, SettlementAccountUnavailableError) as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    document = PurchaseReturn(
        tenant_id=tenant.tenant_id,
        no=allocate_document_no(uow=uow, prefix="CGTH"),
        purchase_in_id=receipt.id,
        purchase_in_no=receipt.no,
        purchase_order_id=receipt.purchase_order_id,
        supplier_id=receipt.supplier_id,
        supplier_name=receipt.supplier_name,
        settlement_account_id=settlement_account_id or receipt.settlement_account_id,
        business_at=resolve_business_at(uow=uow, requested_at=command.business_at),
        owner_id=principal.id,
        total_quantity=amounts.total_quantity,
        product_amount=amounts.product_amount,
        tax_amount=amounts.tax_amount,
        discount_rate=command.discount_rate,
        discount_amount=amounts.discount_amount,
        other_fee=command.other_fee,
        total_amount=amounts.total_amount,
        remark=command.remark,
        created_by=principal.id,
        updated_by=principal.id,
    )
    uow.session.add(document)
    uow.session.flush()
    uow.session.add_all(
        [
            PurchaseReturnItem(
                tenant_id=tenant.tenant_id,
                purchase_return_id=document.id,
                purchase_in_item_id=line.purchase_in_item_id,
                purchase_order_item_id=source_items[line.purchase_in_item_id].purchase_order_item_id,
                line_no=index,
                product_id=source_items[line.purchase_in_item_id].product_id,
                warehouse_id=source_items[line.purchase_in_item_id].warehouse_id,
                product_name=source_items[line.purchase_in_item_id].product_name,
                unit_name=source_items[line.purchase_in_item_id].unit_name,
                quantity=amount.quantity,
                reference_price=amount.reference_price,
                tax_rate=amount.tax_rate,
                product_amount=amount.product_amount,
                tax_amount=amount.tax_amount,
                total_amount=amount.total_amount,
                remark=line.remark,
            )
            for index, (line, amount) in enumerate(zip(command.items, amounts.lines, strict=True), start=1)
        ]
    )
    record_action(uow=uow, resource_type="purchase_return", resource_id=document.id, resource_no=document.no, action=DocumentAction.CREATED, actor_id=principal.id, new_status=str(document.status), new_version=document.version, metadata={"item_count": len(command.items)})
    complete_command(receipt=claim.receipt, resource_type="purchase_return", resource_id=document.id, resource_version=document.version)
    uow.session.commit()
    uow.session.refresh(document)
    return purchase_return_public(uow, document)


@router.patch("/purchase-returns/{document_id}", dependencies=[Depends(require_module_access("erp", "erp:purchase-return:update"))], response_model=PurchaseReturnPublic)
def update_purchase_return(document_id: uuid.UUID, command: PurchaseReturnUpdate, uow: ErpTenantUowDep, principal: CurrentPrincipal) -> PurchaseReturnPublic:
    document = uow.session.exec(select(PurchaseReturn).where(PurchaseReturn.id == document_id).with_for_update()).first()
    if document is None:
        raise HTTPException(status_code=404, detail="Purchase return not found")
    assert_document_scope(uow=uow, principal=principal, document=document)
    if document.status != DocumentStatus.DRAFT or document.version != command.expected_version:
        raise HTTPException(status_code=409, detail="Purchase return version conflict")
    if command.purchase_in_id != document.purchase_in_id:
        raise HTTPException(status_code=409, detail="Purchase return source receipt cannot change")
    receipt = uow.session.exec(select(PurchaseIn).where(PurchaseIn.id == document.purchase_in_id).with_for_update()).first()
    if receipt is None or receipt.status != DocumentStatus.APPROVED:
        raise HTTPException(status_code=409, detail="Purchase receipt must be approved")
    line_ids = [line.purchase_in_item_id for line in command.items]
    if len(set(line_ids)) != len(line_ids):
        raise HTTPException(status_code=422, detail="Purchase return cannot repeat a receipt line")
    source_items = {item.id: item for item in uow.session.exec(select(PurchaseInItem).where(PurchaseInItem.purchase_in_id == receipt.id, PurchaseInItem.id.in_(line_ids)).with_for_update()).all()}
    if len(source_items) != len(line_ids) or any(line.quantity > source_items[line.purchase_in_item_id].quantity - source_items[line.purchase_in_item_id].returned_quantity for line in command.items):
        raise HTTPException(status_code=409, detail="Return quantity exceeds receipt quantity")
    try:
        amounts = calculate_trade_document_amounts(lines=((line.quantity, source_items[line.purchase_in_item_id].reference_price, source_items[line.purchase_in_item_id].tax_rate) for line in command.items), discount_rate=command.discount_rate, discount_amount=command.discount_amount, adjustment=command.other_fee, adjustment_sign=1)
        settlement_account_id = ensure_active_settlement_account(uow=uow, account_id=command.settlement_account_id)
    except (TradeDocumentAmountError, SettlementAccountUnavailableError) as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    old_version = document.version
    for item in uow.session.exec(select(PurchaseReturnItem).where(PurchaseReturnItem.purchase_return_id == document.id)).all():
        uow.session.delete(item)
    uow.session.flush()
    document.settlement_account_id = settlement_account_id or receipt.settlement_account_id
    document.business_at = resolve_business_at(uow=uow, requested_at=command.business_at) if command.business_at is not None else document.business_at
    document.total_quantity, document.product_amount, document.tax_amount, document.discount_rate, document.discount_amount, document.other_fee, document.total_amount, document.remark = amounts.total_quantity, amounts.product_amount, amounts.tax_amount, command.discount_rate, amounts.discount_amount, command.other_fee, amounts.total_amount, command.remark
    document.version += 1
    document.updated_by, document.updated_at = principal.id, get_datetime_utc()
    uow.session.add(document)
    uow.session.add_all([PurchaseReturnItem(tenant_id=uow.tenant_id, purchase_return_id=document.id, purchase_in_item_id=line.purchase_in_item_id, purchase_order_item_id=source_items[line.purchase_in_item_id].purchase_order_item_id, line_no=index, product_id=source_items[line.purchase_in_item_id].product_id, warehouse_id=source_items[line.purchase_in_item_id].warehouse_id, product_name=source_items[line.purchase_in_item_id].product_name, unit_name=source_items[line.purchase_in_item_id].unit_name, quantity=amount.quantity, reference_price=amount.reference_price, tax_rate=amount.tax_rate, product_amount=amount.product_amount, tax_amount=amount.tax_amount, total_amount=amount.total_amount, remark=line.remark) for index, (line, amount) in enumerate(zip(command.items, amounts.lines, strict=True), start=1)])
    record_action(uow=uow, resource_type="purchase_return", resource_id=document.id, resource_no=document.no, action=DocumentAction.UPDATED, actor_id=principal.id, old_version=old_version, new_version=document.version, metadata={"item_count": len(command.items)})
    uow.session.commit()
    uow.session.refresh(document)
    return purchase_return_public(uow, document)


@router.delete("/purchase-returns/{document_id}", dependencies=[Depends(require_module_access("erp", "erp:purchase-return:delete"))], status_code=204)
def delete_purchase_return(document_id: uuid.UUID, uow: ErpTenantUowDep, principal: CurrentPrincipal) -> Response:
    document = uow.session.exec(select(PurchaseReturn).where(PurchaseReturn.id == document_id).with_for_update()).first()
    if document is None:
        raise HTTPException(status_code=404, detail="Purchase return not found")
    assert_document_scope(uow=uow, principal=principal, document=document)
    if document.status != DocumentStatus.DRAFT:
        raise HTTPException(status_code=409, detail="Purchase return must be draft before deletion")
    record_action(uow=uow, resource_type="purchase_return", resource_id=document.id, resource_no=document.no, action=DocumentAction.DELETED, actor_id=principal.id, old_status=str(document.status), old_version=document.version)
    uow.session.delete(document)
    uow.session.commit()
    return Response(status_code=204)


@router.post(
    "/purchase-returns/{document_id}/approve",
    dependencies=[Depends(require_module_access("erp", "erp:purchase-return:approve"))],
    response_model=PurchaseReturnPublic,
)
def approve_purchase_return(
    document_id: uuid.UUID, command: DocumentCommand, uow: ErpTenantUowDep, principal: CurrentPrincipal, idempotency_key: str = Header(alias="Idempotency-Key")
) -> PurchaseReturnPublic:
    claim = command_claim(uow=uow, command_name="erp.purchase-return.approve", idempotency_key=idempotency_key, principal=principal, payload=command.model_dump(mode="json"), resource_id=document_id)
    if claim.replay:
        return replay_document(uow, claim, principal)
    document = uow.session.exec(select(PurchaseReturn).where(PurchaseReturn.id == document_id).with_for_update()).first()
    if document is None:
        raise HTTPException(status_code=404, detail="Purchase return not found")
    assert_document_scope(uow=uow, principal=principal, document=document)
    if document.status != DocumentStatus.DRAFT or document.version != command.expected_version:
        raise HTTPException(status_code=409, detail="Purchase return version conflict")
    receipt = uow.session.exec(select(PurchaseIn).where(PurchaseIn.id == document.purchase_in_id).with_for_update()).first()
    order = uow.session.exec(select(PurchaseOrder).where(PurchaseOrder.id == document.purchase_order_id).with_for_update()).first()
    if receipt is None or receipt.status != DocumentStatus.APPROVED or order is None:
        raise HTTPException(status_code=409, detail="Purchase return source is unavailable")
    items = uow.session.exec(select(PurchaseReturnItem).where(PurchaseReturnItem.purchase_return_id == document.id).order_by(PurchaseReturnItem.line_no)).all()
    receipt_items = uow.session.exec(
        select(PurchaseInItem)
        .where(PurchaseInItem.id.in_({item.purchase_in_item_id for item in items}))
        .order_by(col(PurchaseInItem.id))
        .with_for_update()
    ).all()
    receipt_items_by_id = {item.id: item for item in receipt_items}
    if len(receipt_items_by_id) != len(items):
        raise HTTPException(status_code=409, detail="Purchase receipt line is unavailable")
    order_items = lock_purchase_order_items(uow=uow, item_ids={item.purchase_order_item_id for item in items})
    for item in items:
        receipt_item = receipt_items_by_id[item.purchase_in_item_id]
        order_item = order_items[item.purchase_order_item_id]
        if (
            receipt_item.purchase_in_id != receipt.id
            or receipt_item.purchase_order_item_id != order_item.id
            or item.quantity > receipt_item.quantity - receipt_item.returned_quantity
            or item.quantity > order_item.received_quantity - order_item.returned_quantity
        ):
            raise HTTPException(status_code=409, detail="Return quantity exceeds available received quantity")
    try:
        InventoryPostingService(uow).post(effects=return_effects(document, items), operator_id=principal.id)
    except InventoryConflictError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    for item in items:
        receipt_items_by_id[item.purchase_in_item_id].returned_quantity += item.quantity
        order_items[item.purchase_order_item_id].returned_quantity += item.quantity
        uow.session.add(receipt_items_by_id[item.purchase_in_item_id])
        uow.session.add(order_items[item.purchase_order_item_id])
    old_status, old_version = str(document.status), document.version
    set_approved(document=document, principal=principal)
    uow.session.add(document)
    enqueue_document_lifecycle_event(
        uow=uow, document=document, document_type="purchase_return", action="approved"
    )
    record_action(uow=uow, resource_type="purchase_return", resource_id=document.id, resource_no=document.no, action=DocumentAction.APPROVED, actor_id=principal.id, old_status=old_status, new_status=str(document.status), old_version=old_version, new_version=document.version)
    complete_command(receipt=claim.receipt, resource_type="purchase_return", resource_id=document.id, resource_version=document.version)
    uow.session.commit()
    uow.session.refresh(document)
    return purchase_return_public(uow, document)


@router.post(
    "/purchase-returns/{document_id}/reverse",
    dependencies=[Depends(require_module_access("erp", "erp:purchase-return:reverse"))],
    response_model=PurchaseReturnPublic,
)
def reverse_purchase_return(
    document_id: uuid.UUID, command: DocumentReverseCommand, uow: ErpTenantUowDep, principal: CurrentPrincipal, idempotency_key: str = Header(alias="Idempotency-Key")
) -> PurchaseReturnPublic:
    claim = command_claim(uow=uow, command_name="erp.purchase-return.reverse", idempotency_key=idempotency_key, principal=principal, payload=command.model_dump(mode="json"), resource_id=document_id)
    if claim.replay:
        return replay_document(uow, claim, principal)
    document = uow.session.exec(select(PurchaseReturn).where(PurchaseReturn.id == document_id).with_for_update()).first()
    if document is None:
        raise HTTPException(status_code=404, detail="Purchase return not found")
    assert_document_scope(uow=uow, principal=principal, document=document)
    if document.status != DocumentStatus.APPROVED or document.version != command.expected_version:
        raise HTTPException(status_code=409, detail="Purchase return version conflict")
    if has_approved_payment(uow=uow, source_type=SettlementSourceType.PURCHASE_RETURN, source_document_id=document.id):
        raise HTTPException(status_code=409, detail="Purchase return has approved settlement documents")
    items = uow.session.exec(select(PurchaseReturnItem).where(PurchaseReturnItem.purchase_return_id == document.id).order_by(PurchaseReturnItem.line_no)).all()
    receipt_items = uow.session.exec(
        select(PurchaseInItem)
        .where(PurchaseInItem.id.in_({item.purchase_in_item_id for item in items}))
        .order_by(col(PurchaseInItem.id))
        .with_for_update()
    ).all()
    receipt_items_by_id = {item.id: item for item in receipt_items}
    order_items = lock_purchase_order_items(uow=uow, item_ids={item.purchase_order_item_id for item in items})
    if any(
        receipt_items_by_id.get(item.purchase_in_item_id) is None
        or receipt_items_by_id[item.purchase_in_item_id].returned_quantity < item.quantity
        or order_items[item.purchase_order_item_id].returned_quantity < item.quantity
        for item in items
    ):
        raise HTTPException(status_code=409, detail="Purchase return quantity is inconsistent")
    ledgers = uow.session.exec(
        select(StockLedger).where(
            StockLedger.source_document_type == "purchase_return",
            StockLedger.source_document_id == document.id,
            StockLedger.source_version == document.version,
            StockLedger.ledger_type == StockLedgerType.PURCHASE_RETURN,
            StockLedger.reversal_of_id.is_(None),
        )
    ).all()
    if len(ledgers) != len(items):
        raise HTTPException(status_code=409, detail="Purchase return has no reversible posting")
    try:
        InventoryPostingService(uow).post(
            effects=reversal_effects(document_id=document.id, document_no=document.no, document_type="purchase_return", version=document.version, ledgers=ledgers),
            operator_id=principal.id,
            require_active_references=False,
        )
    except InventoryConflictError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    for item in items:
        receipt_items_by_id[item.purchase_in_item_id].returned_quantity -= item.quantity
        order_items[item.purchase_order_item_id].returned_quantity -= item.quantity
        uow.session.add(receipt_items_by_id[item.purchase_in_item_id])
        uow.session.add(order_items[item.purchase_order_item_id])
    old_status, old_version = str(document.status), document.version
    set_reversed(document=document, principal=principal)
    uow.session.add(document)
    enqueue_document_lifecycle_event(
        uow=uow, document=document, document_type="purchase_return", action="reversed"
    )
    record_action(uow=uow, resource_type="purchase_return", resource_id=document.id, resource_no=document.no, action=DocumentAction.REVERSED, actor_id=principal.id, old_status=old_status, new_status=str(document.status), old_version=old_version, new_version=document.version, reason=command.reason)
    complete_command(receipt=claim.receipt, resource_type="purchase_return", resource_id=document.id, resource_version=document.version)
    uow.session.commit()
    uow.session.refresh(document)
    return purchase_return_public(uow, document)
