import uuid
from datetime import datetime
from typing import Literal

from pydantic import EmailStr
from sqlalchemy import DateTime, ForeignKeyConstraint, UniqueConstraint
from sqlmodel import Field, SQLModel

from app.core.clock import get_datetime_utc
from app.core.tenancy_constants import DEFAULT_TENANT_ID


class UserIdentityBase(SQLModel):
    email: EmailStr = Field(unique=True, index=True, max_length=255)
    mobile: str | None = Field(default=None, unique=True, index=True, max_length=32)
    is_active: bool = True
    is_superuser: bool = False
    full_name: str | None = Field(default=None, max_length=255)
    avatar_url: str | None = Field(default=None, max_length=500)


class UserBase(UserIdentityBase):
    department_id: uuid.UUID | None = None


# Properties to receive via API on creation
class UserCreate(UserBase):
    password: str = Field(min_length=8, max_length=128)


class UserRegister(SQLModel):
    email: EmailStr = Field(max_length=255)
    mobile: str | None = Field(default=None, max_length=32)
    password: str = Field(min_length=8, max_length=128)
    full_name: str | None = Field(default=None, max_length=255)


class SmsCodeRequest(SQLModel):
    tenant_code: str = Field(min_length=1, max_length=100)
    mobile: str = Field(min_length=11, max_length=32)
    scene: Literal["login", "register"] = "login"


class SmsCodeSent(SQLModel):
    message: str
    retry_after_seconds: int
    debug_code: str | None = None


class SmsLoginRequest(SQLModel):
    tenant_code: str = Field(min_length=1, max_length=100)
    mobile: str = Field(min_length=11, max_length=32)
    code: str = Field(min_length=6, max_length=6)


class RegistrationStatus(SQLModel):
    enabled: bool


class QrCodeLoginCreate(SQLModel):
    tenant_code: str = Field(min_length=1, max_length=100)


class QrCodeLoginChallenge(SQLModel):
    challenge_id: uuid.UUID
    scan_token: str
    poll_token: str
    expires_in: int


class QrCodeLoginStatusRequest(SQLModel):
    challenge_id: uuid.UUID
    poll_token: str = Field(min_length=32, max_length=255)


class QrCodeLoginStatus(SQLModel):
    status: Literal["pending", "confirmed"]
    expires_in: int


class QrCodeLoginConfirmRequest(SQLModel):
    challenge_id: uuid.UUID
    scan_token: str = Field(min_length=32, max_length=255)


class QrCodeLoginConfirmResult(SQLModel):
    message: str
    tenant_name: str
    user_name: str


class QrCodeLoginExchangeRequest(SQLModel):
    challenge_id: uuid.UUID
    poll_token: str = Field(min_length=32, max_length=255)


# Properties to receive via API on update, all are optional
class UserUpdate(SQLModel):
    email: EmailStr | None = Field(default=None, max_length=255)
    mobile: str | None = Field(default=None, max_length=32)
    is_active: bool | None = None
    is_superuser: bool | None = None
    full_name: str | None = Field(default=None, max_length=255)
    department_id: uuid.UUID | None = None
    password: str | None = Field(default=None, min_length=8, max_length=128)


class UserUpdateMe(SQLModel):
    full_name: str | None = Field(default=None, max_length=255)
    email: EmailStr | None = Field(default=None, max_length=255)


class MasterDataAnonymizeRequest(SQLModel):
    reason: str = Field(min_length=1, max_length=500)


class UpdatePassword(SQLModel):
    current_password: str = Field(min_length=8, max_length=128)
    new_password: str = Field(min_length=8, max_length=128)


class UserMfaEnable(SQLModel):
    code: str = Field(min_length=6, max_length=16)


class UserMfaEnableResult(SQLModel):
    message: str
    recovery_codes: list[str]


class UserMfaDisable(SQLModel):
    current_password: str = Field(min_length=8, max_length=128)
    code: str = Field(min_length=6, max_length=16)


