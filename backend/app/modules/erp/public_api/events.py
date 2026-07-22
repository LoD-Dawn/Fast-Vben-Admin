import uuid
from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel, ConfigDict


class StockChangedV1(BaseModel):
    """Versioned stock notification emitted with an inventory transaction."""

    model_config = ConfigDict(frozen=True)

    tenant_id: uuid.UUID
    product_id: uuid.UUID
    warehouse_id: uuid.UUID
    delta_quantity: Decimal
    balance_quantity: Decimal
    source_document_type: str
    source_document_id: uuid.UUID


class DocumentLifecycleV1(BaseModel):
    """Versioned document approval or reversal notification."""

    model_config = ConfigDict(frozen=True)

    tenant_id: uuid.UUID
    document_id: uuid.UUID
    document_no: str
    action: str
    version: int
    occurred_at: datetime
    amount: Decimal | None = None


class ReconciliationFailedV1(BaseModel):
    """Versioned alert emitted when a tenant reconciliation finds differences."""

    model_config = ConfigDict(frozen=True)

    tenant_id: uuid.UUID
    reconciliation_run_id: uuid.UUID
    stock_difference_count: int
    settlement_difference_count: int
    occurred_at: datetime
