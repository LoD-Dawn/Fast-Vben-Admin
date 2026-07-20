"""Audit persistence models owned by Platform infrastructure."""

import uuid
from datetime import datetime

from sqlalchemy import DateTime
from sqlmodel import Field, SQLModel

from app.core.clock import get_datetime_utc
from app.core.tenancy_constants import DEFAULT_TENANT_ID


class LoginLogBase(SQLModel):
    user_id: uuid.UUID | None = None
    email: str | None = Field(default=None, max_length=255, index=True)
    ip: str | None = Field(default=None, max_length=100)
    user_agent: str | None = Field(default=None, max_length=500)
    status: str = Field(max_length=20)
    failure_reason: str | None = Field(default=None, max_length=255)


class LoginLog(LoginLogBase, table=True):
    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    tenant_id: uuid.UUID = Field(
        default=DEFAULT_TENANT_ID,
        foreign_key="tenant.id",
        index=True,
        ondelete="CASCADE",
    )
    created_at: datetime | None = Field(
        default_factory=get_datetime_utc,
        sa_type=DateTime(timezone=True),  # type: ignore
        index=True,
    )


class LoginLogPublic(LoginLogBase):
    id: uuid.UUID
    tenant_id: uuid.UUID
    created_at: datetime | None = None


class LoginLogsPublic(SQLModel):
    items: list[LoginLogPublic]
    total: int
    page: int
    page_size: int


class OperationLogBase(SQLModel):
    user_id: uuid.UUID | None = Field(default=None, index=True)
    email: str | None = Field(default=None, max_length=255)
    module: str = Field(max_length=100)
    action: str = Field(max_length=100)
    method: str = Field(max_length=20)
    path: str = Field(max_length=500, index=True)
    status_code: int
    duration_ms: int
    ip: str | None = Field(default=None, max_length=100)
    user_agent: str | None = Field(default=None, max_length=500)
    request_summary: str | None = Field(default=None, max_length=1000)
    response_summary: str | None = Field(default=None, max_length=1000)


class OperationLog(OperationLogBase, table=True):
    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    tenant_id: uuid.UUID = Field(
        default=DEFAULT_TENANT_ID,
        foreign_key="tenant.id",
        index=True,
        ondelete="CASCADE",
    )
    created_at: datetime | None = Field(
        default_factory=get_datetime_utc,
        sa_type=DateTime(timezone=True),  # type: ignore
        index=True,
    )


class OperationLogPublic(OperationLogBase):
    id: uuid.UUID
    tenant_id: uuid.UUID
    created_at: datetime | None = None


class OperationLogsPublic(SQLModel):
    items: list[OperationLogPublic]
    total: int
    page: int
    page_size: int
