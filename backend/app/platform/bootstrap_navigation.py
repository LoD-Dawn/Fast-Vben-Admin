"""Platform navigation seed and legacy menu migration service."""

from sqlmodel import Session, select

from app.core.clock import get_datetime_utc
from app.platform.core.authorization_models import Menu, RoleMenu


def ensure_menu(
    *,
    session: Session,
    title: str,
    type: str,
    sort: int,
    parent_id=None,
    route_path: str | None = None,
    route_name: str | None = None,
    component: str | None = None,
    icon: str | None = None,
    permission_code: str | None = None,
    is_visible: bool = True,
    is_active: bool = True,
) -> Menu:
    menu = None
    if permission_code:
        menu = session.exec(
            select(Menu).where(Menu.permission_code == permission_code)
        ).first()
    elif route_path:
        menu = session.exec(select(Menu).where(Menu.route_path == route_path)).first()

    if menu:
        changed = False
        for field, value in {
            "title": title,
            "type": type,
            "parent_id": parent_id,
            "route_path": route_path,
            "route_name": route_name,
            "component": component,
            "icon": icon,
            "sort": sort,
            "is_visible": is_visible,
            "is_active": is_active,
        }.items():
            if value is not None and getattr(menu, field) != value:
                setattr(menu, field, value)
                changed = True
        if changed:
            session.add(menu)
            session.flush()
        return menu

    menu = Menu(
        title=title,
        type=type,
        parent_id=parent_id,
        route_path=route_path,
        route_name=route_name,
        component=component,
        icon=icon,
        permission_code=permission_code,
        sort=sort,
        is_visible=is_visible,
        is_active=is_active,
    )
    session.add(menu)
    session.flush()
    return menu


