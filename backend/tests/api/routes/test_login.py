from unittest.mock import patch
from urllib.parse import parse_qs, urlparse

import pyotp
from fastapi.testclient import TestClient
from pwdlib.hashers.bcrypt import BcryptHasher
from sqlmodel import Session, select

from app.api.routes import login as login_route
from app.api.routes.login import get_login_captcha_key
from app.core.cache import redis_cache
from app.core.config import settings
from app.core.mfa import encrypt_totp_secret, serialize_recovery_codes
from app.core.security import get_password_hash, verify_password
from app.crud import create_user
from app.models import EnterpriseOidcIdentity, Role, User, UserCreate, UserRole
from app.utils import generate_password_reset_token
from tests.utils.user import user_authentication_headers
from tests.utils.utils import random_email, random_lower_string


def test_get_access_token(client: TestClient) -> None:
    login_data = {
        "username": settings.FIRST_SUPERUSER,
        "password": settings.FIRST_SUPERUSER_PASSWORD,
    }
    r = client.post(f"{settings.API_V1_STR}/login/access-token", data=login_data)
    tokens = r.json()
    assert r.status_code == 200
    assert "access_token" in tokens
    assert tokens["access_token"]


def test_enterprise_oidc_maps_local_user_role_and_active_status(
    client: TestClient,
    db: Session,
    monkeypatch,
    superuser_token_headers: dict[str, str],
) -> None:
    first_user = create_user(
        session=db,
        user_create=UserCreate(
            email=random_email(),
            password=random_lower_string(),
        ),
    )
    disabled_user = create_user(
        session=db,
        user_create=UserCreate(
            email=random_email(),
            password=random_lower_string(),
        ),
    )
    metadata = {
        "authorization_endpoint": "https://idp.example.test/authorize",
        "issuer": "https://idp.example.test",
        "jwks_uri": "https://idp.example.test/jwks",
        "token_endpoint": "https://idp.example.test/token",
    }
    claims: dict[str, object] = {
        "active": True,
        "email": first_user.email,
        "email_verified": True,
        "groups": ["idp-admin"],
        "sub": "enterprise-user-1",
    }
    monkeypatch.setattr(settings, "ENTERPRISE_OIDC_ENABLED", True)
    monkeypatch.setattr(settings, "ENTERPRISE_OIDC_ISSUER", metadata["issuer"])
    monkeypatch.setattr(settings, "ENTERPRISE_OIDC_CLIENT_ID", "test-client")
    monkeypatch.setattr(settings, "ENTERPRISE_OIDC_CLIENT_SECRET", "test-secret")
    monkeypatch.setattr(
        settings,
        "ENTERPRISE_OIDC_REDIRECT_URI",
        "http://testserver/api/v1/login/enterprise-oidc/callback",
    )
    monkeypatch.setattr(
        settings, "ENTERPRISE_OIDC_ROLE_MAPPING", '{"idp-admin":"admin"}'
    )
    monkeypatch.setattr(settings, "ENTERPRISE_OIDC_ROLE_SYNC_MODE", "replace")
    monkeypatch.setattr(settings, "ENTERPRISE_OIDC_SYNC_ACTIVE_STATUS", True)
    monkeypatch.setattr(login_route, "get_oidc_provider_metadata", lambda: metadata)
    monkeypatch.setattr(
        login_route,
        "exchange_authorization_code",
        lambda *, metadata, code, code_verifier: "test-id-token",
    )
    monkeypatch.setattr(
        login_route,
        "validate_identity_token",
        lambda *, id_token, metadata, expected_nonce: claims,
    )

    try:
        status = client.get(f"{settings.API_V1_STR}/login/enterprise-oidc/status")
        assert status.status_code == 200
        assert status.json()["enabled"] is True

        start = client.get(
            f"{settings.API_V1_STR}/login/enterprise-oidc", follow_redirects=False
        )
        assert start.status_code == 302
        authorization_query = parse_qs(urlparse(start.headers["location"]).query)
        assert authorization_query["code_challenge_method"] == ["S256"]
        assert authorization_query["nonce"]

        callback = client.get(
            f"{settings.API_V1_STR}/login/enterprise-oidc/callback",
            follow_redirects=False,
            params={"code": "provider-code", "state": authorization_query["state"][0]},
        )
        assert callback.status_code == 302
        ticket = parse_qs(urlparse(callback.headers["location"]).query)[
            "enterprise_ticket"
        ][0]

        exchange = client.post(
            f"{settings.API_V1_STR}/login/enterprise-oidc/exchange",
            json={"ticket": ticket},
        )
        assert exchange.status_code == 200
        assert exchange.json()["access_token"]

        success_logs = client.get(
            f"{settings.API_V1_STR}/logs/login",
            headers=superuser_token_headers,
            params={"keyword": first_user.email, "page_size": 20},
        )
        assert success_logs.status_code == 200
        assert any(
            log["email"] == first_user.email and log["status"] == "success"
            for log in success_logs.json()["items"]
        )

        repeated_exchange = client.post(
            f"{settings.API_V1_STR}/login/enterprise-oidc/exchange",
            json={"ticket": ticket},
        )
        assert repeated_exchange.status_code == 400
        assert repeated_exchange.json()["code"] == "AUTH_ENTERPRISE_OIDC_TICKET_INVALID"

        assigned_roles = db.exec(
            select(Role.code)
            .join(UserRole, UserRole.role_id == Role.id)
            .where(UserRole.user_id == first_user.id)
        ).all()
        assert assigned_roles == ["admin"]
        assert db.exec(
            select(EnterpriseOidcIdentity).where(
                EnterpriseOidcIdentity.user_id == first_user.id
            )
        ).one()

        claims.update(
            {
                "active": False,
                "email": disabled_user.email,
                "groups": [],
                "sub": "enterprise-user-2",
            }
        )
        disabled_start = client.get(
            f"{settings.API_V1_STR}/login/enterprise-oidc", follow_redirects=False
        )
        disabled_query = parse_qs(urlparse(disabled_start.headers["location"]).query)
        disabled_callback = client.get(
            f"{settings.API_V1_STR}/login/enterprise-oidc/callback",
            params={"code": "provider-code", "state": disabled_query["state"][0]},
        )
        assert disabled_callback.status_code == 403
        db.refresh(disabled_user)
        assert disabled_user.is_active is False
        failure_logs = client.get(
            f"{settings.API_V1_STR}/logs/login",
            headers=superuser_token_headers,
            params={"keyword": disabled_user.email, "page_size": 20},
        )
        assert failure_logs.status_code == 200
        assert any(
            log["email"] == disabled_user.email and log["status"] == "fail"
            for log in failure_logs.json()["items"]
        )
    finally:
        db.delete(first_user)
        db.delete(disabled_user)
        db.commit()


