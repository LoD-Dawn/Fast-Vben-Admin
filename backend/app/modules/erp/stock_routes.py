"""Inventory document and stock query HTTP contracts."""

import csv
import io
import uuid
from datetime import datetime
from decimal import Decimal
from typing import Any

from fastapi import APIRouter, Depends, Header, HTTPException, Response
from fastapi.responses import StreamingResponse
from sqlalchemy import or_
from sqlmodel import col, func, select

from app.core.clock import get_datetime_utc
from app.modules.erp.application.action_log import record_action
from app.modules.erp.application.business_time import resolve_business_at
from app.modules.erp.application.document_listing import stock_document_filters
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
from app.modules.erp.infrastructure.models import (
    Customer,
    DocumentAction,
    DocumentStatus,
    Product,
    ProductUnit,
    StockBalance,
    StockCheck,
    StockCheckItem,
    StockIn,
    StockInItem,
    StockLedger,
    StockLedgerType,
    StockMove,
    StockMoveItem,
    StockOut,
    StockOutItem,
    Supplier,
    Warehouse,
    WarehouseUserGrant,
)
from app.modules.erp.infrastructure.tenant_uow import ErpTenantUowDep
from app.modules.erp.observability import ErpDocumentCommandMetricRoute
from app.modules.erp.public_api.dto import (
    DocumentCommand,
    DocumentReverseCommand,
    StockBalancePublic,
    StockBalancesPublic,
    StockCheckCreate,
    StockCheckItemPublic,
    StockCheckPublic,
    StockChecksPublic,
    StockCheckUpdate,
    StockInCreate,
    StockInItemPublic,
    StockInPublic,
    StockInsPublic,
    StockInUpdate,
    StockLedgerPublic,
    StockLedgersPublic,
    StockMoveCreate,
    StockMoveItemPublic,
    StockMovePublic,
    StockMovesPublic,
    StockMoveUpdate,
    StockOutCreate,
    StockOutItemPublic,
    StockOutPublic,
    StockOutsPublic,
    StockOutUpdate,
)
from app.platform.web_api import (
    CurrentPrincipal,
    CurrentTenant,
    UserDirectoryDep,
    build_owner_data_scope_filter,
    normalize_pagination,
    require_module_access,
)

router = APIRouter(
    prefix="/erp", tags=["erp-stock"], route_class=ErpDocumentCommandMetricRoute
)
_MAX_EXPORT_ROWS = 100_000
_EXPORT_CHUNK_SIZE = 1_000


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
) -> StockInPublic | StockOutPublic | StockMovePublic | StockCheckPublic:
    if claim.receipt.resource_id is None:
        raise HTTPException(status_code=409, detail="Idempotency receipt is unavailable")
    if claim.receipt.resource_type == "stock_in":
        document = uow.session.get(StockIn, claim.receipt.resource_id)
        if document is not None:
            assert_stock_in_scope(
                uow=uow, current_principal=principal, document=document
            )
            return stock_in_public(uow, document)
    if claim.receipt.resource_type == "stock_out":
        document = uow.session.get(StockOut, claim.receipt.resource_id)
        if document is not None:
            assert_stock_out_scope(
                uow=uow, current_principal=principal, document=document
            )
            return stock_out_public(uow, document)
    if claim.receipt.resource_type == "stock_move":
        document = uow.session.get(StockMove, claim.receipt.resource_id)
        if document is not None:
            assert_stock_move_scope(
                uow=uow, current_principal=principal, document=document
            )
            return stock_move_public(uow, document)
    if claim.receipt.resource_type == "stock_check":
        document = uow.session.get(StockCheck, claim.receipt.resource_id)
        if document is not None:
            assert_stock_check_scope(
                uow=uow, current_principal=principal, document=document
            )
            return stock_check_public(uow, document)
    raise HTTPException(status_code=409, detail="Idempotency receipt document is unavailable")


def assert_active_counterparty(*, uow: ErpTenantUowDep, counterparty_id: uuid.UUID, model: Any) -> None:
    counterparty = uow.session.get(model, counterparty_id)
    if counterparty is None or not counterparty.is_active:
        raise HTTPException(status_code=422, detail="Counterparty is unavailable")


def document_scope_filter(
    *, uow: ErpTenantUowDep, current_principal: CurrentPrincipal, owner_column: Any
) -> Any:
    return build_owner_data_scope_filter(
        session=uow.session,
        current_principal=current_principal,
        tenant_id=uow.tenant_id,
        owner_id_column=owner_column,
    )


def stock_in_public(uow: ErpTenantUowDep, document: StockIn) -> StockInPublic:
    items = uow.session.exec(
        select(StockInItem)
        .where(StockInItem.stock_in_id == document.id)
        .order_by(StockInItem.line_no)
    ).all()
    return StockInPublic.model_validate(document).model_copy(
        update={"items": [StockInItemPublic.model_validate(item) for item in items]}
    )


def stock_out_public(uow: ErpTenantUowDep, document: StockOut) -> StockOutPublic:
    items = uow.session.exec(
        select(StockOutItem)
        .where(StockOutItem.stock_out_id == document.id)
        .order_by(StockOutItem.line_no)
    ).all()
    return StockOutPublic.model_validate(document).model_copy(
        update={"items": [StockOutItemPublic.model_validate(item) for item in items]}
    )


def assert_stock_in_scope(
    *,
    uow: ErpTenantUowDep,
    current_principal: CurrentPrincipal,
    document: StockIn,
) -> None:
    allowed = uow.session.exec(
        select(StockIn.id).where(
            StockIn.id == document.id,
            document_scope_filter(
                uow=uow,
                current_principal=current_principal,
                owner_column=StockIn.owner_id,
            ),
        )
    ).first()
    if allowed is None:
        raise HTTPException(status_code=403, detail="Not enough permissions")
    assert_warehouses_authorized(
        uow=uow,
        current_principal=current_principal,
        warehouse_ids=set(
            uow.session.exec(
                select(StockInItem.warehouse_id).where(StockInItem.stock_in_id == document.id)
            ).all()
        ),
    )


def assert_stock_out_scope(
    *,
    uow: ErpTenantUowDep,
    current_principal: CurrentPrincipal,
    document: StockOut,
) -> None:
    allowed = uow.session.exec(
        select(StockOut.id).where(
            StockOut.id == document.id,
            document_scope_filter(
                uow=uow,
                current_principal=current_principal,
                owner_column=StockOut.owner_id,
            ),
        )
    ).first()
    if allowed is None:
        raise HTTPException(status_code=403, detail="Not enough permissions")
    assert_warehouses_authorized(
        uow=uow,
        current_principal=current_principal,
        warehouse_ids=set(
            uow.session.exec(
                select(StockOutItem.warehouse_id).where(StockOutItem.stock_out_id == document.id)
            ).all()
        ),
    )


def stock_in_effects(document: StockIn, items: list[StockInItem]) -> tuple[InventoryEffect, ...]:
    source_version = document.version + 1
    return tuple(
        InventoryEffect(
            product_id=item.product_id,
            warehouse_id=item.warehouse_id,
            delta_quantity=item.quantity,
            ledger_type=StockLedgerType.OTHER_IN,
            source_document_type="stock_in",
            source_document_id=document.id,
            source_item_id=item.id,
            source_document_no=document.no,
            source_version=source_version,
        )
        for item in items
    )


def stock_out_effects(
    document: StockOut, items: list[StockOutItem]
) -> tuple[InventoryEffect, ...]:
    source_version = document.version + 1
    return tuple(
        InventoryEffect(
            product_id=item.product_id,
            warehouse_id=item.warehouse_id,
            delta_quantity=-item.quantity,
            ledger_type=StockLedgerType.OTHER_OUT,
            source_document_type="stock_out",
            source_document_id=document.id,
            source_item_id=item.id,
            source_document_no=document.no,
            source_version=source_version,
        )
        for item in items
    )


def reversal_effects(
    *, document_id: uuid.UUID, document_no: str, document_type: str, version: int, ledgers: list[StockLedger]
) -> tuple[InventoryEffect, ...]:
    reversal_type = {
        StockLedgerType.OTHER_IN: StockLedgerType.OTHER_IN_REVERSAL,
        StockLedgerType.OTHER_OUT: StockLedgerType.OTHER_OUT_REVERSAL,
        StockLedgerType.MOVE_IN: StockLedgerType.MOVE_IN_REVERSAL,
        StockLedgerType.MOVE_OUT: StockLedgerType.MOVE_OUT_REVERSAL,
        StockLedgerType.CHECK_GAIN: StockLedgerType.CHECK_GAIN_REVERSAL,
        StockLedgerType.CHECK_LOSS: StockLedgerType.CHECK_LOSS_REVERSAL,
    }
    return tuple(
        InventoryEffect(
            product_id=ledger.product_id,
            warehouse_id=ledger.warehouse_id,
            delta_quantity=-ledger.delta_quantity,
            ledger_type=reversal_type[ledger.ledger_type],
            source_document_type=document_type,
            source_document_id=document_id,
            source_item_id=ledger.source_item_id,
            source_document_no=document_no,
            source_version=version + 1,
            reversal_of_id=ledger.id,
        )
        for ledger in ledgers
    )


def raise_inventory_conflict(exc: InventoryConflictError) -> None:
    raise HTTPException(status_code=409, detail=str(exc)) from exc


def warehouse_scope_filter(
    *, current_principal: CurrentPrincipal, warehouse_column: Any
) -> Any | None:
    if current_principal.is_superuser:
        return None
    granted_warehouses = select(WarehouseUserGrant.warehouse_id).where(
        WarehouseUserGrant.user_id == current_principal.id
    )
    return warehouse_column.in_(granted_warehouses)


def warehouse_document_scope_filter(
    *,
    current_principal: CurrentPrincipal,
    document_id_column: Any,
    item_document_id_column: Any,
    item_id_column: Any,
    warehouse_columns: tuple[Any, ...],
) -> Any | None:
    """Require a grant for every warehouse touched by a listed document."""

    if current_principal.is_superuser:
        return None
    granted_warehouses = select(WarehouseUserGrant.warehouse_id).where(
        WarehouseUserGrant.user_id == current_principal.id
    )
    unauthorized_warehouse = or_(
        *(~warehouse_column.in_(granted_warehouses) for warehouse_column in warehouse_columns)
    )
    unauthorized_item = select(item_id_column).where(
        item_document_id_column == document_id_column,
        unauthorized_warehouse,
    )
    return ~unauthorized_item.exists()


def record_stock_export(
    *,
    uow: ErpTenantUowDep,
    current_principal: CurrentPrincipal,
    resource_type: str,
    exported_count: int,
    filters: dict[str, str | None],
) -> None:
    record_action(
        uow=uow,
        resource_type=resource_type,
        resource_id=uuid.uuid4(),
        action=DocumentAction.EXPORTED,
        actor_id=current_principal.id,
        metadata={
            "exported_count": exported_count,
            **filters,
        },
    )
    uow.session.commit()