def seed_menus(*, session: Session) -> list[Menu]:
    remove_obsolete_menus(session=session)
    dashboard = ensure_menu(
        session=session,
        title="menu.dashboard",
        type="menu",
        route_path="/dashboard",
        route_name="Dashboard",
        component="#/views/dashboard/analytics/index.vue",
        icon="lucide:layout-dashboard",
        permission_code="dashboard:view",
        sort=0,
    )
    system = ensure_menu(
        session=session,
        title="menu.system",
        type="directory",
        route_path="/system",
        route_name="System",
        icon="lucide:settings",
        sort=10,
    )
    tenant_center = ensure_menu(
        session=session,
        title="menu.systemTenantCenter",
        type="directory",
        parent_id=system.id,
        route_path="/system/tenant-center",
        route_name="SystemTenantCenter",
        icon="lucide:building",
        sort=5,
    )
    basic_settings = ensure_menu(
        session=session,
        title="menu.infrastructure",
        type="directory",
        route_path="/basic-settings",
        route_name="BasicSettings",
        icon="lucide:settings-2",
        sort=15,
    )
    tenants = ensure_menu(
        session=session,
        title="menu.systemTenants",
        type="menu",
        parent_id=tenant_center.id,
        route_path="/system/tenants",
        route_name="SystemTenants",
        component="#/views/system/tenants/index.vue",
        icon="lucide:building-2",
        permission_code="platform:tenant:list",
        sort=10,
    )
    tenant_plans = ensure_menu(
        session=session,
        title="menu.systemTenantPlans",
        type="menu",
        parent_id=tenant_center.id,
        route_path="/system/tenant-plans",
        route_name="SystemTenantPlans",
        component="#/views/system/tenant-plans/index.vue",
        icon="lucide:package",
        permission_code="platform:plan:list",
        sort=20,
    )
    tenant_templates = ensure_menu(
        session=session,
        title="menu.systemTenantTemplates",
        type="menu",
        parent_id=tenant_center.id,
        route_path="/system/tenant-templates",
        route_name="SystemTenantTemplates",
        component="#/views/system/tenant-templates/index.vue",
        icon="lucide:layout-template",
        permission_code="platform:template:list",
        sort=30,
    )
    users = ensure_menu(
        session=session,
        title="menu.systemUsers",
        type="menu",
        parent_id=system.id,
        route_path="/system/users",
        route_name="SystemUsers",
        component="#/views/system/users/index.vue",
        icon="lucide:users",
        permission_code="system:user:list",
        sort=10,
    )
    roles = ensure_menu(
        session=session,
        title="menu.systemRoles",
        type="menu",
        parent_id=system.id,
        route_path="/system/roles",
        route_name="SystemRoles",
        component="#/views/system/roles/index.vue",
        icon="lucide:shield-check",
        permission_code="system:role:list",
        sort=20,
    )
    menus = ensure_menu(
        session=session,
        title="menu.systemMenus",
        type="menu",
        parent_id=system.id,
        route_path="/system/menus",
        route_name="SystemMenus",
        component="#/views/system/menus/index.vue",
        icon="lucide:menu",
        permission_code="system:menu:list",
        sort=30,
    )
    departments = ensure_menu(
        session=session,
        title="menu.systemDepartments",
        type="menu",
        parent_id=system.id,
        route_path="/system/departments",
        route_name="SystemDepartments",
        component="#/views/system/departments/index.vue",
        icon="lucide:building-2",
        permission_code="system:department:list",
        sort=40,
    )
    posts = ensure_menu(
        session=session,
        title="menu.systemPosts",
        type="menu",
        parent_id=system.id,
        route_path="/system/posts",
        route_name="SystemPosts",
        component="#/views/system/posts/index.vue",
        icon="lucide:briefcase-business",
        permission_code="system:post:list",
        sort=50,
    )
    dictionaries = ensure_menu(
        session=session,
        title="menu.systemDictionaries",
        type="menu",
        parent_id=system.id,
        route_path="/system/dictionaries",
        route_name="SystemDictionaries",
        component="#/views/system/dictionaries/index.vue",
        icon="lucide:book-open",
        permission_code="system:dict:list",
        sort=60,
    )
    system_settings = ensure_menu(
        session=session,
        title="menu.systemSettings",
        type="menu",
        parent_id=basic_settings.id,
        route_path="/basic-settings/settings",
        route_name="SystemSettings",
        component="#/views/system/settings/index.vue",
        icon="lucide:sliders-horizontal",
        permission_code="system:setting:list",
        sort=10,
    )
    oauth2 = ensure_menu(
        session=session,
        title="menu.oauth2",
        type="directory",
        parent_id=system.id,
        route_path="/system/oauth2",
        route_name="OAuth2",
        icon="lucide:shield",
        sort=85,
    )
    oauth2_clients = ensure_menu(
        session=session,
        title="menu.oauth2Clients",
        type="menu",
        parent_id=oauth2.id,
        route_path="/system/oauth2/clients",
        route_name="OAuth2Clients",
        component="#/views/oauth2/clients/index.vue",
        icon="lucide:hard-drive",
        permission_code="system:oauth2-client:list",
        sort=10,
    )
    oauth2_tokens = ensure_menu(
        session=session,
        title="menu.oauth2Tokens",
        type="menu",
        parent_id=oauth2.id,
        route_path="/system/oauth2/tokens",
        route_name="OAuth2Tokens",
        component="#/views/oauth2/tokens/index.vue",
        icon="lucide:key-round",
        permission_code="system:oauth2-token:list",
        sort=20,
    )
    social = ensure_menu(
        session=session,
        title="menu.socialLogin",
        type="directory",
        parent_id=system.id,
        route_path="/system/social",
        route_name="SocialLogin",
        icon="lucide:rocket",
        sort=86,
    )
    social_clients = ensure_menu(
        session=session,
        title="menu.socialClients",
        type="menu",
        parent_id=social.id,
        route_path="/system/social/clients",
        route_name="SocialClients",
        component="#/views/social/clients/index.vue",
        icon="lucide:settings-2",
        permission_code="system:social-client:list",
        sort=10,
    )
    social_users = ensure_menu(
        session=session,
        title="menu.socialUsers",
        type="menu",
        parent_id=social.id,
        route_path="/system/social/users",
        route_name="SocialUsers",
        component="#/views/social/users/index.vue",
        icon="lucide:users-round",
        permission_code="system:social-user:list",
        sort=20,
    )
    migrate_directory_menu(
        session=session,
        parent=system,
        route_name="Logs",
        legacy_paths=("/logs",),
        target_path="/system/logs",
        sort=90,
    )
    logs = ensure_menu(
        session=session,
        title="menu.logs",
        type="directory",
        parent_id=system.id,
        route_path="/system/logs",
        route_name="Logs",
        icon="lucide:clipboard-list",
        sort=90,
    )
    login_logs = ensure_menu(
        session=session,
        title="menu.loginLogs",
        type="menu",
        parent_id=logs.id,
        route_path="/system/logs/login",
        route_name="LoginLogs",
        component="#/views/logs/login/index.vue",
        icon="lucide:log-in",
        permission_code="system:login-log:list",
        sort=10,
    )
    operation_logs = ensure_menu(
        session=session,
        title="menu.operationLogs",
        type="menu",
        parent_id=logs.id,
        route_path="/system/logs/operation",
        route_name="OperationLogs",
        component="#/views/logs/operation/index.vue",
        icon="lucide:history",
        permission_code="system:operation-log:list",
        sort=20,
    )
    migrate_directory_menu(
        session=session,
        parent=basic_settings,
        route_name="Files",
        legacy_paths=("/files", "/system/files"),
        target_path="/basic-settings/files",
        sort=20,
    )
    files = ensure_menu(
        session=session,
        title="menu.files",
        type="directory",
        parent_id=basic_settings.id,
        route_path="/basic-settings/files",
        route_name="Files",
        icon="lucide:folder",
        sort=20,
    )
    if files.component is not None or files.permission_code is not None:
        files.component = None
        files.permission_code = None
        session.add(files)
        session.flush()
    file_channels = ensure_menu(
        session=session,
        title="menu.fileChannels",
        type="menu",
        parent_id=files.id,
        route_path="/basic-settings/files/channels",
        route_name="FileChannels",
        component="#/views/files/channels/index.vue",
        icon="lucide:database",
        permission_code="system:file:channel:list",
        sort=10,
    )
    file_config = ensure_menu(
        session=session,
        title="menu.fileConfig",
        type="menu",
        parent_id=files.id,
        route_path="/basic-settings/files/config",
        route_name="FileConfig",
        component="#/views/files/config/index.vue",
        icon="lucide:settings-2",
        permission_code="system:file:config:list",
        sort=20,
    )
    file_list = ensure_menu(
        session=session,
        title="menu.fileList",
        type="menu",
        parent_id=files.id,
        route_path="/basic-settings/files/list",
        route_name="FileList",
        component="#/views/files/index.vue",
        icon="lucide:files",
        permission_code="system:file:list",
        sort=30,
    )
    message_center = ensure_menu(
        session=session,
        title="menu.messageCenter",
        type="directory",
        parent_id=system.id,
        route_path="/system/message-center",
        route_name="MessageCenter",
        icon="lucide:messages-square",
        sort=110,
    )
    notices = ensure_menu(
        session=session,
        title="menu.notices",
        type="menu",
        parent_id=message_center.id,
        route_path="/system/message-center/notices",
        route_name="Notices",
        component="#/views/notices/index.vue",
        icon="lucide:megaphone",
        permission_code="system:notice:list",
        sort=10,
    )
    messages = ensure_menu(
        session=session,
        title="menu.messages",
        type="menu",
        parent_id=message_center.id,
        route_path="/system/message-center/messages",
        route_name="Messages",
        component="#/views/messages/index.vue",
        icon="lucide:mail",
        permission_code="personal:message:list",
        sort=20,
    )
    site_messages = ensure_menu(
        session=session,
        title="menu.siteMessages",
        type="directory",
        parent_id=message_center.id,
        route_path="/system/message-center/site-messages",
        route_name="SiteMessages",
        component="#/views/_core/router-view.vue",
        icon="lucide:inbox",
        sort=30,
    )
    site_message_templates = ensure_menu(
        session=session,
        title="menu.siteMessageTemplates",
        type="menu",
        parent_id=site_messages.id,
        route_path="/system/message-center/site-messages/templates",
        route_name="SiteMessageTemplates",
        component="#/views/site-messages/templates/index.vue",
        icon="lucide:archive",
        permission_code="system:site-message-template:list",
        sort=10,
    )
    site_message_list = ensure_menu(
        session=session,
        title="menu.siteMessageList",
        type="menu",
        parent_id=site_messages.id,
        route_path="/system/message-center/site-messages/list",
        route_name="SiteMessageList",
        component="#/views/site-messages/messages/index.vue",
        icon="lucide:edit-3",
        permission_code="system:site-message:list",
        sort=20,
    )
    sms = ensure_menu(
        session=session,
        title="menu.sms",
        type="directory",
        parent_id=message_center.id,
        route_path="/system/message-center/sms",
        route_name="Sms",
        component="#/views/_core/router-view.vue",
        icon="lucide:message-square-more",
        sort=40,
    )
    sms_channels = ensure_menu(
        session=session,
        title="menu.smsChannels",
        type="menu",
        parent_id=sms.id,
        route_path="/system/message-center/sms/channels",
        route_name="SmsChannels",
        component="#/views/sms/channels/index.vue",
        icon="lucide:messages-square",
        permission_code="system:sms-channel:list",
        sort=10,
    )
    sms_templates = ensure_menu(
        session=session,
        title="menu.smsTemplates",
        type="menu",
        parent_id=sms.id,
        route_path="/system/message-center/sms/templates",
        route_name="SmsTemplates",
        component="#/views/sms/templates/index.vue",
        icon="lucide:scroll-text",
        permission_code="system:sms-template:list",
        sort=20,
    )
    sms_logs = ensure_menu(
        session=session,
        title="menu.smsLogs",
        type="menu",
        parent_id=sms.id,
        route_path="/system/message-center/sms/logs",
        route_name="SmsLogs",
        component="#/views/sms/logs/index.vue",
        icon="lucide:send",
        permission_code="system:sms-log:list",
        sort=30,
    )
    mail = ensure_menu(
        session=session,
        title="menu.mail",
        type="directory",
        parent_id=message_center.id,
        route_path="/system/message-center/mail",
        route_name="Mail",
        component="#/views/_core/router-view.vue",
        icon="lucide:mail",
        sort=50,
    )
    mail_accounts = ensure_menu(
        session=session,
        title="menu.mailAccounts",
        type="menu",
        parent_id=mail.id,
        route_path="/system/message-center/mail/accounts",
        route_name="MailAccounts",
        component="#/views/mail/accounts/index.vue",
        icon="lucide:mail-check",
        permission_code="system:mail-account:list",
        sort=10,
    )
    mail_templates = ensure_menu(
        session=session,
        title="menu.mailTemplates",
        type="menu",
        parent_id=mail.id,
        route_path="/system/message-center/mail/templates",
        route_name="MailTemplates",
        component="#/views/mail/templates/index.vue",
        icon="lucide:scroll-text",
        permission_code="system:mail-template:list",
        sort=20,
    )
    mail_logs = ensure_menu(
        session=session,
        title="menu.mailLogs",
        type="menu",
        parent_id=mail.id,
        route_path="/system/message-center/mail/logs",
        route_name="MailLogs",
        component="#/views/mail/logs/index.vue",
        icon="lucide:send",
        permission_code="system:mail-log:list",
        sort=30,
    )
    items = ensure_menu(
        session=session,
        title="menu.items",
        type="menu",
        route_path="/items",
        route_name="Items",
        component="#/modules/items/views/index.vue",
        icon="lucide:list-todo",
        permission_code="business:item:list",
        sort=20,
    )
    button_permissions = [
        (tenants.id, "新增租户", "platform:tenant:create", 6),
        (tenants.id, "编辑租户", "platform:tenant:update", 7),
        (tenants.id, "停用租户", "platform:tenant:delete", 8),
        (tenants.id, "生命周期操作", "platform:tenant:lifecycle", 9),
        (tenants.id, "同步租户菜单", "platform:tenant:sync-menu", 10),
        (tenant_plans.id, "新增套餐", "platform:plan:create", 9),
        (tenant_plans.id, "编辑套餐", "platform:plan:update", 10),
        (tenant_plans.id, "删除套餐", "platform:plan:delete", 11),
        (tenant_plans.id, "套餐菜单授权", "platform:plan:grant-menu", 12),
        (tenant_plans.id, "同步套餐菜单", "platform:plan:sync-menu", 13),
        (tenant_templates.id, "新增模板", "platform:template:create", 12),
        (tenant_templates.id, "编辑模板", "platform:template:update", 13),
        (tenant_templates.id, "删除模板", "platform:template:delete", 14),
        (users.id, "新增用户", "system:user:create", 11),
        (users.id, "编辑用户", "system:user:update", 12),
        (users.id, "删除用户", "system:user:delete", 13),
        (roles.id, "新增角色", "system:role:create", 21),
        (roles.id, "编辑角色", "system:role:update", 22),
        (roles.id, "删除角色", "system:role:delete", 23),
        (menus.id, "新增菜单", "system:menu:create", 31),
        (menus.id, "编辑菜单", "system:menu:update", 32),
        (menus.id, "删除菜单", "system:menu:delete", 33),
        (departments.id, "新增部门", "system:department:create", 41),
        (departments.id, "编辑部门", "system:department:update", 42),
        (departments.id, "删除部门", "system:department:delete", 43),
        (posts.id, "新增岗位", "system:post:create", 51),
        (posts.id, "编辑岗位", "system:post:update", 52),
        (posts.id, "删除岗位", "system:post:delete", 53),
        (dictionaries.id, "新增字典", "system:dict:create", 61),
        (dictionaries.id, "编辑字典", "system:dict:update", 62),
        (dictionaries.id, "删除字典", "system:dict:delete", 63),
        (system_settings.id, "编辑参数", "system:setting:update", 71),
        (oauth2_clients.id, "新增OAuth2客户端", "system:oauth2-client:create", 82),
        (oauth2_clients.id, "编辑OAuth2客户端", "system:oauth2-client:update", 83),
        (oauth2_clients.id, "删除OAuth2客户端", "system:oauth2-client:delete", 84),
        (oauth2_tokens.id, "吊销OAuth2令牌", "system:oauth2-token:delete", 85),
        (social_clients.id, "新增三方客户端", "system:social-client:create", 86),
        (social_clients.id, "编辑三方客户端", "system:social-client:update", 87),
        (social_clients.id, "删除三方客户端", "system:social-client:delete", 88),
        (file_list.id, "上传文件", "system:file:upload", 71),
        (file_list.id, "删除文件", "system:file:delete", 72),
        (file_channels.id, "新增存储渠道", "system:file:channel:create", 73),
        (file_channels.id, "编辑存储渠道", "system:file:channel:update", 74),
        (file_channels.id, "删除存储渠道", "system:file:channel:delete", 75),
        (file_config.id, "编辑上传配置", "system:file:config:update", 76),
        (notices.id, "新增公告", "system:notice:create", 81),
        (notices.id, "编辑公告", "system:notice:update", 82),
        (notices.id, "删除公告", "system:notice:delete", 83),
        (
            site_message_templates.id,
            "新增站内信模板",
            "system:site-message-template:create",
            84,
        ),
        (
            site_message_templates.id,
            "编辑站内信模板",
            "system:site-message-template:update",
            85,
        ),
        (
            site_message_templates.id,
            "删除站内信模板",
            "system:site-message-template:delete",
            86,
        ),
        (
            site_message_templates.id,
            "发送测试站内信",
            "system:site-message-template:send",
            87,
        ),
        (
            site_message_list.id,
            "删除站内信",
            "system:site-message:delete",
            88,
        ),
        (sms_channels.id, "新增短信渠道", "system:sms-channel:create", 91),
        (sms_channels.id, "编辑短信渠道", "system:sms-channel:update", 92),
        (sms_channels.id, "删除短信渠道", "system:sms-channel:delete", 93),
        (sms_templates.id, "新增短信模板", "system:sms-template:create", 94),
        (sms_templates.id, "编辑短信模板", "system:sms-template:update", 95),
        (sms_templates.id, "删除短信模板", "system:sms-template:delete", 96),
        (sms_templates.id, "发送测试短信", "system:sms-template:send", 97),
        (mail_accounts.id, "新增邮箱账号", "system:mail-account:create", 101),
        (mail_accounts.id, "编辑邮箱账号", "system:mail-account:update", 102),
        (mail_accounts.id, "删除邮箱账号", "system:mail-account:delete", 103),
        (mail_templates.id, "新增邮件模板", "system:mail-template:create", 104),
        (mail_templates.id, "编辑邮件模板", "system:mail-template:update", 105),
        (mail_templates.id, "删除邮件模板", "system:mail-template:delete", 106),
        (mail_templates.id, "发送测试邮件", "system:mail-template:send", 107),
        (mail_logs.id, "重发邮件", "system:mail-log:resend", 108),
        (items.id, "新增示例", "business:item:create", 51),
        (items.id, "编辑示例", "business:item:update", 52),
        (items.id, "删除示例", "business:item:delete", 53),
    ]
    buttons = [
        ensure_menu(
            session=session,
            title=title,
            type="button",
            parent_id=parent_id,
            permission_code=permission_code,
            sort=sort,
            is_visible=False,
        )
        for parent_id, title, permission_code, sort in button_permissions
    ]
    return [
        dashboard,
        system,
        tenant_center,
        basic_settings,
        tenants,
        tenant_plans,
        tenant_templates,
        users,
        roles,
        menus,
        departments,
        posts,
        dictionaries,
        system_settings,
        oauth2,
        oauth2_clients,
        oauth2_tokens,
        social,
        social_clients,
        social_users,
        message_center,
        logs,
        login_logs,
        operation_logs,
        files,
        file_channels,
        file_config,
        file_list,
        notices,
        messages,
        site_messages,
        site_message_templates,
        site_message_list,
        sms,
        sms_channels,
        sms_templates,
        sms_logs,
        mail,
        mail_accounts,
        mail_templates,
        mail_logs,
        items,
        *buttons,
    ]


