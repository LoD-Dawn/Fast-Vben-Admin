"""CSV exports that reuse the same tenant and data-scope predicates as list APIs."""

import csv
import io
import uuid
from collections.abc import Callable
from dataclasses import dataclass
from datetime import date, datetime
from decimal import Decimal
from enum import Enum
from typing import Any

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from sqlalchemy import or_
from sqlalchemy.sql.elements import ColumnElement
from sqlmodel import SQLModel, func, select

from app.modules.erp.application.action_log import record_action
from app.modules.erp.application.document_listing import (
    document_list_filters,
    financial_document_filters,
    stock_document_filters,
)
from app.modules.erp.infrastructure.models import (
    Customer,
    DocumentAction,
    FinancePayment,
    FinanceReceipt,
    Product,
    ProductCategory,
    ProductUnit,
    PurchaseIn,
    PurchaseInItem,
    PurchaseOrder,
    PurchaseOrderItem,
    PurchaseReturn,
    PurchaseReturnItem,
    SaleOrder,
    SaleOrderItem,
    SaleOut,
    SaleOutItem,
    SaleReturn,
    SaleReturnItem,
    SettlementAccount,
    StockCheck,
    StockCheckItem,
    StockIn,
    StockInItem,
    StockMove,
    StockMoveItem,
    StockOut,
    StockOutItem,
    Supplier,
    Warehouse,
)
from app.modules.erp.infrastructure.tenant_uow import ErpTenantUowDep
from app.modules.erp.observability import ErpDocumentCommandMetricRoute
from app.modules.erp.stock_routes import (
    document_scope_filter,
    warehouse_document_scope_filter,
)
from app.platform.web_api import CurrentPrincipal, require_module_access

router = APIRouter(
    prefix="/erp", tags=["erp-exports"], route_class=ErpDocumentCommandMetricRoute
)
_MAX_EXPORT_ROWS = 100_000


def _csv_value(value: object) -> object:
    if value is None:
        return ""
    if isinstance(value, Enum):
        value = value.value
    if isinstance(value, (datetime, date)):
        value = value.isoformat()
    if isinstance(value, Decimal):
        value = str(value)
    if isinstance(value, str) and value[:1] in {"=", "+", "-", "@"}:
        return f"'{value}"
    return value


@dataclass(frozen=True)
class ExportDefinition:
    path: str
    permission: str
    resource_type: str
    file_name: str
    model: type[SQLModel]
    columns: tuple[tuple[str, str], ...]
    scope: Callable[[ErpTenantUowDep, CurrentPrincipal], ColumnElement[bool] | None]
    order_by: Any
    search_fields: tuple[Any, ...] = ()


def _tenant_scope(_uow: ErpTenantUowDep, _principal: CurrentPrincipal) -> None:
    return None


def _owner_scope(model: Any) -> Callable[[ErpTenantUowDep, CurrentPrincipal], ColumnElement[bool]]:
    def scope(uow: ErpTenantUowDep, principal: CurrentPrincipal) -> ColumnElement[bool]:
        return document_scope_filter(
            uow=uow, current_principal=principal, owner_column=model.owner_id
        )

    return scope


def _warehouse_document_scope(
    model: Any, item_model: Any, warehouse_columns: tuple[Any, ...]
) -> Callable[[ErpTenantUowDep, CurrentPrincipal], ColumnElement[bool]]:
    def scope(uow: ErpTenantUowDep, principal: CurrentPrincipal) -> ColumnElement[bool]:
        owner_scope = document_scope_filter(
            uow=uow, current_principal=principal, owner_column=model.owner_id
        )
        warehouse_scope = warehouse_document_scope_filter(
            current_principal=principal,
            document_id_column=model.id,
            item_document_id_column=getattr(item_model, f"{model.__tablename__}_id"),
            item_id_column=item_model.id,
            warehouse_columns=warehouse_columns,
        )
        return owner_scope if warehouse_scope is None else owner_scope & warehouse_scope

    return scope


