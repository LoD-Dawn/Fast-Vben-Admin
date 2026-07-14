from collections.abc import Awaitable, Callable
from time import perf_counter

from fastapi import Request, Response
from prometheus_client import (
    CONTENT_TYPE_LATEST,
    Counter,
    Gauge,
    Histogram,
    generate_latest,
)

from app.core.config import settings

HTTP_REQUESTS_TOTAL = Counter(
    "fast_vben_http_requests_total",
    "Total HTTP requests handled by the application.",
    ("method", "route", "status_code"),
)
HTTP_REQUEST_DURATION_SECONDS = Histogram(
    "fast_vben_http_request_duration_seconds",
    "HTTP request processing duration in seconds.",
    ("method", "route"),
)
HTTP_REQUESTS_IN_PROGRESS = Gauge(
    "fast_vben_http_requests_in_progress",
    "HTTP requests currently being processed.",
    ("method", "route"),
)


def get_route_label(request: Request) -> str:
    route = request.scope.get("route")
    path = getattr(route, "path", None)
    return str(path) if path else "unmatched"


async def metrics_middleware(
    request: Request,
    call_next: Callable[[Request], Awaitable[Response]],
) -> Response:
    if not settings.METRICS_ENABLED:
        return await call_next(request)

    started_at = perf_counter()
    route = get_route_label(request)
    method = request.method
    status_code = 500
    HTTP_REQUESTS_IN_PROGRESS.labels(method=method, route=route).inc()
    try:
        response = await call_next(request)
        status_code = response.status_code
        return response
    finally:
        final_route = get_route_label(request)
        if final_route != route:
            HTTP_REQUESTS_IN_PROGRESS.labels(method=method, route=route).dec()
            HTTP_REQUESTS_IN_PROGRESS.labels(method=method, route=final_route).inc()
        HTTP_REQUESTS_IN_PROGRESS.labels(method=method, route=final_route).dec()
        HTTP_REQUESTS_TOTAL.labels(
            method=method,
            route=final_route,
            status_code=str(status_code),
        ).inc()
        HTTP_REQUEST_DURATION_SECONDS.labels(method=method, route=final_route).observe(
            perf_counter() - started_at
        )


def build_metrics_response() -> Response:
    return Response(content=generate_latest(), media_type=CONTENT_TYPE_LATEST)
