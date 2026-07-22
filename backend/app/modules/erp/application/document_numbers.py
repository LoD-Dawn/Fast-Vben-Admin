"""Database-backed ERP document number allocation."""


from sqlalchemy.dialects.postgresql import insert

from app.core.clock import get_datetime_utc
from app.modules.erp.infrastructure.models import DocumentSequence
from app.modules.erp.infrastructure.tenant_uow import ErpTenantUnitOfWork


def allocate_document_no(*, uow: ErpTenantUnitOfWork, prefix: str) -> str:
    """Allocate a tenant-scoped daily sequence in the current transaction."""

    sequence_date = get_datetime_utc().date()
    next_value = uow.session.exec(
        insert(DocumentSequence)
        .values(
            tenant_id=uow.tenant_id,
            prefix=prefix,
            sequence_date=sequence_date,
            next_value=2,
        )
        .on_conflict_do_update(
            index_elements=("tenant_id", "prefix", "sequence_date"),
            set_={"next_value": DocumentSequence.next_value + 1},
        )
        .returning(DocumentSequence.next_value)
    ).scalar_one()
    allocated = int(next_value) - 1
    return f"{prefix}{sequence_date:%Y%m%d}{allocated:06d}"
