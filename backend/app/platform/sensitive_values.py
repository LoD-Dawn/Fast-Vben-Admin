"""Platform-owned default implementation of sensitive value protection."""

import base64
import hashlib
import hmac
from functools import lru_cache

from cryptography.fernet import Fernet, InvalidToken

from app.core.config import settings
from app.platform.public_api.sensitive_values import SensitiveValueProtectionError

_CURRENT_VERSION = "v1"


class FernetSensitiveValueProtector:
    """Versioned Fernet protector with compatibility for existing unversioned data."""

    def __init__(self) -> None:
        key_material = hashlib.sha256(settings.SECRET_KEY.encode()).digest()
        self._fernet = Fernet(base64.urlsafe_b64encode(key_material))

    def encrypt(self, value: str) -> str:
        if not value:
            raise ValueError("Sensitive value cannot be empty")
        return f"{_CURRENT_VERSION}:{self._fernet.encrypt(value.encode()).decode()}"

    def decrypt(self, protected_value: str) -> str:
        if not protected_value:
            raise SensitiveValueProtectionError("Protected value is empty")
        version, separator, ciphertext = protected_value.partition(":")
        if separator and version != _CURRENT_VERSION:
            raise SensitiveValueProtectionError("Unsupported protected value version")
        try:
            return self._fernet.decrypt(
                (ciphertext if separator else protected_value).encode()
            ).decode()
        except (InvalidToken, UnicodeDecodeError) as exc:
            raise SensitiveValueProtectionError("Invalid protected value") from exc

    @staticmethod
    def fingerprint(value: str) -> str:
        if not value:
            raise ValueError("Sensitive value cannot be empty")
        return "v1:" + hmac.new(
            settings.SECRET_KEY.encode(), value.encode(), hashlib.sha256
        ).hexdigest()

    @staticmethod
    def mask(value: str, *, visible_suffix: int = 4) -> str:
        if visible_suffix < 0:
            raise ValueError("Visible suffix cannot be negative")
        if len(value) <= visible_suffix:
            return "*" * len(value)
        return "*" * (len(value) - visible_suffix) + value[-visible_suffix:]


@lru_cache(maxsize=1)
def get_sensitive_value_protector() -> FernetSensitiveValueProtector:
    """Return the Platform default without exposing its encryption key."""

    return FernetSensitiveValueProtector()
