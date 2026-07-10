from sqlmodel import Session, create_engine, select

from app import crud
from app.core.config import settings
from app.models import (
    Department,
    DictionaryItem,
    DictionaryType,
    Menu,
    Post,
    Role,
    RoleMenu,
    SystemSetting,
    User,
    UserCreate,
    UserRole,
)

engine = create_engine(str(settings.SQLALCHEMY_DATABASE_URI))


# make sure all SQLModel models are imported (app.models) before initializing DB
# otherwise, SQLModel might fail to initialize relationships properly
# for more details: https://github.com/fastapi/full-stack-fastapi-template/issues/28


def init_db(session: Session) -> None:
    # Tables should be created with Alembic migrations
    # But if you don't want to use migrations, create
    # the tables un-commenting the next lines
    # from sqlmodel import SQLModel

    # This works because the models are already imported and registered from app.models
    # SQLModel.metadata.create_all(engine)

    user = session.exec(
        select(User).where(User.email == settings.FIRST_SUPERUSER)
    ).first()
    if not user:
        user_in = UserCreate(
            email=settings.FIRST_SUPERUSER,
            password=settings.FIRST_SUPERUSER_PASSWORD,
            is_superuser=True,
        )
        user = crud.create_user(session=session, user_create=user_in)

    seed_system_data(session=session, superuser=user)


def seed_system_data(*, session: Session, superuser: User) -> None:
    default_department = ensure_department(
        session=session,
        code="headquarters",
        name="总部",
        sort=0,
    )
    if superuser.department_id is None:
        superuser.department_id = default_department.id
        session.add(superuser)

    super_admin = ensure_role(
        session=session,
        code="super_admin",
        name="超级管理员",
        description="内置超级管理员角色，拥有全部权限。",
        sort=0,
        is_system=True,
    )
    admin = ensure_role(
        session=session,
        code="admin",
        name="系统管理员",
        description="可维护系统管理基础数据。",
        sort=10,
        is_system=True,
    )
    default_user = ensure_role(
        session=session,
        code="user",
        name="普通用户",
        description="默认普通用户角色。",
        sort=100,
        is_system=True,
    )

    seed_dictionaries(session=session)
    seed_posts(session=session)
    seed_settings(session=session)
    menus = seed_menus(session=session)
    bind_role_menus(session=session, role=super_admin, menus=menus)
    bind_role_menus(
        session=session,
        role=admin,
        menus=[
            menu
            for menu in menus
            if menu.permission_code
            and (
                menu.permission_code.startswith("system:")
                or menu.permission_code in {"dashboard:view", "personal:message:list"}
            )
        ],
    )
    bind_role_menus(
        session=session,
        role=default_user,
        menus=[
            menu
            for menu in menus
            if menu.permission_code
            in {
                "dashboard:view",
                "personal:message:list",
                "business:item:list",
                "business:item:create",
                "business:item:update",
                "business:item:delete",
            }
        ],
    )
    bind_user_role(session=session, user=superuser, role=super_admin)
    session.commit()


def ensure_department(
    *, session: Session, code: str, name: str, sort: int
) -> Department:
    department = session.exec(select(Department).where(Department.code == code)).first()
    if department:
        return department

    department = Department(code=code, name=name, sort=sort)
    session.add(department)
    session.flush()
    return department


def ensure_role(
    *,
    session: Session,
    code: str,
    name: str,
    description: str,
    sort: int,
    is_system: bool,
) -> Role:
    role = session.exec(select(Role).where(Role.code == code)).first()
    if role:
        return role

    role = Role(
        code=code,
        name=name,
        description=description,
        sort=sort,
        is_system=is_system,
    )
    session.add(role)
    session.flush()
    return role


def ensure_post(*, session: Session, code: str, name: str, sort: int) -> Post:
    post = session.exec(select(Post).where(Post.code == code)).first()
    if post:
        return post

    post = Post(code=code, name=name, sort=sort)
    session.add(post)
    session.flush()
    return post


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
    )
    session.add(menu)
    session.flush()
    return menu


