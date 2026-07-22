"""Stable encryption contract for business-module sensitive values."""

from typing import Protocol


class SensitiveValueProtectionError(ValueError):
    """Raised when a protected value cannot be decrypted safely."""


class SensitiveValueProtector(Protocol):
    """Protects confidential fields without exposing key material to modules."""

    def encrypt(self, value: str) -> str: ...

    def decrypt(self, protected_value: str) -> str: ...

    def fingerprint(self, value: str) -> str: ...

    def mask(self, value: str, *, visible_suffix: int = 4) -> str: ...