def validate_time_range(
    *, occurred_from: datetime | None, occurred_to: datetime | None
) -> None:
    if occurred_from is not None and occurred_to is not None and occurred_from > occurred_to:
        raise HTTPException(status_code=422, detail="Start time must not be after end time")


def stock_balance_filters(
    *,
    current_principal: CurrentPrincipal,
    product_id: uuid.UUID | None,
    category_id: uuid.UUID | None,
    warehouse_id: uuid.UUID | None,
) -> list[Any]:
    filters: list[Any] = []
    if product_id is not None:
        filters.append(StockBalance.product_id == product_id)
    if category_id is not None:
        filters.append(
            StockBalance.product_id.in_(
                select(Product.id).where(Product.category_id == category_id)
            )
        )
    if warehouse_id is not None:
        filters.append(StockBalance.warehouse_id == warehouse_id)
    warehouse_scope = warehouse_scope_filter(
        current_principal=current_principal,
        warehouse_column=StockBalance.warehouse_id,
    )
    if warehouse_scope is not None:
        filters.append(warehouse_scope)
    return filters


def stock_ledger_filters(
    *,
    current_principal: CurrentPrincipal,
    product_id: uuid.UUID | None,
    category_id: uuid.UUID | None,
    warehouse_id: uuid.UUID | None,
    ledger_type: StockLedgerType | None,
    source_document_no: str | None,
    occurred_from: datetime | None,
    occurred_to: datetime | None,
) -> list[Any]:
    validate_time_range(occurred_from=occurred_from, occurred_to=occurred_to)
    filters: list[Any] = []
    if product_id is not None:
        filters.append(StockLedger.product_id == product_id)
    if category_id is not None:
        filters.append(
            StockLedger.product_id.in_(
                select(Product.id).where(Product.category_id == category_id)
            )
        )
    if warehouse_id is not None:
        filters.append(StockLedger.warehouse_id == warehouse_id)
    if ledger_type is not None:
        filters.append(StockLedger.ledger_type == ledger_type)
    if source_document_no:
        filters.append(StockLedger.source_document_no.ilike(f"%{source_document_no}%"))
    if occurred_from is not None:
        filters.append(StockLedger.occurred_at >= occurred_from)
    if occurred_to is not None:
        filters.append(StockLedger.occurred_at <= occurred_to)
    warehouse_scope = warehouse_scope_filter(
        current_principal=current_principal,
        warehouse_column=StockLedger.warehouse_id,
    )
    if warehouse_scope is not None:
        filters.append(warehouse_scope)
    return filters


def stock_public_values(
    *, uow: ErpTenantUowDep, product_ids: set[uuid.UUID], warehouse_ids: set[uuid.UUID]
) -> tuple[dict[uuid.UUID, Product], dict[uuid.UUID, ProductUnit], dict[uuid.UUID, Warehouse]]:
    products = {
        product.id: product
        for product in uow.session.exec(select(Product).where(Product.id.in_(product_ids))).all()
    }
    units = {
        unit.id: unit
        for unit in uow.session.exec(
            select(ProductUnit).where(ProductUnit.id.in_({product.unit_id for product in products.values()}))
        ).all()
    }
    warehouses = {
        warehouse.id: warehouse
        for warehouse in uow.session.exec(select(Warehouse).where(Warehouse.id.in_(warehouse_ids))).all()
    }
    return products, units, warehouses


def balance_publics(
    *, uow: ErpTenantUowDep, balances: list[StockBalance]
) -> list[StockBalancePublic]:
    products, units, warehouses = stock_public_values(
        uow=uow,
        product_ids={balance.product_id for balance in balances},
        warehouse_ids={balance.warehouse_id for balance in balances},
    )
    return [
        StockBalancePublic.model_validate(
            {
                **balance.model_dump(),
                "product_code": products[balance.product_id].code,
                "product_name": products[balance.product_id].name,
                "category_id": products[balance.product_id].category_id,
                "unit_name": units[products[balance.product_id].unit_id].name,
                "warehouse_name": warehouses[balance.warehouse_id].name,
            }
        )
        for balance in balances
    ]


def ledger_publics(
    *,
    uow: ErpTenantUowDep,
    user_directory: UserDirectoryDep,
    records: list[StockLedger],
) -> list[StockLedgerPublic]:
    products, units, warehouses = stock_public_values(
        uow=uow,
        product_ids={record.product_id for record in records},
        warehouse_ids={record.warehouse_id for record in records},
    )
    users = {
        user.id: user
        for user in user_directory.get_users({record.operator_id for record in records})
    }
    return [
        StockLedgerPublic.model_validate(
            {
                **record.model_dump(exclude={"ledger_type"}),
                "ledger_type": (
                    record.ledger_type.value
                    if isinstance(record.ledger_type, StockLedgerType)
                    else str(record.ledger_type)
                ),
                "product_code": products[record.product_id].code,
                "product_name": products[record.product_id].name,
                "category_id": products[record.product_id].category_id,
                "unit_name": units[products[record.product_id].unit_id].name,
                "warehouse_name": warehouses[record.warehouse_id].name,
                "operator_name": (
                    users[record.operator_id].full_name
                    or users[record.operator_id].email
                    if record.operator_id in users
                    else "已删除用户"
                ),
            }
        )
        for record in records
    ]


def csv_value(value: object) -> object:
    if value is None:
        return ""
    if isinstance(value, str) and value[:1] in {"=", "+", "-", "@"}:
        return f"'{value}"
    return value


def assert_warehouses_authorized(
    *, uow: ErpTenantUowDep, current_principal: CurrentPrincipal, warehouse_ids: set[uuid.UUID]
) -> None:
    if current_principal.is_superuser or not warehouse_ids:
        return
    granted = set(
        uow.session.exec(
            select(WarehouseUserGrant.warehouse_id).where(
                WarehouseUserGrant.user_id == current_principal.id,
                WarehouseUserGrant.warehouse_id.in_(warehouse_ids),
            )
        ).all()
    )
    if granted != warehouse_ids:
        raise HTTPException(status_code=403, detail="Not authorized for one or more warehouses")