def remove_obsolete_menus(*, session: Session) -> None:
    obsolete_route_paths = {
        "/system/codegen",
        "/system/online-users",
        "/system/operations",
        "/workflows",
    }
    obsolete_permission_prefixes = (
        "system:api-log:",
        "system:codegen:",
        "system:exception-log:",
        "system:scheduled-task:",
        "system:scheduled-task-log:",
        "system:session:",
        "system:translation:",
        "workflow:",
    )
    obsolete_menus = [
        menu
        for menu in session.exec(select(Menu)).all()
        if menu.route_path in obsolete_route_paths
        or (menu.route_path or "").startswith("/system/operations/")
        or (menu.component or "").startswith("#/views/operations/")
        or (menu.component or "").startswith("#/views/system/online-users/")
        or (menu.permission_code or "").startswith(obsolete_permission_prefixes)
    ]
    if not obsolete_menus:
        return

    obsolete_menu_ids = {menu.id for menu in obsolete_menus}
    for role_menu in session.exec(select(RoleMenu)).all():
        if role_menu.menu_id in obsolete_menu_ids:
            session.delete(role_menu)
    session.flush()

    remaining = {menu.id: menu for menu in obsolete_menus}
    while remaining:
        parent_ids = {
            menu.parent_id for menu in remaining.values() if menu.parent_id in remaining
        }
        leaves = [
            menu for menu_id, menu in remaining.items() if menu_id not in parent_ids
        ]
        for menu in leaves:
            session.delete(menu)
            remaining.pop(menu.id)
        session.flush()


