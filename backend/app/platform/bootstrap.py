from sqlmodel import Session, select

from app import crud
from app.core.cache import CacheNamespace, redis_cache
from app.core.config import settings
from app.core.tenancy import DEFAULT_TENANT_CODE, DEFAULT_TENANT_ID
from app.platform.bootstrap_configuration import (
    seed_dictionaries,
    seed_mail_accounts,
    seed_settings,
    seed_site_message_templates,
    seed_sms_channels,
    seed_storage_channels,
)
from app.platform.bootstrap_navigation import (
    seed_menus,
)
from app.platform.bootstrap_rbac import (
    bind_role_menus,
    bind_user_role,
    ensure_default_tenant_plan_menus,
    ensure_department,
    ensure_role,
    ensure_tenant_membership,
    seed_posts,
)
from app.platform.core.identity_models import User, UserCreate
from app.platform.core.tenancy_models import (
    Tenant,
    TenantInitializationTemplate,
    TenantPlan,
    TenantPlanProfile,
    TenantProfile,
)
from app.platform.tenant_uow import PlatformTenantUnitOfWork


def init_db(session: Session) -> None:
    # Tables should be created with Alembic migrations
    # But if you don't want to use migrations, create
    # the tables un-commenting the next lines
    # from sqlmodel import SQLModel

    # This works because the models are already imported and registered from app.models
    # SQLModel.metadata.create_all(engine)

    default_plan = ensure_default_tenant_plan(session=session)
    default_template = ensure_default_tenant_template(session=session)
    default_tenant = ensure_default_tenant(
        session=session,
        plan=default_plan,
        template=default_template,
    )
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

    ensure_tenant_membership(
        session=session,
        user=user,
        tenant=default_tenant,
        is_default=True,
    )

    seed_system_data(session=session, superuser=user, tenant=default_tenant)
    # A new Edition can add menu permissions to an already initialized tenant.
    # Subsequent logins must not receive a stale RBAC snapshot.
    redis_cache.bump_namespace(CacheNamespace.RBAC)
    redis_cache.bump_namespace(CacheNamespace.MODULE_ACCESS)


def ensure_default_tenant_plan(*, session: Session) -> TenantPlan:
    plan = session.exec(select(TenantPlan).where(TenantPlan.code == "standard")).first()
    if plan is not None:
        ensure_tenant_plan_profile(session=session, plan=plan)
        return plan
    plan = TenantPlan(
        code="standard",
        name="Standard",
        description="Default unlimited plan.",
        is_default=True,
        is_active=True,
    )
    session.add(plan)
    session.flush()
    ensure_tenant_plan_profile(session=session, plan=plan)
    return plan


def ensure_default_tenant_template(*, session: Session) -> TenantInitializationTemplate:
    template = session.exec(
        select(TenantInitializationTemplate).where(
            TenantInitializationTemplate.code == "standard"
        )
    ).first()
    if template is not None:
        return template
    template = TenantInitializationTemplate(
        code="standard",
        name="Standard",
        description="Default full tenant initialization.",
        is_default=True,
        is_active=True,
    )
    session.add(template)
    session.flush()
    return template


def ensure_default_tenant(
    *,
    session: Session,
    plan: TenantPlan,
    template: TenantInitializationTemplate,
) -> Tenant:
    tenant = session.exec(
        select(Tenant).where(Tenant.code == DEFAULT_TENANT_CODE)
    ).first()
    if tenant:
        ensure_tenant_profile(session=session, tenant=tenant)
        return tenant
    tenant = Tenant(
        id=DEFAULT_TENANT_ID,
        code=DEFAULT_TENANT_CODE,
        name="Default Tenant",
        description="Tenant created for data that predates v2.0 multi-tenancy.",
        plan_id=plan.id,
        initialization_template_id=template.id,
    )
    session.add(tenant)
    session.flush()
    ensure_tenant_profile(session=session, tenant=tenant)
    return tenant


def ensure_tenant_profile(*, session: Session, tenant: Tenant) -> TenantProfile:
    profile = session.get(TenantProfile, tenant.id)
    if profile is not None:
        return profile
    profile = TenantProfile(tenant_id=tenant.id)
    session.add(profile)
    session.flush()
    return profile


def ensure_tenant_plan_profile(
    *, session: Session, plan: TenantPlan
) -> TenantPlanProfile:
    profile = session.get(TenantPlanProfile, plan.id)
    if profile is not None:
        return profile
    profile = TenantPlanProfile(plan_id=plan.id)
    session.add(profile)
    session.flush()
    return profile


def seed_system_data(*, session: Session, superuser: User, tenant: Tenant) -> None:
    with PlatformTenantUnitOfWork(session, tenant.id, privileged=True):
        _seed_system_data(session=session, superuser=superuser, tenant=tenant)


def _seed_system_data(*, session: Session, superuser: User, tenant: Tenant) -> None:
    default_department = ensure_department(
        session=session,
        tenant=tenant,
        code="headquarters",
        name="总部",
        sort=0,
    )
    superuser_membership = ensure_tenant_membership(
        session=session,
        user=superuser,
        tenant=tenant,
    )
    if superuser_membership.department_id is None:
        superuser_membership.department_id = default_department.id
        session.add(superuser_membership)

    super_admin = ensure_role(
        session=session,
        tenant=tenant,
        code="super_admin",
        name="超级管理员",
        description="内置超级管理员角色，拥有全部权限。",
        sort=0,
        is_system=True,
        data_scope="all",
    )
    admin = ensure_role(
        session=session,
        tenant=tenant,
        code="admin",
        name="系统管理员",
        description="可维护系统管理基础数据。",
        sort=10,
        is_system=True,
        data_scope="all",
    )
    default_user = ensure_role(
        session=session,
        tenant=tenant,
        code="user",
        name="普通用户",
        description="默认普通用户角色。",
        sort=100,
        is_system=True,
        data_scope="self",
    )

    seed_dictionaries(session=session, tenant=tenant)
    seed_posts(session=session, tenant=tenant)
    seed_settings(session=session, tenant=tenant)
    seed_storage_channels(session=session, tenant=tenant)
    seed_sms_channels(session=session, tenant=tenant)
    seed_mail_accounts(session=session, tenant=tenant)
    seed_site_message_templates(session=session, tenant=tenant)
    menus = seed_menus(session=session)
    ensure_default_tenant_plan_menus(
        session=session,
        plan=session.get(TenantPlan, tenant.plan_id),
        menus=menus,
    )
    bind_role_menus(
        session=session,
        role=super_admin,
        menus=[
            menu
            for menu in menus
            if not (menu.permission_code or "").startswith("platform:")
        ],
    )
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
            or menu.type == "directory"
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
