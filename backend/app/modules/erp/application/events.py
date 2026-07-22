"""Transactional ERP lifecycle notifications."""

from typing import Any

from app.core.clock import get_datetime_utc
from app.modules.erp.infrastructure.tenant_uow import ErpTenantUnitOfWork
from app.modules.erp.public_api.events import DocumentLifecycleV1
from app.modules.outbox import enqueue_event


def enqueue_document_lifecycle_event(
    *,
    uow: ErpTenantUnitOfWork,
    document: Any,
    document_type: str,
    action: str,
) -> None:
    """Queue an approval or reversal event in the caller's transaction."""
    amount = getattr(document, "total_amount", None)
    if amount is None:
        amount = getattr(document, "payment_amount", None)
    if amount is None:
        amount = getattr(document, "receipt_amount", None)
    payload = DocumentLifecycleV1(
        tenant_id=uow.tenant_id,
        document_id=document.id,
        document_no=document.no,
        action=action,
        version=document.version,
        occurred_at=get_datetime_utc(),
        amount=amount,
    )
    enqueue_event(
        session=uow.session,
        module_code="erp",
        event_type=f"erp.{document_type}.{action}",
        tenant_id=uow.tenant_id,
        aggregate_id=str(document.id),
        aggregate_sequence=document.version,
        payload=payload.model_dump(mode="json"),
        allow_zero_subscribers=True,
    )
