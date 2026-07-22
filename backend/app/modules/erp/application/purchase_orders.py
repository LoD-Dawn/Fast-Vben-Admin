"""Purchase-order amount calculation and reference validation."""

from dataclasses import dataclass
from decimal import ROUND_HALF_UP, Decimal

from sqlmodel import select

from app.modules.erp.infrastructure.models import Product, ProductUnit, Supplier
from app.modules.erp.infrastructure.tenant_uow import ErpTenantUnitOfWork
from app.modules.erp.public_api.dto import PurchaseOrderCreate

MONEY_QUANTUM = Decimal("0.0001")
QUANTITY_QUANTUM = Decimal("0.000001")


class PurchaseOrderConflictError(RuntimeError):
    pass


@dataclass(frozen=True)
class PurchaseOrderLineCalculated:
    product: Product
    unit: ProductUnit
    quantity: Decimal
    unit_price: Decimal
    product_amount: Decimal
    tax_rate: Decimal
    tax_amount: Decimal
    total_amount: Decimal
    remark: str | None


@dataclass(frozen=True)
class PurchaseOrderCalculated:
    supplier: Supplier
    lines: tuple[PurchaseOrderLineCalculated, ...]
    total_quantity: Decimal
    product_amount: Decimal
    tax_amount: Decimal
    discount_amount: Decimal
    total_amount: Decimal


def calculate_purchase_order(
    *, uow: ErpTenantUnitOfWork, command: PurchaseOrderCreate
) -> PurchaseOrderCalculated:
    supplier = uow.session.get(Supplier, command.supplier_id)
    if supplier is None or not supplier.is_active:
        raise PurchaseOrderConflictError("Supplier is unavailable")
    product_ids = {line.product_id for line in command.items}
    products = {
        product.id: product
        for product in uow.session.exec(select(Product).where(Product.id.in_(product_ids))).all()
    }
    unit_ids = {product.unit_id for product in products.values()}
    units = {
        unit.id: unit
        for unit in uow.session.exec(select(ProductUnit).where(ProductUnit.id.in_(unit_ids))).all()
    }
    lines: list[PurchaseOrderLineCalculated] = []
    for line in command.items:
        product = products.get(line.product_id)
        if product is None or not product.is_active:
            raise PurchaseOrderConflictError("Product is unavailable")
        unit = units.get(product.unit_id)
        if unit is None or not unit.is_active:
            raise PurchaseOrderConflictError("Product unit is unavailable")
        quantity = line.quantity.quantize(QUANTITY_QUANTUM, rounding=ROUND_HALF_UP)
        product_amount = (quantity * line.unit_price).quantize(MONEY_QUANTUM, rounding=ROUND_HALF_UP)
        tax_amount = (product_amount * line.tax_rate / Decimal("100")).quantize(MONEY_QUANTUM, rounding=ROUND_HALF_UP)
        lines.append(PurchaseOrderLineCalculated(product, unit, quantity, line.unit_price, product_amount, line.tax_rate, tax_amount, product_amount + tax_amount, line.remark))
    product_amount = sum((line.product_amount for line in lines), Decimal("0"))
    tax_amount = sum((line.tax_amount for line in lines), Decimal("0"))
    gross_amount = product_amount + tax_amount
    rate_discount = (gross_amount * command.discount_rate / Decimal("100")).quantize(MONEY_QUANTUM, rounding=ROUND_HALF_UP)
    discount_amount = command.discount_amount if command.discount_amount is not None else rate_discount
    if discount_amount > gross_amount:
        raise PurchaseOrderConflictError("Discount exceeds order amount")
    return PurchaseOrderCalculated(
        supplier=supplier,
        lines=tuple(lines),
        total_quantity=sum((line.quantity for line in lines), Decimal("0")),
        product_amount=product_amount,
        tax_amount=tax_amount,
        discount_amount=discount_amount,
        total_amount=gross_amount - discount_amount,
    )
