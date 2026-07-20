from fastapi.testclient import TestClient

from app.core.config import settings
from app.platform.infra import mail_router as mail_routes
from tests.utils.utils import random_lower_string


def test_manage_mail_and_send_with_smtp_account(
    client: TestClient,
    monkeypatch,
    superuser_token_headers: dict[str, str],
) -> None:
    suffix = random_lower_string()[:8]

    def fake_send_mail(**kwargs) -> str:
        assert kwargs["to_email"] == f"user-{suffix}@example.com"
        assert kwargs["subject"] == "欢迎 Alice"
        assert "Alice" in kwargs["html_content"]
        return f"message-{suffix}"

    monkeypatch.setattr(mail_routes, "send_mail", fake_send_mail)

    account_response = client.post(
        f"{settings.API_V1_STR}/mail/accounts",
        headers=superuser_token_headers,
        json={
            "name": f"测试邮箱账号 {suffix}",
            "code": f"mail-{suffix}",
            "email": f"sender-{suffix}@example.com",
            "username": f"sender-{suffix}@example.com",
            "password": "secret",
            "host": "smtp.example.com",
            "port": 465,
            "ssl_enable": True,
            "starttls_enable": False,
            "is_active": True,
            "is_default": False,
        },
    )
    assert account_response.status_code == 200
    account = account_response.json()
    assert account["password"] == "******"

    template_response = client.post(
        f"{settings.API_V1_STR}/mail/templates",
        headers=superuser_token_headers,
        json={
            "name": f"欢迎模板 {suffix}",
            "code": f"welcome-{suffix}",
            "account_id": account["id"],
            "nickname": "系统通知",
            "title": "欢迎 {name}",
            "content": "<p>您好，{name}</p>",
            "is_active": True,
        },
    )
    assert template_response.status_code == 200
    template = template_response.json()
    assert template["account_code"] == account["code"]
    assert template["params"] == "name"

    send_response = client.post(
        f"{settings.API_V1_STR}/mail/templates/{template['id']}/send-test",
        headers=superuser_token_headers,
        json={
            "to_email": f"user-{suffix}@example.com",
            "template_params": {"name": "Alice"},
        },
    )
    assert send_response.status_code == 200
    mail_log = send_response.json()
    assert mail_log["send_status"] == "success"
    assert mail_log["send_code"] == "SMTP_ACCEPTED"
    assert mail_log["message_id"] == f"message-{suffix}"
    assert mail_log["title"] == "欢迎 Alice"
    assert "Alice" in mail_log["content"]

    logs_response = client.get(
        f"{settings.API_V1_STR}/mail/logs",
        headers=superuser_token_headers,
        params={"to_email": f"user-{suffix}@example.com"},
    )
    assert logs_response.status_code == 200
    assert any(item["id"] == mail_log["id"] for item in logs_response.json()["items"])

    resend_response = client.post(
        f"{settings.API_V1_STR}/mail/logs/{mail_log['id']}/resend",
        headers=superuser_token_headers,
    )
    assert resend_response.status_code == 200
    assert resend_response.json()["send_status"] == "success"

    delete_template_response = client.delete(
        f"{settings.API_V1_STR}/mail/templates/{template['id']}",
        headers=superuser_token_headers,
    )
    assert delete_template_response.status_code == 204
    delete_account_response = client.delete(
        f"{settings.API_V1_STR}/mail/accounts/{account['id']}",
        headers=superuser_token_headers,
    )
    assert delete_account_response.status_code == 204


def test_normal_user_cannot_access_mail_management(
    client: TestClient, normal_user_token_headers: dict[str, str]
) -> None:
    response = client.get(
        f"{settings.API_V1_STR}/mail/accounts",
        headers=normal_user_token_headers,
    )
    assert response.status_code == 403
