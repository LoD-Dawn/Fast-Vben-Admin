import json
import logging
import uuid
from collections.abc import Callable
from dataclasses import dataclass
from datetime import timedelta
from typing import Any

from sqlalchemy import or_
from sqlmodel import Session, col, func, select

from app.core.clock import get_datetime_utc
from app.modules.access import evaluate_module_access
from app.platform.core.runtime_models import (
    EventDelivery,
    EventDeliveryStatus,
    EventDeliveryTargetType,
    InboxReceipt,
    OutboxEvent,
    OutboxEventStatus,
)
from app.platform.tenant_uow import PlatformTenantUnitOfWork

logger = logging.getLogger(__name__)

EventHandler = Callable[[Session, OutboxEvent, dict[str, Any]], None]


@dataclass(frozen=True)
class EventHandlerRegistration:
    consumer_name: str
    handler: EventHandler
    consumer_module: str
    required: bool
    target_type: EventDeliveryTargetType


EVENT_HANDLERS: dict[str, list[EventHandlerRegistration]] = {}


def register_event_handler(
    event_type: str,
    consumer_name: str,
    handler: EventHandler,
    *,
    consumer_module: str = "platform",
    required: bool = True,
) -> None:
    registrations = EVENT_HANDLERS.setdefault(event_type, [])
    if any(entry.consumer_name == consumer_name for entry in registrations):
        raise ValueError(f"Duplicate event consumer: {consumer_name}")
    registrations.append(
        EventHandlerRegistration(
            consumer_name=consumer_name,
            handler=handler,
            consumer_module=consumer_module,
            required=required,
            target_type=EventDeliveryTargetType.LOCAL_CONSUMER,
        )
    )


def register_external_broker_delivery(
    event_type: str,
    target_name: str,
    publish: EventHandler,
    *,
    required: bool = True,
) -> None:
    """Register a broker publisher that returns only after broker acknowledgement."""
    registrations = EVENT_HANDLERS.setdefault(event_type, [])
    if any(entry.consumer_name == target_name for entry in registrations):
        raise ValueError(f"Duplicate event consumer: {target_name}")
    registrations.append(
        EventHandlerRegistration(
            consumer_name=target_name,
            handler=publish,
            consumer_module="",
            required=required,
            target_type=EventDeliveryTargetType.EXTERNAL_BROKER,
        )
    )


def enqueue_event(
    *,
    session: Session,
    module_code: str,
    event_type: str,
    tenant_id,
    aggregate_id: str,
    payload: dict[str, Any],
    event_version: int = 1,
    trace_id: str | None = None,
    aggregate_sequence: int | None = None,
    allow_zero_subscribers: bool = False,
) -> OutboxEvent:
    registrations = EVENT_HANDLERS.get(event_type, [])
    if not registrations and not allow_zero_subscribers:
        raise ValueError(
            f"Event {event_type} has no delivery targets; "
            "set allow_zero_subscribers only for notification events"
        )
    now = get_datetime_utc()
    event = OutboxEvent(
        module_code=module_code,
        event_type=event_type,
        event_version=event_version,
        tenant_id=tenant_id,
        aggregate_id=aggregate_id,
        aggregate_sequence=aggregate_sequence,
        payload=json.dumps(payload, ensure_ascii=False, separators=(",", ":")),
        trace_id=trace_id,
        occurred_at=now,
        available_at=now,
    )
    if not registrations:
        event.status = OutboxEventStatus.COMPLETE
        event.completed_at = now
    session.add(event)
    # EventDelivery only stores the event ID instead of an ORM relationship, so
    # flush the parent first to keep the database foreign-key ordering explicit.
    session.flush()
    for registration in registrations:
        session.add(
            EventDelivery(
                event_id=event.id,
                target_name=registration.consumer_name,
                target_type=registration.target_type,
                consumer_module=registration.consumer_module or None,
                is_required=registration.required,
                available_at=now,
            )
        )
    return event


