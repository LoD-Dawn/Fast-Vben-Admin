from dataclasses import dataclass
from datetime import datetime
from functools import lru_cache
from typing import Any

from sqlalchemy import and_, or_
from sqlmodel import Session, col, select

from app.core.cache import CacheNamespace, redis_cache
from app.core.clock import get_datetime_utc
from app.core.config import settings
from app.platform.core.identity_models import User
from app.platform.core.runtime_models import (
    ModuleDesiredState,
    ModuleEntitlementEffect,
    ModuleObservedState,
    ModuleRegistry,
    ModuleStateAudit,
    TenantModule,
    TenantModuleEntitlementOverride,
    TenantPlanModule,
)
from app.platform.core.tenancy_models import Tenant, TenantPlan
from app.platform.tenant_uow import PlatformTenantUnitOfWork


@dataclass(frozen=True)
class ModuleAccessDecision:
    allowed: bool
    error_code: str | None = None


@dataclass(frozen=True)
class ModuleAccessSnapshot:
    desired_state: ModuleDesiredState
    observed_state: ModuleObservedState
    tenant_is_active: bool | None
    plan_is_active: bool | None
    plan_module_enabled: bool | None
    override_effect: ModuleEntitlementEffect | None
    preference_enabled: bool | None


@lru_cache(maxsize=1)
def get_runtime_manifest() -> Any:
    """Load the immutable process manifest once; requests never read Edition YAML."""
    from app.modules.manifest import build_manifest, load_manifest_file

    if settings.BUILD_MANIFEST_PATH is not None:
        return load_manifest_file(settings.BUILD_MANIFEST_PATH)
    return build_manifest(edition=settings.APP_EDITION)


def clear_runtime_manifest_cache() -> None:
    """Allow controlled test or process lifecycle code to reload the build manifest."""
    get_runtime_manifest.cache_clear()


def reconcile_module_runtime(session: Session, *, manifest=None) -> None:
    """Synchronize build-owned runtime records during migration or explicit reconciliation.

    This is deliberately a write path. Request authorization must only read the
    state produced here and must never create registry or entitlement records.
    """
    manifest = manifest or get_runtime_manifest()
    now = get_datetime_utc()

    for module in manifest.modules:
        registry = session.get(ModuleRegistry, module.code)
        if registry is None:
            registry = ModuleRegistry(
                code=module.code,
                version=module.version,
                desired_state=ModuleDesiredState.ENABLED,
                observed_state=ModuleObservedState.BUNDLED,
                manifest_digest=manifest.manifest_digest,
                updated_at=now,
            )
            session.add(registry)
            record_module_state_audit(
                session=session,
                module_code=module.code,
                action="module.observed_state.changed",
                previous_value=None,
                next_value=ModuleObservedState.BUNDLED,
                reason="module bundled in current build manifest",
                actor=None,
            )
        elif (
            registry.version != module.version
            or registry.manifest_digest != manifest.manifest_digest
        ):
            registry.version = module.version
            registry.manifest_digest = manifest.manifest_digest
            registry.updated_at = now
            session.add(registry)

    session.flush()


def validate_module_runtime(session: Session, *, manifest=None) -> None:
    """Fail closed when persisted runtime state disagrees with the build."""
    manifest = manifest or get_runtime_manifest()
    manifest_codes = {module.code for module in manifest.modules}
    registries = {
        registry.code: registry for registry in session.exec(select(ModuleRegistry)).all()
    }
    enabled_not_bundled = sorted(
        code
        for code, registry in registries.items()
        if registry.desired_state == ModuleDesiredState.ENABLED
        and code not in manifest_codes
    )
    if enabled_not_bundled:
        raise RuntimeError(
            "Enabled modules are absent from the build manifest: "
            + ", ".join(enabled_not_bundled)
        )
    unavailable = sorted(
        code
        for code in manifest_codes
        if (registry := registries.get(code)) is None
        or (
            registry.desired_state == ModuleDesiredState.ENABLED
            and registry.observed_state != ModuleObservedState.READY
        )
    )
    if unavailable:
        raise RuntimeError(
            "Enabled build modules are not ready: " + ", ".join(unavailable)
        )


def set_module_observed_state(
    *,
    session: Session,
    registry: ModuleRegistry,
    observed_state: ModuleObservedState,
    actual_revision: str | None = None,
    reason: str | None = None,
) -> None:
    """Persist a system-owned lifecycle transition and its audit record."""
    previous_state = registry.observed_state
    registry.observed_state = observed_state
    if actual_revision is not None:
        registry.actual_revision = actual_revision
    registry.updated_at = get_datetime_utc()
    session.add(registry)
    if previous_state != observed_state:
        record_module_state_audit(
            session=session,
            module_code=registry.code,
            action="module.observed_state.changed",
            previous_value=previous_state,
            next_value=observed_state,
            reason=reason,
            actor=None,
        )


