import uuid
from typing import Any

from fastapi import APIRouter, Depends, Header, HTTPException, Response
from sqlalchemy.exc import IntegrityError
from sqlmodel import select

from app.modules.erp.application.action_log import record_action
from app.modules.erp.application.idempotency import (
    CommandReceiptClaim,
    IdempotencyConflictError,
    IdempotencyInProgressError,
    claim_command,
    complete_command,
    request_sha256,
)
from app.modules.erp.infrastructure.models import (
    Customer,
    DocumentAction,
    Product,
    ProductCategory,
    ProductUnit,
    Supplier,
    Warehouse,
    WarehouseUserGrant,
)
from app.modules.erp.infrastructure.repository import ErpMasterDataRepository
from app.modules.erp.infrastructure.tenant_uow import ErpTenantUowDep
from app.modules.erp.observability import ErpDocumentCommandMetricRoute
from app.modules.erp.public_api.dto import (
    CounterpartyCreate,
    CounterpartyPublic,
    CounterpartySensitivePublic,
    CounterpartyUpdate,
    CustomersPublic,
    ProductCategoriesPublic,
    ProductCategoryCreate,
    ProductCategoryPublic,
    ProductCategoryUpdate,
    ProductCreate,
    ProductPublic,
    ProductsPublic,
    ProductUnitCreate,
    ProductUnitPublic,
    ProductUnitsPublic,
    ProductUnitUpdate,
    ProductUpdate,
    SuppliersPublic,
    WarehouseCreate,
    WarehousePublic,
    WarehousesPublic,
    WarehouseUpdate,
    WarehouseUserGrantPublic,
    WarehouseUserGrantsPublic,
    WarehouseUserGrantsReplace,
)
from app.platform.public_api import (
    SensitiveValueProtectionError,
    get_sensitive_value_protector,
)
from app.platform.web_api import (
    CurrentPrincipal,
    CurrentTenant,
    UserDirectoryDep,
    normalize_pagination,
    require_module_access,
)

router = APIRouter(
    prefix="/erp", tags=["erp"], route_class=ErpDocumentCommandMetricRoute
)


def get_repository(uow: ErpTenantUowDep) -> ErpMasterDataRepository:
    return ErpMasterDataRepository(uow)


def claim_create_command(
    *,
    uow: ErpTenantUowDep,
    command_name: str,
    idempotency_key: str,
    principal: CurrentPrincipal,
    payload: dict[str, Any],
) -> CommandReceiptClaim:
    try:
        return claim_command(
            uow=uow,
            command_name=command_name,
            idempotency_key=idempotency_key,
            request_hash=request_sha256(
                command_name=command_name,
                actor_id=principal.id,
                payload=payload,
            ),
        )
    except (IdempotencyConflictError, IdempotencyInProgressError) as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc


def replay_created_resource(
    *, claim: CommandReceiptClaim, model: Any, resource_type: str, uow: ErpTenantUowDep
) -> Any | None:
    if not claim.replay:
        return None
    if claim.receipt.resource_type != resource_type or claim.receipt.resource_id is None:
        raise HTTPException(status_code=409, detail="Idempotency receipt is unavailable")
    resource = uow.session.get(model, claim.receipt.resource_id)
    if resource is None:
        raise HTTPException(status_code=409, detail="Idempotency receipt resource is unavailable")
    return resource


def counterparty_public(counterparty: Customer | Supplier) -> CounterpartyPublic:
    masked = (
        f"****{counterparty.bank_account_last4}"
        if counterparty.bank_account_last4 is not None
        else None
    )
    return CounterpartyPublic.model_validate(counterparty).model_copy(
        update={"bank_account_masked": masked}
    )


def protected_bank_account_values(
    values: dict[str, Any], *, require_value: bool = False
) -> dict[str, Any]:
    if "bank_account" not in values:
        return {}
    account = values.pop("bank_account")
    if account is None:
        if require_value:
            raise HTTPException(status_code=422, detail="Bank account is required")
        return {"bank_account_encrypted": None, "bank_account_last4": None}
    normalized = account.strip()
    if not normalized:
        raise HTTPException(status_code=422, detail="Bank account is required")
    return {
        "bank_account_encrypted": get_sensitive_value_protector().encrypt(normalized),
        "bank_account_last4": normalized[-4:],
    }


def ensure_unique_code(
    *,
    uow: ErpTenantUowDep,
    model: Any,
    code: str,
    resource_id: uuid.UUID | None = None,
) -> None:
    statement = select(model.id).where(model.code == code)
    if resource_id is not None:
        statement = statement.where(model.id != resource_id)
    if uow.session.exec(statement).first() is not None:
        raise HTTPException(status_code=409, detail="ERP resource code already exists")