@router.get(
    "/stock-balances",
    dependencies=[Depends(require_module_access("erp", "erp:stock:list"))],
    response_model=StockBalancesPublic,
)
def read_stock_balances(
    uow: ErpTenantUowDep,
    current_principal: CurrentPrincipal,
    page: int = 1,
    page_size: int = 20,
    product_id: uuid.UUID | None = None,
    category_id: uuid.UUID | None = None,
    warehouse_id: uuid.UUID | None = None,
) -> StockBalancesPublic:
    page, page_size = normalize_pagination(page=page, page_size=page_size)
    filters = stock_balance_filters(
        current_principal=current_principal,
        product_id=product_id,
        category_id=category_id,
        warehouse_id=warehouse_id,
    )
    total = int(
        uow.session.exec(
            select(func.count()).select_from(StockBalance).where(*filters)
        ).one()
    )
    balances = uow.session.exec(
        select(StockBalance)
        .where(*filters)
        .order_by(col(StockBalance.updated_at).desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
    ).all()
    return StockBalancesPublic(
        items=balance_publics(uow=uow, balances=balances),
        total=total,
        page=page,
        page_size=page_size,
    )


@router.get(
    "/stock-balances/export",
    dependencies=[Depends(require_module_access("erp", "erp:stock:export"))],
)
def export_stock_balances(
    uow: ErpTenantUowDep,
    current_principal: CurrentPrincipal,
    product_id: uuid.UUID | None = None,
    category_id: uuid.UUID | None = None,
    warehouse_id: uuid.UUID | None = None,
) -> StreamingResponse:
    filters = stock_balance_filters(
        current_principal=current_principal,
        product_id=product_id,
        category_id=category_id,
        warehouse_id=warehouse_id,
    )
    exported_count = int(
        uow.session.exec(
            select(func.count()).select_from(StockBalance).where(*filters)
        ).one()
    )
    if exported_count > _MAX_EXPORT_ROWS:
        raise HTTPException(status_code=422, detail="Export is limited to 100000 rows")
    record_stock_export(
        uow=uow,
        current_principal=current_principal,
        resource_type="stock_balance_export",
        exported_count=exported_count,
        filters={
            "product_id": str(product_id) if product_id else None,
            "category_id": str(category_id) if category_id else None,
            "warehouse_id": str(warehouse_id) if warehouse_id else None,
        },
    )
    def csv_rows() -> Any:
        output = io.StringIO()
        writer = csv.writer(output)
        writer.writerow(["商品编码", "商品名称", "单位", "仓库", "库存数量", "版本", "更新时间"])
        yield "\ufeff" + output.getvalue()
        rows = uow.session.exec(
            select(StockBalance).where(*filters).order_by(StockBalance.updated_at.desc())
        )
        for chunk in rows.yield_per(_EXPORT_CHUNK_SIZE).partitions(_EXPORT_CHUNK_SIZE):
            for balance in balance_publics(uow=uow, balances=list(chunk)):
                output = io.StringIO()
                csv.writer(output).writerow(
                    [
                        csv_value(balance.product_code),
                        csv_value(balance.product_name),
                        csv_value(balance.unit_name),
                        csv_value(balance.warehouse_name),
                        str(balance.quantity),
                        balance.version,
                        balance.updated_at.isoformat() if balance.updated_at else "",
                    ]
                )
                yield output.getvalue()
    return StreamingResponse(
        csv_rows(),
        media_type="text/csv",
        headers={"Content-Disposition": 'attachment; filename="stock-balances.csv"'},
    )


@router.get(
    "/stock-records",
    dependencies=[Depends(require_module_access("erp", "erp:stock-record:list"))],
    response_model=StockLedgersPublic,
)
def read_stock_records(
    uow: ErpTenantUowDep,
    current_principal: CurrentPrincipal,
    user_directory: UserDirectoryDep,
    page: int = 1,
    page_size: int = 20,
    product_id: uuid.UUID | None = None,
    category_id: uuid.UUID | None = None,
    warehouse_id: uuid.UUID | None = None,
    ledger_type: StockLedgerType | None = None,
    source_document_no: str | None = None,
    occurred_from: datetime | None = None,
    occurred_to: datetime | None = None,
) -> StockLedgersPublic:
    page, page_size = normalize_pagination(page=page, page_size=page_size)
    filters = stock_ledger_filters(
        current_principal=current_principal,
        product_id=product_id,
        category_id=category_id,
        warehouse_id=warehouse_id,
        ledger_type=ledger_type,
        source_document_no=source_document_no,
        occurred_from=occurred_from,
        occurred_to=occurred_to,
    )
    total = int(
        uow.session.exec(
            select(func.count()).select_from(StockLedger).where(*filters)
        ).one()
    )
    records = uow.session.exec(
        select(StockLedger)
        .where(*filters)
        .order_by(col(StockLedger.occurred_at).desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
    ).all()
    return StockLedgersPublic(
        items=ledger_publics(uow=uow, user_directory=user_directory, records=records),
        total=total,
        page=page,
        page_size=page_size,
    )


@router.get(
    "/stock-records/export",
    dependencies=[Depends(require_module_access("erp", "erp:stock-record:export"))],
)
def export_stock_records(
    uow: ErpTenantUowDep,
    current_principal: CurrentPrincipal,
    user_directory: UserDirectoryDep,
    product_id: uuid.UUID | None = None,
    category_id: uuid.UUID | None = None,
    warehouse_id: uuid.UUID | None = None,
    ledger_type: StockLedgerType | None = None,
    source_document_no: str | None = None,
    occurred_from: datetime | None = None,
    occurred_to: datetime | None = None,
) -> StreamingResponse:
    filters = stock_ledger_filters(
        current_principal=current_principal,
        product_id=product_id,
        category_id=category_id,
        warehouse_id=warehouse_id,
        ledger_type=ledger_type,
        source_document_no=source_document_no,
        occurred_from=occurred_from,
        occurred_to=occurred_to,
    )
    exported_count = int(
        uow.session.exec(
            select(func.count()).select_from(StockLedger).where(*filters)
        ).one()
    )
    if exported_count > _MAX_EXPORT_ROWS:
        raise HTTPException(status_code=422, detail="Export is limited to 100000 rows")
    record_stock_export(
        uow=uow,
        current_principal=current_principal,
        resource_type="stock_ledger_export",
        exported_count=exported_count,
        filters={
            "product_id": str(product_id) if product_id else None,
            "category_id": str(category_id) if category_id else None,
            "warehouse_id": str(warehouse_id) if warehouse_id else None,
            "ledger_type": ledger_type.value if ledger_type else None,
            "source_document_no": source_document_no,
            "occurred_from": occurred_from.isoformat() if occurred_from else None,
            "occurred_to": occurred_to.isoformat() if occurred_to else None,
        },
    )
    def csv_rows() -> Any:
        output = io.StringIO()
        writer = csv.writer(output)
        writer.writerow(
            [
                "发生时间",
                "业务类型",
                "商品编码",
                "商品名称",
                "单位",
                "仓库",
                "变动数量",
                "结存数量",
                "来源单号",
                "来源单据类型",
                "来源单据 ID",
                "操作人",
            ]
        )
        yield "\ufeff" + output.getvalue()
        rows = uow.session.exec(
            select(StockLedger).where(*filters).order_by(StockLedger.occurred_at.desc())
        )
        for chunk in rows.yield_per(_EXPORT_CHUNK_SIZE).partitions(_EXPORT_CHUNK_SIZE):
            for record in ledger_publics(
                uow=uow, user_directory=user_directory, records=list(chunk)
            ):
                output = io.StringIO()
                csv.writer(output).writerow(
                    [
                        record.occurred_at.isoformat() if record.occurred_at else "",
                        csv_value(record.ledger_type),
                        csv_value(record.product_code),
                        csv_value(record.product_name),
                        csv_value(record.unit_name),
                        csv_value(record.warehouse_name),
                        str(record.delta_quantity),
                        str(record.balance_after),
                        record.source_document_no,
                        record.source_document_type,
                        str(record.source_document_id),
                        csv_value(record.operator_name),
                    ]
                )
                yield output.getvalue()
    return StreamingResponse(
        csv_rows(),
        media_type="text/csv",
        headers={"Content-Disposition": 'attachment; filename="stock-records.csv"'},
    )


@router.get(
    "/stock-ins",
    dependencies=[Depends(require_module_access("erp", "erp:stock-in:list"))],
    response_model=StockInsPublic,
)
def read_stock_ins(
    uow: ErpTenantUowDep,
    current_principal: CurrentPrincipal,
    page: int = 1,
    page_size: int = 20,
    keyword: str | None = None,
    product_id: uuid.UUID | None = None,
    warehouse_id: uuid.UUID | None = None,
    owner_id: uuid.UUID | None = None,
    status: str | None = None,
    remark: str | None = None,
    business_from: datetime | None = None,
    business_to: datetime | None = None,
) -> StockInsPublic:
    page, page_size = normalize_pagination(page=page, page_size=page_size)
    scope = document_scope_filter(
        uow=uow, current_principal=current_principal, owner_column=StockIn.owner_id
    )
    warehouse_scope = warehouse_document_scope_filter(
        current_principal=current_principal,
        document_id_column=StockIn.id,
        item_document_id_column=StockInItem.stock_in_id,
        item_id_column=StockInItem.id,
        warehouse_columns=(StockInItem.warehouse_id,),
    )
    if warehouse_scope is not None:
        scope = scope & warehouse_scope
    try:
        filters = stock_document_filters(
            model=StockIn,
            item_document_column=StockInItem.stock_in_id,
            item_product_column=StockInItem.product_id,
            item_warehouse_columns=(StockInItem.warehouse_id,),
            product_model=Product,
            scope=scope,
            keyword=keyword,
            product_id=product_id,
            warehouse_id=warehouse_id,
            owner_id=owner_id,
            status=status,
            remark=remark,
            business_from=business_from,
            business_to=business_to,
        )
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    total = int(
        uow.session.exec(select(func.count()).select_from(StockIn).where(*filters)).one()
    )
    documents = uow.session.exec(
        select(StockIn)
        .where(*filters)
        .order_by(col(StockIn.business_at).desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
    ).all()
    return StockInsPublic(
        items=[stock_in_public(uow, document) for document in documents],
        total=total,
        page=page,
        page_size=page_size,
    )


@router.post(
    "/stock-ins",
    dependencies=[Depends(require_module_access("erp", "erp:stock-in:create"))],
    response_model=StockInPublic,
)
def create_stock_in(
    stock_in: StockInCreate,
    uow: ErpTenantUowDep,
    current_principal: CurrentPrincipal,
    tenant_context: CurrentTenant,
    idempotency_key: str = Header(alias="Idempotency-Key"),
) -> StockInPublic:
    claim = command_claim(uow=uow, command_name="erp.stock-in.create", idempotency_key=idempotency_key, principal=current_principal, payload=stock_in.model_dump(mode="json"))
    if claim.replay:
        return replay_document(uow, claim, current_principal)
    if stock_in.supplier_id is not None:
        assert_active_counterparty(uow=uow, counterparty_id=stock_in.supplier_id, model=Supplier)
    assert_warehouses_authorized(
        uow=uow,
        current_principal=current_principal,
        warehouse_ids={item.warehouse_id for item in stock_in.items},
    )
    document = StockIn(
        tenant_id=tenant_context.tenant_id,
        no=allocate_document_no(uow=uow, prefix="QTRK"),
        business_at=resolve_business_at(uow=uow, requested_at=stock_in.business_at),
        owner_id=current_principal.id,
        supplier_id=stock_in.supplier_id,
        total_quantity=sum((item.quantity for item in stock_in.items), Decimal("0")),
        total_amount=sum((item.quantity * item.reference_price for item in stock_in.items), Decimal("0")),
        remark=stock_in.remark,
        created_by=current_principal.id,
        updated_by=current_principal.id,
    )
    uow.session.add(document)
    uow.session.flush()
    uow.session.add_all(
        [
            StockInItem(
                tenant_id=tenant_context.tenant_id,
                stock_in_id=document.id,
                line_no=index,
                product_id=item.product_id,
                warehouse_id=item.warehouse_id,
                quantity=item.quantity,
                reference_price=item.reference_price,
                remark=item.remark,
            )
            for index, item in enumerate(stock_in.items, start=1)
        ]
    )
    record_action(uow=uow, resource_type="stock_in", resource_id=document.id, resource_no=document.no, action=DocumentAction.CREATED, actor_id=current_principal.id, new_status=str(document.status), new_version=document.version, metadata={"item_count": len(stock_in.items)})
    complete_command(receipt=claim.receipt, resource_type="stock_in", resource_id=document.id, resource_version=document.version)
    uow.session.commit()
    uow.session.refresh(document)
    return stock_in_public(uow, document)


@router.get(
    "/stock-ins/{document_id}",
    dependencies=[Depends(require_module_access("erp", "erp:stock-in:list"))],
    response_model=StockInPublic,
)
def read_stock_in(
    document_id: uuid.UUID, uow: ErpTenantUowDep, current_principal: CurrentPrincipal
) -> StockInPublic:
    document = uow.session.get(StockIn, document_id)
    if document is None:
        raise HTTPException(status_code=404, detail="Stock in document not found")
    assert_stock_in_scope(uow=uow, current_principal=current_principal, document=document)
    return stock_in_public(uow, document)


@router.patch(
    "/stock-ins/{document_id}",
    dependencies=[Depends(require_module_access("erp", "erp:stock-in:update"))],
    response_model=StockInPublic,
)
def update_stock_in(
    document_id: uuid.UUID,
    command: StockInUpdate,
    uow: ErpTenantUowDep,
    current_principal: CurrentPrincipal,
) -> StockInPublic:
    document = uow.session.exec(select(StockIn).where(StockIn.id == document_id).with_for_update()).first()
    if document is None:
        raise HTTPException(status_code=404, detail="Stock in document not found")
    assert_stock_in_scope(uow=uow, current_principal=current_principal, document=document)
    if document.status != DocumentStatus.DRAFT or document.version != command.expected_version:
        raise HTTPException(status_code=409, detail="Stock document version conflict")
    if command.supplier_id is not None:
        assert_active_counterparty(uow=uow, counterparty_id=command.supplier_id, model=Supplier)
    assert_warehouses_authorized(uow=uow, current_principal=current_principal, warehouse_ids={item.warehouse_id for item in command.items})
    old_version = document.version
    for item in uow.session.exec(select(StockInItem).where(StockInItem.stock_in_id == document.id)).all():
        uow.session.delete(item)
    uow.session.flush()
    document.supplier_id = command.supplier_id
    document.business_at = resolve_business_at(uow=uow, requested_at=command.business_at) if command.business_at is not None else document.business_at
    document.total_quantity = sum((item.quantity for item in command.items), Decimal("0"))
    document.total_amount = sum((item.quantity * item.reference_price for item in command.items), Decimal("0"))
    document.remark = command.remark
    document.version += 1
    document.updated_by = current_principal.id
    document.updated_at = get_datetime_utc()
    uow.session.add(document)
    uow.session.add_all([StockInItem(tenant_id=uow.tenant_id, stock_in_id=document.id, line_no=index, product_id=item.product_id, warehouse_id=item.warehouse_id, quantity=item.quantity, reference_price=item.reference_price, remark=item.remark) for index, item in enumerate(command.items, start=1)])
    record_action(uow=uow, resource_type="stock_in", resource_id=document.id, resource_no=document.no, action=DocumentAction.UPDATED, actor_id=current_principal.id, old_version=old_version, new_version=document.version, metadata={"item_count": len(command.items)})
    uow.session.commit()
    uow.session.refresh(document)
    return stock_in_public(uow, document)


@router.delete(
    "/stock-ins/{document_id}",
    dependencies=[Depends(require_module_access("erp", "erp:stock-in:delete"))],
    status_code=204,
)
def delete_stock_in(document_id: uuid.UUID, uow: ErpTenantUowDep, current_principal: CurrentPrincipal) -> Response:
    document = uow.session.exec(select(StockIn).where(StockIn.id == document_id).with_for_update()).first()
    if document is None:
        raise HTTPException(status_code=404, detail="Stock in document not found")
    assert_stock_in_scope(uow=uow, current_principal=current_principal, document=document)
    if document.status != DocumentStatus.DRAFT:
        raise HTTPException(status_code=409, detail="Stock in document must be draft before deletion")
    record_action(uow=uow, resource_type="stock_in", resource_id=document.id, resource_no=document.no, action=DocumentAction.DELETED, actor_id=current_principal.id, old_status=str(document.status), old_version=document.version)
    uow.session.delete(document)
    uow.session.commit()
    return Response(status_code=204)


@router.post(
    "/stock-ins/{document_id}/approve",
    dependencies=[Depends(require_module_access("erp", "erp:stock-in:approve"))],
    response_model=StockInPublic,
)
def approve_stock_in(
    document_id: uuid.UUID,
    command: DocumentCommand,
    uow: ErpTenantUowDep,
    current_principal: CurrentPrincipal,
    idempotency_key: str = Header(alias="Idempotency-Key"),
) -> StockInPublic:
    claim = command_claim(uow=uow, command_name="erp.stock-in.approve", idempotency_key=idempotency_key, principal=current_principal, payload=command.model_dump(mode="json"), resource_id=document_id)
    if claim.replay:
        return replay_document(uow, claim, current_principal)
    document = uow.session.exec(
        select(StockIn).where(StockIn.id == document_id).with_for_update()
    ).first()
    if document is None:
        raise HTTPException(status_code=404, detail="Stock in document not found")
    assert_stock_in_scope(uow=uow, current_principal=current_principal, document=document)
    if document.status != DocumentStatus.DRAFT or document.version != command.expected_version:
        raise HTTPException(status_code=409, detail="Stock document version conflict")
    items = uow.session.exec(
        select(StockInItem)
        .where(StockInItem.stock_in_id == document.id)
        .order_by(StockInItem.line_no)
    ).all()
    try:
        InventoryPostingService(uow).post(
            effects=stock_in_effects(document, items), operator_id=current_principal.id
        )
    except InventoryConflictError as exc:
        raise_inventory_conflict(exc)
    old_status, old_version = str(document.status), document.version
    document.status = DocumentStatus.APPROVED
    document.version += 1
    document.approved_by = current_principal.id
    document.approved_at = get_datetime_utc()
    document.updated_by = current_principal.id
    document.updated_at = get_datetime_utc()
    uow.session.add(document)
    enqueue_document_lifecycle_event(
        uow=uow, document=document, document_type="stock_in", action="approved"
    )
    record_action(uow=uow, resource_type="stock_in", resource_id=document.id, resource_no=document.no, action=DocumentAction.APPROVED, actor_id=current_principal.id, old_status=old_status, new_status=str(document.status), old_version=old_version, new_version=document.version)
    complete_command(receipt=claim.receipt, resource_type="stock_in", resource_id=document.id, resource_version=document.version)
    uow.session.commit()
    uow.session.refresh(document)
    return stock_in_public(uow, document)


@router.post(
    "/stock-ins/{document_id}/reverse",
    dependencies=[Depends(require_module_access("erp", "erp:stock-in:reverse"))],
    response_model=StockInPublic,
)
def reverse_stock_in(
    document_id: uuid.UUID,
    command: DocumentReverseCommand,
    uow: ErpTenantUowDep,
    current_principal: CurrentPrincipal,
    idempotency_key: str = Header(alias="Idempotency-Key"),
) -> StockInPublic:
    claim = command_claim(uow=uow, command_name="erp.stock-in.reverse", idempotency_key=idempotency_key, principal=current_principal, payload=command.model_dump(mode="json"), resource_id=document_id)
    if claim.replay:
        return replay_document(uow, claim, current_principal)
    document = uow.session.exec(
        select(StockIn).where(StockIn.id == document_id).with_for_update()
    ).first()
    if document is None:
        raise HTTPException(status_code=404, detail="Stock in document not found")
    assert_stock_in_scope(uow=uow, current_principal=current_principal, document=document)
    if document.status != DocumentStatus.APPROVED or document.version != command.expected_version:
        raise HTTPException(status_code=409, detail="Stock document version conflict")
    ledgers = uow.session.exec(
        select(StockLedger).where(
            StockLedger.source_document_type == "stock_in",
            StockLedger.source_document_id == document.id,
            StockLedger.source_version == document.version,
            StockLedger.reversal_of_id.is_(None),
        )
    ).all()
    if not ledgers:
        raise HTTPException(status_code=409, detail="Stock document has no reversible posting")
    try:
        InventoryPostingService(uow).post(
            effects=reversal_effects(
                document_id=document.id,
                document_no=document.no,
                document_type="stock_in",
                version=document.version,
                ledgers=ledgers,
            ),
            operator_id=current_principal.id,
            require_active_references=False,
        )
    except InventoryConflictError as exc:
        raise_inventory_conflict(exc)
    old_status, old_version = str(document.status), document.version
    document.status = DocumentStatus.DRAFT
    document.version += 1
    document.reversed_by = current_principal.id
    document.reversed_at = get_datetime_utc()
    document.updated_by = current_principal.id
    document.updated_at = get_datetime_utc()
    uow.session.add(document)
    enqueue_document_lifecycle_event(
        uow=uow, document=document, document_type="stock_in", action="reversed"
    )
    record_action(uow=uow, resource_type="stock_in", resource_id=document.id, resource_no=document.no, action=DocumentAction.REVERSED, actor_id=current_principal.id, old_status=old_status, new_status=str(document.status), old_version=old_version, new_version=document.version, reason=command.reason)
    complete_command(receipt=claim.receipt, resource_type="stock_in", resource_id=document.id, resource_version=document.version)
    uow.session.commit()
    uow.session.refresh(document)
    return stock_in_public(uow, document)


@router.get(
    "/stock-outs",
    dependencies=[Depends(require_module_access("erp", "erp:stock-out:list"))],
    response_model=StockOutsPublic,
)
def read_stock_outs(
    uow: ErpTenantUowDep,
    current_principal: CurrentPrincipal,
    page: int = 1,
    page_size: int = 20,
    keyword: str | None = None,
    product_id: uuid.UUID | None = None,
    warehouse_id: uuid.UUID | None = None,
    owner_id: uuid.UUID | None = None,
    status: str | None = None,
    remark: str | None = None,
    business_from: datetime | None = None,
    business_to: datetime | None = None,
) -> StockOutsPublic:
    page, page_size = normalize_pagination(page=page, page_size=page_size)
    scope = document_scope_filter(
        uow=uow, current_principal=current_principal, owner_column=StockOut.owner_id
    )
    warehouse_scope = warehouse_document_scope_filter(
        current_principal=current_principal,
        document_id_column=StockOut.id,
        item_document_id_column=StockOutItem.stock_out_id,
        item_id_column=StockOutItem.id,
        warehouse_columns=(StockOutItem.warehouse_id,),
    )
    if warehouse_scope is not None:
        scope = scope & warehouse_scope
    try:
        filters = stock_document_filters(
            model=StockOut,
            item_document_column=StockOutItem.stock_out_id,
            item_product_column=StockOutItem.product_id,
            item_warehouse_columns=(StockOutItem.warehouse_id,),
            product_model=Product,
            scope=scope,
            keyword=keyword,
            product_id=product_id,
            warehouse_id=warehouse_id,
            owner_id=owner_id,
            status=status,
            remark=remark,
            business_from=business_from,
            business_to=business_to,
        )
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    total = int(
        uow.session.exec(select(func.count()).select_from(StockOut).where(*filters)).one()
    )
    documents = uow.session.exec(
        select(StockOut)
        .where(*filters)
        .order_by(col(StockOut.business_at).desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
    ).all()
    return StockOutsPublic(
        items=[stock_out_public(uow, document) for document in documents],
        total=total,
        page=page,
        page_size=page_size,
    )


@router.post(
    "/stock-outs",
    dependencies=[Depends(require_module_access("erp", "erp:stock-out:create"))],
    response_model=StockOutPublic,
)
def create_stock_out(
    stock_out: StockOutCreate,
    uow: ErpTenantUowDep,
    current_principal: CurrentPrincipal,
    tenant_context: CurrentTenant,
    idempotency_key: str = Header(alias="Idempotency-Key"),
) -> StockOutPublic:
    claim = command_claim(uow=uow, command_name="erp.stock-out.create", idempotency_key=idempotency_key, principal=current_principal, payload=stock_out.model_dump(mode="json"))
    if claim.replay:
        return replay_document(uow, claim, current_principal)
    if stock_out.customer_id is not None:
        assert_active_counterparty(uow=uow, counterparty_id=stock_out.customer_id, model=Customer)
    assert_warehouses_authorized(
        uow=uow,
        current_principal=current_principal,
        warehouse_ids={item.warehouse_id for item in stock_out.items},
    )
    document = StockOut(
        tenant_id=tenant_context.tenant_id,
        no=allocate_document_no(uow=uow, prefix="QTCK"),
        business_at=resolve_business_at(uow=uow, requested_at=stock_out.business_at),
        owner_id=current_principal.id,
        customer_id=stock_out.customer_id,
        total_quantity=sum((item.quantity for item in stock_out.items), Decimal("0")),
        total_amount=sum((item.quantity * item.reference_price for item in stock_out.items), Decimal("0")),
        remark=stock_out.remark,
        created_by=current_principal.id,
        updated_by=current_principal.id,
    )
    uow.session.add(document)
    uow.session.flush()
    uow.session.add_all(
        [
            StockOutItem(
                tenant_id=tenant_context.tenant_id,
                stock_out_id=document.id,
                line_no=index,
                product_id=item.product_id,
                warehouse_id=item.warehouse_id,
                quantity=item.quantity,
                reference_price=item.reference_price,
                remark=item.remark,
            )
            for index, item in enumerate(stock_out.items, start=1)
        ]
    )
    record_action(uow=uow, resource_type="stock_out", resource_id=document.id, resource_no=document.no, action=DocumentAction.CREATED, actor_id=current_principal.id, new_status=str(document.status), new_version=document.version, metadata={"item_count": len(stock_out.items)})
    complete_command(receipt=claim.receipt, resource_type="stock_out", resource_id=document.id, resource_version=document.version)
    uow.session.commit()
    uow.session.refresh(document)
    return stock_out_public(uow, document)


@router.get(
    "/stock-outs/{document_id}",
    dependencies=[Depends(require_module_access("erp", "erp:stock-out:list"))],
    response_model=StockOutPublic,
)
def read_stock_out(
    document_id: uuid.UUID, uow: ErpTenantUowDep, current_principal: CurrentPrincipal
) -> StockOutPublic:
    document = uow.session.get(StockOut, document_id)
    if document is None:
        raise HTTPException(status_code=404, detail="Stock out document not found")
    assert_stock_out_scope(uow=uow, current_principal=current_principal, document=document)
    return stock_out_public(uow, document)


@router.patch(
    "/stock-outs/{document_id}",
    dependencies=[Depends(require_module_access("erp", "erp:stock-out:update"))],
    response_model=StockOutPublic,
)
def update_stock_out(document_id: uuid.UUID, command: StockOutUpdate, uow: ErpTenantUowDep, current_principal: CurrentPrincipal) -> StockOutPublic:
    document = uow.session.exec(select(StockOut).where(StockOut.id == document_id).with_for_update()).first()
    if document is None:
        raise HTTPException(status_code=404, detail="Stock out document not found")
    assert_stock_out_scope(uow=uow, current_principal=current_principal, document=document)
    if document.status != DocumentStatus.DRAFT or document.version != command.expected_version:
        raise HTTPException(status_code=409, detail="Stock document version conflict")
    if command.customer_id is not None:
        assert_active_counterparty(uow=uow, counterparty_id=command.customer_id, model=Customer)
    assert_warehouses_authorized(uow=uow, current_principal=current_principal, warehouse_ids={item.warehouse_id for item in command.items})
    old_version = document.version
    for item in uow.session.exec(select(StockOutItem).where(StockOutItem.stock_out_id == document.id)).all():
        uow.session.delete(item)
    uow.session.flush()
    document.customer_id = command.customer_id
    document.business_at = resolve_business_at(uow=uow, requested_at=command.business_at) if command.business_at is not None else document.business_at
    document.total_quantity = sum((item.quantity for item in command.items), Decimal("0"))
    document.total_amount = sum((item.quantity * item.reference_price for item in command.items), Decimal("0"))
    document.remark = command.remark
    document.version += 1
    document.updated_by = current_principal.id
    document.updated_at = get_datetime_utc()
    uow.session.add(document)
    uow.session.add_all([StockOutItem(tenant_id=uow.tenant_id, stock_out_id=document.id, line_no=index, product_id=item.product_id, warehouse_id=item.warehouse_id, quantity=item.quantity, reference_price=item.reference_price, remark=item.remark) for index, item in enumerate(command.items, start=1)])
    record_action(uow=uow, resource_type="stock_out", resource_id=document.id, resource_no=document.no, action=DocumentAction.UPDATED, actor_id=current_principal.id, old_version=old_version, new_version=document.version, metadata={"item_count": len(command.items)})
    uow.session.commit()
    uow.session.refresh(document)
    return stock_out_public(uow, document)


@router.delete(
    "/stock-outs/{document_id}",
    dependencies=[Depends(require_module_access("erp", "erp:stock-out:delete"))],
    status_code=204,
)
def delete_stock_out(document_id: uuid.UUID, uow: ErpTenantUowDep, current_principal: CurrentPrincipal) -> Response:
    document = uow.session.exec(select(StockOut).where(StockOut.id == document_id).with_for_update()).first()
    if document is None:
        raise HTTPException(status_code=404, detail="Stock out document not found")
    assert_stock_out_scope(uow=uow, current_principal=current_principal, document=document)
    if document.status != DocumentStatus.DRAFT:
        raise HTTPException(status_code=409, detail="Stock out document must be draft before deletion")
    record_action(uow=uow, resource_type="stock_out", resource_id=document.id, resource_no=document.no, action=DocumentAction.DELETED, actor_id=current_principal.id, old_status=str(document.status), old_version=document.version)
    uow.session.delete(document)
    uow.session.commit()
    return Response(status_code=204)


@router.post(
    "/stock-outs/{document_id}/approve",
    dependencies=[Depends(require_module_access("erp", "erp:stock-out:approve"))],
    response_model=StockOutPublic,
)
def approve_stock_out(
    document_id: uuid.UUID,
    command: DocumentCommand,
    uow: ErpTenantUowDep,
    current_principal: CurrentPrincipal,
    idempotency_key: str = Header(alias="Idempotency-Key"),
) -> StockOutPublic:
    claim = command_claim(uow=uow, command_name="erp.stock-out.approve", idempotency_key=idempotency_key, principal=current_principal, payload=command.model_dump(mode="json"), resource_id=document_id)
    if claim.replay:
        return replay_document(uow, claim, current_principal)
    document = uow.session.exec(
        select(StockOut).where(StockOut.id == document_id).with_for_update()
    ).first()
    if document is None:
        raise HTTPException(status_code=404, detail="Stock out document not found")
    assert_stock_out_scope(uow=uow, current_principal=current_principal, document=document)
    if document.status != DocumentStatus.DRAFT or document.version != command.expected_version:
        raise HTTPException(status_code=409, detail="Stock document version conflict")
    items = uow.session.exec(
        select(StockOutItem)
        .where(StockOutItem.stock_out_id == document.id)
        .order_by(StockOutItem.line_no)
    ).all()
    try:
        InventoryPostingService(uow).post(
            effects=stock_out_effects(document, items), operator_id=current_principal.id
        )
    except InventoryConflictError as exc:
        raise_inventory_conflict(exc)
    old_status, old_version = str(document.status), document.version
    document.status = DocumentStatus.APPROVED
    document.version += 1
    document.approved_by = current_principal.id
    document.approved_at = get_datetime_utc()
    document.updated_by = current_principal.id
    document.updated_at = get_datetime_utc()
    uow.session.add(document)
    enqueue_document_lifecycle_event(
        uow=uow, document=document, document_type="stock_out", action="approved"
    )
    record_action(uow=uow, resource_type="stock_out", resource_id=document.id, resource_no=document.no, action=DocumentAction.APPROVED, actor_id=current_principal.id, old_status=old_status, new_status=str(document.status), old_version=old_version, new_version=document.version)
    complete_command(receipt=claim.receipt, resource_type="stock_out", resource_id=document.id, resource_version=document.version)
    uow.session.commit()
    uow.session.refresh(document)
    return stock_out_public(uow, document)


@router.post(
    "/stock-outs/{document_id}/reverse",
    dependencies=[Depends(require_module_access("erp", "erp:stock-out:reverse"))],
    response_model=StockOutPublic,
)
def reverse_stock_out(
    document_id: uuid.UUID,
    command: DocumentReverseCommand,
    uow: ErpTenantUowDep,
    current_principal: CurrentPrincipal,
    idempotency_key: str = Header(alias="Idempotency-Key"),
) -> StockOutPublic:
    claim = command_claim(uow=uow, command_name="erp.stock-out.reverse", idempotency_key=idempotency_key, principal=current_principal, payload=command.model_dump(mode="json"), resource_id=document_id)
    if claim.replay:
        return replay_document(uow, claim, current_principal)
    document = uow.session.exec(
        select(StockOut).where(StockOut.id == document_id).with_for_update()
    ).first()
    if document is None:
        raise HTTPException(status_code=404, detail="Stock out document not found")
    assert_stock_out_scope(uow=uow, current_principal=current_principal, document=document)
    if document.status != DocumentStatus.APPROVED or document.version != command.expected_version:
        raise HTTPException(status_code=409, detail="Stock document version conflict")
    ledgers = uow.session.exec(
        select(StockLedger).where(
            StockLedger.source_document_type == "stock_out",
            StockLedger.source_document_id == document.id,
            StockLedger.source_version == document.version,
            StockLedger.reversal_of_id.is_(None),
        )
    ).all()
    if not ledgers:
        raise HTTPException(status_code=409, detail="Stock document has no reversible posting")
    try:
        InventoryPostingService(uow).post(
            effects=reversal_effects(
                document_id=document.id,
                document_no=document.no,
                document_type="stock_out",
                version=document.version,
                ledgers=ledgers,
            ),
            operator_id=current_principal.id,
            require_active_references=False,
        )
    except InventoryConflictError as exc:
        raise_inventory_conflict(exc)
    old_status, old_version = str(document.status), document.version
    document.status = DocumentStatus.DRAFT
    document.version += 1
    document.reversed_by = current_principal.id
    document.reversed_at = get_datetime_utc()
    document.updated_by = current_principal.id
    document.updated_at = get_datetime_utc()
    uow.session.add(document)
    enqueue_document_lifecycle_event(
        uow=uow, document=document, document_type="stock_out", action="reversed"
    )
    record_action(uow=uow, resource_type="stock_out", resource_id=document.id, resource_no=document.no, action=DocumentAction.REVERSED, actor_id=current_principal.id, old_status=old_status, new_status=str(document.status), old_version=old_version, new_version=document.version, reason=command.reason)
    complete_command(receipt=claim.receipt, resource_type="stock_out", resource_id=document.id, resource_version=document.version)
    uow.session.commit()
    uow.session.refresh(document)
    return stock_out_public(uow, document)


def stock_move_public(uow: ErpTenantUowDep, document: StockMove) -> StockMovePublic:
    items = uow.session.exec(
        select(StockMoveItem)
        .where(StockMoveItem.stock_move_id == document.id)
        .order_by(StockMoveItem.line_no)
    ).all()
    return StockMovePublic.model_validate(document).model_copy(
        update={"items": [StockMoveItemPublic.model_validate(item) for item in items]}
    )


def assert_stock_move_scope(
    *,
    uow: ErpTenantUowDep,
    current_principal: CurrentPrincipal,
    document: StockMove,
) -> None:
    allowed = uow.session.exec(
        select(StockMove.id).where(
            StockMove.id == document.id,
            document_scope_filter(
                uow=uow,
                current_principal=current_principal,
                owner_column=StockMove.owner_id,
            ),
        )
    ).first()
    if allowed is None:
        raise HTTPException(status_code=403, detail="Not enough permissions")
    items = uow.session.exec(
        select(StockMoveItem).where(StockMoveItem.stock_move_id == document.id)
    ).all()
    assert_warehouses_authorized(
        uow=uow,
        current_principal=current_principal,
        warehouse_ids={
            warehouse_id
            for item in items
            for warehouse_id in (item.from_warehouse_id, item.to_warehouse_id)
        },
    )


def stock_move_effects(
    document: StockMove, items: list[StockMoveItem]
) -> tuple[InventoryEffect, ...]:
    source_version = document.version + 1
    effects: list[InventoryEffect] = []
    for item in items:
        effects.extend(
            (
                InventoryEffect(
                    product_id=item.product_id,
                    warehouse_id=item.from_warehouse_id,
                    delta_quantity=-item.quantity,
                    ledger_type=StockLedgerType.MOVE_OUT,
                    source_document_type="stock_move",
                    source_document_id=document.id,
                    source_item_id=item.id,
                    source_document_no=document.no,
                    source_version=source_version,
                ),
                InventoryEffect(
                    product_id=item.product_id,
                    warehouse_id=item.to_warehouse_id,
                    delta_quantity=item.quantity,
                    ledger_type=StockLedgerType.MOVE_IN,
                    source_document_type="stock_move",
                    source_document_id=document.id,
                    source_item_id=item.id,
                    source_document_no=document.no,
                    source_version=source_version,
                ),
            )
        )
    return tuple(effects)


@router.get(
    "/stock-moves",
    dependencies=[Depends(require_module_access("erp", "erp:stock-move:list"))],
    response_model=StockMovesPublic,
)
def read_stock_moves(
    uow: ErpTenantUowDep,
    current_principal: CurrentPrincipal,
    page: int = 1,
    page_size: int = 20,
    keyword: str | None = None,
    product_id: uuid.UUID | None = None,
    warehouse_id: uuid.UUID | None = None,
    owner_id: uuid.UUID | None = None,
    status: str | None = None,
    remark: str | None = None,
    business_from: datetime | None = None,
    business_to: datetime | None = None,
) -> StockMovesPublic:
    page, page_size = normalize_pagination(page=page, page_size=page_size)
    scope = document_scope_filter(
        uow=uow, current_principal=current_principal, owner_column=StockMove.owner_id
    )
    warehouse_scope = warehouse_document_scope_filter(
        current_principal=current_principal,
        document_id_column=StockMove.id,
        item_document_id_column=StockMoveItem.stock_move_id,
        item_id_column=StockMoveItem.id,
        warehouse_columns=(
            StockMoveItem.from_warehouse_id,
            StockMoveItem.to_warehouse_id,
        ),
    )
    if warehouse_scope is not None:
        scope = scope & warehouse_scope
    try:
        filters = stock_document_filters(
            model=StockMove,
            item_document_column=StockMoveItem.stock_move_id,
            item_product_column=StockMoveItem.product_id,
            item_warehouse_columns=(
                StockMoveItem.from_warehouse_id,
                StockMoveItem.to_warehouse_id,
            ),
            product_model=Product,
            scope=scope,
            keyword=keyword,
            product_id=product_id,
            warehouse_id=warehouse_id,
            owner_id=owner_id,
            status=status,
            remark=remark,
            business_from=business_from,
            business_to=business_to,
        )
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    total = int(
        uow.session.exec(select(func.count()).select_from(StockMove).where(*filters)).one()
    )
    documents = uow.session.exec(
        select(StockMove)
        .where(*filters)
        .order_by(col(StockMove.business_at).desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
    ).all()
    return StockMovesPublic(
        items=[stock_move_public(uow, document) for document in documents],
        total=total,
        page=page,
        page_size=page_size,
    )


@router.post(
    "/stock-moves",
    dependencies=[Depends(require_module_access("erp", "erp:stock-move:create"))],
    response_model=StockMovePublic,
)
def create_stock_move(
    stock_move: StockMoveCreate,
    uow: ErpTenantUowDep,
    current_principal: CurrentPrincipal,
    tenant_context: CurrentTenant,
    idempotency_key: str = Header(alias="Idempotency-Key"),
) -> StockMovePublic:
    claim = command_claim(uow=uow, command_name="erp.stock-move.create", idempotency_key=idempotency_key, principal=current_principal, payload=stock_move.model_dump(mode="json"))
    if claim.replay:
        return replay_document(uow, claim, current_principal)
    if any(
        item.from_warehouse_id == item.to_warehouse_id for item in stock_move.items
    ):
        raise HTTPException(status_code=422, detail="Stock move warehouses must differ")
    assert_warehouses_authorized(
        uow=uow,
        current_principal=current_principal,
        warehouse_ids={
            warehouse_id
            for item in stock_move.items
            for warehouse_id in (item.from_warehouse_id, item.to_warehouse_id)
        },
    )
    document = StockMove(
        tenant_id=tenant_context.tenant_id,
        no=allocate_document_no(uow=uow, prefix="KCDB"),
        business_at=resolve_business_at(uow=uow, requested_at=stock_move.business_at),
        owner_id=current_principal.id,
        total_quantity=sum((item.quantity for item in stock_move.items), Decimal("0")),
        total_amount=sum((item.quantity * item.reference_price for item in stock_move.items), Decimal("0")),
        remark=stock_move.remark,
        created_by=current_principal.id,
        updated_by=current_principal.id,
    )
    uow.session.add(document)
    uow.session.flush()
    uow.session.add_all(
        [
            StockMoveItem(
                tenant_id=tenant_context.tenant_id,
                stock_move_id=document.id,
                line_no=index,
                product_id=item.product_id,
                from_warehouse_id=item.from_warehouse_id,
                to_warehouse_id=item.to_warehouse_id,
                quantity=item.quantity,
                reference_price=item.reference_price,
                remark=item.remark,
            )
            for index, item in enumerate(stock_move.items, start=1)
        ]
    )
    record_action(uow=uow, resource_type="stock_move", resource_id=document.id, resource_no=document.no, action=DocumentAction.CREATED, actor_id=current_principal.id, new_status=str(document.status), new_version=document.version, metadata={"item_count": len(stock_move.items)})
    complete_command(receipt=claim.receipt, resource_type="stock_move", resource_id=document.id, resource_version=document.version)
    uow.session.commit()
    uow.session.refresh(document)
    return stock_move_public(uow, document)


@router.get("/stock-moves/{document_id}", dependencies=[Depends(require_module_access("erp", "erp:stock-move:list"))], response_model=StockMovePublic)
def read_stock_move(document_id: uuid.UUID, uow: ErpTenantUowDep, current_principal: CurrentPrincipal) -> StockMovePublic:
    document = uow.session.get(StockMove, document_id)
    if document is None:
        raise HTTPException(status_code=404, detail="Stock move document not found")
    assert_stock_move_scope(uow=uow, current_principal=current_principal, document=document)
    return stock_move_public(uow, document)


@router.patch("/stock-moves/{document_id}", dependencies=[Depends(require_module_access("erp", "erp:stock-move:update"))], response_model=StockMovePublic)
def update_stock_move(document_id: uuid.UUID, command: StockMoveUpdate, uow: ErpTenantUowDep, current_principal: CurrentPrincipal) -> StockMovePublic:
    document = uow.session.exec(select(StockMove).where(StockMove.id == document_id).with_for_update()).first()
    if document is None:
        raise HTTPException(status_code=404, detail="Stock move document not found")
    assert_stock_move_scope(uow=uow, current_principal=current_principal, document=document)
    if document.status != DocumentStatus.DRAFT or document.version != command.expected_version:
        raise HTTPException(status_code=409, detail="Stock document version conflict")
    if any(item.from_warehouse_id == item.to_warehouse_id for item in command.items):
        raise HTTPException(status_code=422, detail="Stock move warehouses must differ")
    assert_warehouses_authorized(uow=uow, current_principal=current_principal, warehouse_ids={warehouse_id for item in command.items for warehouse_id in (item.from_warehouse_id, item.to_warehouse_id)})
    old_version = document.version
    for item in uow.session.exec(select(StockMoveItem).where(StockMoveItem.stock_move_id == document.id)).all():
        uow.session.delete(item)
    uow.session.flush()
    document.business_at = resolve_business_at(uow=uow, requested_at=command.business_at) if command.business_at is not None else document.business_at
    document.total_quantity = sum((item.quantity for item in command.items), Decimal("0"))
    document.total_amount = sum((item.quantity * item.reference_price for item in command.items), Decimal("0"))
    document.remark = command.remark
    document.version += 1
    document.updated_by = current_principal.id
    document.updated_at = get_datetime_utc()
    uow.session.add(document)
    uow.session.add_all([StockMoveItem(tenant_id=uow.tenant_id, stock_move_id=document.id, line_no=index, product_id=item.product_id, from_warehouse_id=item.from_warehouse_id, to_warehouse_id=item.to_warehouse_id, quantity=item.quantity, reference_price=item.reference_price, remark=item.remark) for index, item in enumerate(command.items, start=1)])
    record_action(uow=uow, resource_type="stock_move", resource_id=document.id, resource_no=document.no, action=DocumentAction.UPDATED, actor_id=current_principal.id, old_version=old_version, new_version=document.version, metadata={"item_count": len(command.items)})
    uow.session.commit()
    uow.session.refresh(document)
    return stock_move_public(uow, document)


@router.delete("/stock-moves/{document_id}", dependencies=[Depends(require_module_access("erp", "erp:stock-move:delete"))], status_code=204)
def delete_stock_move(document_id: uuid.UUID, uow: ErpTenantUowDep, current_principal: CurrentPrincipal) -> Response:
    document = uow.session.exec(select(StockMove).where(StockMove.id == document_id).with_for_update()).first()
    if document is None:
        raise HTTPException(status_code=404, detail="Stock move document not found")
    assert_stock_move_scope(uow=uow, current_principal=current_principal, document=document)
    if document.status != DocumentStatus.DRAFT:
        raise HTTPException(status_code=409, detail="Stock move document must be draft before deletion")
    record_action(uow=uow, resource_type="stock_move", resource_id=document.id, resource_no=document.no, action=DocumentAction.DELETED, actor_id=current_principal.id, old_status=str(document.status), old_version=document.version)
    uow.session.delete(document)
    uow.session.commit()
    return Response(status_code=204)


@router.post(
    "/stock-moves/{document_id}/approve",
    dependencies=[Depends(require_module_access("erp", "erp:stock-move:approve"))],
    response_model=StockMovePublic,
)
def approve_stock_move(
    document_id: uuid.UUID,
    command: DocumentCommand,
    uow: ErpTenantUowDep,
    current_principal: CurrentPrincipal,
    idempotency_key: str = Header(alias="Idempotency-Key"),
) -> StockMovePublic:
    claim = command_claim(uow=uow, command_name="erp.stock-move.approve", idempotency_key=idempotency_key, principal=current_principal, payload=command.model_dump(mode="json"), resource_id=document_id)
    if claim.replay:
        return replay_document(uow, claim, current_principal)
    document = uow.session.exec(
        select(StockMove).where(StockMove.id == document_id).with_for_update()
    ).first()
    if document is None:
        raise HTTPException(status_code=404, detail="Stock move document not found")
    assert_stock_move_scope(
        uow=uow, current_principal=current_principal, document=document
    )
    if document.status != DocumentStatus.DRAFT or document.version != command.expected_version:
        raise HTTPException(status_code=409, detail="Stock document version conflict")
    items = uow.session.exec(
        select(StockMoveItem)
        .where(StockMoveItem.stock_move_id == document.id)
        .order_by(StockMoveItem.line_no)
    ).all()
    try:
        InventoryPostingService(uow).post(
            effects=stock_move_effects(document, items), operator_id=current_principal.id
        )
    except InventoryConflictError as exc:
        raise_inventory_conflict(exc)
    old_status, old_version = str(document.status), document.version
    document.status = DocumentStatus.APPROVED
    document.version += 1
    document.approved_by = current_principal.id
    document.approved_at = get_datetime_utc()
    document.updated_by = current_principal.id
    document.updated_at = get_datetime_utc()
    uow.session.add(document)
    enqueue_document_lifecycle_event(
        uow=uow, document=document, document_type="stock_move", action="approved"
    )
    record_action(uow=uow, resource_type="stock_move", resource_id=document.id, resource_no=document.no, action=DocumentAction.APPROVED, actor_id=current_principal.id, old_status=old_status, new_status=str(document.status), old_version=old_version, new_version=document.version)
    complete_command(receipt=claim.receipt, resource_type="stock_move", resource_id=document.id, resource_version=document.version)
    uow.session.commit()
    uow.session.refresh(document)
    return stock_move_public(uow, document)


@router.post(
    "/stock-moves/{document_id}/reverse",
    dependencies=[Depends(require_module_access("erp", "erp:stock-move:reverse"))],
    response_model=StockMovePublic,
)
def reverse_stock_move(
    document_id: uuid.UUID,
    command: DocumentReverseCommand,
    uow: ErpTenantUowDep,
    current_principal: CurrentPrincipal,
    idempotency_key: str = Header(alias="Idempotency-Key"),
) -> StockMovePublic:
    claim = command_claim(uow=uow, command_name="erp.stock-move.reverse", idempotency_key=idempotency_key, principal=current_principal, payload=command.model_dump(mode="json"), resource_id=document_id)
    if claim.replay:
        return replay_document(uow, claim, current_principal)
    document = uow.session.exec(
        select(StockMove).where(StockMove.id == document_id).with_for_update()
    ).first()
    if document is None:
        raise HTTPException(status_code=404, detail="Stock move document not found")
    assert_stock_move_scope(
        uow=uow, current_principal=current_principal, document=document
    )
    if document.status != DocumentStatus.APPROVED or document.version != command.expected_version:
        raise HTTPException(status_code=409, detail="Stock document version conflict")
    ledgers = uow.session.exec(
        select(StockLedger).where(
            StockLedger.source_document_type == "stock_move",
            StockLedger.source_document_id == document.id,
            StockLedger.source_version == document.version,
            StockLedger.reversal_of_id.is_(None),
        )
    ).all()
    if not ledgers:
        raise HTTPException(status_code=409, detail="Stock document has no reversible posting")
    try:
        InventoryPostingService(uow).post(
            effects=reversal_effects(
                document_id=document.id,
                document_no=document.no,
                document_type="stock_move",
                version=document.version,
                ledgers=ledgers,
            ),
            operator_id=current_principal.id,
            require_active_references=False,
        )
    except InventoryConflictError as exc:
        raise_inventory_conflict(exc)
    old_status, old_version = str(document.status), document.version
    document.status = DocumentStatus.DRAFT
    document.version += 1
    document.reversed_by = current_principal.id
    document.reversed_at = get_datetime_utc()
    document.updated_by = current_principal.id
    document.updated_at = get_datetime_utc()
    uow.session.add(document)
    enqueue_document_lifecycle_event(
        uow=uow, document=document, document_type="stock_move", action="reversed"
    )
    record_action(uow=uow, resource_type="stock_move", resource_id=document.id, resource_no=document.no, action=DocumentAction.REVERSED, actor_id=current_principal.id, old_status=old_status, new_status=str(document.status), old_version=old_version, new_version=document.version, reason=command.reason)
    complete_command(receipt=claim.receipt, resource_type="stock_move", resource_id=document.id, resource_version=document.version)
    uow.session.commit()
    uow.session.refresh(document)
    return stock_move_public(uow, document)


def stock_check_public(uow: ErpTenantUowDep, document: StockCheck) -> StockCheckPublic:
    items = uow.session.exec(
        select(StockCheckItem)
        .where(StockCheckItem.stock_check_id == document.id)
        .order_by(StockCheckItem.line_no)
    ).all()
    return StockCheckPublic.model_validate(document).model_copy(
        update={"items": [StockCheckItemPublic.model_validate(item) for item in items]}
    )


def assert_stock_check_scope(
    *,
    uow: ErpTenantUowDep,
    current_principal: CurrentPrincipal,
    document: StockCheck,
) -> None:
    allowed = uow.session.exec(
        select(StockCheck.id).where(
            StockCheck.id == document.id,
            document_scope_filter(
                uow=uow,
                current_principal=current_principal,
                owner_column=StockCheck.owner_id,
            ),
        )
    ).first()
    if allowed is None:
        raise HTTPException(status_code=403, detail="Not enough permissions")
    assert_warehouses_authorized(
        uow=uow,
        current_principal=current_principal,
        warehouse_ids=set(
            uow.session.exec(
                select(StockCheckItem.warehouse_id).where(
                    StockCheckItem.stock_check_id == document.id
                )
            ).all()
        ),
    )


@router.get(
    "/stock-checks",
    dependencies=[Depends(require_module_access("erp", "erp:stock-check:list"))],
    response_model=StockChecksPublic,
)
def read_stock_checks(
    uow: ErpTenantUowDep,
    current_principal: CurrentPrincipal,
    page: int = 1,
    page_size: int = 20,
    keyword: str | None = None,
    product_id: uuid.UUID | None = None,
    warehouse_id: uuid.UUID | None = None,
    owner_id: uuid.UUID | None = None,
    status: str | None = None,
    remark: str | None = None,
    business_from: datetime | None = None,
    business_to: datetime | None = None,
) -> StockChecksPublic:
    page, page_size = normalize_pagination(page=page, page_size=page_size)
    scope = document_scope_filter(
        uow=uow, current_principal=current_principal, owner_column=StockCheck.owner_id
    )
    warehouse_scope = warehouse_document_scope_filter(
        current_principal=current_principal,
        document_id_column=StockCheck.id,
        item_document_id_column=StockCheckItem.stock_check_id,
        item_id_column=StockCheckItem.id,
        warehouse_columns=(StockCheckItem.warehouse_id,),
    )
    if warehouse_scope is not None:
        scope = scope & warehouse_scope
    try:
        filters = stock_document_filters(
            model=StockCheck,
            item_document_column=StockCheckItem.stock_check_id,
            item_product_column=StockCheckItem.product_id,
            item_warehouse_columns=(StockCheckItem.warehouse_id,),
            product_model=Product,
            scope=scope,
            keyword=keyword,
            product_id=product_id,
            warehouse_id=warehouse_id,
            owner_id=owner_id,
            status=status,
            remark=remark,
            business_from=business_from,
            business_to=business_to,
        )
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    total = int(
        uow.session.exec(select(func.count()).select_from(StockCheck).where(*filters)).one()
    )
    documents = uow.session.exec(
        select(StockCheck)
        .where(*filters)
        .order_by(col(StockCheck.business_at).desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
    ).all()
    return StockChecksPublic(
        items=[stock_check_public(uow, document) for document in documents],
        total=total,
        page=page,
        page_size=page_size,
    )


@router.post(
    "/stock-checks",
    dependencies=[Depends(require_module_access("erp", "erp:stock-check:create"))],
    response_model=StockCheckPublic,
)
def create_stock_check(
    stock_check: StockCheckCreate,
    uow: ErpTenantUowDep,
    current_principal: CurrentPrincipal,
    tenant_context: CurrentTenant,
    idempotency_key: str = Header(alias="Idempotency-Key"),
) -> StockCheckPublic:
    claim = command_claim(uow=uow, command_name="erp.stock-check.create", idempotency_key=idempotency_key, principal=current_principal, payload=stock_check.model_dump(mode="json"))
    if claim.replay:
        return replay_document(uow, claim, current_principal)
    keys = {(item.product_id, item.warehouse_id) for item in stock_check.items}
    if len(keys) != len(stock_check.items):
        raise HTTPException(status_code=422, detail="Stock check lines must be unique")
    assert_warehouses_authorized(
        uow=uow,
        current_principal=current_principal,
        warehouse_ids={item.warehouse_id for item in stock_check.items},
    )
    snapshots = {
        (balance.product_id, balance.warehouse_id): balance.quantity
        for balance in uow.session.exec(
            select(StockBalance).where(
                StockBalance.product_id.in_({item.product_id for item in stock_check.items}),
                StockBalance.warehouse_id.in_(
                    {item.warehouse_id for item in stock_check.items}
                ),
            )
        ).all()
    }
    difference_amounts = [
        abs(item.actual_quantity - snapshots.get((item.product_id, item.warehouse_id), Decimal("0")))
        * item.reference_price
        for item in stock_check.items
    ]
    document = StockCheck(
        tenant_id=tenant_context.tenant_id,
        no=allocate_document_no(uow=uow, prefix="KCPD"),
        business_at=resolve_business_at(uow=uow, requested_at=stock_check.business_at),
        owner_id=current_principal.id,
        total_quantity=sum(
            (item.actual_quantity for item in stock_check.items), Decimal("0")
        ),
        total_amount=sum(difference_amounts, Decimal("0")),
        remark=stock_check.remark,
        created_by=current_principal.id,
        updated_by=current_principal.id,
    )
    uow.session.add(document)
    uow.session.flush()
    uow.session.add_all(
        [
            StockCheckItem(
                tenant_id=tenant_context.tenant_id,
                stock_check_id=document.id,
                line_no=index,
                product_id=item.product_id,
                warehouse_id=item.warehouse_id,
                snapshot_quantity=snapshots.get(
                    (item.product_id, item.warehouse_id), Decimal("0")
                ),
                actual_quantity=item.actual_quantity,
                difference_quantity=item.actual_quantity
                - snapshots.get((item.product_id, item.warehouse_id), Decimal("0")),
                reference_price=item.reference_price,
                difference_amount=(
                    item.actual_quantity
                    - snapshots.get((item.product_id, item.warehouse_id), Decimal("0"))
                )
                * item.reference_price,
                remark=item.remark,
            )
            for index, item in enumerate(stock_check.items, start=1)
        ]
    )
    record_action(uow=uow, resource_type="stock_check", resource_id=document.id, resource_no=document.no, action=DocumentAction.CREATED, actor_id=current_principal.id, new_status=str(document.status), new_version=document.version, metadata={"item_count": len(stock_check.items)})
    complete_command(receipt=claim.receipt, resource_type="stock_check", resource_id=document.id, resource_version=document.version)
    uow.session.commit()
    uow.session.refresh(document)
    return stock_check_public(uow, document)


@router.get("/stock-checks/{document_id}", dependencies=[Depends(require_module_access("erp", "erp:stock-check:list"))], response_model=StockCheckPublic)
def read_stock_check(document_id: uuid.UUID, uow: ErpTenantUowDep, current_principal: CurrentPrincipal) -> StockCheckPublic:
    document = uow.session.get(StockCheck, document_id)
    if document is None:
        raise HTTPException(status_code=404, detail="Stock check document not found")
    assert_stock_check_scope(uow=uow, current_principal=current_principal, document=document)
    return stock_check_public(uow, document)


@router.patch("/stock-checks/{document_id}", dependencies=[Depends(require_module_access("erp", "erp:stock-check:update"))], response_model=StockCheckPublic)
def update_stock_check(document_id: uuid.UUID, command: StockCheckUpdate, uow: ErpTenantUowDep, current_principal: CurrentPrincipal) -> StockCheckPublic:
    document = uow.session.exec(select(StockCheck).where(StockCheck.id == document_id).with_for_update()).first()
    if document is None:
        raise HTTPException(status_code=404, detail="Stock check document not found")
    assert_stock_check_scope(uow=uow, current_principal=current_principal, document=document)
    if document.status != DocumentStatus.DRAFT or document.version != command.expected_version:
        raise HTTPException(status_code=409, detail="Stock document version conflict")
    keys = {(item.product_id, item.warehouse_id) for item in command.items}
    if len(keys) != len(command.items):
        raise HTTPException(status_code=422, detail="Stock check lines must be unique")
    assert_warehouses_authorized(uow=uow, current_principal=current_principal, warehouse_ids={item.warehouse_id for item in command.items})
    snapshots = {(balance.product_id, balance.warehouse_id): balance.quantity for balance in uow.session.exec(select(StockBalance).where(StockBalance.product_id.in_({item.product_id for item in command.items}), StockBalance.warehouse_id.in_({item.warehouse_id for item in command.items}))).all()}
    old_version = document.version
    for item in uow.session.exec(select(StockCheckItem).where(StockCheckItem.stock_check_id == document.id)).all():
        uow.session.delete(item)
    uow.session.flush()
    document.business_at = resolve_business_at(uow=uow, requested_at=command.business_at) if command.business_at is not None else document.business_at
    document.total_quantity = sum((item.actual_quantity for item in command.items), Decimal("0"))
    document.total_amount = sum((abs(item.actual_quantity - snapshots.get((item.product_id, item.warehouse_id), Decimal("0"))) * item.reference_price for item in command.items), Decimal("0"))
    document.remark = command.remark
    document.version += 1
    document.updated_by = current_principal.id
    document.updated_at = get_datetime_utc()
    uow.session.add(document)
    uow.session.add_all([StockCheckItem(tenant_id=uow.tenant_id, stock_check_id=document.id, line_no=index, product_id=item.product_id, warehouse_id=item.warehouse_id, snapshot_quantity=snapshots.get((item.product_id, item.warehouse_id), Decimal("0")), actual_quantity=item.actual_quantity, difference_quantity=item.actual_quantity - snapshots.get((item.product_id, item.warehouse_id), Decimal("0")), reference_price=item.reference_price, difference_amount=(item.actual_quantity - snapshots.get((item.product_id, item.warehouse_id), Decimal("0"))) * item.reference_price, remark=item.remark) for index, item in enumerate(command.items, start=1)])
    record_action(uow=uow, resource_type="stock_check", resource_id=document.id, resource_no=document.no, action=DocumentAction.UPDATED, actor_id=current_principal.id, old_version=old_version, new_version=document.version, metadata={"item_count": len(command.items), "snapshot_refreshed": True})
    uow.session.commit()
    uow.session.refresh(document)
    return stock_check_public(uow, document)


@router.delete("/stock-checks/{document_id}", dependencies=[Depends(require_module_access("erp", "erp:stock-check:delete"))], status_code=204)
def delete_stock_check(document_id: uuid.UUID, uow: ErpTenantUowDep, current_principal: CurrentPrincipal) -> Response:
    document = uow.session.exec(select(StockCheck).where(StockCheck.id == document_id).with_for_update()).first()
    if document is None:
        raise HTTPException(status_code=404, detail="Stock check document not found")
    assert_stock_check_scope(uow=uow, current_principal=current_principal, document=document)
    if document.status != DocumentStatus.DRAFT:
        raise HTTPException(status_code=409, detail="Stock check document must be draft before deletion")
    record_action(uow=uow, resource_type="stock_check", resource_id=document.id, resource_no=document.no, action=DocumentAction.DELETED, actor_id=current_principal.id, old_status=str(document.status), old_version=document.version)
    uow.session.delete(document)
    uow.session.commit()
    return Response(status_code=204)


@router.post(
    "/stock-checks/{document_id}/approve",
    dependencies=[Depends(require_module_access("erp", "erp:stock-check:approve"))],
    response_model=StockCheckPublic,
)
def approve_stock_check(
    document_id: uuid.UUID,
    command: DocumentCommand,
    uow: ErpTenantUowDep,
    current_principal: CurrentPrincipal,
    idempotency_key: str = Header(alias="Idempotency-Key"),
) -> StockCheckPublic:
    claim = command_claim(uow=uow, command_name="erp.stock-check.approve", idempotency_key=idempotency_key, principal=current_principal, payload=command.model_dump(mode="json"), resource_id=document_id)
    if claim.replay:
        return replay_document(uow, claim, current_principal)
    document = uow.session.exec(
        select(StockCheck).where(StockCheck.id == document_id).with_for_update()
    ).first()
    if document is None:
        raise HTTPException(status_code=404, detail="Stock check document not found")
    assert_stock_check_scope(
        uow=uow, current_principal=current_principal, document=document
    )
    if document.status != DocumentStatus.DRAFT or document.version != command.expected_version:
        raise HTTPException(status_code=409, detail="Stock document version conflict")
    items = uow.session.exec(
        select(StockCheckItem)
        .where(StockCheckItem.stock_check_id == document.id)
        .order_by(StockCheckItem.line_no)
    ).all()
    expected_quantities = {
        (item.product_id, item.warehouse_id): item.snapshot_quantity for item in items
    }
    source_version = document.version + 1
    effects = tuple(
        InventoryEffect(
            product_id=item.product_id,
            warehouse_id=item.warehouse_id,
            delta_quantity=item.difference_quantity,
            ledger_type=(
                StockLedgerType.CHECK_GAIN
                if item.difference_quantity > Decimal("0")
                else StockLedgerType.CHECK_LOSS
            ),
            source_document_type="stock_check",
            source_document_id=document.id,
            source_item_id=item.id,
            source_document_no=document.no,
            source_version=source_version,
        )
        for item in items
        if item.difference_quantity != Decimal("0")
    )
    try:
        InventoryPostingService(uow).post(
            effects=effects,
            operator_id=current_principal.id,
            expected_quantities=expected_quantities,
        )
    except InventoryConflictError as exc:
        raise_inventory_conflict(exc)
    old_status, old_version = str(document.status), document.version
    document.status = DocumentStatus.APPROVED
    document.version += 1
    document.approved_by = current_principal.id
    document.approved_at = get_datetime_utc()
    document.updated_by = current_principal.id
    document.updated_at = get_datetime_utc()
    uow.session.add(document)
    enqueue_document_lifecycle_event(
        uow=uow, document=document, document_type="stock_check", action="approved"
    )
    record_action(uow=uow, resource_type="stock_check", resource_id=document.id, resource_no=document.no, action=DocumentAction.APPROVED, actor_id=current_principal.id, old_status=old_status, new_status=str(document.status), old_version=old_version, new_version=document.version)
    complete_command(receipt=claim.receipt, resource_type="stock_check", resource_id=document.id, resource_version=document.version)
    uow.session.commit()
    uow.session.refresh(document)
    return stock_check_public(uow, document)


@router.post(
    "/stock-checks/{document_id}/reverse",
    dependencies=[Depends(require_module_access("erp", "erp:stock-check:reverse"))],
    response_model=StockCheckPublic,
)
def reverse_stock_check(
    document_id: uuid.UUID,
    command: DocumentReverseCommand,
    uow: ErpTenantUowDep,
    current_principal: CurrentPrincipal,
    idempotency_key: str = Header(alias="Idempotency-Key"),
) -> StockCheckPublic:
    claim = command_claim(uow=uow, command_name="erp.stock-check.reverse", idempotency_key=idempotency_key, principal=current_principal, payload=command.model_dump(mode="json"), resource_id=document_id)
    if claim.replay:
        return replay_document(uow, claim, current_principal)
    document = uow.session.exec(
        select(StockCheck).where(StockCheck.id == document_id).with_for_update()
    ).first()
    if document is None:
        raise HTTPException(status_code=404, detail="Stock check document not found")
    assert_stock_check_scope(
        uow=uow, current_principal=current_principal, document=document
    )
    if document.status != DocumentStatus.APPROVED or document.version != command.expected_version:
        raise HTTPException(status_code=409, detail="Stock document version conflict")
    ledgers = uow.session.exec(
        select(StockLedger).where(
            StockLedger.source_document_type == "stock_check",
            StockLedger.source_document_id == document.id,
            StockLedger.source_version == document.version,
            StockLedger.reversal_of_id.is_(None),
        )
    ).all()
    if ledgers:
        try:
            InventoryPostingService(uow).post(
                effects=reversal_effects(
                    document_id=document.id,
                    document_no=document.no,
                    document_type="stock_check",
                    version=document.version,
                    ledgers=ledgers,
                ),
                operator_id=current_principal.id,
                require_active_references=False,
            )
        except InventoryConflictError as exc:
            raise_inventory_conflict(exc)
    old_status, old_version = str(document.status), document.version
    document.status = DocumentStatus.DRAFT
    document.version += 1
    document.reversed_by = current_principal.id
    document.reversed_at = get_datetime_utc()
    document.updated_by = current_principal.id
    document.updated_at = get_datetime_utc()
    uow.session.add(document)
    enqueue_document_lifecycle_event(
        uow=uow, document=document, document_type="stock_check", action="reversed"
    )
    record_action(uow=uow, resource_type="stock_check", resource_id=document.id, resource_no=document.no, action=DocumentAction.REVERSED, actor_id=current_principal.id, old_status=old_status, new_status=str(document.status), old_version=old_version, new_version=document.version, reason=command.reason)
    complete_command(receipt=claim.receipt, resource_type="stock_check", resource_id=document.id, resource_version=document.version)
    uow.session.commit()
    uow.session.refresh(document)
    return stock_check_public(uow, document)
