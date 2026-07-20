from sqlmodel import Session, func, select

from app.modules.contracts import (
    EventContract,
    MigrationSpec,
    ModuleDefinition,
    ReferenceGuardSpec,
)
from app.modules.items.infrastructure.models import Item
from app.modules.items.routes import router


def count_item_references(
    session: Session, reference_type: str, reference_id, tenant_id=None
) -> int:
    if reference_type != "user":
        return 0
    statement = select(func.count()).select_from(Item).where(Item.owner_id == reference_id)
    if tenant_id is not None:
        statement = statement.where(Item.tenant_id == tenant_id)
    return int(session.exec(statement).one())


definition = ModuleDefinition(
    code="items",
    version="1.0.0",
    dependencies=("platform",),
    routers=(router,),
    api_prefix="/api/v1/items",
    permission_prefix="business:item",
    migration=MigrationSpec(
        namespace="items",
        schema="items",
        owned_tables=("item",),
    ),
    reference_guards=(ReferenceGuardSpec("user", count_item_references),),
    event_publishers=(
        EventContract("items.item.changed", 1),
    ),
    menus=(
        "business:item:list",
        "business:item:create",
        "business:item:update",
        "business:item:delete",
    ),
)
