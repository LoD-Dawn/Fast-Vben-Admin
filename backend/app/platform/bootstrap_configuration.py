"""Default configuration and infrastructure records for a tenant."""

from sqlmodel import Session, select

from app.core.config import settings
from app.platform.core.configuration_models import (
    DictionaryItem,
    DictionaryType,
    SiteMessageTemplate,
    SystemSetting,
)
from app.platform.core.tenancy_models import Tenant
from app.platform.infra.file_models import FileStorageChannel
from app.platform.infra.mail_models import MailAccount, MailTemplate
from app.platform.infra.sms_models import SmsChannel, SmsTemplate


def ensure_dictionary_type(
    *,
    session: Session,
    tenant: Tenant,
    code: str,
    name: str,
    description: str | None = None,
) -> DictionaryType:
    type_ = session.exec(
        select(DictionaryType).where(
            DictionaryType.tenant_id == tenant.id,
            DictionaryType.code == code,
        )
    ).first()
    if type_:
        return type_

    type_ = DictionaryType(
        tenant_id=tenant.id,
        code=code,
        name=name,
        description=description,
    )
    session.add(type_)
    session.flush()
    return type_


def ensure_dictionary_item(
    *,
    session: Session,
    type_: DictionaryType,
    label: str,
    value: str,
    color: str | None = None,
    sort: int = 0,
) -> DictionaryItem:
    item = session.exec(
        select(DictionaryItem).where(
            DictionaryItem.tenant_id == type_.tenant_id,
            DictionaryItem.type_id == type_.id,
            DictionaryItem.value == value,
        )
    ).first()
    if item:
        return item

    item = DictionaryItem(
        tenant_id=type_.tenant_id,
        type_id=type_.id,
        label=label,
        value=value,
        color=color,
        sort=sort,
    )
    session.add(item)
    session.flush()
    return item


def seed_dictionaries(*, session: Session, tenant: Tenant) -> None:
    user_status = ensure_dictionary_type(
        session=session,
        tenant=tenant,
        code="user_status",
        name="用户状态",
        description="用户启用状态",
    )
    ensure_dictionary_item(
        session=session, type_=user_status, label="启用", value="active", color="green"
    )
    ensure_dictionary_item(
        session=session, type_=user_status, label="禁用", value="inactive", color="red"
    )

    yes_no = ensure_dictionary_type(
        session=session,
        tenant=tenant,
        code="yes_no",
        name="是否",
        description="通用是否选项",
    )
    ensure_dictionary_item(session=session, type_=yes_no, label="是", value="yes")
    ensure_dictionary_item(
        session=session, type_=yes_no, label="否", value="no", sort=1
    )

    business_status = ensure_dictionary_type(
        session=session,
        tenant=tenant,
        code="business_status",
        name="业务状态",
        description="示例业务状态",
    )
    ensure_dictionary_item(
        session=session,
        type_=business_status,
        label="草稿",
        value="draft",
        color="default",
    )
    ensure_dictionary_item(
        session=session,
        type_=business_status,
        label="已发布",
        value="published",
        color="green",
        sort=1,
    )
    user_type = ensure_dictionary_type(
        session=session,
        tenant=tenant,
        code="user_type",
        name="用户类型",
        description="登录主体类型",
    )
    ensure_dictionary_item(
        session=session, type_=user_type, label="管理后台", value="admin"
    )
    ensure_dictionary_item(
        session=session, type_=user_type, label="移动端", value="member", sort=1
    )

    oauth2_grant_type = ensure_dictionary_type(
        session=session,
        tenant=tenant,
        code="system_oauth2_grant_type",
        name="OAuth 2.0 授权类型",
        description="OAuth 2.0 客户端授权模式",
    )
    for sort, value in enumerate(
        [
            "authorization_code",
            "refresh_token",
            "password",
            "client_credentials",
            "implicit",
        ]
    ):
        ensure_dictionary_item(
            session=session,
            type_=oauth2_grant_type,
            label=value,
            value=value,
            sort=sort,
        )

    social_type = ensure_dictionary_type(
        session=session,
        tenant=tenant,
        code="system_social_type",
        name="社交类型",
        description="第三方登录平台类型",
    )
    social_options = [
        ("gitee", "Gitee"),
        ("dingtalk", "钉钉"),
        ("wechat_open", "微信开放平台"),
        ("wechat_mp", "微信公众平台"),
        ("wechat_mini", "微信小程序"),
        ("wechat_work", "企业微信"),
    ]
    for sort, (value, label) in enumerate(social_options):
        ensure_dictionary_item(
            session=session,
            type_=social_type,
            label=label,
            value=value,
            sort=sort,
        )


