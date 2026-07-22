import uuid
from contextlib import contextmanager
from datetime import timedelta
from decimal import Decimal
from io import BytesIO

from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlmodel import Session, select

from app.api.main import create_api_router
from app.core.cache import CacheNamespace, redis_cache
from app.core.clock import get_datetime_utc
from app.core.config import settings
from app.models import (
    ModuleDesiredState,
    ModuleRegistry,
    Tenant,
    TenantPlan,
    TenantPlanModule,
    User,
)
from app.modules.access import clear_runtime_manifest_cache
from app.modules.erp.attachment_routes import count_file_references
from app.modules.erp.infrastructure.models import (
    Customer,
    StockBalance,
    StockIn,
    StockInItem,
    Supplier,
    WarehouseUserGrant,
)
from app.modules.erp.infrastructure.tenant_uow import ErpTenantUnitOfWork
from app.modules.erp.stock_routes import warehouse_document_scope_filter
from app.modules.events import configure_event_deliveries
from app.modules.manifest import build_manifest
from app.modules.migrations import migrate_edition
from app.modules.outbox import EVENT_HANDLERS
from app.modules.registry import get_module_definitions
from app.platform.web_api import Principal


@contextmanager
def erp_client(db: Session):
    migrate_edition(edition="erp")
    # Migrations run through their own connection.  Drop any instances held by
    # the shared fixture before updating runtime state, so an old observed
    # state cannot be flushed back over the migration result.
    db.expire_all()
    tenant = db.exec(select(Tenant).where(Tenant.code == "default")).one()
    plan = db.get(TenantPlan, tenant.plan_id)
    assert plan is not None
    entitlement = db.get(TenantPlanModule, (plan.id, "erp"))
    if entitlement is None:
        entitlement = TenantPlanModule(plan_id=plan.id, module_code="erp", is_enabled=True)
    else:
        entitlement.is_enabled = True
    registry = db.get(ModuleRegistry, "erp")
    assert registry is not None
    registry.desired_state = ModuleDesiredState.ENABLED
    db.add_all([entitlement, registry])
    db.commit()
    # This fixture changes module state outside the management API, so it owns
    # the cache invalidation normally performed by that API.
    redis_cache.bump_namespace(CacheNamespace.MODULE_ACCESS)

    from app.modules import access

    original_manifest = access.get_runtime_manifest
    erp_manifest = build_manifest(edition="erp")
    access.get_runtime_manifest = lambda: erp_manifest
    definitions = get_module_definitions()
    configure_event_deliveries(
        (definitions["platform"], definitions["erp"])
    )
    app = FastAPI()
    app.include_router(create_api_router(edition="erp"), prefix=settings.API_V1_STR)
    try:
        with TestClient(app) as client:
            def add_idempotency_key(request: object) -> None:
                if getattr(request, "method", None) != "POST":
                    return
                headers = getattr(request, "headers", None)
                if headers is not None and "Idempotency-Key" not in headers:
                    headers["Idempotency-Key"] = uuid.uuid4().hex

            client.event_hooks["request"].append(add_idempotency_key)
            yield client
    finally:
        access.get_runtime_manifest = original_manifest
        EVENT_HANDLERS.clear()
        clear_runtime_manifest_cache()
        registry = db.get(ModuleRegistry, "erp")
        assert registry is not None
        registry.desired_state = ModuleDesiredState.DISABLED
        db.add(registry)
        db.commit()
        redis_cache.bump_namespace(CacheNamespace.MODULE_ACCESS)


def assert_document_list_and_export_match(
    *,
    client: TestClient,
    headers: dict[str, str],
    export_path: str,
    list_path: str,
    params: dict[str, str],
    document: dict[str, object],
) -> None:
    listed = client.get(list_path, headers=headers, params=params)
    exported = client.get(export_path, headers=headers, params=params)
    assert listed.status_code == exported.status_code == 200
    assert [item["id"] for item in listed.json()["items"]] == [document["id"]]
    assert str(document["no"]) in exported.text


def create_product_category(
    *, client: TestClient, headers: dict[str, str], suffix: str
) -> str:
    response = client.post(
        f"{settings.API_V1_STR}/erp/product-categories",
        headers=headers,
        json={"code": f"category-{suffix}", "name": f"Category {suffix}"},
    )
    assert response.status_code == 200
    return response.json()["id"]


def test_erp_master_data_crud_and_reference_protection(
    superuser_token_headers: dict[str, str], db: Session
) -> None:
    suffix = uuid.uuid4().hex[:12]
    with erp_client(db) as scoped_client:
        unit_payload = {
            "code": f"piece-{suffix}",
            "name": f"Piece {suffix}",
            "symbol": "pc",
        }
        unit_headers = {
            **superuser_token_headers,
            "Idempotency-Key": f"master-unit-{uuid.uuid4().hex}",
        }
        unit = scoped_client.post(
            f"{settings.API_V1_STR}/erp/product-units",
            headers=unit_headers,
            json=unit_payload,
        )
        assert unit.status_code == 200
        unit_id = unit.json()["id"]
        replayed_unit = scoped_client.post(
            f"{settings.API_V1_STR}/erp/product-units",
            headers=unit_headers,
            json=unit_payload,
        )
        assert replayed_unit.status_code == 200
        assert replayed_unit.json()["id"] == unit_id
        conflicting_unit = scoped_client.post(
            f"{settings.API_V1_STR}/erp/product-units",
            headers=unit_headers,
            json={**unit_payload, "name": f"Other unit {suffix}"},
        )
        assert conflicting_unit.status_code == 409

        category = scoped_client.post(
            f"{settings.API_V1_STR}/erp/product-categories",
            headers=superuser_token_headers,
            json={"code": f"hardware-{suffix}", "name": "Hardware"},
        )
        assert category.status_code == 200
        category_id = category.json()["id"]

        product = scoped_client.post(
            f"{settings.API_V1_STR}/erp/products",
            headers=superuser_token_headers,
            json={
                "code": f"bolt-m8-{suffix}",
                "name": "M8 bolt",
                "category_id": category_id,
                "expiry_days": 365,
                "remark": "Corrosion-resistant",
                "unit_id": unit_id,
                "weight": "0.125",
            },
        )
        assert product.status_code == 200
        assert product.json()["unit_id"] == unit_id
        assert Decimal(product.json()["weight"]) == Decimal("0.125")
        assert product.json()["expiry_days"] == 365
        assert product.json()["remark"] == "Corrosion-resistant"

        invalid_product = scoped_client.post(
            f"{settings.API_V1_STR}/erp/products",
            headers=superuser_token_headers,
            json={
                "code": f"invalid-weight-{suffix}",
                "name": "Invalid weight",
                "unit_id": unit_id,
                "weight": "-1",
            },
        )
        assert invalid_product.status_code == 422

        warehouse = scoped_client.post(
            f"{settings.API_V1_STR}/erp/warehouses",
            headers=superuser_token_headers,
            json={"code": f"main-{suffix}", "name": f"Main warehouse {suffix}"},
        )
        assert warehouse.status_code == 200

        listed = scoped_client.get(
            f"{settings.API_V1_STR}/erp/products",
            headers=superuser_token_headers,
        )
        assert listed.status_code == 200
        assert product.json()["id"] in {entry["id"] for entry in listed.json()["items"]}

        duplicate = scoped_client.post(
            f"{settings.API_V1_STR}/erp/product-units",
            headers=superuser_token_headers,
            json={"code": f"piece-{suffix}", "name": "Duplicate"},
        )
        assert duplicate.status_code == 409

        blocked_delete = scoped_client.delete(
            f"{settings.API_V1_STR}/erp/product-units/{unit_id}",
            headers=superuser_token_headers,
        )
        assert blocked_delete.status_code == 409


def test_erp_master_data_normalizes_and_enforces_business_unique_values(
    superuser_token_headers: dict[str, str], db: Session
) -> None:
    suffix = uuid.uuid4().hex[:12]
    with erp_client(db) as scoped_client:
        unit = scoped_client.post(
            f"{settings.API_V1_STR}/erp/product-units",
            headers=superuser_token_headers,
            json={"code": f"unit-{suffix}", "name": f"  Each {suffix}  "},
        )
        assert unit.status_code == 200
        assert unit.json()["name"] == f"Each {suffix}"
        duplicate_unit = scoped_client.post(
            f"{settings.API_V1_STR}/erp/product-units",
            headers=superuser_token_headers,
            json={"code": f"unit-duplicate-{suffix}", "name": f"Each {suffix}"},
        )
        assert duplicate_unit.status_code == 409

        category = scoped_client.post(
            f"{settings.API_V1_STR}/erp/product-categories",
            headers=superuser_token_headers,
            json={"code": f"category-{suffix}", "name": "Category"},
        )
        assert category.status_code == 200
        product_payload = {
            "category_id": category.json()["id"],
            "unit_id": unit.json()["id"],
            "barcode": f" barcode-{suffix} ",
        }
        first_product = scoped_client.post(
            f"{settings.API_V1_STR}/erp/products",
            headers=superuser_token_headers,
            json={"code": f"product-{suffix}", "name": "Product", **product_payload},
        )
        assert first_product.status_code == 200
        assert first_product.json()["barcode"] == f"barcode-{suffix}"
        duplicate_product = scoped_client.post(
            f"{settings.API_V1_STR}/erp/products",
            headers=superuser_token_headers,
            json={
                "code": f"product-duplicate-{suffix}",
                "name": "Duplicate product",
                **product_payload,
            },
        )
        assert duplicate_product.status_code == 409

        warehouse = scoped_client.post(
            f"{settings.API_V1_STR}/erp/warehouses",
            headers=superuser_token_headers,
            json={"code": f"warehouse-{suffix}", "name": f"  Main warehouse {suffix}  "},
        )
        assert warehouse.status_code == 200
        duplicate_warehouse = scoped_client.post(
            f"{settings.API_V1_STR}/erp/warehouses",
            headers=superuser_token_headers,
            json={"code": f"warehouse-duplicate-{suffix}", "name": f"Main warehouse {suffix}"},
        )
        assert duplicate_warehouse.status_code == 409


def test_erp_master_data_export_is_audited_and_escapes_csv_formulas(
    superuser_token_headers: dict[str, str], db: Session
) -> None:
    suffix = uuid.uuid4().hex[:12]
    with erp_client(db) as scoped_client:
        created = scoped_client.post(
            f"{settings.API_V1_STR}/erp/product-units",
            headers=superuser_token_headers,
            json={"code": f"export-{suffix}", "name": "=SUM(A1:A2)"},
        )
        assert created.status_code == 200
        excluded = scoped_client.post(
            f"{settings.API_V1_STR}/erp/product-units",
            headers=superuser_token_headers,
            json={"code": f"excluded-{suffix}", "name": "Excluded"},
        )
        assert excluded.status_code == 200

        exported = scoped_client.get(
            f"{settings.API_V1_STR}/erp/product-units/export",
            headers=superuser_token_headers,
            params={"keyword": f"export-{suffix}"},
        )
        assert exported.status_code == 200
        assert exported.headers["content-type"].startswith("text/csv")
        assert "'=SUM(A1:A2)" in exported.text
        assert f"excluded-{suffix}" not in exported.text

        audit = scoped_client.get(
            f"{settings.API_V1_STR}/erp/action-logs",
            headers=superuser_token_headers,
            params={"resource_type": "product_unit_export", "action": "exported"},
        )
        assert audit.status_code == 200
        assert audit.json()["total"] >= 1