def ensure_unique_name(
    *, uow: ErpTenantUowDep, model: Any, name: str, resource_id: uuid.UUID | None = None
) -> None:
    statement = select(model.id).where(model.name == name)
    if resource_id is not None:
        statement = statement.where(model.id != resource_id)
    if uow.session.exec(statement).first() is not None:
        raise HTTPException(status_code=409, detail="ERP counterparty name already exists")


def ensure_unique_product_barcode(
    *,
    uow: ErpTenantUowDep,
    barcode: str | None,
    resource_id: uuid.UUID | None = None,
) -> None:
    if barcode is None:
        return
    statement = select(Product.id).where(Product.barcode == barcode)
    if resource_id is not None:
        statement = statement.where(Product.id != resource_id)
    if uow.session.exec(statement).first() is not None:
        raise HTTPException(status_code=409, detail="Product barcode already exists")


def ensure_product_references(
    *,
    repository: ErpMasterDataRepository,
    category_id: uuid.UUID,
    unit_id: uuid.UUID,
) -> None:
    category = repository.get_product_category(category_id)
    if category is None:
        raise HTTPException(status_code=422, detail="Product category not found")
    if not category.is_active:
        raise HTTPException(status_code=422, detail="Product category is inactive")
    if repository.has_category_children(category_id):
        raise HTTPException(status_code=422, detail="Product category must be a leaf category")
    parent_id = category.parent_id
    while parent_id is not None:
        parent = repository.get_product_category(parent_id)
        if parent is None or not parent.is_active:
            raise HTTPException(status_code=422, detail="Product category ancestor is inactive")
        parent_id = parent.parent_id
    unit = repository.get_product_unit(unit_id)
    if unit is None:
        raise HTTPException(status_code=422, detail="Product unit not found")
    if not unit.is_active:
        raise HTTPException(status_code=422, detail="Product unit is inactive")


def ensure_product_price_policy(*, sale_reference_price: Any, min_sale_price: Any) -> None:
    if min_sale_price > sale_reference_price:
        raise HTTPException(status_code=422, detail="Minimum sale price exceeds reference price")


def clear_default_warehouse(
    *, uow: ErpTenantUowDep, except_id: uuid.UUID | None = None
) -> None:
    warehouses = uow.session.exec(
        select(Warehouse).where(Warehouse.is_default.is_(True)).with_for_update()
    ).all()
    for warehouse in warehouses:
        if warehouse.id != except_id:
            warehouse.is_default = False
            uow.session.add(warehouse)


def ensure_category_parent(
    *,
    repository: ErpMasterDataRepository,
    parent_id: uuid.UUID | None,
    resource_id: uuid.UUID | None = None,
) -> None:
    if parent_id is None:
        return
    if resource_id == parent_id:
        raise HTTPException(status_code=409, detail="Product category cannot be its own parent")
    parent = repository.get_product_category(parent_id)
    if parent is None:
        raise HTTPException(status_code=422, detail="Product category parent not found")

    visited: set[uuid.UUID] = set()
    while parent.parent_id is not None:
        if parent.id in visited or parent.parent_id == resource_id:
            raise HTTPException(status_code=409, detail="Product category hierarchy is cyclic")
        visited.add(parent.id)
        parent = repository.get_product_category(parent.parent_id)
        if parent is None:
            break


@router.get(
    "/product-units",
    dependencies=[Depends(require_module_access("erp", "erp:product-unit:list"))],
    response_model=ProductUnitsPublic,
)
def read_product_units(
    uow: ErpTenantUowDep,
    page: int = 1,
    page_size: int = 20,
    keyword: str | None = None,
) -> ProductUnitsPublic:
    page, page_size = normalize_pagination(page=page, page_size=page_size)
    items, total = get_repository(uow).list_product_units(
        page=page, page_size=page_size, keyword=keyword
    )
    return ProductUnitsPublic(
        items=[ProductUnitPublic.model_validate(item) for item in items],
        total=total,
        page=page,
        page_size=page_size,
    )


@router.post(
    "/product-units",
    dependencies=[Depends(require_module_access("erp", "erp:product-unit:create"))],
    response_model=ProductUnitPublic,
)
def create_product_unit(
    unit_in: ProductUnitCreate,
    uow: ErpTenantUowDep,
    tenant_context: CurrentTenant,
    principal: CurrentPrincipal,
    idempotency_key: str = Header(alias="Idempotency-Key"),
) -> ProductUnit:
    claim = claim_create_command(
        uow=uow, command_name="erp.product-unit.create", idempotency_key=idempotency_key,
        principal=principal, payload=unit_in.model_dump(mode="json"),
    )
    if replay := replay_created_resource(
        claim=claim, model=ProductUnit, resource_type="product_unit", uow=uow
    ):
        return replay
    ensure_unique_code(uow=uow, model=ProductUnit, code=unit_in.code)
    ensure_unique_name(uow=uow, model=ProductUnit, name=unit_in.name)
    unit = ProductUnit.model_validate(unit_in, update={"tenant_id": tenant_context.tenant_id})
    get_repository(uow).add(unit)
    complete_command(receipt=claim.receipt, resource_type="product_unit", resource_id=unit.id, resource_version=1)
    uow.session.commit()
    uow.session.refresh(unit)
    return unit


