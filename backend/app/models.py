import uuid

from sqlmodel import Field, SQLModel

from app.platform.core.authorization_models import (
    DataScope,
    Department,
    DepartmentBase,
    DepartmentCreate,
    DepartmentPublic,
    DepartmentsPublic,
    DepartmentUpdate,
    Menu,
    MenuBase,
    MenuCreate,
    MenuPublic,
    MenusPublic,
    MenuUpdate,
    Post,
    PostBase,
    PostCreate,
    PostPublic,
    PostsPublic,
    PostUpdate,
    Role,
    RoleBase,
    RoleCreate,
    RoleDataScopeDepartment,
    RoleMenu,
    RoleMenuUpdate,
    RolePublic,
    RolesPublic,
    RoleUpdate,
    UserPost,
    UserPostUpdate,
    UserRole,
    UserRoleUpdate,
)
from app.platform.core.configuration_models import (
    DictionaryItem,
    DictionaryItemBase,
    DictionaryItemCreate,
    DictionaryItemPublic,
    DictionaryItemsPublic,
    DictionaryItemUpdate,
    DictionaryType,
    DictionaryTypeBase,
    DictionaryTypeCreate,
    DictionaryTypePublic,
    DictionaryTypesPublic,
    DictionaryTypeUpdate,
    Notice,
    NoticeBase,
    NoticeCreate,
    NoticePublic,
    NoticesPublic,
    NoticeUpdate,
    SiteMessagePublic,
    SiteMessageSendRequest,
    SiteMessagesPublic,
    SiteMessageTemplate,
    SiteMessageTemplateBase,
    SiteMessageTemplateCreate,
    SiteMessageTemplatePublic,
    SiteMessageTemplatesPublic,
    SiteMessageTemplateUpdate,
    SystemSetting,
    SystemSettingBase,
    SystemSettingCreate,
    SystemSettingPublic,
    SystemSettingsPublic,
    SystemSettingUpdate,
    UserMessage,
    UserMessageBase,
    UserMessagePublic,
    UserMessagesPublic,
)
from app.platform.core.identity_models import (
    EnterpriseOidcAuthorizationState,
    EnterpriseOidcIdentity,
    EnterpriseOidcLoginTicket,
    EnterpriseOidcStatus,
    EnterpriseOidcTicketExchange,
    MasterDataAnonymizeRequest,
    OAuth2AccessToken,
    OAuth2AccessTokenPublic,
    OAuth2AccessTokensPublic,
    OAuth2AuthorizationCode,
    OAuth2Client,
    OAuth2ClientBase,
    OAuth2ClientCreate,
    OAuth2ClientPublic,
    OAuth2ClientsPublic,
    OAuth2ClientUpdate,
    QrCodeLoginChallenge,
    QrCodeLoginConfirmRequest,
    QrCodeLoginConfirmResult,
    QrCodeLoginCreate,
    QrCodeLoginExchangeRequest,
    QrCodeLoginStatus,
    QrCodeLoginStatusRequest,
    RegistrationStatus,
    SmsCodeRequest,
    SmsCodeSent,
    SmsLoginRequest,
    SocialClient,
    SocialClientBase,
    SocialClientCreate,
    SocialClientPublic,
    SocialClientsPublic,
    SocialClientUpdate,
    SocialUser,
    SocialUserBind,
    SocialUserPublic,
    SocialUsersPublic,
    UpdatePassword,
    User,
    UserBase,
    UserCreate,
    UserIdentityBase,
    UserMfaDisable,
    UserMfaEnable,
    UserMfaEnableResult,
    UserMfaSetup,
    UserMfaStatus,
    UserPublic,
    UserRegister,
    UserSession,
    UsersPublic,
    UserUpdate,
    UserUpdateMe,
)
from app.platform.core.runtime_models import (
    CapabilityBinding,
    CapabilityBindingStatus,
    EventDelivery,
    EventDeliveryStatus,
    EventDeliveryTargetType,
    InboxReceipt,
    ModuleDesiredState,
    ModuleDesiredStateUpdate,
    ModuleEntitlementEffect,
    ModuleObservedState,
    ModuleRegistry,
    ModuleRegistryPublic,
    ModuleStateAudit,
    OutboxEvent,
    OutboxEventPublic,
    OutboxEventStatus,
    TenantModule,
    TenantModuleEntitlementOverride,
    TenantModuleEntitlementOverrideCreate,
    TenantModuleUpdate,
    TenantPlanModule,
    TenantPlanModuleUpdate,
)
from app.platform.core.tenancy_models import (
    Tenant,
    TenantBase,
    TenantCreate,
    TenantInitializationTemplate,
    TenantInitializationTemplateBase,
    TenantInitializationTemplateCreate,
    TenantInitializationTemplatePublic,
    TenantInitializationTemplatesPublic,
    TenantInitializationTemplateUpdate,
    TenantLifecycleAction,
    TenantLifecycleActionRequest,
    TenantLifecycleStatus,
    TenantMembership,
    TenantMembershipPublic,
    TenantMenuSyncResult,
    TenantPlan,
    TenantPlanBase,
    TenantPlanCreate,
    TenantPlanMenu,
    TenantPlanMenuUpdate,
    TenantPlanProfile,
    TenantPlanPublic,
    TenantPlansPublic,
    TenantPlanUpdate,
    TenantProfile,
    TenantPublic,
    TenantRegistrationRequest,
    TenantsPublic,
    TenantSwitchRequest,
    TenantUpdate,
    TenantUsagePublic,
)
from app.platform.infra.audit_models import (
    LoginLog,
    LoginLogBase,
    LoginLogPublic,
    LoginLogsPublic,
    OperationLog,
    OperationLogBase,
    OperationLogPublic,
    OperationLogsPublic,
)
from app.platform.infra.file_models import (
    FileAsset,
    FileAssetBase,
    FileAssetPublic,
    FileAssetsPublic,
    FileDownloadUrl,
    FileStorageChannel,
    FileStorageChannelBase,
    FileStorageChannelCreate,
    FileStorageChannelPublic,
    FileStorageChannelsPublic,
    FileStorageChannelUpdate,
    StorageConfigPublic,
    UploadConfigPublic,
    UploadConfigUpdate,
)
from app.platform.infra.mail_models import (
    MailAccount,
    MailAccountBase,
    MailAccountCreate,
    MailAccountPublic,
    MailAccountsPublic,
    MailAccountUpdate,
    MailLog,
    MailLogPublic,
    MailLogsPublic,
    MailSendRequest,
    MailTemplate,
    MailTemplateBase,
    MailTemplateCreate,
    MailTemplatePublic,
    MailTemplatesPublic,
    MailTemplateUpdate,
)
from app.platform.infra.sms_models import (
    SmsChannel,
    SmsChannelBase,
    SmsChannelCreate,
    SmsChannelPublic,
    SmsChannelsPublic,
    SmsChannelUpdate,
    SmsDeliveryCallback,
    SmsLog,
    SmsLogPublic,
    SmsLogsPublic,
    SmsSendRequest,
    SmsTemplate,
    SmsTemplateBase,
    SmsTemplateCreate,
    SmsTemplatePublic,
    SmsTemplatesPublic,
    SmsTemplateUpdate,
)