def test_erp_warehouse_user_grants_replace_the_granted_user_set(
    superuser_token_headers: dict[str, str], db: Session
) -> None:
    suffix = uuid.uuid4().hex[:12]
    assignee = db.exec(select(User).where(User.email == settings.FIRST_SUPERUSER)).one()
    with erp_client(db) as scoped_client:
        warehouse = scoped_client.post(
            f"{settings.API_V1_STR}/erp/warehouses",
            headers=superuser_token_headers,
            json={"code": f"grant-{suffix}", "name": f"Granted warehouse {suffix}"},
        )
        assert warehouse.status_code == 200
        resource_id = warehouse.json()["id"]
        replaced = scoped_client.put(
            f"{settings.API_V1_STR}/erp/warehouses/{resource_id}/users",
            headers=superuser_token_headers,
            json={"user_ids": [str(assignee.id)]},
        )
        assert replaced.status_code == 200
        assert [item["user_id"] for item in replaced.json()["items"]] == [str(assignee.id)]
        listed = scoped_client.get(
            f"{settings.API_V1_STR}/erp/warehouses/{resource_id}/users",
            headers=superuser_token_headers,
        )
        assert listed.status_code == 200
        assert [item["user_id"] for item in listed.json()["items"]] == [str(assignee.id)]
        cleared = scoped_client.put(
            f"{settings.API_V1_STR}/erp/warehouses/{resource_id}/users",
            headers=superuser_token_headers,
            json={"user_ids": []},
        )
        assert cleared.status_code == 200
        assert cleared.json()["items"] == []


def test_erp_warehouse_default_is_unique_and_referenced_records_block_deletion(
    superuser_token_headers: dict[str, str], db: Session
) -> None:
    suffix = uuid.uuid4().hex[:12]
    with erp_client(db) as scoped_client:
        first = scoped_client.post(
            f"{settings.API_V1_STR}/erp/warehouses",
            headers=superuser_token_headers,
            json={"code": f"default-a-{suffix}", "is_default": True, "name": f"Default A {suffix}"},
        )
        second = scoped_client.post(
            f"{settings.API_V1_STR}/erp/warehouses",
            headers=superuser_token_headers,
            json={"code": f"default-b-{suffix}", "is_default": True, "name": f"Default B {suffix}"},
        )
        assert first.status_code == second.status_code == 200
        warehouses = scoped_client.get(
            f"{settings.API_V1_STR}/erp/warehouses",
            headers=superuser_token_headers,
            params={"keyword": suffix},
        )
        assert warehouses.status_code == 200
        defaults = [item["id"] for item in warehouses.json()["items"] if item["is_default"]]
        assert defaults == [second.json()["id"]]

        unit = scoped_client.post(
            f"{settings.API_V1_STR}/erp/product-units",
            headers=superuser_token_headers,
            json={"code": f"warehouse-unit-{suffix}", "name": f"Warehouse unit {suffix}"},
        )
        category_id = create_product_category(
            client=scoped_client, headers=superuser_token_headers, suffix=suffix
        )
        product = scoped_client.post(
            f"{settings.API_V1_STR}/erp/products",
            headers=superuser_token_headers,
            json={
                "code": f"warehouse-product-{suffix}",
                "name": "Warehouse product",
                "category_id": category_id,
                "unit_id": unit.json()["id"],
            },
        )
        document = scoped_client.post(
            f"{settings.API_V1_STR}/erp/stock-ins",
            headers=superuser_token_headers,
            json={
                "items": [
                    {
                        "product_id": product.json()["id"],
                        "quantity": "1",
                        "warehouse_id": second.json()["id"],
                    }
                ]
            },
        )
        assert all(response.status_code == 200 for response in (unit, product, document))
        blocked = scoped_client.delete(
            f"{settings.API_V1_STR}/erp/warehouses/{second.json()['id']}",
            headers=superuser_token_headers,
        )
        assert blocked.status_code == 409


def test_erp_stock_document_scope_hides_documents_with_ungranted_warehouses(
    superuser_token_headers: dict[str, str], db: Session
) -> None:
    suffix = uuid.uuid4().hex[:12]
    with erp_client(db) as scoped_client:
        unit = scoped_client.post(
            f"{settings.API_V1_STR}/erp/product-units",
            headers=superuser_token_headers,
            json={"code": f"scope-unit-{suffix}", "name": f"Scope unit {suffix}"},
        )
        first_warehouse = scoped_client.post(
            f"{settings.API_V1_STR}/erp/warehouses",
            headers=superuser_token_headers,
            json={"code": f"scope-a-{suffix}", "name": f"Authorized warehouse {suffix}"},
        )
        second_warehouse = scoped_client.post(
            f"{settings.API_V1_STR}/erp/warehouses",
            headers=superuser_token_headers,
            json={"code": f"scope-b-{suffix}", "name": f"Unauthorized warehouse {suffix}"},
        )
        category_id = create_product_category(
            client=scoped_client, headers=superuser_token_headers, suffix=suffix
        )
        product = scoped_client.post(
            f"{settings.API_V1_STR}/erp/products",
            headers=superuser_token_headers,
            json={
                "code": f"scope-product-{suffix}",
                "name": "Scope product",
                "category_id": category_id,
                "unit_id": unit.json()["id"],
            },
        )
        assert all(
            response.status_code == 200
            for response in (unit, first_warehouse, second_warehouse, product)
        )
        allowed_document = scoped_client.post(
            f"{settings.API_V1_STR}/erp/stock-ins",
            headers=superuser_token_headers,
            json={
                "items": [
                    {
                        "product_id": product.json()["id"],
                        "warehouse_id": first_warehouse.json()["id"],
                        "quantity": "1",
                    }
                ]
            },
        )
        mixed_document = scoped_client.post(
            f"{settings.API_V1_STR}/erp/stock-ins",
            headers=superuser_token_headers,
            json={
                "items": [
                    {
                        "product_id": product.json()["id"],
                        "warehouse_id": first_warehouse.json()["id"],
                        "quantity": "1",
                    },
                    {
                        "product_id": product.json()["id"],
                        "warehouse_id": second_warehouse.json()["id"],
                        "quantity": "1",
                    },
                ]
            },
        )
        assert allowed_document.status_code == 200
        assert mixed_document.status_code == 200
        tenant = db.exec(select(Tenant).where(Tenant.code == "default")).one()
        principal = Principal(id=uuid.uuid4(), is_superuser=False)
        with ErpTenantUnitOfWork(session=db, tenant_id=tenant.id) as uow:
            scope = warehouse_document_scope_filter(
                current_principal=principal,
                document_id_column=StockIn.id,
                item_document_id_column=StockInItem.stock_in_id,
                item_id_column=StockInItem.id,
                warehouse_columns=(StockInItem.warehouse_id,),
            )
            assert scope is not None
            assert uow.session.exec(
                select(StockIn.id).where(
                    StockIn.id.in_(
                        [
                            uuid.UUID(allowed_document.json()["id"]),
                            uuid.UUID(mixed_document.json()["id"]),
                        ]
                    ),
                    scope,
                )
            ).all() == []
            uow.session.add(
                WarehouseUserGrant(
                    tenant_id=tenant.id,
                    warehouse_id=uuid.UUID(first_warehouse.json()["id"]),
                    user_id=principal.id,
                    granted_by=principal.id,
                )
            )
            uow.session.commit()
            visible = set(
                uow.session.exec(
                    select(StockIn.id).where(
                        StockIn.id.in_(
                            [
                                uuid.UUID(allowed_document.json()["id"]),
                                uuid.UUID(mixed_document.json()["id"]),
                            ]
                        ),
                        scope,
                    )
                ).all()
            )
        assert visible == {uuid.UUID(allowed_document.json()["id"])}


def test_erp_stock_exports_write_audit_records(
    superuser_token_headers: dict[str, str], db: Session
) -> None:
    suffix = uuid.uuid4().hex[:12]
    with erp_client(db) as scoped_client:
        unit = scoped_client.post(
            f"{settings.API_V1_STR}/erp/product-units",
            headers=superuser_token_headers,
            json={"code": f"export-unit-{suffix}", "name": f"Export unit {suffix}"},
        )
        category = scoped_client.post(
            f"{settings.API_V1_STR}/erp/product-categories",
            headers=superuser_token_headers,
            json={"code": f"export-category-{suffix}", "name": "Export category"},
        )
        warehouse = scoped_client.post(
            f"{settings.API_V1_STR}/erp/warehouses",
            headers=superuser_token_headers,
            json={"code": f"export-warehouse-{suffix}", "name": f"Export warehouse {suffix}"},
        )
        product = scoped_client.post(
            f"{settings.API_V1_STR}/erp/products",
            headers=superuser_token_headers,
            json={
                "code": f"export-product-{suffix}",
                "name": "Export product",
                "category_id": category.json()["id"],
                "unit_id": unit.json()["id"],
            },
        )
        assert all(
            response.status_code == 200
            for response in (unit, category, warehouse, product)
        )
        stock_in = scoped_client.post(
            f"{settings.API_V1_STR}/erp/stock-ins",
            headers=superuser_token_headers,
            json={
                "items": [
                    {
                        "product_id": product.json()["id"],
                        "warehouse_id": warehouse.json()["id"],
                        "quantity": "2",
                    }
                ]
            },
        )
        assert stock_in.status_code == 200
        assert scoped_client.post(
            f"{settings.API_V1_STR}/erp/stock-ins/{stock_in.json()['id']}/approve",
            headers=superuser_token_headers,
            json={"expected_version": 1},
        ).status_code == 200
        balances_export = scoped_client.get(
            f"{settings.API_V1_STR}/erp/stock-balances/export",
            headers=superuser_token_headers,
            params={"product_id": product.json()["id"]},
        )
        records_export = scoped_client.get(
            f"{settings.API_V1_STR}/erp/stock-records/export",
            headers=superuser_token_headers,
            params={"product_id": product.json()["id"]},
        )
        assert balances_export.status_code == 200
        assert records_export.status_code == 200
        assert balances_export.headers["content-type"].startswith("text/csv")
        assert records_export.headers["content-type"].startswith("text/csv")
        balances = scoped_client.get(
            f"{settings.API_V1_STR}/erp/stock-balances",
            headers=superuser_token_headers,
            params={"category_id": category.json()["id"]},
        )
        records = scoped_client.get(
            f"{settings.API_V1_STR}/erp/stock-records",
            headers=superuser_token_headers,
            params={
                "ledger_type": "other_in",
                "source_document_no": stock_in.json()["no"],
            },
        )
        invalid_range = scoped_client.get(
            f"{settings.API_V1_STR}/erp/stock-records",
            headers=superuser_token_headers,
            params={
                "occurred_from": "2026-01-02T00:00:00+00:00",
                "occurred_to": "2026-01-01T00:00:00+00:00",
            },
        )
        assert balances.status_code == records.status_code == 200
        assert invalid_range.status_code == 422
        assert any(
                item["product_id"] == product.json()["id"]
                and item["product_name"] == "Export product"
                and item["warehouse_name"] == f"Export warehouse {suffix}"
            for item in balances.json()["items"]
        )
        assert [item["source_document_no"] for item in records.json()["items"]] == [
            stock_in.json()["no"]
        ]
        category_export = scoped_client.get(
            f"{settings.API_V1_STR}/erp/stock-balances/export",
            headers=superuser_token_headers,
            params={"category_id": category.json()["id"]},
        )
        assert category_export.status_code == 200
        assert f"export-product-{suffix}" in category_export.text
        for resource_type in ("stock_balance_export", "stock_ledger_export"):
            logs = scoped_client.get(
                f"{settings.API_V1_STR}/erp/action-logs",
                headers=superuser_token_headers,
                params={"resource_type": resource_type, "action": "exported"},
            )
            assert logs.status_code == 200
            assert any(item["metadata_json"]["product_id"] == product.json()["id"] for item in logs.json()["items"])