def test_get_access_token_incorrect_password(client: TestClient) -> None:
    login_data = {
        "username": settings.FIRST_SUPERUSER,
        "password": "incorrect",
    }
    r = client.post(f"{settings.API_V1_STR}/login/access-token", data=login_data)
    assert r.status_code == 401
    assert r.json()["code"] == "AUTH_INVALID_CREDENTIALS"


def test_login_requires_and_validates_enabled_mfa(
    client: TestClient, db: Session
) -> None:
    email = random_email()
    password = random_lower_string()
    secret = "JBSWY3DPEHPK3PXP"
    user = create_user(
        session=db,
        user_create=UserCreate(
            email=email,
            password=password,
            is_active=True,
            is_superuser=False,
        ),
    )
    user.mfa_enabled = True
    user.mfa_secret_encrypted = encrypt_totp_secret(secret)
    user.mfa_recovery_code_hashes = serialize_recovery_codes(["RECOVERY-CODE"])
    db.add(user)
    db.commit()

    missing_code = client.post(
        f"{settings.API_V1_STR}/login/access-token",
        data={"username": email, "password": password},
    )
    assert missing_code.status_code == 400
    assert missing_code.json()["code"] == "AUTH_MFA_REQUIRED"

    invalid_code = client.post(
        f"{settings.API_V1_STR}/login/access-token",
        data={"username": email, "password": password, "mfa_code": "invalid"},
    )
    assert invalid_code.status_code == 400
    assert invalid_code.json()["code"] == "AUTH_MFA_INVALID"

    valid_code = client.post(
        f"{settings.API_V1_STR}/login/access-token",
        data={
            "username": email,
            "password": password,
            "mfa_code": pyotp.TOTP(secret).now(),
        },
    )
    assert valid_code.status_code == 200
    assert valid_code.json()["access_token"]

    recovery_code = client.post(
        f"{settings.API_V1_STR}/login/access-token",
        data={"username": email, "password": password, "mfa_code": "RECOVERY-CODE"},
    )
    assert recovery_code.status_code == 200

    consumed_recovery_code = client.post(
        f"{settings.API_V1_STR}/login/access-token",
        data={"username": email, "password": password, "mfa_code": "RECOVERY-CODE"},
    )
    assert consumed_recovery_code.status_code == 400
    assert consumed_recovery_code.json()["code"] == "AUTH_MFA_INVALID"


