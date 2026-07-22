"""Sales shipment and return HTTP contracts with source-order inventory posting."""

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
    FinanceReceipt,
    FinanceReceiptItem,
    SaleOrder,
    SaleOrderItem,
    SaleOut,
    SaleOutItem,
    SaleReturn,
    SaleReturnItem,
    SettlementSourceType,
    StockLedger,
    StockLedgerType,
)
from app.modules.erp.infrastructure.tenant_uow import ErpTenantUowDep
from app.modules.erp.observability import ErpDocumentCommandMetricRoute
from app.modules.erp.public_api.dto import (
    DocumentCommand,
    DocumentReverseCommand,
    SaleOutCreate,
    SaleOutItemPublic,
    SaleOutPublic,
    SaleOutsPublic,
    SaleOutUpdate,
    SaleReturnCreate,
    SaleReturnItemPublic,
    SaleReturnPublic,
    SaleReturnsPublic,
    SaleReturnUpdate,
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
    tags=["erp-sale-stock"],
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
) -> SaleOutPublic | SaleReturnPublic:
    if claim.receipt.resource_id is None:
        raise HTTPException(status_code=409, detail="Idempotency receipt is unavailable")
    if claim.receipt.resource_type == "sale_out":
        document = uow.session.get(SaleOut, claim.receipt.resource_id)
        if document is not None:
            assert_document_scope(uow=uow, principal=principal, document=document)
            return sale_out_public(uow, document)
    if claim.receipt.resource_type == "sale_return":
        document = uow.session.get(SaleReturn, claim.receipt.resource_id)
        if document is not None:
            assert_document_scope(uow=uow, principal=principal, document=document)
            return sale_return_public(uow, document)
    raise HTTPException(status_code=409, detail="Idempotency receipt document is unavailable")


def owner_scope(*, uow: ErpTenantUowDep, principal: CurrentPrincipal, owner_column: Any) -> Any:
    return build_owner_data_scope_filter(
        session=uow.session,
        current_principal=principal,
        tenant_id=uow.tenant_id,
        owner_id_column=owner_column,
    )


def assert_document_scope(*, uow: ErpTenantUowDep, principal: CurrentPrincipal, document: SaleOut | SaleReturn) -> None:
    model = SaleOut if isinstance(document, SaleOut) else SaleReturn
    allowed = uow.session.exec(
        select(model.id).where(
            model.id == document.id,
            owner_scope(uow=uow, principal=principal, owner_column=model.owner_id),
        )
    ).first()
    if allowed is None:
        raise HTTPException(status_code=403, detail="Not enough permissions")


def sale_out_public(uow: ErpTenantUowDep, document: SaleOut) -> SaleOutPublic:
    items = uow.session.exec(
        select(SaleOutItem)
        .where(SaleOutItem.sale_out_id == document.id)
        .order_by(SaleOutItem.line_no)
    ).all()
    return SaleOutPublic.model_validate(document).model_copy(
        update={"items": [SaleOutItemPublic.model_validate(item) for item in items]}
    )


def sale_return_public(
    uow: ErpTenantUowDep, document: SaleReturn
) -> SaleReturnPublic:
    items = uow.session.exec(
        select(SaleReturnItem)
        .where(SaleReturnItem.sale_return_id == document.id)
        .order_by(SaleReturnItem.line_no)
    ).all()
    return SaleReturnPublic.model_validate(document).model_copy(
        update={
            "items": [SaleReturnItemPublic.model_validate(item) for item in items]
        }
    )


def shipment_effects(
    document: SaleOut, items: list[SaleOutItem]
) -> tuple[InventoryEffect, ...]:
    return tuple(
        InventoryEffect(
            product_id=item.product_id,
            warehouse_id=item.warehouse_id,
            delta_quantity=-item.quantity,
            ledger_type=StockLedgerType.SALE_OUT,
            source_document_type="sale_out",
            source_document_id=document.id,
            source_item_id=item.id,
            source_document_no=document.no,
            source_version=document.version + 1,
        )
        for item in items
    )