def test_erp_stock_document_list_and_export_share_filters(
    superuser_token_headers: dict[str, str], db: Session
) -> None:
    suffix = uuid.uuid4().hex[:12]
    with erp_client(db) as scoped_client:
        unit = scoped_client.post(
            f"{settings.API_V1_STR}/erp/product-units",
            headers=superuser_token_headers,
            json={"code": f"stock-filter-unit-{suffix}", "name": f"Stock filter unit {suffix}"},
        )
        source = scoped_client.post(
            f"{settings.API_V1_STR}/erp/warehouses",
            headers=superuser_token_headers,
            json={"code": f"stock-filter-source-{suffix}", "name": f"Stock filter source {suffix}"},
        )
        destination = scoped_client.post(
            f"{settings.API_V1_STR}/erp/warehouses",
            headers=superuser_token_headers,
            json={"code": f"stock-filter-destination-{suffix}", "name": f"Stock filter destination {suffix}"},
        )
        category_id = create_product_category(
            client=scoped_client, headers=superuser_token_headers, suffix=suffix
        )
        product = scoped_client.post(
            f"{settings.API_V1_STR}/erp/products",
            headers=superuser_token_headers,
            json={
                "code": f"stock-filter-product-{suffix}",
                "name": "Stock filter product",
                "category_id": category_id,
                "unit_id": unit.json()["id"],
            },
        )
        assert all(
            response.status_code == 200
            for response in (unit, source, destination, product)
        )

        stock_in = scoped_client.post(
            f"{settings.API_V1_STR}/erp/stock-ins",
            headers=superuser_token_headers,
            json={
                "items": [
                    {
                        "product_id": product.json()["id"],
                        "quantity": "1",
                        "warehouse_id": source.json()["id"],
                    }
                ],
                "remark": f"stock filter {suffix}",
            },
        )
        stock_out = scoped_client.post(
            f"{settings.API_V1_STR}/erp/stock-outs",
            headers=superuser_token_headers,
            json={
                "items": [
                    {
                        "product_id": product.json()["id"],
                        "quantity": "1",
                        "warehouse_id": source.json()["id"],
                    }
                ],
                "remark": f"stock filter {suffix}",
            },
        )
        stock_move = scoped_client.post(
            f"{settings.API_V1_STR}/erp/stock-moves",
            headers=superuser_token_headers,
            json={
                "items": [
                    {
                        "from_warehouse_id": source.json()["id"],
                        "product_id": product.json()["id"],
                        "quantity": "1",
                        "to_warehouse_id": destination.json()["id"],
                    }
                ],
                "remark": f"stock filter {suffix}",
            },
        )
        stock_check = scoped_client.post(
            f"{settings.API_V1_STR}/erp/stock-checks",
            headers=superuser_token_headers,
            json={
                "items": [
                    {
                        "actual_quantity": "0",
                        "product_id": product.json()["id"],
                        "warehouse_id": source.json()["id"],
                    }
                ],
                "remark": f"stock filter {suffix}",
            },
        )
        assert all(
            response.status_code == 200
            for response in (stock_in, stock_out, stock_move, stock_check)
        )

        for list_path, export_path, document in (
            (
                f"{settings.API_V1_STR}/erp/stock-ins",
                f"{settings.API_V1_STR}/erp/stock-ins/export",
                stock_in.json(),
            ),
            (
                f"{settings.API_V1_STR}/erp/stock-outs",
                f"{settings.API_V1_STR}/erp/stock-outs/export",
                stock_out.json(),
            ),
            (
                f"{settings.API_V1_STR}/erp/stock-moves",
                f"{settings.API_V1_STR}/erp/stock-moves/export",
                stock_move.json(),
            ),
            (
                f"{settings.API_V1_STR}/erp/stock-checks",
                f"{settings.API_V1_STR}/erp/stock-checks/export",
                stock_check.json(),
            ),
        ):
            assert_document_list_and_export_match(
                client=scoped_client,
                headers=superuser_token_headers,
                list_path=list_path,
                export_path=export_path,
                document=document,
                params={
                    "keyword": str(document["no"]),
                    "product_id": product.json()["id"],
                    "remark": f"stock filter {suffix}",
                    "status": "draft",
                    "warehouse_id": source.json()["id"],
                },
            )


def test_erp_statistics_and_reconciliation_detect_stock_balance_differences(
    superuser_token_headers: dict[str, str], db: Session
) -> None:
    suffix = uuid.uuid4().hex[:12]
    with erp_client(db) as scoped_client:
        unit = scoped_client.post(
            f"{settings.API_V1_STR}/erp/product-units",
            headers=superuser_token_headers,
            json={"code": f"reconcile-unit-{suffix}", "name": f"Reconcile unit {suffix}"},
        )
        warehouse = scoped_client.post(
            f"{settings.API_V1_STR}/erp/warehouses",
            headers=superuser_token_headers,
            json={"code": f"reconcile-warehouse-{suffix}", "name": f"Reconcile warehouse {suffix}"},
        )
        category_id = create_product_category(
            client=scoped_client, headers=superuser_token_headers, suffix=suffix
        )
        product = scoped_client.post(
            f"{settings.API_V1_STR}/erp/products",
            headers=superuser_token_headers,
            json={
                "code": f"reconcile-product-{suffix}",
                "name": "Reconcile product",
                "category_id": category_id,
                "unit_id": unit.json()["id"],
            },
        )
        assert all(response.status_code == 200 for response in (unit, warehouse, product))
        stock_in = scoped_client.post(
            f"{settings.API_V1_STR}/erp/stock-ins",
            headers=superuser_token_headers,
            json={
                "items": [
                    {
                        "product_id": product.json()["id"],
                        "warehouse_id": warehouse.json()["id"],
                        "quantity": "3",
                    }
                ]
            },
        )
        assert stock_in.status_code == 200
        assert scoped_client.post(
            f"{settings.API_V1_STR}/erp/stock-ins/{stock_in.json()['id']}/approve",
            headers=superuser_token_headers,
            json={"expected_version": 1},
        ).status_code == 200
        summary = scoped_client.get(
            f"{settings.API_V1_STR}/erp/statistics/summary",
            headers=superuser_token_headers,
        )
        assert summary.status_code == 200
        assert Decimal(summary.json()["today"]["purchase_amount"]) >= Decimal("0")
        series = scoped_client.get(
            f"{settings.API_V1_STR}/erp/statistics/time-series",
            headers=superuser_token_headers,
            params={"type": "sale", "start": "2000-01-01", "end": "2000-12-31"},
        )
        assert series.status_code == 200
        assert series.json()["items"] == []
        first_run = scoped_client.post(
            f"{settings.API_V1_STR}/erp/reconciliation-runs",
            headers={**superuser_token_headers, "Idempotency-Key": f"reconcile-{suffix}"},
        )
        assert first_run.status_code == 200
        baseline_stock_difference_count = first_run.json()["stock_difference_count"]
        assert first_run.json()["status"] in {"passed", "failed"}
        replay = scoped_client.post(
            f"{settings.API_V1_STR}/erp/reconciliation-runs",
            headers={**superuser_token_headers, "Idempotency-Key": f"reconcile-{suffix}"},
        )
        assert replay.status_code == 200
        assert replay.json()["id"] == first_run.json()["id"]
        tenant = db.exec(select(Tenant).where(Tenant.code == "default")).one()
        with ErpTenantUnitOfWork(session=db, tenant_id=tenant.id):
            balance = db.exec(
                select(StockBalance).where(
                    StockBalance.product_id == uuid.UUID(product.json()["id"]),
                    StockBalance.warehouse_id == uuid.UUID(warehouse.json()["id"]),
                )
            ).one()
            balance.quantity += Decimal("1")
            db.add(balance)
            db.commit()
        failed_run = scoped_client.post(
            f"{settings.API_V1_STR}/erp/reconciliation-runs",
            headers={
                **superuser_token_headers,
                "Idempotency-Key": f"reconcile-failed-{suffix}",
            },
        )
        assert failed_run.status_code == 200
        assert failed_run.json()["status"] == "failed"
        assert (
            failed_run.json()["stock_difference_count"]
            >= baseline_stock_difference_count + 1
        )
        latest = scoped_client.get(
            f"{settings.API_V1_STR}/erp/reconciliation-runs/latest",
            headers=superuser_token_headers,
        )
        assert latest.status_code == 200
        assert latest.json()["id"] == failed_run.json()["id"]


def test_erp_counterparty_crud_enforces_name_and_tax_rate_rules(
    superuser_token_headers: dict[str, str], db: Session
) -> None:
    suffix = uuid.uuid4().hex[:12]
    with erp_client(db) as scoped_client:
        supplier = scoped_client.post(
            f"{settings.API_V1_STR}/erp/suppliers",
            headers=superuser_token_headers,
            json={
                "name": f"Supplier {suffix}",
                "contact_name": "Jane",
                "email": "jane@example.com",
                "bank_account": f"6222{suffix}7890",
                "tax_rate": "13",
            },
        )
        assert supplier.status_code == 200
        supplier_id = supplier.json()["id"]
        assert Decimal(supplier.json()["tax_rate"]) == Decimal("13")
        assert supplier.json()["bank_account_masked"] == "****7890"
        assert "bank_account" not in supplier.json()
        tenant = db.exec(select(Tenant).where(Tenant.code == "default")).one()
        with ErpTenantUnitOfWork(session=db, tenant_id=tenant.id):
            supplier_record = db.get(Supplier, uuid.UUID(supplier_id))
            assert supplier_record is not None
            assert supplier_record.bank_account_encrypted is not None
            assert f"6222{suffix}7890" not in supplier_record.bank_account_encrypted
        sensitive_supplier = scoped_client.get(
            f"{settings.API_V1_STR}/erp/suppliers/{supplier_id}/sensitive",
            headers=superuser_token_headers,
        )
        assert sensitive_supplier.status_code == 200
        assert sensitive_supplier.json()["bank_account"] == f"6222{suffix}7890"

        duplicate_supplier = scoped_client.post(
            f"{settings.API_V1_STR}/erp/suppliers",
            headers=superuser_token_headers,
            json={"name": f"Supplier {suffix}"},
        )
        assert duplicate_supplier.status_code == 409

        customer = scoped_client.post(
            f"{settings.API_V1_STR}/erp/customers",
            headers=superuser_token_headers,
            json={
                "name": f"Customer {suffix}",
                "tax_rate": "6",
                "bank_account": f"9558{suffix}5678",
            },
        )
        assert customer.status_code == 200
        customer_id = customer.json()["id"]
        assert customer.json()["bank_account_masked"] == "****5678"
        with ErpTenantUnitOfWork(session=db, tenant_id=tenant.id):
            customer_record = db.get(Customer, uuid.UUID(customer_id))
            assert customer_record is not None
            assert customer_record.bank_account_encrypted is not None
            assert f"9558{suffix}5678" not in customer_record.bank_account_encrypted
        sensitive_customer = scoped_client.get(
            f"{settings.API_V1_STR}/erp/customers/{customer_id}/sensitive",
            headers=superuser_token_headers,
        )
        assert sensitive_customer.status_code == 200
        assert sensitive_customer.json()["bank_account"] == f"9558{suffix}5678"

        invalid_tax_rate = scoped_client.patch(
            f"{settings.API_V1_STR}/erp/customers/{customer_id}",
            headers=superuser_token_headers,
            json={"tax_rate": "101"},
        )
        assert invalid_tax_rate.status_code == 422

        updated_supplier = scoped_client.patch(
            f"{settings.API_V1_STR}/erp/suppliers/{supplier_id}",
            headers=superuser_token_headers,
            json={"is_active": False, "remark": "Do not use for new orders"},
        )
        assert updated_supplier.status_code == 200
        assert updated_supplier.json()["is_active"] is False

        listed_customers = scoped_client.get(
            f"{settings.API_V1_STR}/erp/customers",
            headers=superuser_token_headers,
            params={"keyword": suffix},
        )
        assert listed_customers.status_code == 200
        assert customer_id in {item["id"] for item in listed_customers.json()["items"]}


