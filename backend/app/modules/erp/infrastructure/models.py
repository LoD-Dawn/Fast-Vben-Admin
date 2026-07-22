"""ERP master-data tables owned exclusively by the ERP module."""

import uuid
from datetime import date, datetime
from decimal import Decimal
from enum import StrEnum

from sqlalchemy import (
    CheckConstraint,
    DateTime,
    ForeignKeyConstraint,
    Index,
    Numeric,
    String,
    UniqueConstraint,
    text,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlmodel import Field, SQLModel

from app.core.clock import get_datetime_utc


class DocumentStatus(StrEnum):
    DRAFT = "draft"
    APPROVED = "approved"


class DocumentAction(StrEnum):
    CREATED = "created"
    UPDATED = "updated"
    DELETED = "deleted"
    APPROVED = "approved"
    REVERSED = "reversed"
    EXPORTED = "exported"
    SENSITIVE_VIEWED = "sensitive_viewed"


class ReconciliationRunStatus(StrEnum):
    RUNNING = "running"
    PASSED = "passed"
    FAILED = "failed"


class CommandReceiptStatus(StrEnum):
    PROCESSING = "processing"
    COMPLETED = "completed"


class ErpSetting(SQLModel, table=True):
    __tablename__ = "erp_setting"
    __table_args__ = (
        CheckConstraint("version > 0", name="ck_erp_setting_version"),
        CheckConstraint(
            "integrity_status IN ('healthy', 'degraded')",
            name="ck_erp_setting_integrity_status",
        ),
        {"schema": "erp"},
    )

    tenant_id: uuid.UUID = Field(primary_key=True)
    timezone: str = Field(default="UTC", max_length=64)
    integrity_status: str = Field(default="healthy", max_length=16)
    last_reconciled_at: datetime | None = Field(
        default=None, sa_type=DateTime(timezone=True)
    )  # type: ignore
    version: int = 1
    created_at: datetime = Field(
        default_factory=get_datetime_utc, sa_type=DateTime(timezone=True)
    )  # type: ignore
    updated_at: datetime = Field(
        default_factory=get_datetime_utc, sa_type=DateTime(timezone=True)
    )  # type: ignore


class ReconciliationRun(SQLModel, table=True):
    __tablename__ = "reconciliation_run"
    __table_args__ = (
        CheckConstraint(
            "status IN ('running', 'passed', 'failed')",
            name="ck_erp_reconciliation_run_status",
        ),
        CheckConstraint(
            "stock_difference_count >= 0",
            name="ck_erp_reconciliation_run_stock_difference_count",
        ),
        CheckConstraint(
            "settlement_difference_count >= 0",
            name="ck_erp_reconciliation_run_settlement_difference_count",
        ),
        {"schema": "erp"},
    )

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    tenant_id: uuid.UUID = Field(index=True, nullable=False)
    status: ReconciliationRunStatus = Field(
        default=ReconciliationRunStatus.RUNNING, sa_type=String(16)
    )
    stock_difference_count: int = 0
    settlement_difference_count: int = 0
    summary_json: dict[str, object] = Field(default_factory=dict, sa_type=JSONB)
    started_at: datetime = Field(
        default_factory=get_datetime_utc, sa_type=DateTime(timezone=True), index=True
    )  # type: ignore
    completed_at: datetime | None = Field(
        default=None, sa_type=DateTime(timezone=True)
    )  # type: ignore
    triggered_by: uuid.UUID | None = Field(default=None, index=True)


class StockLedgerType(StrEnum):
    PURCHASE_IN = "purchase_in"
    PURCHASE_IN_REVERSAL = "purchase_in_reversal"
    PURCHASE_RETURN = "purchase_return"
    PURCHASE_RETURN_REVERSAL = "purchase_return_reversal"
    SALE_OUT = "sale_out"
    SALE_OUT_REVERSAL = "sale_out_reversal"
    SALE_RETURN = "sale_return"
    SALE_RETURN_REVERSAL = "sale_return_reversal"
    OTHER_IN = "other_in"
    OTHER_IN_REVERSAL = "other_in_reversal"
    OTHER_OUT = "other_out"
    OTHER_OUT_REVERSAL = "other_out_reversal"
    MOVE_IN = "move_in"
    MOVE_IN_REVERSAL = "move_in_reversal"
    MOVE_OUT = "move_out"
    MOVE_OUT_REVERSAL = "move_out_reversal"
    CHECK_GAIN = "check_gain"
    CHECK_GAIN_REVERSAL = "check_gain_reversal"
    CHECK_LOSS = "check_loss"
    CHECK_LOSS_REVERSAL = "check_loss_reversal"


class SettlementSourceType(StrEnum):
    PURCHASE_IN = "purchase_in"
    PURCHASE_RETURN = "purchase_return"
    SALE_OUT = "sale_out"
    SALE_RETURN = "sale_return"


class ProductUnit(SQLModel, table=True):
    __tablename__ = "product_unit"
    __table_args__ = (
        UniqueConstraint("tenant_id", "code", name="uq_erp_product_unit_tenant_code"),
        UniqueConstraint("tenant_id", "name", name="uq_erp_product_unit_tenant_name"),
        UniqueConstraint("id", "tenant_id", name="uq_erp_product_unit_id_tenant_id"),
        {"schema": "erp"},
    )

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    tenant_id: uuid.UUID = Field(index=True, nullable=False)
    code: str = Field(min_length=1, max_length=50)
    name: str = Field(min_length=1, max_length=100)
    symbol: str | None = Field(default=None, max_length=20)
    is_active: bool = True
    created_at: datetime | None = Field(
        default_factory=get_datetime_utc,
        sa_type=DateTime(timezone=True),  # type: ignore
    )
    updated_at: datetime | None = Field(
        default_factory=get_datetime_utc,
        sa_type=DateTime(timezone=True),  # type: ignore
    )


class ProductCategory(SQLModel, table=True):
    __tablename__ = "product_category"
    __table_args__ = (
        ForeignKeyConstraint(
            ["parent_id", "tenant_id"],
            ["erp.product_category.id", "erp.product_category.tenant_id"],
            ondelete="RESTRICT",
        ),
        UniqueConstraint("tenant_id", "code", name="uq_erp_product_category_tenant_code"),
        UniqueConstraint("id", "tenant_id", name="uq_erp_product_category_id_tenant_id"),
        {"schema": "erp"},
    )

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    tenant_id: uuid.UUID = Field(index=True, nullable=False)
    code: str = Field(min_length=1, max_length=50)
    name: str = Field(min_length=1, max_length=100)
    parent_id: uuid.UUID | None = Field(default=None, index=True)
    sort: int = 0
    is_active: bool = True
    created_at: datetime | None = Field(
        default_factory=get_datetime_utc,
        sa_type=DateTime(timezone=True),  # type: ignore
    )
    updated_at: datetime | None = Field(
        default_factory=get_datetime_utc,
        sa_type=DateTime(timezone=True),  # type: ignore
    )


class Product(SQLModel, table=True):
    __tablename__ = "product"
    __table_args__ = (
        ForeignKeyConstraint(
            ["category_id", "tenant_id"],
            ["erp.product_category.id", "erp.product_category.tenant_id"],
            ondelete="RESTRICT",
        ),
        ForeignKeyConstraint(
            ["unit_id", "tenant_id"],
            ["erp.product_unit.id", "erp.product_unit.tenant_id"],
            ondelete="RESTRICT",
        ),
        UniqueConstraint("tenant_id", "code", name="uq_erp_product_tenant_code"),
        Index(
            "uq_erp_product_tenant_barcode",
            "tenant_id",
            "barcode",
            unique=True,
            postgresql_where=text("barcode IS NOT NULL AND barcode <> ''"),
        ),
        UniqueConstraint("id", "tenant_id", name="uq_erp_product_id_tenant_id"),
        CheckConstraint("purchase_reference_price >= 0", name="ck_erp_product_purchase_reference_price"),
        CheckConstraint("sale_reference_price >= 0", name="ck_erp_product_sale_reference_price"),
        CheckConstraint("min_sale_price >= 0", name="ck_erp_product_min_sale_price"),
        {"schema": "erp"},
    )

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    tenant_id: uuid.UUID = Field(index=True, nullable=False)
    code: str = Field(min_length=1, max_length=100)
    name: str = Field(min_length=1, max_length=200)
    category_id: uuid.UUID = Field(index=True, nullable=False)
    unit_id: uuid.UUID = Field(index=True, nullable=False)
    barcode: str | None = Field(default=None, max_length=100)
    specification: str | None = Field(default=None, max_length=500)
    weight: Decimal = Field(default=Decimal("0"), sa_type=Numeric(20, 6))
    expiry_days: int = Field(default=0)
    remark: str | None = Field(default=None, max_length=500)
    purchase_reference_price: Decimal = Field(default=Decimal("0"), sa_type=Numeric(20, 4))
    sale_reference_price: Decimal = Field(default=Decimal("0"), sa_type=Numeric(20, 4))
    min_sale_price: Decimal = Field(default=Decimal("0"), sa_type=Numeric(20, 4))
    is_active: bool = True
    created_at: datetime | None = Field(
        default_factory=get_datetime_utc,
        sa_type=DateTime(timezone=True),  # type: ignore
    )
    updated_at: datetime | None = Field(
        default_factory=get_datetime_utc,
        sa_type=DateTime(timezone=True),  # type: ignore
    )


class Warehouse(SQLModel, table=True):
    __tablename__ = "warehouse"
    __table_args__ = (
        UniqueConstraint("tenant_id", "code", name="uq_erp_warehouse_tenant_code"),
        UniqueConstraint("tenant_id", "name", name="uq_erp_warehouse_tenant_name"),
        UniqueConstraint("id", "tenant_id", name="uq_erp_warehouse_id_tenant_id"),
        Index(
            "uq_erp_warehouse_tenant_default",
            "tenant_id",
            unique=True,
            postgresql_where=text("is_default"),
        ),
        {"schema": "erp"},
    )

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    tenant_id: uuid.UUID = Field(index=True, nullable=False)
    code: str = Field(min_length=1, max_length=50)
    name: str = Field(min_length=1, max_length=100)
    contact_name: str | None = Field(default=None, max_length=100)
    contact_phone: str | None = Field(default=None, max_length=50)
    address: str | None = Field(default=None, max_length=500)
    storage_fee_reference: Decimal = Field(default=Decimal("0"), sa_type=Numeric(20, 4))
    transport_fee_reference: Decimal = Field(default=Decimal("0"), sa_type=Numeric(20, 4))
    sort: int = 0
    is_active: bool = True
    is_default: bool = False
    remark: str | None = Field(default=None, max_length=500)
    created_at: datetime | None = Field(
        default_factory=get_datetime_utc,
        sa_type=DateTime(timezone=True),  # type: ignore
    )
    updated_at: datetime | None = Field(
        default_factory=get_datetime_utc,
        sa_type=DateTime(timezone=True),  # type: ignore
    )


class WarehouseUserGrant(SQLModel, table=True):
    __tablename__ = "warehouse_user_grant"
    __table_args__ = (
        ForeignKeyConstraint(
            ["warehouse_id", "tenant_id"],
            ["erp.warehouse.id", "erp.warehouse.tenant_id"],
            ondelete="CASCADE",
        ),
        UniqueConstraint(
            "tenant_id", "warehouse_id", "user_id", name="uq_erp_warehouse_user_grant"
        ),
        {"schema": "erp"},
    )

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    tenant_id: uuid.UUID = Field(index=True, nullable=False)
    warehouse_id: uuid.UUID = Field(index=True, nullable=False)
    user_id: uuid.UUID = Field(index=True, nullable=False)
    granted_by: uuid.UUID = Field(nullable=False)
    granted_at: datetime = Field(default_factory=get_datetime_utc, sa_type=DateTime(timezone=True))  # type: ignore


class Supplier(SQLModel, table=True):
    __tablename__ = "supplier"
    __table_args__ = (
        CheckConstraint("tax_rate >= 0 AND tax_rate <= 100", name="ck_erp_supplier_tax_rate"),
        Index("ix_erp_supplier_name", "name"),
        Index("ix_erp_supplier_contact_name", "contact_name"),
        UniqueConstraint("tenant_id", "name", name="uq_erp_supplier_tenant_name"),
        UniqueConstraint("id", "tenant_id", name="uq_erp_supplier_id_tenant_id"),
        {"schema": "erp"},
    )

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    tenant_id: uuid.UUID = Field(index=True, nullable=False)
    name: str = Field(min_length=1, max_length=200)
    contact_name: str | None = Field(default=None, max_length=100)
    mobile: str | None = Field(default=None, max_length=50)
    phone: str | None = Field(default=None, max_length=50)
    email: str | None = Field(default=None, max_length=320)
    fax: str | None = Field(default=None, max_length=50)
    tax_no: str | None = Field(default=None, max_length=100)
    tax_rate: Decimal = Field(default=Decimal("0"), sa_type=Numeric(7, 4))
    bank_name: str | None = Field(default=None, max_length=200)
    bank_account_encrypted: str | None = Field(default=None, max_length=1000)
    bank_account_last4: str | None = Field(default=None, max_length=4)
    address: str | None = Field(default=None, max_length=500)
    sort: int = 0
    is_active: bool = True
    remark: str | None = Field(default=None, max_length=500)
    created_at: datetime | None = Field(
        default_factory=get_datetime_utc,
        sa_type=DateTime(timezone=True),  # type: ignore
    )
    updated_at: datetime | None = Field(
        default_factory=get_datetime_utc,
        sa_type=DateTime(timezone=True),  # type: ignore
    )


class Customer(SQLModel, table=True):
    __tablename__ = "customer"
    __table_args__ = (
        CheckConstraint("tax_rate >= 0 AND tax_rate <= 100", name="ck_erp_customer_tax_rate"),
        Index("ix_erp_customer_name", "name"),
        Index("ix_erp_customer_contact_name", "contact_name"),
        UniqueConstraint("tenant_id", "name", name="uq_erp_customer_tenant_name"),
        UniqueConstraint("id", "tenant_id", name="uq_erp_customer_id_tenant_id"),
        {"schema": "erp"},
    )

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    tenant_id: uuid.UUID = Field(index=True, nullable=False)
    name: str = Field(min_length=1, max_length=200)
    contact_name: str | None = Field(default=None, max_length=100)
    mobile: str | None = Field(default=None, max_length=50)
    phone: str | None = Field(default=None, max_length=50)
    email: str | None = Field(default=None, max_length=320)
    fax: str | None = Field(default=None, max_length=50)
    tax_no: str | None = Field(default=None, max_length=100)
    tax_rate: Decimal = Field(default=Decimal("0"), sa_type=Numeric(7, 4))
    bank_name: str | None = Field(default=None, max_length=200)
    bank_account_encrypted: str | None = Field(default=None, max_length=1000)
    bank_account_last4: str | None = Field(default=None, max_length=4)
    address: str | None = Field(default=None, max_length=500)
    sort: int = 0
    is_active: bool = True
    remark: str | None = Field(default=None, max_length=500)
    created_at: datetime | None = Field(
        default_factory=get_datetime_utc,
        sa_type=DateTime(timezone=True),  # type: ignore
    )
    updated_at: datetime | None = Field(
        default_factory=get_datetime_utc,
        sa_type=DateTime(timezone=True),  # type: ignore
    )


class SettlementAccount(SQLModel, table=True):
    __tablename__ = "settlement_account"
    __table_args__ = (
        UniqueConstraint("tenant_id", "name", name="uq_erp_settlement_account_tenant_name"),
        UniqueConstraint(
            "tenant_id",
            "account_no_fingerprint",
            name="uq_erp_settlement_account_tenant_fingerprint",
        ),
        UniqueConstraint("id", "tenant_id", name="uq_erp_settlement_account_id_tenant_id"),
        Index(
            "uq_erp_settlement_account_default_per_tenant",
            "tenant_id",
            unique=True,
            postgresql_where=text("is_default IS TRUE"),
        ),
        {"schema": "erp"},
    )

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    tenant_id: uuid.UUID = Field(index=True, nullable=False)
    name: str = Field(min_length=1, max_length=200)
    account_no_encrypted: str = Field(max_length=1000)
    account_no_fingerprint: str = Field(max_length=80)
    account_no_last4: str = Field(max_length=4)
    sort: int = 0
    is_active: bool = True
    is_default: bool = False
    remark: str | None = Field(default=None, max_length=500)
    created_at: datetime | None = Field(
        default_factory=get_datetime_utc,
        sa_type=DateTime(timezone=True),  # type: ignore
    )
    updated_at: datetime | None = Field(
        default_factory=get_datetime_utc,
        sa_type=DateTime(timezone=True),  # type: ignore
    )


class DocumentActionLog(SQLModel, table=True):
    __tablename__ = "document_action_log"
    __table_args__ = (
        CheckConstraint("old_version IS NULL OR old_version > 0", name="ck_erp_action_log_old_version"),
        CheckConstraint("new_version IS NULL OR new_version > 0", name="ck_erp_action_log_new_version"),
        {"schema": "erp"},
    )

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    tenant_id: uuid.UUID = Field(index=True, nullable=False)
    resource_type: str = Field(max_length=64, index=True)
    resource_id: uuid.UUID = Field(index=True, nullable=False)
    resource_no: str | None = Field(default=None, max_length=32)
    action: DocumentAction = Field(sa_type=String(32), index=True)
    old_status: str | None = Field(default=None, max_length=32)
    new_status: str | None = Field(default=None, max_length=32)
    old_version: int | None = Field(default=None)
    new_version: int | None = Field(default=None)
    actor_id: uuid.UUID = Field(nullable=False, index=True)
    reason: str | None = Field(default=None, max_length=500)
    metadata_json: dict[str, object] = Field(default_factory=dict, sa_type=JSONB)
    occurred_at: datetime = Field(default_factory=get_datetime_utc, sa_type=DateTime(timezone=True), index=True)  # type: ignore


class CommandReceipt(SQLModel, table=True):
    """A short-lived record that makes an ERP write command safe to retry."""

    __tablename__ = "command_receipt"
    __table_args__ = (
        CheckConstraint(
            "status IN ('processing', 'completed')",
            name="ck_erp_command_receipt_status",
        ),
        UniqueConstraint(
            "tenant_id",
            "command_name",
            "idempotency_key_sha256",
            name="uq_erp_command_receipt_command_key",
        ),
        {"schema": "erp"},
    )

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    tenant_id: uuid.UUID = Field(index=True, nullable=False)
    command_name: str = Field(max_length=120, index=True)
    # The raw key is never persisted. Its SHA-256 digest is sufficient for the
    # tenant-scoped uniqueness check and cannot be replayed from database reads.
    idempotency_key_sha256: str = Field(max_length=64)
    request_sha256: str = Field(max_length=64)
    resource_type: str | None = Field(default=None, max_length=64)
    resource_id: uuid.UUID | None = Field(default=None, index=True)
    resource_version: int | None = Field(default=None)
    status: CommandReceiptStatus = Field(
        default=CommandReceiptStatus.PROCESSING, sa_type=String(32)
    )
    expires_at: datetime = Field(sa_type=DateTime(timezone=True), index=True)  # type: ignore
    created_at: datetime = Field(default_factory=get_datetime_utc, sa_type=DateTime(timezone=True))  # type: ignore
    completed_at: datetime | None = Field(default=None, sa_type=DateTime(timezone=True))  # type: ignore


class DocumentAttachment(SQLModel, table=True):
    """Logical file attachment for an ERP document aggregate."""

    __tablename__ = "document_attachment"
    __table_args__ = (
        CheckConstraint("sort >= 0", name="ck_erp_document_attachment_sort"),
        UniqueConstraint(
            "tenant_id",
            "document_type",
            "document_id",
            "file_id",
            name="uq_erp_document_attachment_file",
        ),
        {"schema": "erp"},
    )

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    tenant_id: uuid.UUID = Field(index=True, nullable=False)
    document_type: str = Field(max_length=64, index=True)
    document_id: uuid.UUID = Field(index=True, nullable=False)
    file_id: uuid.UUID = Field(index=True, nullable=False)
    sort: int = 0
    created_by: uuid.UUID = Field(nullable=False)
    created_at: datetime = Field(default_factory=get_datetime_utc, sa_type=DateTime(timezone=True))  # type: ignore


class FinancePayment(SQLModel, table=True):
    __tablename__ = "finance_payment"
    __table_args__ = (
        ForeignKeyConstraint(["supplier_id", "tenant_id"], ["erp.supplier.id", "erp.supplier.tenant_id"], ondelete="RESTRICT"),
        ForeignKeyConstraint(["settlement_account_id", "tenant_id"], ["erp.settlement_account.id", "erp.settlement_account.tenant_id"], ondelete="RESTRICT"),
        CheckConstraint("version > 0", name="ck_erp_finance_payment_version"),
        CheckConstraint("total_settlement_amount >= 0", name="ck_erp_finance_payment_settlement_amount"),
        CheckConstraint("discount_amount >= 0", name="ck_erp_finance_payment_discount_amount"),
        CheckConstraint("payment_amount >= 0", name="ck_erp_finance_payment_payment_amount"),
        UniqueConstraint("tenant_id", "no", name="uq_erp_finance_payment_tenant_no"),
        UniqueConstraint("id", "tenant_id", name="uq_erp_finance_payment_id_tenant_id"),
        {"schema": "erp"},
    )

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    tenant_id: uuid.UUID = Field(index=True, nullable=False)
    no: str = Field(max_length=32)
    supplier_id: uuid.UUID = Field(index=True, nullable=False)
    supplier_name: str = Field(max_length=200)
    settlement_account_id: uuid.UUID = Field(index=True, nullable=False)
    status: DocumentStatus = Field(default=DocumentStatus.DRAFT, sa_type=String(32))
    version: int = 1
    business_at: datetime = Field(default_factory=get_datetime_utc, sa_type=DateTime(timezone=True), index=True)  # type: ignore
    owner_id: uuid.UUID = Field(index=True, nullable=False)
    total_settlement_amount: Decimal = Field(sa_type=Numeric(20, 4))
    discount_amount: Decimal = Field(default=Decimal("0"), sa_type=Numeric(20, 4))
    payment_amount: Decimal = Field(sa_type=Numeric(20, 4))
    remark: str | None = Field(default=None, max_length=500)
    created_by: uuid.UUID = Field(nullable=False)
    updated_by: uuid.UUID = Field(nullable=False)
    approved_by: uuid.UUID | None = Field(default=None)
    approved_at: datetime | None = Field(default=None, sa_type=DateTime(timezone=True))  # type: ignore
    reversed_by: uuid.UUID | None = Field(default=None)
    reversed_at: datetime | None = Field(default=None, sa_type=DateTime(timezone=True))  # type: ignore
    created_at: datetime | None = Field(default_factory=get_datetime_utc, sa_type=DateTime(timezone=True))  # type: ignore
    updated_at: datetime | None = Field(default_factory=get_datetime_utc, sa_type=DateTime(timezone=True))  # type: ignore


class FinancePaymentItem(SQLModel, table=True):
    __tablename__ = "finance_payment_item"
    __table_args__ = (
        ForeignKeyConstraint(["finance_payment_id", "tenant_id"], ["erp.finance_payment.id", "erp.finance_payment.tenant_id"], ondelete="CASCADE"),
        CheckConstraint("source_type IN ('purchase_in', 'purchase_return')", name="ck_erp_finance_payment_item_source_type"),
        Index("ix_erp_finance_payment_item_source_type", "source_type"),
        CheckConstraint("discount_allocated >= 0", name="ck_erp_finance_payment_item_discount"),
        CheckConstraint("settlement_signed <> 0", name="ck_erp_finance_payment_item_settlement"),
        UniqueConstraint("finance_payment_id", "source_type", "source_document_id", name="uq_erp_finance_payment_item_source"),
        {"schema": "erp"},
    )

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    tenant_id: uuid.UUID = Field(index=True, nullable=False)
    finance_payment_id: uuid.UUID = Field(index=True, nullable=False)
    source_type: SettlementSourceType = Field(sa_type=String(32))
    source_document_id: uuid.UUID = Field(index=True, nullable=False)
    source_document_no: str = Field(max_length=32)
    source_total_signed: Decimal = Field(sa_type=Numeric(20, 4))
    settled_before_signed: Decimal = Field(sa_type=Numeric(20, 4))
    settlement_signed: Decimal = Field(sa_type=Numeric(20, 4))
    discount_allocated: Decimal = Field(default=Decimal("0"), sa_type=Numeric(20, 4))
    remark: str | None = Field(default=None, max_length=500)


class FinanceReceipt(SQLModel, table=True):
    __tablename__ = "finance_receipt"
    __table_args__ = (
        ForeignKeyConstraint(["customer_id", "tenant_id"], ["erp.customer.id", "erp.customer.tenant_id"], ondelete="RESTRICT"),
        ForeignKeyConstraint(["settlement_account_id", "tenant_id"], ["erp.settlement_account.id", "erp.settlement_account.tenant_id"], ondelete="RESTRICT"),
        CheckConstraint("version > 0", name="ck_erp_finance_receipt_version"),
        CheckConstraint("total_settlement_amount >= 0", name="ck_erp_finance_receipt_settlement_amount"),
        CheckConstraint("discount_amount >= 0", name="ck_erp_finance_receipt_discount_amount"),
        CheckConstraint("receipt_amount >= 0", name="ck_erp_finance_receipt_receipt_amount"),
        UniqueConstraint("tenant_id", "no", name="uq_erp_finance_receipt_tenant_no"),
        UniqueConstraint("id", "tenant_id", name="uq_erp_finance_receipt_id_tenant_id"),
        {"schema": "erp"},
    )

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    tenant_id: uuid.UUID = Field(index=True, nullable=False)
    no: str = Field(max_length=32)
    customer_id: uuid.UUID = Field(index=True, nullable=False)
    customer_name: str = Field(max_length=200)
    settlement_account_id: uuid.UUID = Field(index=True, nullable=False)
    status: DocumentStatus = Field(default=DocumentStatus.DRAFT, sa_type=String(32))
    version: int = 1
    business_at: datetime = Field(default_factory=get_datetime_utc, sa_type=DateTime(timezone=True), index=True)  # type: ignore
    owner_id: uuid.UUID = Field(index=True, nullable=False)
    total_settlement_amount: Decimal = Field(sa_type=Numeric(20, 4))
    discount_amount: Decimal = Field(default=Decimal("0"), sa_type=Numeric(20, 4))
    receipt_amount: Decimal = Field(sa_type=Numeric(20, 4))
    remark: str | None = Field(default=None, max_length=500)
    created_by: uuid.UUID = Field(nullable=False)
    updated_by: uuid.UUID = Field(nullable=False)
    approved_by: uuid.UUID | None = Field(default=None)
    approved_at: datetime | None = Field(default=None, sa_type=DateTime(timezone=True))  # type: ignore
    reversed_by: uuid.UUID | None = Field(default=None)
    reversed_at: datetime | None = Field(default=None, sa_type=DateTime(timezone=True))  # type: ignore
    created_at: datetime | None = Field(default_factory=get_datetime_utc, sa_type=DateTime(timezone=True))  # type: ignore
    updated_at: datetime | None = Field(default_factory=get_datetime_utc, sa_type=DateTime(timezone=True))  # type: ignore


class FinanceReceiptItem(SQLModel, table=True):
    __tablename__ = "finance_receipt_item"
    __table_args__ = (
        ForeignKeyConstraint(["finance_receipt_id", "tenant_id"], ["erp.finance_receipt.id", "erp.finance_receipt.tenant_id"], ondelete="CASCADE"),
        CheckConstraint("source_type IN ('sale_out', 'sale_return')", name="ck_erp_finance_receipt_item_source_type"),
        Index("ix_erp_finance_receipt_item_source_type", "source_type"),
        CheckConstraint("discount_allocated >= 0", name="ck_erp_finance_receipt_item_discount"),
        CheckConstraint("settlement_signed <> 0", name="ck_erp_finance_receipt_item_settlement"),
        UniqueConstraint("finance_receipt_id", "source_type", "source_document_id", name="uq_erp_finance_receipt_item_source"),
        {"schema": "erp"},
    )

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    tenant_id: uuid.UUID = Field(index=True, nullable=False)
    finance_receipt_id: uuid.UUID = Field(index=True, nullable=False)
    source_type: SettlementSourceType = Field(sa_type=String(32))
    source_document_id: uuid.UUID = Field(index=True, nullable=False)
    source_document_no: str = Field(max_length=32)
    source_total_signed: Decimal = Field(sa_type=Numeric(20, 4))
    settled_before_signed: Decimal = Field(sa_type=Numeric(20, 4))
    settlement_signed: Decimal = Field(sa_type=Numeric(20, 4))
    discount_allocated: Decimal = Field(default=Decimal("0"), sa_type=Numeric(20, 4))
    remark: str | None = Field(default=None, max_length=500)


class DocumentSequence(SQLModel, table=True):
    __tablename__ = "document_sequence"
    __table_args__ = (
        CheckConstraint("next_value > 0", name="ck_erp_document_sequence_next_value"),
        {"schema": "erp"},
    )

    tenant_id: uuid.UUID = Field(primary_key=True)
    prefix: str = Field(primary_key=True, max_length=12)
    sequence_date: date = Field(primary_key=True)
    next_value: int = 1


class PurchaseOrder(SQLModel, table=True):
    __tablename__ = "purchase_order"
    __table_args__ = (
        ForeignKeyConstraint(
            ["supplier_id", "tenant_id"],
            ["erp.supplier.id", "erp.supplier.tenant_id"],
            ondelete="RESTRICT",
        ),
        ForeignKeyConstraint(["settlement_account_id", "tenant_id"], ["erp.settlement_account.id", "erp.settlement_account.tenant_id"], ondelete="RESTRICT"),
        CheckConstraint("version > 0", name="ck_erp_purchase_order_version"),
        CheckConstraint("total_quantity > 0", name="ck_erp_purchase_order_quantity"),
        CheckConstraint("product_amount >= 0", name="ck_erp_purchase_order_product_amount"),
        CheckConstraint("tax_amount >= 0", name="ck_erp_purchase_order_tax_amount"),
        CheckConstraint("discount_rate >= 0 AND discount_rate <= 100", name="ck_erp_purchase_order_discount_rate"),
        CheckConstraint("discount_amount >= 0", name="ck_erp_purchase_order_discount_amount"),
        CheckConstraint("deposit_amount >= 0", name="ck_erp_purchase_order_deposit_amount"),
        CheckConstraint("total_amount >= 0", name="ck_erp_purchase_order_total_amount"),
        UniqueConstraint("tenant_id", "no", name="uq_erp_purchase_order_tenant_no"),
        UniqueConstraint("id", "tenant_id", name="uq_erp_purchase_order_id_tenant_id"),
        {"schema": "erp"},
    )

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    tenant_id: uuid.UUID = Field(index=True, nullable=False)
    no: str = Field(max_length=32)
    supplier_id: uuid.UUID = Field(index=True, nullable=False)
    supplier_name: str = Field(max_length=200)
    settlement_account_id: uuid.UUID | None = Field(default=None, index=True)
    status: DocumentStatus = Field(default=DocumentStatus.DRAFT, sa_type=String(32))
    version: int = 1
    business_at: datetime = Field(default_factory=get_datetime_utc, sa_type=DateTime(timezone=True), index=True)  # type: ignore
    owner_id: uuid.UUID = Field(index=True, nullable=False)
    total_quantity: Decimal = Field(sa_type=Numeric(20, 6))
    product_amount: Decimal = Field(sa_type=Numeric(20, 4))
    tax_amount: Decimal = Field(sa_type=Numeric(20, 4))
    discount_rate: Decimal = Field(default=Decimal("0"), sa_type=Numeric(7, 4))
    discount_amount: Decimal = Field(default=Decimal("0"), sa_type=Numeric(20, 4))
    deposit_amount: Decimal = Field(default=Decimal("0"), sa_type=Numeric(20, 4))
    total_amount: Decimal = Field(sa_type=Numeric(20, 4))
    remark: str | None = Field(default=None, max_length=500)
    created_by: uuid.UUID = Field(nullable=False)
    updated_by: uuid.UUID = Field(nullable=False)
    approved_by: uuid.UUID | None = Field(default=None)
    approved_at: datetime | None = Field(default=None, sa_type=DateTime(timezone=True))  # type: ignore
    reversed_by: uuid.UUID | None = Field(default=None)
    reversed_at: datetime | None = Field(default=None, sa_type=DateTime(timezone=True))  # type: ignore
    created_at: datetime | None = Field(default_factory=get_datetime_utc, sa_type=DateTime(timezone=True))  # type: ignore
    updated_at: datetime | None = Field(default_factory=get_datetime_utc, sa_type=DateTime(timezone=True))  # type: ignore


class PurchaseOrderItem(SQLModel, table=True):
    __tablename__ = "purchase_order_item"
    __table_args__ = (
        ForeignKeyConstraint(
            ["purchase_order_id", "tenant_id"],
            ["erp.purchase_order.id", "erp.purchase_order.tenant_id"],
            ondelete="CASCADE",
        ),
        ForeignKeyConstraint(
            ["product_id", "tenant_id"],
            ["erp.product.id", "erp.product.tenant_id"],
            ondelete="RESTRICT",
        ),
        ForeignKeyConstraint(
            ["unit_id", "tenant_id"],
            ["erp.product_unit.id", "erp.product_unit.tenant_id"],
            ondelete="RESTRICT",
        ),
        CheckConstraint("quantity > 0", name="ck_erp_purchase_order_item_quantity"),
        CheckConstraint("unit_price >= 0", name="ck_erp_purchase_order_item_unit_price"),
        CheckConstraint("tax_rate >= 0 AND tax_rate <= 100", name="ck_erp_purchase_order_item_tax_rate"),
        CheckConstraint("received_quantity >= 0 AND received_quantity <= quantity", name="ck_erp_purchase_order_item_received_quantity"),
        CheckConstraint("returned_quantity >= 0 AND returned_quantity <= received_quantity", name="ck_erp_purchase_order_item_returned_quantity"),
        UniqueConstraint("purchase_order_id", "line_no", name="uq_erp_purchase_order_item_line"),
        {"schema": "erp"},
    )

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    tenant_id: uuid.UUID = Field(index=True, nullable=False)
    purchase_order_id: uuid.UUID = Field(index=True, nullable=False)
    line_no: int
    product_id: uuid.UUID = Field(index=True, nullable=False)
    unit_id: uuid.UUID = Field(index=True, nullable=False)
    product_name: str = Field(max_length=200)
    product_barcode: str | None = Field(default=None, max_length=100)
    unit_name: str = Field(max_length=100)
    quantity: Decimal = Field(sa_type=Numeric(20, 6))
    unit_price: Decimal = Field(sa_type=Numeric(20, 4))
    product_amount: Decimal = Field(sa_type=Numeric(20, 4))
    tax_rate: Decimal = Field(sa_type=Numeric(7, 4))
    tax_amount: Decimal = Field(sa_type=Numeric(20, 4))
    total_amount: Decimal = Field(sa_type=Numeric(20, 4))
    received_quantity: Decimal = Field(default=Decimal("0"), sa_type=Numeric(20, 6))
    returned_quantity: Decimal = Field(default=Decimal("0"), sa_type=Numeric(20, 6))
    remark: str | None = Field(default=None, max_length=500)


class PurchaseIn(SQLModel, table=True):
    __tablename__ = "purchase_in"
    __table_args__ = (
        ForeignKeyConstraint(
            ["purchase_order_id", "tenant_id"],
            ["erp.purchase_order.id", "erp.purchase_order.tenant_id"],
            ondelete="RESTRICT",
        ),
        ForeignKeyConstraint(
            ["supplier_id", "tenant_id"],
            ["erp.supplier.id", "erp.supplier.tenant_id"],
            ondelete="RESTRICT",
        ),
        ForeignKeyConstraint(["settlement_account_id", "tenant_id"], ["erp.settlement_account.id", "erp.settlement_account.tenant_id"], ondelete="RESTRICT"),
        CheckConstraint("version > 0", name="ck_erp_purchase_in_version"),
        CheckConstraint("total_quantity > 0", name="ck_erp_purchase_in_quantity"),
        CheckConstraint("total_amount >= 0", name="ck_erp_purchase_in_total_amount"),
        CheckConstraint("product_amount >= 0", name="ck_erp_purchase_in_product_amount"),
        CheckConstraint("tax_amount >= 0", name="ck_erp_purchase_in_tax_amount"),
        CheckConstraint("discount_rate >= 0 AND discount_rate <= 100", name="ck_erp_purchase_in_discount_rate"),
        CheckConstraint("discount_amount >= 0", name="ck_erp_purchase_in_discount_amount"),
        CheckConstraint("other_fee >= 0", name="ck_erp_purchase_in_other_fee"),
        CheckConstraint("settled_amount >= 0", name="ck_erp_purchase_in_settled_amount"),
        UniqueConstraint("tenant_id", "no", name="uq_erp_purchase_in_tenant_no"),
        UniqueConstraint("id", "tenant_id", name="uq_erp_purchase_in_id_tenant_id"),
        {"schema": "erp"},
    )

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    tenant_id: uuid.UUID = Field(index=True, nullable=False)
    no: str = Field(max_length=32)
    purchase_order_id: uuid.UUID = Field(index=True, nullable=False)
    purchase_order_no: str = Field(max_length=32)
    supplier_id: uuid.UUID = Field(index=True, nullable=False)
    supplier_name: str = Field(max_length=200)
    settlement_account_id: uuid.UUID | None = Field(default=None, index=True)
    status: DocumentStatus = Field(default=DocumentStatus.DRAFT, sa_type=String(32))
    version: int = 1
    business_at: datetime = Field(default_factory=get_datetime_utc, sa_type=DateTime(timezone=True), index=True)  # type: ignore
    owner_id: uuid.UUID = Field(index=True, nullable=False)
    total_quantity: Decimal = Field(sa_type=Numeric(20, 6))
    product_amount: Decimal = Field(default=Decimal("0"), sa_type=Numeric(20, 4))
    tax_amount: Decimal = Field(default=Decimal("0"), sa_type=Numeric(20, 4))
    discount_rate: Decimal = Field(default=Decimal("0"), sa_type=Numeric(7, 4))
    discount_amount: Decimal = Field(default=Decimal("0"), sa_type=Numeric(20, 4))
    other_fee: Decimal = Field(default=Decimal("0"), sa_type=Numeric(20, 4))
    total_amount: Decimal = Field(default=Decimal("0"), sa_type=Numeric(20, 4))
    settled_amount: Decimal = Field(default=Decimal("0"), sa_type=Numeric(20, 4))
    remark: str | None = Field(default=None, max_length=500)
    created_by: uuid.UUID = Field(nullable=False)
    updated_by: uuid.UUID = Field(nullable=False)
    approved_by: uuid.UUID | None = Field(default=None)
    approved_at: datetime | None = Field(default=None, sa_type=DateTime(timezone=True))  # type: ignore
    reversed_by: uuid.UUID | None = Field(default=None)
    reversed_at: datetime | None = Field(default=None, sa_type=DateTime(timezone=True))  # type: ignore
    created_at: datetime | None = Field(default_factory=get_datetime_utc, sa_type=DateTime(timezone=True))  # type: ignore
    updated_at: datetime | None = Field(default_factory=get_datetime_utc, sa_type=DateTime(timezone=True))  # type: ignore


class PurchaseInItem(SQLModel, table=True):
    __tablename__ = "purchase_in_item"
    __table_args__ = (
        ForeignKeyConstraint(["purchase_in_id", "tenant_id"], ["erp.purchase_in.id", "erp.purchase_in.tenant_id"], ondelete="CASCADE"),
        ForeignKeyConstraint(["purchase_order_item_id"], ["erp.purchase_order_item.id"], ondelete="RESTRICT"),
        ForeignKeyConstraint(["product_id", "tenant_id"], ["erp.product.id", "erp.product.tenant_id"], ondelete="RESTRICT"),
        ForeignKeyConstraint(["warehouse_id", "tenant_id"], ["erp.warehouse.id", "erp.warehouse.tenant_id"], ondelete="RESTRICT"),
        CheckConstraint("quantity > 0", name="ck_erp_purchase_in_item_quantity"),
        CheckConstraint("tax_rate >= 0 AND tax_rate <= 100", name="ck_erp_purchase_in_item_tax_rate"),
        CheckConstraint("returned_quantity >= 0 AND returned_quantity <= quantity", name="ck_erp_purchase_in_item_returned_quantity"),
        UniqueConstraint("purchase_in_id", "line_no", name="uq_erp_purchase_in_item_line"),
        UniqueConstraint("purchase_in_id", "purchase_order_item_id", name="uq_erp_purchase_in_item_order_line"),
        {"schema": "erp"},
    )

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    tenant_id: uuid.UUID = Field(index=True, nullable=False)
    purchase_in_id: uuid.UUID = Field(index=True, nullable=False)
    purchase_order_item_id: uuid.UUID = Field(index=True, nullable=False)
    line_no: int
    product_id: uuid.UUID = Field(index=True, nullable=False)
    warehouse_id: uuid.UUID = Field(index=True, nullable=False)
    product_name: str = Field(max_length=200)
    unit_name: str = Field(max_length=100)
    quantity: Decimal = Field(sa_type=Numeric(20, 6))
    reference_price: Decimal = Field(default=Decimal("0"), sa_type=Numeric(20, 4))
    tax_rate: Decimal = Field(default=Decimal("0"), sa_type=Numeric(7, 4))
    product_amount: Decimal = Field(default=Decimal("0"), sa_type=Numeric(20, 4))
    tax_amount: Decimal = Field(default=Decimal("0"), sa_type=Numeric(20, 4))
    total_amount: Decimal = Field(default=Decimal("0"), sa_type=Numeric(20, 4))
    returned_quantity: Decimal = Field(default=Decimal("0"), sa_type=Numeric(20, 6))
    remark: str | None = Field(default=None, max_length=500)


class PurchaseReturn(SQLModel, table=True):
    __tablename__ = "purchase_return"
    __table_args__ = (
        ForeignKeyConstraint(["purchase_in_id", "tenant_id"], ["erp.purchase_in.id", "erp.purchase_in.tenant_id"], ondelete="RESTRICT"),
        ForeignKeyConstraint(["purchase_order_id", "tenant_id"], ["erp.purchase_order.id", "erp.purchase_order.tenant_id"], ondelete="RESTRICT"),
        ForeignKeyConstraint(["supplier_id", "tenant_id"], ["erp.supplier.id", "erp.supplier.tenant_id"], ondelete="RESTRICT"),
        ForeignKeyConstraint(["settlement_account_id", "tenant_id"], ["erp.settlement_account.id", "erp.settlement_account.tenant_id"], ondelete="RESTRICT"),
        CheckConstraint("version > 0", name="ck_erp_purchase_return_version"),
        CheckConstraint("total_quantity > 0", name="ck_erp_purchase_return_quantity"),
        CheckConstraint("total_amount >= 0", name="ck_erp_purchase_return_total_amount"),
        CheckConstraint("product_amount >= 0", name="ck_erp_purchase_return_product_amount"),
        CheckConstraint("tax_amount >= 0", name="ck_erp_purchase_return_tax_amount"),
        CheckConstraint("discount_rate >= 0 AND discount_rate <= 100", name="ck_erp_purchase_return_discount_rate"),
        CheckConstraint("discount_amount >= 0", name="ck_erp_purchase_return_discount_amount"),
        CheckConstraint("other_fee >= 0", name="ck_erp_purchase_return_other_fee"),
        CheckConstraint("settled_amount >= 0", name="ck_erp_purchase_return_settled_amount"),
        UniqueConstraint("tenant_id", "no", name="uq_erp_purchase_return_tenant_no"),
        UniqueConstraint("id", "tenant_id", name="uq_erp_purchase_return_id_tenant_id"),
        {"schema": "erp"},
    )

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    tenant_id: uuid.UUID = Field(index=True, nullable=False)
    no: str = Field(max_length=32)
    purchase_in_id: uuid.UUID = Field(index=True, nullable=False)
    purchase_in_no: str = Field(max_length=32)
    purchase_order_id: uuid.UUID = Field(index=True, nullable=False)
    supplier_id: uuid.UUID = Field(index=True, nullable=False)
    supplier_name: str = Field(max_length=200)
    settlement_account_id: uuid.UUID | None = Field(default=None, index=True)
    status: DocumentStatus = Field(default=DocumentStatus.DRAFT, sa_type=String(32))
    version: int = 1
    business_at: datetime = Field(default_factory=get_datetime_utc, sa_type=DateTime(timezone=True), index=True)  # type: ignore
    owner_id: uuid.UUID = Field(index=True, nullable=False)
    total_quantity: Decimal = Field(sa_type=Numeric(20, 6))
    product_amount: Decimal = Field(default=Decimal("0"), sa_type=Numeric(20, 4))
    tax_amount: Decimal = Field(default=Decimal("0"), sa_type=Numeric(20, 4))
    discount_rate: Decimal = Field(default=Decimal("0"), sa_type=Numeric(7, 4))
    discount_amount: Decimal = Field(default=Decimal("0"), sa_type=Numeric(20, 4))
    other_fee: Decimal = Field(default=Decimal("0"), sa_type=Numeric(20, 4))
    total_amount: Decimal = Field(default=Decimal("0"), sa_type=Numeric(20, 4))
    settled_amount: Decimal = Field(default=Decimal("0"), sa_type=Numeric(20, 4))
    remark: str | None = Field(default=None, max_length=500)
    created_by: uuid.UUID = Field(nullable=False)
    updated_by: uuid.UUID = Field(nullable=False)
    approved_by: uuid.UUID | None = Field(default=None)
    approved_at: datetime | None = Field(default=None, sa_type=DateTime(timezone=True))  # type: ignore
    reversed_by: uuid.UUID | None = Field(default=None)
    reversed_at: datetime | None = Field(default=None, sa_type=DateTime(timezone=True))  # type: ignore
    created_at: datetime | None = Field(default_factory=get_datetime_utc, sa_type=DateTime(timezone=True))  # type: ignore
    updated_at: datetime | None = Field(default_factory=get_datetime_utc, sa_type=DateTime(timezone=True))  # type: ignore


class PurchaseReturnItem(SQLModel, table=True):
    __tablename__ = "purchase_return_item"
    __table_args__ = (
        ForeignKeyConstraint(["purchase_return_id", "tenant_id"], ["erp.purchase_return.id", "erp.purchase_return.tenant_id"], ondelete="CASCADE"),
        ForeignKeyConstraint(["purchase_in_item_id"], ["erp.purchase_in_item.id"], ondelete="RESTRICT"),
        ForeignKeyConstraint(["purchase_order_item_id"], ["erp.purchase_order_item.id"], ondelete="RESTRICT"),
        ForeignKeyConstraint(["product_id", "tenant_id"], ["erp.product.id", "erp.product.tenant_id"], ondelete="RESTRICT"),
        ForeignKeyConstraint(["warehouse_id", "tenant_id"], ["erp.warehouse.id", "erp.warehouse.tenant_id"], ondelete="RESTRICT"),
        CheckConstraint("quantity > 0", name="ck_erp_purchase_return_item_quantity"),
        CheckConstraint("tax_rate >= 0 AND tax_rate <= 100", name="ck_erp_purchase_return_item_tax_rate"),
        UniqueConstraint("purchase_return_id", "line_no", name="uq_erp_purchase_return_item_line"),
        UniqueConstraint("purchase_return_id", "purchase_in_item_id", name="uq_erp_purchase_return_item_in_line"),
        {"schema": "erp"},
    )

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    tenant_id: uuid.UUID = Field(index=True, nullable=False)
    purchase_return_id: uuid.UUID = Field(index=True, nullable=False)
    purchase_in_item_id: uuid.UUID = Field(index=True, nullable=False)
    purchase_order_item_id: uuid.UUID = Field(index=True, nullable=False)
    line_no: int
    product_id: uuid.UUID = Field(index=True, nullable=False)
    warehouse_id: uuid.UUID = Field(index=True, nullable=False)
    product_name: str = Field(max_length=200)
    unit_name: str = Field(max_length=100)
    quantity: Decimal = Field(sa_type=Numeric(20, 6))
    reference_price: Decimal = Field(default=Decimal("0"), sa_type=Numeric(20, 4))
    tax_rate: Decimal = Field(default=Decimal("0"), sa_type=Numeric(7, 4))
    product_amount: Decimal = Field(default=Decimal("0"), sa_type=Numeric(20, 4))
    tax_amount: Decimal = Field(default=Decimal("0"), sa_type=Numeric(20, 4))
    total_amount: Decimal = Field(default=Decimal("0"), sa_type=Numeric(20, 4))
    remark: str | None = Field(default=None, max_length=500)


class SaleOrder(SQLModel, table=True):
    __tablename__ = "sale_order"
    __table_args__ = (
        ForeignKeyConstraint(["customer_id", "tenant_id"], ["erp.customer.id", "erp.customer.tenant_id"], ondelete="RESTRICT"),
        ForeignKeyConstraint(["settlement_account_id", "tenant_id"], ["erp.settlement_account.id", "erp.settlement_account.tenant_id"], ondelete="RESTRICT"),
        CheckConstraint("version > 0", name="ck_erp_sale_order_version"),
        CheckConstraint("total_quantity > 0", name="ck_erp_sale_order_quantity"),
        CheckConstraint("product_amount >= 0", name="ck_erp_sale_order_product_amount"),
        CheckConstraint("tax_amount >= 0", name="ck_erp_sale_order_tax_amount"),
        CheckConstraint("discount_rate >= 0 AND discount_rate <= 100", name="ck_erp_sale_order_discount_rate"),
        CheckConstraint("discount_amount >= 0", name="ck_erp_sale_order_discount_amount"),
        CheckConstraint("deposit_amount >= 0", name="ck_erp_sale_order_deposit_amount"),
        CheckConstraint("total_amount >= 0", name="ck_erp_sale_order_total_amount"),
        UniqueConstraint("tenant_id", "no", name="uq_erp_sale_order_tenant_no"),
        UniqueConstraint("id", "tenant_id", name="uq_erp_sale_order_id_tenant_id"),
        {"schema": "erp"},
    )
    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    tenant_id: uuid.UUID = Field(index=True, nullable=False)
    no: str = Field(max_length=32)
    customer_id: uuid.UUID = Field(index=True, nullable=False)
    customer_name: str = Field(max_length=200)
    settlement_account_id: uuid.UUID | None = Field(default=None, index=True)
    status: DocumentStatus = Field(default=DocumentStatus.DRAFT, sa_type=String(32))
    version: int = 1
    business_at: datetime = Field(default_factory=get_datetime_utc, sa_type=DateTime(timezone=True), index=True)  # type: ignore
    owner_id: uuid.UUID = Field(index=True, nullable=False)
    total_quantity: Decimal = Field(sa_type=Numeric(20, 6))
    product_amount: Decimal = Field(sa_type=Numeric(20, 4))
    tax_amount: Decimal = Field(sa_type=Numeric(20, 4))
    discount_rate: Decimal = Field(default=Decimal("0"), sa_type=Numeric(7, 4))
    discount_amount: Decimal = Field(default=Decimal("0"), sa_type=Numeric(20, 4))
    deposit_amount: Decimal = Field(default=Decimal("0"), sa_type=Numeric(20, 4))
    total_amount: Decimal = Field(sa_type=Numeric(20, 4))
    remark: str | None = Field(default=None, max_length=500)
    created_by: uuid.UUID = Field(nullable=False)
    updated_by: uuid.UUID = Field(nullable=False)
    approved_by: uuid.UUID | None = Field(default=None)
    approved_at: datetime | None = Field(default=None, sa_type=DateTime(timezone=True))  # type: ignore
    reversed_by: uuid.UUID | None = Field(default=None)
    reversed_at: datetime | None = Field(default=None, sa_type=DateTime(timezone=True))  # type: ignore
    created_at: datetime | None = Field(default_factory=get_datetime_utc, sa_type=DateTime(timezone=True))  # type: ignore
    updated_at: datetime | None = Field(default_factory=get_datetime_utc, sa_type=DateTime(timezone=True))  # type: ignore


class SaleOrderItem(SQLModel, table=True):
    __tablename__ = "sale_order_item"
    __table_args__ = (
        ForeignKeyConstraint(["sale_order_id", "tenant_id"], ["erp.sale_order.id", "erp.sale_order.tenant_id"], ondelete="CASCADE"),
        ForeignKeyConstraint(["product_id", "tenant_id"], ["erp.product.id", "erp.product.tenant_id"], ondelete="RESTRICT"),
        ForeignKeyConstraint(["unit_id", "tenant_id"], ["erp.product_unit.id", "erp.product_unit.tenant_id"], ondelete="RESTRICT"),
        CheckConstraint("quantity > 0", name="ck_erp_sale_order_item_quantity"),
        CheckConstraint("unit_price >= 0", name="ck_erp_sale_order_item_unit_price"),
        CheckConstraint("tax_rate >= 0 AND tax_rate <= 100", name="ck_erp_sale_order_item_tax_rate"),
        CheckConstraint("shipped_quantity >= 0 AND shipped_quantity <= quantity", name="ck_erp_sale_order_item_shipped_quantity"),
        CheckConstraint("returned_quantity >= 0 AND returned_quantity <= shipped_quantity", name="ck_erp_sale_order_item_returned_quantity"),
        UniqueConstraint("sale_order_id", "line_no", name="uq_erp_sale_order_item_line"),
        {"schema": "erp"},
    )
    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    tenant_id: uuid.UUID = Field(index=True, nullable=False)
    sale_order_id: uuid.UUID = Field(index=True, nullable=False)
    line_no: int
    product_id: uuid.UUID = Field(index=True, nullable=False)
    unit_id: uuid.UUID = Field(index=True, nullable=False)
    product_name: str = Field(max_length=200)
    product_barcode: str | None = Field(default=None, max_length=100)
    unit_name: str = Field(max_length=100)
    quantity: Decimal = Field(sa_type=Numeric(20, 6))
    unit_price: Decimal = Field(sa_type=Numeric(20, 4))
    product_amount: Decimal = Field(sa_type=Numeric(20, 4))
    tax_rate: Decimal = Field(sa_type=Numeric(7, 4))
    tax_amount: Decimal = Field(sa_type=Numeric(20, 4))
    total_amount: Decimal = Field(sa_type=Numeric(20, 4))
    shipped_quantity: Decimal = Field(default=Decimal("0"), sa_type=Numeric(20, 6))
    returned_quantity: Decimal = Field(default=Decimal("0"), sa_type=Numeric(20, 6))
    remark: str | None = Field(default=None, max_length=500)


class SaleOut(SQLModel, table=True):
    __tablename__ = "sale_out"
    __table_args__ = (
        ForeignKeyConstraint(["sale_order_id", "tenant_id"], ["erp.sale_order.id", "erp.sale_order.tenant_id"], ondelete="RESTRICT"),
        ForeignKeyConstraint(["customer_id", "tenant_id"], ["erp.customer.id", "erp.customer.tenant_id"], ondelete="RESTRICT"),
        ForeignKeyConstraint(["settlement_account_id", "tenant_id"], ["erp.settlement_account.id", "erp.settlement_account.tenant_id"], ondelete="RESTRICT"),
        CheckConstraint("version > 0", name="ck_erp_sale_out_version"),
        CheckConstraint("total_quantity > 0", name="ck_erp_sale_out_quantity"),
        CheckConstraint("total_amount >= 0", name="ck_erp_sale_out_total_amount"),
        CheckConstraint("product_amount >= 0", name="ck_erp_sale_out_product_amount"),
        CheckConstraint("tax_amount >= 0", name="ck_erp_sale_out_tax_amount"),
        CheckConstraint("discount_rate >= 0 AND discount_rate <= 100", name="ck_erp_sale_out_discount_rate"),
        CheckConstraint("discount_amount >= 0", name="ck_erp_sale_out_discount_amount"),
        CheckConstraint("other_deduction >= 0", name="ck_erp_sale_out_other_deduction"),
        CheckConstraint("settled_amount >= 0", name="ck_erp_sale_out_settled_amount"),
        UniqueConstraint("tenant_id", "no", name="uq_erp_sale_out_tenant_no"),
        UniqueConstraint("id", "tenant_id", name="uq_erp_sale_out_id_tenant_id"),
        {"schema": "erp"},
    )

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    tenant_id: uuid.UUID = Field(index=True, nullable=False)
    no: str = Field(max_length=32)
    sale_order_id: uuid.UUID = Field(index=True, nullable=False)
    sale_order_no: str = Field(max_length=32)
    customer_id: uuid.UUID = Field(index=True, nullable=False)
    customer_name: str = Field(max_length=200)
    settlement_account_id: uuid.UUID | None = Field(default=None, index=True)
    status: DocumentStatus = Field(default=DocumentStatus.DRAFT, sa_type=String(32))
    version: int = 1
    business_at: datetime = Field(default_factory=get_datetime_utc, sa_type=DateTime(timezone=True), index=True)  # type: ignore
    owner_id: uuid.UUID = Field(index=True, nullable=False)
    total_quantity: Decimal = Field(sa_type=Numeric(20, 6))
    product_amount: Decimal = Field(default=Decimal("0"), sa_type=Numeric(20, 4))
    tax_amount: Decimal = Field(default=Decimal("0"), sa_type=Numeric(20, 4))
    discount_rate: Decimal = Field(default=Decimal("0"), sa_type=Numeric(7, 4))
    discount_amount: Decimal = Field(default=Decimal("0"), sa_type=Numeric(20, 4))
    other_deduction: Decimal = Field(default=Decimal("0"), sa_type=Numeric(20, 4))
    total_amount: Decimal = Field(default=Decimal("0"), sa_type=Numeric(20, 4))
    settled_amount: Decimal = Field(default=Decimal("0"), sa_type=Numeric(20, 4))
    remark: str | None = Field(default=None, max_length=500)
    created_by: uuid.UUID = Field(nullable=False)
    updated_by: uuid.UUID = Field(nullable=False)
    approved_by: uuid.UUID | None = Field(default=None)
    approved_at: datetime | None = Field(default=None, sa_type=DateTime(timezone=True))  # type: ignore
    reversed_by: uuid.UUID | None = Field(default=None)
    reversed_at: datetime | None = Field(default=None, sa_type=DateTime(timezone=True))  # type: ignore
    created_at: datetime | None = Field(default_factory=get_datetime_utc, sa_type=DateTime(timezone=True))  # type: ignore
    updated_at: datetime | None = Field(default_factory=get_datetime_utc, sa_type=DateTime(timezone=True))  # type: ignore


class SaleOutItem(SQLModel, table=True):
    __tablename__ = "sale_out_item"
    __table_args__ = (
        ForeignKeyConstraint(["sale_out_id", "tenant_id"], ["erp.sale_out.id", "erp.sale_out.tenant_id"], ondelete="CASCADE"),
        ForeignKeyConstraint(["sale_order_item_id"], ["erp.sale_order_item.id"], ondelete="RESTRICT"),
        ForeignKeyConstraint(["product_id", "tenant_id"], ["erp.product.id", "erp.product.tenant_id"], ondelete="RESTRICT"),
        ForeignKeyConstraint(["warehouse_id", "tenant_id"], ["erp.warehouse.id", "erp.warehouse.tenant_id"], ondelete="RESTRICT"),
        CheckConstraint("quantity > 0", name="ck_erp_sale_out_item_quantity"),
        CheckConstraint("tax_rate >= 0 AND tax_rate <= 100", name="ck_erp_sale_out_item_tax_rate"),
        CheckConstraint("returned_quantity >= 0 AND returned_quantity <= quantity", name="ck_erp_sale_out_item_returned_quantity"),
        UniqueConstraint("sale_out_id", "line_no", name="uq_erp_sale_out_item_line"),
        UniqueConstraint("sale_out_id", "sale_order_item_id", name="uq_erp_sale_out_item_order_line"),
        {"schema": "erp"},
    )

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    tenant_id: uuid.UUID = Field(index=True, nullable=False)
    sale_out_id: uuid.UUID = Field(index=True, nullable=False)
    sale_order_item_id: uuid.UUID = Field(index=True, nullable=False)
    line_no: int
    product_id: uuid.UUID = Field(index=True, nullable=False)
    warehouse_id: uuid.UUID = Field(index=True, nullable=False)
    product_name: str = Field(max_length=200)
    unit_name: str = Field(max_length=100)
    quantity: Decimal = Field(sa_type=Numeric(20, 6))
    reference_price: Decimal = Field(default=Decimal("0"), sa_type=Numeric(20, 4))
    tax_rate: Decimal = Field(default=Decimal("0"), sa_type=Numeric(7, 4))
    product_amount: Decimal = Field(default=Decimal("0"), sa_type=Numeric(20, 4))
    tax_amount: Decimal = Field(default=Decimal("0"), sa_type=Numeric(20, 4))
    total_amount: Decimal = Field(default=Decimal("0"), sa_type=Numeric(20, 4))
    returned_quantity: Decimal = Field(default=Decimal("0"), sa_type=Numeric(20, 6))
    remark: str | None = Field(default=None, max_length=500)


class SaleReturn(SQLModel, table=True):
    __tablename__ = "sale_return"
    __table_args__ = (
        ForeignKeyConstraint(["sale_out_id", "tenant_id"], ["erp.sale_out.id", "erp.sale_out.tenant_id"], ondelete="RESTRICT"),
        ForeignKeyConstraint(["sale_order_id", "tenant_id"], ["erp.sale_order.id", "erp.sale_order.tenant_id"], ondelete="RESTRICT"),
        ForeignKeyConstraint(["customer_id", "tenant_id"], ["erp.customer.id", "erp.customer.tenant_id"], ondelete="RESTRICT"),
        ForeignKeyConstraint(["settlement_account_id", "tenant_id"], ["erp.settlement_account.id", "erp.settlement_account.tenant_id"], ondelete="RESTRICT"),
        CheckConstraint("version > 0", name="ck_erp_sale_return_version"),
        CheckConstraint("total_quantity > 0", name="ck_erp_sale_return_quantity"),
        CheckConstraint("total_amount >= 0", name="ck_erp_sale_return_total_amount"),
        CheckConstraint("product_amount >= 0", name="ck_erp_sale_return_product_amount"),
        CheckConstraint("tax_amount >= 0", name="ck_erp_sale_return_tax_amount"),
        CheckConstraint("discount_rate >= 0 AND discount_rate <= 100", name="ck_erp_sale_return_discount_rate"),
        CheckConstraint("discount_amount >= 0", name="ck_erp_sale_return_discount_amount"),
        CheckConstraint("other_deduction >= 0", name="ck_erp_sale_return_other_deduction"),
        CheckConstraint("settled_amount >= 0", name="ck_erp_sale_return_settled_amount"),
        UniqueConstraint("tenant_id", "no", name="uq_erp_sale_return_tenant_no"),
        UniqueConstraint("id", "tenant_id", name="uq_erp_sale_return_id_tenant_id"),
        {"schema": "erp"},
    )

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    tenant_id: uuid.UUID = Field(index=True, nullable=False)
    no: str = Field(max_length=32)
    sale_out_id: uuid.UUID = Field(index=True, nullable=False)
    sale_out_no: str = Field(max_length=32)
    sale_order_id: uuid.UUID = Field(index=True, nullable=False)
    customer_id: uuid.UUID = Field(index=True, nullable=False)
    customer_name: str = Field(max_length=200)
    settlement_account_id: uuid.UUID | None = Field(default=None, index=True)
    status: DocumentStatus = Field(default=DocumentStatus.DRAFT, sa_type=String(32))
    version: int = 1
    business_at: datetime = Field(default_factory=get_datetime_utc, sa_type=DateTime(timezone=True), index=True)  # type: ignore
    owner_id: uuid.UUID = Field(index=True, nullable=False)
    total_quantity: Decimal = Field(sa_type=Numeric(20, 6))
    product_amount: Decimal = Field(default=Decimal("0"), sa_type=Numeric(20, 4))
    tax_amount: Decimal = Field(default=Decimal("0"), sa_type=Numeric(20, 4))
    discount_rate: Decimal = Field(default=Decimal("0"), sa_type=Numeric(7, 4))
    discount_amount: Decimal = Field(default=Decimal("0"), sa_type=Numeric(20, 4))
    other_deduction: Decimal = Field(default=Decimal("0"), sa_type=Numeric(20, 4))
    total_amount: Decimal = Field(default=Decimal("0"), sa_type=Numeric(20, 4))
    settled_amount: Decimal = Field(default=Decimal("0"), sa_type=Numeric(20, 4))
    remark: str | None = Field(default=None, max_length=500)
    created_by: uuid.UUID = Field(nullable=False)
    updated_by: uuid.UUID = Field(nullable=False)
    approved_by: uuid.UUID | None = Field(default=None)
    approved_at: datetime | None = Field(default=None, sa_type=DateTime(timezone=True))  # type: ignore
    reversed_by: uuid.UUID | None = Field(default=None)
    reversed_at: datetime | None = Field(default=None, sa_type=DateTime(timezone=True))  # type: ignore
    created_at: datetime | None = Field(default_factory=get_datetime_utc, sa_type=DateTime(timezone=True))  # type: ignore
    updated_at: datetime | None = Field(default_factory=get_datetime_utc, sa_type=DateTime(timezone=True))  # type: ignore


class SaleReturnItem(SQLModel, table=True):
    __tablename__ = "sale_return_item"
    __table_args__ = (
        ForeignKeyConstraint(["sale_return_id", "tenant_id"], ["erp.sale_return.id", "erp.sale_return.tenant_id"], ondelete="CASCADE"),
        ForeignKeyConstraint(["sale_out_item_id"], ["erp.sale_out_item.id"], ondelete="RESTRICT"),
        ForeignKeyConstraint(["sale_order_item_id"], ["erp.sale_order_item.id"], ondelete="RESTRICT"),
        ForeignKeyConstraint(["product_id", "tenant_id"], ["erp.product.id", "erp.product.tenant_id"], ondelete="RESTRICT"),
        ForeignKeyConstraint(["warehouse_id", "tenant_id"], ["erp.warehouse.id", "erp.warehouse.tenant_id"], ondelete="RESTRICT"),
        CheckConstraint("quantity > 0", name="ck_erp_sale_return_item_quantity"),
        CheckConstraint("tax_rate >= 0 AND tax_rate <= 100", name="ck_erp_sale_return_item_tax_rate"),
        UniqueConstraint("sale_return_id", "line_no", name="uq_erp_sale_return_item_line"),
        UniqueConstraint("sale_return_id", "sale_out_item_id", name="uq_erp_sale_return_item_out_line"),
        {"schema": "erp"},
    )

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    tenant_id: uuid.UUID = Field(index=True, nullable=False)
    sale_return_id: uuid.UUID = Field(index=True, nullable=False)
    sale_out_item_id: uuid.UUID = Field(index=True, nullable=False)
    sale_order_item_id: uuid.UUID = Field(index=True, nullable=False)
    line_no: int
    product_id: uuid.UUID = Field(index=True, nullable=False)
    warehouse_id: uuid.UUID = Field(index=True, nullable=False)
    product_name: str = Field(max_length=200)
    unit_name: str = Field(max_length=100)
    quantity: Decimal = Field(sa_type=Numeric(20, 6))
    reference_price: Decimal = Field(default=Decimal("0"), sa_type=Numeric(20, 4))
    tax_rate: Decimal = Field(default=Decimal("0"), sa_type=Numeric(7, 4))
    product_amount: Decimal = Field(default=Decimal("0"), sa_type=Numeric(20, 4))
    tax_amount: Decimal = Field(default=Decimal("0"), sa_type=Numeric(20, 4))
    total_amount: Decimal = Field(default=Decimal("0"), sa_type=Numeric(20, 4))
    remark: str | None = Field(default=None, max_length=500)


class StockBalance(SQLModel, table=True):
    __tablename__ = "stock_balance"
    __table_args__ = (
        ForeignKeyConstraint(
            ["product_id", "tenant_id"],
            ["erp.product.id", "erp.product.tenant_id"],
            ondelete="RESTRICT",
        ),
        ForeignKeyConstraint(
            ["warehouse_id", "tenant_id"],
            ["erp.warehouse.id", "erp.warehouse.tenant_id"],
            ondelete="RESTRICT",
        ),
        CheckConstraint("quantity >= 0", name="ck_erp_stock_balance_quantity"),
        CheckConstraint("version > 0", name="ck_erp_stock_balance_version"),
        UniqueConstraint(
            "tenant_id",
            "product_id",
            "warehouse_id",
            name="uq_erp_stock_balance_tenant_product_warehouse",
        ),
        UniqueConstraint("id", "tenant_id", name="uq_erp_stock_balance_id_tenant_id"),
        {"schema": "erp"},
    )

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    tenant_id: uuid.UUID = Field(index=True, nullable=False)
    product_id: uuid.UUID = Field(index=True, nullable=False)
    warehouse_id: uuid.UUID = Field(index=True, nullable=False)
    quantity: Decimal = Field(default=Decimal("0"), sa_type=Numeric(20, 6))
    version: int = 1
    updated_at: datetime | None = Field(
        default_factory=get_datetime_utc,
        sa_type=DateTime(timezone=True),  # type: ignore
    )


class StockLedger(SQLModel, table=True):
    __tablename__ = "stock_ledger"
    __table_args__ = (
        ForeignKeyConstraint(
            ["product_id", "tenant_id"],
            ["erp.product.id", "erp.product.tenant_id"],
            ondelete="RESTRICT",
        ),
        ForeignKeyConstraint(
            ["warehouse_id", "tenant_id"],
            ["erp.warehouse.id", "erp.warehouse.tenant_id"],
            ondelete="RESTRICT",
        ),
        CheckConstraint("delta_quantity <> 0", name="ck_erp_stock_ledger_delta"),
        CheckConstraint(
            "balance_after >= 0", name="ck_erp_stock_ledger_balance_after"
        ),
        UniqueConstraint(
            "tenant_id",
            "source_document_type",
            "source_document_id",
            "source_item_id",
            "source_version",
            "ledger_type",
            name="uq_erp_stock_ledger_source_effect",
        ),
        Index(
            "uq_erp_stock_ledger_reversal",
            "tenant_id",
            "reversal_of_id",
            unique=True,
            postgresql_where=text("reversal_of_id IS NOT NULL"),
        ),
        {"schema": "erp"},
    )

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    tenant_id: uuid.UUID = Field(index=True, nullable=False)
    product_id: uuid.UUID = Field(index=True, nullable=False)
    warehouse_id: uuid.UUID = Field(index=True, nullable=False)
    delta_quantity: Decimal = Field(sa_type=Numeric(20, 6))
    balance_after: Decimal = Field(sa_type=Numeric(20, 6))
    ledger_type: StockLedgerType = Field(sa_type=String(32), index=True)
    source_document_type: str = Field(max_length=32, index=True)
    source_document_id: uuid.UUID = Field(index=True, nullable=False)
    source_item_id: uuid.UUID = Field(index=True, nullable=False)
    source_document_no: str = Field(max_length=32)
    source_version: int
    reversal_of_id: uuid.UUID | None = Field(default=None, index=True)
    operator_id: uuid.UUID = Field(nullable=False)
    occurred_at: datetime = Field(  # type: ignore
        default_factory=get_datetime_utc,
        sa_type=DateTime(timezone=True),
        index=True,
    )


class StockIn(SQLModel, table=True):
    __tablename__ = "stock_in"
    __table_args__ = (
        ForeignKeyConstraint(
            ["supplier_id", "tenant_id"],
            ["erp.supplier.id", "erp.supplier.tenant_id"],
            ondelete="RESTRICT",
        ),
        CheckConstraint("version > 0", name="ck_erp_stock_in_version"),
        UniqueConstraint("tenant_id", "no", name="uq_erp_stock_in_tenant_no"),
        UniqueConstraint("id", "tenant_id", name="uq_erp_stock_in_id_tenant_id"),
        {"schema": "erp"},
    )

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    tenant_id: uuid.UUID = Field(index=True, nullable=False)
    no: str = Field(max_length=32)
    status: DocumentStatus = Field(default=DocumentStatus.DRAFT, sa_type=String(32))
    version: int = 1
    business_at: datetime = Field(  # type: ignore
        default_factory=get_datetime_utc,
        sa_type=DateTime(timezone=True),
        index=True,
    )
    owner_id: uuid.UUID = Field(index=True, nullable=False)
    supplier_id: uuid.UUID | None = Field(default=None, index=True)
    total_quantity: Decimal = Field(default=Decimal("0"), sa_type=Numeric(20, 6))
    total_amount: Decimal = Field(default=Decimal("0"), sa_type=Numeric(20, 4))
    remark: str | None = Field(default=None, max_length=500)
    created_by: uuid.UUID = Field(nullable=False)
    updated_by: uuid.UUID = Field(nullable=False)
    approved_by: uuid.UUID | None = Field(default=None)
    approved_at: datetime | None = Field(default=None, sa_type=DateTime(timezone=True))  # type: ignore
    reversed_by: uuid.UUID | None = Field(default=None)
    reversed_at: datetime | None = Field(default=None, sa_type=DateTime(timezone=True))  # type: ignore
    created_at: datetime | None = Field(
        default_factory=get_datetime_utc,
        sa_type=DateTime(timezone=True),  # type: ignore
    )
    updated_at: datetime | None = Field(
        default_factory=get_datetime_utc,
        sa_type=DateTime(timezone=True),  # type: ignore
    )


class StockInItem(SQLModel, table=True):
    __tablename__ = "stock_in_item"
    __table_args__ = (
        ForeignKeyConstraint(
            ["stock_in_id", "tenant_id"],
            ["erp.stock_in.id", "erp.stock_in.tenant_id"],
            ondelete="CASCADE",
        ),
        ForeignKeyConstraint(
            ["product_id", "tenant_id"],
            ["erp.product.id", "erp.product.tenant_id"],
            ondelete="RESTRICT",
        ),
        ForeignKeyConstraint(
            ["warehouse_id", "tenant_id"],
            ["erp.warehouse.id", "erp.warehouse.tenant_id"],
            ondelete="RESTRICT",
        ),
        CheckConstraint("quantity > 0", name="ck_erp_stock_in_item_quantity"),
        UniqueConstraint("stock_in_id", "line_no", name="uq_erp_stock_in_item_line"),
        {"schema": "erp"},
    )

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    tenant_id: uuid.UUID = Field(index=True, nullable=False)
    stock_in_id: uuid.UUID = Field(index=True, nullable=False)
    line_no: int
    product_id: uuid.UUID = Field(index=True, nullable=False)
    warehouse_id: uuid.UUID = Field(index=True, nullable=False)
    quantity: Decimal = Field(sa_type=Numeric(20, 6))
    reference_price: Decimal = Field(default=Decimal("0"), sa_type=Numeric(20, 4))
    remark: str | None = Field(default=None, max_length=500)


class StockOut(SQLModel, table=True):
    __tablename__ = "stock_out"
    __table_args__ = (
        ForeignKeyConstraint(
            ["customer_id", "tenant_id"],
            ["erp.customer.id", "erp.customer.tenant_id"],
            ondelete="RESTRICT",
        ),
        CheckConstraint("version > 0", name="ck_erp_stock_out_version"),
        UniqueConstraint("tenant_id", "no", name="uq_erp_stock_out_tenant_no"),
        UniqueConstraint("id", "tenant_id", name="uq_erp_stock_out_id_tenant_id"),
        {"schema": "erp"},
    )

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    tenant_id: uuid.UUID = Field(index=True, nullable=False)
    no: str = Field(max_length=32)
    status: DocumentStatus = Field(default=DocumentStatus.DRAFT, sa_type=String(32))
    version: int = 1
    business_at: datetime = Field(  # type: ignore
        default_factory=get_datetime_utc,
        sa_type=DateTime(timezone=True),
        index=True,
    )
    owner_id: uuid.UUID = Field(index=True, nullable=False)
    customer_id: uuid.UUID | None = Field(default=None, index=True)
    total_quantity: Decimal = Field(default=Decimal("0"), sa_type=Numeric(20, 6))
    total_amount: Decimal = Field(default=Decimal("0"), sa_type=Numeric(20, 4))
    remark: str | None = Field(default=None, max_length=500)
    created_by: uuid.UUID = Field(nullable=False)
    updated_by: uuid.UUID = Field(nullable=False)
    approved_by: uuid.UUID | None = Field(default=None)
    approved_at: datetime | None = Field(default=None, sa_type=DateTime(timezone=True))  # type: ignore
    reversed_by: uuid.UUID | None = Field(default=None)
    reversed_at: datetime | None = Field(default=None, sa_type=DateTime(timezone=True))  # type: ignore
    created_at: datetime | None = Field(
        default_factory=get_datetime_utc,
        sa_type=DateTime(timezone=True),  # type: ignore
    )
    updated_at: datetime | None = Field(
        default_factory=get_datetime_utc,
        sa_type=DateTime(timezone=True),  # type: ignore
    )


class StockOutItem(SQLModel, table=True):
    __tablename__ = "stock_out_item"
    __table_args__ = (
        ForeignKeyConstraint(
            ["stock_out_id", "tenant_id"],
            ["erp.stock_out.id", "erp.stock_out.tenant_id"],
            ondelete="CASCADE",
        ),
        ForeignKeyConstraint(
            ["product_id", "tenant_id"],
            ["erp.product.id", "erp.product.tenant_id"],
            ondelete="RESTRICT",
        ),
        ForeignKeyConstraint(
            ["warehouse_id", "tenant_id"],
            ["erp.warehouse.id", "erp.warehouse.tenant_id"],
            ondelete="RESTRICT",
        ),
        CheckConstraint("quantity > 0", name="ck_erp_stock_out_item_quantity"),
        UniqueConstraint("stock_out_id", "line_no", name="uq_erp_stock_out_item_line"),
        {"schema": "erp"},
    )

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    tenant_id: uuid.UUID = Field(index=True, nullable=False)
    stock_out_id: uuid.UUID = Field(index=True, nullable=False)
    line_no: int
    product_id: uuid.UUID = Field(index=True, nullable=False)
    warehouse_id: uuid.UUID = Field(index=True, nullable=False)
    quantity: Decimal = Field(sa_type=Numeric(20, 6))
    reference_price: Decimal = Field(default=Decimal("0"), sa_type=Numeric(20, 4))
    remark: str | None = Field(default=None, max_length=500)


class StockMove(SQLModel, table=True):
    __tablename__ = "stock_move"
    __table_args__ = (
        CheckConstraint("version > 0", name="ck_erp_stock_move_version"),
        UniqueConstraint("tenant_id", "no", name="uq_erp_stock_move_tenant_no"),
        UniqueConstraint("id", "tenant_id", name="uq_erp_stock_move_id_tenant_id"),
        {"schema": "erp"},
    )

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    tenant_id: uuid.UUID = Field(index=True, nullable=False)
    no: str = Field(max_length=32)
    status: DocumentStatus = Field(default=DocumentStatus.DRAFT, sa_type=String(32))
    version: int = 1
    business_at: datetime = Field(  # type: ignore
        default_factory=get_datetime_utc,
        sa_type=DateTime(timezone=True),
        index=True,
    )
    owner_id: uuid.UUID = Field(index=True, nullable=False)
    total_quantity: Decimal = Field(default=Decimal("0"), sa_type=Numeric(20, 6))
    total_amount: Decimal = Field(default=Decimal("0"), sa_type=Numeric(20, 4))
    remark: str | None = Field(default=None, max_length=500)
    created_by: uuid.UUID = Field(nullable=False)
    updated_by: uuid.UUID = Field(nullable=False)
    approved_by: uuid.UUID | None = Field(default=None)
    approved_at: datetime | None = Field(default=None, sa_type=DateTime(timezone=True))  # type: ignore
    reversed_by: uuid.UUID | None = Field(default=None)
    reversed_at: datetime | None = Field(default=None, sa_type=DateTime(timezone=True))  # type: ignore
    created_at: datetime | None = Field(
        default_factory=get_datetime_utc,
        sa_type=DateTime(timezone=True),  # type: ignore
    )
    updated_at: datetime | None = Field(
        default_factory=get_datetime_utc,
        sa_type=DateTime(timezone=True),  # type: ignore
    )


class StockMoveItem(SQLModel, table=True):
    __tablename__ = "stock_move_item"
    __table_args__ = (
        ForeignKeyConstraint(
            ["stock_move_id", "tenant_id"],
            ["erp.stock_move.id", "erp.stock_move.tenant_id"],
            ondelete="CASCADE",
        ),
        ForeignKeyConstraint(
            ["product_id", "tenant_id"],
            ["erp.product.id", "erp.product.tenant_id"],
            ondelete="RESTRICT",
        ),
        ForeignKeyConstraint(
            ["from_warehouse_id", "tenant_id"],
            ["erp.warehouse.id", "erp.warehouse.tenant_id"],
            ondelete="RESTRICT",
        ),
        ForeignKeyConstraint(
            ["to_warehouse_id", "tenant_id"],
            ["erp.warehouse.id", "erp.warehouse.tenant_id"],
            ondelete="RESTRICT",
        ),
        CheckConstraint("quantity > 0", name="ck_erp_stock_move_item_quantity"),
        CheckConstraint(
            "from_warehouse_id <> to_warehouse_id",
            name="ck_erp_stock_move_item_warehouses",
        ),
        UniqueConstraint("stock_move_id", "line_no", name="uq_erp_stock_move_item_line"),
        {"schema": "erp"},
    )

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    tenant_id: uuid.UUID = Field(index=True, nullable=False)
    stock_move_id: uuid.UUID = Field(index=True, nullable=False)
    line_no: int
    product_id: uuid.UUID = Field(index=True, nullable=False)
    from_warehouse_id: uuid.UUID = Field(index=True, nullable=False)
    to_warehouse_id: uuid.UUID = Field(index=True, nullable=False)
    quantity: Decimal = Field(sa_type=Numeric(20, 6))
    reference_price: Decimal = Field(default=Decimal("0"), sa_type=Numeric(20, 4))
    remark: str | None = Field(default=None, max_length=500)


class StockCheck(SQLModel, table=True):
    __tablename__ = "stock_check"
    __table_args__ = (
        CheckConstraint("version > 0", name="ck_erp_stock_check_version"),
        UniqueConstraint("tenant_id", "no", name="uq_erp_stock_check_tenant_no"),
        UniqueConstraint("id", "tenant_id", name="uq_erp_stock_check_id_tenant_id"),
        {"schema": "erp"},
    )

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    tenant_id: uuid.UUID = Field(index=True, nullable=False)
    no: str = Field(max_length=32)
    status: DocumentStatus = Field(default=DocumentStatus.DRAFT, sa_type=String(32))
    version: int = 1
    business_at: datetime = Field(  # type: ignore
        default_factory=get_datetime_utc,
        sa_type=DateTime(timezone=True),
        index=True,
    )
    owner_id: uuid.UUID = Field(index=True, nullable=False)
    total_quantity: Decimal = Field(default=Decimal("0"), sa_type=Numeric(20, 6))
    total_amount: Decimal = Field(default=Decimal("0"), sa_type=Numeric(20, 4))
    remark: str | None = Field(default=None, max_length=500)
    created_by: uuid.UUID = Field(nullable=False)
    updated_by: uuid.UUID = Field(nullable=False)
    approved_by: uuid.UUID | None = Field(default=None)
    approved_at: datetime | None = Field(default=None, sa_type=DateTime(timezone=True))  # type: ignore
    reversed_by: uuid.UUID | None = Field(default=None)
    reversed_at: datetime | None = Field(default=None, sa_type=DateTime(timezone=True))  # type: ignore
    created_at: datetime | None = Field(
        default_factory=get_datetime_utc,
        sa_type=DateTime(timezone=True),  # type: ignore
    )
    updated_at: datetime | None = Field(
        default_factory=get_datetime_utc,
        sa_type=DateTime(timezone=True),  # type: ignore
    )


class StockCheckItem(SQLModel, table=True):
    __tablename__ = "stock_check_item"
    __table_args__ = (
        ForeignKeyConstraint(
            ["stock_check_id", "tenant_id"],
            ["erp.stock_check.id", "erp.stock_check.tenant_id"],
            ondelete="CASCADE",
        ),
        ForeignKeyConstraint(
            ["product_id", "tenant_id"],
            ["erp.product.id", "erp.product.tenant_id"],
            ondelete="RESTRICT",
        ),
        ForeignKeyConstraint(
            ["warehouse_id", "tenant_id"],
            ["erp.warehouse.id", "erp.warehouse.tenant_id"],
            ondelete="RESTRICT",
        ),
        CheckConstraint("snapshot_quantity >= 0", name="ck_erp_stock_check_item_snapshot"),
        CheckConstraint("actual_quantity >= 0", name="ck_erp_stock_check_item_actual"),
        CheckConstraint(
            "difference_quantity = actual_quantity - snapshot_quantity",
            name="ck_erp_stock_check_item_difference",
        ),
        UniqueConstraint("stock_check_id", "line_no", name="uq_erp_stock_check_item_line"),
        {"schema": "erp"},
    )

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    tenant_id: uuid.UUID = Field(index=True, nullable=False)
    stock_check_id: uuid.UUID = Field(index=True, nullable=False)
    line_no: int
    product_id: uuid.UUID = Field(index=True, nullable=False)
    warehouse_id: uuid.UUID = Field(index=True, nullable=False)
    snapshot_quantity: Decimal = Field(sa_type=Numeric(20, 6))
    actual_quantity: Decimal = Field(sa_type=Numeric(20, 6))
    difference_quantity: Decimal = Field(sa_type=Numeric(20, 6))
    reference_price: Decimal = Field(default=Decimal("0"), sa_type=Numeric(20, 4))
    difference_amount: Decimal = Field(default=Decimal("0"), sa_type=Numeric(20, 4))
    remark: str | None = Field(default=None, max_length=500)


ERP_TENANT_SCOPED_MODELS = (
    ErpSetting,
    ReconciliationRun,
    ProductUnit,
    ProductCategory,
    Product,
    Warehouse,
    WarehouseUserGrant,
    Supplier,
    Customer,
    SettlementAccount,
    DocumentActionLog,
    CommandReceipt,
    DocumentAttachment,
    FinancePayment,
    FinancePaymentItem,
    FinanceReceipt,
    FinanceReceiptItem,
    DocumentSequence,
    PurchaseOrder,
    PurchaseOrderItem,
    PurchaseIn,
    PurchaseInItem,
    PurchaseReturn,
    PurchaseReturnItem,
    SaleOrder,
    SaleOrderItem,
    SaleOut,
    SaleOutItem,
    SaleReturn,
    SaleReturnItem,
    StockBalance,
    StockLedger,
    StockIn,
    StockInItem,
    StockOut,
    StockOutItem,
    StockMove,
    StockMoveItem,
    StockCheck,
    StockCheckItem,
)
