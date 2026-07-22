"""Transactional idempotency receipts for public ERP write commands."""

import hashlib
import json
import uuid
from dataclasses import dataclass
from datetime import timedelta
from typing import Any

from sqlalchemy.exc import IntegrityError
from sqlmodel import select

from app.core.clock import get_datetime_utc
from app.modules.erp.infrastructure.models import CommandReceipt, CommandReceiptStatus
from app.modules.erp.infrastructure.tenant_uow import ErpTenantUnitOfWork


class IdempotencyConflictError(ValueError):
    """The caller reused a key for a different command payload."""


class IdempotencyInProgressError(ValueError):
    """A concurrent request still owns the idempotency key."""


@dataclass(frozen=True)
class CommandReceiptClaim:
    receipt: CommandReceipt
    replay: bool


def _sha256(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def validate_idempotency_key(key: str) -> str:
    if not 1 <= len(key) <= 128 or any(ord(character) < 32 or ord(character) > 126 for character in key):
        raise IdempotencyConflictError("Idempotency-Key must be 1 to 128 printable ASCII characters")
    return key


def request_sha256(
    *,
    command_name: str,
    actor_id: uuid.UUID,
    payload: Any,
    resource_id: uuid.UUID | None = None,
) -> str:
    """Hash command semantics without retaining the original request body."""

    canonical = json.dumps(
        {
            "actor_id": str(actor_id),
            "command_name": command_name,
            "payload": payload,
            "resource_id": str(resource_id) if resource_id is not None else None,
        },
        ensure_ascii=True,
        separators=(",", ":"),
        sort_keys=True,
    )
    return _sha256(canonical)


def claim_command(
    *,
    uow: ErpTenantUnitOfWork,
    command_name: str,
    idempotency_key: str,
    request_hash: str,
) -> CommandReceiptClaim:
    """Reserve a receipt, or return the completed receipt for a safe replay."""

    key_hash = _sha256(validate_idempotency_key(idempotency_key))
    statement = select(CommandReceipt).where(
        CommandReceipt.command_name == command_name,
        CommandReceipt.idempotency_key_sha256 == key_hash,
    )
    receipt = uow.session.exec(statement.with_for_update()).first()
    claimed_now = False
    if receipt is None:
        receipt = CommandReceipt(
            tenant_id=uow.tenant_id,
            command_name=command_name,
            idempotency_key_sha256=key_hash,
            request_sha256=request_hash,
            expires_at=get_datetime_utc() + timedelta(days=7),
        )
        try:
            # A savepoint keeps a duplicate-key race from rolling back the
            # surrounding document transaction.
            with uow.session.begin_nested():
                uow.session.add(receipt)
                uow.session.flush()
            claimed_now = True
        except IntegrityError:
            receipt = uow.session.exec(statement.with_for_update()).one()

    if receipt.request_sha256 != request_hash:
        raise IdempotencyConflictError("Idempotency-Key has already been used for a different request")
    if claimed_now:
        return CommandReceiptClaim(receipt=receipt, replay=False)
    if receipt.status == CommandReceiptStatus.COMPLETED:
        return CommandReceiptClaim(receipt=receipt, replay=True)
    raise IdempotencyInProgressError("A request with this Idempotency-Key is still processing")


def complete_command(
    *,
    receipt: CommandReceipt,
    resource_type: str,
    resource_id: uuid.UUID,
    resource_version: int,
) -> None:
    receipt.resource_type = resource_type
    receipt.resource_id = resource_id
    receipt.resource_version = resource_version
    receipt.status = CommandReceiptStatus.COMPLETED
    receipt.completed_at = get_datetime_utc()
