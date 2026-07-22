import uuid
from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field, field_validator


class StrippedInputModel(BaseModel):
    """Normalize user-entered text before business uniqueness checks."""

    model_config = ConfigDict(str_strip_whitespace=True)


class ProductUnitCreate(StrippedInputModel):
    code: str = Field(min_length=1, max_length=50)
    name: str = Field(min_length=1, max_length=100)
    symbol: str | None = Field(default=None, max_length=20)
    is_active: bool = True


class ProductUnitUpdate(StrippedInputModel):
    code: str | None = Field(default=None, min_length=1, max_length=50)
    name: str | None = Field(default=None, min_length=1, max_length=100)
    symbol: str | None = Field(default=None, max_length=20)
    is_active: bool | None = None


class ProductUnitPublic(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    tenant_id: uuid.UUID
    code: str
    name: str
    symbol: str | None = None
    is_active: bool
    created_at: datetime | None = None
    updated_at: datetime | None = None


class ProductCategoryCreate(StrippedInputModel):
    code: str = Field(min_length=1, max_length=50)
    name: str = Field(min_length=1, max_length=100)
    parent_id: uuid.UUID | None = None
    sort: int = Field(default=0, ge=0)
    is_active: bool = True


class ProductCategoryUpdate(StrippedInputModel):
    code: str | None = Field(default=None, min_length=1, max_length=50)
    name: str | None = Field(default=None, min_length=1, max_length=100)
    parent_id: uuid.UUID | None = None
    sort: int | None = Field(default=None, ge=0)
    is_active: bool | None = None


class ProductCategoryPublic(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    tenant_id: uuid.UUID
    code: str
    name: str
    parent_id: uuid.UUID | None = None
    sort: int
    is_active: bool
    created_at: datetime | None = None
    updated_at: datetime | None = None


class ProductCreate(StrippedInputModel):
    code: str = Field(min_length=1, max_length=100)
    name: str = Field(min_length=1, max_length=200)
    category_id: uuid.UUID
    unit_id: uuid.UUID
    barcode: str | None = Field(default=None, max_length=100)
    specification: str | None = Field(default=None, max_length=500)
    weight: Decimal = Field(default=Decimal("0"), ge=0, max_digits=20, decimal_places=6)
    expiry_days: int = Field(default=0, ge=0)
    remark: str | None = Field(default=None, max_length=500)
    purchase_reference_price: Decimal = Field(default=Decimal("0"), ge=0, max_digits=20, decimal_places=4)
    sale_reference_price: Decimal = Field(default=Decimal("0"), ge=0, max_digits=20, decimal_places=4)
    min_sale_price: Decimal = Field(default=Decimal("0"), ge=0, max_digits=20, decimal_places=4)
    is_active: bool = True

    @field_validator("barcode")
    @classmethod
    def blank_barcode_is_absent(cls, value: str | None) -> str | None:
        return value or None


class ProductUpdate(StrippedInputModel):
    code: str | None = Field(default=None, min_length=1, max_length=100)
    name: str | None = Field(default=None, min_length=1, max_length=200)
    category_id: uuid.UUID | None = None
    unit_id: uuid.UUID | None = None
    barcode: str | None = Field(default=None, max_length=100)
    specification: str | None = Field(default=None, max_length=500)
    weight: Decimal | None = Field(default=None, ge=0, max_digits=20, decimal_places=6)
    expiry_days: int | None = Field(default=None, ge=0)
    remark: str | None = Field(default=None, max_length=500)
    purchase_reference_price: Decimal | None = Field(default=None, ge=0, max_digits=20, decimal_places=4)
    sale_reference_price: Decimal | None = Field(default=None, ge=0, max_digits=20, decimal_places=4)
    min_sale_price: Decimal | None = Field(default=None, ge=0, max_digits=20, decimal_places=4)
    is_active: bool | None = None

    @field_validator("barcode")
    @classmethod
    def blank_barcode_is_absent(cls, value: str | None) -> str | None:
        return value or None


class ProductPublic(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    tenant_id: uuid.UUID
    code: str
    name: str
    category_id: uuid.UUID | None = None
    unit_id: uuid.UUID
    barcode: str | None = None
    specification: str | None = None
    weight: Decimal
    expiry_days: int
    remark: str | None = None
    purchase_reference_price: Decimal
    sale_reference_price: Decimal
    min_sale_price: Decimal
    is_active: bool
    created_at: datetime | None = None
    updated_at: datetime | None = None


class WarehouseCreate(StrippedInputModel):
    code: str = Field(min_length=1, max_length=50)
    name: str = Field(min_length=1, max_length=100)
    contact_name: str | None = Field(default=None, max_length=100)
    contact_phone: str | None = Field(default=None, max_length=50)
    address: str | None = Field(default=None, max_length=500)
    storage_fee_reference: Decimal = Field(default=Decimal("0"), ge=0, max_digits=20, decimal_places=4)
    transport_fee_reference: Decimal = Field(default=Decimal("0"), ge=0, max_digits=20, decimal_places=4)
    sort: int = Field(default=0, ge=0)
    is_active: bool = True
    is_default: bool = False
    remark: str | None = Field(default=None, max_length=500)


class WarehouseUpdate(StrippedInputModel):
    code: str | None = Field(default=None, min_length=1, max_length=50)
    name: str | None = Field(default=None, min_length=1, max_length=100)
    contact_name: str | None = Field(default=None, max_length=100)
    contact_phone: str | None = Field(default=None, max_length=50)
    address: str | None = Field(default=None, max_length=500)
    storage_fee_reference: Decimal | None = Field(default=None, ge=0, max_digits=20, decimal_places=4)
    transport_fee_reference: Decimal | None = Field(default=None, ge=0, max_digits=20, decimal_places=4)
    sort: int | None = Field(default=None, ge=0)
    is_active: bool | None = None
    is_default: bool | None = None
    remark: str | None = Field(default=None, max_length=500)


class WarehousePublic(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    tenant_id: uuid.UUID
    code: str
    name: str
    contact_name: str | None = None
    contact_phone: str | None = None
    address: str | None = None
    storage_fee_reference: Decimal
    transport_fee_reference: Decimal
    sort: int
    is_active: bool
    is_default: bool
    remark: str | None = None
    created_at: datetime | None = None
    updated_at: datetime | None = None


class WarehouseUserGrantPublic(BaseModel):
    user_id: uuid.UUID
    full_name: str | None = None
    email: str


class WarehouseUserGrantsPublic(BaseModel):
    items: list[WarehouseUserGrantPublic]


class WarehouseUserGrantsReplace(BaseModel):
    user_ids: list[uuid.UUID] = Field(default_factory=list, max_length=500)


class ProductUnitsPublic(BaseModel):
    items: list[ProductUnitPublic]
    total: int
    page: int
    page_size: int


class ProductCategoriesPublic(BaseModel):
    items: list[ProductCategoryPublic]
    total: int
    page: int
    page_size: int


class ProductsPublic(BaseModel):
    items: list[ProductPublic]
    total: int
    page: int
    page_size: int


class WarehousesPublic(BaseModel):
    items: list[WarehousePublic]
    total: int
    page: int
    page_size: int


class CounterpartyCreate(BaseModel):
    name: str = Field(min_length=1, max_length=200)
    contact_name: str | None = Field(default=None, max_length=100)
    mobile: str | None = Field(default=None, max_length=50)
    phone: str | None = Field(default=None, max_length=50)
    email: str | None = Field(default=None, max_length=320)
    fax: str | None = Field(default=None, max_length=50)
    tax_no: str | None = Field(default=None, max_length=100)
    tax_rate: Decimal = Field(default=Decimal("0"), ge=0, le=100, max_digits=7, decimal_places=4)
    bank_name: str | None = Field(default=None, max_length=200)
    bank_account: str | None = Field(default=None, min_length=1, max_length=500)
    address: str | None = Field(default=None, max_length=500)
    sort: int = Field(default=0, ge=0)
    is_active: bool = True
    remark: str | None = Field(default=None, max_length=500)


class CounterpartyUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=200)
    contact_name: str | None = Field(default=None, max_length=100)
    mobile: str | None = Field(default=None, max_length=50)
    phone: str | None = Field(default=None, max_length=50)
    email: str | None = Field(default=None, max_length=320)
    fax: str | None = Field(default=None, max_length=50)
    tax_no: str | None = Field(default=None, max_length=100)
    tax_rate: Decimal | None = Field(default=None, ge=0, le=100, max_digits=7, decimal_places=4)
    bank_name: str | None = Field(default=None, max_length=200)
    bank_account: str | None = Field(default=None, min_length=1, max_length=500)
    address: str | None = Field(default=None, max_length=500)
    sort: int | None = Field(default=None, ge=0)
    is_active: bool | None = None
    remark: str | None = Field(default=None, max_length=500)


class CounterpartyPublic(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    tenant_id: uuid.UUID
    name: str
    contact_name: str | None = None
    mobile: str | None = None
    phone: str | None = None
    email: str | None = None
    fax: str | None = None
    tax_no: str | None = None
    tax_rate: Decimal
    bank_name: str | None = None
    bank_account_masked: str | None = None
    address: str | None = None
    sort: int
    is_active: bool
    remark: str | None = None
    created_at: datetime | None = None
    updated_at: datetime | None = None


class SuppliersPublic(BaseModel):
    items: list[CounterpartyPublic]
    total: int
    page: int
    page_size: int


class CustomersPublic(BaseModel):
    items: list[CounterpartyPublic]
    total: int
    page: int
    page_size: int


class CounterpartySensitivePublic(BaseModel):
    id: uuid.UUID
    bank_account: str


class SettlementAccountCreate(BaseModel):
    name: str = Field(min_length=1, max_length=200)
    account_no: str = Field(min_length=1, max_length=500)
    sort: int = Field(default=0, ge=0)
    is_active: bool = True
    is_default: bool = False
    remark: str | None = Field(default=None, max_length=500)


class SettlementAccountUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=200)
    account_no: str | None = Field(default=None, min_length=1, max_length=500)
    sort: int | None = Field(default=None, ge=0)
    is_active: bool | None = None
    is_default: bool | None = None
    remark: str | None = Field(default=None, max_length=500)


class SettlementAccountPublic(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    name: str
    account_no_masked: str
    sort: int
    is_active: bool
    is_default: bool
    remark: str | None = None
    created_at: datetime | None = None
    updated_at: datetime | None = None


class SettlementAccountSensitivePublic(BaseModel):
    id: uuid.UUID
    account_no: str


class SettlementAccountsPublic(BaseModel):
    items: list[SettlementAccountPublic]
    total: int
    page: int
    page_size: int


class DocumentActionLogPublic(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    resource_type: str
    resource_id: uuid.UUID
    resource_no: str | None = None
    action: str
    old_status: str | None = None
    new_status: str | None = None
    old_version: int | None = None
    new_version: int | None = None
    actor_id: uuid.UUID
    reason: str | None = None
    metadata_json: dict[str, object]
    occurred_at: datetime


class DocumentActionLogsPublic(BaseModel):
    items: list[DocumentActionLogPublic]
    total: int
    page: int
    page_size: int


class DocumentAttachmentCreate(BaseModel):
    file_id: uuid.UUID
    sort: int = Field(default=0, ge=0)


class DocumentAttachmentPublic(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    file_id: uuid.UUID
    file_name: str
    content_type: str | None = None
    size: int
    sort: int
    created_at: datetime


class DocumentAttachmentsPublic(BaseModel):
    items: list[DocumentAttachmentPublic]


class SettlementLineCreate(BaseModel):
    source_type: str
    source_document_id: uuid.UUID
    settlement_amount: Decimal = Field(gt=0, max_digits=20, decimal_places=4)
    remark: str | None = Field(default=None, max_length=500)


class FinancePaymentCreate(BaseModel):
    supplier_id: uuid.UUID
    settlement_account_id: uuid.UUID
    business_at: datetime | None = None
    discount_amount: Decimal = Field(default=Decimal("0"), ge=0, max_digits=20, decimal_places=4)
    remark: str | None = Field(default=None, max_length=500)
    items: list[SettlementLineCreate] = Field(min_length=1, max_length=500)


class FinancePaymentUpdate(FinancePaymentCreate):
    expected_version: int = Field(ge=1)


class FinanceReceiptCreate(BaseModel):
    customer_id: uuid.UUID
    settlement_account_id: uuid.UUID
    business_at: datetime | None = None
    discount_amount: Decimal = Field(default=Decimal("0"), ge=0, max_digits=20, decimal_places=4)
    remark: str | None = Field(default=None, max_length=500)
    items: list[SettlementLineCreate] = Field(min_length=1, max_length=500)


class FinanceReceiptUpdate(FinanceReceiptCreate):
    expected_version: int = Field(ge=1)


class FinancePaymentItemPublic(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    source_type: str
    source_document_id: uuid.UUID
    source_document_no: str
    source_total_signed: Decimal
    settled_before_signed: Decimal
    settlement_signed: Decimal
    discount_allocated: Decimal
    remark: str | None = None


class FinanceReceiptItemPublic(FinancePaymentItemPublic):
    pass


class FinancePaymentPublic(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    no: str
    supplier_id: uuid.UUID
    supplier_name: str
    settlement_account_id: uuid.UUID
    status: str
    version: int
    business_at: datetime
    owner_id: uuid.UUID
    total_settlement_amount: Decimal
    discount_amount: Decimal
    payment_amount: Decimal
    remark: str | None = None
    approved_at: datetime | None = None
    reversed_at: datetime | None = None
    items: list[FinancePaymentItemPublic] = []


class FinanceReceiptPublic(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    no: str
    customer_id: uuid.UUID
    customer_name: str
    settlement_account_id: uuid.UUID
    status: str
    version: int
    business_at: datetime
    owner_id: uuid.UUID
    total_settlement_amount: Decimal
    discount_amount: Decimal
    receipt_amount: Decimal
    remark: str | None = None
    approved_at: datetime | None = None
    reversed_at: datetime | None = None
    items: list[FinanceReceiptItemPublic] = []


class FinancePaymentsPublic(BaseModel):
    items: list[FinancePaymentPublic]
    total: int
    page: int
    page_size: int


class FinanceReceiptsPublic(BaseModel):
    items: list[FinanceReceiptPublic]
    total: int
    page: int
    page_size: int


class PurchaseOrderLineCreate(BaseModel):
    product_id: uuid.UUID
    quantity: Decimal = Field(gt=0, max_digits=20, decimal_places=6)
    unit_price: Decimal = Field(ge=0, max_digits=20, decimal_places=4)
    tax_rate: Decimal = Field(default=Decimal("0"), ge=0, le=100, max_digits=7, decimal_places=4)
    remark: str | None = Field(default=None, max_length=500)


class PurchaseOrderCreate(BaseModel):
    supplier_id: uuid.UUID
    settlement_account_id: uuid.UUID | None = None
    business_at: datetime | None = None
    discount_rate: Decimal = Field(default=Decimal("0"), ge=0, le=100, max_digits=7, decimal_places=4)
    discount_amount: Decimal | None = Field(default=None, ge=0, max_digits=20, decimal_places=4)
    deposit_amount: Decimal = Field(default=Decimal("0"), ge=0, max_digits=20, decimal_places=4)
    remark: str | None = Field(default=None, max_length=500)
    items: list[PurchaseOrderLineCreate] = Field(min_length=1, max_length=500)


class PurchaseOrderUpdate(PurchaseOrderCreate):
    expected_version: int = Field(ge=1)


class PurchaseOrderItemPublic(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    purchase_order_id: uuid.UUID
    line_no: int
    product_id: uuid.UUID
    unit_id: uuid.UUID
    product_name: str
    product_barcode: str | None = None
    unit_name: str
    quantity: Decimal
    unit_price: Decimal
    product_amount: Decimal
    tax_rate: Decimal
    tax_amount: Decimal
    total_amount: Decimal
    received_quantity: Decimal
    returned_quantity: Decimal
    remark: str | None = None


class PurchaseOrderPublic(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    no: str
    supplier_id: uuid.UUID
    supplier_name: str
    settlement_account_id: uuid.UUID | None = None
    status: str
    version: int
    business_at: datetime
    owner_id: uuid.UUID
    total_quantity: Decimal
    product_amount: Decimal
    tax_amount: Decimal
    discount_rate: Decimal
    discount_amount: Decimal
    deposit_amount: Decimal
    total_amount: Decimal
    remark: str | None = None
    approved_at: datetime | None = None
    reversed_at: datetime | None = None
    items: list[PurchaseOrderItemPublic] = []


class PurchaseOrdersPublic(BaseModel):
    items: list[PurchaseOrderPublic]
    total: int
    page: int
    page_size: int


class PurchaseInLineCreate(BaseModel):
    purchase_order_item_id: uuid.UUID
    warehouse_id: uuid.UUID
    quantity: Decimal = Field(gt=0, max_digits=20, decimal_places=6)
    remark: str | None = Field(default=None, max_length=500)


class PurchaseInCreate(BaseModel):
    purchase_order_id: uuid.UUID
    settlement_account_id: uuid.UUID | None = None
    business_at: datetime | None = None
    discount_rate: Decimal = Field(default=Decimal("0"), ge=0, le=100, max_digits=7, decimal_places=4)
    discount_amount: Decimal | None = Field(default=None, ge=0, max_digits=20, decimal_places=4)
    other_fee: Decimal = Field(default=Decimal("0"), ge=0, max_digits=20, decimal_places=4)
    remark: str | None = Field(default=None, max_length=500)
    items: list[PurchaseInLineCreate] = Field(min_length=1, max_length=500)


class PurchaseInUpdate(PurchaseInCreate):
    expected_version: int = Field(ge=1)


class PurchaseInItemPublic(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    purchase_in_id: uuid.UUID
    purchase_order_item_id: uuid.UUID
    line_no: int
    product_id: uuid.UUID
    warehouse_id: uuid.UUID
    product_name: str
    unit_name: str
    quantity: Decimal
    reference_price: Decimal
    tax_rate: Decimal
    product_amount: Decimal
    tax_amount: Decimal
    total_amount: Decimal
    returned_quantity: Decimal
    remark: str | None = None


class PurchaseInPublic(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    no: str
    purchase_order_id: uuid.UUID
    purchase_order_no: str
    supplier_id: uuid.UUID
    supplier_name: str
    settlement_account_id: uuid.UUID | None = None
    status: str
    version: int
    business_at: datetime
    owner_id: uuid.UUID
    total_quantity: Decimal
    product_amount: Decimal
    tax_amount: Decimal
    discount_rate: Decimal
    discount_amount: Decimal
    other_fee: Decimal
    total_amount: Decimal
    settled_amount: Decimal
    remark: str | None = None
    approved_at: datetime | None = None
    reversed_at: datetime | None = None
    items: list[PurchaseInItemPublic] = []


class PurchaseInsPublic(BaseModel):
    items: list[PurchaseInPublic]
    total: int
    page: int
    page_size: int


class PurchaseReturnLineCreate(BaseModel):
    purchase_in_item_id: uuid.UUID
    quantity: Decimal = Field(gt=0, max_digits=20, decimal_places=6)
    remark: str | None = Field(default=None, max_length=500)


class PurchaseReturnCreate(BaseModel):
    purchase_in_id: uuid.UUID
    settlement_account_id: uuid.UUID | None = None
    business_at: datetime | None = None
    discount_rate: Decimal = Field(default=Decimal("0"), ge=0, le=100, max_digits=7, decimal_places=4)
    discount_amount: Decimal | None = Field(default=None, ge=0, max_digits=20, decimal_places=4)
    other_fee: Decimal = Field(default=Decimal("0"), ge=0, max_digits=20, decimal_places=4)
    remark: str | None = Field(default=None, max_length=500)
    items: list[PurchaseReturnLineCreate] = Field(min_length=1, max_length=500)


class PurchaseReturnUpdate(PurchaseReturnCreate):
    expected_version: int = Field(ge=1)


class PurchaseReturnItemPublic(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    purchase_return_id: uuid.UUID
    purchase_in_item_id: uuid.UUID
    purchase_order_item_id: uuid.UUID
    line_no: int
    product_id: uuid.UUID
    warehouse_id: uuid.UUID
    product_name: str
    unit_name: str
    quantity: Decimal
    reference_price: Decimal
    tax_rate: Decimal
    product_amount: Decimal
    tax_amount: Decimal
    total_amount: Decimal
    remark: str | None = None


class PurchaseReturnPublic(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    no: str
    purchase_in_id: uuid.UUID
    purchase_in_no: str
    purchase_order_id: uuid.UUID
    supplier_id: uuid.UUID
    supplier_name: str
    settlement_account_id: uuid.UUID | None = None
    status: str
    version: int
    business_at: datetime
    owner_id: uuid.UUID
    total_quantity: Decimal
    product_amount: Decimal
    tax_amount: Decimal
    discount_rate: Decimal
    discount_amount: Decimal
    other_fee: Decimal
    total_amount: Decimal
    settled_amount: Decimal
    remark: str | None = None
    approved_at: datetime | None = None
    reversed_at: datetime | None = None
    items: list[PurchaseReturnItemPublic] = []


class PurchaseReturnsPublic(BaseModel):
    items: list[PurchaseReturnPublic]
    total: int
    page: int
    page_size: int


class SaleOrderLineCreate(PurchaseOrderLineCreate):
    pass


class SaleOrderCreate(BaseModel):
    customer_id: uuid.UUID
    settlement_account_id: uuid.UUID | None = None
    business_at: datetime | None = None
    discount_rate: Decimal = Field(default=Decimal("0"), ge=0, le=100, max_digits=7, decimal_places=4)
    discount_amount: Decimal | None = Field(default=None, ge=0, max_digits=20, decimal_places=4)
    deposit_amount: Decimal = Field(default=Decimal("0"), ge=0, max_digits=20, decimal_places=4)
    remark: str | None = Field(default=None, max_length=500)
    items: list[SaleOrderLineCreate] = Field(min_length=1, max_length=500)


class SaleOrderUpdate(SaleOrderCreate):
    expected_version: int = Field(ge=1)


class SaleOrderItemPublic(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    sale_order_id: uuid.UUID
    line_no: int
    product_id: uuid.UUID
    unit_id: uuid.UUID
    product_name: str
    product_barcode: str | None = None
    unit_name: str
    quantity: Decimal
    unit_price: Decimal
    product_amount: Decimal
    tax_rate: Decimal
    tax_amount: Decimal
    total_amount: Decimal
    shipped_quantity: Decimal
    returned_quantity: Decimal
    remark: str | None = None


class SaleOrderPublic(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    no: str
    customer_id: uuid.UUID
    customer_name: str
    settlement_account_id: uuid.UUID | None = None
    status: str
    version: int
    business_at: datetime
    owner_id: uuid.UUID
    total_quantity: Decimal
    product_amount: Decimal
    tax_amount: Decimal
    discount_rate: Decimal
    discount_amount: Decimal
    deposit_amount: Decimal
    total_amount: Decimal
    remark: str | None = None
    approved_at: datetime | None = None
    reversed_at: datetime | None = None
    items: list[SaleOrderItemPublic] = []


class SaleOrdersPublic(BaseModel):
    items: list[SaleOrderPublic]
    total: int
    page: int
    page_size: int


class SaleOutLineCreate(BaseModel):
    sale_order_item_id: uuid.UUID
    warehouse_id: uuid.UUID
    quantity: Decimal = Field(gt=0, max_digits=20, decimal_places=6)
    remark: str | None = Field(default=None, max_length=500)


class SaleOutCreate(BaseModel):
    sale_order_id: uuid.UUID
    settlement_account_id: uuid.UUID | None = None
    business_at: datetime | None = None
    discount_rate: Decimal = Field(default=Decimal("0"), ge=0, le=100, max_digits=7, decimal_places=4)
    discount_amount: Decimal | None = Field(default=None, ge=0, max_digits=20, decimal_places=4)
    other_deduction: Decimal = Field(default=Decimal("0"), ge=0, max_digits=20, decimal_places=4)
    remark: str | None = Field(default=None, max_length=500)
    items: list[SaleOutLineCreate] = Field(min_length=1, max_length=500)


class SaleOutUpdate(SaleOutCreate):
    expected_version: int = Field(ge=1)


class SaleOutItemPublic(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    sale_out_id: uuid.UUID
    sale_order_item_id: uuid.UUID
    line_no: int
    product_id: uuid.UUID
    warehouse_id: uuid.UUID
    product_name: str
    unit_name: str
    quantity: Decimal
    reference_price: Decimal
    tax_rate: Decimal
    product_amount: Decimal
    tax_amount: Decimal
    total_amount: Decimal
    returned_quantity: Decimal
    remark: str | None = None


class SaleOutPublic(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    no: str
    sale_order_id: uuid.UUID
    sale_order_no: str
    customer_id: uuid.UUID
    customer_name: str
    settlement_account_id: uuid.UUID | None = None
    status: str
    version: int
    business_at: datetime
    owner_id: uuid.UUID
    total_quantity: Decimal
    product_amount: Decimal
    tax_amount: Decimal
    discount_rate: Decimal
    discount_amount: Decimal
    other_deduction: Decimal
    total_amount: Decimal
    settled_amount: Decimal
    remark: str | None = None
    approved_at: datetime | None = None
    reversed_at: datetime | None = None
    items: list[SaleOutItemPublic] = []


class SaleOutsPublic(BaseModel):
    items: list[SaleOutPublic]
    total: int
    page: int
    page_size: int


class SaleReturnLineCreate(BaseModel):
    sale_out_item_id: uuid.UUID
    quantity: Decimal = Field(gt=0, max_digits=20, decimal_places=6)
    remark: str | None = Field(default=None, max_length=500)


class SaleReturnCreate(BaseModel):
    sale_out_id: uuid.UUID
    settlement_account_id: uuid.UUID | None = None
    business_at: datetime | None = None
    discount_rate: Decimal = Field(default=Decimal("0"), ge=0, le=100, max_digits=7, decimal_places=4)
    discount_amount: Decimal | None = Field(default=None, ge=0, max_digits=20, decimal_places=4)
    other_deduction: Decimal = Field(default=Decimal("0"), ge=0, max_digits=20, decimal_places=4)
    remark: str | None = Field(default=None, max_length=500)
    items: list[SaleReturnLineCreate] = Field(min_length=1, max_length=500)


class SaleReturnUpdate(SaleReturnCreate):
    expected_version: int = Field(ge=1)


class SaleReturnItemPublic(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    sale_return_id: uuid.UUID
    sale_out_item_id: uuid.UUID
    sale_order_item_id: uuid.UUID
    line_no: int
    product_id: uuid.UUID
    warehouse_id: uuid.UUID
    product_name: str
    unit_name: str
    quantity: Decimal
    reference_price: Decimal
    tax_rate: Decimal
    product_amount: Decimal
    tax_amount: Decimal
    total_amount: Decimal
    remark: str | None = None


class SaleReturnPublic(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    no: str
    sale_out_id: uuid.UUID
    sale_out_no: str
    sale_order_id: uuid.UUID
    customer_id: uuid.UUID
    customer_name: str
    settlement_account_id: uuid.UUID | None = None
    status: str
    version: int
    business_at: datetime
    owner_id: uuid.UUID
    total_quantity: Decimal
    product_amount: Decimal
    tax_amount: Decimal
    discount_rate: Decimal
    discount_amount: Decimal
    other_deduction: Decimal
    total_amount: Decimal
    settled_amount: Decimal
    remark: str | None = None
    approved_at: datetime | None = None
    reversed_at: datetime | None = None
    items: list[SaleReturnItemPublic] = []


class SaleReturnsPublic(BaseModel):
    items: list[SaleReturnPublic]
    total: int
    page: int
    page_size: int


class StockDocumentItemCreate(BaseModel):
    product_id: uuid.UUID
    warehouse_id: uuid.UUID
    quantity: Decimal = Field(gt=0, max_digits=20, decimal_places=6)
    reference_price: Decimal = Field(
        default=Decimal("0"), ge=0, max_digits=20, decimal_places=4
    )
    remark: str | None = Field(default=None, max_length=500)


class StockInCreate(BaseModel):
    business_at: datetime | None = None
    supplier_id: uuid.UUID | None = None
    remark: str | None = Field(default=None, max_length=500)
    items: list[StockDocumentItemCreate] = Field(min_length=1, max_length=500)


class StockInUpdate(StockInCreate):
    expected_version: int = Field(ge=1)


class StockOutCreate(BaseModel):
    business_at: datetime | None = None
    customer_id: uuid.UUID | None = None
    remark: str | None = Field(default=None, max_length=500)
    items: list[StockDocumentItemCreate] = Field(min_length=1, max_length=500)


class StockOutUpdate(StockOutCreate):
    expected_version: int = Field(ge=1)


class StockMoveItemCreate(BaseModel):
    product_id: uuid.UUID
    from_warehouse_id: uuid.UUID
    to_warehouse_id: uuid.UUID
    quantity: Decimal = Field(gt=0, max_digits=20, decimal_places=6)
    reference_price: Decimal = Field(
        default=Decimal("0"), ge=0, max_digits=20, decimal_places=4
    )
    remark: str | None = Field(default=None, max_length=500)


class StockMoveCreate(BaseModel):
    business_at: datetime | None = None
    remark: str | None = Field(default=None, max_length=500)
    items: list[StockMoveItemCreate] = Field(min_length=1, max_length=500)


class StockMoveUpdate(StockMoveCreate):
    expected_version: int = Field(ge=1)


class StockCheckItemCreate(BaseModel):
    product_id: uuid.UUID
    warehouse_id: uuid.UUID
    actual_quantity: Decimal = Field(ge=0, max_digits=20, decimal_places=6)
    reference_price: Decimal = Field(default=Decimal("0"), ge=0, max_digits=20, decimal_places=4)
    remark: str | None = Field(default=None, max_length=500)


class StockCheckCreate(BaseModel):
    business_at: datetime | None = None
    remark: str | None = Field(default=None, max_length=500)
    items: list[StockCheckItemCreate] = Field(min_length=1, max_length=500)


class StockCheckUpdate(StockCheckCreate):
    expected_version: int = Field(ge=1)


class DocumentCommand(BaseModel):
    expected_version: int = Field(ge=1)


class DocumentReverseCommand(DocumentCommand):
    reason: str = Field(min_length=1, max_length=500)


class StockInItemPublic(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    stock_in_id: uuid.UUID
    line_no: int
    product_id: uuid.UUID
    warehouse_id: uuid.UUID
    quantity: Decimal
    reference_price: Decimal
    remark: str | None = None


class StockOutItemPublic(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    stock_out_id: uuid.UUID
    line_no: int
    product_id: uuid.UUID
    warehouse_id: uuid.UUID
    quantity: Decimal
    reference_price: Decimal
    remark: str | None = None


class StockInPublic(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    no: str
    status: str
    version: int
    business_at: datetime
    owner_id: uuid.UUID
    supplier_id: uuid.UUID | None = None
    total_quantity: Decimal
    total_amount: Decimal
    remark: str | None = None
    approved_at: datetime | None = None
    reversed_at: datetime | None = None
    items: list[StockInItemPublic] = []


class StockOutPublic(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    no: str
    status: str
    version: int
    business_at: datetime
    owner_id: uuid.UUID
    customer_id: uuid.UUID | None = None
    total_quantity: Decimal
    total_amount: Decimal
    remark: str | None = None
    approved_at: datetime | None = None
    reversed_at: datetime | None = None
    items: list[StockOutItemPublic] = []


class StockInsPublic(BaseModel):
    items: list[StockInPublic]
    total: int
    page: int
    page_size: int


class StockOutsPublic(BaseModel):
    items: list[StockOutPublic]
    total: int
    page: int
    page_size: int


class StockMoveItemPublic(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    stock_move_id: uuid.UUID
    line_no: int
    product_id: uuid.UUID
    from_warehouse_id: uuid.UUID
    to_warehouse_id: uuid.UUID
    quantity: Decimal
    reference_price: Decimal
    remark: str | None = None


class StockMovePublic(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    no: str
    status: str
    version: int
    business_at: datetime
    owner_id: uuid.UUID
    total_quantity: Decimal
    total_amount: Decimal
    remark: str | None = None
    items: list[StockMoveItemPublic] = []


class StockMovesPublic(BaseModel):
    items: list[StockMovePublic]
    total: int
    page: int
    page_size: int


class StockCheckItemPublic(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    stock_check_id: uuid.UUID
    line_no: int
    product_id: uuid.UUID
    warehouse_id: uuid.UUID
    snapshot_quantity: Decimal
    actual_quantity: Decimal
    difference_quantity: Decimal
    reference_price: Decimal
    difference_amount: Decimal
    remark: str | None = None


class StockCheckPublic(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    no: str
    status: str
    version: int
    business_at: datetime
    owner_id: uuid.UUID
    total_quantity: Decimal
    total_amount: Decimal
    remark: str | None = None
    items: list[StockCheckItemPublic] = []


class StockChecksPublic(BaseModel):
    items: list[StockCheckPublic]
    total: int
    page: int
    page_size: int


class StockBalancePublic(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    product_id: uuid.UUID
    product_code: str
    product_name: str
    category_id: uuid.UUID | None = None
    unit_name: str
    warehouse_id: uuid.UUID
    warehouse_name: str
    quantity: Decimal
    version: int
    updated_at: datetime | None = None


class StockBalancesPublic(BaseModel):
    items: list[StockBalancePublic]
    total: int
    page: int
    page_size: int


class StockLedgerPublic(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    product_id: uuid.UUID
    product_code: str
    product_name: str
    category_id: uuid.UUID | None = None
    unit_name: str
    warehouse_id: uuid.UUID
    warehouse_name: str
    delta_quantity: Decimal
    balance_after: Decimal
    ledger_type: str
    source_document_type: str
    source_document_id: uuid.UUID
    source_item_id: uuid.UUID
    source_document_no: str
    source_version: int
    reversal_of_id: uuid.UUID | None = None
    operator_id: uuid.UUID
    operator_name: str
    occurred_at: datetime


class StockLedgersPublic(BaseModel):
    items: list[StockLedgerPublic]
    total: int
    page: int
    page_size: int


class StatisticsAmountsPublic(BaseModel):
    purchase_amount: Decimal
    sale_amount: Decimal


class StatisticsSummaryPublic(BaseModel):
    today: StatisticsAmountsPublic
    yesterday: StatisticsAmountsPublic
    month: StatisticsAmountsPublic
    year: StatisticsAmountsPublic


class StatisticsTimeSeriesPointPublic(BaseModel):
    period_start: datetime
    amount: Decimal


class StatisticsTimeSeriesPublic(BaseModel):
    type: str
    granularity: str
    items: list[StatisticsTimeSeriesPointPublic]


class ReconciliationRunPublic(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    status: str
    stock_difference_count: int
    settlement_difference_count: int
    summary_json: dict[str, object]
    started_at: datetime
    completed_at: datetime | None = None
    triggered_by: uuid.UUID | None = None
