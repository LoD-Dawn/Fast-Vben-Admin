"""Append-only ERP business-action audit records."""

import uuid
from collections.abc import Mapping

from app.modules.erp.infrastructure.models import DocumentAction, DocumentActionLog
from app.modules.erp.infrastructure.tenant_uow import ErpTenantUnitOfWork


def record_action(
    *,
    uow: ErpTenantUnitOfWork,
    resource_type: str,
    resource_id: uuid.UUID,
    action: DocumentAction,
    actor_id: uuid.UUID,
    resource_no: str | None = None,
    old_status: str | None = None,
    new_status: str | None = None,
    old_version: int | None = None,
    new_version: int | None = None,
    reason: str | None = None,
    metadata: Mapping[str, object] | None = None,
) -> None:
    """Append an audit event; callers must only pass non-sensitive summaries."""

    uow.session.add(
        DocumentActionLog(
            tenant_id=uow.tenant_id,
            resource_type=resource_type,
            resource_id=resource_id,
            resource_no=resource_no,
            action=action,
            old_status=old_status,
            new_status=new_status,
            old_version=old_version,
            new_version=new_version,
            actor_id=actor_id,
            reason=reason,
            metadata_json=dict(metadata or {}),
        )
    )