def module_for_permission(permission_code: str | None) -> str | None:
    if not permission_code:
        return None
    from app.modules.registry import get_module_definitions

    for definition in get_module_definitions().values():
        if definition.code == "platform":
            continue
        if permission_code.startswith(f"{definition.permission_prefix}:"):
            return definition.code
    return None


def _active_override(
    *, session: Session, tenant_id, module_code: str, now: datetime
) -> TenantModuleEntitlementOverride | None:
    overrides = session.exec(
        select(TenantModuleEntitlementOverride)
        .where(
            TenantModuleEntitlementOverride.tenant_id == tenant_id,
            TenantModuleEntitlementOverride.module_code == module_code,
        )
        .order_by(col(TenantModuleEntitlementOverride.created_at).desc())
    ).all()
    for override in overrides:
        if override.starts_at is not None and override.starts_at > now:
            continue
        if override.ends_at is not None and override.ends_at <= now:
            continue
        return override
    return None


def tenant_has_module_entitlement(
    *, session: Session, tenant: Tenant, module_code: str, now: datetime | None = None
) -> bool:
    with PlatformTenantUnitOfWork(session, tenant.id, privileged=True):
        return _tenant_has_module_entitlement(
            session=session,
            tenant=tenant,
            module_code=module_code,
            now=now,
        )


def _tenant_has_module_entitlement(
    *, session: Session, tenant: Tenant, module_code: str, now: datetime | None = None
) -> bool:
    now = now or get_datetime_utc()
    plan = session.get(TenantPlan, tenant.plan_id)
    if plan is None or not plan.is_active:
        return False
    override = _active_override(
        session=session,
        tenant_id=tenant.id,
        module_code=module_code,
        now=now,
    )
    if override is not None:
        return override.effect == ModuleEntitlementEffect.GRANT
    mapping = session.get(TenantPlanModule, (tenant.plan_id, module_code))
    return bool(mapping and mapping.is_enabled)


def _load_module_access_snapshot(
    *, session: Session, tenant_id, module_code: str
) -> ModuleAccessSnapshot | None:
    """Read all business-module access inputs in one SQL statement."""
    now = get_datetime_utc()
    active_override_id = (
        select(TenantModuleEntitlementOverride.id)
        .where(
            TenantModuleEntitlementOverride.tenant_id == tenant_id,
            TenantModuleEntitlementOverride.module_code == module_code,
            or_(
                TenantModuleEntitlementOverride.starts_at.is_(None),
                TenantModuleEntitlementOverride.starts_at <= now,
            ),
            or_(
                TenantModuleEntitlementOverride.ends_at.is_(None),
                TenantModuleEntitlementOverride.ends_at > now,
            ),
        )
        .order_by(col(TenantModuleEntitlementOverride.created_at).desc())
        .limit(1)
        .scalar_subquery()
    )
    statement = (
        select(
            ModuleRegistry.desired_state,
            ModuleRegistry.observed_state,
            Tenant.is_active,
            TenantPlan.is_active,
            TenantPlanModule.is_enabled,
            TenantModuleEntitlementOverride.effect,
            TenantModule.is_enabled,
        )
        .select_from(ModuleRegistry)
        .outerjoin(Tenant, Tenant.id == tenant_id)
        .outerjoin(TenantPlan, TenantPlan.id == Tenant.plan_id)
        .outerjoin(
            TenantPlanModule,
            and_(
                TenantPlanModule.plan_id == Tenant.plan_id,
                TenantPlanModule.module_code == module_code,
            ),
        )
        .outerjoin(
            TenantModule,
            and_(
                TenantModule.tenant_id == tenant_id,
                TenantModule.module_code == module_code,
            ),
        )
        .outerjoin(
            TenantModuleEntitlementOverride,
            TenantModuleEntitlementOverride.id == active_override_id,
        )
        .where(ModuleRegistry.code == module_code)
    )
    row = session.exec(statement).one_or_none()
    if row is None:
        return None
    return ModuleAccessSnapshot(*row)


