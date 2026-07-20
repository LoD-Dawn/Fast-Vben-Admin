import csv
import io
import uuid
from typing import Any

from fastapi import APIRouter, Depends, File, HTTPException, Response, UploadFile
from fastapi.responses import StreamingResponse
from sqlmodel import col, select

from app.modules.items.infrastructure.models import (
    Item,
)
from app.modules.items.infrastructure.repository import ItemsRepository
from app.modules.items.infrastructure.tenant_uow import ItemsTenantUowDep
from app.modules.items.public_api.dto import (
    ItemCreate,
    ItemPublic,
    ItemsPublic,
    ItemUpdate,
)
from app.platform.web_api import (
    CurrentPrincipal,
    CurrentTenant,
    build_owner_data_scope_filter,
    normalize_pagination,
    require_module_access,
)

router = APIRouter(prefix="/items", tags=["items"])


def item_to_csv_row(item: Item) -> list[Any]:
    return [
        item.id,
        item.title,
        item.description or "",
        item.owner_id,
        item.created_at or "",
        item.updated_at or "",
    ]


def ensure_item_in_data_scope(
    *,
    uow: ItemsTenantUowDep,
    current_principal: CurrentPrincipal,
    tenant_id: uuid.UUID,
    item: Item,
) -> None:
    scope_filter = build_owner_data_scope_filter(
        session=uow.session,
        current_principal=current_principal,
        tenant_id=tenant_id,
        owner_id_column=Item.owner_id,
    )
    allowed = uow.session.exec(
        select(Item.id).where(
            Item.id == item.id,
            scope_filter,
        )
    ).first()
    if allowed is None:
        raise HTTPException(status_code=403, detail="Not enough permissions")


@router.get(
    "",
    dependencies=[Depends(require_module_access("items", "business:item:list"))],
    response_model=ItemsPublic,
)
def read_items(
    uow: ItemsTenantUowDep,
    current_principal: CurrentPrincipal,
    tenant_context: CurrentTenant,
    page: int = 1,
    page_size: int = 20,
    keyword: str | None = None,
) -> Any:
    """
    Retrieve items.
    """
    page, page_size = normalize_pagination(page=page, page_size=page_size)

    repository = ItemsRepository(uow)
    filters = []
    if keyword:
        pattern = f"%{keyword}%"
        filters.append(
            (col(Item.title).ilike(pattern)) | (col(Item.description).ilike(pattern))
        )

    filters.append(
        build_owner_data_scope_filter(
            session=uow.session,
            current_principal=current_principal,
            tenant_id=tenant_context.tenant_id,
            owner_id_column=Item.owner_id,
        )
    )
    items, count = repository.list(page=page, page_size=page_size, filters=filters)

    items_public = [ItemPublic.model_validate(item) for item in items]
    return ItemsPublic(
        items=items_public,
        total=count,
        page=page,
        page_size=page_size,
    )


@router.get(
    "/export",
    dependencies=[Depends(require_module_access("items", "business:item:list"))],
)
def export_items(
    uow: ItemsTenantUowDep,
    current_principal: CurrentPrincipal,
    tenant_context: CurrentTenant,
) -> StreamingResponse:
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(
        ["id", "title", "description", "owner_id", "created_at", "updated_at"]
    )
    items = ItemsRepository(uow).all(filters=[
        build_owner_data_scope_filter(
            session=uow.session,
            current_principal=current_principal,
            tenant_id=tenant_context.tenant_id,
            owner_id_column=Item.owner_id,
        )
    ])
    for item in items:
        writer.writerow(item_to_csv_row(item))
    output.seek(0)
    return StreamingResponse(
        iter([output.getvalue()]),
        media_type="text/csv",
        headers={"Content-Disposition": 'attachment; filename="items.csv"'},
    )


@router.get(
    "/import-template",
    dependencies=[Depends(require_module_access("items", "business:item:create"))],
)
def download_import_template() -> StreamingResponse:
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(["title", "description"])
    writer.writerow(["示例资源", "这是导入模板示例"])
    output.seek(0)
    return StreamingResponse(
        iter([output.getvalue()]),
        media_type="text/csv",
        headers={
            "Content-Disposition": 'attachment; filename="items-import-template.csv"'
        },
    )


