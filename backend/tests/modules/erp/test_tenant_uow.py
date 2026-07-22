import uuid
from datetime import timedelta

import psycopg
import pytest
from sqlalchemy import delete, text
from sqlmodel import Session, select

from app.core.clock import get_datetime_utc
from app.core.database import engine
from app.models import ModuleDesiredState, ModuleRegistry, Tenant, User
from app.modules.erp.application.schedules import (
    cleanup_completed_command_receipts,
    run_daily_reconciliation,
)
from app.modules.erp.infrastructure.models import (
    CommandReceipt,
    CommandReceiptStatus,
    DocumentAttachment,
    ProductUnit,
    ReconciliationRun,
    SettlementAccount,
)
from app.modules.erp.infrastructure.repository import ErpMasterDataRepository
from app.modules.erp.infrastructure.tenant_uow import (
    ErpTenantUnitOfWork,
    TenantScopeError,
)
from app.modules.erp.module import definition as erp_definition
from app.modules.erp.reference_guards import count_user_references
from app.modules.migrations import migrate_edition
from app.platform.provision_db_roles import provision_runtime_role


def ensure_erp_schema(db: Session) -> None:
    migrate_edition(edition="erp")
    registry = db.get(ModuleRegistry, "erp")
    assert registry is not None
    registry.desired_state = ModuleDesiredState.DISABLED
    db.add(registry)
    db.commit()


def test_erp_tenant_uow_enforces_read_write_and_bulk_boundaries(db: Session) -> None:
    ensure_erp_schema(db)
    default_tenant = db.exec(select(Tenant).where(Tenant.code == "default")).one()
    other_tenant = Tenant(code=f"erp-uow-{uuid.uuid4().hex[:12]}", name="ERP UoW tenant")
    db.add(other_tenant)
    db.flush()
    other_unit = ProductUnit(
        code="other-unit",
        name="Other unit",
        tenant_id=other_tenant.id,
    )
    db.add(other_unit)
    db.commit()

    try:
        with Session(engine) as session:
            with ErpTenantUnitOfWork(session, default_tenant.id) as uow:
                repository = ErpMasterDataRepository(uow)
                assert repository.get_product_unit(other_unit.id) is None
                assert session.exec(
                    text("SELECT current_setting('app.tenant_id', true)")
                ).one()[0] == str(default_tenant.id)

                repository.add(
                    ProductUnit(
                        code="wrong-tenant-unit",
                        name="Wrong tenant unit",
                        tenant_id=other_tenant.id,
                    )
                )
                with pytest.raises(TenantScopeError, match="does not match"):
                    session.flush()
                session.rollback()

            with ErpTenantUnitOfWork(session, default_tenant.id):
                with pytest.raises(TenantScopeError, match="bulk DML"):
                    session.exec(delete(ProductUnit).where(ProductUnit.id == other_unit.id))

            with ErpTenantUnitOfWork(session, other_tenant.id) as uow:
                assert ErpMasterDataRepository(uow).get_product_unit(other_unit.id) is not None
    finally:
        db.delete(other_unit)
        db.delete(other_tenant)
        db.commit()