def ensure_setting(
    *,
    session: Session,
    tenant: Tenant,
    key: str,
    name: str,
    value: str,
    value_type: str,
    group: str,
    description: str | None = None,
    is_public: bool = False,
    is_system: bool = False,
) -> SystemSetting:
    setting = session.exec(
        select(SystemSetting).where(
            SystemSetting.tenant_id == tenant.id,
            SystemSetting.key == key,
        )
    ).first()
    if setting:
        return setting

    setting = SystemSetting(
        tenant_id=tenant.id,
        key=key,
        name=name,
        value=value,
        value_type=value_type,
        group=group,
        description=description,
        is_public=is_public,
        is_system=is_system,
    )
    session.add(setting)
    session.flush()
    return setting


def seed_settings(*, session: Session, tenant: Tenant) -> None:
    ensure_setting(
        session=session,
        tenant=tenant,
        key="system.name",
        name="系统名称",
        value="Fast Vben Admin",
        value_type="string",
        group="system",
        description="显示在后台中的系统名称",
        is_public=True,
        is_system=True,
    )
    ensure_setting(
        session=session,
        tenant=tenant,
        key="system.default_page_size",
        name="默认分页大小",
        value="20",
        value_type="number",
        group="system",
        is_public=True,
        is_system=True,
    )
    ensure_setting(
        session=session,
        tenant=tenant,
        key="auth.allow_register",
        name="是否开放注册",
        value="false",
        value_type="boolean",
        group="auth",
        description="MVP 默认关闭公开注册",
        is_public=True,
        is_system=True,
    )
    ensure_setting(
        session=session,
        tenant=tenant,
        key="upload.max_size_mb",
        name="上传大小限制 MB",
        value="10",
        value_type="number",
        group="upload",
        is_public=False,
        is_system=True,
    )
    ensure_setting(
        session=session,
        tenant=tenant,
        key="upload.allowed_extensions",
        name="允许上传扩展名",
        value=settings.UPLOAD_ALLOWED_EXTENSIONS,
        value_type="string",
        group="upload",
        is_public=False,
        is_system=True,
    )
    ensure_setting(
        session=session,
        tenant=tenant,
        key="upload.default_public",
        name="默认公开访问",
        value="false",
        value_type="boolean",
        group="upload",
        is_public=False,
        is_system=True,
    )
    ensure_setting(
        session=session,
        tenant=tenant,
        key="upload.presigned_url_expire_seconds",
        name="下载链接有效期秒数",
        value=str(settings.S3_PRESIGNED_URL_EXPIRE_SECONDS),
        value_type="number",
        group="upload",
        is_public=False,
        is_system=True,
    )


def seed_storage_channels(*, session: Session, tenant: Tenant) -> None:
    existing_default = session.exec(
        select(FileStorageChannel).where(
            FileStorageChannel.tenant_id == tenant.id,
            FileStorageChannel.is_default,
        )
    ).first()
    if existing_default:
        return

    provider = settings.STORAGE_PROVIDER
    channel = FileStorageChannel(
        tenant_id=tenant.id,
        name="本地存储" if provider == "local" else "默认对象存储",
        code="local" if provider == "local" else "default-s3",
        provider=provider,
        endpoint_url=settings.S3_ENDPOINT_URL,
        region=settings.S3_REGION,
        bucket=settings.S3_BUCKET,
        access_key_id=settings.S3_ACCESS_KEY_ID,
        secret_access_key=settings.S3_SECRET_ACCESS_KEY,
        object_prefix=settings.S3_OBJECT_PREFIX,
        addressing_style=settings.S3_ADDRESSING_STYLE,
        auto_create_bucket=settings.S3_AUTO_CREATE_BUCKET,
        is_default=True,
        is_active=True,
        remark="由环境变量初始化，可在后台调整。",
    )
    session.add(channel)
    session.flush()


