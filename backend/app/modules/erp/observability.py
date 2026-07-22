"""Bounded Prometheus metrics owned by the ERP module."""

from collections.abc import Awaitable, Callable
from importlib import import_module
from time import perf_counter

from fastapi import HTTPException, Request, Response
from fastapi.routing import APIRoute
from prometheus_client import Counter, Gauge, Histogram
from sqlmodel import Session

from app.core.config import settings

ERP_DOCUMENT_COMMANDS_TOTAL = Counter(
    "erp_document_commands_total",
    "ERP document commands grouped by document type, action, and result.",
    ("type", "action", "result"),
)
ERP_DOCUMENT_COMMAND_DURATION_SECONDS = Histogram(
    "erp_document_command_duration_seconds",
    "ERP document command duration in seconds.",
    ("type", "action"),
)
ERP_STOCK_CONFLICTS_TOTAL = Counter(
    "erp_stock_conflicts_total",
    "ERP stock conflicts grouped by stable reason.",
    ("reason",),
)
ERP_SETTLEMENT_CONFLICTS_TOTAL = Counter(
    "erp_settlement_conflicts_total",
    "ERP settlement conflicts grouped by stable reason.",
    ("reason",),
)
ERP_RECONCILIATION_DIFFERENCES = Gauge(
    "erp_reconciliation_differences",
    "Differences found by the most recent ERP reconciliation run.",
    ("kind",),
)
ERP_OUTBOX_PENDING_TOTAL = Gauge(
    "erp_outbox_pending_total",
    "Pending ERP outbox events.",
)

_DOCUMENT_TYPES = {
    "finance-payments": "finance_payment",
    "finance-receipts": "finance_receipt",
    "purchase-ins": "purchase_in",
    "purchase-orders": "purchase_order",
    "purchase-returns": "purchase_return",
    "sale-orders": "sale_order",
    "sale-outs": "sale_out",
    "sale-returns": "sale_return",
    "stock-checks": "stock_check",
    "stock-ins": "stock_in",
    "stock-moves": "stock_move",
    "stock-outs": "stock_out",
}


def document_command_labels(path: str, method: str) -> tuple[str, str] | None:
    """Return bounded document-command labels from an ERP route template."""

    segments = path.strip("/").split("/")
    if len(segments) < 2 or segments[0] != "erp":
        return None
    document_type = _DOCUMENT_TYPES.get(segments[1])
    if document_type is None:
        return None
    if segments[-1] in {"approve", "reverse"} and method == "POST":
        return document_type, segments[-1]
    if method == "POST" and len(segments) == 2:
        return document_type, "create"
    if method == "PATCH":
        return document_type, "update"
    if method == "DELETE":
        return document_type, "delete"
    return None


def _command_result(status_code: int) -> str:
    if 200 <= status_code < 300:
        return "success"
    if status_code == 409:
        return "conflict"
    if 400 <= status_code < 500:
        return "rejected"
    return "failure"


def observe_document_command(
    *, document_type: str, action: str, result: str, duration_seconds: float
) -> None:
    if not settings.METRICS_ENABLED:
        return
    ERP_DOCUMENT_COMMANDS_TOTAL.labels(
        type=document_type, action=action, result=result
    ).inc()
    ERP_DOCUMENT_COMMAND_DURATION_SECONDS.labels(
        type=document_type, action=action
    ).observe(duration_seconds)


def observe_stock_conflict(*, reason: str) -> None:
    if settings.METRICS_ENABLED:
        ERP_STOCK_CONFLICTS_TOTAL.labels(reason=reason).inc()


def observe_settlement_conflict(*, reason: str) -> None:
    if settings.METRICS_ENABLED:
        ERP_SETTLEMENT_CONFLICTS_TOTAL.labels(reason=reason).inc()


def observe_reconciliation_differences(
    *, stock_difference_count: int, settlement_difference_count: int
) -> None:
    if not settings.METRICS_ENABLED:
        return
    ERP_RECONCILIATION_DIFFERENCES.labels(kind="stock").set(stock_difference_count)
    ERP_RECONCILIATION_DIFFERENCES.labels(kind="settlement").set(
        settlement_difference_count
    )


def observe_outbox_pending(*, total: int) -> None:
    if settings.METRICS_ENABLED:
        ERP_OUTBOX_PENDING_TOTAL.set(total)


def refresh_outbox_pending(session: Session) -> None:
    """Refresh the module backlog gauge from the worker's global session."""

    count_pending_events = import_module("app.modules.outbox").count_pending_events
    observe_outbox_pending(total=count_pending_events(session=session, module_code="erp"))


class ErpDocumentCommandMetricRoute(APIRoute):
    """Record ERP document command metrics without duplicating every endpoint."""

    def get_route_handler(self) -> Callable[[Request], Awaitable[Response]]:
        original_handler = super().get_route_handler()
        method = next(iter(self.methods), "")
        labels = document_command_labels(path=self.path, method=method)
        if labels is None:
            return original_handler
        document_type, action = labels

        async def metric_handler(request: Request) -> Response:
            started_at = perf_counter()
            try:
                response = await original_handler(request)
            except HTTPException as exc:
                observe_document_command(
                    document_type=document_type,
                    action=action,
                    result=_command_result(exc.status_code),
                    duration_seconds=perf_counter() - started_at,
                )
                raise
            except Exception:
                observe_document_command(
                    document_type=document_type,
                    action=action,
                    result="failure",
                    duration_seconds=perf_counter() - started_at,
                )
                raise
            observe_document_command(
                document_type=document_type,
                action=action,
                result=_command_result(response.status_code),
                duration_seconds=perf_counter() - started_at,
            )
            return response

        return metric_handler