def test_erp_rls_restricts_app_runtime_role(db: Session, monkeypatch: pytest.MonkeyPatch) -> None:
    """The database role must enforce tenant isolation independently of the ORM."""

    ensure_erp_schema(db)
    default_tenant = db.exec(select(Tenant).where(Tenant.code == "default")).one()
    other_tenant = Tenant(code=f"erp-rls-{uuid.uuid4().hex[:12]}", name="ERP RLS tenant")
    db.add(other_tenant)
    db.flush()
    user = db.exec(select(User).where(User.email.is_not(None))).first()
    assert user is not None
    default_unit = ProductUnit(
        code=f"runtime-{uuid.uuid4().hex[:12]}",
        name=f"Runtime default {uuid.uuid4().hex[:8]}",
        tenant_id=default_tenant.id,
    )
    other_unit = ProductUnit(
        code=f"runtime-{uuid.uuid4().hex[:12]}",
        name=f"Runtime other {uuid.uuid4().hex[:8]}",
        tenant_id=other_tenant.id,
    )
    default_account = SettlementAccount(
        tenant_id=default_tenant.id,
        name=f"Runtime default {uuid.uuid4().hex[:8]}",
        account_no_encrypted="encrypted-default",
        account_no_fingerprint=f"default-{uuid.uuid4().hex}",
        account_no_last4="0001",
    )
    other_account = SettlementAccount(
        tenant_id=other_tenant.id,
        name=f"Runtime other {uuid.uuid4().hex[:8]}",
        account_no_encrypted="encrypted-other",
        account_no_fingerprint=f"other-{uuid.uuid4().hex}",
        account_no_last4="0002",
    )
    default_receipt = CommandReceipt(
        tenant_id=default_tenant.id,
        command_name=f"runtime-default-{uuid.uuid4().hex}",
        idempotency_key_sha256="a" * 64,
        request_sha256="b" * 64,
        status=CommandReceiptStatus.COMPLETED,
        expires_at=get_datetime_utc() + timedelta(days=1),
    )
    other_receipt = CommandReceipt(
        tenant_id=other_tenant.id,
        command_name=f"runtime-other-{uuid.uuid4().hex}",
        idempotency_key_sha256="c" * 64,
        request_sha256="d" * 64,
        status=CommandReceiptStatus.COMPLETED,
        expires_at=get_datetime_utc() + timedelta(days=1),
    )
    default_attachment = DocumentAttachment(
        tenant_id=default_tenant.id,
        document_type="runtime",
        document_id=uuid.uuid4(),
        file_id=uuid.uuid4(),
        created_by=user.id,
    )
    other_attachment = DocumentAttachment(
        tenant_id=other_tenant.id,
        document_type="runtime",
        document_id=uuid.uuid4(),
        file_id=uuid.uuid4(),
        created_by=user.id,
    )
    db.add_all(
        [
            default_unit,
            other_unit,
            default_account,
            other_account,
            default_receipt,
            other_receipt,
            default_attachment,
            other_attachment,
        ]
    )
    db.commit()

    monkeypatch.setenv("APP_RUNTIME_DB_USER", "app_runtime")
    monkeypatch.setenv("APP_RUNTIME_DB_PASSWORD", "local-compose-placeholder")
    provision_runtime_role()

    runtime_url = (
        engine.url.set(
            username="app_runtime", password="local-compose-placeholder"
        )
        .render_as_string(hide_password=False)
        .replace("postgresql+psycopg://", "postgresql://", 1)
    )
    try:
        owned_tables = set(erp_definition.migration.owned_tables)
        catalog_rows = db.exec(
            text(
                """
                SELECT pg_tables.tablename, pg_class.relrowsecurity, pg_class.relforcerowsecurity,
                       pg_policies.policyname, pg_policies.qual, pg_policies.with_check
                FROM pg_tables
                JOIN pg_class ON pg_class.relname = pg_tables.tablename
                JOIN pg_namespace ON pg_namespace.oid = pg_class.relnamespace
                LEFT JOIN pg_policies
                  ON pg_policies.schemaname = pg_tables.schemaname
                 AND pg_policies.tablename = pg_tables.tablename
                WHERE pg_tables.schemaname = 'erp'
                  AND pg_namespace.nspname = 'erp'
                """
            )
        ).all()
        catalog_by_table = {row[0]: row[1:] for row in catalog_rows}
        assert set(catalog_by_table) >= owned_tables
        for table in owned_tables:
            rowsecurity, force_rowsecurity, policy_name, qual, with_check = catalog_by_table[table]
            assert rowsecurity and force_rowsecurity, table
            assert policy_name == f"erp_{table}_tenant_isolation", table
            assert "tenant_id" in qual and "current_setting" in qual, table
            assert "tenant_id" in with_check and "current_setting" in with_check, table

        with psycopg.connect(runtime_url) as connection:
            with connection.cursor() as cursor:
                cursor.execute(
                    "SELECT id FROM erp.product_unit WHERE id IN (%s, %s)",
                    (default_unit.id, other_unit.id),
                )
                assert cursor.fetchall() == []
                with pytest.raises(psycopg.errors.InsufficientPrivilege):
                    cursor.execute(
                        "INSERT INTO erp.product_unit "
                        "(id, tenant_id, code, name, is_active) VALUES (%s, %s, %s, %s, true)",
                        (uuid.uuid4(), default_tenant.id, "no-scope", "No scope"),
                    )
                connection.rollback()

                cursor.execute("SELECT set_config('app.tenant_id', %s, false)", (str(default_tenant.id),))
                for table, default_id, other_id in (
                    ("product_unit", default_unit.id, other_unit.id),
                    ("settlement_account", default_account.id, other_account.id),
                    ("command_receipt", default_receipt.id, other_receipt.id),
                    ("document_attachment", default_attachment.id, other_attachment.id),
                ):
                    cursor.execute(
                        f"SELECT id FROM erp.{table} WHERE id IN (%s, %s) ORDER BY id",
                        (default_id, other_id),
                    )
                    assert cursor.fetchall() == [(default_id,)], table
                cursor.execute(
                    "UPDATE erp.settlement_account SET name = name WHERE id = %s RETURNING id",
                    (other_account.id,),
                )
                assert cursor.fetchall() == []
                connection.rollback()
    finally:
        db.rollback()
        for record in (
            default_attachment,
            other_attachment,
            default_receipt,
            other_receipt,
            default_account,
            other_account,
            default_unit,
            other_unit,
        ):
            db.delete(record)
        db.delete(other_tenant)
        db.commit()


