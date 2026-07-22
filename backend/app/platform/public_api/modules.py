"""Stable module-runtime queries available to business modules and workers."""

import uuid
from typing import Protocol


class EnabledModuleTenantDirectory(Protocol):
    """Enumerates tenants that may receive a module-owned scheduled job."""

    def list_enabled_tenant_ids(self, *, module_code: str) -> tuple[uuid.UUID, ...]: ...
