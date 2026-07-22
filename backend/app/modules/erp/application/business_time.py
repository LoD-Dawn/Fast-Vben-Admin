"""Tenant-timezone validation for ERP business dates."""

from datetime import datetime
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from fastapi import HTTPException

from app.core.clock import get_datetime_utc
from app.modules.erp.infrastructure.models import ErpSetting
from app.modules.erp.infrastructure.tenant_uow import ErpTenantUowDep


def resolve_business_at(
    *, uow: ErpTenantUowDep, requested_at: datetime | None
) -> datetime:
    """Use now by default and reject a business date after the tenant's today."""

    business_at = requested_at or get_datetime_utc()
    if business_at.tzinfo is None:
        raise HTTPException(status_code=422, detail="Business time must include a timezone")
    setting = uow.session.get(ErpSetting, uow.tenant_id)
    try:
        timezone = ZoneInfo(setting.timezone if setting is not None else "UTC")
    except ZoneInfoNotFoundError as exc:
        raise HTTPException(status_code=409, detail="ERP tenant timezone is invalid") from exc
    today = get_datetime_utc().astimezone(timezone).date()
    if business_at.astimezone(timezone).date() > today:
        raise HTTPException(status_code=422, detail="Business date cannot be in the future")
    return business_at