# Database model, database table inferred from class name
class User(UserIdentityBase, table=True):
    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    hashed_password: str
    mfa_enabled: bool = Field(default=False, nullable=False)
    mfa_secret_encrypted: str | None = Field(default=None, max_length=500)
    mfa_recovery_code_hashes: str | None = Field(default=None, max_length=2000)
    mfa_confirmed_at: datetime | None = Field(
        default=None,
        sa_type=DateTime(timezone=True),  # type: ignore
    )
    created_at: datetime | None = Field(
        default_factory=get_datetime_utc,
        sa_type=DateTime(timezone=True),  # type: ignore
    )
    updated_at: datetime | None = Field(
        default_factory=get_datetime_utc,
        sa_type=DateTime(timezone=True),  # type: ignore
    )
    archived_at: datetime | None = Field(
        default=None,
        sa_type=DateTime(timezone=True),
        index=True,  # type: ignore
    )
    anonymized_at: datetime | None = Field(
        default=None,
        sa_type=DateTime(timezone=True),
        index=True,  # type: ignore
    )


# Properties to return via API, id is always required
class UserPublic(UserBase):
    id: uuid.UUID
    created_at: datetime | None = None
    updated_at: datetime | None = None


class UsersPublic(SQLModel):
    items: list[UserPublic]
    total: int
    page: int
    page_size: int


class UserMfaStatus(SQLModel):
    enabled: bool
    pending_setup: bool = False
    method: str | None = None
    confirmed_at: datetime | None = None
    recovery_codes_remaining: int = 0


class UserMfaSetup(SQLModel):
    secret: str
    otpauth_uri: str
    issuer: str
    account_name: str


class UserSession(SQLModel, table=True):
    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    user_id: uuid.UUID = Field(
        foreign_key="user.id", index=True, nullable=False, ondelete="CASCADE"
    )
    tenant_id: uuid.UUID = Field(
        foreign_key="tenant.id", index=True, nullable=False, ondelete="RESTRICT"
    )
    token_jti: str = Field(max_length=64, unique=True, index=True)
    ip: str | None = Field(default=None, max_length=100)
    user_agent: str | None = Field(default=None, max_length=500)
    created_at: datetime | None = Field(
        default_factory=get_datetime_utc,
        sa_type=DateTime(timezone=True),  # type: ignore
    )
    last_active_at: datetime | None = Field(
        default_factory=get_datetime_utc,
        sa_type=DateTime(timezone=True),  # type: ignore
    )
    expires_at: datetime = Field(sa_type=DateTime(timezone=True))  # type: ignore
    revoked_at: datetime | None = Field(default=None, sa_type=DateTime(timezone=True))  # type: ignore


class OAuth2ClientBase(SQLModel):
    client_id: str = Field(min_length=1, max_length=100, unique=True, index=True)
    client_secret: str | None = Field(default=None, max_length=500)
    name: str = Field(min_length=1, max_length=100)
    logo: str | None = Field(default=None, max_length=500)
    description: str | None = Field(default=None, max_length=500)
    access_token_validity_seconds: int = Field(default=7200, ge=60)
    refresh_token_validity_seconds: int = Field(default=2_592_000, ge=60)
    authorized_grant_types: str = Field(
        default="authorization_code,refresh_token", max_length=500
    )
    scopes: str | None = Field(default="read,write", max_length=500)
    auto_approve_scopes: str | None = Field(default=None, max_length=500)
    redirect_uris: str | None = Field(default=None, max_length=1000)
    authorities: str | None = Field(default=None, max_length=500)
    resource_ids: str | None = Field(default=None, max_length=500)
    additional_information: str | None = Field(default=None, max_length=2000)
    is_active: bool = True


