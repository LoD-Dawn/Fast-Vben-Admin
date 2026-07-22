"""ERP reference guards used by Platform destructive operations."""

from typing import Any

from sqlalchemy import or_, text
from sqlmodel import Session, func, select

from app.modules.erp.infrastructure.models import (
    DocumentActionLog,
    DocumentAttachment,
    FinancePayment,
    FinanceReceipt,
    PurchaseIn,
    PurchaseOrder,
    PurchaseReturn,
    SaleOrder,
    SaleOut,
    SaleReturn,
    StockCheck,
    StockIn,
    StockLedger,
    StockMove,
    StockOut,
    WarehouseUserGrant,
)

_USER_REFERENCE_COLUMNS: tuple[tuple[type[Any], tuple[Any, ...]], ...] = (
    (DocumentActionLog, (DocumentActionLog.actor_id,)),
    (DocumentAttachment, (DocumentAttachment.created_by,)),
    (FinancePayment, (FinancePayment.owner_id, FinancePayment.created_by, FinancePayment.updated_by, FinancePayment.approved_by, FinancePayment.reversed_by)),
    (FinanceReceipt, (FinanceReceipt.owner_id, FinanceReceipt.created_by, FinanceReceipt.updated_by, FinanceReceipt.approved_by, FinanceReceipt.reversed_by)),
    (PurchaseOrder, (PurchaseOrder.owner_id, PurchaseOrder.created_by, PurchaseOrder.updated_by, PurchaseOrder.approved_by, PurchaseOrder.reversed_by)),
    (PurchaseIn, (PurchaseIn.owner_id, PurchaseIn.created_by, PurchaseIn.updated_by, PurchaseIn.approved_by, PurchaseIn.reversed_by)),
    (PurchaseReturn, (PurchaseReturn.owner_id, PurchaseReturn.created_by, PurchaseReturn.updated_by, PurchaseReturn.approved_by, PurchaseReturn.reversed_by)),
    (SaleOrder, (SaleOrder.owner_id, SaleOrder.created_by, SaleOrder.updated_by, SaleOrder.approved_by, SaleOrder.reversed_by)),
    (SaleOut, (SaleOut.owner_id, SaleOut.created_by, SaleOut.updated_by, SaleOut.approved_by, SaleOut.reversed_by)),
    (SaleReturn, (SaleReturn.owner_id, SaleReturn.created_by, SaleReturn.updated_by, SaleReturn.approved_by, SaleReturn.reversed_by)),
    (StockLedger, (StockLedger.operator_id,)),
    (StockIn, (StockIn.owner_id, StockIn.created_by, StockIn.updated_by, StockIn.approved_by, StockIn.reversed_by)),
    (StockOut, (StockOut.owner_id, StockOut.created_by, StockOut.updated_by, StockOut.approved_by, StockOut.reversed_by)),
    (StockMove, (StockMove.owner_id, StockMove.created_by, StockMove.updated_by, StockMove.approved_by, StockMove.reversed_by)),
    (StockCheck, (StockCheck.owner_id, StockCheck.created_by, StockCheck.updated_by, StockCheck.approved_by, StockCheck.reversed_by)),
    (WarehouseUserGrant, (WarehouseUserGrant.user_id, WarehouseUserGrant.granted_by)),
)


def count_user_references(
    session: Session, reference_type: str, reference_id: object, tenant_id: object | None = None
) -> int:
    """Count every tenant-local ERP user reference without bypassing RLS."""

    if reference_type != "user" or tenant_id is None:
        return 0
    session.execute(
        text("SELECT set_config('app.tenant_id', :tenant_id, true)"),
        {"tenant_id": str(tenant_id)},
    )
    try:
        total = 0
        for model, columns in _USER_REFERENCE_COLUMNS:
            total += int(
                session.exec(
                    select(func.count())
                    .select_from(model)
                    .where(model.tenant_id == tenant_id, or_(*(column == reference_id for column in columns)))
                ).one()
            )
        return total
    finally:
        session.execute(text("SELECT set_config('app.tenant_id', '', true)"))
