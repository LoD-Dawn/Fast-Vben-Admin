"""Mail persistence models owned by Platform infrastructure."""

import uuid
from datetime import datetime

from pydantic import EmailStr
from sqlalchemy import DateTime, ForeignKeyConstraint, UniqueConstraint
from sqlmodel import Field, SQLModel

from app.core.clock import get_datetime_utc
from app.core.tenancy_constants import DEFAULT_TENANT_ID


class MailAccountBase(SQLModel):
    name: str = Field(min_length=1, max_length=100)
    code: str = Field(min_length=1, max_length=100, index=True)
    email: EmailStr = Field(max_length=255)
    username: str | None = Field(default=None, max_length=255)
    password: str | None = Field(default=None, max_length=500)
    host: str = Field(min_length=1, max_length=255)
    port: int = Field(default=465, ge=1, le=65_535)
    ssl_enable: bool = True
    starttls_enable: bool = False
    is_default: bool = False
    is_active: bool = True
    remark: str | None = Field(default=None, max_length=255)


class MailAccount(MailAccountBase, table=True):
    __table_args__ = (
        UniqueConstraint("tenant_id", "code", name="uq_mailaccount_tenant_code"),
        UniqueConstraint("id", "tenant_id", name="uq_mailaccount_id_tenant_id"),
    )

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
    )
    updated_at: datetime | None = Field(
        default_factory=get_datetime_utc,
        sa_type=DateTime(timezone=True),  # type: ignore
    )


class MailAccountCreate(MailAccountBase):
    pass


class MailAccountUpdate(SQLModel):
    name: str | None = Field(default=None, min_length=1, max_length=100)
    code: str | None = Field(default=None, min_length=1, max_length=100)
    email: EmailStr | None = Field(default=None, max_length=255)
    username: str | None = Field(default=None, max_length=255)
    password: str | None = Field(default=None, max_length=500)
    host: str | None = Field(default=None, min_length=1, max_length=255)
    port: int | None = Field(default=None, ge=1, le=65_535)
    ssl_enable: bool | None = None
    starttls_enable: bool | None = None
    is_default: bool | None = None
    is_active: bool | None = None
    remark: str | None = Field(default=None, max_length=255)


class MailAccountPublic(MailAccountBase):
    id: uuid.UUID
    tenant_id: uuid.UUID
    password: str | None = None
    created_at: datetime | None = None
    updated_at: datetime | None = None


class MailAccountsPublic(SQLModel):
    items: list[MailAccountPublic]
    total: int
    page: int
    page_size: int


class MailTemplateBase(SQLModel):
    name: str = Field(min_length=1, max_length=100)
    code: str = Field(min_length=1, max_length=100, index=True)
    account_id: uuid.UUID | None = Field(default=None, index=True)
    nickname: str | None = Field(default=None, max_length=100)
    title: str = Field(min_length=1, max_length=255)
    content: str = Field(min_length=1, max_length=20_000)
    is_active: bool = True
    remark: str | None = Field(default=None, max_length=255)


class MailTemplate(MailTemplateBase, table=True):
    __table_args__ = (
        ForeignKeyConstraint(
            ["account_id", "tenant_id"],
            ["mailaccount.id", "mailaccount.tenant_id"],
        ),
        UniqueConstraint("tenant_id", "code", name="uq_mailtemplate_tenant_code"),
        UniqueConstraint("id", "tenant_id", name="uq_mailtemplate_id_tenant_id"),
    )

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    tenant_id: uuid.UUID = Field(
        default=DEFAULT_TENANT_ID,
        foreign_key="tenant.id",
        index=True,
        ondelete="CASCADE",
    )
    account_code: str | None = Field(default=None, max_length=100)
    params: str = Field(default="", max_length=500)
    created_at: datetime | None = Field(
        default_factory=get_datetime_utc,
        sa_type=DateTime(timezone=True),  # type: ignore
    )
    updated_at: datetime | None = Field(
        default_factory=get_datetime_utc,
        sa_type=DateTime(timezone=True),  # type: ignore
    )


class MailTemplateCreate(MailTemplateBase):
    pass


class MailTemplateUpdate(SQLModel):
    name: str | None = Field(default=None, min_length=1, max_length=100)
    code: str | None = Field(default=None, min_length=1, max_length=100)
    account_id: uuid.UUID | None = None
    nickname: str | None = Field(default=None, max_length=100)
    title: str | None = Field(default=None, min_length=1, max_length=255)
    content: str | None = Field(default=None, min_length=1, max_length=20_000)
    is_active: bool | None = None
    remark: str | None = Field(default=None, max_length=255)


class MailTemplatePublic(MailTemplateBase):
    id: uuid.UUID
    tenant_id: uuid.UUID
    account_code: str | None = None
    params: str
    created_at: datetime | None = None
    updated_at: datetime | None = None


class MailTemplatesPublic(SQLModel):
    items: list[MailTemplatePublic]
    total: int
    page: int
    page_size: int


class MailSendRequest(SQLModel):
    to_email: EmailStr
    template_params: dict[str, str] = Field(default_factory=dict)


class MailLog(SQLModel, table=True):
    __table_args__ = (
        ForeignKeyConstraint(
            ["account_id", "tenant_id"],
            ["mailaccount.id", "mailaccount.tenant_id"],
        ),
        ForeignKeyConstraint(
            ["template_id", "tenant_id"],
            ["mailtemplate.id", "mailtemplate.tenant_id"],
        ),
    )

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    tenant_id: uuid.UUID = Field(
        default=DEFAULT_TENANT_ID,
        foreign_key="tenant.id",
        index=True,
        ondelete="CASCADE",
    )
    account_id: uuid.UUID | None = None
    account_code: str | None = Field(default=None, max_length=100)
    account_name: str | None = Field(default=None, max_length=100)
    template_id: uuid.UUID | None = None
    template_code: str | None = Field(default=None, max_length=100)
    template_name: str | None = Field(default=None, max_length=100)
    from_email: str = Field(max_length=255)
    from_name: str | None = Field(default=None, max_length=100)
    to_email: str = Field(max_length=255, index=True)
    title: str = Field(max_length=255)
    content: str = Field(max_length=20_000)
    template_params: str | None = Field(default=None, max_length=4000)
    send_status: str = Field(default="pending", max_length=20)
    sent_at: datetime | None = Field(  # type: ignore
        default=None,
        sa_type=DateTime(timezone=True),
        index=True,
    )
    message_id: str | None = Field(default=None, max_length=255)
    send_code: str | None = Field(default=None, max_length=100)
    send_message: str | None = Field(default=None, max_length=2000)
    created_at: datetime | None = Field(
        default_factory=get_datetime_utc,
        sa_type=DateTime(timezone=True),  # type: ignore
        index=True,
    )


class MailLogPublic(SQLModel):
    id: uuid.UUID
    tenant_id: uuid.UUID
    account_id: uuid.UUID | None = None
    account_code: str | None = None
    account_name: str | None = None
    template_id: uuid.UUID | None = None
    template_code: str | None = None
    template_name: str | None = None
    from_email: str
    from_name: str | None = None
    to_email: str
    title: str
    content: str
    template_params: str | None = None
    send_status: str
    sent_at: datetime | None = None
    message_id: str | None = None
    send_code: str | None = None
    send_message: str | None = None
    created_at: datetime | None = None


class MailLogsPublic(SQLModel):
    items: list[MailLogPublic]
    total: int
    page: int
    page_size: int