def seed_sms_channels(*, session: Session, tenant: Tenant) -> None:
    debug_channel = session.exec(
        select(SmsChannel).where(
            SmsChannel.tenant_id == tenant.id,
            SmsChannel.code == "debug",
        )
    ).first()
    if not debug_channel:
        debug_channel = SmsChannel(
            tenant_id=tenant.id,
            name="本地调试渠道",
            code="debug",
            provider="debug",
            signature="系统通知",
            is_default=True,
            is_active=True,
            remark="仅记录发送结果，不会向真实手机号发送短信。",
        )
        session.add(debug_channel)
        session.flush()

    sample_template = session.exec(
        select(SmsTemplate).where(
            SmsTemplate.tenant_id == tenant.id,
            SmsTemplate.code == "verify_code",
        )
    ).first()
    if not sample_template:
        session.add(
            SmsTemplate(
                tenant_id=tenant.id,
                type="verification",
                code="verify_code",
                name="验证码",
                content="您的验证码为 {code}，5 分钟内有效。",
                params="code",
                remark="系统内置演示模板，可用于验证短信渠道和日志。",
                channel_id=debug_channel.id,
                channel_code=debug_channel.code,
                is_active=True,
            )
        )
        session.flush()


def seed_mail_accounts(*, session: Session, tenant: Tenant) -> None:
    if not settings.SMTP_HOST or not settings.EMAILS_FROM_EMAIL:
        return

    default_account = session.exec(
        select(MailAccount).where(
            MailAccount.tenant_id == tenant.id,
            MailAccount.code == "default",
        )
    ).first()
    if not default_account:
        default_account = MailAccount(
            tenant_id=tenant.id,
            name="系统邮箱账号",
            code="default",
            email=settings.EMAILS_FROM_EMAIL,
            username=settings.SMTP_USER,
            password=settings.SMTP_PASSWORD,
            host=settings.SMTP_HOST,
            port=settings.SMTP_PORT,
            ssl_enable=settings.SMTP_SSL,
            starttls_enable=settings.SMTP_TLS,
            is_default=True,
            is_active=True,
            remark="由环境变量初始化，可在后台调整。",
        )
        session.add(default_account)
        session.flush()

    sample_template = session.exec(
        select(MailTemplate).where(
            MailTemplate.tenant_id == tenant.id,
            MailTemplate.code == "welcome_mail",
        )
    ).first()
    if not sample_template:
        session.add(
            MailTemplate(
                tenant_id=tenant.id,
                code="welcome_mail",
                name="欢迎邮件",
                account_id=default_account.id,
                account_code=default_account.code,
                nickname=settings.EMAILS_FROM_NAME,
                title="欢迎加入 {project}",
                content="<p>您好，{name}。</p><p>欢迎使用 {project}。</p>",
                params="project,name",
                remark="系统内置演示模板，可用于验证邮箱账号和日志。",
                is_active=True,
            )
        )
        session.flush()


def seed_site_message_templates(*, session: Session, tenant: Tenant) -> None:
    welcome_template = session.exec(
        select(SiteMessageTemplate).where(
            SiteMessageTemplate.tenant_id == tenant.id,
            SiteMessageTemplate.code == "system_notice",
        )
    ).first()
    if not welcome_template:
        session.add(
            SiteMessageTemplate(
                tenant_id=tenant.id,
                code="system_notice",
                name="通知公告",
                sender_name="通知公告",
                content="尊敬的用户，{title}",
                type="notice",
                params="title",
                remark="系统内置演示模板，可用于验证站内信发送和列表。",
                is_active=True,
            )
        )
        session.flush()
