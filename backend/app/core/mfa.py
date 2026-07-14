import base64
import hashlib
import hmac
import json
import secrets

import pyotp
from cryptography.fernet import Fernet, InvalidToken

from app.core.config import settings


def _get_fernet() -> Fernet:
    key_material = hashlib.sha256(settings.SECRET_KEY.encode()).digest()
    return Fernet(base64.urlsafe_b64encode(key_material))


def generate_totp_secret() -> str:
    return pyotp.random_base32()


def build_totp_uri(*, secret: str, account_name: str) -> str:
    return pyotp.TOTP(secret).provisioning_uri(
        name=account_name,
        issuer_name=settings.MFA_TOTP_ISSUER,
    )


def normalize_totp_code(code: str) -> str:
    return "".join(char for char in code if char.isdigit())


def verify_totp_code(*, secret: str, code: str) -> bool:
    normalized_code = normalize_totp_code(code)
    if len(normalized_code) != 6:
        return False
    return bool(
        pyotp.TOTP(secret).verify(
            normalized_code,
            valid_window=settings.MFA_TOTP_VALID_WINDOW,
        )
    )


def encrypt_totp_secret(secret: str) -> str:
    return encrypt_secret(secret)


def decrypt_totp_secret(secret_encrypted: str) -> str:
    return decrypt_secret(secret_encrypted)


def encrypt_secret(value: str) -> str:
    return _get_fernet().encrypt(value.encode()).decode()


def decrypt_secret(value_encrypted: str) -> str:
    try:
        return _get_fernet().decrypt(value_encrypted.encode()).decode()
    except InvalidToken as exc:
        raise ValueError("Invalid encrypted secret") from exc


def generate_recovery_codes(*, count: int = 10) -> list[str]:
    return [secrets.token_urlsafe(9).upper() for _ in range(count)]


def _hash_recovery_code(code: str) -> str:
    return hmac.new(
        settings.SECRET_KEY.encode(),
        code.strip().upper().encode(),
        hashlib.sha256,
    ).hexdigest()


def serialize_recovery_codes(codes: list[str]) -> str:
    return json.dumps([_hash_recovery_code(code) for code in codes])


def consume_recovery_code(
    recovery_codes_serialized: str | None, code: str
) -> str | None:
    if not recovery_codes_serialized:
        return None
    try:
        recovery_code_hashes = json.loads(recovery_codes_serialized)
    except json.JSONDecodeError:
        return None
    if not isinstance(recovery_code_hashes, list):
        return None

    expected_hash = _hash_recovery_code(code)
    for index, recovery_code_hash in enumerate(recovery_code_hashes):
        if isinstance(recovery_code_hash, str) and hmac.compare_digest(
            recovery_code_hash, expected_hash
        ):
            recovery_code_hashes.pop(index)
            return json.dumps(recovery_code_hashes)
    return None


def get_recovery_code_count(recovery_codes_serialized: str | None) -> int:
    if not recovery_codes_serialized:
        return 0
    try:
        recovery_code_hashes = json.loads(recovery_codes_serialized)
    except json.JSONDecodeError:
        return 0
    return len(recovery_code_hashes) if isinstance(recovery_code_hashes, list) else 0
