"""Versioned payload contracts published by the Platform module."""

import uuid

from pydantic import BaseModel

from app.platform.core.runtime_models import ModuleObservedState


class ModuleObservedStateChangedV1(BaseModel):
    module_code: str
    previous_state: ModuleObservedState
    observed_state: ModuleObservedState
    actual_revision: str | None = None
    reason: str


class DepartmentArchivedV1(BaseModel):
    department_id: uuid.UUID
    tenant_id: uuid.UUID
    name: str


class PostArchivedV1(BaseModel):
    post_id: uuid.UUID
    tenant_id: uuid.UUID
    name: str


class TenantArchivedV1(BaseModel):
    tenant_id: uuid.UUID
    tenant_code: str


class UserArchivedV1(BaseModel):
    user_id: uuid.UUID
    tenant_id: uuid.UUID
    full_name: str | None = None


class UserAnonymizedV1(BaseModel):
    user_id: uuid.UUID
    tenant_id: uuid.UUID
    reason: str