def _cached_module_access_decision(
    *, manifest_digest: str, tenant_id, module_code: str
) -> ModuleAccessDecision | None:
    key = redis_cache.build_versioned_key(
        CacheNamespace.MODULE_ACCESS,
        "module-access",
        manifest_digest,
        tenant_id,
        module_code,
    )
    cached = redis_cache.get_json(key)
    if not isinstance(cached, dict) or not isinstance(cached.get("allowed"), bool):
        return None
    error_code = cached.get("error_code")
    return ModuleAccessDecision(
        allowed=cached["allowed"],
        error_code=error_code if isinstance(error_code, str) else None,
    )


def _cache_module_access_decision(
    *,
    manifest_digest: str,
    tenant_id,
    module_code: str,
    decision: ModuleAccessDecision,
) -> None:
    key = redis_cache.build_versioned_key(
        CacheNamespace.MODULE_ACCESS,
        "module-access",
        manifest_digest,
        tenant_id,
        module_code,
    )
    redis_cache.set_json(
        key,
        {"allowed": decision.allowed, "error_code": decision.error_code},
    )


def _evaluate_module_access_snapshot(
    snapshot: ModuleAccessSnapshot | None,
) -> ModuleAccessDecision:
    if snapshot is None:
        return ModuleAccessDecision(False, "MODULE_UNAVAILABLE")
    if snapshot.desired_state != ModuleDesiredState.ENABLED:
        return ModuleAccessDecision(False, "MODULE_UNAVAILABLE")
    if snapshot.observed_state != ModuleObservedState.READY:
        return ModuleAccessDecision(False, "MODULE_UNAVAILABLE")
    if not snapshot.tenant_is_active or not snapshot.plan_is_active:
        return ModuleAccessDecision(False, "TENANT_MODULE_ENTITLEMENT_REQUIRED")

    entitled = (
        snapshot.override_effect == ModuleEntitlementEffect.GRANT
        if snapshot.override_effect is not None
        else bool(snapshot.plan_module_enabled)
    )
    if not entitled:
        return ModuleAccessDecision(False, "TENANT_MODULE_ENTITLEMENT_REQUIRED")
    if snapshot.preference_enabled is False:
        return ModuleAccessDecision(False, "TENANT_MODULE_DISABLED")
    return ModuleAccessDecision(True)


def evaluate_module_access(
    *, session: Session, tenant_id, module_code: str
) -> ModuleAccessDecision:
    manifest = get_runtime_manifest()
    if module_code not in {module.code for module in manifest.modules}:
        return ModuleAccessDecision(False, "MODULE_NOT_INSTALLED")

    if module_code == "platform":
        registry = session.exec(
            select(ModuleRegistry.desired_state, ModuleRegistry.observed_state).where(
                ModuleRegistry.code == module_code
            )
        ).one_or_none()
        if registry is None:
            return ModuleAccessDecision(False, "MODULE_UNAVAILABLE")
        desired_state, observed_state = registry
        return (
            ModuleAccessDecision(True)
            if desired_state == ModuleDesiredState.ENABLED
            and observed_state == ModuleObservedState.READY
            else ModuleAccessDecision(False, "MODULE_UNAVAILABLE")
        )

    cached = _cached_module_access_decision(
        manifest_digest=manifest.manifest_digest,
        tenant_id=tenant_id,
        module_code=module_code,
    )
    if cached is not None:
        return cached

    decision = _evaluate_module_access_snapshot(
        _load_module_access_snapshot(
            session=session,
            tenant_id=tenant_id,
            module_code=module_code,
        )
    )
    _cache_module_access_decision(
        manifest_digest=manifest.manifest_digest,
        tenant_id=tenant_id,
        module_code=module_code,
        decision=decision,
    )
    return decision


def filter_module_scoped_permissions(
    *, session: Session, tenant_id, permission_codes: list[str]
) -> list[str]:
    decisions: dict[str, bool] = {}
    filtered: list[str] = []
    for permission_code in permission_codes:
        module_code = module_for_permission(permission_code)
        if module_code is None:
            filtered.append(permission_code)
            continue
        if module_code not in decisions:
            decisions[module_code] = evaluate_module_access(
                session=session,
                tenant_id=tenant_id,
                module_code=module_code,
            ).allowed
        if decisions[module_code]:
            filtered.append(permission_code)
    return filtered


def record_module_state_audit(
    *,
    session: Session,
    module_code: str,
    action: str,
    previous_value: str | None,
    next_value: str | None,
    reason: str | None,
    actor: User | None,
    tenant_id=None,
) -> None:
    session.add(
        ModuleStateAudit(
            module_code=module_code,
            tenant_id=tenant_id,
            action=action,
            previous_value=previous_value,
            next_value=next_value,
            reason=reason,
            actor_user_id=actor.id if actor is not None else None,
        )
    )
