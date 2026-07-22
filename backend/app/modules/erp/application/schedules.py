"""Tenant-local ERP maintenance jobs invoked by the Platform schedule worker."""

import uuid

from sqlmodel import Session, select

from app.core.clock import get_datetime_utc
from app.modules.erp.application.reconciliation import run_reconciliation
from app.modules.erp.infrastructure.models import CommandReceipt, CommandReceiptStatus
from app.modules.erp.infrastructure.tenant_uow import ErpTenantUnitOfWork


def run_daily_reconciliation(session: Session, tenant_id: uuid.UUID) -> None:
    with ErpTenantUnitOfWork(session=session, tenant_id=tenant_id) as uow:
        run_reconciliation(uow=uow, triggered_by=None)
        session.commit()


def cleanup_completed_command_receipts(session: Session, tenant_id: uuid.UUID) -> None:
    with ErpTenantUnitOfWork(session=session, tenant_id=tenant_id) as uow:
        expired = uow.session.exec(
            select(CommandReceipt).where(
                CommandReceipt.status == CommandReceiptStatus.COMPLETED,
                CommandReceipt.expires_at < get_datetime_utc(),
            )
        ).all()
        for receipt in expired:
            uow.session.delete(receipt)
        session.commit()
