from app.main import resolve_error_code


def test_erp_error_codes_preserve_business_failure_categories() -> None:
    assert resolve_error_code(
        status_code=404,
        detail="Purchase order not found",
        path="/api/v1/erp/purchase-orders/id",
    ) == "ERP_RESOURCE_NOT_FOUND"
    assert resolve_error_code(
        status_code=409,
        detail="Purchase order version conflict",
        path="/api/v1/erp/purchase-orders/id/approve",
    ) == "ERP_DOCUMENT_VERSION_CONFLICT"
    assert resolve_error_code(
        status_code=409,
        detail="Stock is insufficient",
        path="/api/v1/erp/stock-outs/id/approve",
    ) == "ERP_STOCK_INSUFFICIENT"
    assert resolve_error_code(
        status_code=409,
        detail="Return quantity exceeds available shipped quantity",
        path="/api/v1/erp/sale-returns",
    ) == "ERP_QUANTITY_EXCEEDED"
    assert resolve_error_code(
        status_code=409,
        detail="Settlement amount exceeds source balance",
        path="/api/v1/erp/finance-payments",
    ) == "ERP_SETTLEMENT_LIMIT_EXCEEDED"
    assert resolve_error_code(
        status_code=409,
        detail="Idempotency-Key has already been used for a different request",
        path="/api/v1/erp/products",
    ) == "ERP_IDEMPOTENCY_CONFLICT"


def test_non_erp_error_codes_keep_existing_status_mapping() -> None:
    assert resolve_error_code(
        status_code=404,
        detail="Unknown resource not found",
        path="/api/v1/users/id",
    ) == "NOT_FOUND"
