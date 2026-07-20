from fastapi.testclient import TestClient

from app.core.config import settings
from tests.utils.utils import random_lower_string


def test_manage_sms_and_send_with_debug_channel(
    client: TestClient, superuser_token_headers: dict[str, str]
) -> None:
    suffix = random_lower_string()[:8]
    channel_response = client.post(
        f"{settings.API_V1_STR}/sms/channels",
        headers=superuser_token_headers,
        json={
            "name": f"测试调试渠道 {suffix}",
            "code": f"debug-{suffix}",
            "provider": "debug",
            "signature": "测试通知",
            "is_active": True,
            "is_default": False,
        },
    )
    assert channel_response.status_code == 200
    channel = channel_response.json()

    template_response = client.post(
        f"{settings.API_V1_STR}/sms/templates",
        headers=superuser_token_headers,
        json={
            "name": f"测试模板 {suffix}",
            "code": f"test-{suffix}",
            "type": "verification",
            "content": "您的验证码为 {code}。",
            "channel_id": channel["id"],
            "is_active": True,
        },
    )
    assert template_response.status_code == 200
    template = template_response.json()
    assert template["channel_code"] == channel["code"]
    assert template["params"] == "code"

    send_response = client.post(
        f"{settings.API_V1_STR}/sms/templates/{template['id']}/send-test",
        headers=superuser_token_headers,
        json={
            "mobile": "13800138000",
            "template_params": {"code": "123456"},
        },
    )
    assert send_response.status_code == 200
    sms_log = send_response.json()
    assert sms_log["send_status"] == "success"
    assert sms_log["receive_status"] == "pending"
    assert sms_log["api_send_code"] == "DEBUG_ACCEPTED"
    assert sms_log["template_content"] == "您的验证码为 123456。"

    callback_response = client.post(
        f"{settings.API_V1_STR}/sms/callbacks/{channel['code']}",
        params={"tenant_code": "default"},
        json={
            "request_id": sms_log["api_request_id"],
            "status": "success",
            "message": "DELIVRD",
        },
    )
    assert callback_response.status_code == 200
    assert callback_response.json()["receive_status"] == "success"
    assert callback_response.json()["api_receive_message"] == "DELIVRD"

    logs_response = client.get(
        f"{settings.API_V1_STR}/sms/logs",
        headers=superuser_token_headers,
        params={"keyword": "13800138000"},
    )
    assert logs_response.status_code == 200
    assert any(item["id"] == sms_log["id"] for item in logs_response.json()["items"])

    delete_template_response = client.delete(
        f"{settings.API_V1_STR}/sms/templates/{template['id']}",
        headers=superuser_token_headers,
    )
    assert delete_template_response.status_code == 204
    delete_channel_response = client.delete(
        f"{settings.API_V1_STR}/sms/channels/{channel['id']}",
        headers=superuser_token_headers,
    )
    assert delete_channel_response.status_code == 204


def test_normal_user_cannot_access_sms_management(
    client: TestClient, normal_user_token_headers: dict[str, str]
) -> None:
    response = client.get(
        f"{settings.API_V1_STR}/sms/channels",
        headers=normal_user_token_headers,
    )
    assert response.status_code == 403