def test_erp_settlement_accounts_encrypt_and_mask_account_numbers(
    superuser_token_headers: dict[str, str], db: Session
) -> None:
    suffix = uuid.uuid4().hex[:12]
    first_account_no = f"6222{suffix}7890"
    second_account_no = f"9558{suffix}5678"
    with erp_client(db) as scoped_client:
        first = scoped_client.post(
            f"{settings.API_V1_STR}/erp/settlement-accounts",
            headers=superuser_token_headers,
            json={
                "name": f"Account {suffix}",
                "account_no": first_account_no,
                "is_default": True,
            },
        )
        assert first.status_code == 200
        assert first.json()["account_no_masked"] == f"****{first_account_no[-4:]}"
        assert "account_no" not in first.json()
        sensitive = scoped_client.get(
            f"{settings.API_V1_STR}/erp/settlement-accounts/{first.json()['id']}/sensitive",
            headers=superuser_token_headers,
        )
        assert sensitive.status_code == 200
        assert sensitive.json()["account_no"] == first_account_no
        logs = scoped_client.get(
            f"{settings.API_V1_STR}/erp/action-logs",
            headers=superuser_token_headers,
            params={"resource_id": first.json()["id"], "resource_type": "settlement_account"},
        )
        assert logs.status_code == 200
        assert {entry["action"] for entry in logs.json()["items"]} >= {
            "created",
            "sensitive_viewed",
        }

        duplicate = scoped_client.post(
            f"{settings.API_V1_STR}/erp/settlement-accounts",
            headers=superuser_token_headers,
            json={
                "name": f"Duplicate {suffix}",
                "account_no": first_account_no,
            },
        )
        assert duplicate.status_code == 409

        second = scoped_client.post(
            f"{settings.API_V1_STR}/erp/settlement-accounts",
            headers=superuser_token_headers,
            json={
                "name": f"Second account {suffix}",
                "account_no": second_account_no,
                "is_default": True,
            },
        )
        assert second.status_code == 200
        listed = scoped_client.get(
            f"{settings.API_V1_STR}/erp/settlement-accounts",
            headers=superuser_token_headers,
        )
        assert listed.status_code == 200
        accounts = {item["id"]: item for item in listed.json()["items"]}
        assert accounts[first.json()["id"]]["is_default"] is False
        assert accounts[second.json()["id"]]["is_default"] is True


def test_erp_stock_documents_use_tenant_daily_document_sequences(
    superuser_token_headers: dict[str, str], db: Session
) -> None:
    suffix = uuid.uuid4().hex[:12]
    with erp_client(db) as scoped_client:
        unit = scoped_client.post(
            f"{settings.API_V1_STR}/erp/product-units",
            headers=superuser_token_headers,
            json={"code": f"sequence-unit-{suffix}", "name": f"Unit {suffix}"},
        )
        warehouse = scoped_client.post(
            f"{settings.API_V1_STR}/erp/warehouses",
            headers=superuser_token_headers,
            json={"code": f"sequence-warehouse-{suffix}", "name": f"Warehouse {suffix}"},
        )
        category_id = create_product_category(
            client=scoped_client, headers=superuser_token_headers, suffix=suffix
        )
        product = scoped_client.post(
            f"{settings.API_V1_STR}/erp/products",
            headers=superuser_token_headers,
            json={
                "code": f"sequence-product-{suffix}",
                "name": "Product",
                "category_id": category_id,
                "unit_id": unit.json()["id"],
            },
        )
        assert all(
            response.status_code == 200 for response in (unit, warehouse, product)
        )
        payload = {
            "items": [
                {
                    "product_id": product.json()["id"],
                    "warehouse_id": warehouse.json()["id"],
                    "quantity": "1",
                }
            ]
        }
        first = scoped_client.post(
            f"{settings.API_V1_STR}/erp/stock-ins",
            headers=superuser_token_headers,
            json=payload,
        )
        second = scoped_client.post(
            f"{settings.API_V1_STR}/erp/stock-ins",
            headers=superuser_token_headers,
            json=payload,
        )
        assert first.status_code == second.status_code == 200
        assert first.json()["no"].startswith("QTRK")
        assert int(second.json()["no"][-6:]) == int(first.json()["no"][-6:]) + 1


def test_erp_purchase_order_recalculates_amounts_and_transitions(
    superuser_token_headers: dict[str, str], db: Session
) -> None:
    suffix = uuid.uuid4().hex[:12]
    with erp_client(db) as scoped_client:
        unit = scoped_client.post(
            f"{settings.API_V1_STR}/erp/product-units",
            headers=superuser_token_headers,
            json={"code": f"purchase-unit-{suffix}", "name": f"Unit {suffix}"},
        )
        category_id = create_product_category(
            client=scoped_client, headers=superuser_token_headers, suffix=suffix
        )
        product = scoped_client.post(
            f"{settings.API_V1_STR}/erp/products",
            headers=superuser_token_headers,
            json={
                "code": f"purchase-product-{suffix}",
                "name": "Product",
                "category_id": category_id,
                "unit_id": unit.json()["id"],
            },
        )
        supplier = scoped_client.post(
            f"{settings.API_V1_STR}/erp/suppliers",
            headers=superuser_token_headers,
            json={"name": f"Supplier {suffix}"},
        )
        assert all(response.status_code == 200 for response in (unit, product, supplier))
        future_order = scoped_client.post(
            f"{settings.API_V1_STR}/erp/purchase-orders",
            headers=superuser_token_headers,
            json={
                "business_at": (get_datetime_utc() + timedelta(days=1)).isoformat(),
                "supplier_id": supplier.json()["id"],
                "items": [
                    {
                        "product_id": product.json()["id"],
                        "quantity": "1",
                        "unit_price": "10",
                    }
                ],
            },
        )
        assert future_order.status_code == 422
        order_payload = {
            "supplier_id": supplier.json()["id"],
            "discount_rate": "10",
            "deposit_amount": "5",
            "items": [
                {
                    "product_id": product.json()["id"],
                    "quantity": "2",
                    "unit_price": "10",
                    "tax_rate": "13",
                }
            ],
        }
        order_headers = {
            **superuser_token_headers,
            "Idempotency-Key": f"purchase-order-create-{suffix}",
        }
        order = scoped_client.post(
            f"{settings.API_V1_STR}/erp/purchase-orders",
            headers=order_headers,
            json=order_payload,
        )
        assert order.status_code == 200
        assert order.json()["no"].startswith("CGDD")
        assert Decimal(order.json()["product_amount"]) == Decimal("20")
        assert Decimal(order.json()["tax_amount"]) == Decimal("2.6")
        assert Decimal(order.json()["discount_amount"]) == Decimal("2.26")
        assert Decimal(order.json()["total_amount"]) == Decimal("20.34")
        replayed_order = scoped_client.post(
            f"{settings.API_V1_STR}/erp/purchase-orders",
            headers=order_headers,
            json=order_payload,
        )
        assert replayed_order.status_code == 200
        assert replayed_order.json()["id"] == order.json()["id"]
        conflicting_replay = scoped_client.post(
            f"{settings.API_V1_STR}/erp/purchase-orders",
            headers=order_headers,
            json={**order_payload, "remark": "different request"},
        )
        assert conflicting_replay.status_code == 409

        filtered = scoped_client.get(
            f"{settings.API_V1_STR}/erp/purchase-orders",
            headers=superuser_token_headers,
            params={
                "keyword": order.json()["no"],
                "product_id": product.json()["id"],
                "status": "draft",
                "supplier_id": supplier.json()["id"],
            },
        )
        exported = scoped_client.get(
            f"{settings.API_V1_STR}/erp/purchase-orders/export",
            headers=superuser_token_headers,
            params={
                "keyword": order.json()["no"],
                "product_id": product.json()["id"],
                "status": "draft",
                "supplier_id": supplier.json()["id"],
            },
        )
        assert filtered.status_code == exported.status_code == 200
        assert [item["id"] for item in filtered.json()["items"]] == [order.json()["id"]]
        assert order.json()["no"] in exported.text

        updated = scoped_client.patch(
            f"{settings.API_V1_STR}/erp/purchase-orders/{order.json()['id']}",
            headers=superuser_token_headers,
            json={
                "expected_version": 1,
                "supplier_id": supplier.json()["id"],
                "discount_rate": "10",
                "deposit_amount": "5",
                "items": [
                    {
                        "product_id": product.json()["id"],
                        "quantity": "3",
                        "unit_price": "10",
                        "tax_rate": "13",
                    }
                ],
            },
        )
        assert updated.status_code == 200
        assert updated.json()["version"] == 2
        assert Decimal(updated.json()["product_amount"]) == Decimal("30")
        assert Decimal(updated.json()["tax_amount"]) == Decimal("3.9")
        assert Decimal(updated.json()["total_amount"]) == Decimal("30.51")

        approved = scoped_client.post(
            f"{settings.API_V1_STR}/erp/purchase-orders/{order.json()['id']}/approve",
            headers={
                **superuser_token_headers,
                "Idempotency-Key": f"purchase-order-approve-{suffix}",
            },
            json={"expected_version": 2, "reason": "Test reversal"},
        )
        assert approved.status_code == 200
        assert approved.json()["status"] == "approved"
        replayed_approval = scoped_client.post(
            f"{settings.API_V1_STR}/erp/purchase-orders/{order.json()['id']}/approve",
            headers={
                **superuser_token_headers,
                "Idempotency-Key": f"purchase-order-approve-{suffix}",
            },
            json={"expected_version": 2, "reason": "Test reversal"},
        )
        assert replayed_approval.status_code == 200
        assert replayed_approval.json()["version"] == approved.json()["version"]
        reversed_order = scoped_client.post(
            f"{settings.API_V1_STR}/erp/purchase-orders/{order.json()['id']}/reverse",
            headers={
                **superuser_token_headers,
                "Idempotency-Key": f"purchase-order-reverse-{suffix}",
            },
            json={"expected_version": 3, "reason": "Test purchase order reversal"},
        )
        assert reversed_order.status_code == 200
        assert reversed_order.json()["status"] == "draft"
        replayed_reverse = scoped_client.post(
            f"{settings.API_V1_STR}/erp/purchase-orders/{order.json()['id']}/reverse",
            headers={
                **superuser_token_headers,
                "Idempotency-Key": f"purchase-order-reverse-{suffix}",
            },
            json={"expected_version": 3, "reason": "Test purchase order reversal"},
        )
        assert replayed_reverse.status_code == 200
        assert replayed_reverse.json()["version"] == reversed_order.json()["version"]

        blocked_update = scoped_client.patch(
            f"{settings.API_V1_STR}/erp/purchase-orders/{order.json()['id']}",
            headers=superuser_token_headers,
            json={
                "expected_version": 3,
                "supplier_id": supplier.json()["id"],
                "items": [
                    {
                        "product_id": product.json()["id"],
                        "quantity": "1",
                        "unit_price": "10",
                    }
                ],
            },
        )
        assert blocked_update.status_code == 409

        deletable = scoped_client.post(
            f"{settings.API_V1_STR}/erp/purchase-orders",
            headers=superuser_token_headers,
            json={
                "supplier_id": supplier.json()["id"],
                "items": [
                    {
                        "product_id": product.json()["id"],
                        "quantity": "1",
                        "unit_price": "10",
                    }
                ],
            },
        )
        assert deletable.status_code == 200
        assert scoped_client.delete(
            f"{settings.API_V1_STR}/erp/purchase-orders/{deletable.json()['id']}",
            headers=superuser_token_headers,
        ).status_code == 204