@router.get(
    "/product-units/{resource_id}",
    dependencies=[Depends(require_module_access("erp", "erp:product-unit:list"))],
    response_model=ProductUnitPublic,
)
def read_product_unit(resource_id: uuid.UUID, uow: ErpTenantUowDep) -> ProductUnit:
    unit = get_repository(uow).get_product_unit(resource_id)
    if unit is None:
        raise HTTPException(status_code=404, detail="Product unit not found")
    return unit


@router.patch(
    "/product-units/{resource_id}",
    dependencies=[Depends(require_module_access("erp", "erp:product-unit:update"))],
    response_model=ProductUnitPublic,
)
def update_product_unit(
    resource_id: uuid.UUID, unit_in: ProductUnitUpdate, uow: ErpTenantUowDep
) -> ProductUnit:
    repository = get_repository(uow)
    unit = repository.get_product_unit(resource_id)
    if unit is None:
        raise HTTPException(status_code=404, detail="Product unit not found")
    values = unit_in.model_dump(exclude_unset=True)
    if "code" in values:
        ensure_unique_code(
            uow=uow, model=ProductUnit, code=values["code"], resource_id=resource_id
        )
    if "name" in values:
        ensure_unique_name(
            uow=uow, model=ProductUnit, name=values["name"], resource_id=resource_id
        )
    repository.update(unit, values)
    uow.session.commit()
    uow.session.refresh(unit)
    return unit


@router.delete(
    "/product-units/{resource_id}",
    dependencies=[Depends(require_module_access("erp", "erp:product-unit:delete"))],
    status_code=204,
)
def delete_product_unit(resource_id: uuid.UUID, uow: ErpTenantUowDep) -> Response:
    repository = get_repository(uow)
    unit = repository.get_product_unit(resource_id)
    if unit is None:
        raise HTTPException(status_code=404, detail="Product unit not found")
    if repository.has_unit_dependents(resource_id):
        raise HTTPException(status_code=409, detail="Product unit is in use")
    repository.delete(unit)
    uow.session.commit()
    return Response(status_code=204)


@router.get(
    "/product-categories",
    dependencies=[Depends(require_module_access("erp", "erp:product-category:list"))],
    response_model=ProductCategoriesPublic,
)
def read_product_categories(
    uow: ErpTenantUowDep,
    page: int = 1,
    page_size: int = 20,
    keyword: str | None = None,
) -> ProductCategoriesPublic:
    page, page_size = normalize_pagination(page=page, page_size=page_size)
    items, total = get_repository(uow).list_product_categories(
        page=page, page_size=page_size, keyword=keyword
    )
    return ProductCategoriesPublic(
        items=[ProductCategoryPublic.model_validate(item) for item in items],
        total=total,
        page=page,
        page_size=page_size,
    )


@router.post(
    "/product-categories",
    dependencies=[Depends(require_module_access("erp", "erp:product-category:create"))],
    response_model=ProductCategoryPublic,
)
def create_product_category(
    category_in: ProductCategoryCreate,
    uow: ErpTenantUowDep,
    tenant_context: CurrentTenant,
    principal: CurrentPrincipal,
    idempotency_key: str = Header(alias="Idempotency-Key"),
) -> ProductCategory:
    claim = claim_create_command(
        uow=uow, command_name="erp.product-category.create", idempotency_key=idempotency_key,
        principal=principal, payload=category_in.model_dump(mode="json"),
    )
    if replay := replay_created_resource(
        claim=claim, model=ProductCategory, resource_type="product_category", uow=uow
    ):
        return replay
    repository = get_repository(uow)
    ensure_unique_code(uow=uow, model=ProductCategory, code=category_in.code)
    ensure_category_parent(repository=repository, parent_id=category_in.parent_id)
    category = ProductCategory.model_validate(
        category_in, update={"tenant_id": tenant_context.tenant_id}
    )
    repository.add(category)
    complete_command(receipt=claim.receipt, resource_type="product_category", resource_id=category.id, resource_version=1)
    uow.session.commit()
    uow.session.refresh(category)
    return category


@router.get(
    "/product-categories/{resource_id}",
    dependencies=[Depends(require_module_access("erp", "erp:product-category:list"))],
    response_model=ProductCategoryPublic,
)
def read_product_category(
    resource_id: uuid.UUID, uow: ErpTenantUowDep
) -> ProductCategory:
    category = get_repository(uow).get_product_category(resource_id)
    if category is None:
        raise HTTPException(status_code=404, detail="Product category not found")
    return category


