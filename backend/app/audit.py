"""Deprecated compatibility import for Platform audit infrastructure."""

from app.platform.infra.audit import (
    audit_operation_middleware,
    create_login_log,
    get_client_ip,
    get_user_agent,
)

__all__ = [
    "audit_operation_middleware",
    "create_login_log",
    "get_client_ip",
    "get_user_agent",
]
