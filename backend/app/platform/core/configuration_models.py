"""Platform configuration, dictionary, notice, and site-message models."""

import uuid
from datetime import datetime

from sqlalchemy import DateTime, ForeignKeyConstraint, UniqueConstraint
from sqlmodel import Field, SQLModel

from app.core.clock import get_datetime_utc
from app.core.tenancy_constants import DEFAULT_TENANT_ID


class DictionaryTypeBase(SQLModel):
    code: str = Field(min_length=1, max_length=100, index=True)
    name: str = Field(min_length=1, max_length=100)
    description: str | None = Field(default=None, max_length=255)
    is_active: bool = True


class DictionaryTypeCreate(DictionaryTypeBase):
    pass


class DictionaryTypeUpdate(SQLModel):
    code: str | None = Field(default=None, min_length=1, max_length=100)
    name: str | None = Field(default=None, min_length=1, max_length=100)
    description: str | None = Field(default=None, max_length=255)
    is_active: bool | None = None


class DictionaryType(DictionaryTypeBase, table=True):
    __table_args__ = (
        UniqueConstraint("tenant_id", "code", name="uq_dictionarytype_tenant_code"),
        UniqueConstraint("id", "tenant_id", name="uq_dictionarytype_id_tenant_id"),
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


class DictionaryTypePublic(DictionaryTypeBase):
    id: uuid.UUID
    tenant_id: uuid.UUID
    created_at: datetime | None = None
    updated_at: datetime | None = None


class DictionaryTypesPublic(SQLModel):
    items: list[DictionaryTypePublic]
    total: int
    page: int
    page_size: int


class DictionaryItemBase(SQLModel):
    type_id: uuid.UUID
    label: str = Field(min_length=1, max_length=100)
    value: str = Field(min_length=1, max_length=100)
    color: str | None = Field(default=None, max_length=50)
    sort: int = 0
    is_active: bool = True
    extra_data: str | None = Field(default=None, max_length=1000)


class DictionaryItemCreate(DictionaryItemBase):
    pass


class DictionaryItemUpdate(SQLModel):
    type_id: uuid.UUID | None = None
    label: str | None = Field(default=None, min_length=1, max_length=100)
    value: str | None = Field(default=None, min_length=1, max_length=100)
    color: str | None = Field(default=None, max_length=50)
    sort: int | None = None
    is_active: bool | None = None
    extra_data: str | None = Field(default=None, max_length=1000)


class DictionaryItem(DictionaryItemBase, table=True):
    __table_args__ = (
        ForeignKeyConstraint(
            ["type_id", "tenant_id"],
            ["dictionarytype.id", "dictionarytype.tenant_id"],
            ondelete="CASCADE",
        ),
        UniqueConstraint(
            "tenant_id",
            "type_id",
            "value",
            name="uq_dictionaryitem_tenant_type_value",
        ),
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


class DictionaryItemPublic(DictionaryItemBase):
    id: uuid.UUID
    tenant_id: uuid.UUID
    created_at: datetime | None = None
    updated_at: datetime | None = None


class DictionaryItemsPublic(SQLModel):
    items: list[DictionaryItemPublic]
    total: int
    page: int
    page_size: int


class SystemSettingBase(SQLModel):
    key: str = Field(min_length=1, max_length=100, index=True)
    name: str = Field(min_length=1, max_length=100)
    value: str = Field(default="", max_length=2000)
    value_type: str = Field(default="string", max_length=20)
    group: str = Field(default="default", max_length=100)
    description: str | None = Field(default=None, max_length=255)
    is_public: bool = False
    is_system: bool = False


class SystemSettingCreate(SystemSettingBase):
    pass


class SystemSettingUpdate(SQLModel):
    name: str | None = Field(default=None, min_length=1, max_length=100)
    value: str | None = Field(default=None, max_length=2000)
    value_type: str | None = Field(default=None, max_length=20)
    group: str | None = Field(default=None, max_length=100)
    description: str | None = Field(default=None, max_length=255)
    is_public: bool | None = None
    is_system: bool | None = None


class SystemSetting(SystemSettingBase, table=True):
    __table_args__ = (
        UniqueConstraint("tenant_id", "key", name="uq_systemsetting_tenant_key"),
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


class SystemSettingPublic(SystemSettingBase):
    id: uuid.UUID
    tenant_id: uuid.UUID
    created_at: datetime | None = None
    updated_at: datetime | None = None


class SystemSettingsPublic(SQLModel):
    items: list[SystemSettingPublic]
    total: int
    page: int
    page_size: int


class NoticeBase(SQLModel):
    title: str = Field(min_length=1, max_length=200)
    content: str = Field(min_length=1, max_length=10000)
    type: str = Field(default="notice", max_length=50)
    priority: int = 0
    status: str = Field(default="draft", max_length=20, index=True)
    published_at: datetime | None = Field(  # type: ignore
        default=None,
        sa_type=DateTime(timezone=True),
        index=True,
    )


class NoticeCreate(SQLModel):
    title: str = Field(min_length=1, max_length=200)
    content: str = Field(min_length=1, max_length=10000)
    type: str = Field(default="notice", max_length=50)
    priority: int = 0


class NoticeUpdate(SQLModel):
    title: str | None = Field(default=None, min_length=1, max_length=200)
    content: str | None = Field(default=None, min_length=1, max_length=10000)
    type: str | None = Field(default=None, max_length=50)
    priority: int | None = None
    status: str | None = Field(default=None, max_length=20)


class Notice(NoticeBase, table=True):
    __table_args__ = (
        UniqueConstraint("id", "tenant_id", name="uq_notice_id_tenant_id"),
    )

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    tenant_id: uuid.UUID = Field(
        default=DEFAULT_TENANT_ID,
        foreign_key="tenant.id",
        index=True,
        ondelete="CASCADE",
    )
    created_by: uuid.UUID | None = Field(
        default=None, foreign_key="user.id", ondelete="SET NULL"
    )
    created_at: datetime | None = Field(
        default_factory=get_datetime_utc,
        sa_type=DateTime(timezone=True),  # type: ignore
        index=True,
    )
    updated_at: datetime | None = Field(
        default_factory=get_datetime_utc,
        sa_type=DateTime(timezone=True),  # type: ignore
    )


class NoticePublic(NoticeBase):
    id: uuid.UUID
    tenant_id: uuid.UUID
    created_by: uuid.UUID | None = None
    created_at: datetime | None = None
    updated_at: datetime | None = None


class NoticesPublic(SQLModel):
    items: list[NoticePublic]
    total: int
    page: int
    page_size: int


class UserMessageBase(SQLModel):
    user_id: uuid.UUID = Field(index=True)
    notice_id: uuid.UUID | None = Field(default=None, index=True)
    template_id: uuid.UUID | None = Field(
        default=None,
        index=True,
    )
    template_code: str | None = Field(default=None, max_length=100, index=True)
    template_name: str | None = Field(default=None, max_length=100)
    sender_name: str | None = Field(default=None, max_length=100)
    template_params: str | None = Field(default=None, max_length=4000)
    title: str = Field(min_length=1, max_length=200)
    content: str = Field(min_length=1, max_length=10000)
    type: str = Field(default="notice", max_length=50)
    is_read: bool = False
    read_at: datetime | None = Field(default=None, sa_type=DateTime(timezone=True))  # type: ignore


class UserMessage(UserMessageBase, table=True):
    __table_args__ = (
        ForeignKeyConstraint(
            ["user_id", "tenant_id"],
            ["tenantmembership.user_id", "tenantmembership.tenant_id"],
            ondelete="CASCADE",
        ),
        ForeignKeyConstraint(
            ["notice_id", "tenant_id"],
            ["notice.id", "notice.tenant_id"],
        ),
        ForeignKeyConstraint(
            ["template_id", "tenant_id"],
            ["sitemessagetemplate.id", "sitemessagetemplate.tenant_id"],
        ),
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
        index=True,
    )


class UserMessagePublic(UserMessageBase):
    id: uuid.UUID
    tenant_id: uuid.UUID
    created_at: datetime | None = None


class UserMessagesPublic(SQLModel):
    items: list[UserMessagePublic]
    total: int
    page: int
    page_size: int


class SiteMessageTemplateBase(SQLModel):
    name: str = Field(min_length=1, max_length=100)
    code: str = Field(min_length=1, max_length=100, index=True)
    sender_name: str = Field(default="系统通知", min_length=1, max_length=100)
    content: str = Field(min_length=1, max_length=10_000)
    type: str = Field(default="notification", max_length=50)
    is_active: bool = True
    remark: str | None = Field(default=None, max_length=255)


class SiteMessageTemplate(SiteMessageTemplateBase, table=True):
    __table_args__ = (
        UniqueConstraint(
            "tenant_id",
            "code",
            name="uq_sitemessagetemplate_tenant_code",
        ),
        UniqueConstraint(
            "id",
            "tenant_id",
            name="uq_sitemessagetemplate_id_tenant_id",
        ),
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


class SiteMessageTemplateCreate(SiteMessageTemplateBase):
    pass


class SiteMessageTemplateUpdate(SQLModel):
    name: str | None = Field(default=None, min_length=1, max_length=100)
    code: str | None = Field(default=None, min_length=1, max_length=100)
    sender_name: str | None = Field(default=None, min_length=1, max_length=100)
    content: str | None = Field(default=None, min_length=1, max_length=10_000)
    type: str | None = Field(default=None, max_length=50)
    is_active: bool | None = None
    remark: str | None = Field(default=None, max_length=255)


class SiteMessageTemplatePublic(SiteMessageTemplateBase):
    id: uuid.UUID
    tenant_id: uuid.UUID
    params: str
    created_at: datetime | None = None
    updated_at: datetime | None = None


class SiteMessageTemplatesPublic(SQLModel):
    items: list[SiteMessageTemplatePublic]
    total: int
    page: int
    page_size: int


class SiteMessageSendRequest(SQLModel):
    user_id: uuid.UUID
    template_params: dict[str, str] = Field(default_factory=dict)


class SiteMessagePublic(UserMessagePublic):
    user_email: str | None = None
    user_full_name: str | None = None


class SiteMessagesPublic(SQLModel):
    items: list[SiteMessagePublic]
    total: int
    page: int
    page_size: int