@router.patch(
    "/product-categories/{resource_id}",
    dependencies=[Depends(require_module_access("erp", "erp:product-category:update"))],
    response_model=ProductCategoryPublic,
)
def update_product_category(
    resource_id: uuid.UUID, category_in: ProductCategoryUpdate, uow: ErpTenantUowDep
) -> ProductCategory:
    repository = get_repository(uow)
    category = repository.get_product_category(resource_id)
    if category is None:
        raise HTTPException(status_code=404, detail="Product category not found")
    values = category_in.model_dump(exclude_unset=True)
    if "code" in values:
        ensure_unique_code(
            uow=uow,
            model=ProductCategory,
            code=values["code"],
            resource_id=resource_id,
        )
    if "parent_id" in values:
        ensure_category_parent(
            repository=repository,
            parent_id=values["parent_id"],
            resource_id=resource_id,
        )
    repository.update(category, values)
    uow.session.commit()
    uow.session.refresh(category)
    return category


@router.delete(
    "/product-categories/{resource_id}",
    dependencies=[Depends(require_module_access("erp", "erp:product-category:delete"))],
    status_code=204,
)
def delete_product_category(resource_id: uuid.UUID, uow: ErpTenantUowDep) -> Response:
    repository = get_repository(uow)
    category = repository.get_product_category(resource_id)
    if category is None:
        raise HTTPException(status_code=404, detail="Product category not found")
    if repository.has_category_dependents(resource_id):
        raise HTTPException(status_code=409, detail="Product category is in use")
    repository.delete(category)
    uow.session.commit()
    return Response(status_code=204)


@router.get(
    "/products",
    dependencies=[Depends(require_module_access("erp", "erp:product:list"))],
    response_model=ProductsPublic,
)
def read_products(
    uow: ErpTenantUowDep,
    page: int = 1,
    page_size: int = 20,
    keyword: str | None = None,
) -> ProductsPublic:
    page, page_size = normalize_pagination(page=page, page_size=page_size)
    items, total = get_repository(uow).list_products(
        page=page, page_size=page_size, keyword=keyword
    )
    return ProductsPublic(
        items=[ProductPublic.model_validate(item) for item in items],
        total=total,
        page=page,
        page_size=page_size,
    )


@router.post(
    "/products",
    dependencies=[Depends(require_module_access("erp", "erp:product:create"))],
    response_model=ProductPublic,
)
def create_product(
    product_in: ProductCreate,
    uow: ErpTenantUowDep,
    tenant_context: CurrentTenant,
    principal: CurrentPrincipal,
    idempotency_key: str = Header(alias="Idempotency-Key"),
) -> Product:
    claim = claim_create_command(
        uow=uow, command_name="erp.product.create", idempotency_key=idempotency_key,
        principal=principal, payload=product_in.model_dump(mode="json"),
    )
    if replay := replay_created_resource(
        claim=claim, model=Product, resource_type="product", uow=uow
    ):
        return replay
    repository = get_repository(uow)
    ensure_unique_code(uow=uow, model=Product, code=product_in.code)
    ensure_unique_product_barcode(uow=uow, barcode=product_in.barcode)
    ensure_product_references(
        repository=repository,
        category_id=product_in.category_id,
        unit_id=product_in.unit_id,
    )
    ensure_product_price_policy(
        sale_reference_price=product_in.sale_reference_price,
        min_sale_price=product_in.min_sale_price,
    )
    product = Product.model_validate(
        product_in, update={"tenant_id": tenant_context.tenant_id}
    )
    repository.add(product)
    complete_command(receipt=claim.receipt, resource_type="product", resource_id=product.id, resource_version=1)
    uow.session.commit()
    uow.session.refresh(product)
    return product


@router.get(
    "/products/{resource_id}",
    dependencies=[Depends(require_module_access("erp", "erp:product:list"))],
    response_model=ProductPublic,
)
def read_product(resource_id: uuid.UUID, uow: ErpTenantUowDep) -> Product:
    product = get_repository(uow).get_product(resource_id)
    if product is None:
        raise HTTPException(status_code=404, detail="Product not found")
    return product


@router.patch(
    "/products/{resource_id}",
    dependencies=[Depends(require_module_access("erp", "erp:product:update"))],
    response_model=ProductPublic,
)
def update_product(
    resource_id: uuid.UUID, product_in: ProductUpdate, uow: ErpTenantUowDep
) -> Product:
    repository = get_repository(uow)
    product = repository.get_product(resource_id)
    if product is None:
        raise HTTPException(status_code=404, detail="Product not found")
    values = product_in.model_dump(exclude_unset=True)
    if "code" in values:
        ensure_unique_code(
            uow=uow, model=Product, code=values["code"], resource_id=resource_id
        )
    if "barcode" in values:
        ensure_unique_product_barcode(
            uow=uow,
            barcode=values["barcode"],
            resource_id=resource_id,
        )
    if "category_id" in values or "unit_id" in values:
        category_id = values.get("category_id", product.category_id)
        if category_id is None:
            raise HTTPException(status_code=422, detail="Product category is required")
        ensure_product_references(
            repository=repository,
            category_id=category_id,
            unit_id=values.get("unit_id", product.unit_id),
        )
    if "sale_reference_price" in values or "min_sale_price" in values:
        ensure_product_price_policy(
            sale_reference_price=values.get(
                "sale_reference_price", product.sale_reference_price
            ),
            min_sale_price=values.get("min_sale_price", product.min_sale_price),
        )
    repository.update(product, values)
    uow.session.commit()
    uow.session.refresh(product)
    return product