# Transitional exports keep the historical aggregate-model import path stable.
PLATFORM_MODEL_COMPATIBILITY_EXPORTS = (
    UserIdentityBase,
    UserBase,
    UserCreate,
    UserRegister,
    SmsCodeRequest,
    SmsCodeSent,
    SmsLoginRequest,
    RegistrationStatus,
    QrCodeLoginCreate,
    QrCodeLoginChallenge,
    QrCodeLoginStatusRequest,
    QrCodeLoginStatus,
    QrCodeLoginConfirmRequest,
    QrCodeLoginConfirmResult,
    QrCodeLoginExchangeRequest,
    UserUpdate,
    UserUpdateMe,
    MasterDataAnonymizeRequest,
    UpdatePassword,
    UserMfaEnable,
    UserMfaEnableResult,
    UserMfaDisable,
    User,
    UserPublic,
    UsersPublic,
    UserMfaStatus,
    UserMfaSetup,
    UserSession,
    OAuth2ClientBase,
    OAuth2Client,
    OAuth2ClientCreate,
    OAuth2ClientUpdate,
    OAuth2ClientPublic,
    OAuth2ClientsPublic,
    OAuth2AccessToken,
    OAuth2AccessTokenPublic,
    OAuth2AccessTokensPublic,
    OAuth2AuthorizationCode,
    EnterpriseOidcAuthorizationState,
    EnterpriseOidcIdentity,
    EnterpriseOidcLoginTicket,
    EnterpriseOidcStatus,
    EnterpriseOidcTicketExchange,
    SocialClientBase,
    SocialClient,
    SocialClientCreate,
    SocialClientUpdate,
    SocialClientPublic,
    SocialClientsPublic,
    SocialUser,
    SocialUserPublic,
    SocialUsersPublic,
    SocialUserBind,
    DataScope,
    Department,
    DepartmentBase,
    DepartmentCreate,
    DepartmentPublic,
    DepartmentsPublic,
    DepartmentUpdate,
    Menu,
    MenuBase,
    MenuCreate,
    MenuPublic,
    MenusPublic,
    MenuUpdate,
    Post,
    PostBase,
    PostCreate,
    PostPublic,
    PostsPublic,
    PostUpdate,
    Role,
    RoleBase,
    RoleCreate,
    RoleDataScopeDepartment,
    RoleMenu,
    RoleMenuUpdate,
    RolePublic,
    RolesPublic,
    RoleUpdate,
    UserPost,
    UserPostUpdate,
    UserRole,
    UserRoleUpdate,
    DictionaryItem,
    DictionaryItemBase,
    DictionaryItemCreate,
    DictionaryItemPublic,
    DictionaryItemsPublic,
    DictionaryItemUpdate,
    DictionaryType,
    DictionaryTypeBase,
    DictionaryTypeCreate,
    DictionaryTypePublic,
    DictionaryTypesPublic,
    DictionaryTypeUpdate,
    Notice,
    NoticeBase,
    NoticeCreate,
    NoticePublic,
    NoticesPublic,
    NoticeUpdate,
    SiteMessagePublic,
    SiteMessageSendRequest,
    SiteMessagesPublic,
    SiteMessageTemplate,
    SiteMessageTemplateBase,
    SiteMessageTemplateCreate,
    SiteMessageTemplatePublic,
    SiteMessageTemplatesPublic,
    SiteMessageTemplateUpdate,
    SystemSetting,
    SystemSettingBase,
    SystemSettingCreate,
    SystemSettingPublic,
    SystemSettingsPublic,
    SystemSettingUpdate,
    UserMessage,
    UserMessageBase,
    UserMessagePublic,
    UserMessagesPublic,
    CapabilityBinding,
    CapabilityBindingStatus,
    EventDelivery,
    EventDeliveryStatus,
    EventDeliveryTargetType,
    InboxReceipt,
    ModuleDesiredState,
    ModuleDesiredStateUpdate,
    ModuleEntitlementEffect,
    ModuleObservedState,
    ModuleRegistry,
    ModuleRegistryPublic,
    ModuleStateAudit,
    OutboxEvent,
    OutboxEventPublic,
    OutboxEventStatus,
    TenantModule,
    TenantModuleEntitlementOverride,
    TenantModuleEntitlementOverrideCreate,
    TenantModuleUpdate,
    TenantPlanModule,
    TenantPlanModuleUpdate,
    Tenant,
    TenantBase,
    TenantCreate,
    TenantInitializationTemplate,
    TenantInitializationTemplateBase,
    TenantInitializationTemplateCreate,
    TenantInitializationTemplatePublic,
    TenantInitializationTemplatesPublic,
    TenantInitializationTemplateUpdate,
    TenantLifecycleAction,
    TenantLifecycleActionRequest,
    TenantLifecycleStatus,
    TenantMembership,
    TenantMembershipPublic,
    TenantMenuSyncResult,
    TenantPlan,
    TenantPlanBase,
    TenantPlanCreate,
    TenantPlanMenu,
    TenantPlanMenuUpdate,
    TenantPlanProfile,
    TenantPlanPublic,
    TenantPlansPublic,
    TenantPlanUpdate,
    TenantProfile,
    TenantPublic,
    TenantRegistrationRequest,
    TenantsPublic,
    TenantSwitchRequest,
    TenantUpdate,
    TenantUsagePublic,
    SmsChannel,
    SmsChannelBase,
    SmsChannelCreate,
    SmsChannelPublic,
    SmsChannelsPublic,
    SmsChannelUpdate,
    SmsDeliveryCallback,
    SmsLog,
    SmsLogPublic,
    SmsLogsPublic,
    SmsSendRequest,
    SmsTemplate,
    SmsTemplateBase,
    SmsTemplateCreate,
    SmsTemplatePublic,
    SmsTemplatesPublic,
    SmsTemplateUpdate,
    MailAccount,
    MailAccountBase,
    MailAccountCreate,
    MailAccountPublic,
    MailAccountsPublic,
    MailAccountUpdate,
    MailLog,
    MailLogPublic,
    MailLogsPublic,
    MailSendRequest,
    MailTemplate,
    MailTemplateBase,
    MailTemplateCreate,
    MailTemplatePublic,
    MailTemplatesPublic,
    MailTemplateUpdate,
    FileAsset,
    FileAssetBase,
    FileAssetPublic,
    FileAssetsPublic,
    FileDownloadUrl,
    FileStorageChannel,
    FileStorageChannelBase,
    FileStorageChannelCreate,
    FileStorageChannelPublic,
    FileStorageChannelsPublic,
    FileStorageChannelUpdate,
    StorageConfigPublic,
    UploadConfigPublic,
    UploadConfigUpdate,
    LoginLog,
    LoginLogBase,
    LoginLogPublic,
    LoginLogsPublic,
    OperationLog,
    OperationLogBase,
    OperationLogPublic,
    OperationLogsPublic,
)




