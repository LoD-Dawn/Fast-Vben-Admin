import json
import uuid

from sqlmodel import Session, select

from app.models import EventDelivery, InboxReceipt, OutboxEvent, Tenant
from app.modules.erp.application import reconciliation
from app.modules.erp.application.reconciliation import run_reconciliation
from app.modules.erp.infrastructure.tenant_uow import ErpTenantUnitOfWork
from app.modules.events import configure_event_deliveries
from app.modules.outbox import EVENT_HANDLERS, dispatch_pending_events
from app.modules.registry import get_module_definitions


def test_reconciliation_failure_has_a_required_platform_outbox_consumer(
    db: Session, monkeypatch
) -> None:
    definitions = get_module_definitions()
    configure_event_deliveries((definitions["platform"], definitions["erp"]))
    tenant = db.exec(select(Tenant).where(Tenant.code == "default")).one()
    difference = (uuid.uuid4(), uuid.uuid4())
    monkeypatch.setattr(
        reconciliation, "_stock_differences", lambda _uow: [difference]
    )
    try:
        with ErpTenantUnitOfWork(session=db, tenant_id=tenant.id) as uow:
            run = run_reconciliation(uow=uow, triggered_by=None)
            db.commit()

        event = db.exec(
            select(OutboxEvent).where(
                OutboxEvent.event_type == "erp.reconciliation.failed",
                OutboxEvent.aggregate_id == str(run.id),
            )
        ).one()
        delivery = db.exec(
            select(EventDelivery).where(EventDelivery.event_id == event.id)
        ).one()
        assert delivery.target_name == "platform.erp-reconciliation-alert"
        assert delivery.consumer_module == "platform"
        assert delivery.is_required is True
        assert json.loads(event.payload) == {
            "tenant_id": str(tenant.id),
            "reconciliation_run_id": str(run.id),
            "stock_difference_count": 1,
            "settlement_difference_count": 0,
            "occurred_at": run.completed_at.isoformat().replace("+00:00", "Z"),
        }

        assert dispatch_pending_events(session=db) == (1, 0)
        db.commit()
        assert db.get(InboxReceipt, ("platform.erp-reconciliation-alert", event.id))
    finally:
        EVENT_HANDLERS.clear()
