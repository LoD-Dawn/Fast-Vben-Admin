import uuid

import pytest
from sqlalchemy import delete, text
from sqlmodel import Session, select

from app.core.database import engine
from app.models import Tenant
from app.modules.items.infrastructure.models import Item
from app.modules.items.infrastructure.repository import ItemsRepository
from app.modules.items.infrastructure.tenant_uow import (
    ItemsTenantUnitOfWork,
    TenantScopeError,
)


def test_items_tenant_uow_enforces_read_write_and_bulk_boundaries(db: Session) -> None:
    default_tenant = db.exec(select(Tenant).where(Tenant.code == "default")).one()
    other_tenant = Tenant(code=f"uow-{uuid.uuid4().hex[:12]}", name="UoW tenant")
    db.add(other_tenant)
    db.flush()
    other_item = Item(
        title="other tenant item",
        owner_id=uuid.uuid4(),
        tenant_id=other_tenant.id,
    )
    db.add(other_item)
    db.commit()

    try:
        with Session(engine) as session:
            with ItemsTenantUnitOfWork(session, default_tenant.id) as uow:
                repository = ItemsRepository(uow)
                assert repository.get(other_item.id) is None
                assert session.exec(
                    text("SELECT current_setting('app.tenant_id', true)")
                ).one()[0] == str(default_tenant.id)

                repository.add(
                    Item(
                        title="wrong tenant item",
                        owner_id=uuid.uuid4(),
                        tenant_id=other_tenant.id,
                    )
                )
                with pytest.raises(TenantScopeError, match="does not match"):
                    session.flush()
                session.rollback()

            with ItemsTenantUnitOfWork(session, default_tenant.id):
                with pytest.raises(TenantScopeError, match="bulk DML"):
                    session.exec(delete(Item).where(Item.id == other_item.id))
    finally:
        db.delete(other_item)
        db.delete(other_tenant)
        db.commit()