def migrate_directory_menu(
    *,
    session: Session,
    parent: Menu,
    route_name: str,
    legacy_paths: tuple[str, ...],
    target_path: str,
    sort: int,
) -> None:
    legacy_menu = session.exec(
        select(Menu).where(
            Menu.route_name == route_name,
            Menu.route_path.in_(legacy_paths),
        )
    ).first()
    if not legacy_menu:
        return

    target_menu = session.exec(
        select(Menu).where(Menu.route_path == target_path)
    ).first()
    if not target_menu:
        legacy_menu.parent_id = parent.id
        legacy_menu.route_path = target_path
        legacy_menu.sort = sort
        legacy_menu.updated_at = get_datetime_utc()
        session.add(legacy_menu)
        session.flush()
        return

    for role_menu in session.exec(
        select(RoleMenu).where(RoleMenu.menu_id == legacy_menu.id)
    ).all():
        target_mapping = session.exec(
            select(RoleMenu).where(
                RoleMenu.role_id == role_menu.role_id,
                RoleMenu.menu_id == target_menu.id,
            )
        ).first()
        if not target_mapping:
            session.add(RoleMenu(role_id=role_menu.role_id, menu_id=target_menu.id))
        session.delete(role_menu)
    session.flush()
    session.delete(legacy_menu)
    session.flush()
