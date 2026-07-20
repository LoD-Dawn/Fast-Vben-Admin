"""Deprecated compatibility import for Platform mail infrastructure."""

from app.platform.infra.mail import get_template_params, render_template, send_mail

__all__ = ["get_template_params", "render_template", "send_mail"]