def test_erp_purchase_receipt_and_return_post_inventory_and_source_quantities(
    superuser_token_headers: dict[str, str], db: Session
) -> None:
    suffix = uuid.uuid4().hex[:12]
    with erp_client(db) as scoped_client:
        unit = scoped_client.post(
            f"{settings.API_V1_STR}/erp/product-units",
            headers=superuser_token_headers,
            json={"code": f"receipt-unit-{suffix}", "name": f"Unit {suffix}"},
        )
        warehouse = scoped_client.post(
            f"{settings.API_V1_STR}/erp/warehouses",
            headers=superuser_token_headers,
            json={"code": f"receipt-warehouse-{suffix}", "name": f"Warehouse {suffix}"},
        )
        category_id = create_product_category(
            client=scoped_client, headers=superuser_token_headers, suffix=suffix
        )
        product = scoped_client.post(
            f"{settings.API_V1_STR}/erp/products",
            headers=superuser_token_headers,
            json={
                "code": f"receipt-product-{suffix}",
                "name": "Receipt product",
                "category_id": category_id,
                "unit_id": unit.json()["id"],
            },
        )
        supplier = scoped_client.post(
            f"{settings.API_V1_STR}/erp/suppliers",
            headers=superuser_token_headers,
            json={"name": f"Receipt supplier {suffix}"},
        )
        assert all(
            response.status_code == 200
            for response in (unit, warehouse, product, supplier)
        )
        order = scoped_client.post(
            f"{settings.API_V1_STR}/erp/purchase-orders",
            headers=superuser_token_headers,
            json={
                "supplier_id": supplier.json()["id"],
                "items": [
                    {
                        "product_id": product.json()["id"],
                        "quantity": "5",
                        "unit_price": "12.5",
                        "tax_rate": "13",
                    }
                ],
            },
        )
        assert order.status_code == 200
        assert scoped_client.post(
            f"{settings.API_V1_STR}/erp/purchase-orders/{order.json()['id']}/approve",
            headers=superuser_token_headers,
            json={"expected_version": 1},
        ).status_code == 200
        order_line_id = order.json()["items"][0]["id"]
        receipt_payload = {
            "purchase_order_id": order.json()["id"],
            "discount_rate": "10",
            "other_fee": "1",
            "items": [
                {
                    "purchase_order_item_id": order_line_id,
                    "warehouse_id": warehouse.json()["id"],
                    "quantity": "4",
                }
            ],
        }
        receipt = scoped_client.post(
            f"{settings.API_V1_STR}/erp/purchase-ins",
            headers=superuser_token_headers,
            json=receipt_payload,
        )
        assert receipt.status_code == 200
        assert receipt.json()["no"].startswith("CGRK")
        assert Decimal(receipt.json()["product_amount"]) == Decimal("50")
        assert Decimal(receipt.json()["tax_amount"]) == Decimal("6.5")
        assert Decimal(receipt.json()["discount_amount"]) == Decimal("5.65")
        assert Decimal(receipt.json()["total_amount"]) == Decimal("51.85")
        assert Decimal(receipt.json()["items"][0]["tax_rate"]) == Decimal("13")
        assert scoped_client.post(
            f"{settings.API_V1_STR}/erp/purchase-ins/{receipt.json()['id']}/approve",
            headers=superuser_token_headers,
            json={"expected_version": 1},
        ).status_code == 200
        current_order = scoped_client.get(
            f"{settings.API_V1_STR}/erp/purchase-orders/{order.json()['id']}",
            headers=superuser_token_headers,
        )
        assert Decimal(current_order.json()["items"][0]["received_quantity"]) == Decimal("4")
        balance = scoped_client.get(
            f"{settings.API_V1_STR}/erp/stock-balances",
            headers=superuser_token_headers,
            params={"product_id": product.json()["id"], "warehouse_id": warehouse.json()["id"]},
        )
        assert Decimal(balance.json()["items"][0]["quantity"]) == Decimal("4")

        overflow = scoped_client.post(
            f"{settings.API_V1_STR}/erp/purchase-ins",
            headers=superuser_token_headers,
            json={
                "purchase_order_id": order.json()["id"],
                "items": [
                    {
                        "purchase_order_item_id": order_line_id,
                        "warehouse_id": warehouse.json()["id"],
                        "quantity": "2",
                    }
                ],
            },
        )
        assert overflow.status_code == 409
        purchase_return = scoped_client.post(
            f"{settings.API_V1_STR}/erp/purchase-returns",
            headers=superuser_token_headers,
            json={
                "purchase_in_id": receipt.json()["id"],
                "discount_amount": "1.25",
                "other_fee": "0.75",
                "items": [
                    {
                        "purchase_in_item_id": receipt.json()["items"][0]["id"],
                        "quantity": "2",
                    }
                ],
            },
        )
        assert purchase_return.status_code == 200
        assert purchase_return.json()["no"].startswith("CGTH")
        assert Decimal(purchase_return.json()["product_amount"]) == Decimal("25")
        assert Decimal(purchase_return.json()["tax_amount"]) == Decimal("3.25")
        assert Decimal(purchase_return.json()["discount_amount"]) == Decimal("1.25")
        assert Decimal(purchase_return.json()["total_amount"]) == Decimal("27.75")
        assert scoped_client.post(
            f"{settings.API_V1_STR}/erp/purchase-returns/{purchase_return.json()['id']}/approve",
            headers=superuser_token_headers,
            json={"expected_version": 1},
        ).status_code == 200
        for list_path, export_path, document in (
            (
                f"{settings.API_V1_STR}/erp/purchase-ins",
                f"{settings.API_V1_STR}/erp/purchase-ins/export",
                receipt.json(),
            ),
            (
                f"{settings.API_V1_STR}/erp/purchase-returns",
                f"{settings.API_V1_STR}/erp/purchase-returns/export",
                purchase_return.json(),
            ),
        ):
            assert_document_list_and_export_match(
                client=scoped_client,
                headers=superuser_token_headers,
                list_path=list_path,
                export_path=export_path,
                document=document,
                params={
                    "keyword": str(document["no"]),
                    "product_id": product.json()["id"],
                    "status": "approved",
                    "supplier_id": supplier.json()["id"],
                },
            )
        blocked_reverse = scoped_client.post(
            f"{settings.API_V1_STR}/erp/purchase-ins/{receipt.json()['id']}/reverse",
            headers=superuser_token_headers,
            json={"expected_version": 2, "reason": "Test reversal"},
        )
        assert blocked_reverse.status_code == 409
        reversed_return = scoped_client.post(
            f"{settings.API_V1_STR}/erp/purchase-returns/{purchase_return.json()['id']}/reverse",
            headers=superuser_token_headers,
            json={"expected_version": 2, "reason": "Test reversal"},
        )
        assert reversed_return.status_code == 200
        reversed_receipt = scoped_client.post(
            f"{settings.API_V1_STR}/erp/purchase-ins/{receipt.json()['id']}/reverse",
            headers=superuser_token_headers,
            json={"expected_version": 2, "reason": "Test reversal"},
        )
        assert reversed_receipt.status_code == 200
        current_order = scoped_client.get(
            f"{settings.API_V1_STR}/erp/purchase-orders/{order.json()['id']}",
            headers=superuser_token_headers,
        )
        assert Decimal(current_order.json()["items"][0]["received_quantity"]) == 0
        assert Decimal(current_order.json()["items"][0]["returned_quantity"]) == 0


def test_erp_sale_order_rejects_below_minimum_price(
    superuser_token_headers: dict[str, str], db: Session
) -> None:
    suffix = uuid.uuid4().hex[:12]
    with erp_client(db) as scoped_client:
        unit = scoped_client.post(
            f"{settings.API_V1_STR}/erp/product-units",
            headers=superuser_token_headers,
            json={"code": f"sale-unit-{suffix}", "name": f"Unit {suffix}"},
        )
        category_id = create_product_category(
            client=scoped_client, headers=superuser_token_headers, suffix=suffix
        )
        product = scoped_client.post(
            f"{settings.API_V1_STR}/erp/products",
            headers=superuser_token_headers,
            json={
                "code": f"sale-product-{suffix}",
                "name": "Product",
                "category_id": category_id,
                "unit_id": unit.json()["id"],
                "sale_reference_price": "20",
                "min_sale_price": "15",
            },
        )
        customer = scoped_client.post(
            f"{settings.API_V1_STR}/erp/customers",
            headers=superuser_token_headers,
            json={"name": f"Customer {suffix}"},
        )
        assert all(response.status_code == 200 for response in (unit, product, customer))
        payload = {
            "customer_id": customer.json()["id"],
            "items": [
                {
                    "product_id": product.json()["id"],
                    "quantity": "1",
                    "unit_price": "10",
                }
            ],
        }
        blocked = scoped_client.post(
            f"{settings.API_V1_STR}/erp/sale-orders",
            headers=superuser_token_headers,
            json=payload,
        )
        assert blocked.status_code == 409
        payload["items"][0]["unit_price"] = "20"
        order = scoped_client.post(
            f"{settings.API_V1_STR}/erp/sale-orders",
            headers=superuser_token_headers,
            json=payload,
        )
        assert order.status_code == 200
        assert order.json()["no"].startswith("XSDD")
        blocked_update = scoped_client.patch(
            f"{settings.API_V1_STR}/erp/sale-orders/{order.json()['id']}",
            headers=superuser_token_headers,
            json={
                "expected_version": 1,
                "customer_id": customer.json()["id"],
                "items": [
                    {
                        "product_id": product.json()["id"],
                        "quantity": "2",
                        "unit_price": "10",
                    }
                ],
            },
        )
        assert blocked_update.status_code == 409
        updated = scoped_client.patch(
            f"{settings.API_V1_STR}/erp/sale-orders/{order.json()['id']}",
            headers=superuser_token_headers,
            json={
                "expected_version": 1,
                "customer_id": customer.json()["id"],
                "items": [
                    {
                        "product_id": product.json()["id"],
                        "quantity": "2",
                        "unit_price": "20",
                    }
                ],
            },
        )
        assert updated.status_code == 200
        assert updated.json()["version"] == 2
        assert Decimal(updated.json()["total_amount"]) == Decimal("40")
        approved = scoped_client.post(
            f"{settings.API_V1_STR}/erp/sale-orders/{order.json()['id']}/approve",
            headers=superuser_token_headers,
            json={"expected_version": 2},
        )
        assert approved.status_code == 200
        assert scoped_client.post(
            f"{settings.API_V1_STR}/erp/sale-orders/{order.json()['id']}/reverse",
            headers=superuser_token_headers,
            json={"expected_version": 3, "reason": "Test sale order reversal"},
        ).status_code == 200
        deletable = scoped_client.post(
            f"{settings.API_V1_STR}/erp/sale-orders",
            headers=superuser_token_headers,
            json={
                "customer_id": customer.json()["id"],
                "items": [
                    {
                        "product_id": product.json()["id"],
                        "quantity": "1",
                        "unit_price": "20",
                    }
                ],
            },
        )
        assert deletable.status_code == 200
        assert scoped_client.delete(
            f"{settings.API_V1_STR}/erp/sale-orders/{deletable.json()['id']}",
            headers=superuser_token_headers,
        ).status_code == 204


