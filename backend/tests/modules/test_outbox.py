from datetime import timedelta

import pytest
from sqlmodel import Session, select

from app.core.clock import get_datetime_utc
from app.models import (
    EventDelivery,
    EventDeliveryStatus,
    EventDeliveryTargetType,
    InboxReceipt,
    ModuleDesiredState,
    ModuleRegistry,
    OutboxEvent,
    OutboxEventStatus,
    Tenant,
)
from app.modules.outbox import (
    EVENT_HANDLERS,
    dispatch_pending_events,
    enqueue_event,
    register_event_handler,
    register_external_broker_delivery,
)


@pytest.fixture(autouse=True)
def clean_outbox_state(db: Session):
    """The shared integration session must not leak retryable deliveries."""
    db.execute(EventDelivery.__table__.delete())
    db.execute(InboxReceipt.__table__.delete())
    db.execute(OutboxEvent.__table__.delete())
    db.commit()
    yield
    db.execute(EventDelivery.__table__.delete())
    db.execute(InboxReceipt.__table__.delete())
    db.execute(OutboxEvent.__table__.delete())
    db.commit()


def test_outbox_delivery_is_idempotent_after_consumer_commit(db: Session) -> None:
    delivered_payloads: list[dict[str, object]] = []

    def successful_handler(
        _session: Session, _event: OutboxEvent, payload: dict[str, object]
    ) -> None:
        delivered_payloads.append(payload)

    event_type = "test.outbox.delivered.v2"
    register_event_handler(event_type, "test-success", successful_handler)
    try:
        event = enqueue_event(
            session=db,
            module_code="platform",
            event_type=event_type,
            tenant_id=None,
            aggregate_id="aggregate-1",
            payload={"value": "expected"},
        )
        db.commit()

        assert dispatch_pending_events(session=db) == (1, 0)
        db.commit()
        db.refresh(event)
        delivery = db.exec(
            select(EventDelivery).where(EventDelivery.event_id == event.id)
        ).one()
        assert event.status == OutboxEventStatus.COMPLETE
        assert delivery.status == EventDeliveryStatus.DELIVERED
        assert delivered_payloads == [{"value": "expected"}]
        assert db.get(InboxReceipt, ("test-success", event.id)) is not None

        # Simulate a worker restart after the consumer transaction committed but
        # before it acknowledged the delivery.
        delivery.status = EventDeliveryStatus.PENDING
        delivery.available_at = get_datetime_utc()
        db.add(delivery)
        db.commit()
        assert dispatch_pending_events(session=db) == (1, 0)
        db.commit()
        assert delivered_payloads == [{"value": "expected"}]
    finally:
        EVENT_HANDLERS.pop(event_type, None)


def test_failed_delivery_rolls_back_consumer_work_and_retries(db: Session) -> None:
    event_type = "test.outbox.failed.v2"

    def failing_handler(session: Session, event: OutboxEvent, _payload: dict[str, object]) -> None:
        session.add(InboxReceipt(consumer_name="should-rollback", event_id=event.id, processed_at=get_datetime_utc()))
        raise RuntimeError("expected handler failure")

    register_event_handler(event_type, "test-failure", failing_handler)
    try:
        event = enqueue_event(
            session=db,
            module_code="platform",
            event_type=event_type,
            tenant_id=None,
            aggregate_id="aggregate-2",
            payload={},
        )
        db.commit()

        assert dispatch_pending_events(session=db) == (0, 1)
        db.commit()
        db.refresh(event)
        delivery = db.exec(
            select(EventDelivery).where(EventDelivery.event_id == event.id)
        ).one()
        assert event.status == OutboxEventStatus.PENDING
        assert delivery.status == EventDeliveryStatus.PENDING
        assert delivery.attempts == 1
        assert delivery.last_error == "DELIVERY_HANDLER_FAILED:RuntimeError"
        assert db.get(InboxReceipt, ("should-rollback", event.id)) is None
    finally:
        EVENT_HANDLERS.pop(event_type, None)


def test_zero_subscriber_policy_is_explicit(db: Session) -> None:
    with pytest.raises(ValueError, match="no delivery targets"):
        enqueue_event(
            session=db,
            module_code="platform",
            event_type="test.outbox.required.v2",
            tenant_id=None,
            aggregate_id="required",
            payload={},
        )

    event = enqueue_event(
        session=db,
        module_code="platform",
        event_type="test.outbox.lifecycle.v2",
        tenant_id=None,
        aggregate_id="lifecycle",
        payload={},
        allow_zero_subscribers=True,
    )
    assert event.status == OutboxEventStatus.COMPLETE
    assert event.completed_at is not None


