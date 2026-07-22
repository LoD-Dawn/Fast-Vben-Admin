"""Database implementation of the module schedule tenant directory."""

import uuid

from sqlmodel import Session, select

from app.modules.access import evaluate_module_access
from app.platform.core.tenancy_models import Tenant


class SqlEnabledModuleTenantDirectory:
    def __init__(self, session: Session) -> None:
        self._session = session

    def list_enabled_tenant_ids(self, *, module_code: str) -> tuple[uuid.UUID, ...]:
        tenant_ids = self._session.exec(
            select(Tenant.id).where(Tenant.is_active.is_(True)).order_by(Tenant.id)
        ).all()
        return tuple(
            tenant_id
            for tenant_id in tenant_ids
            if evaluate_module_access(
                session=self._session, tenant_id=tenant_id, module_code=module_code
            ).allowed
        )
