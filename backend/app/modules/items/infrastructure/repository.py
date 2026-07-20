import uuid
from typing import Any

from sqlmodel import col, func, select

from app.modules.items.infrastructure.models import Item, get_datetime_utc
from app.modules.items.infrastructure.tenant_uow import ItemsTenantUnitOfWork


class ItemsRepository:
    """Items persistence access constrained by an active TenantUnitOfWork."""

    def __init__(self, uow: ItemsTenantUnitOfWork) -> None:
        self._uow = uow

    def get(self, item_id: uuid.UUID) -> Item | None:
        return self._uow.session.get(Item, item_id)

    def list(
        self,
        *,
        page: int,
        page_size: int,
        filters: list[Any],
    ) -> tuple[list[Item], int]:
        count = self._uow.session.exec(
            select(func.count()).select_from(Item).where(*filters)
        ).one()
        items = self._uow.session.exec(
            select(Item)
            .where(*filters)
            .order_by(col(Item.created_at).desc())
            .offset((page - 1) * page_size)
            .limit(page_size)
        ).all()
        return items, int(count)

    def all(self, *, filters: list[Any]) -> list[Item]:
        return self._uow.session.exec(
            select(Item).where(*filters).order_by(col(Item.created_at).desc())
        ).all()

    def add(self, item: Item) -> Item:
        self._uow.session.add(item)
        return item

    def update(self, item: Item, values: dict[str, Any]) -> Item:
        item.sqlmodel_update(values)
        item.updated_at = get_datetime_utc()
        self._uow.session.add(item)
        return item

    def delete(self, item: Item) -> None:
        self._uow.session.delete(item)
