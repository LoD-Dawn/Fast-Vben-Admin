"""Logical ERP document-file attachment HTTP contracts."""

import uuid
from typing import Any

from fastapi import APIRouter, Depends, Header, HTTPException, Response
from sqlalchemy import text
from sqlmodel import Session, func, select

from app.modules.erp.application.action_log import record_action
from app.modules.erp.application.idempotency import (
    IdempotencyConflictError,
    IdempotencyInProgressError,
    claim_command,
    complete_command,
    request_sha256,
)
from app.modules.erp.infrastructure.models import (
    DocumentAction,
    DocumentAttachment,
    FinancePayment,
    FinanceReceipt,
    PurchaseIn,
    PurchaseOrder,
    PurchaseReturn,
    SaleOrder,
    SaleOut,
    SaleReturn,
    StockCheck,
    StockIn,
    StockMove,
    StockOut,
)
from app.modules.erp.infrastructure.tenant_uow import ErpTenantUowDep
from app.modules.erp.observability import ErpDocumentCommandMetricRoute
from app.modules.erp.public_api.dto import (
    DocumentAttachmentCreate,
    DocumentAttachmentPublic,
    DocumentAttachmentsPublic,
)
from app.platform.web_api import (
    CurrentPrincipal,
    FileAssetDirectoryDep,
    build_owner_data_scope_filter,
    require_module_access,
)

router = APIRouter(
    prefix="/erp", tags=["erp-attachments"], route_class=ErpDocumentCommandMetricRoute
)

DOCUMENT_MODELS: dict[str, Any] = {
    "finance_payment": FinancePayment,
    "finance_receipt": FinanceReceipt,
    "purchase_in": PurchaseIn,
    "purchase_order": PurchaseOrder,
    "purchase_return": PurchaseReturn,
    "sale_out": SaleOut,
    "sale_order": SaleOrder,
    "sale_return": SaleReturn,
    "stock_check": StockCheck,
    "stock_in": StockIn,
    "stock_move": StockMove,
    "stock_out": StockOut,
}


def document_status_value(document: Any) -> str:
    status = document.status
    return str(getattr(status, "value", status))


def assert_attachment_mutable(document: Any) -> None:
    if document_status_value(document) != "draft":
        raise HTTPException(
            status_code=409,
            detail="Attachments cannot be changed after document approval",
        )


def count_file_references(
    session: Session, reference_type: str, reference_id: object, tenant_id: object | None = None
) -> int:
    if reference_type != "file":
        return 0
    if tenant_id is None:
        return 0
    # Reference guards run from Platform's destructive-operation path, outside
    # the ERP request UoW. Activate the already trusted tenant only for this
    # RLS-protected count, then clear it before returning the shared Session.
    session.execute(
        text("SELECT set_config('app.tenant_id', :tenant_id, true)"),
        {"tenant_id": str(tenant_id)},
    )
    try:
        statement = select(func.count()).select_from(DocumentAttachment).where(
            DocumentAttachment.file_id == reference_id,
            DocumentAttachment.tenant_id == tenant_id,
        )
        return int(session.exec(statement).one())
    finally:
        session.execute(text("SELECT set_config('app.tenant_id', '', true)"))


def get_document(
    *,
    uow: ErpTenantUowDep,
    principal: CurrentPrincipal,
    document_type: str,
    document_id: uuid.UUID,
) -> Any:
    model = DOCUMENT_MODELS.get(document_type)
    if model is None:
        raise HTTPException(status_code=422, detail="Unsupported ERP document type")
    scope = build_owner_data_scope_filter(
        session=uow.session,
        current_principal=principal,
        tenant_id=uow.tenant_id,
        owner_id_column=model.owner_id,
    )
    document = uow.session.exec(
        select(model).where(model.id == document_id, scope)
    ).first()
    if document is None:
        raise HTTPException(status_code=404, detail="ERP document not found")
    return document


def attachment_public(*, attachment: DocumentAttachment, file_directory: FileAssetDirectoryDep, tenant_id: uuid.UUID) -> DocumentAttachmentPublic:
    file = file_directory.get_accessible_file(tenant_id=tenant_id, file_id=attachment.file_id)
    if file is None:
        raise HTTPException(status_code=409, detail="Attached file is unavailable")
    return DocumentAttachmentPublic(
        id=attachment.id,
        file_id=file.id,
        file_name=file.original_name,
        content_type=file.content_type,
        size=file.size,
        sort=attachment.sort,
        created_at=attachment.created_at,
    )


