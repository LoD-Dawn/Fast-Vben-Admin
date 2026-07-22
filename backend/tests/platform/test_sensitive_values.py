import base64
import hashlib

import pytest
from cryptography.fernet import Fernet

from app.core.config import settings
from app.core.mfa import decrypt_secret, encrypt_secret
from app.platform.public_api import get_sensitive_value_protector
from app.platform.public_api.sensitive_values import SensitiveValueProtectionError


def test_sensitive_value_protector_is_versioned_and_masks_values() -> None:
    protector = get_sensitive_value_protector()

    protected = protector.encrypt("6222021234567890")

    assert protected.startswith("v1:")
    assert protector.decrypt(protected) == "6222021234567890"
    assert protector.fingerprint("6222021234567890") == protector.fingerprint(
        "6222021234567890"
    )
    assert protector.fingerprint("6222021234567890") != protector.fingerprint(
        "6222021234567891"
    )
    assert protector.mask("6222021234567890") == "************7890"
    assert protector.mask("123", visible_suffix=4) == "***"


def test_sensitive_value_protector_reads_legacy_fernet_values() -> None:
    key_material = hashlib.sha256(settings.SECRET_KEY.encode()).digest()
    legacy = Fernet(base64.urlsafe_b64encode(key_material)).encrypt(b"legacy-value").decode()

    assert get_sensitive_value_protector().decrypt(legacy) == "legacy-value"
    assert decrypt_secret(legacy) == "legacy-value"
    assert decrypt_secret(encrypt_secret("new-value")) == "new-value"


def test_sensitive_value_protector_rejects_unknown_versions() -> None:
    with pytest.raises(SensitiveValueProtectionError):
        get_sensitive_value_protector().decrypt("v2:not-a-valid-ciphertext")