@router.delete(
    "/products/{resource_id}",
    dependencies=[Depends(require_module_access("erp", "erp:product:delete"))],
    status_code=204,
)
def delete_product(resource_id: uuid.UUID, uow: ErpTenantUowDep) -> Response:
    repository = get_repository(uow)
    product = repository.get_product(resource_id)
    if product is None:
        raise HTTPException(status_code=404, detail="Product not found")
    repository.delete(product)
    try:
        uow.session.commit()
    except IntegrityError as exc:
        uow.session.rollback()
        raise HTTPException(status_code=409, detail="Product is in use") from exc
    return Response(status_code=204)


@router.get(
    "/warehouses",
    dependencies=[Depends(require_module_access("erp", "erp:warehouse:list"))],
    response_model=WarehousesPublic,
)
def read_warehouses(
    uow: ErpTenantUowDep,
    page: int = 1,
    page_size: int = 20,
    keyword: str | None = None,
) -> WarehousesPublic:
    page, page_size = normalize_pagination(page=page, page_size=page_size)
    items, total = get_repository(uow).list_warehouses(
        page=page, page_size=page_size, keyword=keyword
    )
    return WarehousesPublic(
        items=[WarehousePublic.model_validate(item) for item in items],
        total=total,
        page=page,
        page_size=page_size,
    )


@router.post(
    "/warehouses",
    dependencies=[Depends(require_module_access("erp", "erp:warehouse:create"))],
    response_model=WarehousePublic,
)
def create_warehouse(
    warehouse_in: WarehouseCreate,
    uow: ErpTenantUowDep,
    tenant_context: CurrentTenant,
    principal: CurrentPrincipal,
    idempotency_key: str = Header(alias="Idempotency-Key"),
) -> Warehouse:
    claim = claim_create_command(
        uow=uow, command_name="erp.warehouse.create", idempotency_key=idempotency_key,
        principal=principal, payload=warehouse_in.model_dump(mode="json"),
    )
    if replay := replay_created_resource(
        claim=claim, model=Warehouse, resource_type="warehouse", uow=uow
    ):
        return replay
    ensure_unique_code(uow=uow, model=Warehouse, code=warehouse_in.code)
    ensure_unique_name(uow=uow, model=Warehouse, name=warehouse_in.name)
    if warehouse_in.is_default:
        clear_default_warehouse(uow=uow)
    warehouse = Warehouse.model_validate(
        warehouse_in, update={"tenant_id": tenant_context.tenant_id}
    )
    get_repository(uow).add(warehouse)
    complete_command(receipt=claim.receipt, resource_type="warehouse", resource_id=warehouse.id, resource_version=1)
    try:
        uow.session.commit()
    except IntegrityError as exc:
        uow.session.rollback()
        raise HTTPException(status_code=409, detail="Warehouse default conflicts") from exc
    uow.session.refresh(warehouse)
    return warehouse


@router.get(
    "/warehouses/{resource_id}",
    dependencies=[Depends(require_module_access("erp", "erp:warehouse:list"))],
    response_model=WarehousePublic,
)
def read_warehouse(resource_id: uuid.UUID, uow: ErpTenantUowDep) -> Warehouse:
    warehouse = get_repository(uow).get_warehouse(resource_id)
    if warehouse is None:
        raise HTTPException(status_code=404, detail="Warehouse not found")
    return warehouse


@router.patch(
    "/warehouses/{resource_id}",
    dependencies=[Depends(require_module_access("erp", "erp:warehouse:update"))],
    response_model=WarehousePublic,
)
def update_warehouse(
    resource_id: uuid.UUID, warehouse_in: WarehouseUpdate, uow: ErpTenantUowDep
) -> Warehouse:
    repository = get_repository(uow)
    warehouse = repository.get_warehouse(resource_id)
    if warehouse is None:
        raise HTTPException(status_code=404, detail="Warehouse not found")
    values = warehouse_in.model_dump(exclude_unset=True)
    if "code" in values:
        ensure_unique_code(
            uow=uow, model=Warehouse, code=values["code"], resource_id=resource_id
        )
    if "name" in values:
        ensure_unique_name(
            uow=uow, model=Warehouse, name=values["name"], resource_id=resource_id
        )
    if values.get("is_default") is True:
        clear_default_warehouse(uow=uow, except_id=warehouse.id)
    repository.update(warehouse, values)
    try:
        uow.session.commit()
    except IntegrityError as exc:
        uow.session.rollback()
        raise HTTPException(status_code=409, detail="Warehouse default conflicts") from exc
    uow.session.refresh(warehouse)
    return warehouse


