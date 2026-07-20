"""Tenant-scoped database boundary for the Items business module."""

import uuid
from collections.abc import Generator
from dataclasses import dataclass
from typing import Annotated, Any

from fastapi import Depends
from sqlalchemy import event, inspect, text
from sqlalchemy.orm import with_loader_criteria
from sqlmodel import Session

from app.modules.items.infrastructure.models import Item
from app.platform.web_api import CurrentTenant, SessionDep


class TenantScopeError(RuntimeError):
    """Raised when a business data operation escapes its tenant boundary."""


@dataclass
class ItemsTenantUnitOfWork:
    session: Session
    tenant_id: uuid.UUID

    def __enter__(self) -> ItemsTenantUnitOfWork:
        existing = self.session.info.get("items_tenant_id")
        if existing is not None and existing != self.tenant_id:
            raise TenantScopeError("A session cannot serve multiple tenants")
        self.session.info["items_tenant_id"] = self.tenant_id
        return self

    def __exit__(self, exc_type: Any, exc_value: Any, traceback: Any) -> None:
        self.session.info.pop("items_tenant_id", None)


def get_items_tenant_uow(
    session: SessionDep, tenant_context: CurrentTenant
) -> Generator[ItemsTenantUnitOfWork]:
    with ItemsTenantUnitOfWork(session=session, tenant_id=tenant_context.tenant_id) as uow:
        yield uow


ItemsTenantUowDep = Annotated[ItemsTenantUnitOfWork, Depends(get_items_tenant_uow)]


@event.listens_for(Session, "after_begin")
def set_transaction_tenant(session: Session, transaction: Any, connection: Any) -> None:
    tenant_id = session.info.get("items_tenant_id")
    if tenant_id is None or transaction.nested:
        return
    connection.execute(
        text("SELECT set_config('app.tenant_id', :tenant_id, true)"),
        {"tenant_id": str(tenant_id)},
    )


@event.listens_for(Session, "do_orm_execute")
def enforce_items_query_scope(execute_state: Any) -> None:
    tenant_id = execute_state.session.info.get("items_tenant_id")
    if tenant_id is None:
        return
    if execute_state.is_update or execute_state.is_delete:
        raise TenantScopeError("Tenant UnitOfWork forbids ORM bulk DML")
    if execute_state.is_select:
        execute_state.statement = execute_state.statement.options(
            with_loader_criteria(
                Item,
                lambda item: item.tenant_id == tenant_id,
                include_aliases=True,
            )
        )


@event.listens_for(Session, "before_flush")
def enforce_items_write_scope(
    session: Session, _flush_context: Any, _instances: Any
) -> None:
    tenant_id = session.info.get("items_tenant_id")
    if tenant_id is None:
        return
    for item in (*session.new, *session.dirty):
        if not isinstance(item, Item):
            continue
        if item.tenant_id != tenant_id:
            raise TenantScopeError("Item tenant_id does not match the active tenant")
        if item in session.dirty and inspect(item).attrs.tenant_id.history.has_changes():
            raise TenantScopeError("Item tenant_id is immutable")
