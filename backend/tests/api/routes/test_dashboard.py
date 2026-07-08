from fastapi.testclient import TestClient

from app.core.config import settings


def test_read_dashboard_analytics(
    client: TestClient, superuser_token_headers: dict[str, str]
) -> None:
    response = client.get(
        f"{settings.API_V1_STR}/dashboard/analytics",
        headers=superuser_token_headers,
    )
    assert response.status_code == 200
    data = response.json()
    assert "overview" in data
    assert "hourly_trends" in data
    assert "monthly_visits" in data
    assert data["overview"]["user_total"] >= 1
    assert len(data["hourly_trends"]) == 18
    assert len(data["monthly_visits"]) == 12


def test_read_dashboard_analytics_requires_auth(client: TestClient) -> None:
    response = client.get(f"{settings.API_V1_STR}/dashboard/analytics")
    assert response.status_code == 401