def test_login_rate_limit_blocks_after_repeated_failures(
    client: TestClient, monkeypatch
) -> None:
    key_store: dict[str, str] = {}
    counters: dict[str, int] = {}

    monkeypatch.setattr(settings, "LOGIN_RATE_LIMIT_MAX_ATTEMPTS", 2)
    monkeypatch.setattr(settings, "LOGIN_RATE_LIMIT_ENABLED", True)

    monkeypatch.setattr(redis_cache, "get", lambda key: key_store.get(key))

    def fake_incr(key: str, *, ttl_seconds: int | None = None) -> int:
        _ = ttl_seconds
        counters[key] = counters.get(key, 0) + 1
        return counters[key]

    def fake_set(key: str, value: str, *, ttl_seconds: int | None = None) -> None:
        _ = ttl_seconds
        key_store[key] = value

    monkeypatch.setattr(redis_cache, "incr", fake_incr)
    monkeypatch.setattr(redis_cache, "set", fake_set)
    monkeypatch.setattr(redis_cache, "delete", lambda *keys: None)

    login_data = {
        "username": settings.FIRST_SUPERUSER,
        "password": "incorrect",
    }

    first = client.post(f"{settings.API_V1_STR}/login/access-token", data=login_data)
    second = client.post(f"{settings.API_V1_STR}/login/access-token", data=login_data)
    third = client.post(f"{settings.API_V1_STR}/login/access-token", data=login_data)

    assert first.status_code == 401
    assert second.status_code == 429
    assert second.json()["code"] == "AUTH_RATE_LIMITED"
    assert third.status_code == 429


def test_login_rate_limit_degrades_gracefully_when_cache_unavailable(
    client: TestClient, monkeypatch
) -> None:
    monkeypatch.setattr(settings, "LOGIN_RATE_LIMIT_ENABLED", True)
    monkeypatch.setattr(redis_cache, "get", lambda key: None)
    monkeypatch.setattr(
        redis_cache,
        "incr",
        lambda key, *, ttl_seconds=None: None,
    )
    monkeypatch.setattr(
        redis_cache, "set", lambda key, value, *, ttl_seconds=None: None
    )
    monkeypatch.setattr(redis_cache, "delete", lambda *keys: None)

    login_data = {
        "username": settings.FIRST_SUPERUSER,
        "password": "incorrect",
    }
    response = client.post(f"{settings.API_V1_STR}/login/access-token", data=login_data)

    assert response.status_code == 401
    assert response.json()["code"] == "AUTH_INVALID_CREDENTIALS"


def test_successful_login_clears_failed_login_rate_limit_state(
    client: TestClient, monkeypatch
) -> None:
    deleted_keys: list[tuple[str, ...]] = []
    monkeypatch.setattr(settings, "LOGIN_RATE_LIMIT_ENABLED", True)
    monkeypatch.setattr(redis_cache, "get", lambda key: None)
    monkeypatch.setattr(
        redis_cache,
        "delete",
        lambda *keys: deleted_keys.append(tuple(keys)),
    )

    login_data = {
        "username": settings.FIRST_SUPERUSER,
        "password": settings.FIRST_SUPERUSER_PASSWORD,
    }
    response = client.post(f"{settings.API_V1_STR}/login/access-token", data=login_data)

    assert response.status_code == 200
    assert deleted_keys


