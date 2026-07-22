"""Source-document settlement planning and atomic balance application."""

import uuid
from dataclasses import dataclass
from decimal import ROUND_HALF_UP, Decimal
from typing import Protocol

from sqlmodel import select

from app.modules.erp.infrastructure.models import (
    DocumentStatus,
    PurchaseIn,
    PurchaseReturn,
    SaleOut,
    SaleReturn,
    SettlementSourceType,
)
from app.modules.erp.infrastructure.tenant_uow import ErpTenantUnitOfWork
from app.modules.erp.observability import observe_settlement_conflict

_MONEY_QUANTUM = Decimal("0.0001")


class SettlementConflictError(RuntimeError):
    """Raised when settlement sources are unavailable or over-allocated."""

    def __init__(self, message: str, *, reason: str) -> None:
        super().__init__(message)
        observe_settlement_conflict(reason=reason)


class SettlementSource(Protocol):
    id: uuid.UUID
    no: str
    status: DocumentStatus
    total_amount: Decimal
    settled_amount: Decimal


@dataclass(frozen=True)
class SettlementLine:
    source_type: SettlementSourceType
    source_document_id: uuid.UUID
    settlement_amount: Decimal
    remark: str | None = None


@dataclass(frozen=True)
class PlannedSettlementLine:
    source_type: SettlementSourceType
    source_document_id: uuid.UUID
    source_document_no: str
    source_total_signed: Decimal
    settled_before_signed: Decimal
    settlement_signed: Decimal
    discount_allocated: Decimal
    remark: str | None


_SOURCE_MODELS = {
    SettlementSourceType.PURCHASE_IN: PurchaseIn,
    SettlementSourceType.PURCHASE_RETURN: PurchaseReturn,
    SettlementSourceType.SALE_OUT: SaleOut,
    SettlementSourceType.SALE_RETURN: SaleReturn,
}


def positive_source_types(*, flow: str) -> set[SettlementSourceType]:
    if flow == "payment":
        return {SettlementSourceType.PURCHASE_IN}
    if flow == "receipt":
        return {SettlementSourceType.SALE_OUT}
    raise ValueError(f"Unknown settlement flow: {flow}")


def allowed_source_types(*, flow: str) -> set[SettlementSourceType]:
    if flow == "payment":
        return {SettlementSourceType.PURCHASE_IN, SettlementSourceType.PURCHASE_RETURN}
    if flow == "receipt":
        return {SettlementSourceType.SALE_OUT, SettlementSourceType.SALE_RETURN}
    raise ValueError(f"Unknown settlement flow: {flow}")


def source_counterparty_id(source: SettlementSource, *, flow: str) -> uuid.UUID:
    return source.supplier_id if flow == "payment" else source.customer_id  # type: ignore[attr-defined]


