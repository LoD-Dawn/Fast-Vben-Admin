"""ERP purchase and sale statistics HTTP contracts."""

from datetime import date, datetime, time, timedelta
from decimal import Decimal
from typing import Any, Literal
from zoneinfo import ZoneInfo

from fastapi import APIRouter, Depends, HTTPException
from sqlmodel import func, select

from app.core.clock import get_datetime_utc
from app.modules.erp.infrastructure.models import (
    DocumentStatus,
    ErpSetting,
    PurchaseIn,
    PurchaseInItem,
    PurchaseReturn,
    PurchaseReturnItem,
    SaleOut,
    SaleOutItem,
    SaleReturn,
    SaleReturnItem,
)
from app.modules.erp.infrastructure.tenant_uow import ErpTenantUowDep
from app.modules.erp.observability import ErpDocumentCommandMetricRoute
from app.modules.erp.public_api.dto import (
    StatisticsAmountsPublic,
    StatisticsSummaryPublic,
    StatisticsTimeSeriesPointPublic,
    StatisticsTimeSeriesPublic,
)
from app.modules.erp.stock_routes import warehouse_document_scope_filter
from app.platform.web_api import (
    CurrentPrincipal,
    build_owner_data_scope_filter,
    require_module_access,
)

router = APIRouter(
    prefix="/erp",
    tags=["erp-statistics"],
    route_class=ErpDocumentCommandMetricRoute,
)

_ZERO = Decimal("0")


def _tenant_timezone(uow: ErpTenantUowDep) -> ZoneInfo:
    setting = uow.session.get(ErpSetting, uow.tenant_id)
    try:
        return ZoneInfo(setting.timezone if setting is not None else "UTC")
    except ValueError as exc:
        raise HTTPException(status_code=409, detail="ERP tenant timezone is invalid") from exc


def _time_range(
    *, timezone: ZoneInfo, start: date, end: date
) -> tuple[datetime, datetime]:
    if end < start:
        raise HTTPException(status_code=422, detail="Statistics end date must not precede start date")
    start_at = datetime.combine(start, time.min, tzinfo=timezone).astimezone(ZoneInfo("UTC"))
    end_at = datetime.combine(
        end + timedelta(days=1), time.min, tzinfo=timezone
    ).astimezone(ZoneInfo("UTC"))
    return start_at, end_at


def _document_scope(
    *,
    uow: ErpTenantUowDep,
    principal: CurrentPrincipal,
    document_id_column: Any,
    owner_column: Any,
    item_document_id_column: Any,
    item_id_column: Any,
    warehouse_column: Any,
) -> Any:
    scope = build_owner_data_scope_filter(
        session=uow.session,
        current_principal=principal,
        tenant_id=uow.tenant_id,
        owner_id_column=owner_column,
    )
    warehouse_scope = warehouse_document_scope_filter(
        current_principal=principal,
        document_id_column=document_id_column,
        item_document_id_column=item_document_id_column,
        item_id_column=item_id_column,
        warehouse_columns=(warehouse_column,),
    )
    return scope if warehouse_scope is None else scope & warehouse_scope


def _amount(
    *,
    uow: ErpTenantUowDep,
    principal: CurrentPrincipal,
    model: Any,
    item_model: Any,
    item_document_id_column: Any,
    warehouse_column: Any,
    start_at: datetime,
    end_at: datetime,
) -> Decimal:
    scope = _document_scope(
        uow=uow,
        principal=principal,
        document_id_column=model.id,
        owner_column=model.owner_id,
        item_document_id_column=item_document_id_column,
        item_id_column=item_model.id,
        warehouse_column=warehouse_column,
    )
    value = uow.session.exec(
        select(func.coalesce(func.sum(model.total_amount), _ZERO)).where(
            model.status == DocumentStatus.APPROVED,
            model.business_at >= start_at,
            model.business_at < end_at,
            scope,
        )
    ).one()
    return Decimal(value)


def _amounts_for_range(
    *, uow: ErpTenantUowDep, principal: CurrentPrincipal, start_at: datetime, end_at: datetime
) -> StatisticsAmountsPublic:
    purchase = _amount(
        uow=uow,
        principal=principal,
        model=PurchaseIn,
        item_model=PurchaseInItem,
        item_document_id_column=PurchaseInItem.purchase_in_id,
        warehouse_column=PurchaseInItem.warehouse_id,
        start_at=start_at,
        end_at=end_at,
    ) - _amount(
        uow=uow,
        principal=principal,
        model=PurchaseReturn,
        item_model=PurchaseReturnItem,
        item_document_id_column=PurchaseReturnItem.purchase_return_id,
        warehouse_column=PurchaseReturnItem.warehouse_id,
        start_at=start_at,
        end_at=end_at,
    )
    sale = _amount(
        uow=uow,
        principal=principal,
        model=SaleOut,
        item_model=SaleOutItem,
        item_document_id_column=SaleOutItem.sale_out_id,
        warehouse_column=SaleOutItem.warehouse_id,
        start_at=start_at,
        end_at=end_at,
    ) - _amount(
        uow=uow,
        principal=principal,
        model=SaleReturn,
        item_model=SaleReturnItem,
        item_document_id_column=SaleReturnItem.sale_return_id,
        warehouse_column=SaleReturnItem.warehouse_id,
        start_at=start_at,
        end_at=end_at,
    )
    return StatisticsAmountsPublic(purchase_amount=purchase, sale_amount=sale)


