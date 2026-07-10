import jwt
from fastapi.testclient import TestClient
from sqlmodel import Session, select

from app import crud
from app.core import security
from app.core.config import settings
from app.models import UserCreate, UserSession
from tests.utils.user import user_authentication_headers
from tests.utils.utils import random_email, random_lower_string


def test_login_creates_user_session(client: TestClient, db: Session) -> None:
    email = random_email()
    password = random_lower_string()
    user = crud.create_user(
        session=db,
        user_create=UserCreate(email=email, password=password),
    )

    headers = user_authentication_headers(
        client=client,
        email=email,
        password=password,
    )

    token = headers["Authorization"].removeprefix("Bearer ")
    payload = jwt.decode(
        token,
        settings.SECRET_KEY,
        algorithms=[security.ALGORITHM],
    )
    user_session = db.exec(
        select(UserSession).where(UserSession.user_id == user.id)
    ).first()

    assert payload["jti"]
    assert user_session
    assert user_session.token_jti == payload["jti"]


def test_normal_user_cannot_read_user_sessions(
    client: TestClient, normal_user_token_headers: dict[str, str]
) -> None:
    response = client.get(
        f"{settings.API_V1_STR}/sessions",
        headers=normal_user_token_headers,
    )

    assert response.status_code == 403


def test_revoke_user_session_invalidates_token(
    client: TestClient,
    db: Session,
    superuser_token_headers: dict[str, str],
) -> None:
    email = random_email()
    password = random_lower_string()
    crud.create_user(
        session=db,
        user_create=UserCreate(email=email, password=password),
    )
    target_headers = user_authentication_headers(
        client=client,
        email=email,
        password=password,
    )
    target_token = target_headers["Authorization"].removeprefix("Bearer ")
    target_payload = jwt.decode(
        target_token,
        settings.SECRET_KEY,
        algorithms=[security.ALGORITHM],
    )
    target_session = db.exec(
        select(UserSession).where(UserSession.token_jti == target_payload["jti"])
    ).first()
    assert target_session

    response = client.post(
        f"{settings.API_V1_STR}/sessions/{target_session.id}/revoke",
        headers=superuser_token_headers,
    )
    assert response.status_code == 200
    assert response.json()["message"] == "Session revoked"

    rejected_response = client.get(
        f"{settings.API_V1_STR}/users/me",
        headers=target_headers,
    )
    assert rejected_response.status_code == 403


def test_cannot_revoke_current_user_session(
    client: TestClient,
    db: Session,
    superuser_token_headers: dict[str, str],
) -> None:
    token = superuser_token_headers["Authorization"].removeprefix("Bearer ")
    payload = jwt.decode(
        token,
        settings.SECRET_KEY,
        algorithms=[security.ALGORITHM],
    )
    current_session = db.exec(
        select(UserSession).where(UserSession.token_jti == payload["jti"])
    ).first()
    assert current_session

    response = client.post(
        f"{settings.API_V1_STR}/sessions/{current_session.id}/revoke",
        headers=superuser_token_headers,
    )

    assert response.status_code == 400
    assert response.json()["message"] == "Cannot revoke current session"