def count_pending_events(*, session: Session, module_code: str) -> int:
    """Return the current pending event count for one module."""

    return int(
        session.exec(
            select(func.count())
            .select_from(OutboxEvent)
            .where(
                OutboxEvent.module_code == module_code,
                OutboxEvent.status == OutboxEventStatus.PENDING,
            )
        ).one()
    )


def dispatch_pending_events(
    *,
    session: Session,
    max_events: int = 100,
    max_attempts: int = 8,
    worker_id: str | None = None,
    lease_seconds: int = 60,
) -> tuple[int, int]:
    """Dispatch individual delivery targets with lease-based, at-least-once semantics."""
    now = get_datetime_utc()
    worker_id = worker_id or f"worker-{uuid.uuid4()}"
    deliveries = session.exec(
        select(EventDelivery)
        .where(
            EventDelivery.status.in_(
                [EventDeliveryStatus.PENDING, EventDeliveryStatus.PROCESSING]
            ),
            EventDelivery.available_at <= now,
            or_(
                EventDelivery.locked_until.is_(None),
                EventDelivery.locked_until <= now,
            ),
        )
        .order_by(col(EventDelivery.available_at), col(EventDelivery.id))
        .limit(max_events)
        .with_for_update(skip_locked=True)
    ).all()
    delivered = 0
    failed = 0
    for delivery in deliveries:
        event = session.get(OutboxEvent, delivery.event_id)
        if event is None:
            continue
        if not _delivery_can_run(session=session, delivery=delivery, event=event):
            continue
        delivery.status = EventDeliveryStatus.PROCESSING
        delivery.locked_by = worker_id
        delivery.locked_until = now + timedelta(seconds=lease_seconds)
        session.add(delivery)
        registration = _registration_for_delivery(event.event_type, delivery.target_name)
        if registration is None:
            _record_delivery_failure(
                session=session,
                delivery=delivery,
                event=event,
                error="DELIVERY_TARGET_UNAVAILABLE",
                max_attempts=max_attempts,
            )
            failed += 1
            continue
        if (
            delivery.target_type == EventDeliveryTargetType.LOCAL_CONSUMER
            and delivery.consumer_module != "platform"
            and event.tenant_id is not None
        ):
            with PlatformTenantUnitOfWork(
                session, event.tenant_id, privileged=True
            ):
                decision = evaluate_module_access(
                    session=session,
                    tenant_id=event.tenant_id,
                    module_code=delivery.consumer_module or "platform",
                )
            if not decision.allowed:
                # A disabled consumer retains work without consuming retry budget.
                delivery.status = EventDeliveryStatus.PENDING
                delivery.locked_by = None
                delivery.locked_until = None
                session.add(delivery)
                continue
        try:
            payload = json.loads(event.payload)
            if not isinstance(payload, dict):
                raise ValueError("Outbox payload must be an object")
            receipt = (
                session.get(InboxReceipt, (delivery.target_name, event.id))
                if delivery.target_type == EventDeliveryTargetType.LOCAL_CONSUMER
                else None
            )
            if receipt is None:
                with session.begin_nested():
                    registration.handler(session, event, payload)
                    if delivery.target_type == EventDeliveryTargetType.LOCAL_CONSUMER:
                        session.add(
                            InboxReceipt(
                                consumer_name=delivery.target_name,
                                event_id=event.id,
                                processed_at=get_datetime_utc(),
                            )
                        )
            delivery.status = EventDeliveryStatus.DELIVERED
            delivery.delivered_at = get_datetime_utc()
            delivery.locked_by = None
            delivery.locked_until = None
            delivery.last_error = None
            session.add(delivery)
            _refresh_event_status(session=session, event=event)
            delivered += 1
        except Exception as exc:  # Event handlers must not terminate the worker loop.
            _record_delivery_failure(
                session=session,
                delivery=delivery,
                event=event,
                error=_delivery_error(exc),
                max_attempts=max_attempts,
            )
            logger.exception("Outbox delivery %s failed", delivery.id)
            failed += 1
    return delivered, failed