_EXPORTS = (
    ExportDefinition("product-units", "erp:product-unit:export", "product_unit_export", "product-units.csv", ProductUnit, (("编码", "code"), ("名称", "name"), ("符号", "symbol"), ("状态", "is_active")), _tenant_scope, ProductUnit.code, (ProductUnit.code, ProductUnit.name)),
    ExportDefinition("product-categories", "erp:product-category:export", "product_category_export", "product-categories.csv", ProductCategory, (("编码", "code"), ("名称", "name"), ("父分类 ID", "parent_id"), ("排序", "sort"), ("状态", "is_active")), _tenant_scope, ProductCategory.code, (ProductCategory.code, ProductCategory.name)),
    ExportDefinition("products", "erp:product:export", "product_export", "products.csv", Product, (("编码", "code"), ("名称", "name"), ("条码", "barcode"), ("规格", "specification"), ("采购参考价", "purchase_reference_price"), ("销售参考价", "sale_reference_price"), ("最低售价", "min_sale_price"), ("状态", "is_active")), _tenant_scope, Product.code, (Product.code, Product.name, Product.barcode)),
    ExportDefinition("warehouses", "erp:warehouse:export", "warehouse_export", "warehouses.csv", Warehouse, (("编码", "code"), ("名称", "name"), ("联系人", "contact_name"), ("联系电话", "contact_phone"), ("地址", "address"), ("状态", "is_active")), _tenant_scope, Warehouse.code, (Warehouse.code, Warehouse.name)),
    ExportDefinition("suppliers", "erp:supplier:export", "supplier_export", "suppliers.csv", Supplier, (("供应商名称", "name"), ("联系人", "contact_name"), ("手机号码", "mobile"), ("联系电话", "phone"), ("电子邮箱", "email"), ("状态", "is_active"), ("排序", "sort"), ("备注", "remark")), _tenant_scope, Supplier.name, (Supplier.name, Supplier.contact_name, Supplier.mobile)),
    ExportDefinition("customers", "erp:customer:export", "customer_export", "customers.csv", Customer, (("名称", "name"), ("联系人", "contact_name"), ("手机", "mobile"), ("电话", "phone"), ("税号", "tax_no"), ("税率", "tax_rate"), ("账号末四位", "bank_account_last4"), ("状态", "is_active")), _tenant_scope, Customer.name, (Customer.name, Customer.contact_name, Customer.mobile)),
    ExportDefinition("settlement-accounts", "erp:account:export", "settlement_account_export", "settlement-accounts.csv", SettlementAccount, (("名称", "name"), ("账号末四位", "account_no_last4"), ("默认", "is_default"), ("状态", "is_active"), ("排序", "sort")), _tenant_scope, SettlementAccount.name, (SettlementAccount.name,)),
    ExportDefinition("purchase-orders", "erp:purchase-order:export", "purchase_order_export", "purchase-orders.csv", PurchaseOrder, (("单号", "no"), ("供应商", "supplier_name"), ("状态", "status"), ("业务时间", "business_at"), ("数量", "total_quantity"), ("金额", "total_amount")), _owner_scope(PurchaseOrder), PurchaseOrder.business_at.desc()),
    ExportDefinition("purchase-ins", "erp:purchase-in:export", "purchase_in_export", "purchase-ins.csv", PurchaseIn, (("单号", "no"), ("采购订单", "purchase_order_no"), ("供应商", "supplier_name"), ("状态", "status"), ("业务时间", "business_at"), ("数量", "total_quantity"), ("金额", "total_amount"), ("已结算", "settled_amount")), _owner_scope(PurchaseIn), PurchaseIn.business_at.desc()),
    ExportDefinition("purchase-returns", "erp:purchase-return:export", "purchase_return_export", "purchase-returns.csv", PurchaseReturn, (("单号", "no"), ("采购入库", "purchase_in_no"), ("供应商", "supplier_name"), ("状态", "status"), ("业务时间", "business_at"), ("数量", "total_quantity"), ("金额", "total_amount"), ("已结算", "settled_amount")), _owner_scope(PurchaseReturn), PurchaseReturn.business_at.desc()),
    ExportDefinition("sale-orders", "erp:sale-order:export", "sale_order_export", "sale-orders.csv", SaleOrder, (("单号", "no"), ("客户", "customer_name"), ("状态", "status"), ("业务时间", "business_at"), ("数量", "total_quantity"), ("金额", "total_amount")), _owner_scope(SaleOrder), SaleOrder.business_at.desc()),
    ExportDefinition("sale-outs", "erp:sale-out:export", "sale_out_export", "sale-outs.csv", SaleOut, (("单号", "no"), ("销售订单", "sale_order_no"), ("客户", "customer_name"), ("状态", "status"), ("业务时间", "business_at"), ("数量", "total_quantity"), ("金额", "total_amount"), ("已结算", "settled_amount")), _owner_scope(SaleOut), SaleOut.business_at.desc()),
    ExportDefinition("sale-returns", "erp:sale-return:export", "sale_return_export", "sale-returns.csv", SaleReturn, (("单号", "no"), ("销售出库", "sale_out_no"), ("客户", "customer_name"), ("状态", "status"), ("业务时间", "business_at"), ("数量", "total_quantity"), ("金额", "total_amount"), ("已结算", "settled_amount")), _owner_scope(SaleReturn), SaleReturn.business_at.desc()),
    ExportDefinition("finance-payments", "erp:finance-payment:export", "finance_payment_export", "finance-payments.csv", FinancePayment, (("单号", "no"), ("供应商", "supplier_name"), ("状态", "status"), ("付款金额", "payment_amount"), ("优惠金额", "discount_amount"), ("业务时间", "business_at")), _owner_scope(FinancePayment), FinancePayment.business_at.desc()),
    ExportDefinition("finance-receipts", "erp:finance-receipt:export", "finance_receipt_export", "finance-receipts.csv", FinanceReceipt, (("单号", "no"), ("客户", "customer_name"), ("状态", "status"), ("收款金额", "receipt_amount"), ("优惠金额", "discount_amount"), ("业务时间", "business_at")), _owner_scope(FinanceReceipt), FinanceReceipt.business_at.desc()),
    ExportDefinition("stock-ins", "erp:stock-in:export", "stock_in_export", "stock-ins.csv", StockIn, (("单号", "no"), ("状态", "status"), ("业务时间", "business_at"), ("数量", "total_quantity"), ("备注", "remark")), _warehouse_document_scope(StockIn, StockInItem, (StockInItem.warehouse_id,)), StockIn.business_at.desc()),
    ExportDefinition("stock-outs", "erp:stock-out:export", "stock_out_export", "stock-outs.csv", StockOut, (("单号", "no"), ("状态", "status"), ("业务时间", "business_at"), ("数量", "total_quantity"), ("备注", "remark")), _warehouse_document_scope(StockOut, StockOutItem, (StockOutItem.warehouse_id,)), StockOut.business_at.desc()),
    ExportDefinition("stock-moves", "erp:stock-move:export", "stock_move_export", "stock-moves.csv", StockMove, (("单号", "no"), ("状态", "status"), ("业务时间", "business_at"), ("数量", "total_quantity"), ("备注", "remark")), _warehouse_document_scope(StockMove, StockMoveItem, (StockMoveItem.from_warehouse_id, StockMoveItem.to_warehouse_id)), StockMove.business_at.desc()),
    ExportDefinition("stock-checks", "erp:stock-check:export", "stock_check_export", "stock-checks.csv", StockCheck, (("单号", "no"), ("状态", "status"), ("业务时间", "business_at"), ("数量", "total_quantity"), ("备注", "remark")), _warehouse_document_scope(StockCheck, StockCheckItem, (StockCheckItem.warehouse_id,)), StockCheck.business_at.desc()),
)