@router.delete(
    "/warehouses/{resource_id}",
    dependencies=[Depends(require_module_access("erp", "erp:warehouse:delete"))],
    status_code=204,
)
def delete_warehouse(resource_id: uuid.UUID, uow: ErpTenantUowDep) -> Response:
    repository = get_repository(uow)
    warehouse = repository.get_warehouse(resource_id)
    if warehouse is None:
        raise HTTPException(status_code=404, detail="Warehouse not found")
    repository.delete(warehouse)
    try:
        uow.session.commit()
    except IntegrityError as exc:
        uow.session.rollback()
        raise HTTPException(status_code=409, detail="Warehouse is in use") from exc
    return Response(status_code=204)


@router.get(
    "/warehouses/{resource_id}/users",
    dependencies=[Depends(require_module_access("erp", "erp:warehouse:assign"))],
    response_model=WarehouseUserGrantsPublic,
)
def read_warehouse_user_grants(
    resource_id: uuid.UUID,
    uow: ErpTenantUowDep,
    user_directory: UserDirectoryDep,
) -> WarehouseUserGrantsPublic:
    warehouse = get_repository(uow).get_warehouse(resource_id)
    if warehouse is None:
        raise HTTPException(status_code=404, detail="Warehouse not found")
    grants = uow.session.exec(
        select(WarehouseUserGrant).where(WarehouseUserGrant.warehouse_id == resource_id)
    ).all()
    users = {user.id: user for user in user_directory.get_users([grant.user_id for grant in grants])}
    return WarehouseUserGrantsPublic(
        items=[
            WarehouseUserGrantPublic(
                user_id=grant.user_id,
                full_name=users[grant.user_id].full_name,
                email=users[grant.user_id].email,
            )
            for grant in grants
            if grant.user_id in users
        ]
    )


@router.put(
    "/warehouses/{resource_id}/users",
    dependencies=[Depends(require_module_access("erp", "erp:warehouse:assign"))],
    response_model=WarehouseUserGrantsPublic,
)
def replace_warehouse_user_grants(
    resource_id: uuid.UUID,
    command: WarehouseUserGrantsReplace,
    uow: ErpTenantUowDep,
    principal: CurrentPrincipal,
    user_directory: UserDirectoryDep,
) -> WarehouseUserGrantsPublic:
    warehouse = get_repository(uow).get_warehouse(resource_id)
    if warehouse is None:
        raise HTTPException(status_code=404, detail="Warehouse not found")
    user_ids = set(command.user_ids)
    try:
        user_directory.validate_active_users(user_ids)
    except ValueError as exc:
        raise HTTPException(status_code=409, detail="Warehouse users must be active") from exc
    existing = uow.session.exec(
        select(WarehouseUserGrant).where(WarehouseUserGrant.warehouse_id == resource_id)
    ).all()
    for grant in existing:
        uow.session.delete(grant)
    uow.session.add_all(
        [
            WarehouseUserGrant(
                tenant_id=uow.tenant_id,
                warehouse_id=resource_id,
                user_id=user_id,
                granted_by=principal.id,
            )
            for user_id in sorted(user_ids, key=str)
        ]
    )
    uow.session.commit()
    users = {user.id: user for user in user_directory.get_users(user_ids)}
    return WarehouseUserGrantsPublic(
        items=[
            WarehouseUserGrantPublic(
                user_id=user_id,
                full_name=users[user_id].full_name,
                email=users[user_id].email,
            )
            for user_id in sorted(user_ids, key=str)
        ]
    )


@router.get(
    "/suppliers",
    dependencies=[Depends(require_module_access("erp", "erp:supplier:list"))],
    response_model=SuppliersPublic,
)
def read_suppliers(
    uow: ErpTenantUowDep,
    page: int = 1,
    page_size: int = 20,
    keyword: str | None = None,
    name: str | None = None,
    mobile: str | None = None,
    phone: str | None = None,
) -> SuppliersPublic:
    page, page_size = normalize_pagination(page=page, page_size=page_size)
    items, total = get_repository(uow).list_suppliers(
        page=page,
        page_size=page_size,
        keyword=keyword,
        name=name,
        mobile=mobile,
        phone=phone,
    )
    return SuppliersPublic(
        items=[counterparty_public(item) for item in items],
        total=total,
        page=page,
        page_size=page_size,
    )