@router.get(
    "/documents/{document_type}/{document_id}/attachments",
    dependencies=[Depends(require_module_access("erp", "erp:attachment:list"))],
    response_model=DocumentAttachmentsPublic,
)
def read_document_attachments(
    document_type: str,
    document_id: uuid.UUID,
    uow: ErpTenantUowDep,
    principal: CurrentPrincipal,
    file_directory: FileAssetDirectoryDep,
) -> DocumentAttachmentsPublic:
    get_document(
        uow=uow, principal=principal, document_type=document_type, document_id=document_id
    )
    attachments = uow.session.exec(
        select(DocumentAttachment)
        .where(
            DocumentAttachment.document_type == document_type,
            DocumentAttachment.document_id == document_id,
        )
        .order_by(DocumentAttachment.sort, DocumentAttachment.created_at)
    ).all()
    return DocumentAttachmentsPublic(
        items=[
            attachment_public(
                attachment=attachment,
                file_directory=file_directory,
                tenant_id=uow.tenant_id,
            )
            for attachment in attachments
        ]
    )


@router.post(
    "/documents/{document_type}/{document_id}/attachments",
    dependencies=[Depends(require_module_access("erp", "erp:attachment:create"))],
    response_model=DocumentAttachmentPublic,
)
def create_document_attachment(
    document_type: str,
    document_id: uuid.UUID,
    command: DocumentAttachmentCreate,
    uow: ErpTenantUowDep,
    principal: CurrentPrincipal,
    file_directory: FileAssetDirectoryDep,
    idempotency_key: str = Header(alias="Idempotency-Key"),
) -> DocumentAttachmentPublic:
    document = get_document(
        uow=uow, principal=principal, document_type=document_type, document_id=document_id
    )
    assert_attachment_mutable(document)
    command_name = "erp.document-attachment.create"
    try:
        claim = claim_command(
            uow=uow,
            command_name=command_name,
            idempotency_key=idempotency_key,
            request_hash=request_sha256(
                command_name=command_name,
                actor_id=principal.id,
                resource_id=document_id,
                payload={"document_type": document_type, **command.model_dump(mode="json")},
            ),
        )
    except (IdempotencyConflictError, IdempotencyInProgressError) as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    if claim.replay:
        if claim.receipt.resource_type != "document_attachment" or claim.receipt.resource_id is None:
            raise HTTPException(status_code=409, detail="Idempotency receipt is unavailable")
        attachment = uow.session.get(DocumentAttachment, claim.receipt.resource_id)
        if attachment is None or attachment.document_type != document_type or attachment.document_id != document_id:
            raise HTTPException(status_code=409, detail="Idempotency receipt resource is unavailable")
        return attachment_public(attachment=attachment, file_directory=file_directory, tenant_id=uow.tenant_id)
    file = file_directory.get_accessible_file(tenant_id=uow.tenant_id, file_id=command.file_id)
    if file is None:
        raise HTTPException(status_code=409, detail="File is unavailable for the current tenant")
    duplicate = uow.session.exec(
        select(DocumentAttachment.id).where(
            DocumentAttachment.document_type == document_type,
            DocumentAttachment.document_id == document_id,
            DocumentAttachment.file_id == command.file_id,
        )
    ).first()
    if duplicate is not None:
        raise HTTPException(status_code=409, detail="File is already attached to this document")
    attachment = DocumentAttachment(
        tenant_id=uow.tenant_id,
        document_type=document_type,
        document_id=document_id,
        file_id=file.id,
        sort=command.sort,
        created_by=principal.id,
    )
    uow.session.add(attachment)
    record_action(
        uow=uow,
        resource_type=document_type,
        resource_id=document.id,
        resource_no=document.no,
        action=DocumentAction.UPDATED,
        actor_id=principal.id,
        new_status=document_status_value(document),
        new_version=document.version,
        metadata={"attachment_id": str(attachment.id), "change": "attached"},
    )
    complete_command(
        receipt=claim.receipt,
        resource_type="document_attachment",
        resource_id=attachment.id,
        resource_version=1,
    )
    uow.session.commit()
    uow.session.refresh(attachment)
    return attachment_public(attachment=attachment, file_directory=file_directory, tenant_id=uow.tenant_id)


@router.delete(
    "/documents/{document_type}/{document_id}/attachments/{attachment_id}",
    dependencies=[Depends(require_module_access("erp", "erp:attachment:delete"))],
    status_code=204,
)
def delete_document_attachment(
    document_type: str,
    document_id: uuid.UUID,
    attachment_id: uuid.UUID,
    uow: ErpTenantUowDep,
    principal: CurrentPrincipal,
) -> Response:
    document = get_document(
        uow=uow, principal=principal, document_type=document_type, document_id=document_id
    )
    assert_attachment_mutable(document)
    attachment = uow.session.get(DocumentAttachment, attachment_id)
    if attachment is None or attachment.document_type != document_type or attachment.document_id != document_id:
        raise HTTPException(status_code=404, detail="Document attachment not found")
    record_action(
        uow=uow,
        resource_type=document_type,
        resource_id=document.id,
        resource_no=document.no,
        action=DocumentAction.UPDATED,
        actor_id=principal.id,
        new_status=document_status_value(document),
        new_version=document.version,
        metadata={"attachment_id": str(attachment.id), "change": "detached"},
    )
    uow.session.delete(attachment)
    uow.session.commit()
    return Response(status_code=204)