_STOCK_DOCUMENT_FILTERS = {
    StockIn: (StockInItem, StockInItem.stock_in_id, (StockInItem.warehouse_id,)),
    StockOut: (StockOutItem, StockOutItem.stock_out_id, (StockOutItem.warehouse_id,)),
    StockMove: (
        StockMoveItem,
        StockMoveItem.stock_move_id,
        (StockMoveItem.from_warehouse_id, StockMoveItem.to_warehouse_id),
    ),
    StockCheck: (StockCheckItem, StockCheckItem.stock_check_id, (StockCheckItem.warehouse_id,)),
}


def _export(definition: ExportDefinition) -> Callable[..., StreamingResponse]:
    def endpoint(
        uow: ErpTenantUowDep,
        principal: CurrentPrincipal,
        keyword: str | None = None,
        name: str | None = None,
        mobile: str | None = None,
        phone: str | None = None,
        product_id: uuid.UUID | None = None,
        warehouse_id: uuid.UUID | None = None,
        supplier_id: uuid.UUID | None = None,
        customer_id: uuid.UUID | None = None,
        owner_id: uuid.UUID | None = None,
        status: str | None = None,
        remark: str | None = None,
        business_from: datetime | None = None,
        business_to: datetime | None = None,
    ) -> StreamingResponse:
        scope = definition.scope(uow, principal)
        if definition.model is PurchaseOrder:
            try:
                filters = document_list_filters(
                    model=PurchaseOrder,
                    item_model=PurchaseOrderItem,
                    item_document_column=PurchaseOrderItem.purchase_order_id,
                    counterparty_id_column=PurchaseOrder.supplier_id,
                    counterparty_name_column=PurchaseOrder.supplier_name,
                    scope=scope,
                    keyword=keyword,
                    product_id=product_id,
                    counterparty_id=supplier_id,
                    owner_id=owner_id,
                    status=status,
                    remark=remark,
                    business_from=business_from,
                    business_to=business_to,
                )
            except ValueError as exc:
                raise HTTPException(status_code=422, detail=str(exc)) from exc
        elif definition.model is SaleOrder:
            try:
                filters = document_list_filters(
                    model=SaleOrder,
                    item_model=SaleOrderItem,
                    item_document_column=SaleOrderItem.sale_order_id,
                    counterparty_id_column=SaleOrder.customer_id,
                    counterparty_name_column=SaleOrder.customer_name,
                    scope=scope,
                    keyword=keyword,
                    product_id=product_id,
                    counterparty_id=customer_id,
                    owner_id=owner_id,
                    status=status,
                    remark=remark,
                    business_from=business_from,
                    business_to=business_to,
                )
            except ValueError as exc:
                raise HTTPException(status_code=422, detail=str(exc)) from exc
        elif definition.model is PurchaseIn:
            try:
                filters = document_list_filters(
                    model=PurchaseIn,
                    item_model=PurchaseInItem,
                    item_document_column=PurchaseInItem.purchase_in_id,
                    counterparty_id_column=PurchaseIn.supplier_id,
                    counterparty_name_column=PurchaseIn.supplier_name,
                    scope=scope,
                    keyword=keyword,
                    product_id=product_id,
                    counterparty_id=supplier_id,
                    owner_id=owner_id,
                    status=status,
                    remark=remark,
                    business_from=business_from,
                    business_to=business_to,
                )
            except ValueError as exc:
                raise HTTPException(status_code=422, detail=str(exc)) from exc
        elif definition.model is PurchaseReturn:
            try:
                filters = document_list_filters(
                    model=PurchaseReturn,
                    item_model=PurchaseReturnItem,
                    item_document_column=PurchaseReturnItem.purchase_return_id,
                    counterparty_id_column=PurchaseReturn.supplier_id,
                    counterparty_name_column=PurchaseReturn.supplier_name,
                    scope=scope,
                    keyword=keyword,
                    product_id=product_id,
                    counterparty_id=supplier_id,
                    owner_id=owner_id,
                    status=status,
                    remark=remark,
                    business_from=business_from,
                    business_to=business_to,
                )
            except ValueError as exc:
                raise HTTPException(status_code=422, detail=str(exc)) from exc
        elif definition.model is SaleOut:
            try:
                filters = document_list_filters(
                    model=SaleOut,
                    item_model=SaleOutItem,
                    item_document_column=SaleOutItem.sale_out_id,
                    counterparty_id_column=SaleOut.customer_id,
                    counterparty_name_column=SaleOut.customer_name,
                    scope=scope,
                    keyword=keyword,
                    product_id=product_id,
                    counterparty_id=customer_id,
                    owner_id=owner_id,
                    status=status,
                    remark=remark,
                    business_from=business_from,
                    business_to=business_to,
                )
            except ValueError as exc:
                raise HTTPException(status_code=422, detail=str(exc)) from exc
        elif definition.model is SaleReturn:
            try:
                filters = document_list_filters(
                    model=SaleReturn,
                    item_model=SaleReturnItem,
                    item_document_column=SaleReturnItem.sale_return_id,
                    counterparty_id_column=SaleReturn.customer_id,
                    counterparty_name_column=SaleReturn.customer_name,
                    scope=scope,
                    keyword=keyword,
                    product_id=product_id,
                    counterparty_id=customer_id,
                    owner_id=owner_id,
                    status=status,
                    remark=remark,
                    business_from=business_from,
                    business_to=business_to,
                )
            except ValueError as exc:
                raise HTTPException(status_code=422, detail=str(exc)) from exc
        elif definition.model is FinancePayment:
            try:
                filters = financial_document_filters(
                    model=FinancePayment,
                    counterparty_id_column=FinancePayment.supplier_id,
                    counterparty_name_column=FinancePayment.supplier_name,
                    scope=scope,
                    keyword=keyword,
                    counterparty_id=supplier_id,
                    owner_id=owner_id,
                    status=status,
                    remark=remark,
                    business_from=business_from,
                    business_to=business_to,
                )
            except ValueError as exc:
                raise HTTPException(status_code=422, detail=str(exc)) from exc
        elif definition.model is FinanceReceipt:
            try:
                filters = financial_document_filters(
                    model=FinanceReceipt,
                    counterparty_id_column=FinanceReceipt.customer_id,
                    counterparty_name_column=FinanceReceipt.customer_name,
                    scope=scope,
                    keyword=keyword,
                    counterparty_id=customer_id,
                    owner_id=owner_id,
                    status=status,
                    remark=remark,
                    business_from=business_from,
                    business_to=business_to,
                )
            except ValueError as exc:
                raise HTTPException(status_code=422, detail=str(exc)) from exc
        elif stock_filter := _STOCK_DOCUMENT_FILTERS.get(definition.model):
            item_model, item_document_column, item_warehouse_columns = stock_filter
            try:
                filters = stock_document_filters(
                    model=definition.model,
                    item_document_column=item_document_column,
                    item_product_column=item_model.product_id,
                    item_warehouse_columns=item_warehouse_columns,
                    product_model=Product,
                    scope=scope,
                    keyword=keyword,
                    product_id=product_id,
                    warehouse_id=warehouse_id,
                    owner_id=owner_id,
                    status=status,
                    remark=remark,
                    business_from=business_from,
                    business_to=business_to,
                )
            except ValueError as exc:
                raise HTTPException(status_code=422, detail=str(exc)) from exc
        else:
            filters = [scope] if scope is not None else []
        if definition.model in {Customer, Supplier}:
            if name:
                filters.append(definition.model.name.ilike(f"%{name}%"))
            if mobile:
                filters.append(definition.model.mobile.ilike(f"%{mobile}%"))
            if phone:
                filters.append(definition.model.phone.ilike(f"%{phone}%"))
        if definition.model not in {
            PurchaseOrder,
            PurchaseIn,
            PurchaseReturn,
            SaleOrder,
            SaleOut,
            SaleReturn,
            StockIn,
            StockOut,
            StockMove,
            StockCheck,
            FinancePayment,
            FinanceReceipt,
        } and keyword and definition.search_fields:
            filters.append(
                or_(
                    *(field.ilike(f"%{keyword}%") for field in definition.search_fields)
                )
            )
        exported_count = int(
            uow.session.exec(
                select(func.count()).select_from(definition.model).where(*filters)
            ).one()
        )
        if exported_count > _MAX_EXPORT_ROWS:
            raise HTTPException(status_code=422, detail="Export is limited to 100000 rows")
        record_action(
            uow=uow,
            resource_type=definition.resource_type,
            resource_id=uuid.uuid4(),
            action=DocumentAction.EXPORTED,
            actor_id=principal.id,
            metadata={
                "exported_count": exported_count,
                "keyword": keyword or "",
                "name": name or "",
                "mobile": mobile or "",
                "phone": phone or "",
                "product_id": str(product_id) if product_id else None,
                "warehouse_id": str(warehouse_id) if warehouse_id else None,
                "supplier_id": str(supplier_id) if supplier_id else None,
                "customer_id": str(customer_id) if customer_id else None,
                "owner_id": str(owner_id) if owner_id else None,
                "status": status,
                "remark": remark,
                "business_from": business_from.isoformat() if business_from else None,
                "business_to": business_to.isoformat() if business_to else None,
            },
        )
        uow.session.commit()
        def csv_rows() -> Any:
            output = io.StringIO()
            writer = csv.writer(output)
            writer.writerow([title for title, _field in definition.columns])
            yield "\ufeff" + output.getvalue()
            rows = uow.session.exec(
                select(definition.model).where(*filters).order_by(definition.order_by)
            )
            for row in rows.yield_per(1_000):
                output = io.StringIO()
                csv.writer(output).writerow(
                    [_csv_value(getattr(row, field)) for _title, field in definition.columns]
                )
                yield output.getvalue()
        return StreamingResponse(
            csv_rows(),
            media_type="text/csv",
            headers={"Content-Disposition": f'attachment; filename="{definition.file_name}"'},
        )

    return endpoint


for _definition in _EXPORTS:
    router.add_api_route(
        f"/{_definition.path}/export",
        _export(_definition),
        methods=["GET"],
        dependencies=[Depends(require_module_access("erp", _definition.permission))],
        response_class=StreamingResponse,
        name=f"export_{_definition.path.replace('-', '_')}",
    )
