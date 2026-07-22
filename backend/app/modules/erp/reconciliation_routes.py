"""ERP reconciliation HTTP contracts."""

from fastapi import APIRouter, Depends, Header, HTTPException
from sqlmodel import select

from app.modules.erp.application.idempotency import (
    IdempotencyConflictError,
    IdempotencyInProgressError,
    claim_command,
    complete_command,
    request_sha256,
)
from app.modules.erp.application.reconciliation import run_reconciliation
from app.modules.erp.infrastructure.models import ReconciliationRun
from app.modules.erp.infrastructure.tenant_uow import ErpTenantUowDep
from app.modules.erp.observability import ErpDocumentCommandMetricRoute
from app.modules.erp.public_api.dto import ReconciliationRunPublic
from app.platform.web_api import CurrentPrincipal, require_module_access

router = APIRouter(
    prefix="/erp",
    tags=["erp-reconciliation"],
    route_class=ErpDocumentCommandMetricRoute,
)


def _reconciliation_public(run: ReconciliationRun) -> ReconciliationRunPublic:
    return ReconciliationRunPublic.model_validate(run)


@router.post(
    "/reconciliation-runs",
    dependencies=[Depends(require_module_access("erp", "erp:reconciliation:execute"))],
    response_model=ReconciliationRunPublic,
)
def create_reconciliation_run(
    uow: ErpTenantUowDep,
    principal: CurrentPrincipal,
    idempotency_key: str = Header(alias="Idempotency-Key"),
) -> ReconciliationRunPublic:
    command_name = "erp.reconciliation-run.create"
    try:
        claim = claim_command(
            uow=uow,
            command_name=command_name,
            idempotency_key=idempotency_key,
            request_hash=request_sha256(
                command_name=command_name, actor_id=principal.id, payload={}
            ),
        )
    except (IdempotencyConflictError, IdempotencyInProgressError) as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    if claim.replay:
        if (
            claim.receipt.resource_type != "reconciliation_run"
            or claim.receipt.resource_id is None
        ):
            raise HTTPException(status_code=409, detail="Idempotency receipt is unavailable")
        run = uow.session.get(ReconciliationRun, claim.receipt.resource_id)
        if run is None:
            raise HTTPException(status_code=409, detail="Reconciliation run is unavailable")
        return _reconciliation_public(run)
    run = run_reconciliation(uow=uow, triggered_by=principal.id)
    complete_command(
        receipt=claim.receipt,
        resource_type="reconciliation_run",
        resource_id=run.id,
        resource_version=1,
    )
    uow.session.commit()
    uow.session.refresh(run)
    return _reconciliation_public(run)


@router.get(
    "/reconciliation-runs/latest",
    dependencies=[Depends(require_module_access("erp", "erp:reconciliation:read"))],
    response_model=ReconciliationRunPublic | None,
)
def read_latest_reconciliation_run(uow: ErpTenantUowDep) -> ReconciliationRunPublic | None:
    run = uow.session.exec(
        select(ReconciliationRun).order_by(ReconciliationRun.started_at.desc()).limit(1)
    ).first()
    return _reconciliation_public(run) if run is not None else None
