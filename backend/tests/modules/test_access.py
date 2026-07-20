from sqlalchemy import event
from sqlmodel import Session, select

from app.models import ModuleStateAudit, Tenant, TenantPlanModule
from app.modules import access
from app.platform.tenant_uow import PlatformTenantUnitOfWork


def test_reconcile_does_not_create_plan_entitlements(db: Session) -> None:
    tenant = db.exec(select(Tenant).where(Tenant.code == "default")).one()
    original = db.get(TenantPlanModule, (tenant.plan_id, "items"))
    original_enabled = original.is_enabled if original is not None else None
    if original is not None:
        db.delete(original)
        db.commit()

    try:
        access.reconcile_module_runtime(db)
        db.commit()
        assert db.get(TenantPlanModule, (tenant.plan_id, "items")) is None
    finally:
        if original_enabled is not None:
            db.add(
                TenantPlanModule(
                    plan_id=tenant.plan_id,
                    module_code="items",
                    is_enabled=original_enabled,
                )
            )
            db.commit()


def test_module_access_is_one_read_query_and_never_reconciles(
    db: Session, monkeypatch
) -> None:
    tenant = db.exec(select(Tenant).where(Tenant.code == "default")).one()
    audit_count = len(db.exec(select(ModuleStateAudit)).all())
    statements: list[str] = []

    def fail_if_called(*_args, **_kwargs) -> None:
        raise AssertionError("request authorization must not reconcile module runtime")

    monkeypatch.setattr(access, "reconcile_module_runtime", fail_if_called)
    monkeypatch.setattr(access.redis_cache, "get_json", lambda *_args, **_kwargs: None)
    monkeypatch.setattr(access.redis_cache, "set_json", lambda *_args, **_kwargs: False)

    engine = db.get_bind()

    def capture_statement(_conn, _cursor, statement, _parameters, _context, _executemany):
        statements.append(statement)

    with PlatformTenantUnitOfWork(db, tenant.id, privileged=True):
        event.listen(engine, "before_cursor_execute", capture_statement)
        try:
            decision = access.evaluate_module_access(
                session=db,
                tenant_id=tenant.id,
                module_code="items",
            )
        finally:
            event.remove(engine, "before_cursor_execute", capture_statement)

    assert decision.allowed
    assert len(statements) == 1
    assert len(db.exec(select(ModuleStateAudit)).all()) == audit_count
