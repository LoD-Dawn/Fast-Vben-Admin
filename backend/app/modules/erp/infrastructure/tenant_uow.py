"""Tenant-scoped database boundary for the ERP business module."""

import uuid
from collections.abc import Generator
from dataclasses import dataclass
from typing import Annotated, Any

from fastapi import Depends
from sqlalchemy import event, inspect, text
from sqlalchemy.orm import with_loader_criteria
from sqlmodel import Session

from app.modules.erp.infrastructure.models import (
    ERP_TENANT_SCOPED_MODELS,
    DocumentActionLog,
    StockLedger,
)
from app.platform.web_api import CurrentTenant, SessionDep


class TenantScopeError(RuntimeError):
    """Raised when an ERP operation escapes its tenant boundary."""


@dataclass
class ErpTenantUnitOfWork:
    session: Session
    tenant_id: uuid.UUID

    def __enter__(self) -> ErpTenantUnitOfWork:
        existing = self.session.info.get("erp_tenant_id")
        if existing is not None and existing != self.tenant_id:
            raise TenantScopeError("A session cannot serve multiple tenants")
        self.session.info["erp_tenant_id"] = self.tenant_id
        if self.session.in_transaction():
            self.session.execute(
                text("SELECT set_config('app.tenant_id', :tenant_id, true)"),
                {"tenant_id": str(self.tenant_id)},
            )
        return self

    def __exit__(self, exc_type: Any, exc_value: Any, traceback: Any) -> None:
        if self.session.in_transaction():
            self.session.execute(text("SELECT set_config('app.tenant_id', '', true)"))
        self.session.info.pop("erp_tenant_id", None)
        self.session.expire_all()


def get_erp_tenant_uow(
    session: SessionDep, tenant_context: CurrentTenant
) -> Generator[ErpTenantUnitOfWork]:
    with ErpTenantUnitOfWork(session=session, tenant_id=tenant_context.tenant_id) as uow:
        yield uow


ErpTenantUowDep = Annotated[ErpTenantUnitOfWork, Depends(get_erp_tenant_uow)]


@event.listens_for(Session, "after_begin")
def set_transaction_tenant(session: Session, transaction: Any, connection: Any) -> None:
    tenant_id = session.info.get("erp_tenant_id")
    if tenant_id is None or transaction.nested:
        return
    connection.execute(
        text("SELECT set_config('app.tenant_id', :tenant_id, true)"),
        {"tenant_id": str(tenant_id)},
    )


@event.listens_for(Session, "do_orm_execute")
def enforce_erp_query_scope(execute_state: Any) -> None:
    tenant_id = execute_state.session.info.get("erp_tenant_id")
    if tenant_id is None:
        return
    if execute_state.is_update or execute_state.is_delete:
        raise TenantScopeError("Tenant UnitOfWork forbids ORM bulk DML")
    if execute_state.is_select:
        for model in ERP_TENANT_SCOPED_MODELS:
            execute_state.statement = execute_state.statement.options(
                with_loader_criteria(
                    model,
                    lambda entity: entity.tenant_id == tenant_id,
                    include_aliases=True,
                )
            )


@event.listens_for(Session, "before_flush")
def enforce_erp_write_scope(
    session: Session, _flush_context: Any, _instances: Any
) -> None:
    tenant_id = session.info.get("erp_tenant_id")
    if tenant_id is None:
        return
    for entity in session.deleted:
        if isinstance(entity, (DocumentActionLog, StockLedger)):
            raise TenantScopeError("ERP append-only record is immutable")
    for entity in (*session.new, *session.dirty):
        if not isinstance(entity, ERP_TENANT_SCOPED_MODELS):
            continue
        if isinstance(entity, (DocumentActionLog, StockLedger)) and entity in session.dirty:
            raise TenantScopeError("ERP append-only record is immutable")
        if entity.tenant_id != tenant_id:
            raise TenantScopeError("ERP tenant_id does not match the active tenant")
        if entity in session.dirty and inspect(entity).attrs.tenant_id.history.has_changes():
            raise TenantScopeError("ERP tenant_id is immutable")