class OAuth2Client(OAuth2ClientBase, table=True):
    __table_args__ = (
        UniqueConstraint(
            "tenant_id",
            "client_id",
            name="uq_oauth2client_tenant_client_id",
        ),
        UniqueConstraint("id", "tenant_id", name="uq_oauth2client_id_tenant_id"),
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


class OAuth2ClientCreate(OAuth2ClientBase):
    pass


class OAuth2ClientUpdate(SQLModel):
    current_password: str | None = Field(default=None, min_length=8, max_length=128)
    client_id: str | None = Field(default=None, min_length=1, max_length=100)
    client_secret: str | None = Field(default=None, max_length=500)
    name: str | None = Field(default=None, min_length=1, max_length=100)
    logo: str | None = Field(default=None, max_length=500)
    description: str | None = Field(default=None, max_length=500)
    access_token_validity_seconds: int | None = Field(default=None, ge=60)
    refresh_token_validity_seconds: int | None = Field(default=None, ge=60)
    authorized_grant_types: str | None = Field(default=None, max_length=500)
    scopes: str | None = Field(default=None, max_length=500)
    auto_approve_scopes: str | None = Field(default=None, max_length=500)
    redirect_uris: str | None = Field(default=None, max_length=1000)
    authorities: str | None = Field(default=None, max_length=500)
    resource_ids: str | None = Field(default=None, max_length=500)
    additional_information: str | None = Field(default=None, max_length=2000)
    is_active: bool | None = None


class OAuth2ClientPublic(OAuth2ClientBase):
    id: uuid.UUID
    tenant_id: uuid.UUID
    client_secret: str | None = None
    created_at: datetime | None = None
    updated_at: datetime | None = None


class OAuth2ClientsPublic(SQLModel):
    items: list[OAuth2ClientPublic]
    total: int
    page: int
    page_size: int


class OAuth2AccessToken(SQLModel, table=True):
    __table_args__ = (
        ForeignKeyConstraint(
            ["client_id", "tenant_id"],
            ["oauth2client.client_id", "oauth2client.tenant_id"],
        ),
    )

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    tenant_id: uuid.UUID = Field(
        default=DEFAULT_TENANT_ID,
        foreign_key="tenant.id",
        index=True,
        ondelete="CASCADE",
    )
    access_token: str | None = Field(
        default=None, max_length=500, unique=True, index=True
    )
    refresh_token: str | None = Field(default=None, max_length=500, index=True)
    access_token_hash: str | None = Field(
        default=None, max_length=128, unique=True, index=True
    )
    refresh_token_hash: str | None = Field(default=None, max_length=128, index=True)
    refresh_expires_at: datetime | None = Field(
        default=None,
        sa_type=DateTime(timezone=True),  # type: ignore
    )
    token_family_id: uuid.UUID | None = Field(default=None, index=True)
    user_id: uuid.UUID | None = Field(
        default=None, foreign_key="user.id", index=True, ondelete="SET NULL"
    )
    user_email: str | None = Field(default=None, max_length=255)
    user_full_name: str | None = Field(default=None, max_length=255)
    client_id: str = Field(max_length=100, index=True)
    scopes: str | None = Field(default=None, max_length=500)
    expires_at: datetime = Field(sa_type=DateTime(timezone=True))  # type: ignore
    created_at: datetime | None = Field(
        default_factory=get_datetime_utc,
        sa_type=DateTime(timezone=True),  # type: ignore
    )
    revoked_at: datetime | None = Field(default=None, sa_type=DateTime(timezone=True))  # type: ignore


class OAuth2AccessTokenPublic(SQLModel):
    id: uuid.UUID
    tenant_id: uuid.UUID
    access_token: str | None = None
    refresh_token: str | None = None
    user_id: uuid.UUID | None = None
    user_email: str | None = None
    user_full_name: str | None = None
    client_id: str
    scopes: str | None = None
    expires_at: datetime
    created_at: datetime | None = None
    revoked_at: datetime | None = None


class OAuth2AccessTokensPublic(SQLModel):
    items: list[OAuth2AccessTokenPublic]
    total: int
    page: int
    page_size: int


class OAuth2AuthorizationCode(SQLModel, table=True):
    __table_args__ = (
        ForeignKeyConstraint(
            ["client_id", "tenant_id"],
            ["oauth2client.client_id", "oauth2client.tenant_id"],
        ),
    )

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    tenant_id: uuid.UUID = Field(
        default=DEFAULT_TENANT_ID,
        foreign_key="tenant.id",
        index=True,
        ondelete="CASCADE",
    )
    code_hash: str = Field(max_length=128, unique=True, index=True)
    client_id: str = Field(max_length=100, index=True)
    user_id: uuid.UUID = Field(foreign_key="user.id", index=True, ondelete="CASCADE")
    redirect_uri: str = Field(max_length=1000)
    scopes: str | None = Field(default=None, max_length=500)
    code_challenge: str = Field(max_length=128)
    code_challenge_method: str = Field(default="S256", max_length=10)
    expires_at: datetime = Field(sa_type=DateTime(timezone=True))  # type: ignore
    created_at: datetime | None = Field(
        default_factory=get_datetime_utc,
        sa_type=DateTime(timezone=True),  # type: ignore
    )
    used_at: datetime | None = Field(default=None, sa_type=DateTime(timezone=True))  # type: ignore


class EnterpriseOidcAuthorizationState(SQLModel, table=True):
    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    state_hash: str = Field(max_length=128, unique=True, index=True)
    code_verifier: str = Field(max_length=128)
    nonce: str = Field(max_length=128)
    expires_at: datetime = Field(sa_type=DateTime(timezone=True))  # type: ignore
    created_at: datetime | None = Field(
        default_factory=get_datetime_utc,
        sa_type=DateTime(timezone=True),  # type: ignore
    )
    consumed_at: datetime | None = Field(default=None, sa_type=DateTime(timezone=True))  # type: ignore


class EnterpriseOidcIdentity(SQLModel, table=True):
    __table_args__ = (
        UniqueConstraint(
            "provider", "subject", name="uq_enterpriseoidcidentity_provider_subject"
        ),
    )

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    provider: str = Field(default="enterprise_oidc", max_length=100)
    subject: str = Field(max_length=500)
    user_id: uuid.UUID = Field(foreign_key="user.id", index=True, ondelete="CASCADE")
    created_at: datetime | None = Field(
        default_factory=get_datetime_utc,
        sa_type=DateTime(timezone=True),  # type: ignore
    )
    updated_at: datetime | None = Field(
        default_factory=get_datetime_utc,
        sa_type=DateTime(timezone=True),  # type: ignore
    )


class EnterpriseOidcLoginTicket(SQLModel, table=True):
    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    ticket_hash: str = Field(max_length=128, unique=True, index=True)
    user_id: uuid.UUID = Field(foreign_key="user.id", index=True, ondelete="CASCADE")
    expires_at: datetime = Field(sa_type=DateTime(timezone=True))  # type: ignore
    created_at: datetime | None = Field(
        default_factory=get_datetime_utc,
        sa_type=DateTime(timezone=True),  # type: ignore
    )
    consumed_at: datetime | None = Field(default=None, sa_type=DateTime(timezone=True))  # type: ignore


class EnterpriseOidcStatus(SQLModel):
    enabled: bool
    login_url: str | None = None


class EnterpriseOidcTicketExchange(SQLModel):
    ticket: str = Field(min_length=32, max_length=500)


class SocialClientBase(SQLModel):
    name: str = Field(min_length=1, max_length=100)
    social_type: str = Field(min_length=1, max_length=50, index=True)
    user_type: str = Field(default="admin", max_length=50)
    client_id: str = Field(min_length=1, max_length=255)
    client_secret: str | None = Field(default=None, max_length=500)
    agent_id: str | None = Field(default=None, max_length=100)
    is_active: bool = True
    remark: str | None = Field(default=None, max_length=255)


class SocialClient(SocialClientBase, table=True):
    __table_args__ = (
        UniqueConstraint(
            "tenant_id",
            "social_type",
            "user_type",
            name="uq_socialclient_tenant_social_type_user_type",
        ),
        UniqueConstraint("id", "tenant_id", name="uq_socialclient_id_tenant_id"),
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


class SocialClientCreate(SocialClientBase):
    pass


class SocialClientUpdate(SQLModel):
    current_password: str | None = Field(default=None, min_length=8, max_length=128)
    name: str | None = Field(default=None, min_length=1, max_length=100)
    social_type: str | None = Field(default=None, min_length=1, max_length=50)
    user_type: str | None = Field(default=None, max_length=50)
    client_id: str | None = Field(default=None, min_length=1, max_length=255)
    client_secret: str | None = Field(default=None, max_length=500)
    agent_id: str | None = Field(default=None, max_length=100)
    is_active: bool | None = None
    remark: str | None = Field(default=None, max_length=255)


class SocialClientPublic(SocialClientBase):
    id: uuid.UUID
    tenant_id: uuid.UUID
    client_secret: str | None = None
    created_at: datetime | None = None
    updated_at: datetime | None = None


class SocialClientsPublic(SQLModel):
    items: list[SocialClientPublic]
    total: int
    page: int
    page_size: int


class SocialUser(SQLModel, table=True):
    __table_args__ = (
        ForeignKeyConstraint(
            ["user_id", "tenant_id"],
            ["tenantmembership.user_id", "tenantmembership.tenant_id"],
        ),
        ForeignKeyConstraint(
            ["social_client_id", "tenant_id"],
            ["socialclient.id", "socialclient.tenant_id"],
        ),
        UniqueConstraint(
            "tenant_id",
            "type",
            "openid",
            name="uq_socialuser_tenant_type_openid",
        ),
    )

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    tenant_id: uuid.UUID = Field(
        default=DEFAULT_TENANT_ID,
        foreign_key="tenant.id",
        index=True,
        ondelete="CASCADE",
    )
    type: str = Field(max_length=50, index=True)
    openid: str = Field(max_length=255, index=True)
    unionid: str | None = Field(default=None, max_length=255)
    nickname: str | None = Field(default=None, max_length=255)
    avatar: str | None = Field(default=None, max_length=500)
    token: str | None = Field(default=None, max_length=1000)
    raw_token_info: str | None = Field(default=None, max_length=4000)
    raw_user_info: str | None = Field(default=None, max_length=4000)
    code: str | None = Field(default=None, max_length=255)
    state: str | None = Field(default=None, max_length=255)
    user_id: uuid.UUID | None = Field(
        default=None, foreign_key="user.id", index=True, ondelete="SET NULL"
    )
    social_client_id: uuid.UUID | None = Field(
        default=None, foreign_key="socialclient.id", index=True, ondelete="SET NULL"
    )
    created_at: datetime | None = Field(
        default_factory=get_datetime_utc,
        sa_type=DateTime(timezone=True),  # type: ignore
    )
    updated_at: datetime | None = Field(
        default_factory=get_datetime_utc,
        sa_type=DateTime(timezone=True),  # type: ignore
    )


class SocialUserPublic(SQLModel):
    id: uuid.UUID
    tenant_id: uuid.UUID
    type: str
    openid: str
    unionid: str | None = None
    nickname: str | None = None
    avatar: str | None = None
    token: str | None = None
    raw_token_info: str | None = None
    raw_user_info: str | None = None
    code: str | None = None
    state: str | None = None
    user_id: uuid.UUID | None = None
    social_client_id: uuid.UUID | None = None
    user_email: str | None = None
    user_full_name: str | None = None
    created_at: datetime | None = None
    updated_at: datetime | None = None


class SocialUsersPublic(SQLModel):
    items: list[SocialUserPublic]
    total: int
    page: int
    page_size: int


class SocialUserBind(SQLModel):
    user_id: uuid.UUID
