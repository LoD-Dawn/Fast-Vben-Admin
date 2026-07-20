import ast
from pathlib import Path

BACKEND_ROOT = Path(__file__).resolve().parents[2]
ITEMS_ROOT = BACKEND_ROOT / "app" / "modules" / "items"
PLATFORM_ROOT = BACKEND_ROOT / "app" / "platform"
PLATFORM_CORE_ROOT = PLATFORM_ROOT / "core"


def imported_modules(path: Path) -> set[str]:
    tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    imports: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            imports.update(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            imports.add(node.module)
    return imports


def imported_names_from(path: Path, module: str) -> set[str]:
    tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    return {
        alias.name
        for node in ast.walk(tree)
        if isinstance(node, ast.ImportFrom) and node.module == module
        for alias in node.names
    }


def python_files(root: Path) -> list[Path]:
    return sorted(path for path in root.rglob("*.py") if "__pycache__" not in path.parts)


def test_items_does_not_import_platform_internal_or_global_models() -> None:
    forbidden_prefixes = ("app.models", "app.api.routes", "app.storage", "app.mail")
    for path in python_files(ITEMS_ROOT):
        imports = imported_modules(path)
        violations = sorted(
            imported
            for imported in imports
            if imported.startswith(forbidden_prefixes)
        )
        assert not violations, f"{path.relative_to(BACKEND_ROOT)} imports {violations}"


def test_platform_core_does_not_import_business_modules() -> None:
    for path in python_files(PLATFORM_ROOT):
        if path.name == "web_api.py":
            continue
        imports = imported_modules(path)
        violations = sorted(
            imported for imported in imports if imported.startswith("app.modules.items")
        )
        assert not violations, f"{path.relative_to(BACKEND_ROOT)} imports {violations}"


def test_platform_core_has_no_reverse_dependencies() -> None:
    forbidden_prefixes = (
        "app.api.routes",
        "app.models",
        "app.modules.items",
        "app.platform.infra",
    )
    for path in python_files(PLATFORM_CORE_ROOT):
        imports = imported_modules(path)
        violations = sorted(
            imported
            for imported in imports
            if imported.startswith(forbidden_prefixes)
        )
        assert not violations, f"{path.relative_to(BACKEND_ROOT)} imports {violations}"


def test_production_does_not_import_the_legacy_database_facade() -> None:
    legacy_facade = BACKEND_ROOT / "app" / "core" / "db.py"
    for path in python_files(BACKEND_ROOT / "app"):
        if path == legacy_facade:
            continue
        assert "app.core.db" not in imported_modules(path), path.relative_to(
            BACKEND_ROOT
        )

    source = legacy_facade.read_text(encoding="utf-8")
    assert "app.core.database" in source
    assert "app.platform.bootstrap" in source
    assert "sqlmodel" not in source
    assert "app.models" not in source


def test_platform_bootstrap_delegates_configuration_and_infrastructure_seeding() -> None:
    imports = imported_modules(PLATFORM_ROOT / "bootstrap.py")
    assert "app.platform.bootstrap_configuration" in imports
    assert "app.platform.bootstrap_navigation" in imports
    assert "app.platform.bootstrap_rbac" in imports
    forbidden = (
        "app.models",
        "app.platform.core.configuration_models",
        "app.platform.core.authorization_models",
        "app.platform.infra.file_models",
        "app.platform.infra.mail_models",
        "app.platform.infra.sms_models",
    )
    assert not (imports & set(forbidden))


def test_business_modules_do_not_import_platform_infrastructure() -> None:
    for path in python_files(ITEMS_ROOT):
        imports = imported_modules(path)
        violations = sorted(
            imported
            for imported in imports
            if imported.startswith("app.platform.infra")
        )
        assert not violations, f"{path.relative_to(BACKEND_ROOT)} imports {violations}"


def test_public_api_does_not_depend_on_module_implementation() -> None:
    for public_api_root in (ITEMS_ROOT / "public_api", PLATFORM_ROOT / "public_api"):
        for path in python_files(public_api_root):
            imports = imported_modules(path)
            violations = sorted(
                imported
                for imported in imports
                if any(
                    marker in imported
                    for marker in (".infrastructure", ".routes", ".application", ".domain")
                )
            )
            assert not violations, f"{path.relative_to(BACKEND_ROOT)} imports {violations}"


def test_platform_composition_uses_infrastructure_routers() -> None:
    source = (BACKEND_ROOT / "app" / "modules" / "platform.py").read_text(
        encoding="utf-8"
    )
    for router_name in ("files_router", "logs_router", "mail_router", "sms_router"):
        assert f"{router_name}.router" in source

    for legacy_router in ("files.router", "logs.router", "mail.router", "sms.router"):
        assert legacy_router not in source


def test_legacy_platform_route_paths_are_compatibility_facades() -> None:
    for route_name in ("files", "logs", "mail", "sms"):
        source = (
            BACKEND_ROOT / "app" / "api" / "routes" / f"{route_name}.py"
        ).read_text(encoding="utf-8")
        assert f"app.platform.infra.{route_name}_router" in source


def test_message_models_have_platform_owners_and_compatibility_exports() -> None:
    from sqlmodel import SQLModel

    import app.models as compatibility_models
    from app.platform.core import (
        authorization_models,
        configuration_models,
        identity_models,
        runtime_models,
        tenancy_models,
    )
    from app.platform.infra import audit_models, file_models, mail_models, sms_models
    from app.platform.migration_metadata import PLATFORM_MODEL_GROUPS

    sms_group = next(group for group in PLATFORM_MODEL_GROUPS if group.owner == "infra.sms")
    assert sms_group.module == "app.platform.infra.sms_models"
    assert sms_group.tables <= set(SQLModel.metadata.tables)
    assert compatibility_models.SmsChannel is sms_models.SmsChannel
    assert compatibility_models.SmsTemplate is sms_models.SmsTemplate
    assert compatibility_models.SmsLog is sms_models.SmsLog

    mail_group = next(group for group in PLATFORM_MODEL_GROUPS if group.owner == "infra.mail")
    assert mail_group.module == "app.platform.infra.mail_models"
    assert mail_group.tables <= set(SQLModel.metadata.tables)
    assert compatibility_models.MailAccount is mail_models.MailAccount
    assert compatibility_models.MailTemplate is mail_models.MailTemplate
    assert compatibility_models.MailLog is mail_models.MailLog

    file_group = next(group for group in PLATFORM_MODEL_GROUPS if group.owner == "infra.files")
    assert file_group.module == "app.platform.infra.file_models"
    assert file_group.tables <= set(SQLModel.metadata.tables)
    assert compatibility_models.FileAsset is file_models.FileAsset
    assert compatibility_models.FileStorageChannel is file_models.FileStorageChannel

    audit_group = next(group for group in PLATFORM_MODEL_GROUPS if group.owner == "infra.audit")
    assert audit_group.module == "app.platform.infra.audit_models"
    assert audit_group.tables <= set(SQLModel.metadata.tables)
    assert compatibility_models.LoginLog is audit_models.LoginLog
    assert compatibility_models.OperationLog is audit_models.OperationLog

    runtime_group = next(
        group for group in PLATFORM_MODEL_GROUPS if group.owner == "core.module-runtime"
    )
    assert runtime_group.module == "app.platform.core.runtime_models"
    assert runtime_group.tables <= set(SQLModel.metadata.tables)
    assert compatibility_models.ModuleRegistry is runtime_models.ModuleRegistry
    assert compatibility_models.OutboxEvent is runtime_models.OutboxEvent
    assert compatibility_models.CapabilityBinding is runtime_models.CapabilityBinding

    configuration_group = next(
        group for group in PLATFORM_MODEL_GROUPS if group.owner == "core.configuration"
    )
    assert configuration_group.module == "app.platform.core.configuration_models"
    assert configuration_group.tables <= set(SQLModel.metadata.tables)
    assert compatibility_models.DictionaryType is configuration_models.DictionaryType
    assert compatibility_models.SystemSetting is configuration_models.SystemSetting
    assert compatibility_models.Notice is configuration_models.Notice
    assert compatibility_models.UserMessage is configuration_models.UserMessage

    authorization_group = next(
        group for group in PLATFORM_MODEL_GROUPS if group.owner == "core.authorization"
    )
    assert authorization_group.module == "app.platform.core.authorization_models"
    assert authorization_group.tables <= set(SQLModel.metadata.tables)
    assert compatibility_models.Department is authorization_models.Department
    assert compatibility_models.Post is authorization_models.Post
    assert compatibility_models.Role is authorization_models.Role
    assert compatibility_models.Menu is authorization_models.Menu

    tenancy_group = next(
        group for group in PLATFORM_MODEL_GROUPS if group.owner == "core.tenancy"
    )
    assert tenancy_group.module == "app.platform.core.tenancy_models"
    assert tenancy_group.tables <= set(SQLModel.metadata.tables)
    assert compatibility_models.Tenant is tenancy_models.Tenant
    assert compatibility_models.TenantPlan is tenancy_models.TenantPlan
    assert compatibility_models.TenantMembership is tenancy_models.TenantMembership
    assert compatibility_models.TenantProfile is tenancy_models.TenantProfile

    identity_group = next(
        group for group in PLATFORM_MODEL_GROUPS if group.owner == "core.identity"
    )
    assert identity_group.module == "app.platform.core.identity_models"
    assert identity_group.tables <= set(SQLModel.metadata.tables)
    assert compatibility_models.User is identity_models.User
    assert compatibility_models.UserSession is identity_models.UserSession
    assert compatibility_models.OAuth2Client is identity_models.OAuth2Client
    assert compatibility_models.SocialUser is identity_models.SocialUser


def test_message_routers_do_not_depend_on_aggregate_models() -> None:
    for router_name in ("logs_router.py", "mail_router.py", "sms_router.py"):
        imports = imported_modules(PLATFORM_ROOT / "infra" / router_name)
        assert "app.models" not in imports


def test_file_storage_adapter_uses_the_owned_file_models() -> None:
    source = (PLATFORM_ROOT / "infra" / "storage_impl.py").read_text(encoding="utf-8")
    assert "from app.platform.infra.file_models import FileStorageChannel" in source


def test_module_runtime_services_do_not_import_runtime_models_from_aggregate() -> None:
    runtime_names = {
        "CapabilityBinding",
        "EventDelivery",
        "InboxReceipt",
        "ModuleRegistry",
        "ModuleStateAudit",
        "OutboxEvent",
        "TenantModule",
        "TenantModuleEntitlementOverride",
        "TenantPlanModule",
    }
    paths = (
        BACKEND_ROOT / "app" / "api" / "routes" / "modules.py",
        BACKEND_ROOT / "app" / "modules" / "access.py",
        BACKEND_ROOT / "app" / "modules" / "capabilities.py",
        BACKEND_ROOT / "app" / "modules" / "migrations.py",
        BACKEND_ROOT / "app" / "modules" / "outbox.py",
    )
    for path in paths:
        assert not (
            imported_names_from(path, "app.models") & runtime_names
        ), path.relative_to(BACKEND_ROOT)


def test_configuration_consumers_use_owned_models() -> None:
    configuration_names = {
        "DictionaryItem",
        "DictionaryType",
        "Notice",
        "SiteMessageTemplate",
        "SystemSetting",
        "UserMessage",
    }
    paths = (
        BACKEND_ROOT / "app" / "api" / "routes" / "dictionaries.py",
        BACKEND_ROOT / "app" / "api" / "routes" / "notices.py",
        BACKEND_ROOT / "app" / "api" / "routes" / "settings.py",
        BACKEND_ROOT / "app" / "api" / "routes" / "site_messages.py",
        BACKEND_ROOT / "app" / "core" / "db.py",
        BACKEND_ROOT / "app" / "platform" / "infra" / "storage_impl.py",
    )
    for path in paths:
        assert not (
            imported_names_from(path, "app.models") & configuration_names
        ), path.relative_to(BACKEND_ROOT)


def test_authorization_consumers_use_owned_models() -> None:
    authorization_names = {
        "DataScope",
        "Department",
        "DepartmentBase",
        "DepartmentCreate",
        "DepartmentPublic",
        "DepartmentsPublic",
        "DepartmentUpdate",
        "Menu",
        "MenuBase",
        "MenuCreate",
        "MenuPublic",
        "MenusPublic",
        "MenuUpdate",
        "Post",
        "PostBase",
        "PostCreate",
        "PostPublic",
        "PostsPublic",
        "PostUpdate",
        "Role",
        "RoleBase",
        "RoleCreate",
        "RoleDataScopeDepartment",
        "RoleMenu",
        "RoleMenuUpdate",
        "RolePublic",
        "RolesPublic",
        "RoleUpdate",
        "UserPost",
        "UserPostUpdate",
        "UserRole",
        "UserRoleUpdate",
    }
    for path in python_files(BACKEND_ROOT / "app"):
        if path == BACKEND_ROOT / "app" / "models.py":
            continue
        assert not (
            imported_names_from(path, "app.models") & authorization_names
        ), path.relative_to(BACKEND_ROOT)


def test_tenancy_consumers_use_owned_models() -> None:
    tenancy_names = {
        "Tenant",
        "TenantBase",
        "TenantCreate",
        "TenantInitializationTemplate",
        "TenantInitializationTemplateBase",
        "TenantInitializationTemplateCreate",
        "TenantInitializationTemplatePublic",
        "TenantInitializationTemplatesPublic",
        "TenantInitializationTemplateUpdate",
        "TenantLifecycleAction",
        "TenantLifecycleActionRequest",
        "TenantLifecycleStatus",
        "TenantMembership",
        "TenantMembershipPublic",
        "TenantMenuSyncResult",
        "TenantPlan",
        "TenantPlanBase",
        "TenantPlanCreate",
        "TenantPlanMenu",
        "TenantPlanMenuUpdate",
        "TenantPlanProfile",
        "TenantPlanPublic",
        "TenantPlansPublic",
        "TenantPlanUpdate",
        "TenantProfile",
        "TenantPublic",
        "TenantRegistrationRequest",
        "TenantsPublic",
        "TenantSwitchRequest",
        "TenantUpdate",
        "TenantUsagePublic",
    }
    violations = []
    for path in python_files(BACKEND_ROOT / "app"):
        if path == BACKEND_ROOT / "app" / "models.py":
            continue
        names = imported_names_from(path, "app.models") & tenancy_names
        if names:
            violations.append((str(path.relative_to(BACKEND_ROOT)), sorted(names)))
    assert not violations, "\n".join(f"{path}: {names}" for path, names in violations)


def test_identity_consumers_use_owned_models() -> None:
    identity_names = {
        "UserIdentityBase",
        "UserBase",
        "UserCreate",
        "UserRegister",
        "SmsCodeRequest",
        "SmsCodeSent",
        "SmsLoginRequest",
        "RegistrationStatus",
        "QrCodeLoginCreate",
        "QrCodeLoginChallenge",
        "QrCodeLoginStatusRequest",
        "QrCodeLoginStatus",
        "QrCodeLoginConfirmRequest",
        "QrCodeLoginConfirmResult",
        "QrCodeLoginExchangeRequest",
        "UserUpdate",
        "UserUpdateMe",
        "MasterDataAnonymizeRequest",
        "UpdatePassword",
        "UserMfaEnable",
        "UserMfaEnableResult",
        "UserMfaDisable",
        "User",
        "UserPublic",
        "UsersPublic",
        "UserMfaStatus",
        "UserMfaSetup",
        "UserSession",
        "OAuth2ClientBase",
        "OAuth2Client",
        "OAuth2ClientCreate",
        "OAuth2ClientUpdate",
        "OAuth2ClientPublic",
        "OAuth2ClientsPublic",
        "OAuth2AccessToken",
        "OAuth2AccessTokenPublic",
        "OAuth2AccessTokensPublic",
        "OAuth2AuthorizationCode",
        "EnterpriseOidcAuthorizationState",
        "EnterpriseOidcIdentity",
        "EnterpriseOidcLoginTicket",
        "EnterpriseOidcStatus",
        "EnterpriseOidcTicketExchange",
        "SocialClientBase",
        "SocialClient",
        "SocialClientCreate",
        "SocialClientUpdate",
        "SocialClientPublic",
        "SocialClientsPublic",
        "SocialUser",
        "SocialUserPublic",
        "SocialUsersPublic",
        "SocialUserBind",
    }
    violations = []
    for path in python_files(BACKEND_ROOT / "app"):
        if path == BACKEND_ROOT / "app" / "models.py":
            continue
        names = imported_names_from(path, "app.models") & identity_names
        if names:
            violations.append((str(path.relative_to(BACKEND_ROOT)), sorted(names)))
    assert not violations, "\n".join(f"{path}: {names}" for path, names in violations)


def test_alembic_aggregates_platform_model_groups_before_legacy_models() -> None:
    source = (BACKEND_ROOT / "app" / "alembic" / "env.py").read_text(
        encoding="utf-8"
    )
    assert source.index("import_platform_model_groups()") < source.index(
        'import_module("app.models")'
    )


def test_every_platform_table_has_one_declared_owner() -> None:
    from sqlmodel import SQLModel

    import app.models  # noqa: F401
    from app.platform.migration_metadata import platform_table_owners

    platform_tables = {
        table_name
        for table_name in SQLModel.metadata.tables
        if "." not in table_name
    }
    assert set(platform_table_owners()) == platform_tables