@router.get(
    "/statistics/summary",
    dependencies=[Depends(require_module_access("erp", "erp:statistics:query"))],
    response_model=StatisticsSummaryPublic,
)
def read_statistics_summary(
    uow: ErpTenantUowDep, principal: CurrentPrincipal
) -> StatisticsSummaryPublic:
    timezone = _tenant_timezone(uow)
    today = get_datetime_utc().astimezone(timezone).date()
    month_start = today.replace(day=1)
    year_start = today.replace(month=1, day=1)
    return StatisticsSummaryPublic(
        today=_amounts_for_range(
            uow=uow,
            principal=principal,
            start_at=_time_range(timezone=timezone, start=today, end=today)[0],
            end_at=_time_range(timezone=timezone, start=today, end=today)[1],
        ),
        yesterday=_amounts_for_range(
            uow=uow,
            principal=principal,
            start_at=_time_range(
                timezone=timezone, start=today - timedelta(days=1), end=today - timedelta(days=1)
            )[0],
            end_at=_time_range(
                timezone=timezone, start=today - timedelta(days=1), end=today - timedelta(days=1)
            )[1],
        ),
        month=_amounts_for_range(
            uow=uow,
            principal=principal,
            start_at=_time_range(timezone=timezone, start=month_start, end=today)[0],
            end_at=_time_range(timezone=timezone, start=month_start, end=today)[1],
        ),
        year=_amounts_for_range(
            uow=uow,
            principal=principal,
            start_at=_time_range(timezone=timezone, start=year_start, end=today)[0],
            end_at=_time_range(timezone=timezone, start=year_start, end=today)[1],
        ),
    )


@router.get(
    "/statistics/time-series",
    dependencies=[Depends(require_module_access("erp", "erp:statistics:query"))],
    response_model=StatisticsTimeSeriesPublic,
)
def read_statistics_time_series(
    uow: ErpTenantUowDep,
    principal: CurrentPrincipal,
    type: Literal["purchase", "sale"],
    start: date,
    end: date,
    granularity: Literal["day", "month"] = "day",
) -> StatisticsTimeSeriesPublic:
    timezone = _tenant_timezone(uow)
    start_at, end_at = _time_range(timezone=timezone, start=start, end=end)
    models = (
        (
            PurchaseIn,
            PurchaseInItem,
            PurchaseInItem.purchase_in_id,
            PurchaseInItem.warehouse_id,
            1,
        ),
        (
            PurchaseReturn,
            PurchaseReturnItem,
            PurchaseReturnItem.purchase_return_id,
            PurchaseReturnItem.warehouse_id,
            -1,
        ),
    ) if type == "purchase" else (
        (SaleOut, SaleOutItem, SaleOutItem.sale_out_id, SaleOutItem.warehouse_id, 1),
        (
            SaleReturn,
            SaleReturnItem,
            SaleReturnItem.sale_return_id,
            SaleReturnItem.warehouse_id,
            -1,
        ),
    )
    amounts: dict[datetime, Decimal] = {}
    for model, item_model, item_document_id, warehouse_column, sign in models:
        scope = _document_scope(
            uow=uow,
            principal=principal,
            document_id_column=model.id,
            owner_column=model.owner_id,
            item_document_id_column=item_document_id,
            item_id_column=item_model.id,
            warehouse_column=warehouse_column,
        )
        period = func.date_trunc(granularity, model.business_at)
        rows = uow.session.exec(
            select(period, func.sum(model.total_amount))
            .where(
                model.status == DocumentStatus.APPROVED,
                model.business_at >= start_at,
                model.business_at < end_at,
                scope,
            )
            .group_by(period)
            .order_by(period)
        ).all()
        for period_start, amount in rows:
            amounts[period_start] = amounts.get(period_start, _ZERO) + sign * Decimal(amount)
    return StatisticsTimeSeriesPublic(
        type=type,
        granularity=granularity,
        items=[
            StatisticsTimeSeriesPointPublic(period_start=period_start, amount=amount)
            for period_start, amount in sorted(amounts.items())
        ],
    )
