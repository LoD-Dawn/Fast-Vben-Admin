"""Stable Platform-owned operational event consumers for business modules."""

import logging
from typing import Any

from app.modules.outbox import register_event_handler

logger = logging.getLogger(__name__)


def register_reconciliation_failure_consumer() -> None:
    """Register the required Platform consumer for ERP integrity failures."""

    register_event_handler(
        "erp.reconciliation.failed",
        "platform.erp-reconciliation-alert",
        _record_reconciliation_failure,
        consumer_module="platform",
        required=True,
    )


def _record_reconciliation_failure(
    _session: object, event: Any, payload: dict[str, Any]
) -> None:
    """Emit a structured operational alert from the trusted Outbox envelope."""

    if event.tenant_id is None:
        raise ValueError("ERP reconciliation failure event requires a tenant")
    stock_count = payload.get("stock_difference_count")
    settlement_count = payload.get("settlement_difference_count")
    if (
        not isinstance(stock_count, int)
        or isinstance(stock_count, bool)
        or stock_count < 0
        or not isinstance(settlement_count, int)
        or isinstance(settlement_count, bool)
        or settlement_count < 0
    ):
        raise ValueError("ERP reconciliation failure event has invalid difference counts")
    logger.error(
        "ERP reconciliation failed",
        extra={
            "event_id": str(event.id),
            "tenant_id": str(event.tenant_id),
            "stock_difference_count": stock_count,
            "settlement_difference_count": settlement_count,
        },
    )
