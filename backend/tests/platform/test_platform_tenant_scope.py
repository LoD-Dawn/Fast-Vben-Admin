import uuid

import pytest
from sqlalchemy import delete, text
from sqlmodel import Session, select

from app.core.database import engine
from app.platform.core.authorization_models import Role
from app.platform.core.runtime_models import (
    ModuleEntitlementEffect,
    TenantModule,
    TenantModuleEntitlementOverride,
)
from app.platform.core.tenancy_models import Tenant
from app.platform.infra.audit_models import LoginLog
from app.platform.infra.file_models import FileAsset
from app.platform.infra.mail_models import MailAccount
from app.platform.tenant_uow import PlatformTenantScopeError, PlatformTenantUnitOfWork


def test_platform_tenant_uow_enforces_read_write_and_bulk_boundaries(
    db: Session,
) -> None:
    default_tenant = db.exec(select(Tenant).where(Tenant.code == "default")).one()
    other_tenant = Tenant(code=f"platform-uow-{uuid.uuid4().hex[:12]}", name="UoW")
    db.add(other_tenant)
    db.flush()
    other_tenant_id = other_tenant.id
    with PlatformTenantUnitOfWork(db, other_tenant_id, privileged=True):
        other_role = Role(
            tenant_id=other_tenant_id,
            code=f"platform-uow-{uuid.uuid4().hex[:12]}",
            name="Other tenant role",
        )
        other_role_id = other_role.id
        tenant_module = TenantModule(
            tenant_id=other_tenant_id,
            module_code="items",
        )
        entitlement_override = TenantModuleEntitlementOverride(
            tenant_id=other_tenant_id,
            module_code="items",
            effect=ModuleEntitlementEffect.GRANT,
            reason="Platform UoW isolation test",
        )
        entitlement_override_id = entitlement_override.id
        db.add(other_role)
        db.add(tenant_module)
        db.add(entitlement_override)
        db.commit()

    try:
        with Session(engine) as session:
            with PlatformTenantUnitOfWork(session, default_tenant.id):
                assert session.get(Role, other_role_id) is None
                assert session.get(TenantModule, (other_tenant_id, "items")) is None
                assert (
                    session.get(
                        TenantModuleEntitlementOverride, entitlement_override_id
                    )
                    is None
                )
                assert session.exec(
                    text("SELECT current_setting('app.tenant_id', true)")
                ).one()[0] == str(default_tenant.id)

                session.add(
                    Role(
                        tenant_id=other_tenant_id,
                        code=f"wrong-{uuid.uuid4().hex[:12]}",
                        name="Wrong tenant role",
                    )
                )
                with pytest.raises(PlatformTenantScopeError, match="does not match"):
                    session.flush()
                session.rollback()

                session.add(
                    TenantModule(
                        tenant_id=other_tenant_id,
                        module_code="wrong-tenant",
                    )
                )
                with pytest.raises(PlatformTenantScopeError, match="does not match"):
                    session.flush()
                session.rollback()

            with PlatformTenantUnitOfWork(session, default_tenant.id):
                result = session.exec(delete(Role).where(Role.id == other_role_id))
                session.commit()
                assert result.rowcount == 0
                result = session.exec(
                    delete(TenantModule).where(
                        TenantModule.tenant_id == other_tenant_id,
                        TenantModule.module_code == "items",
                    )
                )
                session.commit()
                assert result.rowcount == 0

            assert session.exec(
                text("SELECT current_setting('app.tenant_id', true)")
            ).one()[0] == ""

        with Session(engine) as verification_session:
            with PlatformTenantUnitOfWork(verification_session, other_tenant_id):
                assert verification_session.get(Role, other_role_id) is not None
                assert (
                    verification_session.get(
                        TenantModule, (other_tenant_id, "items")
                    )
                    is not None
                )
    finally:
        with PlatformTenantUnitOfWork(db, other_tenant_id, privileged=True):
            result = db.exec(
                delete(TenantModuleEntitlementOverride).where(
                    TenantModuleEntitlementOverride.id == entitlement_override_id
                )
            )
            assert result.rowcount == 1
            result = db.exec(
                delete(TenantModule).where(
                    TenantModule.tenant_id == other_tenant_id,
                    TenantModule.module_code == "items",
                )
            )
            assert result.rowcount == 1
            result = db.exec(delete(Role).where(Role.id == other_role_id))
            assert result.rowcount == 1
            tenant = db.get(Tenant, other_tenant_id)
            assert tenant is not None
            db.delete(tenant)
            db.commit()


def test_platform_tenant_uow_scopes_infrastructure_records(db: Session) -> None:
    default_tenant = db.exec(select(Tenant).where(Tenant.code == "default")).one()
    other_tenant = Tenant(code=f"infra-uow-{uuid.uuid4().hex[:12]}", name="Infra UoW")
    db.add(other_tenant)
    db.flush()
    other_tenant_id = other_tenant.id
    with PlatformTenantUnitOfWork(db, other_tenant_id, privileged=True):
        file_asset = FileAsset(
            tenant_id=other_tenant_id,
            original_name="other.txt",
            stored_name="other.txt",
            size=1,
            sha256=uuid.uuid4().hex * 2,
            storage_path="tenants/other/other.txt",
        )
        file_asset_id = file_asset.id
        mail_account = MailAccount(
            tenant_id=other_tenant_id,
            name="Other mail",
            code=f"infra-uow-{uuid.uuid4().hex[:12]}",
            email="other@example.com",
            host="smtp.example.com",
        )
        mail_account_id = mail_account.id
        login_log = LoginLog(tenant_id=other_tenant_id, status="success")
        login_log_id = login_log.id
        db.add(file_asset)
        db.add(mail_account)
        db.add(login_log)
        db.commit()

    try:
        with Session(engine) as session:
            with PlatformTenantUnitOfWork(session, default_tenant.id):
                assert session.get(FileAsset, file_asset_id) is None
                assert session.get(MailAccount, mail_account_id) is None
                assert session.get(LoginLog, login_log_id) is None

                session.add(
                    FileAsset(
                        tenant_id=other_tenant_id,
                        original_name="wrong.txt",
                        stored_name="wrong.txt",
                        size=1,
                        sha256=uuid.uuid4().hex * 2,
                        storage_path="tenants/other/wrong.txt",
                    )
                )
                with pytest.raises(PlatformTenantScopeError, match="does not match"):
                    session.flush()
                session.rollback()

            with PlatformTenantUnitOfWork(session, default_tenant.id):
                result = session.exec(
                    delete(FileAsset).where(FileAsset.id == file_asset_id)
                )
                session.commit()
                assert result.rowcount == 0

        with Session(engine) as verification_session:
            with PlatformTenantUnitOfWork(verification_session, other_tenant_id):
                assert verification_session.get(FileAsset, file_asset_id) is not None
    finally:
        with PlatformTenantUnitOfWork(db, other_tenant_id, privileged=True):
            for model, instance_id in (
                (LoginLog, login_log_id),
                (MailAccount, mail_account_id),
                (FileAsset, file_asset_id),
            ):
                result = db.exec(delete(model).where(model.id == instance_id))
                assert result.rowcount == 1
            tenant = db.get(Tenant, other_tenant_id)
            assert tenant is not None
            db.delete(tenant)
            db.commit()
