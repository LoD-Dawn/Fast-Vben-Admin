"""Settlement-account reference checks shared by ERP document routes."""

import uuid

from sqlmodel import select

from app.modules.erp.infrastructure.models import SettlementAccount
from app.modules.erp.infrastructure.tenant_uow import ErpTenantUnitOfWork


class SettlementAccountUnavailableError(ValueError):
    pass


def ensure_active_settlement_account(
    *, uow: ErpTenantUnitOfWork, account_id: uuid.UUID | None
) -> uuid.UUID | None:
    if account_id is None:
        return None
    account = uow.session.exec(
        select(SettlementAccount).where(SettlementAccount.id == account_id)
    ).first()
    if account is None or not account.is_active:
        raise SettlementAccountUnavailableError("Settlement account is unavailable")
    return account.id