def test_erp_sale_shipment_and_return_post_inventory_and_source_quantities(
    superuser_token_headers: dict[str, str], db: Session
) -> None:
    suffix = uuid.uuid4().hex[:12]
    with erp_client(db) as scoped_client:
        unit = scoped_client.post(
            f"{settings.API_V1_STR}/erp/product-units",
            headers=superuser_token_headers,
            json={"code": f"shipment-unit-{suffix}", "name": f"Unit {suffix}"},
        )
        warehouse = scoped_client.post(
            f"{settings.API_V1_STR}/erp/warehouses",
            headers=superuser_token_headers,
            json={"code": f"shipment-warehouse-{suffix}", "name": f"Warehouse {suffix}"},
        )
        category_id = create_product_category(
            client=scoped_client, headers=superuser_token_headers, suffix=suffix
        )
        product = scoped_client.post(
            f"{settings.API_V1_STR}/erp/products",
            headers=superuser_token_headers,
            json={
                "code": f"shipment-product-{suffix}",
                "name": "Shipment product",
                "category_id": category_id,
                "unit_id": unit.json()["id"],
            },
        )
        customer = scoped_client.post(
            f"{settings.API_V1_STR}/erp/customers",
            headers=superuser_token_headers,
            json={"name": f"Shipment customer {suffix}"},
        )
        assert all(
            response.status_code == 200
            for response in (unit, warehouse, product, customer)
        )
        opening_stock = scoped_client.post(
            f"{settings.API_V1_STR}/erp/stock-ins",
            headers=superuser_token_headers,
            json={
                "items": [
                    {
                        "product_id": product.json()["id"],
                        "warehouse_id": warehouse.json()["id"],
                        "quantity": "5",
                    }
                ]
            },
        )
        assert opening_stock.status_code == 200
        assert scoped_client.post(
            f"{settings.API_V1_STR}/erp/stock-ins/{opening_stock.json()['id']}/approve",
            headers=superuser_token_headers,
            json={"expected_version": 1},
        ).status_code == 200
        order = scoped_client.post(
            f"{settings.API_V1_STR}/erp/sale-orders",
            headers=superuser_token_headers,
            json={
                "customer_id": customer.json()["id"],
                "items": [
                    {
                        "product_id": product.json()["id"],
                        "quantity": "4",
                        "unit_price": "20",
                        "tax_rate": "13",
                    }
                ],
            },
        )
        assert order.status_code == 200
        assert scoped_client.post(
            f"{settings.API_V1_STR}/erp/sale-orders/{order.json()['id']}/approve",
            headers=superuser_token_headers,
            json={"expected_version": 1},
        ).status_code == 200
        order_line_id = order.json()["items"][0]["id"]
        shipment = scoped_client.post(
            f"{settings.API_V1_STR}/erp/sale-outs",
            headers=superuser_token_headers,
            json={
                "sale_order_id": order.json()["id"],
                "discount_rate": "10",
                "other_deduction": "1",
                "items": [
                    {
                        "sale_order_item_id": order_line_id,
                        "warehouse_id": warehouse.json()["id"],
                        "quantity": "4",
                    }
                ],
            },
        )
        assert shipment.status_code == 200
        assert shipment.json()["no"].startswith("XSCK")
        assert Decimal(shipment.json()["product_amount"]) == Decimal("80")
        assert Decimal(shipment.json()["tax_amount"]) == Decimal("10.4")
        assert Decimal(shipment.json()["discount_amount"]) == Decimal("9.04")
        assert Decimal(shipment.json()["total_amount"]) == Decimal("80.36")
        assert scoped_client.post(
            f"{settings.API_V1_STR}/erp/sale-outs/{shipment.json()['id']}/approve",
            headers=superuser_token_headers,
            json={"expected_version": 1},
        ).status_code == 200
        current_order = scoped_client.get(
            f"{settings.API_V1_STR}/erp/sale-orders/{order.json()['id']}",
            headers=superuser_token_headers,
        )
        assert Decimal(current_order.json()["items"][0]["shipped_quantity"]) == Decimal("4")
        balance = scoped_client.get(
            f"{settings.API_V1_STR}/erp/stock-balances",
            headers=superuser_token_headers,
            params={"product_id": product.json()["id"], "warehouse_id": warehouse.json()["id"]},
        )
        assert Decimal(balance.json()["items"][0]["quantity"]) == Decimal("1")

        sale_return = scoped_client.post(
            f"{settings.API_V1_STR}/erp/sale-returns",
            headers=superuser_token_headers,
            json={
                "sale_out_id": shipment.json()["id"],
                "discount_amount": "2",
                "other_deduction": "0.5",
                "items": [
                    {"sale_out_item_id": shipment.json()["items"][0]["id"], "quantity": "2"}
                ],
            },
        )
        assert sale_return.status_code == 200
        assert sale_return.json()["no"].startswith("XSTH")
        assert Decimal(sale_return.json()["product_amount"]) == Decimal("40")
        assert Decimal(sale_return.json()["tax_amount"]) == Decimal("5.2")
        assert Decimal(sale_return.json()["total_amount"]) == Decimal("42.7")
        assert scoped_client.post(
            f"{settings.API_V1_STR}/erp/sale-returns/{sale_return.json()['id']}/approve",
            headers=superuser_token_headers,
            json={"expected_version": 1},
        ).status_code == 200
        for list_path, export_path, document in (
            (
                f"{settings.API_V1_STR}/erp/sale-outs",
                f"{settings.API_V1_STR}/erp/sale-outs/export",
                shipment.json(),
            ),
            (
                f"{settings.API_V1_STR}/erp/sale-returns",
                f"{settings.API_V1_STR}/erp/sale-returns/export",
                sale_return.json(),
            ),
        ):
            assert_document_list_and_export_match(
                client=scoped_client,
                headers=superuser_token_headers,
                list_path=list_path,
                export_path=export_path,
                document=document,
                params={
                    "customer_id": customer.json()["id"],
                    "keyword": str(document["no"]),
                    "product_id": product.json()["id"],
                    "status": "approved",
                },
            )
        blocked_reverse = scoped_client.post(
            f"{settings.API_V1_STR}/erp/sale-outs/{shipment.json()['id']}/reverse",
            headers=superuser_token_headers,
            json={"expected_version": 2, "reason": "Test reversal"},
        )
        assert blocked_reverse.status_code == 409
        assert scoped_client.post(
            f"{settings.API_V1_STR}/erp/sale-returns/{sale_return.json()['id']}/reverse",
            headers=superuser_token_headers,
            json={"expected_version": 2, "reason": "Test reversal"},
        ).status_code == 200
        assert scoped_client.post(
            f"{settings.API_V1_STR}/erp/sale-outs/{shipment.json()['id']}/reverse",
            headers=superuser_token_headers,
            json={"expected_version": 2, "reason": "Test reversal"},
        ).status_code == 200
        current_order = scoped_client.get(
            f"{settings.API_V1_STR}/erp/sale-orders/{order.json()['id']}",
            headers=superuser_token_headers,
        )
        assert Decimal(current_order.json()["items"][0]["shipped_quantity"]) == 0
        assert Decimal(current_order.json()["items"][0]["returned_quantity"]) == 0