def test_erp_scheduled_tasks_stay_tenant_local(db: Session) -> None:
    ensure_erp_schema(db)
    default_tenant = db.exec(select(Tenant).where(Tenant.code == "default")).one()
    other_tenant = Tenant(code=f"erp-job-{uuid.uuid4().hex[:12]}", name="ERP job tenant")
    db.add(other_tenant)
    db.flush()
    expired_default = CommandReceipt(
        tenant_id=default_tenant.id,
        command_name="expired-default",
        idempotency_key_sha256="a" * 64,
        request_sha256="b" * 64,
        status=CommandReceiptStatus.COMPLETED,
        expires_at=get_datetime_utc() - timedelta(seconds=1),
    )
    expired_other = CommandReceipt(
        tenant_id=other_tenant.id,
        command_name="expired-other",
        idempotency_key_sha256="c" * 64,
        request_sha256="d" * 64,
        status=CommandReceiptStatus.COMPLETED,
        expires_at=get_datetime_utc() - timedelta(seconds=1),
    )
    db.add_all([expired_default, expired_other])
    db.commit()

    try:
        cleanup_completed_command_receipts(db, default_tenant.id)
        assert db.get(CommandReceipt, expired_default.id) is None
        assert db.get(CommandReceipt, expired_other.id) is not None

        run_daily_reconciliation(db, default_tenant.id)
        run = db.exec(
            select(ReconciliationRun)
            .where(ReconciliationRun.tenant_id == default_tenant.id)
            .order_by(ReconciliationRun.started_at.desc())
        ).first()
        assert run is not None
        assert run.completed_at is not None
    finally:
        db.delete(expired_other)
        db.delete(other_tenant)
        db.commit()


def test_erp_user_reference_guard_counts_tenant_local_audit_references(
    db: Session,
) -> None:
    ensure_erp_schema(db)
    tenant = db.exec(select(Tenant).where(Tenant.code == "default")).one()
    user = db.exec(select(User).where(User.email.is_not(None))).first()
    assert user is not None
    attachment = DocumentAttachment(
        tenant_id=tenant.id,
        document_type="stock_in",
        document_id=uuid.uuid4(),
        file_id=uuid.uuid4(),
        created_by=user.id,
    )
    db.add(attachment)
    db.commit()
    try:
        assert (
            count_user_references(
                db, "user", user.id, tenant.id
            )
            >= 1
        )
        assert count_user_references(db, "file", attachment.file_id, tenant.id) == 0
    finally:
        db.delete(attachment)
        db.commit()