# Global user identity properties


class DashboardOverview(SQLModel):
    user_count: int
    user_total: int
    login_count: int
    login_total: int
    file_count: int
    file_total: int
    operation_count: int
    operation_total: int


class DashboardHourlyTrend(SQLModel):
    hour: str
    login_count: int
    operation_count: int


class DashboardMonthlyVisit(SQLModel):
    month: str
    count: int


class DashboardNamedValue(SQLModel):
    name: str
    value: int


class DashboardRadarSeries(SQLModel):
    name: str
    values: list[int]


class DashboardAnalytics(SQLModel):
    overview: DashboardOverview
    hourly_trends: list[DashboardHourlyTrend]
    monthly_visits: list[DashboardMonthlyVisit]
    device_radar: list[DashboardRadarSeries]
    login_sources: list[DashboardNamedValue]
    module_distribution: list[DashboardNamedValue]


# Generic message
class Message(SQLModel):
    message: str


# JSON payload containing access token
class Token(SQLModel):
    access_token: str
    token_type: str = "bearer"
    tenant_id: uuid.UUID


class LoginCaptchaChallenge(SQLModel):
    captcha_id: str
    challenge_text: str
    expires_in: int


# Contents of JWT token
class TokenPayload(SQLModel):
    sub: str | None = None
    jti: str | None = None
    tenant_id: uuid.UUID | None = None


class NewPassword(SQLModel):
    token: str
    new_password: str = Field(min_length=8, max_length=128)


class HealthDependencyStatus(SQLModel):
    status: str
    enabled: bool = True
    degraded: bool = False
    available: bool | None = None


class HealthStatus(SQLModel):
    ok: bool
    degraded: bool = False
    database: HealthDependencyStatus
    redis: HealthDependencyStatus