def test_erp_payment_and_receipt_settlement_lock_source_balances(
    superuser_token_headers: dict[str, str], db: Session
) -> None:
    suffix = uuid.uuid4().hex[:12]
    with erp_client(db) as scoped_client:
        unit = scoped_client.post(
            f"{settings.API_V1_STR}/erp/product-units",
            headers=superuser_token_headers,
            json={"code": f"settlement-unit-{suffix}", "name": f"Unit {suffix}"},
        )
        warehouse = scoped_client.post(
            f"{settings.API_V1_STR}/erp/warehouses",
            headers=superuser_token_headers,
            json={"code": f"settlement-warehouse-{suffix}", "name": f"Warehouse {suffix}"},
        )
        category_id = create_product_category(
            client=scoped_client, headers=superuser_token_headers, suffix=suffix
        )
        product = scoped_client.post(
            f"{settings.API_V1_STR}/erp/products",
            headers=superuser_token_headers,
            json={
                "code": f"settlement-product-{suffix}",
                "name": "Settlement product",
                "category_id": category_id,
                "unit_id": unit.json()["id"],
            },
        )
        supplier = scoped_client.post(
            f"{settings.API_V1_STR}/erp/suppliers",
            headers=superuser_token_headers,
            json={"name": f"Settlement supplier {suffix}"},
        )
        customer = scoped_client.post(
            f"{settings.API_V1_STR}/erp/customers",
            headers=superuser_token_headers,
            json={"name": f"Settlement customer {suffix}"},
        )
        account = scoped_client.post(
            f"{settings.API_V1_STR}/erp/settlement-accounts",
            headers=superuser_token_headers,
            json={
                "name": f"Settlement account {suffix}",
                "account_no": f"ACCT-{suffix}",
            },
        )
        assert all(
            response.status_code == 200
            for response in (unit, warehouse, product, supplier, customer, account)
        )
        purchase_order = scoped_client.post(
            f"{settings.API_V1_STR}/erp/purchase-orders",
            headers=superuser_token_headers,
            json={
                "supplier_id": supplier.json()["id"],
                "items": [
                    {
                        "product_id": product.json()["id"],
                        "quantity": "4",
                        "unit_price": "10",
                    }
                ],
            },
        )
        assert purchase_order.status_code == 200
        assert scoped_client.post(
            f"{settings.API_V1_STR}/erp/purchase-orders/{purchase_order.json()['id']}/approve",
            headers=superuser_token_headers,
            json={"expected_version": 1},
        ).status_code == 200
        purchase_in = scoped_client.post(
            f"{settings.API_V1_STR}/erp/purchase-ins",
            headers=superuser_token_headers,
            json={
                "purchase_order_id": purchase_order.json()["id"],
                "items": [
                    {
                        "purchase_order_item_id": purchase_order.json()["items"][0]["id"],
                        "warehouse_id": warehouse.json()["id"],
                        "quantity": "4",
                    }
                ],
            },
        )
        assert purchase_in.status_code == 200
        assert Decimal(purchase_in.json()["total_amount"]) == Decimal("40")
        assert scoped_client.post(
            f"{settings.API_V1_STR}/erp/purchase-ins/{purchase_in.json()['id']}/approve",
            headers=superuser_token_headers,
            json={"expected_version": 1},
        ).status_code == 200
        payment_headers = {
            **superuser_token_headers,
            "Idempotency-Key": f"payment-create-{suffix}",
        }
        payment = scoped_client.post(
            f"{settings.API_V1_STR}/erp/finance-payments",
            headers=payment_headers,
            json={
                "supplier_id": supplier.json()["id"],
                "settlement_account_id": account.json()["id"],
                "discount_amount": "2",
                "items": [
                    {
                        "source_type": "purchase_in",
                        "source_document_id": purchase_in.json()["id"],
                        "settlement_amount": "20",
                    }
                ],
            },
        )
        assert payment.status_code == 200
        assert Decimal(payment.json()["payment_amount"]) == Decimal("18")
        assert Decimal(payment.json()["items"][0]["discount_allocated"]) == Decimal("2")
        replayed_payment = scoped_client.post(
            f"{settings.API_V1_STR}/erp/finance-payments",
            headers=payment_headers,
            json={
                "supplier_id": supplier.json()["id"],
                "settlement_account_id": account.json()["id"],
                "discount_amount": "2",
                "items": [
                    {
                        "source_type": "purchase_in",
                        "source_document_id": purchase_in.json()["id"],
                        "settlement_amount": "20",
                    }
                ],
            },
        )
        assert replayed_payment.status_code == 200
        assert replayed_payment.json()["id"] == payment.json()["id"]
        reused_key = scoped_client.post(
            f"{settings.API_V1_STR}/erp/finance-payments",
            headers=payment_headers,
            json={
                "supplier_id": supplier.json()["id"],
                "settlement_account_id": account.json()["id"],
                "discount_amount": "1",
                "items": [
                    {
                        "source_type": "purchase_in",
                        "source_document_id": purchase_in.json()["id"],
                        "settlement_amount": "20",
                    }
                ],
            },
        )
        assert reused_key.status_code == 409
        assert scoped_client.post(
            f"{settings.API_V1_STR}/erp/finance-payments/{payment.json()['id']}/approve",
            headers={
                **superuser_token_headers,
                "Idempotency-Key": f"payment-approve-{suffix}",
            },
            json={"expected_version": 1},
        ).status_code == 200
        assert_document_list_and_export_match(
            client=scoped_client,
            headers=superuser_token_headers,
            list_path=f"{settings.API_V1_STR}/erp/finance-payments",
            export_path=f"{settings.API_V1_STR}/erp/finance-payments/export",
            document=payment.json(),
            params={
                "keyword": payment.json()["no"],
                "status": "approved",
                "supplier_id": supplier.json()["id"],
            },
        )
        current_purchase_in = scoped_client.get(
            f"{settings.API_V1_STR}/erp/purchase-ins/{purchase_in.json()['id']}",
            headers=superuser_token_headers,
        )
        assert Decimal(current_purchase_in.json()["settled_amount"]) == Decimal("22")
        assert scoped_client.post(
            f"{settings.API_V1_STR}/erp/purchase-ins/{purchase_in.json()['id']}/reverse",
            headers=superuser_token_headers,
            json={"expected_version": 2, "reason": "Test reversal"},
        ).status_code == 409
        overpayment = scoped_client.post(
            f"{settings.API_V1_STR}/erp/finance-payments",
            headers={
                **superuser_token_headers,
                "Idempotency-Key": f"payment-over-{suffix}",
            },
            json={
                "supplier_id": supplier.json()["id"],
                "settlement_account_id": account.json()["id"],
                "items": [
                    {
                        "source_type": "purchase_in",
                        "source_document_id": purchase_in.json()["id"],
                        "settlement_amount": "19",
                    }
                ],
            },
        )
        assert overpayment.status_code == 409
        assert scoped_client.post(
            f"{settings.API_V1_STR}/erp/finance-payments/{payment.json()['id']}/reverse",
            headers={
                **superuser_token_headers,
                "Idempotency-Key": f"payment-reverse-{suffix}",
            },
            json={"expected_version": 2, "reason": "Test reversal"},
        ).status_code == 200
        current_purchase_in = scoped_client.get(
            f"{settings.API_V1_STR}/erp/purchase-ins/{purchase_in.json()['id']}",
            headers=superuser_token_headers,
        )
        assert Decimal(current_purchase_in.json()["settled_amount"]) == 0

        sale_order = scoped_client.post(
            f"{settings.API_V1_STR}/erp/sale-orders",
            headers=superuser_token_headers,
            json={
                "customer_id": customer.json()["id"],
                "items": [
                    {
                        "product_id": product.json()["id"],
                        "quantity": "2",
                        "unit_price": "15",
                    }
                ],
            },
        )
        assert sale_order.status_code == 200
        assert scoped_client.post(
            f"{settings.API_V1_STR}/erp/sale-orders/{sale_order.json()['id']}/approve",
            headers=superuser_token_headers,
            json={"expected_version": 1},
        ).status_code == 200
        sale_out = scoped_client.post(
            f"{settings.API_V1_STR}/erp/sale-outs",
            headers=superuser_token_headers,
            json={
                "sale_order_id": sale_order.json()["id"],
                "items": [
                    {
                        "sale_order_item_id": sale_order.json()["items"][0]["id"],
                        "warehouse_id": warehouse.json()["id"],
                        "quantity": "2",
                    }
                ],
            },
        )
        assert sale_out.status_code == 200
        assert scoped_client.post(
            f"{settings.API_V1_STR}/erp/sale-outs/{sale_out.json()['id']}/approve",
            headers=superuser_token_headers,
            json={"expected_version": 1},
        ).status_code == 200
        receipt = scoped_client.post(
            f"{settings.API_V1_STR}/erp/finance-receipts",
            headers={
                **superuser_token_headers,
                "Idempotency-Key": f"receipt-create-{suffix}",
            },
            json={
                "customer_id": customer.json()["id"],
                "settlement_account_id": account.json()["id"],
                "items": [
                    {
                        "source_type": "sale_out",
                        "source_document_id": sale_out.json()["id"],
                        "settlement_amount": "30",
                    }
                ],
            },
        )
        assert receipt.status_code == 200
        assert receipt.json()["no"].startswith("SKD")
        assert scoped_client.post(
            f"{settings.API_V1_STR}/erp/finance-receipts/{receipt.json()['id']}/approve",
            headers={
                **superuser_token_headers,
                "Idempotency-Key": f"receipt-approve-{suffix}",
            },
            json={"expected_version": 1},
        ).status_code == 200
        assert_document_list_and_export_match(
            client=scoped_client,
            headers=superuser_token_headers,
            list_path=f"{settings.API_V1_STR}/erp/finance-receipts",
            export_path=f"{settings.API_V1_STR}/erp/finance-receipts/export",
            document=receipt.json(),
            params={
                "customer_id": customer.json()["id"],
                "keyword": receipt.json()["no"],
                "status": "approved",
            },
        )
        current_sale_out = scoped_client.get(
            f"{settings.API_V1_STR}/erp/sale-outs/{sale_out.json()['id']}",
            headers=superuser_token_headers,
        )
        assert Decimal(current_sale_out.json()["settled_amount"]) == Decimal("30")
        assert scoped_client.post(
            f"{settings.API_V1_STR}/erp/sale-outs/{sale_out.json()['id']}/reverse",
            headers=superuser_token_headers,
            json={"expected_version": 2, "reason": "Test reversal"},
        ).status_code == 409


def test_erp_document_attachment_prevents_referenced_file_deletion(
    superuser_token_headers: dict[str, str], db: Session
) -> None:
    suffix = uuid.uuid4().hex[:12]
    with erp_client(db) as scoped_client:
        unit = scoped_client.post(
            f"{settings.API_V1_STR}/erp/product-units",
            headers=superuser_token_headers,
            json={"code": f"attachment-unit-{suffix}", "name": f"Attachment unit {suffix}"},
        )
        category = scoped_client.post(
            f"{settings.API_V1_STR}/erp/product-categories",
            headers=superuser_token_headers,
            json={"code": f"attachment-category-{suffix}", "name": "Attachment category"},
        )
        warehouse = scoped_client.post(
            f"{settings.API_V1_STR}/erp/warehouses",
            headers=superuser_token_headers,
            json={"code": f"attachment-warehouse-{suffix}", "name": f"Attachment warehouse {suffix}"},
        )
        product = scoped_client.post(
            f"{settings.API_V1_STR}/erp/products",
            headers=superuser_token_headers,
            json={
                "code": f"attachment-product-{suffix}",
                "name": "Attachment product",
                "category_id": category.json()["id"],
                "unit_id": unit.json()["id"],
            },
        )
        assert all(response.status_code == 200 for response in (unit, category, warehouse, product))
        document = scoped_client.post(
            f"{settings.API_V1_STR}/erp/stock-ins",
            headers=superuser_token_headers,
            json={
                "items": [
                    {
                        "product_id": product.json()["id"],
                        "warehouse_id": warehouse.json()["id"],
                        "quantity": "1",
                    }
                ]
            },
        )
        assert document.status_code == 200
        uploaded = scoped_client.post(
            f"{settings.API_V1_STR}/files/upload",
            headers=superuser_token_headers,
            files={"file": (f"attachment-{suffix}.txt", BytesIO(b"ERP attachment"), "text/plain")},
        )
        assert uploaded.status_code == 200
        attachment = scoped_client.post(
            f"{settings.API_V1_STR}/erp/documents/stock_in/{document.json()['id']}/attachments",
            headers=superuser_token_headers,
            json={"file_id": uploaded.json()["id"], "sort": 2},
        )
        assert attachment.status_code == 200
        assert attachment.json()["file_name"] == f"attachment-{suffix}.txt"
        listed = scoped_client.get(
            f"{settings.API_V1_STR}/erp/documents/stock_in/{document.json()['id']}/attachments",
            headers=superuser_token_headers,
        )
        assert listed.status_code == 200
        assert [item["id"] for item in listed.json()["items"]] == [attachment.json()["id"]]
        assert scoped_client.post(
            f"{settings.API_V1_STR}/erp/stock-ins/{document.json()['id']}/approve",
            headers=superuser_token_headers,
            json={"expected_version": 1},
        ).status_code == 200
        assert scoped_client.post(
            f"{settings.API_V1_STR}/erp/documents/stock_in/{document.json()['id']}/attachments",
            headers=superuser_token_headers,
            json={"file_id": uploaded.json()["id"], "sort": 3},
        ).status_code == 409
        assert scoped_client.delete(
            f"{settings.API_V1_STR}/erp/documents/stock_in/{document.json()['id']}/attachments/{attachment.json()['id']}",
            headers=superuser_token_headers,
        ).status_code == 409
        # Restore draft before the cleanup path removes the attachment and file.
        assert scoped_client.post(
            f"{settings.API_V1_STR}/erp/stock-ins/{document.json()['id']}/reverse",
            headers=superuser_token_headers,
            json={"expected_version": 2, "reason": "Attachment cleanup"},
        ).status_code == 200
        tenant = db.exec(select(Tenant).where(Tenant.code == "default")).one()
        with ErpTenantUnitOfWork(session=db, tenant_id=tenant.id):
            assert count_file_references(
                db, "file", uuid.UUID(uploaded.json()["id"]), tenant.id
            ) == 1
        assert scoped_client.delete(
            f"{settings.API_V1_STR}/erp/documents/stock_in/{document.json()['id']}/attachments/{attachment.json()['id']}",
            headers=superuser_token_headers,
        ).status_code == 204
        assert scoped_client.delete(
            f"{settings.API_V1_STR}/files/{uploaded.json()['id']}",
            headers=superuser_token_headers,
        ).status_code == 204


