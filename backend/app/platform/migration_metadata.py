"""Platform-owned model groups used exclusively by Alembic metadata aggregation."""

from dataclasses import dataclass
from importlib import import_module


@dataclass(frozen=True)
class PlatformModelGroup:
    owner: str
    module: str
    tables: frozenset[str]


PLATFORM_MODEL_GROUPS = (
    PlatformModelGroup(
        owner="core.identity",
        module="app.platform.core.identity_models",
        tables=frozenset(
            {
                "enterpriseoidcauthorizationstate",
                "enterpriseoidcidentity",
                "enterpriseoidcloginticket",
                "oauth2accesstoken",
                "oauth2authorizationcode",
                "oauth2client",
                "socialclient",
                "socialuser",
                "user",
                "usersession",
            }
        ),
    ),
    PlatformModelGroup(
        owner="core.tenancy",
        module="app.platform.core.tenancy_models",
        tables=frozenset(
            {
                "tenant",
                "tenantinitializationtemplate",
                "tenantmembership",
                "tenantplan",
                "tenantplanmenu",
                "tenantplanprofile",
                "tenantprofile",
            }
        ),
    ),
    PlatformModelGroup(
        owner="core.authorization",
        module="app.platform.core.authorization_models",
        tables=frozenset(
            {
                "department",
                "menu",
                "post",
                "role",
                "roledatascopedepartment",
                "rolemenu",
                "userpost",
                "userrole",
            }
        ),
    ),
    PlatformModelGroup(
        owner="core.configuration",
        module="app.platform.core.configuration_models",
        tables=frozenset(
            {
                "dictionaryitem",
                "dictionarytype",
                "notice",
                "sitemessagetemplate",
                "systemsetting",
                "usermessage",
            }
        ),
    ),
    PlatformModelGroup(
        owner="core.module-runtime",
        module="app.platform.core.runtime_models",
        tables=frozenset(
            {
                "capabilitybinding",
                "eventdelivery",
                "inboxreceipt",
                "moduleregistry",
                "modulestateaudit",
                "outboxevent",
                "tenantmodule",
                "tenantmoduleentitlementoverride",
                "tenantplanmodule",
            }
        ),
    ),
    PlatformModelGroup(
        owner="infra.sms",
        module="app.platform.infra.sms_models",
        tables=frozenset({"smschannel", "smstemplate", "smslog"}),
    ),
    PlatformModelGroup(
        owner="infra.mail",
        module="app.platform.infra.mail_models",
        tables=frozenset({"mailaccount", "mailtemplate", "maillog"}),
    ),
    PlatformModelGroup(
        owner="infra.files",
        module="app.platform.infra.file_models",
        tables=frozenset({"fileasset", "filestoragechannel"}),
    ),
    PlatformModelGroup(
        owner="infra.audit",
        module="app.platform.infra.audit_models",
        tables=frozenset({"loginlog", "operationlog"}),
    ),
)


def import_platform_model_groups() -> None:
    """Register physically-owned Platform models before Alembic reads metadata."""
    for group in PLATFORM_MODEL_GROUPS:
        import_module(group.module)


def platform_table_owners() -> dict[str, str]:
    """Return the unique internal owner of every Platform table."""
    owners: dict[str, str] = {}
    for group in PLATFORM_MODEL_GROUPS:
        for table in group.tables:
            if table in owners:
                raise ValueError(
                    f"Platform table {table!r} has multiple owners: "
                    f"{owners[table]!r}, {group.owner!r}"
                )
            owners[table] = group.owner
    return owners
