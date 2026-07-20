"""File persistence models owned by Platform infrastructure."""

import uuid
from datetime import datetime

from sqlalchemy import DateTime, UniqueConstraint
from sqlmodel import Field, SQLModel

from app.core.clock import get_datetime_utc
from app.core.tenancy_constants import DEFAULT_TENANT_ID


class FileAssetBase(SQLModel):
    original_name: str = Field(max_length=255)
    stored_name: str = Field(max_length=255)
    content_type: str | None = Field(default=None, max_length=100)
    extension: str | None = Field(default=None, max_length=20)
    size: int
    sha256: str = Field(max_length=64, index=True)
    storage_provider: str = Field(default="local", max_length=50)
    storage_path: str = Field(max_length=500)
    public_url: str | None = Field(default=None, max_length=500)
    uploader_id: uuid.UUID | None = Field(default=None, index=True)
    is_public: bool = False


class FileAsset(FileAssetBase, table=True):
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


class FileAssetPublic(FileAssetBase):
    id: uuid.UUID
    tenant_id: uuid.UUID
    created_at: datetime | None = None


class FileAssetsPublic(SQLModel):
    items: list[FileAssetPublic]
    total: int
    page: int
    page_size: int


class FileStorageChannelBase(SQLModel):
    name: str = Field(min_length=1, max_length=100)
    code: str = Field(min_length=1, max_length=100, index=True)
    provider: str = Field(default="local", max_length=50)
    endpoint_url: str | None = Field(default=None, max_length=500)
    region: str | None = Field(default=None, max_length=100)
    bucket: str | None = Field(default=None, max_length=255)
    access_key_id: str | None = Field(default=None, max_length=255)
    secret_access_key: str | None = Field(default=None, max_length=500)
    object_prefix: str | None = Field(default=None, max_length=255)
    addressing_style: str = Field(default="auto", max_length=20)
    auto_create_bucket: bool = False
    is_default: bool = False
    is_active: bool = True
    remark: str | None = Field(default=None, max_length=255)


class FileStorageChannel(FileStorageChannelBase, table=True):
    __table_args__ = (
        UniqueConstraint(
            "tenant_id",
            "code",
            name="uq_filestoragechannel_tenant_code",
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


class FileStorageChannelCreate(FileStorageChannelBase):
    pass


class FileStorageChannelUpdate(SQLModel):
    name: str | None = Field(default=None, min_length=1, max_length=100)
    code: str | None = Field(default=None, min_length=1, max_length=100)
    provider: str | None = Field(default=None, max_length=50)
    endpoint_url: str | None = Field(default=None, max_length=500)
    region: str | None = Field(default=None, max_length=100)
    bucket: str | None = Field(default=None, max_length=255)
    access_key_id: str | None = Field(default=None, max_length=255)
    secret_access_key: str | None = Field(default=None, max_length=500)
    object_prefix: str | None = Field(default=None, max_length=255)
    addressing_style: str | None = Field(default=None, max_length=20)
    auto_create_bucket: bool | None = None
    is_default: bool | None = None
    is_active: bool | None = None
    remark: str | None = Field(default=None, max_length=255)


class FileStorageChannelPublic(FileStorageChannelBase):
    id: uuid.UUID
    tenant_id: uuid.UUID
    secret_access_key: str | None = None
    created_at: datetime | None = None
    updated_at: datetime | None = None


class FileStorageChannelsPublic(SQLModel):
    items: list[FileStorageChannelPublic]
    total: int
    page: int
    page_size: int


class FileDownloadUrl(SQLModel):
    url: str
    expires_in: int | None = None


class StorageConfigPublic(SQLModel):
    provider: str
    channel_id: uuid.UUID | None = None
    channel_name: str | None = None
    max_size_mb: int
    allowed_extensions: str
    default_public: bool = False
    s3_bucket: str | None = None
    s3_endpoint_url: str | None = None
    presigned_url_expire_seconds: int | None = None


class UploadConfigPublic(SQLModel):
    max_size_mb: int
    allowed_extensions: str
    default_public: bool
    presigned_url_expire_seconds: int


class UploadConfigUpdate(SQLModel):
    max_size_mb: int | None = Field(default=None, ge=1, le=1024)
    allowed_extensions: str | None = Field(default=None, max_length=1000)
    default_public: bool | None = None
    presigned_url_expire_seconds: int | None = Field(default=None, ge=60, le=86_400)
