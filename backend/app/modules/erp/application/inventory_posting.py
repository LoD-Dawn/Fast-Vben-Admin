"""Transactional inventory posting with balance and ledger invariants."""

import uuid
from dataclasses import dataclass
from decimal import Decimal

from sqlalchemy.dialects.postgresql import insert
from sqlmodel import select

from app.core.clock import get_datetime_utc
from app.modules.erp.infrastructure.models import (
    Product,
    StockBalance,
    StockLedger,
    StockLedgerType,
    Warehouse,
)
from app.modules.erp.infrastructure.tenant_uow import ErpTenantUnitOfWork
from app.modules.erp.observability import observe_stock_conflict
from app.modules.erp.public_api.events import StockChangedV1
from app.modules.outbox import enqueue_event


class InventoryConflictError(RuntimeError):
    """Raised when an inventory command would violate a stock invariant."""

    def __init__(self, message: str, *, reason: str) -> None:
        super().__init__(message)
        observe_stock_conflict(reason=reason)


@dataclass(frozen=True)
class InventoryEffect:
    product_id: uuid.UUID
    warehouse_id: uuid.UUID
    delta_quantity: Decimal
    ledger_type: StockLedgerType
    source_document_type: str
    source_document_id: uuid.UUID
    source_item_id: uuid.UUID
    source_document_no: str
    source_version: int
    reversal_of_id: uuid.UUID | None = None


class InventoryPostingService:
    """The only ERP application service allowed to mutate stock balances."""

    def __init__(self, uow: ErpTenantUnitOfWork) -> None:
        self._uow = uow

    def post(
        self,
        *,
        effects: tuple[InventoryEffect, ...],
        operator_id: uuid.UUID,
        require_active_references: bool = True,
        expected_quantities: dict[tuple[uuid.UUID, uuid.UUID], Decimal] | None = None,
    ) -> None:
        expected_quantities = expected_quantities or {}
        if not effects and not expected_quantities:
            raise InventoryConflictError(
                "Inventory document requires at least one line",
                reason="empty_document",
            )
        self._validate_effects(effects)
        keys = {(effect.product_id, effect.warehouse_id) for effect in effects} | set(
            expected_quantities
        )
        if require_active_references:
            self._validate_active_references(keys)
        balances = self._lock_balances(keys=keys)
        for key, expected_quantity in expected_quantities.items():
            if balances[key].quantity != expected_quantity:
                raise InventoryConflictError(
                    "Stock snapshot is stale", reason="snapshot_stale"
                )

        for effect in effects:
            balance = balances[(effect.product_id, effect.warehouse_id)]
            next_quantity = balance.quantity + effect.delta_quantity
            if next_quantity < Decimal("0"):
                raise InventoryConflictError(
                    "Stock is insufficient", reason="insufficient_stock"
                )
            balance.quantity = next_quantity
            balance.version += 1
            balance.updated_at = get_datetime_utc()
            self._uow.session.add(balance)
            ledger = StockLedger(
                tenant_id=self._uow.tenant_id,
                product_id=effect.product_id,
                warehouse_id=effect.warehouse_id,
                delta_quantity=effect.delta_quantity,
                balance_after=next_quantity,
                ledger_type=effect.ledger_type,
                source_document_type=effect.source_document_type,
                source_document_id=effect.source_document_id,
                source_item_id=effect.source_item_id,
                source_document_no=effect.source_document_no,
                source_version=effect.source_version,
                reversal_of_id=effect.reversal_of_id,
                operator_id=operator_id,
            )
            self._uow.session.add(ledger)
            self._uow.session.flush()
            enqueue_event(
                session=self._uow.session,
                module_code="erp",
                event_type="erp.stock.changed",
                tenant_id=self._uow.tenant_id,
                aggregate_id=f"{effect.product_id}:{effect.warehouse_id}",
                aggregate_sequence=balance.version,
                payload=StockChangedV1(
                    tenant_id=self._uow.tenant_id,
                    product_id=effect.product_id,
                    warehouse_id=effect.warehouse_id,
                    delta_quantity=effect.delta_quantity,
                    balance_quantity=next_quantity,
                    source_document_type=effect.source_document_type,
                    source_document_id=effect.source_document_id,
                ).model_dump(mode="json"),
                allow_zero_subscribers=True,
            )

    def _lock_balances(
        self, *, keys: set[tuple[uuid.UUID, uuid.UUID]]
    ) -> dict[tuple[uuid.UUID, uuid.UUID], StockBalance]:
        ordered_keys = sorted(
            keys,
            key=lambda key: (str(key[0]), str(key[1])),
        )
        balances: dict[tuple[uuid.UUID, uuid.UUID], StockBalance] = {}
        for product_id, warehouse_id in ordered_keys:
            self._uow.session.exec(
                insert(StockBalance)
                .values(
                    tenant_id=self._uow.tenant_id,
                    product_id=product_id,
                    warehouse_id=warehouse_id,
                    quantity=Decimal("0"),
                    version=1,
                    updated_at=get_datetime_utc(),
                )
                .on_conflict_do_nothing(
                    index_elements=("tenant_id", "product_id", "warehouse_id")
                )
            )
            balance = self._uow.session.exec(
                select(StockBalance)
                .where(
                    StockBalance.product_id == product_id,
                    StockBalance.warehouse_id == warehouse_id,
                )
                .with_for_update()
            ).one()
            balances[(product_id, warehouse_id)] = balance
        return balances

    def _validate_active_references(
        self, keys: set[tuple[uuid.UUID, uuid.UUID]]
    ) -> None:
        product_ids = {product_id for product_id, _ in keys}
        warehouse_ids = {warehouse_id for _, warehouse_id in keys}
        products = {
            product.id: product
            for product in self._uow.session.exec(
                select(Product).where(Product.id.in_(product_ids))
            ).all()
        }
        warehouses = {
            warehouse.id: warehouse
            for warehouse in self._uow.session.exec(
                select(Warehouse).where(Warehouse.id.in_(warehouse_ids))
            ).all()
        }
        for product_id in product_ids:
            if (product := products.get(product_id)) is None or not product.is_active:
                raise InventoryConflictError(
                    "Product is unavailable", reason="product_unavailable"
                )
        for warehouse_id in warehouse_ids:
            if (
                (warehouse := warehouses.get(warehouse_id)) is None
                or not warehouse.is_active
            ):
                raise InventoryConflictError(
                    "Warehouse is unavailable", reason="warehouse_unavailable"
                )

    @staticmethod
    def _validate_effects(effects: tuple[InventoryEffect, ...]) -> None:
        for effect in effects:
            if effect.delta_quantity == Decimal("0"):
                raise InventoryConflictError(
                    "Inventory effect cannot be zero", reason="zero_effect"
                )
