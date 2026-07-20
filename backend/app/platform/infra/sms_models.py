"""SMS persistence models owned by Platform infrastructure."""

import uuid
from datetime import datetime

from sqlalchemy import DateTime, ForeignKeyConstraint, UniqueConstraint
from sqlmodel import Field, SQLModel

from app.core.clock import get_datetime_utc
from app.core.tenancy_constants import DEFAULT_TENANT_ID


class SmsChannelBase(SQLModel):
    name: str = Field(min_length=1, max_length=100)
    code: str = Field(min_length=1, max_length=100, index=True)
    provider: str = Field(default="debug", max_length=50)
    signature: str = Field(min_length=1, max_length=100)
    api_key: str | None = Field(default=None, max_length=500)
    api_secret: str | None = Field(default=None, max_length=500)
    callback_url: str | None = Field(default=None, max_length=500)
    is_default: bool = False
    is_active: bool = True
    remark: str | None = Field(default=None, max_length=255)


class SmsChannel(SmsChannelBase, table=True):
    __table_args__ = (
        UniqueConstraint("tenant_id", "code", name="uq_smschannel_tenant_code"),
        UniqueConstraint("id", "tenant_id", name="uq_smschannel_id_tenant_id"),
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


class SmsChannelCreate(SmsChannelBase):
    pass


class SmsChannelUpdate(SQLModel):
    name: str | None = Field(default=None, min_length=1, max_length=100)
    code: str | None = Field(default=None, min_length=1, max_length=100)
    provider: str | None = Field(default=None, max_length=50)
    signature: str | None = Field(default=None, min_length=1, max_length=100)
    api_key: str | None = Field(default=None, max_length=500)
    api_secret: str | None = Field(default=None, max_length=500)
    callback_url: str | None = Field(default=None, max_length=500)
    is_default: bool | None = None
    is_active: bool | None = None
    remark: str | None = Field(default=None, max_length=255)


class SmsChannelPublic(SmsChannelBase):
    id: uuid.UUID
    tenant_id: uuid.UUID
    api_secret: str | None = None
    created_at: datetime | None = None
    updated_at: datetime | None = None


class SmsChannelsPublic(SQLModel):
    items: list[SmsChannelPublic]
    total: int
    page: int
    page_size: int


class SmsTemplateBase(SQLModel):
    type: str = Field(default="notification", max_length=50)
    code: str = Field(min_length=1, max_length=100, index=True)
    name: str = Field(min_length=1, max_length=100)
    content: str = Field(min_length=1, max_length=1000)
    remark: str | None = Field(default=None, max_length=255)
    api_template_id: str | None = Field(default=None, max_length=100)
    channel_id: uuid.UUID | None = Field(default=None, index=True)
    channel_code: str | None = Field(default=None, max_length=100)
    is_active: bool = True


class SmsTemplate(SmsTemplateBase, table=True):
    __table_args__ = (
        ForeignKeyConstraint(
            ["channel_id", "tenant_id"],
            ["smschannel.id", "smschannel.tenant_id"],
        ),
        UniqueConstraint("tenant_id", "code", name="uq_smstemplate_tenant_code"),
        UniqueConstraint("id", "tenant_id", name="uq_smstemplate_id_tenant_id"),
    )

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    tenant_id: uuid.UUID = Field(
        default=DEFAULT_TENANT_ID,
        foreign_key="tenant.id",
        index=True,
        ondelete="CASCADE",
    )
    params: str = Field(default="", max_length=500)
    created_at: datetime | None = Field(
        default_factory=get_datetime_utc,
        sa_type=DateTime(timezone=True),  # type: ignore
    )
    updated_at: datetime | None = Field(
        default_factory=get_datetime_utc,
        sa_type=DateTime(timezone=True),  # type: ignore
    )


class SmsTemplateCreate(SmsTemplateBase):
    pass


class SmsTemplateUpdate(SQLModel):
    type: str | None = Field(default=None, max_length=50)
    code: str | None = Field(default=None, min_length=1, max_length=100)
    name: str | None = Field(default=None, min_length=1, max_length=100)
    content: str | None = Field(default=None, min_length=1, max_length=1000)
    remark: str | None = Field(default=None, max_length=255)
    api_template_id: str | None = Field(default=None, max_length=100)
    channel_id: uuid.UUID | None = None
    is_active: bool | None = None


class SmsTemplatePublic(SmsTemplateBase):
    id: uuid.UUID
    tenant_id: uuid.UUID
    params: str
    created_at: datetime | None = None
    updated_at: datetime | None = None


class SmsTemplatesPublic(SQLModel):
    items: list[SmsTemplatePublic]
    total: int
    page: int
    page_size: int


class SmsSendRequest(SQLModel):
    mobile: str = Field(min_length=6, max_length=32)
    template_params: dict[str, str] = Field(default_factory=dict)


class SmsDeliveryCallback(SQLModel):
    request_id: str = Field(min_length=1, max_length=100)
    status: str = Field(min_length=1, max_length=20)
    message: str | None = Field(default=None, max_length=1000)


class SmsLog(SQLModel, table=True):
    __table_args__ = (
        ForeignKeyConstraint(
            ["channel_id", "tenant_id"],
            ["smschannel.id", "smschannel.tenant_id"],
        ),
        ForeignKeyConstraint(
            ["template_id", "tenant_id"],
            ["smstemplate.id", "smstemplate.tenant_id"],
        ),
    )

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    tenant_id: uuid.UUID = Field(
        default=DEFAULT_TENANT_ID,
        foreign_key="tenant.id",
        index=True,
        ondelete="CASCADE",
    )
    channel_id: uuid.UUID | None = None
    channel_code: str | None = Field(default=None, max_length=100)
    template_id: uuid.UUID | None = None
    template_code: str | None = Field(default=None, max_length=100)
    template_name: str | None = Field(default=None, max_length=100)
    template_type: str | None = Field(default=None, max_length=50)
    template_content: str = Field(max_length=1000)
    template_params: str | None = Field(default=None, max_length=2000)
    api_template_id: str | None = Field(default=None, max_length=100)
    mobile: str = Field(max_length=32, index=True)
    send_status: str = Field(default="success", max_length=20)
    sent_at: datetime | None = Field(
        default_factory=get_datetime_utc,
        sa_type=DateTime(timezone=True),  # type: ignore
        index=True,
    )
    api_send_code: str | None = Field(default=None, max_length=100)
    api_send_message: str | None = Field(default=None, max_length=1000)
    api_request_id: str | None = Field(default=None, max_length=100, index=True)
    api_serial_no: str | None = Field(default=None, max_length=100)
    receive_status: str = Field(default="pending", max_length=20)
    received_at: datetime | None = Field(default=None, sa_type=DateTime(timezone=True))  # type: ignore
    api_receive_code: str | None = Field(default=None, max_length=100)
    api_receive_message: str | None = Field(default=None, max_length=1000)
    created_at: datetime | None = Field(
        default_factory=get_datetime_utc,
        sa_type=DateTime(timezone=True),  # type: ignore
        index=True,
    )


class SmsLogPublic(SQLModel):
    id: uuid.UUID
    tenant_id: uuid.UUID
    channel_id: uuid.UUID | None = None
    channel_code: str | None = None
    template_id: uuid.UUID | None = None
    template_code: str | None = None
    template_name: str | None = None
    template_type: str | None = None
    template_content: str
    template_params: str | None = None
    api_template_id: str | None = None
    mobile: str
    send_status: str
    sent_at: datetime | None = None
    api_send_code: str | None = None
    api_send_message: str | None = None
    api_request_id: str | None = None
    api_serial_no: str | None = None
    receive_status: str
    received_at: datetime | None = None
    api_receive_code: str | None = None
    api_receive_message: str | None = None
    created_at: datetime | None = None


class SmsLogsPublic(SQLModel):
    items: list[SmsLogPublic]
    total: int
    page: int
    page_size: int
