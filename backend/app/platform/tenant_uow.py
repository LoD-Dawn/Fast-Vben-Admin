"""Tenant-scoped database boundary for Platform operational data."""

import uuid
from collections.abc import Generator
from dataclasses import dataclass
from typing import Any

from sqlalchemy import event, inspect, text
from sqlalchemy.orm import with_loader_criteria
from sqlmodel import Session

from app.platform.core.authorization_models import (
    Department,
    Post,
    Role,
    RoleDataScopeDepartment,
    UserPost,
    UserRole,
)
from app.platform.core.configuration_models import (
    DictionaryItem,
    DictionaryType,
    Notice,
    SiteMessageTemplate,
    SystemSetting,
    UserMessage,
)
from app.platform.core.identity_models import SocialClient, SocialUser, UserSession
from app.platform.core.runtime_models import (
    TenantModule,
    TenantModuleEntitlementOverride,
)
from app.platform.infra.audit_models import LoginLog, OperationLog
from app.platform.infra.file_models import FileAsset, FileStorageChannel
from app.platform.infra.mail_models import MailAccount, MailLog, MailTemplate
from app.platform.infra.sms_models import SmsChannel, SmsLog, SmsTemplate


class PlatformTenantScopeError(RuntimeError):
    """Raised when Platform operational data escapes its tenant boundary."""


TENANT_SCOPED_MODELS = (
    Department,
    Post,
    Role,
    RoleDataScopeDepartment,
    UserPost,
    UserRole,
    DictionaryItem,
    DictionaryType,
    Notice,
    SiteMessageTemplate,
    SystemSetting,
    UserMessage,
    FileAsset,
    FileStorageChannel,
    MailAccount,
    MailTemplate,
    MailLog,
    LoginLog,
    OperationLog,
    SmsChannel,
    SmsTemplate,
    SmsLog,
    SocialClient,
    SocialUser,
    UserSession,
    TenantModule,
    TenantModuleEntitlementOverride,
)


def _set_transaction_tenant(session: Session, tenant_id: uuid.UUID) -> None:
    session.connection().execute(
        text("SELECT set_config('app.tenant_id', :tenant_id, true)"),
        {"tenant_id": str(tenant_id)},
    )


def _clear_transaction_tenant(session: Session) -> None:
    session.connection().execute(text("SELECT set_config('app.tenant_id', '', true)"))


def activate_platform_tenant_scope(
    session: Session, tenant_id: uuid.UUID, *, privileged: bool = False
) -> None:
    """Bind a request session to one tenant after authentication resolves it."""
    existing = session.info.get("platform_tenant_id")
    if existing is not None and existing != tenant_id and not privileged:
        raise PlatformTenantScopeError("A session cannot serve multiple tenants")
    session.info["platform_tenant_id"] = tenant_id
    _set_transaction_tenant(session, tenant_id)


@dataclass
class PlatformTenantUnitOfWork:
    session: Session
    tenant_id: uuid.UUID
    privileged: bool = False

    def __enter__(self) -> PlatformTenantUnitOfWork:
        self._previous_tenant_id = self.session.info.get("platform_tenant_id")
        if (
            self._previous_tenant_id is not None
            and self._previous_tenant_id != self.tenant_id
            and not self.privileged
        ):
            raise PlatformTenantScopeError("A session cannot serve multiple tenants")
        self.session.info["platform_tenant_id"] = self.tenant_id
        _set_transaction_tenant(self.session, self.tenant_id)
        return self

    def __exit__(self, exc_type: Any, exc_value: Any, traceback: Any) -> None:
        if self._previous_tenant_id is None:
            self.session.info.pop("platform_tenant_id", None)
            _clear_transaction_tenant(self.session)
            return
        self.session.info["platform_tenant_id"] = self._previous_tenant_id
        _set_transaction_tenant(self.session, self._previous_tenant_id)


def get_platform_tenant_uow(
    session: Session, tenant_id: uuid.UUID
) -> Generator[PlatformTenantUnitOfWork]:
    with PlatformTenantUnitOfWork(session=session, tenant_id=tenant_id) as uow:
        yield uow


@event.listens_for(Session, "after_begin")
def set_transaction_tenant(session: Session, transaction: Any, connection: Any) -> None:
    tenant_id = session.info.get("platform_tenant_id")
    if tenant_id is None or transaction.nested:
        return
    connection.execute(
        text("SELECT set_config('app.tenant_id', :tenant_id, true)"),
        {"tenant_id": str(tenant_id)},
    )


@event.listens_for(Session, "do_orm_execute")
def enforce_platform_query_scope(execute_state: Any) -> None:
    tenant_id = execute_state.session.info.get("platform_tenant_id")
    if tenant_id is None:
        return
    if (
        execute_state.is_select
        or execute_state.is_update
        or execute_state.is_delete
    ):
        for model in TENANT_SCOPED_MODELS:
            execute_state.statement = execute_state.statement.options(
                with_loader_criteria(
                    model,
                    lambda entity: entity.tenant_id == tenant_id,
                    include_aliases=True,
                )
            )


@event.listens_for(Session, "before_flush")
def enforce_platform_write_scope(
    session: Session, _flush_context: Any, _instances: Any
) -> None:
    tenant_id = session.info.get("platform_tenant_id")
    if tenant_id is None:
        return
    for entity in (*session.new, *session.dirty):
        if not isinstance(entity, TENANT_SCOPED_MODELS):
            continue
        if entity.tenant_id != tenant_id:
            raise PlatformTenantScopeError(
                f"{type(entity).__name__} tenant_id does not match the active tenant"
            )
        if entity in session.dirty and inspect(entity).attrs.tenant_id.history.has_changes():
            raise PlatformTenantScopeError(
                f"{type(entity).__name__} tenant_id is immutable"
            )