@router.post(
    "/suppliers",
    dependencies=[Depends(require_module_access("erp", "erp:supplier:create"))],
    response_model=CounterpartyPublic,
)
def create_supplier(
    supplier_in: CounterpartyCreate,
    uow: ErpTenantUowDep,
    tenant_context: CurrentTenant,
    principal: CurrentPrincipal,
    idempotency_key: str = Header(alias="Idempotency-Key"),
) -> CounterpartyPublic:
    claim = claim_create_command(
        uow=uow, command_name="erp.supplier.create", idempotency_key=idempotency_key,
        principal=principal, payload=supplier_in.model_dump(mode="json"),
    )
    if replay := replay_created_resource(
        claim=claim, model=Supplier, resource_type="supplier", uow=uow
    ):
        return counterparty_public(replay)
    ensure_unique_name(uow=uow, model=Supplier, name=supplier_in.name)
    values = supplier_in.model_dump()
    values.update(protected_bank_account_values(values))
    supplier = Supplier(tenant_id=tenant_context.tenant_id, **values)
    get_repository(uow).add(supplier)
    complete_command(receipt=claim.receipt, resource_type="supplier", resource_id=supplier.id, resource_version=1)
    uow.session.commit()
    uow.session.refresh(supplier)
    return counterparty_public(supplier)


@router.get(
    "/suppliers/{resource_id}",
    dependencies=[Depends(require_module_access("erp", "erp:supplier:list"))],
    response_model=CounterpartyPublic,
)
def read_supplier(resource_id: uuid.UUID, uow: ErpTenantUowDep) -> CounterpartyPublic:
    supplier = get_repository(uow).get_supplier(resource_id)
    if supplier is None:
        raise HTTPException(status_code=404, detail="Supplier not found")
    return counterparty_public(supplier)


@router.patch(
    "/suppliers/{resource_id}",
    dependencies=[Depends(require_module_access("erp", "erp:supplier:update"))],
    response_model=CounterpartyPublic,
)
def update_supplier(
    resource_id: uuid.UUID, supplier_in: CounterpartyUpdate, uow: ErpTenantUowDep
) -> CounterpartyPublic:
    repository = get_repository(uow)
    supplier = repository.get_supplier(resource_id)
    if supplier is None:
        raise HTTPException(status_code=404, detail="Supplier not found")
    values = supplier_in.model_dump(exclude_unset=True)
    values.update(protected_bank_account_values(values))
    if "name" in values:
        ensure_unique_name(
            uow=uow, model=Supplier, name=values["name"], resource_id=resource_id
        )
    repository.update(supplier, values)
    uow.session.commit()
    uow.session.refresh(supplier)
    return counterparty_public(supplier)


@router.get(
    "/suppliers/{resource_id}/sensitive",
    dependencies=[Depends(require_module_access("erp", "erp:finance-sensitive:read"))],
    response_model=CounterpartySensitivePublic,
)
def read_supplier_sensitive(
    resource_id: uuid.UUID, uow: ErpTenantUowDep, principal: CurrentPrincipal
) -> CounterpartySensitivePublic:
    supplier = get_repository(uow).get_supplier(resource_id)
    if supplier is None or supplier.bank_account_encrypted is None:
        raise HTTPException(status_code=404, detail="Supplier bank account not found")
    try:
        account = get_sensitive_value_protector().decrypt(supplier.bank_account_encrypted)
    except SensitiveValueProtectionError as exc:
        raise HTTPException(status_code=409, detail="Supplier bank account cannot be decrypted") from exc
    record_action(
        uow=uow,
        resource_type="supplier",
        resource_id=supplier.id,
        action=DocumentAction.SENSITIVE_VIEWED,
        actor_id=principal.id,
        metadata={"field": "bank_account"},
    )
    uow.session.commit()
    return CounterpartySensitivePublic(id=supplier.id, bank_account=account)


@router.delete(
    "/suppliers/{resource_id}",
    dependencies=[Depends(require_module_access("erp", "erp:supplier:delete"))],
    status_code=204,
)
def delete_supplier(resource_id: uuid.UUID, uow: ErpTenantUowDep) -> Response:
    repository = get_repository(uow)
    supplier = repository.get_supplier(resource_id)
    if supplier is None:
        raise HTTPException(status_code=404, detail="Supplier not found")
    repository.delete(supplier)
    try:
        uow.session.commit()
    except IntegrityError as exc:
        uow.session.rollback()
        raise HTTPException(status_code=409, detail="Supplier is in use") from exc
    return Response(status_code=204)


