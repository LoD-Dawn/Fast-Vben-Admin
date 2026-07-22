"""Deterministic calculations for trade-document amount snapshots."""

from collections.abc import Iterable
from dataclasses import dataclass
from decimal import ROUND_HALF_UP, Decimal

MONEY_QUANTUM = Decimal("0.0001")
QUANTITY_QUANTUM = Decimal("0.000001")


class TradeDocumentAmountError(ValueError):
    pass


@dataclass(frozen=True)
class TradeDocumentLineAmount:
    quantity: Decimal
    reference_price: Decimal
    tax_rate: Decimal
    product_amount: Decimal
    tax_amount: Decimal
    total_amount: Decimal


@dataclass(frozen=True)
class TradeDocumentAmount:
    total_quantity: Decimal
    product_amount: Decimal
    tax_amount: Decimal
    discount_amount: Decimal
    total_amount: Decimal
    lines: tuple[TradeDocumentLineAmount, ...]


def calculate_trade_document_amounts(
    *,
    lines: Iterable[tuple[Decimal, Decimal, Decimal]],
    discount_rate: Decimal,
    discount_amount: Decimal | None,
    adjustment: Decimal,
    adjustment_sign: int,
) -> TradeDocumentAmount:
    calculated_lines = tuple(
        _line_amount(quantity=quantity, reference_price=reference_price, tax_rate=tax_rate)
        for quantity, reference_price, tax_rate in lines
    )
    product_amount = sum((line.product_amount for line in calculated_lines), Decimal("0"))
    tax_amount = sum((line.tax_amount for line in calculated_lines), Decimal("0"))
    gross_amount = product_amount + tax_amount
    rate_discount = (gross_amount * discount_rate / Decimal("100")).quantize(
        MONEY_QUANTUM, rounding=ROUND_HALF_UP
    )
    applied_discount = discount_amount if discount_amount is not None else rate_discount
    if applied_discount > gross_amount:
        raise TradeDocumentAmountError("Discount exceeds document amount")
    total_amount = (gross_amount - applied_discount + adjustment_sign * adjustment).quantize(
        MONEY_QUANTUM, rounding=ROUND_HALF_UP
    )
    if total_amount < 0:
        raise TradeDocumentAmountError("Document total amount cannot be negative")
    return TradeDocumentAmount(
        total_quantity=sum((line.quantity for line in calculated_lines), Decimal("0")),
        product_amount=product_amount,
        tax_amount=tax_amount,
        discount_amount=applied_discount,
        total_amount=total_amount,
        lines=calculated_lines,
    )


def _line_amount(*, quantity: Decimal, reference_price: Decimal, tax_rate: Decimal) -> TradeDocumentLineAmount:
    normalized_quantity = quantity.quantize(QUANTITY_QUANTUM, rounding=ROUND_HALF_UP)
    product_amount = (normalized_quantity * reference_price).quantize(
        MONEY_QUANTUM, rounding=ROUND_HALF_UP
    )
    tax_amount = (product_amount * tax_rate / Decimal("100")).quantize(
        MONEY_QUANTUM, rounding=ROUND_HALF_UP
    )
    return TradeDocumentLineAmount(
        quantity=normalized_quantity,
        reference_price=reference_price,
        tax_rate=tax_rate,
        product_amount=product_amount,
        tax_amount=tax_amount,
        total_amount=product_amount + tax_amount,
    )
