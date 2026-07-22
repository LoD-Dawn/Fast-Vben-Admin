"""Read-only ERP business action-audit HTTP contracts."""

import uuid
from datetime import datetime

from fastapi import APIRouter, Depends
from sqlmodel import col, func, select

from app.modules.erp.infrastructure.models import DocumentAction, DocumentActionLog
from app.modules.erp.infrastructure.tenant_uow import ErpTenantUowDep
from app.modules.erp.observability import ErpDocumentCommandMetricRoute
from app.modules.erp.public_api.dto import (
    DocumentActionLogPublic,
    DocumentActionLogsPublic,
)
from app.platform.web_api import normalize_pagination, require_module_access

router = APIRouter(
    prefix="/erp", tags=["erp-audit"], route_class=ErpDocumentCommandMetricRoute
)


@router.get(
    "/action-logs",
    dependencies=[Depends(require_module_access("erp", "erp:audit:list"))],
    response_model=DocumentActionLogsPublic,
)
def read_document_action_logs(
    uow: ErpTenantUowDep,
    page: int = 1,
    page_size: int = 20,
    resource_type: str | None = None,
    resource_id: uuid.UUID | None = None,
    action: DocumentAction | None = None,
    occurred_from: datetime | None = None,
    occurred_to: datetime | None = None,
) -> DocumentActionLogsPublic:
    """Return append-only audit summaries visible to the current tenant."""

    page, page_size = normalize_pagination(page=page, page_size=page_size)
    filters = []
    if resource_type:
        filters.append(DocumentActionLog.resource_type == resource_type)
    if resource_id:
        filters.append(DocumentActionLog.resource_id == resource_id)
    if action:
        filters.append(DocumentActionLog.action == action)
    if occurred_from:
        filters.append(DocumentActionLog.occurred_at >= occurred_from)
    if occurred_to:
        filters.append(DocumentActionLog.occurred_at <= occurred_to)
    total = int(
        uow.session.exec(
            select(func.count()).select_from(DocumentActionLog).where(*filters)
        ).one()
    )
    records = uow.session.exec(
        select(DocumentActionLog)
        .where(*filters)
        .order_by(col(DocumentActionLog.occurred_at).desc(), col(DocumentActionLog.id).desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
    ).all()
    return DocumentActionLogsPublic(
        items=[DocumentActionLogPublic.model_validate(record) for record in records],
        total=total,
        page=page,
        page_size=page_size,
    )