@router.post(
    "/import",
    dependencies=[Depends(require_module_access("items", "business:item:create"))],
)
async def import_items(
    uow: ItemsTenantUowDep,
    current_principal: CurrentPrincipal,
    tenant_context: CurrentTenant,
    file: UploadFile = File(...),
) -> dict[str, Any]:
    if not file.filename or not file.filename.lower().endswith(".csv"):
        raise HTTPException(status_code=400, detail="Only CSV files are supported")

    raw_content = await file.read()
    try:
        content = raw_content.decode("utf-8-sig")
    except UnicodeDecodeError:
        raise HTTPException(status_code=400, detail="CSV file must be UTF-8 encoded")

    reader = csv.DictReader(io.StringIO(content))
    if not reader.fieldnames or "title" not in reader.fieldnames:
        raise HTTPException(status_code=400, detail="CSV must contain title column")

    success_count = 0
    errors: list[dict[str, Any]] = []
    for row_number, row in enumerate(reader, start=2):
        title = (row.get("title") or "").strip()
        description = (row.get("description") or "").strip() or None
        if not title:
            errors.append({"row": row_number, "error": "title is required"})
            continue
        item = Item(
            title=title[:255],
            description=description[:255] if description else None,
            owner_id=current_principal.id,
            tenant_id=tenant_context.tenant_id,
        )
        ItemsRepository(uow).add(item)
        success_count += 1

    uow.session.commit()
    return {
        "errors": errors,
        "failed": len(errors),
        "success": success_count,
        "total": success_count + len(errors),
    }


@router.get(
    "/{id}",
    dependencies=[Depends(require_module_access("items", "business:item:list"))],
    response_model=ItemPublic,
)
def read_item(
    uow: ItemsTenantUowDep,
    current_principal: CurrentPrincipal,
    tenant_context: CurrentTenant,
    id: uuid.UUID,
) -> Any:
    """
    Get item by ID.
    """
    item = ItemsRepository(uow).get(id)
    if not item:
        raise HTTPException(status_code=404, detail="Item not found")
    ensure_item_in_data_scope(
        uow=uow,
        current_principal=current_principal,
        tenant_id=tenant_context.tenant_id,
        item=item,
    )
    return item


@router.post(
    "",
    dependencies=[Depends(require_module_access("items", "business:item:create"))],
    response_model=ItemPublic,
)
def create_item(
    *,
    uow: ItemsTenantUowDep,
    current_principal: CurrentPrincipal,
    tenant_context: CurrentTenant,
    item_in: ItemCreate,
) -> Any:
    """
    Create new item.
    """
    item = Item.model_validate(
        item_in,
        update={
            "owner_id": current_principal.id,
            "tenant_id": tenant_context.tenant_id,
        },
    )
    ItemsRepository(uow).add(item)
    uow.session.commit()
    uow.session.refresh(item)
    return item


@router.patch(
    "/{id}",
    dependencies=[Depends(require_module_access("items", "business:item:update"))],
    response_model=ItemPublic,
)
def update_item(
    *,
    uow: ItemsTenantUowDep,
    current_principal: CurrentPrincipal,
    tenant_context: CurrentTenant,
    id: uuid.UUID,
    item_in: ItemUpdate,
) -> Any:
    """
    Update an item.
    """
    item = ItemsRepository(uow).get(id)
    if not item:
        raise HTTPException(status_code=404, detail="Item not found")
    ensure_item_in_data_scope(
        uow=uow,
        current_principal=current_principal,
        tenant_id=tenant_context.tenant_id,
        item=item,
    )
    update_dict = item_in.model_dump(exclude_unset=True)
    ItemsRepository(uow).update(item, update_dict)
    uow.session.commit()
    uow.session.refresh(item)
    return item


@router.delete(
    "/{id}",
    dependencies=[Depends(require_module_access("items", "business:item:delete"))],
    status_code=204,
)
def delete_item(
    uow: ItemsTenantUowDep,
    current_principal: CurrentPrincipal,
    tenant_context: CurrentTenant,
    id: uuid.UUID,
) -> Response:
    """
    Delete an item.
    """
    item = ItemsRepository(uow).get(id)
    if not item:
        raise HTTPException(status_code=404, detail="Item not found")
    ensure_item_in_data_scope(
        uow=uow,
        current_principal=current_principal,
        tenant_id=tenant_context.tenant_id,
        item=item,
    )
    ItemsRepository(uow).delete(item)
    uow.session.commit()
    return Response(status_code=204)