@router.get(
    "/customers",
    dependencies=[Depends(require_module_access("erp", "erp:customer:list"))],
    response_model=CustomersPublic,
)
def read_customers(
    uow: ErpTenantUowDep,
    page: int = 1,
    page_size: int = 20,
    keyword: str | None = None,
    name: str | None = None,
    mobile: str | None = None,
    phone: str | None = None,
) -> CustomersPublic:
    page, page_size = normalize_pagination(page=page, page_size=page_size)
    items, total = get_repository(uow).list_customers(
        page=page,
        page_size=page_size,
        keyword=keyword,
        name=name,
        mobile=mobile,
        phone=phone,
    )
    return CustomersPublic(
        items=[counterparty_public(item) for item in items],
        total=total,
        page=page,
        page_size=page_size,
    )


@router.post(
    "/customers",
    dependencies=[Depends(require_module_access("erp", "erp:customer:create"))],
    response_model=CounterpartyPublic,
)
def create_customer(
    customer_in: CounterpartyCreate,
    uow: ErpTenantUowDep,
    tenant_context: CurrentTenant,
    principal: CurrentPrincipal,
    idempotency_key: str = Header(alias="Idempotency-Key"),
) -> CounterpartyPublic:
    claim = claim_create_command(
        uow=uow, command_name="erp.customer.create", idempotency_key=idempotency_key,
        principal=principal, payload=customer_in.model_dump(mode="json"),
    )
    if replay := replay_created_resource(
        claim=claim, model=Customer, resource_type="customer", uow=uow
    ):
        return counterparty_public(replay)
    ensure_unique_name(uow=uow, model=Customer, name=customer_in.name)
    values = customer_in.model_dump()
    values.update(protected_bank_account_values(values))
    customer = Customer(tenant_id=tenant_context.tenant_id, **values)
    get_repository(uow).add(customer)
    complete_command(receipt=claim.receipt, resource_type="customer", resource_id=customer.id, resource_version=1)
    uow.session.commit()
    uow.session.refresh(customer)
    return counterparty_public(customer)


@router.get(
    "/customers/{resource_id}",
    dependencies=[Depends(require_module_access("erp", "erp:customer:list"))],
    response_model=CounterpartyPublic,
)
def read_customer(resource_id: uuid.UUID, uow: ErpTenantUowDep) -> CounterpartyPublic:
    customer = get_repository(uow).get_customer(resource_id)
    if customer is None:
        raise HTTPException(status_code=404, detail="Customer not found")
    return counterparty_public(customer)


@router.patch(
    "/customers/{resource_id}",
    dependencies=[Depends(require_module_access("erp", "erp:customer:update"))],
    response_model=CounterpartyPublic,
)
def update_customer(
    resource_id: uuid.UUID, customer_in: CounterpartyUpdate, uow: ErpTenantUowDep
) -> CounterpartyPublic:
    repository = get_repository(uow)
    customer = repository.get_customer(resource_id)
    if customer is None:
        raise HTTPException(status_code=404, detail="Customer not found")
    values = customer_in.model_dump(exclude_unset=True)
    values.update(protected_bank_account_values(values))
    if "name" in values:
        ensure_unique_name(
            uow=uow, model=Customer, name=values["name"], resource_id=resource_id
        )
    repository.update(customer, values)
    uow.session.commit()
    uow.session.refresh(customer)
    return counterparty_public(customer)


@router.get(
    "/customers/{resource_id}/sensitive",
    dependencies=[Depends(require_module_access("erp", "erp:finance-sensitive:read"))],
    response_model=CounterpartySensitivePublic,
)
def read_customer_sensitive(
    resource_id: uuid.UUID, uow: ErpTenantUowDep, principal: CurrentPrincipal
) -> CounterpartySensitivePublic:
    customer = get_repository(uow).get_customer(resource_id)
    if customer is None or customer.bank_account_encrypted is None:
        raise HTTPException(status_code=404, detail="Customer bank account not found")
    try:
        account = get_sensitive_value_protector().decrypt(customer.bank_account_encrypted)
    except SensitiveValueProtectionError as exc:
        raise HTTPException(status_code=409, detail="Customer bank account cannot be decrypted") from exc
    record_action(
        uow=uow,
        resource_type="customer",
        resource_id=customer.id,
        action=DocumentAction.SENSITIVE_VIEWED,
        actor_id=principal.id,
        metadata={"field": "bank_account"},
    )
    uow.session.commit()
    return CounterpartySensitivePublic(id=customer.id, bank_account=account)


@router.delete(
    "/customers/{resource_id}",
    dependencies=[Depends(require_module_access("erp", "erp:customer:delete"))],
    status_code=204,
)
def delete_customer(resource_id: uuid.UUID, uow: ErpTenantUowDep) -> Response:
    repository = get_repository(uow)
    customer = repository.get_customer(resource_id)
    if customer is None:
        raise HTTPException(status_code=404, detail="Customer not found")
    repository.delete(customer)
    try:
        uow.session.commit()
    except IntegrityError as exc:
        uow.session.rollback()
        raise HTTPException(status_code=409, detail="Customer is in use") from exc
    return Response(status_code=204)
