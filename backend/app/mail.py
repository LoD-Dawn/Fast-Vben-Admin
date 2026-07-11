import re
from typing import Any

import emails

from app.models import MailAccount

TEMPLATE_PARAM_PATTERN = re.compile(r"\{([A-Za-z_][A-Za-z0-9_]*)\}")


def get_template_params(*parts: str) -> str:
    params: list[str] = []
    for part in parts:
        params.extend(TEMPLATE_PARAM_PATTERN.findall(part))
    return ",".join(dict.fromkeys(params))


def render_template(content: str, params: dict[str, str]) -> str:
    return TEMPLATE_PARAM_PATTERN.sub(
        lambda match: params[match.group(1)],
        content,
    )


def send_mail(
    *,
    account: MailAccount,
    to_email: str,
    subject: str,
    html_content: str,
    from_name: str | None = None,
) -> str | None:
    message = emails.message.Message(
        subject=subject,
        html=html_content,
        mail_from=(from_name or account.name, str(account.email)),
    )
    smtp_options: dict[str, Any] = {"host": account.host, "port": account.port}
    if account.ssl_enable:
        smtp_options["ssl"] = True
    elif account.starttls_enable:
        smtp_options["tls"] = True
    if account.username:
        smtp_options["user"] = account.username
    if account.password:
        smtp_options["password"] = account.password

    response = message.send(to=to_email, smtp=smtp_options)
    return getattr(response, "message_id", None)
