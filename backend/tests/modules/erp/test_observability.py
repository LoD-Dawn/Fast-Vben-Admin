from fastapi import APIRouter, FastAPI, HTTPException
from fastapi.testclient import TestClient
from prometheus_client import REGISTRY

from app.core.config import settings
from app.core.metrics import build_metrics_response
from app.modules.erp.application.inventory_posting import InventoryConflictError
from app.modules.erp.application.settlement import SettlementConflictError
from app.modules.erp.observability import (
    ErpDocumentCommandMetricRoute,
    observe_outbox_pending,
    observe_reconciliation_differences,
)


def _sample_value(name: str, labels: dict[str, str]) -> float:
    return REGISTRY.get_sample_value(name, labels=labels) or 0.0


def test_erp_observability_uses_bounded_labels(monkeypatch) -> None:
    monkeypatch.setattr(settings, "METRICS_ENABLED", True)
    app = FastAPI()
    router = APIRouter(route_class=ErpDocumentCommandMetricRoute)

    @router.post("/erp/purchase-orders/{order_id}/approve")
    def approve_purchase_order(order_id: str) -> dict[str, str]:
        return {"id": order_id}

    @router.post("/erp/stock-ins/{document_id}/approve")
    def conflicting_stock_command(document_id: str) -> None:
        del document_id
        raise HTTPException(status_code=409, detail="Stock is insufficient")

    app.include_router(router)
    client = TestClient(app)

    success_labels = {
        "type": "purchase_order",
        "action": "approve",
        "result": "success",
    }
    conflict_labels = {
        "type": "stock_in",
        "action": "approve",
        "result": "conflict",
    }
    success_before = _sample_value("erp_document_commands_total", success_labels)
    conflict_before = _sample_value("erp_document_commands_total", conflict_labels)

    assert client.post("/erp/purchase-orders/order-1/approve").status_code == 200
    assert client.post("/erp/stock-ins/stock-1/approve").status_code == 409

    assert _sample_value("erp_document_commands_total", success_labels) == success_before + 1
    assert _sample_value("erp_document_commands_total", conflict_labels) == conflict_before + 1

    InventoryConflictError("Stock is insufficient", reason="insufficient_stock")
    SettlementConflictError(
        "Settlement source is unavailable", reason="source_unavailable"
    )
    observe_reconciliation_differences(
        stock_difference_count=2, settlement_difference_count=3
    )
    observe_outbox_pending(total=4)

    exposition = build_metrics_response().body.decode()
    assert "erp_stock_conflicts_total" in exposition
    assert "erp_settlement_conflicts_total" in exposition
    assert "erp_reconciliation_differences" in exposition
    assert "erp_outbox_pending_total" in exposition
    metric_lines = [line for line in exposition.splitlines() if line.startswith("erp_")]
    assert all("tenant_id" not in line and "document_no" not in line for line in metric_lines)