class SettlementService:
    def __init__(self, uow: ErpTenantUnitOfWork) -> None:
        self._uow = uow

    def plan(
        self,
        *,
        flow: str,
        counterparty_id: uuid.UUID,
        lines: tuple[SettlementLine, ...],
        discount_amount: Decimal,
    ) -> tuple[tuple[PlannedSettlementLine, ...], Decimal, Decimal]:
        if not lines:
            raise SettlementConflictError(
                "Settlement document requires at least one line",
                reason="empty_document",
            )
        if discount_amount < 0:
            raise SettlementConflictError(
                "Settlement discount cannot be negative",
                reason="negative_discount",
            )
        allowed = allowed_source_types(flow=flow)
        seen: set[tuple[SettlementSourceType, uuid.UUID]] = set()
        source_by_key: dict[tuple[SettlementSourceType, uuid.UUID], SettlementSource] = {}
        for line in lines:
            key = (line.source_type, line.source_document_id)
            if line.source_type not in allowed or key in seen:
                raise SettlementConflictError(
                    "Settlement source is invalid or repeated",
                    reason="invalid_or_repeated_source",
                )
            seen.add(key)
            source_by_key[key] = self._load_source(
                source_type=line.source_type,
                source_document_id=line.source_document_id,
                lock=False,
            )

        positive_types = positive_source_types(flow=flow)
        signed_sum = sum(
            (
                line.settlement_amount
                if line.source_type in positive_types
                else -line.settlement_amount
                for line in lines
            ),
            Decimal("0"),
        )
        cash_amount = signed_sum - discount_amount
        if cash_amount < 0:
            raise SettlementConflictError(
                "Settlement net amount cannot be negative", reason="negative_cash_amount"
            )
        positive_total = sum(
            (line.settlement_amount for line in lines if line.source_type in positive_types),
            Decimal("0"),
        )
        if discount_amount > positive_total:
            raise SettlementConflictError(
                "Settlement discount exceeds positive sources",
                reason="discount_exceeds_positive_sources",
            )
        allocations = self._allocate_discount(
            lines=lines,
            discount_amount=discount_amount,
            positive_types=positive_types,
        )
        planned: list[PlannedSettlementLine] = []
        for line in lines:
            source = source_by_key[(line.source_type, line.source_document_id)]
            self._validate_source(
                source=source,
                flow=flow,
                counterparty_id=counterparty_id,
                settlement_amount=line.settlement_amount,
                discount_allocated=allocations[(line.source_type, line.source_document_id)],
                is_positive=line.source_type in positive_types,
            )
            sign = Decimal("1") if line.source_type in positive_types else Decimal("-1")
            planned.append(
                PlannedSettlementLine(
                    source_type=line.source_type,
                    source_document_id=source.id,
                    source_document_no=source.no,
                    source_total_signed=source.total_amount * sign,
                    settled_before_signed=source.settled_amount * sign,
                    settlement_signed=line.settlement_amount * sign,
                    discount_allocated=allocations[(line.source_type, line.source_document_id)],
                    remark=line.remark,
                )
            )
        return tuple(planned), signed_sum, cash_amount

    def apply(
        self,
        *,
        flow: str,
        counterparty_id: uuid.UUID,
        lines: tuple[PlannedSettlementLine, ...],
        reverse: bool = False,
    ) -> None:
        positive_types = positive_source_types(flow=flow)
        for line in sorted(lines, key=lambda item: (item.source_type.value, str(item.source_document_id))):
            source = self._load_source(
                source_type=line.source_type,
                source_document_id=line.source_document_id,
                lock=True,
            )
            if source.no != line.source_document_no:
                raise SettlementConflictError(
                    "Settlement source changed", reason="source_changed"
                )
            amount = abs(line.settlement_signed) + (
                line.discount_allocated if line.source_type in positive_types else Decimal("0")
            )
            if reverse:
                if source.settled_amount < amount:
                    raise SettlementConflictError(
                        "Settlement source balance is inconsistent",
                        reason="source_balance_inconsistent",
                    )
                source.settled_amount -= amount
            else:
                self._validate_source(
                    source=source,
                    flow=flow,
                    counterparty_id=counterparty_id,
                    settlement_amount=abs(line.settlement_signed),
                    discount_allocated=line.discount_allocated,
                    is_positive=line.source_type in positive_types,
                )
                source.settled_amount += amount
            self._uow.session.add(source)

    def _load_source(
        self,
        *,
        source_type: SettlementSourceType,
        source_document_id: uuid.UUID,
        lock: bool,
    ) -> SettlementSource:
        model = _SOURCE_MODELS[source_type]
        statement = select(model).where(model.id == source_document_id)
        if lock:
            statement = statement.with_for_update()
        source = self._uow.session.exec(statement).first()
        if source is None:
            raise SettlementConflictError(
                "Settlement source is unavailable", reason="source_unavailable"
            )
        return source

    @staticmethod
    def _validate_source(
        *,
        source: SettlementSource,
        flow: str,
        counterparty_id: uuid.UUID,
        settlement_amount: Decimal,
        discount_allocated: Decimal,
        is_positive: bool,
    ) -> None:
        if source.status != DocumentStatus.APPROVED:
            raise SettlementConflictError(
                "Settlement source must be approved", reason="source_not_approved"
            )
        if source_counterparty_id(source, flow=flow) != counterparty_id:
            raise SettlementConflictError(
                "Settlement sources must use the same counterparty",
                reason="counterparty_mismatch",
            )
        required = settlement_amount + (discount_allocated if is_positive else Decimal("0"))
        if required > source.total_amount - source.settled_amount:
            raise SettlementConflictError(
                "Settlement amount exceeds source balance",
                reason="amount_exceeds_source_balance",
            )

    @staticmethod
    def _allocate_discount(
        *,
        lines: tuple[SettlementLine, ...],
        discount_amount: Decimal,
        positive_types: set[SettlementSourceType],
    ) -> dict[tuple[SettlementSourceType, uuid.UUID], Decimal]:
        allocations = {(line.source_type, line.source_document_id): Decimal("0") for line in lines}
        positives = sorted(
            (line for line in lines if line.source_type in positive_types),
            key=lambda line: str(line.source_document_id),
        )
        if not positives or discount_amount == 0:
            return allocations
        positive_total = sum((line.settlement_amount for line in positives), Decimal("0"))
        remaining = discount_amount
        for index, line in enumerate(positives):
            key = (line.source_type, line.source_document_id)
            if index == len(positives) - 1:
                allocations[key] = remaining
            else:
                allocation = (discount_amount * line.settlement_amount / positive_total).quantize(
                    _MONEY_QUANTUM, rounding=ROUND_HALF_UP
                )
                allocations[key] = allocation
                remaining -= allocation
        return allocations