def test_login_captcha_endpoint_returns_challenge(
    client: TestClient, monkeypatch
) -> None:
    store: dict[str, object] = {}

    def fake_set_json(
        key: str, value: object, *, ttl_seconds: int | None = None
    ) -> None:
        _ = ttl_seconds
        store[key] = value

    monkeypatch.setattr(redis_cache, "set_json", fake_set_json)
    monkeypatch.setattr(
        "app.api.routes.login.random.randint",
        lambda start, end: 4 if start == 1 else 5,
    )

    response = client.get(
        f"{settings.API_V1_STR}/login/captcha",
        params={"username": settings.FIRST_SUPERUSER},
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["challenge_text"] == "4 + 4 = ?"
    assert get_login_captcha_key(payload["captcha_id"]) in store


def test_login_requires_captcha_after_threshold(
    client: TestClient, monkeypatch
) -> None:
    key_store: dict[str, str] = {}
    counters: dict[str, int] = {}

    monkeypatch.setattr(settings, "LOGIN_CAPTCHA_THRESHOLD", 1)
    monkeypatch.setattr(settings, "LOGIN_CAPTCHA_ENABLED", True)
    monkeypatch.setattr(settings, "LOGIN_RATE_LIMIT_ENABLED", True)
    monkeypatch.setattr(settings, "LOGIN_RATE_LIMIT_MAX_ATTEMPTS", 99)
    monkeypatch.setattr(redis_cache, "get", lambda key: key_store.get(key))

    def fake_incr(key: str, *, ttl_seconds: int | None = None) -> int:
        _ = ttl_seconds
        counters[key] = counters.get(key, 0) + 1
        key_store[key] = str(counters[key])
        return counters[key]

    monkeypatch.setattr(redis_cache, "incr", fake_incr)
    monkeypatch.setattr(redis_cache, "delete", lambda *keys: None)

    first = client.post(
        f"{settings.API_V1_STR}/login/access-token",
        data={
            "username": settings.FIRST_SUPERUSER,
            "password": "incorrect",
        },
    )
    second = client.post(
        f"{settings.API_V1_STR}/login/access-token",
        data={
            "username": settings.FIRST_SUPERUSER,
            "password": settings.FIRST_SUPERUSER_PASSWORD,
        },
    )

    assert first.status_code == 401
    assert second.status_code == 400
    assert second.json()["code"] == "AUTH_CAPTCHA_REQUIRED"


def test_login_accepts_valid_captcha_after_threshold(
    client: TestClient, monkeypatch
) -> None:
    key_store: dict[str, str] = {}
    json_store: dict[str, object] = {}
    counters: dict[str, int] = {}

    monkeypatch.setattr(settings, "LOGIN_CAPTCHA_THRESHOLD", 1)
    monkeypatch.setattr(settings, "LOGIN_CAPTCHA_ENABLED", True)
    monkeypatch.setattr(settings, "LOGIN_RATE_LIMIT_ENABLED", True)
    monkeypatch.setattr(settings, "LOGIN_RATE_LIMIT_MAX_ATTEMPTS", 99)

    monkeypatch.setattr(redis_cache, "get", lambda key: key_store.get(key))

    def fake_incr(key: str, *, ttl_seconds: int | None = None) -> int:
        _ = ttl_seconds
        counters[key] = counters.get(key, 0) + 1
        key_store[key] = str(counters[key])
        return counters[key]

    def fake_set_json(
        key: str, value: object, *, ttl_seconds: int | None = None
    ) -> None:
        _ = ttl_seconds
        json_store[key] = value

    def fake_get_json(key: str) -> object | None:
        return json_store.get(key)

    def fake_delete(*keys: str) -> None:
        for key in keys:
            key_store.pop(key, None)
            json_store.pop(key, None)

    monkeypatch.setattr(redis_cache, "incr", fake_incr)
    monkeypatch.setattr(redis_cache, "set_json", fake_set_json)
    monkeypatch.setattr(redis_cache, "get_json", fake_get_json)
    monkeypatch.setattr(redis_cache, "delete", fake_delete)
    monkeypatch.setattr(
        "app.api.routes.login.random.randint",
        lambda start, end: 3,
    )

    first = client.post(
        f"{settings.API_V1_STR}/login/access-token",
        data={
            "username": settings.FIRST_SUPERUSER,
            "password": "incorrect",
        },
    )
    assert first.status_code == 401

    captcha_response = client.get(
        f"{settings.API_V1_STR}/login/captcha",
        params={"username": settings.FIRST_SUPERUSER},
    )
    assert captcha_response.status_code == 200
    captcha = captcha_response.json()

    second = client.post(
        f"{settings.API_V1_STR}/login/access-token",
        data={
            "username": settings.FIRST_SUPERUSER,
            "password": settings.FIRST_SUPERUSER_PASSWORD,
            "captcha_id": captcha["captcha_id"],
            "captcha_code": "6",
        },
    )

    assert second.status_code == 200
    assert "access_token" in second.json()


def test_use_access_token(
    client: TestClient, superuser_token_headers: dict[str, str]
) -> None:
    r = client.post(
        f"{settings.API_V1_STR}/login/test-token",
        headers=superuser_token_headers,
    )
    result = r.json()
    assert r.status_code == 200
    assert "email" in result


def test_recovery_password(
    client: TestClient, normal_user_token_headers: dict[str, str]
) -> None:
    with (
        patch("app.core.config.settings.SMTP_HOST", "smtp.example.com"),
        patch("app.core.config.settings.SMTP_USER", "admin@example.com"),
    ):
        email = "test@example.com"
        r = client.post(
            f"{settings.API_V1_STR}/password-recovery/{email}",
            headers=normal_user_token_headers,
        )
        assert r.status_code == 200
        assert r.json() == {
            "message": "If that email is registered, we sent a password recovery link"
        }


def test_recovery_password_user_not_exits(
    client: TestClient, normal_user_token_headers: dict[str, str]
) -> None:
    email = "jVgQr@example.com"
    r = client.post(
        f"{settings.API_V1_STR}/password-recovery/{email}",
        headers=normal_user_token_headers,
    )
    # Should return 200 with generic message to prevent email enumeration attacks
    assert r.status_code == 200
    assert r.json() == {
        "message": "If that email is registered, we sent a password recovery link"
    }


def test_reset_password(client: TestClient, db: Session) -> None:
    email = random_email()
    password = random_lower_string()
    new_password = random_lower_string()

    user_create = UserCreate(
        email=email,
        full_name="Test User",
        password=password,
        is_active=True,
        is_superuser=False,
    )
    user = create_user(session=db, user_create=user_create)
    token = generate_password_reset_token(email=email)
    headers = user_authentication_headers(client=client, email=email, password=password)
    data = {"new_password": new_password, "token": token}

    r = client.post(
        f"{settings.API_V1_STR}/reset-password",
        headers=headers,
        json=data,
    )

    assert r.status_code == 200
    assert r.json() == {"message": "Password updated successfully"}

    db.refresh(user)
    verified, _ = verify_password(new_password, user.hashed_password)
    assert verified

    rejected_response = client.get(
        f"{settings.API_V1_STR}/users/me",
        headers=headers,
    )
    assert rejected_response.status_code == 403


def test_reset_password_invalid_token(
    client: TestClient, superuser_token_headers: dict[str, str]
) -> None:
    data = {"new_password": "changethis", "token": "invalid"}
    r = client.post(
        f"{settings.API_V1_STR}/reset-password",
        headers=superuser_token_headers,
        json=data,
    )
    response = r.json()

    assert r.status_code == 400
    assert response["message"] == "Invalid token"


def test_login_with_bcrypt_password_upgrades_to_argon2(
    client: TestClient, db: Session
) -> None:
    """Test that logging in with a bcrypt password hash upgrades it to argon2."""
    email = random_email()
    password = random_lower_string()

    # Create a bcrypt hash directly (simulating legacy password)
    bcrypt_hasher = BcryptHasher()
    bcrypt_hash = bcrypt_hasher.hash(password)
    assert bcrypt_hash.startswith("$2")  # bcrypt hashes start with $2

    user = User(email=email, hashed_password=bcrypt_hash, is_active=True)
    db.add(user)
    db.commit()
    db.refresh(user)

    assert user.hashed_password.startswith("$2")

    login_data = {"username": email, "password": password}
    r = client.post(f"{settings.API_V1_STR}/login/access-token", data=login_data)
    assert r.status_code == 200
    tokens = r.json()
    assert "access_token" in tokens

    db.refresh(user)

    # Verify the hash was upgraded to argon2
    assert user.hashed_password.startswith("$argon2")

    verified, updated_hash = verify_password(password, user.hashed_password)
    assert verified
    # Should not need another update since it's already argon2
    assert updated_hash is None


def test_login_with_argon2_password_keeps_hash(client: TestClient, db: Session) -> None:
    """Test that logging in with an argon2 password hash does not update it."""
    email = random_email()
    password = random_lower_string()

    # Create an argon2 hash (current default)
    argon2_hash = get_password_hash(password)
    assert argon2_hash.startswith("$argon2")

    # Create user with argon2 hash
    user = User(email=email, hashed_password=argon2_hash, is_active=True)
    db.add(user)
    db.commit()
    db.refresh(user)

    original_hash = user.hashed_password

    login_data = {"username": email, "password": password}
    r = client.post(f"{settings.API_V1_STR}/login/access-token", data=login_data)
    assert r.status_code == 200
    tokens = r.json()
    assert "access_token" in tokens

    db.refresh(user)

    assert user.hashed_password == original_hash
    assert user.hashed_password.startswith("$argon2")
