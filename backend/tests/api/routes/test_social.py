from fastapi.testclient import TestClient
from sqlmodel import Session

from app import crud
from app.core.config import settings
from app.models import SocialClient, SocialUser, UserCreate
from tests.utils.utils import random_email, random_lower_string


def test_superuser_can_bind_and_unbind_social_user(
    client: TestClient, db: Session, superuser_token_headers: dict[str, str]
) -> None:
    target_user = crud.create_user(
        session=db,
        user_create=UserCreate(email=random_email(), password=random_lower_string()),
    )
    social_user = SocialUser(type="gitee", openid=random_lower_string())
    conflicting_social_user = SocialUser(
        type="gitee", openid=random_lower_string(), user_id=target_user.id
    )
    db.add(social_user)
    db.add(conflicting_social_user)
    db.commit()

    try:
        conflict = client.post(
            f"{settings.API_V1_STR}/social/users/{social_user.id}/bind",
            headers=superuser_token_headers,
            json={"user_id": str(target_user.id)},
        )
        assert conflict.status_code == 409

        db.delete(conflicting_social_user)
        db.commit()

        bound = client.post(
            f"{settings.API_V1_STR}/social/users/{social_user.id}/bind",
            headers=superuser_token_headers,
            json={"user_id": str(target_user.id)},
        )
        assert bound.status_code == 200
        assert bound.json()["user_id"] == str(target_user.id)

        unbound = client.post(
            f"{settings.API_V1_STR}/social/users/{social_user.id}/unbind",
            headers=superuser_token_headers,
        )
        assert unbound.status_code == 200
        assert unbound.json()["user_id"] is None
    finally:
        db.delete(social_user)
        db.delete(target_user)
        db.commit()


def test_social_client_secret_update_requires_current_password(
    client: TestClient, db: Session, superuser_token_headers: dict[str, str]
) -> None:
    social_client = SocialClient(
        name="Secret update test client",
        social_type="gitee",
        client_id=random_lower_string(),
        client_secret="old-secret",
    )
    db.add(social_client)
    db.commit()

    try:
        missing_password = client.patch(
            f"{settings.API_V1_STR}/social/clients/{social_client.id}",
            headers=superuser_token_headers,
            json={"client_secret": "new-secret"},
        )
        assert missing_password.status_code == 400
        assert missing_password.json()["code"] == "AUTH_REAUTH_REQUIRED"

        incorrect_password = client.patch(
            f"{settings.API_V1_STR}/social/clients/{social_client.id}",
            headers=superuser_token_headers,
            json={"client_secret": "new-secret", "current_password": "incorrect"},
        )
        assert incorrect_password.status_code == 400
        assert incorrect_password.json()["code"] == "BAD_REQUEST"

        secret_update = client.patch(
            f"{settings.API_V1_STR}/social/clients/{social_client.id}",
            headers=superuser_token_headers,
            json={
                "client_secret": "new-secret",
                "current_password": settings.FIRST_SUPERUSER_PASSWORD,
            },
        )
        assert secret_update.status_code == 200
        assert secret_update.json()["client_secret"] == "******"
    finally:
        db.delete(social_client)
        db.commit()
