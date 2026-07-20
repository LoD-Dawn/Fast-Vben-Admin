"""Deprecated compatibility import for Platform SMS infrastructure routes."""

from app.platform.infra.sms_router import (
    create_sms_log,
    get_template_channel,
    router,
)

__all__ = ["create_sms_log", "get_template_channel", "router"]
