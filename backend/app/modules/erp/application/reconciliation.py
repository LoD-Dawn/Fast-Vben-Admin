"""Tenant-local consistency checks for ERP stock and settlements."""

import uuid
from collections import defaultdict
from decimal import Decimal

from sqlmodel import select

from app.core.clock import get_datetime_utc
from app.modules.erp.infrastructure.models import (
    DocumentStatus,
    ErpSetting,
    FinancePayment,
    FinancePaymentItem,
    FinanceReceipt,
    FinanceReceiptItem,
    PurchaseIn,
    PurchaseReturn,
    ReconciliationRun,
    ReconciliationRunStatus,
    SaleOut,
    SaleReturn,
    SettlementSourceType,
    StockBalance,
    StockLedger,
)
from app.modules.erp.infrastructure.tenant_uow import ErpTenantUnitOfWork
from app.modules.erp.observability import observe_reconciliation_differences
from app.modules.erp.public_api.events import ReconciliationFailedV1
from app.modules.outbox import enqueue_event

_ZERO = Decimal("0")
_SAMPLE_LIMIT = 20


def _stock_differences(uow: ErpTenantUnitOfWork) -> list[tuple[uuid.UUID, uuid.UUID]]:
    ledger_totals: defaultdict[tuple[uuid.UUID, uuid.UUID], Decimal] = defaultdict(
        lambda: _ZERO
    )
    for ledger in uow.session.exec(select(StockLedger)).all():
        ledger_totals[(ledger.product_id, ledger.warehouse_id)] += ledger.delta_quantity
    balances = {
        (balance.product_id, balance.warehouse_id): balance.quantity
        for balance in uow.session.exec(select(StockBalance)).all()
    }
    return [
        key
        for key in set(ledger_totals) | set(balances)
        if ledger_totals[key] != balances.get(key, _ZERO)
    ]


def _settlement_totals(uow: ErpTenantUnitOfWork) -> dict[tuple[str, uuid.UUID], Decimal]:
    totals: defaultdict[tuple[str, uuid.UUID], Decimal] = defaultdict(lambda: _ZERO)
    payment_rows = uow.session.exec(
        select(FinancePayment, FinancePaymentItem)
        .join(FinancePaymentItem, FinancePaymentItem.finance_payment_id == FinancePayment.id)
        .where(FinancePayment.status == DocumentStatus.APPROVED)
    ).all()
    receipt_rows = uow.session.exec(
        select(FinanceReceipt, FinanceReceiptItem)
        .join(FinanceReceiptItem, FinanceReceiptItem.finance_receipt_id == FinanceReceipt.id)
        .where(FinanceReceipt.status == DocumentStatus.APPROVED)
    ).all()
    for _header, item in (*payment_rows, *receipt_rows):
        source_type = SettlementSourceType(item.source_type)
        amount = abs(item.settlement_signed)
        if source_type in {
            SettlementSourceType.PURCHASE_IN,
            SettlementSourceType.SALE_OUT,
        }:
            amount += item.discount_allocated
        totals[(source_type.value, item.source_document_id)] += amount
    return dict(totals)


def _settlement_differences(uow: ErpTenantUnitOfWork) -> list[tuple[str, uuid.UUID]]:
    expected = _settlement_totals(uow)
    actual: dict[tuple[str, uuid.UUID], Decimal] = {}
    for source_type, model in (
        (SettlementSourceType.PURCHASE_IN, PurchaseIn),
        (SettlementSourceType.PURCHASE_RETURN, PurchaseReturn),
        (SettlementSourceType.SALE_OUT, SaleOut),
        (SettlementSourceType.SALE_RETURN, SaleReturn),
    ):
        for source in uow.session.exec(select(model)).all():
            actual[(source_type.value, source.id)] = source.settled_amount
    return [
        key
        for key in set(expected) | set(actual)
        if expected.get(key, _ZERO) != actual.get(key, _ZERO)
    ]


def run_reconciliation(
    *, uow: ErpTenantUnitOfWork, triggered_by: uuid.UUID | None
) -> ReconciliationRun:
    """Record a read-only consistency check and update the tenant health state."""

    run = ReconciliationRun(tenant_id=uow.tenant_id, triggered_by=triggered_by)
    uow.session.add(run)
    uow.session.flush()
    stock_differences = _stock_differences(uow)
    settlement_differences = _settlement_differences(uow)
    is_healthy = not stock_differences and not settlement_differences
    now = get_datetime_utc()
    run.stock_difference_count = len(stock_differences)
    run.settlement_difference_count = len(settlement_differences)
    observe_reconciliation_differences(
        stock_difference_count=run.stock_difference_count,
        settlement_difference_count=run.settlement_difference_count,
    )
    run.status = (
        ReconciliationRunStatus.PASSED if is_healthy else ReconciliationRunStatus.FAILED
    )
    run.summary_json = {
        "stock_difference_samples": [
            {"product_id": str(product_id), "warehouse_id": str(warehouse_id)}
            for product_id, warehouse_id in stock_differences[:_SAMPLE_LIMIT]
        ],
        "settlement_difference_samples": [
            {"source_type": source_type, "source_document_id": str(document_id)}
            for source_type, document_id in settlement_differences[:_SAMPLE_LIMIT]
        ],
    }
    run.completed_at = now
    setting = uow.session.get(ErpSetting, uow.tenant_id)
    if setting is None:
        setting = ErpSetting(tenant_id=uow.tenant_id)
    setting.integrity_status = "healthy" if is_healthy else "degraded"
    setting.last_reconciled_at = now
    setting.version += 1
    setting.updated_at = now
    uow.session.add_all([run, setting])
    if not is_healthy:
        enqueue_event(
            session=uow.session,
            module_code="erp",
            event_type="erp.reconciliation.failed",
            tenant_id=uow.tenant_id,
            aggregate_id=str(run.id),
            payload=ReconciliationFailedV1(
                tenant_id=uow.tenant_id,
                reconciliation_run_id=run.id,
                stock_difference_count=run.stock_difference_count,
                settlement_difference_count=run.settlement_difference_count,
                occurred_at=now,
            ).model_dump(mode="json"),
        )
    return run