def requeue_dead_letter(*, session: Session, event: OutboxEvent) -> None:
    event.status = OutboxEventStatus.PENDING
    event.attempts = 0
    event.last_error = None
    event.dead_lettered_at = None
    event.completed_at = None
    session.add(event)
    for delivery in session.exec(
        select(EventDelivery).where(EventDelivery.event_id == event.id)
    ).all():
        if delivery.status != EventDeliveryStatus.DEAD_LETTER:
            continue
        delivery.status = EventDeliveryStatus.PENDING
        delivery.attempts = 0
        delivery.available_at = get_datetime_utc()
        delivery.locked_by = None
        delivery.locked_until = None
        delivery.dead_lettered_at = None
        delivery.last_error = None
        session.add(delivery)


def _registration_for_delivery(
    event_type: str, target_name: str
) -> EventHandlerRegistration | None:
    return next(
        (
            registration
            for registration in EVENT_HANDLERS.get(event_type, [])
            if registration.consumer_name == target_name
        ),
        None,
    )


def _delivery_can_run(
    *, session: Session, delivery: EventDelivery, event: OutboxEvent
) -> bool:
    if event.aggregate_sequence is None:
        return True
    prior_delivery = session.exec(
        select(EventDelivery.id)
        .join(OutboxEvent, OutboxEvent.id == EventDelivery.event_id)
        .where(
            OutboxEvent.module_code == event.module_code,
            OutboxEvent.aggregate_id == event.aggregate_id,
            OutboxEvent.aggregate_sequence < event.aggregate_sequence,
            EventDelivery.target_name == delivery.target_name,
            EventDelivery.is_required.is_(True),
            EventDelivery.status != EventDeliveryStatus.DELIVERED,
        )
        .limit(1)
    ).first()
    return prior_delivery is None


def _record_delivery_failure(
    *,
    session: Session,
    delivery: EventDelivery,
    event: OutboxEvent,
    error: str,
    max_attempts: int,
) -> None:
    delivery.attempts += 1
    delivery.last_error = error[:2000]
    delivery.locked_by = None
    delivery.locked_until = None
    if delivery.attempts >= max_attempts:
        delivery.status = EventDeliveryStatus.DEAD_LETTER
        delivery.dead_lettered_at = get_datetime_utc()
    else:
        delivery.status = EventDeliveryStatus.PENDING
        delivery.available_at = get_datetime_utc() + timedelta(
            seconds=min(300, 2**delivery.attempts)
        )
    session.add(delivery)
    _refresh_event_status(session=session, event=event)


def _delivery_error(exc: Exception) -> str:
    """Persist a stable, non-sensitive failure classification for operators."""
    return f"DELIVERY_HANDLER_FAILED:{type(exc).__name__}"


def _refresh_event_status(*, session: Session, event: OutboxEvent) -> None:
    deliveries = session.exec(
        select(EventDelivery).where(EventDelivery.event_id == event.id)
    ).all()
    required_deliveries = [delivery for delivery in deliveries if delivery.is_required]
    event.attempts = max((delivery.attempts for delivery in deliveries), default=0)
    required_dead = any(
        delivery.status == EventDeliveryStatus.DEAD_LETTER
        for delivery in required_deliveries
    )
    required_complete = all(
        delivery.status == EventDeliveryStatus.DELIVERED
        for delivery in required_deliveries
    )
    if required_dead:
        event.status = OutboxEventStatus.DEAD_LETTER
        event.dead_lettered_at = get_datetime_utc()
        event.completed_at = None
        event.last_error = next(
            (
                delivery.last_error
                for delivery in required_deliveries
                if delivery.status == EventDeliveryStatus.DEAD_LETTER
            ),
            None,
        )
    elif required_complete:
        event.status = OutboxEventStatus.COMPLETE
        event.completed_at = get_datetime_utc()
        event.dead_lettered_at = None
        event.last_error = None
    else:
        event.status = OutboxEventStatus.PENDING
        event.completed_at = None
    session.add(event)