def seed_menus(*, session: Session) -> list[Menu]:
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
        parent_id=system.id,
        route_path="/system/settings",
        route_name="SystemSettings",
        component="#/views/system/settings/index.vue",
        icon="lucide:sliders-horizontal",
        permission_code="system:setting:list",
        sort=70,
    )
    online_users = ensure_menu(
        session=session,
        title="menu.systemOnlineUsers",
        type="menu",
        parent_id=system.id,
        route_path="/system/online-users",
        route_name="SystemOnlineUsers",
        component="#/views/system/online-users/index.vue",
        icon="lucide:monitor-smartphone",
        permission_code="system:session:list",
        sort=80,
    )
    logs = ensure_menu(
        session=session,
        title="menu.logs",
        type="directory",
        route_path="/logs",
        route_name="Logs",
        icon="lucide:clipboard-list",
        sort=15,
    )
    login_logs = ensure_menu(
        session=session,
        title="menu.loginLogs",
        type="menu",
        parent_id=logs.id,
        route_path="/logs/login",
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
        route_path="/logs/operation",
        route_name="OperationLogs",
        component="#/views/logs/operation/index.vue",
        icon="lucide:history",
        permission_code="system:operation-log:list",
        sort=20,
    )
    files = ensure_menu(
        session=session,
        title="menu.files",
        type="menu",
        route_path="/files",
        route_name="Files",
        component="#/views/files/index.vue",
        icon="lucide:folder",
        permission_code="system:file:list",
        sort=25,
    )
    notices = ensure_menu(
        session=session,
        title="menu.notices",
        type="menu",
        route_path="/notices",
        route_name="Notices",
        component="#/views/notices/index.vue",
        icon="lucide:megaphone",
        permission_code="system:notice:list",
        sort=26,
    )
    messages = ensure_menu(
        session=session,
        title="menu.messages",
        type="menu",
        route_path="/messages",
        route_name="Messages",
        component="#/views/messages/index.vue",
        icon="lucide:mail",
        permission_code="personal:message:list",
        sort=27,
    )
    items = ensure_menu(
        session=session,
        title="menu.items",
        type="menu",
        route_path="/items",
        route_name="Items",
        component="#/views/items/index.vue",
        icon="lucide:list-todo",
        permission_code="business:item:list",
        sort=20,
    )

    button_permissions = [
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
        (online_users.id, "强制下线", "system:session:revoke", 81),
        (files.id, "上传文件", "system:file:upload", 71),
        (files.id, "删除文件", "system:file:delete", 72),
        (notices.id, "新增公告", "system:notice:create", 81),
        (notices.id, "编辑公告", "system:notice:update", 82),
        (notices.id, "删除公告", "system:notice:delete", 83),
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
        users,
        roles,
        menus,
        departments,
        posts,
        dictionaries,
        system_settings,
        online_users,
        logs,
        login_logs,
        operation_logs,
        files,
        notices,
        messages,
        items,
        *buttons,
    ]


def seed_posts(*, session: Session) -> None:
    ensure_post(session=session, code="manager", name="经理", sort=10)
    ensure_post(session=session, code="developer", name="开发工程师", sort=20)
    ensure_post(session=session, code="operator", name="运营专员", sort=30)


def ensure_dictionary_type(
    *, session: Session, code: str, name: str, description: str | None = None
) -> DictionaryType:
    type_ = session.exec(select(DictionaryType).where(DictionaryType.code == code)).first()
    if type_:
        return type_

    type_ = DictionaryType(code=code, name=name, description=description)
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
            DictionaryItem.type_id == type_.id,
            DictionaryItem.value == value,
        )
    ).first()
    if item:
        return item

    item = DictionaryItem(
        type_id=type_.id,
        label=label,
        value=value,
        color=color,
        sort=sort,
    )
    session.add(item)
    session.flush()
    return item


def seed_dictionaries(*, session: Session) -> None:
    user_status = ensure_dictionary_type(
        session=session,
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
        code="yes_no",
        name="是否",
        description="通用是否选项",
    )
    ensure_dictionary_item(session=session, type_=yes_no, label="是", value="yes")
    ensure_dictionary_item(session=session, type_=yes_no, label="否", value="no", sort=1)

    business_status = ensure_dictionary_type(
        session=session,
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


def ensure_setting(
    *,
    session: Session,
    key: str,
    name: str,
    value: str,
    value_type: str,
    group: str,
    description: str | None = None,
    is_public: bool = False,
    is_system: bool = False,
) -> SystemSetting:
    setting = session.exec(select(SystemSetting).where(SystemSetting.key == key)).first()
    if setting:
        return setting

    setting = SystemSetting(
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


def seed_settings(*, session: Session) -> None:
    ensure_setting(
        session=session,
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
        key="upload.max_size_mb",
        name="上传大小限制 MB",
        value="10",
        value_type="number",
        group="upload",
        is_public=False,
        is_system=True,
    )


def bind_role_menus(*, session: Session, role: Role, menus: list[Menu]) -> None:
    existing_menu_ids = {
        role_menu.menu_id
        for role_menu in session.exec(
            select(RoleMenu).where(RoleMenu.role_id == role.id)
        ).all()
    }
    for menu in menus:
        if menu.id not in existing_menu_ids:
            session.add(RoleMenu(role_id=role.id, menu_id=menu.id))


def bind_user_role(*, session: Session, user: User, role: Role) -> None:
    existing = session.exec(
        select(UserRole).where(UserRole.user_id == user.id, UserRole.role_id == role.id)
    ).first()
    if not existing:
        session.add(UserRole(user_id=user.id, role_id=role.id))