def test_erp_inventory_posting_reversal_and_insufficient_stock(
    superuser_token_headers: dict[str, str], db: Session
) -> None:
    suffix = uuid.uuid4().hex[:12]
    with erp_client(db) as scoped_client:
        unit = scoped_client.post(
            f"{settings.API_V1_STR}/erp/product-units",
            headers=superuser_token_headers,
            json={"code": f"unit-{suffix}", "name": f"Unit {suffix}"},
        )
        assert unit.status_code == 200
        warehouse = scoped_client.post(
            f"{settings.API_V1_STR}/erp/warehouses",
            headers=superuser_token_headers,
            json={"code": f"warehouse-{suffix}", "name": f"Warehouse {suffix}"},
        )
        assert warehouse.status_code == 200
        category_id = create_product_category(
            client=scoped_client, headers=superuser_token_headers, suffix=suffix
        )
        product = scoped_client.post(
            f"{settings.API_V1_STR}/erp/products",
            headers=superuser_token_headers,
            json={
                "code": f"product-{suffix}",
                "name": "Inventory product",
                "category_id": category_id,
                "unit_id": unit.json()["id"],
            },
        )
        assert product.status_code == 200

        stock_in = scoped_client.post(
            f"{settings.API_V1_STR}/erp/stock-ins",
            headers=superuser_token_headers,
            json={
                "items": [
                    {
                        "product_id": product.json()["id"],
                        "warehouse_id": warehouse.json()["id"],
                        "quantity": "10",
                    }
                ]
            },
        )
        assert stock_in.status_code == 200
        draft_stock_in = scoped_client.post(
            f"{settings.API_V1_STR}/erp/stock-ins",
            headers=superuser_token_headers,
            json={
                "items": [
                    {
                        "product_id": product.json()["id"],
                        "warehouse_id": warehouse.json()["id"],
                        "quantity": "1",
                    }
                ]
            },
        )
        assert draft_stock_in.status_code == 200
        updated_draft = scoped_client.patch(
            f"{settings.API_V1_STR}/erp/stock-ins/{draft_stock_in.json()['id']}",
            headers=superuser_token_headers,
            json={
                "expected_version": 1,
                "remark": "Draft changed",
                "items": [
                    {
                        "product_id": product.json()["id"],
                        "warehouse_id": warehouse.json()["id"],
                        "quantity": "2",
                    }
                ],
            },
        )
        assert updated_draft.status_code == 200
        assert updated_draft.json()["version"] == 2
        assert scoped_client.patch(
            f"{settings.API_V1_STR}/erp/stock-ins/{draft_stock_in.json()['id']}",
            headers=superuser_token_headers,
            json={
                "expected_version": 1,
                "items": [
                    {
                        "product_id": product.json()["id"],
                        "warehouse_id": warehouse.json()["id"],
                        "quantity": "3",
                    }
                ],
            },
        ).status_code == 409
        assert scoped_client.delete(
            f"{settings.API_V1_STR}/erp/stock-ins/{draft_stock_in.json()['id']}",
            headers=superuser_token_headers,
        ).status_code == 204
        approved_in = scoped_client.post(
            f"{settings.API_V1_STR}/erp/stock-ins/{stock_in.json()['id']}/approve",
            headers=superuser_token_headers,
            json={"expected_version": 1},
        )
        assert approved_in.status_code == 200
        assert approved_in.json()["status"] == "approved"
        assert approved_in.json()["version"] == 2

        stock_out = scoped_client.post(
            f"{settings.API_V1_STR}/erp/stock-outs",
            headers=superuser_token_headers,
            json={
                "items": [
                    {
                        "product_id": product.json()["id"],
                        "warehouse_id": warehouse.json()["id"],
                        "quantity": "4",
                    }
                ]
            },
        )
        assert stock_out.status_code == 200
        approved_out = scoped_client.post(
            f"{settings.API_V1_STR}/erp/stock-outs/{stock_out.json()['id']}/approve",
            headers=superuser_token_headers,
            json={"expected_version": 1},
        )
        assert approved_out.status_code == 200
        assert approved_out.json()["version"] == 2

        insufficient = scoped_client.post(
            f"{settings.API_V1_STR}/erp/stock-outs",
            headers=superuser_token_headers,
            json={
                "items": [
                    {
                        "product_id": product.json()["id"],
                        "warehouse_id": warehouse.json()["id"],
                        "quantity": "7",
                    }
                ]
            },
        )
        assert insufficient.status_code == 200
        insufficient_approval = scoped_client.post(
            f"{settings.API_V1_STR}/erp/stock-outs/{insufficient.json()['id']}/approve",
            headers=superuser_token_headers,
            json={"expected_version": 1},
        )
        assert insufficient_approval.status_code == 409

        blocked_reverse = scoped_client.post(
            f"{settings.API_V1_STR}/erp/stock-ins/{stock_in.json()['id']}/reverse",
            headers=superuser_token_headers,
            json={"expected_version": 2, "reason": "Test blocked reversal"},
        )
        assert blocked_reverse.status_code == 409

        missing_reason = scoped_client.post(
            f"{settings.API_V1_STR}/erp/stock-outs/{stock_out.json()['id']}/reverse",
            headers=superuser_token_headers,
            json={"expected_version": 2},
        )
        assert missing_reason.status_code == 422

        reversed_out = scoped_client.post(
            f"{settings.API_V1_STR}/erp/stock-outs/{stock_out.json()['id']}/reverse",
            headers=superuser_token_headers,
            json={"expected_version": 2, "reason": "Test stock out reversal"},
        )
        assert reversed_out.status_code == 200
        assert reversed_out.json()["status"] == "draft"
        assert reversed_out.json()["version"] == 3

        reversed_in = scoped_client.post(
            f"{settings.API_V1_STR}/erp/stock-ins/{stock_in.json()['id']}/reverse",
            headers=superuser_token_headers,
            json={"expected_version": 2, "reason": "Test stock in reversal"},
        )
        assert reversed_in.status_code == 200
        assert reversed_in.json()["status"] == "draft"
        assert reversed_in.json()["version"] == 3

        balances = scoped_client.get(
            f"{settings.API_V1_STR}/erp/stock-balances",
            headers=superuser_token_headers,
            params={"product_id": product.json()["id"]},
        )
        assert balances.status_code == 200
        assert Decimal(str(balances.json()["items"][0]["quantity"])) == Decimal("0")

        records = scoped_client.get(
            f"{settings.API_V1_STR}/erp/stock-records",
            headers=superuser_token_headers,
            params={"product_id": product.json()["id"]},
        )
        assert records.status_code == 200
        assert len(records.json()["items"]) == 4
        assert sum(
            (Decimal(str(record["delta_quantity"])) for record in records.json()["items"]),
            Decimal("0"),
        ) == Decimal("0")


def test_erp_stock_move_posts_both_warehouse_effects(
    superuser_token_headers: dict[str, str], db: Session
) -> None:
    suffix = uuid.uuid4().hex[:12]
    with erp_client(db) as scoped_client:
        unit = scoped_client.post(
            f"{settings.API_V1_STR}/erp/product-units",
            headers=superuser_token_headers,
            json={"code": f"move-unit-{suffix}", "name": f"Move unit {suffix}"},
        )
        source = scoped_client.post(
            f"{settings.API_V1_STR}/erp/warehouses",
            headers=superuser_token_headers,
            json={"code": f"source-{suffix}", "name": f"Source warehouse {suffix}"},
        )
        destination = scoped_client.post(
            f"{settings.API_V1_STR}/erp/warehouses",
            headers=superuser_token_headers,
            json={"code": f"destination-{suffix}", "name": f"Destination warehouse {suffix}"},
        )
        category_id = create_product_category(
            client=scoped_client, headers=superuser_token_headers, suffix=suffix
        )
        product = scoped_client.post(
            f"{settings.API_V1_STR}/erp/products",
            headers=superuser_token_headers,
            json={
                "code": f"move-product-{suffix}",
                "name": "Move product",
                "category_id": category_id,
                "unit_id": unit.json()["id"],
            },
        )
        assert all(
            response.status_code == 200
            for response in (unit, source, destination, product)
        )
        stock_in = scoped_client.post(
            f"{settings.API_V1_STR}/erp/stock-ins",
            headers=superuser_token_headers,
            json={
                "items": [
                    {
                        "product_id": product.json()["id"],
                        "warehouse_id": source.json()["id"],
                        "quantity": "5",
                    }
                ]
            },
        )
        assert stock_in.status_code == 200
        assert scoped_client.post(
            f"{settings.API_V1_STR}/erp/stock-ins/{stock_in.json()['id']}/approve",
            headers=superuser_token_headers,
            json={"expected_version": 1},
        ).status_code == 200

        move = scoped_client.post(
            f"{settings.API_V1_STR}/erp/stock-moves",
            headers=superuser_token_headers,
            json={
                "items": [
                    {
                        "product_id": product.json()["id"],
                        "from_warehouse_id": source.json()["id"],
                        "to_warehouse_id": destination.json()["id"],
                        "quantity": "5",
                    }
                ]
            },
        )
        assert move.status_code == 200
        approved = scoped_client.post(
            f"{settings.API_V1_STR}/erp/stock-moves/{move.json()['id']}/approve",
            headers=superuser_token_headers,
            json={"expected_version": 1},
        )
        assert approved.status_code == 200
        balances = scoped_client.get(
            f"{settings.API_V1_STR}/erp/stock-balances",
            headers=superuser_token_headers,
            params={"product_id": product.json()["id"]},
        )
        quantities = {
            balance["warehouse_id"]: Decimal(str(balance["quantity"]))
            for balance in balances.json()["items"]
        }
        assert quantities[source.json()["id"]] == Decimal("0")
        assert quantities[destination.json()["id"]] == Decimal("5")


def test_erp_stock_check_rejects_stale_snapshot_and_posts_difference(
    superuser_token_headers: dict[str, str], db: Session
) -> None:
    suffix = uuid.uuid4().hex[:12]
    with erp_client(db) as scoped_client:
        unit = scoped_client.post(
            f"{settings.API_V1_STR}/erp/product-units",
            headers=superuser_token_headers,
            json={"code": f"check-unit-{suffix}", "name": f"Check unit {suffix}"},
        )
        warehouse = scoped_client.post(
            f"{settings.API_V1_STR}/erp/warehouses",
            headers=superuser_token_headers,
            json={"code": f"check-warehouse-{suffix}", "name": f"Check warehouse {suffix}"},
        )
        category_id = create_product_category(
            client=scoped_client, headers=superuser_token_headers, suffix=suffix
        )
        product = scoped_client.post(
            f"{settings.API_V1_STR}/erp/products",
            headers=superuser_token_headers,
            json={
                "code": f"check-product-{suffix}",
                "name": "Check product",
                "category_id": category_id,
                "unit_id": unit.json()["id"],
            },
        )
        assert all(
            response.status_code == 200 for response in (unit, warehouse, product)
        )

        stock_in = scoped_client.post(
            f"{settings.API_V1_STR}/erp/stock-ins",
            headers=superuser_token_headers,
            json={
                "items": [
                    {
                        "product_id": product.json()["id"],
                        "warehouse_id": warehouse.json()["id"],
                        "quantity": "5",
                    }
                ]
            },
        )
        assert scoped_client.post(
            f"{settings.API_V1_STR}/erp/stock-ins/{stock_in.json()['id']}/approve",
            headers=superuser_token_headers,
            json={"expected_version": 1},
        ).status_code == 200

        stale_check = scoped_client.post(
            f"{settings.API_V1_STR}/erp/stock-checks",
            headers=superuser_token_headers,
            json={
                "items": [
                    {
                        "product_id": product.json()["id"],
                        "warehouse_id": warehouse.json()["id"],
                        "actual_quantity": "7",
                    }
                ]
            },
        )
        assert stale_check.status_code == 200
        stock_out = scoped_client.post(
            f"{settings.API_V1_STR}/erp/stock-outs",
            headers=superuser_token_headers,
            json={
                "items": [
                    {
                        "product_id": product.json()["id"],
                        "warehouse_id": warehouse.json()["id"],
                        "quantity": "1",
                    }
                ]
            },
        )
        assert scoped_client.post(
            f"{settings.API_V1_STR}/erp/stock-outs/{stock_out.json()['id']}/approve",
            headers=superuser_token_headers,
            json={"expected_version": 1},
        ).status_code == 200
        assert scoped_client.post(
            f"{settings.API_V1_STR}/erp/stock-checks/{stale_check.json()['id']}/approve",
            headers=superuser_token_headers,
            json={"expected_version": 1},
        ).status_code == 409

        current_check = scoped_client.post(
            f"{settings.API_V1_STR}/erp/stock-checks",
            headers=superuser_token_headers,
            json={
                "items": [
                    {
                        "product_id": product.json()["id"],
                        "warehouse_id": warehouse.json()["id"],
                        "actual_quantity": "6",
                    }
                ]
            },
        )
        approved = scoped_client.post(
            f"{settings.API_V1_STR}/erp/stock-checks/{current_check.json()['id']}/approve",
            headers=superuser_token_headers,
            json={"expected_version": 1},
        )
        assert approved.status_code == 200
        reversed_check = scoped_client.post(
            f"{settings.API_V1_STR}/erp/stock-checks/{current_check.json()['id']}/reverse",
            headers=superuser_token_headers,
            json={"expected_version": 2, "reason": "Test reversal"},
        )
        assert reversed_check.status_code == 200
        assert reversed_check.json()["status"] == "draft"
        assert reversed_check.json()["version"] == 3
        balances = scoped_client.get(
            f"{settings.API_V1_STR}/erp/stock-balances",
            headers=superuser_token_headers,
            params={"product_id": product.json()["id"]},
        )
        assert Decimal(str(balances.json()["items"][0]["quantity"])) == Decimal("4")
