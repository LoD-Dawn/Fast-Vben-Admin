import uuid
from typing import Any

from sqlmodel import col, func, select

from app.core.clock import get_datetime_utc
from app.modules.erp.infrastructure.models import (
    Customer,
    Product,
    ProductCategory,
    ProductUnit,
    Supplier,
    Warehouse,
)
from app.modules.erp.infrastructure.tenant_uow import ErpTenantUnitOfWork


class ErpMasterDataRepository:
    """ERP master-data persistence access constrained by a tenant UoW."""

    def __init__(self, uow: ErpTenantUnitOfWork) -> None:
        self._uow = uow

    def get_product_unit(self, resource_id: uuid.UUID) -> ProductUnit | None:
        return self._uow.session.get(ProductUnit, resource_id)

    def get_product_category(self, resource_id: uuid.UUID) -> ProductCategory | None:
        return self._uow.session.get(ProductCategory, resource_id)

    def get_product(self, resource_id: uuid.UUID) -> Product | None:
        return self._uow.session.get(Product, resource_id)

    def get_warehouse(self, resource_id: uuid.UUID) -> Warehouse | None:
        return self._uow.session.get(Warehouse, resource_id)

    def get_supplier(self, resource_id: uuid.UUID) -> Supplier | None:
        return self._uow.session.get(Supplier, resource_id)

    def get_customer(self, resource_id: uuid.UUID) -> Customer | None:
        return self._uow.session.get(Customer, resource_id)

    def list_product_units(
        self, *, page: int, page_size: int, keyword: str | None
    ) -> tuple[list[ProductUnit], int]:
        filters = self._keyword_filters(ProductUnit, keyword)
        return self._list(ProductUnit, page=page, page_size=page_size, filters=filters)

    def list_product_categories(
        self, *, page: int, page_size: int, keyword: str | None
    ) -> tuple[list[ProductCategory], int]:
        filters = self._keyword_filters(ProductCategory, keyword)
        return self._list(
            ProductCategory, page=page, page_size=page_size, filters=filters
        )

    def list_products(
        self, *, page: int, page_size: int, keyword: str | None
    ) -> tuple[list[Product], int]:
        filters = self._keyword_filters(Product, keyword)
        return self._list(Product, page=page, page_size=page_size, filters=filters)

    def list_warehouses(
        self, *, page: int, page_size: int, keyword: str | None
    ) -> tuple[list[Warehouse], int]:
        filters = self._keyword_filters(Warehouse, keyword)
        return self._list(Warehouse, page=page, page_size=page_size, filters=filters)

    def list_suppliers(
        self,
        *,
        page: int,
        page_size: int,
        keyword: str | None,
        name: str | None,
        mobile: str | None,
        phone: str | None,
    ) -> tuple[list[Supplier], int]:
        filters = self._counterparty_filters(
            Supplier,
            keyword=keyword,
            name=name,
            mobile=mobile,
            phone=phone,
        )
        return self._list(Supplier, page=page, page_size=page_size, filters=filters)

    def list_customers(
        self,
        *,
        page: int,
        page_size: int,
        keyword: str | None,
        name: str | None,
        mobile: str | None,
        phone: str | None,
    ) -> tuple[list[Customer], int]:
        filters = self._counterparty_filters(
            Customer,
            keyword=keyword,
            name=name,
            mobile=mobile,
            phone=phone,
        )
        return self._list(Customer, page=page, page_size=page_size, filters=filters)

    def has_category_dependents(self, category_id: uuid.UUID) -> bool:
        return bool(
            self._uow.session.exec(
                select(ProductCategory.id).where(ProductCategory.parent_id == category_id)
            ).first()
            or self._uow.session.exec(
                select(Product.id).where(Product.category_id == category_id)
            ).first()
        )

    def has_category_children(self, category_id: uuid.UUID) -> bool:
        return (
            self._uow.session.exec(
                select(ProductCategory.id).where(ProductCategory.parent_id == category_id)
            ).first()
            is not None
        )

    def has_unit_dependents(self, unit_id: uuid.UUID) -> bool:
        return self._uow.session.exec(
            select(Product.id).where(Product.unit_id == unit_id)
        ).first() is not None

    def add(self, entity: Any) -> Any:
        self._uow.session.add(entity)
        return entity

    def update(self, entity: Any, values: dict[str, Any]) -> Any:
        entity.sqlmodel_update(values)
        entity.updated_at = get_datetime_utc()
        self._uow.session.add(entity)
        return entity

    def delete(self, entity: Any) -> None:
        self._uow.session.delete(entity)

    def _list(
        self, model: Any, *, page: int, page_size: int, filters: list[Any]
    ) -> tuple[list[Any], int]:
        count = self._uow.session.exec(
            select(func.count()).select_from(model).where(*filters)
        ).one()
        items = self._uow.session.exec(
            select(model)
            .where(*filters)
            .order_by(col(model.created_at).desc())
            .offset((page - 1) * page_size)
            .limit(page_size)
        ).all()
        return items, int(count)

    def _list_by_name(
        self, model: Any, *, page: int, page_size: int, keyword: str | None
    ) -> tuple[list[Any], int]:
        filters = []
        if keyword:
            pattern = f"%{keyword}%"
            filters = [
                (col(model.name).ilike(pattern)) | (col(model.contact_name).ilike(pattern))
            ]
        return self._list(model, page=page, page_size=page_size, filters=filters)

    @staticmethod
    def _counterparty_filters(
        model: Any,
        *,
        keyword: str | None,
        name: str | None,
        mobile: str | None,
        phone: str | None,
    ) -> list[Any]:
        filters = []
        if keyword:
            pattern = f"%{keyword}%"
            filters.append(
                (col(model.name).ilike(pattern)) | (col(model.contact_name).ilike(pattern))
            )
        if name:
            filters.append(col(model.name).ilike(f"%{name}%"))
        if mobile:
            filters.append(col(model.mobile).ilike(f"%{mobile}%"))
        if phone:
            filters.append(col(model.phone).ilike(f"%{phone}%"))
        return filters

    @staticmethod
    def _keyword_filters(model: Any, keyword: str | None) -> list[Any]:
        if not keyword:
            return []
        pattern = f"%{keyword}%"
        return [(col(model.code).ilike(pattern)) | (col(model.name).ilike(pattern))]