def test_optional_failure_does_not_block_required_completion(db: Session) -> None:
    event_type = "test.outbox.optional.v2"

    def success(_session: Session, _event: OutboxEvent, _payload: dict[str, object]) -> None:
        return None

    def failure(_session: Session, _event: OutboxEvent, _payload: dict[str, object]) -> None:
        raise RuntimeError("optional failure")

    register_event_handler(event_type, "required-consumer", success)
    register_event_handler(event_type, "optional-consumer", failure, required=False)
    try:
        event = enqueue_event(
            session=db,
            module_code="platform",
            event_type=event_type,
            tenant_id=None,
            aggregate_id="optional",
            payload={},
        )
        db.commit()
        assert dispatch_pending_events(session=db, max_attempts=1) == (1, 1)
        db.commit()
        db.refresh(event)
        deliveries = db.exec(
            select(EventDelivery).where(EventDelivery.event_id == event.id)
        ).all()
        assert event.status == OutboxEventStatus.COMPLETE
        assert {delivery.status for delivery in deliveries} == {
            EventDeliveryStatus.DELIVERED,
            EventDeliveryStatus.DEAD_LETTER,
        }
    finally:
        EVENT_HANDLERS.pop(event_type, None)


def test_external_broker_delivery_completes_after_ack(db: Session) -> None:
    event_type = "test.outbox.broker.v2"
    acknowledgements: list[str] = []
    register_external_broker_delivery(
        event_type,
        "test-broker",
        lambda _session, event, _payload: acknowledgements.append(str(event.id)),
    )
    try:
        event = enqueue_event(
            session=db,
            module_code="platform",
            event_type=event_type,
            tenant_id=None,
            aggregate_id="broker",
            payload={},
        )
        db.commit()
        assert dispatch_pending_events(session=db) == (1, 0)
        db.commit()
        delivery = db.exec(
            select(EventDelivery).where(EventDelivery.event_id == event.id)
        ).one()
        assert delivery.target_type == EventDeliveryTargetType.EXTERNAL_BROKER
        assert delivery.status == EventDeliveryStatus.DELIVERED
        assert acknowledgements == [str(event.id)]
        assert db.get(InboxReceipt, ("test-broker", event.id)) is None
    finally:
        EVENT_HANDLERS.pop(event_type, None)


def test_disabled_consumer_delivery_is_retained_without_retry(db: Session) -> None:
    tenant = db.exec(select(Tenant).where(Tenant.code == "default")).one()
    registry = db.get(ModuleRegistry, "items")
    assert registry is not None
    previous_state = registry.desired_state
    event_type = "test.outbox.consumer-disabled.v2"
    register_event_handler(
        event_type,
        "items-consumer",
        lambda _session, _event, _payload: None,
        consumer_module="items",
    )
    try:
        event = enqueue_event(
            session=db,
            module_code="platform",
            event_type=event_type,
            tenant_id=tenant.id,
            aggregate_id="item-1",
            payload={},
        )
        registry.desired_state = ModuleDesiredState.DISABLED
        db.add(registry)
        db.commit()
        assert dispatch_pending_events(session=db) == (0, 0)
        db.commit()
        delivery = db.exec(
            select(EventDelivery).where(EventDelivery.event_id == event.id)
        ).one()
        assert delivery.status == EventDeliveryStatus.PENDING
        assert delivery.attempts == 0
    finally:
        registry.desired_state = previous_state
        db.add(registry)
        EVENT_HANDLERS.pop(event_type, None)
        db.commit()


def test_expired_delivery_lease_is_reclaimed(db: Session) -> None:
    event_type = "test.outbox.lease.v2"
    calls: list[str] = []
    register_event_handler(
        event_type,
        "lease-consumer",
        lambda _session, _event, _payload: calls.append("called"),
    )
    try:
        event = enqueue_event(
            session=db,
            module_code="platform",
            event_type=event_type,
            tenant_id=None,
            aggregate_id="lease",
            payload={},
        )
        db.commit()
        delivery = db.exec(
            select(EventDelivery).where(EventDelivery.event_id == event.id)
        ).one()
        delivery.status = EventDeliveryStatus.PROCESSING
        delivery.locked_by = "dead-worker"
        delivery.locked_until = get_datetime_utc() - timedelta(seconds=1)
        db.add(delivery)
        db.commit()

        assert dispatch_pending_events(session=db, worker_id="recovery-worker") == (1, 0)
        db.commit()
        assert calls == ["called"]
    finally:
        EVENT_HANDLERS.pop(event_type, None)
