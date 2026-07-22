"""Reusable SQL predicates for ERP document lists and CSV exports."""

import uuid
from datetime import datetime
from typing import Any

from sqlalchemy import or_
from sqlmodel import select


def document_list_filters(
    *,
    model: Any,
    item_model: Any,
    item_document_column: Any,
    counterparty_id_column: Any,
    counterparty_name_column: Any,
    scope: Any,
    keyword: str | None,
    product_id: uuid.UUID | None,
    counterparty_id: uuid.UUID | None,
    owner_id: uuid.UUID | None,
    status: str | None,
    remark: str | None,
    business_from: datetime | None,
    business_to: datetime | None,
) -> list[Any]:
    if business_from is not None and business_to is not None and business_from > business_to:
        raise ValueError("Start time must not be after end time")

    filters = [scope] if scope is not None else []
    if keyword:
        pattern = f"%{keyword}%"
        filters.append(
            or_(
                model.no.ilike(pattern),
                model.remark.ilike(pattern),
                counterparty_name_column.ilike(pattern),
                model.id.in_(
                    select(item_document_column).where(item_model.product_name.ilike(pattern))
                ),
            )
        )
    if product_id is not None:
        filters.append(
            model.id.in_(
                select(item_document_column).where(item_model.product_id == product_id)
            )
        )
    if counterparty_id is not None:
        filters.append(counterparty_id_column == counterparty_id)
    if owner_id is not None:
        filters.append(model.owner_id == owner_id)
    if status is not None:
        filters.append(model.status == status)
    if remark:
        filters.append(model.remark.ilike(f"%{remark}%"))
    if business_from is not None:
        filters.append(model.business_at >= business_from)
    if business_to is not None:
        filters.append(model.business_at <= business_to)
    return filters


def financial_document_filters(
    *,
    model: Any,
    counterparty_id_column: Any,
    counterparty_name_column: Any,
    scope: Any,
    keyword: str | None,
    counterparty_id: uuid.UUID | None,
    owner_id: uuid.UUID | None,
    status: str | None,
    remark: str | None,
    business_from: datetime | None,
    business_to: datetime | None,
) -> list[Any]:
    if business_from is not None and business_to is not None and business_from > business_to:
        raise ValueError("Start time must not be after end time")
    filters = [scope] if scope is not None else []
    if keyword:
        pattern = f"%{keyword}%"
        filters.append(
            or_(
                model.no.ilike(pattern),
                model.remark.ilike(pattern),
                counterparty_name_column.ilike(pattern),
            )
        )
    if counterparty_id is not None:
        filters.append(counterparty_id_column == counterparty_id)
    if owner_id is not None:
        filters.append(model.owner_id == owner_id)
    if status is not None:
        filters.append(model.status == status)
    if remark:
        filters.append(model.remark.ilike(f"%{remark}%"))
    if business_from is not None:
        filters.append(model.business_at >= business_from)
    if business_to is not None:
        filters.append(model.business_at <= business_to)
    return filters


def stock_document_filters(
    *,
    model: Any,
    item_document_column: Any,
    item_product_column: Any,
    item_warehouse_columns: tuple[Any, ...],
    product_model: Any,
    scope: Any,
    keyword: str | None,
    product_id: uuid.UUID | None,
    warehouse_id: uuid.UUID | None,
    owner_id: uuid.UUID | None,
    status: str | None,
    remark: str | None,
    business_from: datetime | None,
    business_to: datetime | None,
) -> list[Any]:
    """Predicates shared by inventory document lists and their CSV exports."""
    if business_from is not None and business_to is not None and business_from > business_to:
        raise ValueError("Start time must not be after end time")

    filters = [scope] if scope is not None else []
    if keyword:
        pattern = f"%{keyword}%"
        matching_items = (
            select(item_document_column)
            .join(product_model, item_product_column == product_model.id)
            .where(
                or_(
                    product_model.code.ilike(pattern),
                    product_model.name.ilike(pattern),
                )
            )
        )
        filters.append(
            or_(
                model.no.ilike(pattern),
                model.remark.ilike(pattern),
                model.id.in_(matching_items),
            )
        )
    if product_id is not None:
        filters.append(
            model.id.in_(
                select(item_document_column).where(item_product_column == product_id)
            )
        )
    if warehouse_id is not None:
        filters.append(
            model.id.in_(
                select(item_document_column).where(
                    or_(*(column == warehouse_id for column in item_warehouse_columns))
                )
            )
        )
    if owner_id is not None:
        filters.append(model.owner_id == owner_id)
    if status is not None:
        filters.append(model.status == status)
    if remark:
        filters.append(model.remark.ilike(f"%{remark}%"))
    if business_from is not None:
        filters.append(model.business_at >= business_from)
    if business_to is not None:
        filters.append(model.business_at <= business_to)
    return filters