def return_effects(
    document: SaleReturn, items: list[SaleReturnItem]
) -> tuple[InventoryEffect, ...]:
    return tuple(
        InventoryEffect(
            product_id=item.product_id,
            warehouse_id=item.warehouse_id,
            delta_quantity=item.quantity,
            ledger_type=StockLedgerType.SALE_RETURN,
            source_document_type="sale_return",
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
        StockLedgerType.SALE_OUT: StockLedgerType.SALE_OUT_REVERSAL,
        StockLedgerType.SALE_RETURN: StockLedgerType.SALE_RETURN_REVERSAL,
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


def lock_sale_order_items(
    *, uow: ErpTenantUowDep, item_ids: set[uuid.UUID]
) -> dict[uuid.UUID, SaleOrderItem]:
    items = uow.session.exec(
        select(SaleOrderItem)
        .where(SaleOrderItem.id.in_(item_ids))
        .order_by(col(SaleOrderItem.id))
        .with_for_update()
    ).all()
    if len(items) != len(item_ids):
        raise HTTPException(status_code=409, detail="Sales order line is unavailable")
    return {item.id: item for item in items}


def set_approved(*, document: SaleOut | SaleReturn, principal: CurrentPrincipal) -> None:
    document.status = DocumentStatus.APPROVED
    document.version += 1
    document.approved_by = principal.id
    document.approved_at = get_datetime_utc()
    document.updated_by = principal.id
    document.updated_at = get_datetime_utc()


def set_reversed(*, document: SaleOut | SaleReturn, principal: CurrentPrincipal) -> None:
    document.status = DocumentStatus.DRAFT
    document.version += 1
    document.reversed_by = principal.id
    document.reversed_at = get_datetime_utc()
    document.updated_by = principal.id
    document.updated_at = get_datetime_utc()


def has_approved_receipt(*, uow: ErpTenantUowDep, source_type: SettlementSourceType, source_document_id: uuid.UUID) -> bool:
    return uow.session.exec(
        select(FinanceReceiptItem.id)
        .join(FinanceReceipt, FinanceReceipt.id == FinanceReceiptItem.finance_receipt_id)
        .where(
            FinanceReceiptItem.source_type == source_type,
            FinanceReceiptItem.source_document_id == source_document_id,
            FinanceReceipt.status == DocumentStatus.APPROVED,
        )
    ).first() is not None


@router.get(
    "/sale-outs",
    dependencies=[Depends(require_module_access("erp", "erp:sale-out:list"))],
    response_model=SaleOutsPublic,
)
def read_sale_outs(
    uow: ErpTenantUowDep, principal: CurrentPrincipal, page: int = 1, page_size: int = 20,
    keyword: str | None = None, product_id: uuid.UUID | None = None, customer_id: uuid.UUID | None = None,
    owner_id: uuid.UUID | None = None, status: str | None = None, remark: str | None = None,
    business_from: datetime | None = None, business_to: datetime | None = None,
) -> SaleOutsPublic:
    page, page_size = normalize_pagination(page=page, page_size=page_size)
    try:
        filters = document_list_filters(model=SaleOut, item_model=SaleOutItem, item_document_column=SaleOutItem.sale_out_id, counterparty_id_column=SaleOut.customer_id, counterparty_name_column=SaleOut.customer_name, scope=owner_scope(uow=uow, principal=principal, owner_column=SaleOut.owner_id), keyword=keyword, product_id=product_id, counterparty_id=customer_id, owner_id=owner_id, status=status, remark=remark, business_from=business_from, business_to=business_to)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    total = int(uow.session.exec(select(func.count()).select_from(SaleOut).where(*filters)).one())
    documents = uow.session.exec(
        select(SaleOut)
        .where(*filters)
        .order_by(col(SaleOut.business_at).desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
    ).all()
    return SaleOutsPublic(
        items=[sale_out_public(uow, document) for document in documents],
        total=total,
        page=page,
        page_size=page_size,
    )


@router.get(
    "/sale-outs/{document_id}",
    dependencies=[Depends(require_module_access("erp", "erp:sale-out:list"))],
    response_model=SaleOutPublic,
)
def read_sale_out(
    document_id: uuid.UUID, uow: ErpTenantUowDep, principal: CurrentPrincipal
) -> SaleOutPublic:
    document = uow.session.get(SaleOut, document_id)
    if document is None:
        raise HTTPException(status_code=404, detail="Sales shipment not found")
    assert_document_scope(uow=uow, principal=principal, document=document)
    return sale_out_public(uow, document)


@router.post(
    "/sale-outs",
    dependencies=[Depends(require_module_access("erp", "erp:sale-out:create"))],
    response_model=SaleOutPublic,
)
def create_sale_out(
    command: SaleOutCreate,
    uow: ErpTenantUowDep,
    principal: CurrentPrincipal,
    tenant: CurrentTenant,
    idempotency_key: str = Header(alias="Idempotency-Key"),
) -> SaleOutPublic:
    claim = command_claim(uow=uow, command_name="erp.sale-out.create", idempotency_key=idempotency_key, principal=principal, payload=command.model_dump(mode="json"))
    if claim.replay:
        return replay_document(uow, claim, principal)
    order = uow.session.exec(
        select(SaleOrder).where(
            SaleOrder.id == command.sale_order_id,
            owner_scope(uow=uow, principal=principal, owner_column=SaleOrder.owner_id),
        )
    ).first()
    if order is None:
        raise HTTPException(status_code=404, detail="Sales order not found")
    if order.status != DocumentStatus.APPROVED:
        raise HTTPException(status_code=409, detail="Sales order must be approved")
    line_ids = [line.sale_order_item_id for line in command.items]
    if len(set(line_ids)) != len(line_ids):
        raise HTTPException(status_code=422, detail="Sales shipment cannot repeat an order line")
    source_items = {
        item.id: item
        for item in uow.session.exec(
            select(SaleOrderItem).where(
                SaleOrderItem.sale_order_id == order.id,
                SaleOrderItem.id.in_(line_ids),
            )
        ).all()
    }
    if len(source_items) != len(line_ids):
        raise HTTPException(status_code=409, detail="Sales order line is unavailable")
    for line in command.items:
        source = source_items[line.sale_order_item_id]
        if line.quantity > source.quantity - source.shipped_quantity:
            raise HTTPException(status_code=409, detail="Shipment quantity exceeds remaining order quantity")
    try:
        amounts = calculate_trade_document_amounts(
            lines=(
                (line.quantity, source_items[line.sale_order_item_id].unit_price, source_items[line.sale_order_item_id].tax_rate)
                for line in command.items
            ),
            discount_rate=command.discount_rate,
            discount_amount=command.discount_amount,
            adjustment=command.other_deduction,
            adjustment_sign=-1,
        )
        settlement_account_id = ensure_active_settlement_account(
            uow=uow, account_id=command.settlement_account_id
        )
    except (TradeDocumentAmountError, SettlementAccountUnavailableError) as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc

    document = SaleOut(
        tenant_id=tenant.tenant_id,
        no=allocate_document_no(uow=uow, prefix="XSCK"),
        sale_order_id=order.id,
        sale_order_no=order.no,
        customer_id=order.customer_id,
        customer_name=order.customer_name,
        settlement_account_id=settlement_account_id or order.settlement_account_id,
        business_at=resolve_business_at(uow=uow, requested_at=command.business_at),
        owner_id=principal.id,
        total_quantity=amounts.total_quantity,
        product_amount=amounts.product_amount,
        tax_amount=amounts.tax_amount,
        discount_rate=command.discount_rate,
        discount_amount=amounts.discount_amount,
        other_deduction=command.other_deduction,
        total_amount=amounts.total_amount,
        remark=command.remark,
        created_by=principal.id,
        updated_by=principal.id,
    )
    uow.session.add(document)
    uow.session.flush()
    uow.session.add_all(
        [
            SaleOutItem(
                tenant_id=tenant.tenant_id,
                sale_out_id=document.id,
                sale_order_item_id=line.sale_order_item_id,
                line_no=index,
                product_id=source_items[line.sale_order_item_id].product_id,
                warehouse_id=line.warehouse_id,
                product_name=source_items[line.sale_order_item_id].product_name,
                unit_name=source_items[line.sale_order_item_id].unit_name,
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
    record_action(uow=uow, resource_type="sale_out", resource_id=document.id, resource_no=document.no, action=DocumentAction.CREATED, actor_id=principal.id, new_status=str(document.status), new_version=document.version, metadata={"item_count": len(command.items)})
    complete_command(receipt=claim.receipt, resource_type="sale_out", resource_id=document.id, resource_version=document.version)
    uow.session.commit()
    uow.session.refresh(document)
    return sale_out_public(uow, document)


@router.patch("/sale-outs/{document_id}", dependencies=[Depends(require_module_access("erp", "erp:sale-out:update"))], response_model=SaleOutPublic)
def update_sale_out(document_id: uuid.UUID, command: SaleOutUpdate, uow: ErpTenantUowDep, principal: CurrentPrincipal) -> SaleOutPublic:
    document = uow.session.exec(select(SaleOut).where(SaleOut.id == document_id).with_for_update()).first()
    if document is None:
        raise HTTPException(status_code=404, detail="Sale shipment not found")
    assert_document_scope(uow=uow, principal=principal, document=document)
    if document.status != DocumentStatus.DRAFT or document.version != command.expected_version:
        raise HTTPException(status_code=409, detail="Sale shipment version conflict")
    if command.sale_order_id != document.sale_order_id:
        raise HTTPException(status_code=409, detail="Sale shipment source order cannot change")
    order = uow.session.exec(select(SaleOrder).where(SaleOrder.id == document.sale_order_id).with_for_update()).first()
    if order is None or order.status != DocumentStatus.APPROVED:
        raise HTTPException(status_code=409, detail="Sale order must be approved")
    line_ids = [line.sale_order_item_id for line in command.items]
    if len(set(line_ids)) != len(line_ids):
        raise HTTPException(status_code=422, detail="Sale shipment cannot repeat an order line")
    source_items = lock_sale_order_items(uow=uow, item_ids=set(line_ids))
    if any(item.sale_order_id != order.id for item in source_items.values()) or any(line.quantity > source_items[line.sale_order_item_id].quantity - source_items[line.sale_order_item_id].shipped_quantity for line in command.items):
        raise HTTPException(status_code=409, detail="Shipment quantity exceeds remaining order quantity")
    try:
        amounts = calculate_trade_document_amounts(lines=((line.quantity, source_items[line.sale_order_item_id].unit_price, source_items[line.sale_order_item_id].tax_rate) for line in command.items), discount_rate=command.discount_rate, discount_amount=command.discount_amount, adjustment=command.other_deduction, adjustment_sign=-1)
        settlement_account_id = ensure_active_settlement_account(uow=uow, account_id=command.settlement_account_id)
    except (TradeDocumentAmountError, SettlementAccountUnavailableError) as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    old_version = document.version
    for item in uow.session.exec(select(SaleOutItem).where(SaleOutItem.sale_out_id == document.id)).all():
        uow.session.delete(item)
    uow.session.flush()
    document.settlement_account_id = settlement_account_id or order.settlement_account_id
    document.business_at = resolve_business_at(uow=uow, requested_at=command.business_at) if command.business_at is not None else document.business_at
    document.total_quantity, document.product_amount, document.tax_amount, document.discount_rate, document.discount_amount, document.other_deduction, document.total_amount, document.remark = amounts.total_quantity, amounts.product_amount, amounts.tax_amount, command.discount_rate, amounts.discount_amount, command.other_deduction, amounts.total_amount, command.remark
    document.version += 1
    document.updated_by, document.updated_at = principal.id, get_datetime_utc()
    uow.session.add(document)
    uow.session.add_all([SaleOutItem(tenant_id=uow.tenant_id, sale_out_id=document.id, sale_order_item_id=line.sale_order_item_id, line_no=index, product_id=source_items[line.sale_order_item_id].product_id, warehouse_id=line.warehouse_id, product_name=source_items[line.sale_order_item_id].product_name, unit_name=source_items[line.sale_order_item_id].unit_name, quantity=amount.quantity, reference_price=amount.reference_price, tax_rate=amount.tax_rate, product_amount=amount.product_amount, tax_amount=amount.tax_amount, total_amount=amount.total_amount, remark=line.remark) for index, (line, amount) in enumerate(zip(command.items, amounts.lines, strict=True), start=1)])
    record_action(uow=uow, resource_type="sale_out", resource_id=document.id, resource_no=document.no, action=DocumentAction.UPDATED, actor_id=principal.id, old_version=old_version, new_version=document.version, metadata={"item_count": len(command.items)})
    uow.session.commit()
    uow.session.refresh(document)
    return sale_out_public(uow, document)


@router.delete("/sale-outs/{document_id}", dependencies=[Depends(require_module_access("erp", "erp:sale-out:delete"))], status_code=204)
def delete_sale_out(document_id: uuid.UUID, uow: ErpTenantUowDep, principal: CurrentPrincipal) -> Response:
    document = uow.session.exec(select(SaleOut).where(SaleOut.id == document_id).with_for_update()).first()
    if document is None:
        raise HTTPException(status_code=404, detail="Sale shipment not found")
    assert_document_scope(uow=uow, principal=principal, document=document)
    if document.status != DocumentStatus.DRAFT:
        raise HTTPException(status_code=409, detail="Sale shipment must be draft before deletion")
    record_action(uow=uow, resource_type="sale_out", resource_id=document.id, resource_no=document.no, action=DocumentAction.DELETED, actor_id=principal.id, old_status=str(document.status), old_version=document.version)
    uow.session.delete(document)
    uow.session.commit()
    return Response(status_code=204)


@router.post(
    "/sale-outs/{document_id}/approve",
    dependencies=[Depends(require_module_access("erp", "erp:sale-out:approve"))],
    response_model=SaleOutPublic,
)
def approve_sale_out(
    document_id: uuid.UUID, command: DocumentCommand, uow: ErpTenantUowDep, principal: CurrentPrincipal, idempotency_key: str = Header(alias="Idempotency-Key")
) -> SaleOutPublic:
    claim = command_claim(uow=uow, command_name="erp.sale-out.approve", idempotency_key=idempotency_key, principal=principal, payload=command.model_dump(mode="json"), resource_id=document_id)
    if claim.replay:
        return replay_document(uow, claim, principal)
    document = uow.session.exec(select(SaleOut).where(SaleOut.id == document_id).with_for_update()).first()
    if document is None:
        raise HTTPException(status_code=404, detail="Sales shipment not found")
    assert_document_scope(uow=uow, principal=principal, document=document)
    if document.status != DocumentStatus.DRAFT or document.version != command.expected_version:
        raise HTTPException(status_code=409, detail="Sales shipment version conflict")
    order = uow.session.exec(select(SaleOrder).where(SaleOrder.id == document.sale_order_id).with_for_update()).first()
    if order is None or order.status != DocumentStatus.APPROVED:
        raise HTTPException(status_code=409, detail="Sales order must be approved")
    items = uow.session.exec(select(SaleOutItem).where(SaleOutItem.sale_out_id == document.id).order_by(SaleOutItem.line_no)).all()
    order_items = lock_sale_order_items(uow=uow, item_ids={item.sale_order_item_id for item in items})
    for item in items:
        source = order_items[item.sale_order_item_id]
        if source.sale_order_id != order.id or item.quantity > source.quantity - source.shipped_quantity:
            raise HTTPException(status_code=409, detail="Shipment quantity exceeds remaining order quantity")
    try:
        InventoryPostingService(uow).post(effects=shipment_effects(document, items), operator_id=principal.id)
    except InventoryConflictError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    for item in items:
        source = order_items[item.sale_order_item_id]
        source.shipped_quantity += item.quantity
        uow.session.add(source)
    old_status, old_version = str(document.status), document.version
    set_approved(document=document, principal=principal)
    uow.session.add(document)
    enqueue_document_lifecycle_event(
        uow=uow, document=document, document_type="sale_out", action="approved"
    )
    record_action(uow=uow, resource_type="sale_out", resource_id=document.id, resource_no=document.no, action=DocumentAction.APPROVED, actor_id=principal.id, old_status=old_status, new_status=str(document.status), old_version=old_version, new_version=document.version)
    complete_command(receipt=claim.receipt, resource_type="sale_out", resource_id=document.id, resource_version=document.version)
    uow.session.commit()
    uow.session.refresh(document)
    return sale_out_public(uow, document)


@router.post(
    "/sale-outs/{document_id}/reverse",
    dependencies=[Depends(require_module_access("erp", "erp:sale-out:reverse"))],
    response_model=SaleOutPublic,
)
def reverse_sale_out(
    document_id: uuid.UUID, command: DocumentReverseCommand, uow: ErpTenantUowDep, principal: CurrentPrincipal, idempotency_key: str = Header(alias="Idempotency-Key")
) -> SaleOutPublic:
    claim = command_claim(uow=uow, command_name="erp.sale-out.reverse", idempotency_key=idempotency_key, principal=principal, payload=command.model_dump(mode="json"), resource_id=document_id)
    if claim.replay:
        return replay_document(uow, claim, principal)
    document = uow.session.exec(select(SaleOut).where(SaleOut.id == document_id).with_for_update()).first()
    if document is None:
        raise HTTPException(status_code=404, detail="Sales shipment not found")
    assert_document_scope(uow=uow, principal=principal, document=document)
    if document.status != DocumentStatus.APPROVED or document.version != command.expected_version:
        raise HTTPException(status_code=409, detail="Sales shipment version conflict")
    items = uow.session.exec(select(SaleOutItem).where(SaleOutItem.sale_out_id == document.id).order_by(SaleOutItem.line_no).with_for_update()).all()
    if any(item.returned_quantity > 0 for item in items):
        raise HTTPException(status_code=409, detail="Sales shipment has downstream return documents")
    if has_approved_receipt(uow=uow, source_type=SettlementSourceType.SALE_OUT, source_document_id=document.id):
        raise HTTPException(status_code=409, detail="Sales shipment has approved settlement documents")
    ledgers = uow.session.exec(
        select(StockLedger).where(
            StockLedger.source_document_type == "sale_out",
            StockLedger.source_document_id == document.id,
            StockLedger.source_version == document.version,
            StockLedger.ledger_type == StockLedgerType.SALE_OUT,
            StockLedger.reversal_of_id.is_(None),
        )
    ).all()
    if len(ledgers) != len(items):
        raise HTTPException(status_code=409, detail="Sales shipment has no reversible posting")
    order = uow.session.exec(select(SaleOrder).where(SaleOrder.id == document.sale_order_id).with_for_update()).first()
    if order is None:
        raise HTTPException(status_code=409, detail="Sales order is unavailable")
    order_items = lock_sale_order_items(uow=uow, item_ids={item.sale_order_item_id for item in items})
    if any(order_items[item.sale_order_item_id].shipped_quantity < item.quantity for item in items):
        raise HTTPException(status_code=409, detail="Sales order shipment quantity is inconsistent")
    try:
        InventoryPostingService(uow).post(
            effects=reversal_effects(document_id=document.id, document_no=document.no, document_type="sale_out", version=document.version, ledgers=ledgers),
            operator_id=principal.id,
            require_active_references=False,
        )
    except InventoryConflictError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    for item in items:
        source = order_items[item.sale_order_item_id]
        source.shipped_quantity -= item.quantity
        uow.session.add(source)
    old_status, old_version = str(document.status), document.version
    set_reversed(document=document, principal=principal)
    uow.session.add(document)
    enqueue_document_lifecycle_event(
        uow=uow, document=document, document_type="sale_out", action="reversed"
    )
    record_action(uow=uow, resource_type="sale_out", resource_id=document.id, resource_no=document.no, action=DocumentAction.REVERSED, actor_id=principal.id, old_status=old_status, new_status=str(document.status), old_version=old_version, new_version=document.version, reason=command.reason)
    complete_command(receipt=claim.receipt, resource_type="sale_out", resource_id=document.id, resource_version=document.version)
    uow.session.commit()
    uow.session.refresh(document)
    return sale_out_public(uow, document)


@router.get(
    "/sale-returns",
    dependencies=[Depends(require_module_access("erp", "erp:sale-return:list"))],
    response_model=SaleReturnsPublic,
)
def read_sale_returns(
    uow: ErpTenantUowDep, principal: CurrentPrincipal, page: int = 1, page_size: int = 20,
    keyword: str | None = None, product_id: uuid.UUID | None = None, customer_id: uuid.UUID | None = None,
    owner_id: uuid.UUID | None = None, status: str | None = None, remark: str | None = None,
    business_from: datetime | None = None, business_to: datetime | None = None,
) -> SaleReturnsPublic:
    page, page_size = normalize_pagination(page=page, page_size=page_size)
    try:
        filters = document_list_filters(model=SaleReturn, item_model=SaleReturnItem, item_document_column=SaleReturnItem.sale_return_id, counterparty_id_column=SaleReturn.customer_id, counterparty_name_column=SaleReturn.customer_name, scope=owner_scope(uow=uow, principal=principal, owner_column=SaleReturn.owner_id), keyword=keyword, product_id=product_id, counterparty_id=customer_id, owner_id=owner_id, status=status, remark=remark, business_from=business_from, business_to=business_to)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    total = int(uow.session.exec(select(func.count()).select_from(SaleReturn).where(*filters)).one())
    documents = uow.session.exec(
        select(SaleReturn)
        .where(*filters)
        .order_by(col(SaleReturn.business_at).desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
    ).all()
    return SaleReturnsPublic(
        items=[sale_return_public(uow, document) for document in documents],
        total=total,
        page=page,
        page_size=page_size,
    )


@router.get(
    "/sale-returns/{document_id}",
    dependencies=[Depends(require_module_access("erp", "erp:sale-return:list"))],
    response_model=SaleReturnPublic,
)
def read_sale_return(
    document_id: uuid.UUID, uow: ErpTenantUowDep, principal: CurrentPrincipal
) -> SaleReturnPublic:
    document = uow.session.get(SaleReturn, document_id)
    if document is None:
        raise HTTPException(status_code=404, detail="Sales return not found")
    assert_document_scope(uow=uow, principal=principal, document=document)
    return sale_return_public(uow, document)


@router.post(
    "/sale-returns",
    dependencies=[Depends(require_module_access("erp", "erp:sale-return:create"))],
    response_model=SaleReturnPublic,
)
def create_sale_return(
    command: SaleReturnCreate,
    uow: ErpTenantUowDep,
    principal: CurrentPrincipal,
    tenant: CurrentTenant,
    idempotency_key: str = Header(alias="Idempotency-Key"),
) -> SaleReturnPublic:
    claim = command_claim(uow=uow, command_name="erp.sale-return.create", idempotency_key=idempotency_key, principal=principal, payload=command.model_dump(mode="json"))
    if claim.replay:
        return replay_document(uow, claim, principal)
    shipment = uow.session.exec(
        select(SaleOut).where(
            SaleOut.id == command.sale_out_id,
            owner_scope(uow=uow, principal=principal, owner_column=SaleOut.owner_id),
        )
    ).first()
    if shipment is None:
        raise HTTPException(status_code=404, detail="Sales shipment not found")
    if shipment.status != DocumentStatus.APPROVED:
        raise HTTPException(status_code=409, detail="Sales shipment must be approved")
    line_ids = [line.sale_out_item_id for line in command.items]
    if len(set(line_ids)) != len(line_ids):
        raise HTTPException(status_code=422, detail="Sales return cannot repeat a shipment line")
    source_items = {
        item.id: item
        for item in uow.session.exec(
            select(SaleOutItem).where(
                SaleOutItem.sale_out_id == shipment.id,
                SaleOutItem.id.in_(line_ids),
            )
        ).all()
    }
    if len(source_items) != len(line_ids):
        raise HTTPException(status_code=409, detail="Sales shipment line is unavailable")
    for line in command.items:
        source = source_items[line.sale_out_item_id]
        if line.quantity > source.quantity - source.returned_quantity:
            raise HTTPException(status_code=409, detail="Return quantity exceeds shipment quantity")
    try:
        amounts = calculate_trade_document_amounts(
            lines=(
                (line.quantity, source_items[line.sale_out_item_id].reference_price, source_items[line.sale_out_item_id].tax_rate)
                for line in command.items
            ),
            discount_rate=command.discount_rate,
            discount_amount=command.discount_amount,
            adjustment=command.other_deduction,
            adjustment_sign=-1,
        )
        settlement_account_id = ensure_active_settlement_account(
            uow=uow, account_id=command.settlement_account_id
        )
    except (TradeDocumentAmountError, SettlementAccountUnavailableError) as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    document = SaleReturn(
        tenant_id=tenant.tenant_id,
        no=allocate_document_no(uow=uow, prefix="XSTH"),
        sale_out_id=shipment.id,
        sale_out_no=shipment.no,
        sale_order_id=shipment.sale_order_id,
        customer_id=shipment.customer_id,
        customer_name=shipment.customer_name,
        settlement_account_id=settlement_account_id or shipment.settlement_account_id,
        business_at=resolve_business_at(uow=uow, requested_at=command.business_at),
        owner_id=principal.id,
        total_quantity=amounts.total_quantity,
        product_amount=amounts.product_amount,
        tax_amount=amounts.tax_amount,
        discount_rate=command.discount_rate,
        discount_amount=amounts.discount_amount,
        other_deduction=command.other_deduction,
        total_amount=amounts.total_amount,
        remark=command.remark,
        created_by=principal.id,
        updated_by=principal.id,
    )
    uow.session.add(document)
    uow.session.flush()
    uow.session.add_all(
        [
            SaleReturnItem(
                tenant_id=tenant.tenant_id,
                sale_return_id=document.id,
                sale_out_item_id=line.sale_out_item_id,
                sale_order_item_id=source_items[line.sale_out_item_id].sale_order_item_id,
                line_no=index,
                product_id=source_items[line.sale_out_item_id].product_id,
                warehouse_id=source_items[line.sale_out_item_id].warehouse_id,
                product_name=source_items[line.sale_out_item_id].product_name,
                unit_name=source_items[line.sale_out_item_id].unit_name,
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
    record_action(uow=uow, resource_type="sale_return", resource_id=document.id, resource_no=document.no, action=DocumentAction.CREATED, actor_id=principal.id, new_status=str(document.status), new_version=document.version, metadata={"item_count": len(command.items)})
    complete_command(receipt=claim.receipt, resource_type="sale_return", resource_id=document.id, resource_version=document.version)
    uow.session.commit()
    uow.session.refresh(document)
    return sale_return_public(uow, document)


@router.patch("/sale-returns/{document_id}", dependencies=[Depends(require_module_access("erp", "erp:sale-return:update"))], response_model=SaleReturnPublic)
def update_sale_return(document_id: uuid.UUID, command: SaleReturnUpdate, uow: ErpTenantUowDep, principal: CurrentPrincipal) -> SaleReturnPublic:
    document = uow.session.exec(select(SaleReturn).where(SaleReturn.id == document_id).with_for_update()).first()
    if document is None:
        raise HTTPException(status_code=404, detail="Sale return not found")
    assert_document_scope(uow=uow, principal=principal, document=document)
    if document.status != DocumentStatus.DRAFT or document.version != command.expected_version:
        raise HTTPException(status_code=409, detail="Sale return version conflict")
    if command.sale_out_id != document.sale_out_id:
        raise HTTPException(status_code=409, detail="Sale return source shipment cannot change")
    shipment = uow.session.exec(select(SaleOut).where(SaleOut.id == document.sale_out_id).with_for_update()).first()
    if shipment is None or shipment.status != DocumentStatus.APPROVED:
        raise HTTPException(status_code=409, detail="Sale shipment must be approved")
    line_ids = [line.sale_out_item_id for line in command.items]
    if len(set(line_ids)) != len(line_ids):
        raise HTTPException(status_code=422, detail="Sale return cannot repeat a shipment line")
    source_items = {item.id: item for item in uow.session.exec(select(SaleOutItem).where(SaleOutItem.sale_out_id == shipment.id, SaleOutItem.id.in_(line_ids)).with_for_update()).all()}
    if len(source_items) != len(line_ids) or any(line.quantity > source_items[line.sale_out_item_id].quantity - source_items[line.sale_out_item_id].returned_quantity for line in command.items):
        raise HTTPException(status_code=409, detail="Return quantity exceeds shipment quantity")
    try:
        amounts = calculate_trade_document_amounts(lines=((line.quantity, source_items[line.sale_out_item_id].reference_price, source_items[line.sale_out_item_id].tax_rate) for line in command.items), discount_rate=command.discount_rate, discount_amount=command.discount_amount, adjustment=command.other_deduction, adjustment_sign=-1)
        settlement_account_id = ensure_active_settlement_account(uow=uow, account_id=command.settlement_account_id)
    except (TradeDocumentAmountError, SettlementAccountUnavailableError) as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    old_version = document.version
    for item in uow.session.exec(select(SaleReturnItem).where(SaleReturnItem.sale_return_id == document.id)).all():
        uow.session.delete(item)
    uow.session.flush()
    document.settlement_account_id = settlement_account_id or shipment.settlement_account_id
    document.business_at = resolve_business_at(uow=uow, requested_at=command.business_at) if command.business_at is not None else document.business_at
    document.total_quantity, document.product_amount, document.tax_amount, document.discount_rate, document.discount_amount, document.other_deduction, document.total_amount, document.remark = amounts.total_quantity, amounts.product_amount, amounts.tax_amount, command.discount_rate, amounts.discount_amount, command.other_deduction, amounts.total_amount, command.remark
    document.version += 1
    document.updated_by, document.updated_at = principal.id, get_datetime_utc()
    uow.session.add(document)
    uow.session.add_all([SaleReturnItem(tenant_id=uow.tenant_id, sale_return_id=document.id, sale_out_item_id=line.sale_out_item_id, sale_order_item_id=source_items[line.sale_out_item_id].sale_order_item_id, line_no=index, product_id=source_items[line.sale_out_item_id].product_id, warehouse_id=source_items[line.sale_out_item_id].warehouse_id, product_name=source_items[line.sale_out_item_id].product_name, unit_name=source_items[line.sale_out_item_id].unit_name, quantity=amount.quantity, reference_price=amount.reference_price, tax_rate=amount.tax_rate, product_amount=amount.product_amount, tax_amount=amount.tax_amount, total_amount=amount.total_amount, remark=line.remark) for index, (line, amount) in enumerate(zip(command.items, amounts.lines, strict=True), start=1)])
    record_action(uow=uow, resource_type="sale_return", resource_id=document.id, resource_no=document.no, action=DocumentAction.UPDATED, actor_id=principal.id, old_version=old_version, new_version=document.version, metadata={"item_count": len(command.items)})
    uow.session.commit()
    uow.session.refresh(document)
    return sale_return_public(uow, document)


@router.delete("/sale-returns/{document_id}", dependencies=[Depends(require_module_access("erp", "erp:sale-return:delete"))], status_code=204)
def delete_sale_return(document_id: uuid.UUID, uow: ErpTenantUowDep, principal: CurrentPrincipal) -> Response:
    document = uow.session.exec(select(SaleReturn).where(SaleReturn.id == document_id).with_for_update()).first()
    if document is None:
        raise HTTPException(status_code=404, detail="Sale return not found")
    assert_document_scope(uow=uow, principal=principal, document=document)
    if document.status != DocumentStatus.DRAFT:
        raise HTTPException(status_code=409, detail="Sale return must be draft before deletion")
    record_action(uow=uow, resource_type="sale_return", resource_id=document.id, resource_no=document.no, action=DocumentAction.DELETED, actor_id=principal.id, old_status=str(document.status), old_version=document.version)
    uow.session.delete(document)
    uow.session.commit()
    return Response(status_code=204)


@router.post(
    "/sale-returns/{document_id}/approve",
    dependencies=[Depends(require_module_access("erp", "erp:sale-return:approve"))],
    response_model=SaleReturnPublic,
)
def approve_sale_return(
    document_id: uuid.UUID, command: DocumentCommand, uow: ErpTenantUowDep, principal: CurrentPrincipal, idempotency_key: str = Header(alias="Idempotency-Key")
) -> SaleReturnPublic:
    claim = command_claim(uow=uow, command_name="erp.sale-return.approve", idempotency_key=idempotency_key, principal=principal, payload=command.model_dump(mode="json"), resource_id=document_id)
    if claim.replay:
        return replay_document(uow, claim, principal)
    document = uow.session.exec(select(SaleReturn).where(SaleReturn.id == document_id).with_for_update()).first()
    if document is None:
        raise HTTPException(status_code=404, detail="Sales return not found")
    assert_document_scope(uow=uow, principal=principal, document=document)
    if document.status != DocumentStatus.DRAFT or document.version != command.expected_version:
        raise HTTPException(status_code=409, detail="Sales return version conflict")
    shipment = uow.session.exec(select(SaleOut).where(SaleOut.id == document.sale_out_id).with_for_update()).first()
    order = uow.session.exec(select(SaleOrder).where(SaleOrder.id == document.sale_order_id).with_for_update()).first()
    if shipment is None or shipment.status != DocumentStatus.APPROVED or order is None:
        raise HTTPException(status_code=409, detail="Sales return source is unavailable")
    items = uow.session.exec(select(SaleReturnItem).where(SaleReturnItem.sale_return_id == document.id).order_by(SaleReturnItem.line_no)).all()
    shipment_items = uow.session.exec(
        select(SaleOutItem)
        .where(SaleOutItem.id.in_({item.sale_out_item_id for item in items}))
        .order_by(col(SaleOutItem.id))
        .with_for_update()
    ).all()
    shipment_items_by_id = {item.id: item for item in shipment_items}
    if len(shipment_items_by_id) != len(items):
        raise HTTPException(status_code=409, detail="Sales shipment line is unavailable")
    order_items = lock_sale_order_items(uow=uow, item_ids={item.sale_order_item_id for item in items})
    for item in items:
        shipment_item = shipment_items_by_id[item.sale_out_item_id]
        order_item = order_items[item.sale_order_item_id]
        if (
            shipment_item.sale_out_id != shipment.id
            or shipment_item.sale_order_item_id != order_item.id
            or item.quantity > shipment_item.quantity - shipment_item.returned_quantity
            or item.quantity > order_item.shipped_quantity - order_item.returned_quantity
        ):
            raise HTTPException(status_code=409, detail="Return quantity exceeds available shipped quantity")
    try:
        InventoryPostingService(uow).post(effects=return_effects(document, items), operator_id=principal.id)
    except InventoryConflictError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    for item in items:
        shipment_items_by_id[item.sale_out_item_id].returned_quantity += item.quantity
        order_items[item.sale_order_item_id].returned_quantity += item.quantity
        uow.session.add(shipment_items_by_id[item.sale_out_item_id])
        uow.session.add(order_items[item.sale_order_item_id])
    old_status, old_version = str(document.status), document.version
    set_approved(document=document, principal=principal)
    uow.session.add(document)
    enqueue_document_lifecycle_event(
        uow=uow, document=document, document_type="sale_return", action="approved"
    )
    record_action(uow=uow, resource_type="sale_return", resource_id=document.id, resource_no=document.no, action=DocumentAction.APPROVED, actor_id=principal.id, old_status=old_status, new_status=str(document.status), old_version=old_version, new_version=document.version)
    complete_command(receipt=claim.receipt, resource_type="sale_return", resource_id=document.id, resource_version=document.version)
    uow.session.commit()
    uow.session.refresh(document)
    return sale_return_public(uow, document)


@router.post(
    "/sale-returns/{document_id}/reverse",
    dependencies=[Depends(require_module_access("erp", "erp:sale-return:reverse"))],
    response_model=SaleReturnPublic,
)
def reverse_sale_return(
    document_id: uuid.UUID, command: DocumentReverseCommand, uow: ErpTenantUowDep, principal: CurrentPrincipal, idempotency_key: str = Header(alias="Idempotency-Key")
) -> SaleReturnPublic:
    claim = command_claim(uow=uow, command_name="erp.sale-return.reverse", idempotency_key=idempotency_key, principal=principal, payload=command.model_dump(mode="json"), resource_id=document_id)
    if claim.replay:
        return replay_document(uow, claim, principal)
    document = uow.session.exec(select(SaleReturn).where(SaleReturn.id == document_id).with_for_update()).first()
    if document is None:
        raise HTTPException(status_code=404, detail="Sales return not found")
    assert_document_scope(uow=uow, principal=principal, document=document)
    if document.status != DocumentStatus.APPROVED or document.version != command.expected_version:
        raise HTTPException(status_code=409, detail="Sales return version conflict")
    if has_approved_receipt(uow=uow, source_type=SettlementSourceType.SALE_RETURN, source_document_id=document.id):
        raise HTTPException(status_code=409, detail="Sales return has approved settlement documents")
    items = uow.session.exec(select(SaleReturnItem).where(SaleReturnItem.sale_return_id == document.id).order_by(SaleReturnItem.line_no)).all()
    shipment_items = uow.session.exec(
        select(SaleOutItem)
        .where(SaleOutItem.id.in_({item.sale_out_item_id for item in items}))
        .order_by(col(SaleOutItem.id))
        .with_for_update()
    ).all()
    shipment_items_by_id = {item.id: item for item in shipment_items}
    order_items = lock_sale_order_items(uow=uow, item_ids={item.sale_order_item_id for item in items})
    if any(
        shipment_items_by_id.get(item.sale_out_item_id) is None
        or shipment_items_by_id[item.sale_out_item_id].returned_quantity < item.quantity
        or order_items[item.sale_order_item_id].returned_quantity < item.quantity
        for item in items
    ):
        raise HTTPException(status_code=409, detail="Sales return quantity is inconsistent")
    ledgers = uow.session.exec(
        select(StockLedger).where(
            StockLedger.source_document_type == "sale_return",
            StockLedger.source_document_id == document.id,
            StockLedger.source_version == document.version,
            StockLedger.ledger_type == StockLedgerType.SALE_RETURN,
            StockLedger.reversal_of_id.is_(None),
        )
    ).all()
    if len(ledgers) != len(items):
        raise HTTPException(status_code=409, detail="Sales return has no reversible posting")
    try:
        InventoryPostingService(uow).post(
            effects=reversal_effects(document_id=document.id, document_no=document.no, document_type="sale_return", version=document.version, ledgers=ledgers),
            operator_id=principal.id,
            require_active_references=False,
        )
    except InventoryConflictError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    for item in items:
        shipment_items_by_id[item.sale_out_item_id].returned_quantity -= item.quantity
        order_items[item.sale_order_item_id].returned_quantity -= item.quantity
        uow.session.add(shipment_items_by_id[item.sale_out_item_id])
        uow.session.add(order_items[item.sale_order_item_id])
    old_status, old_version = str(document.status), document.version
    set_reversed(document=document, principal=principal)
    uow.session.add(document)
    enqueue_document_lifecycle_event(
        uow=uow, document=document, document_type="sale_return", action="reversed"
    )
    record_action(uow=uow, resource_type="sale_return", resource_id=document.id, resource_no=document.no, action=DocumentAction.REVERSED, actor_id=principal.id, old_status=old_status, new_status=str(document.status), old_version=old_version, new_version=document.version, reason=command.reason)
    complete_command(receipt=claim.receipt, resource_type="sale_return", resource_id=document.id, resource_version=document.version)
    uow.session.commit()
    uow.session.refresh(document)
    return sale_return_public(uow, document)
