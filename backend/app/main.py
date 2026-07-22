from contextlib import asynccontextmanager

import sentry_sdk
from fastapi import FastAPI, HTTPException, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from fastapi.routing import APIRoute
from sqlmodel import Session
from starlette.middleware.cors import CORSMiddleware

from app.api.main import api_router
from app.core.config import settings
from app.core.database import engine
from app.core.metrics import build_metrics_response, metrics_middleware
from app.modules.access import get_runtime_manifest, validate_module_runtime
from app.modules.events import configure_event_deliveries
from app.modules.registry import get_module_definitions
from app.platform.infra.audit import audit_operation_middleware


def custom_generate_unique_id(route: APIRoute) -> str:
    return f"{route.tags[0]}-{route.name}"


ERROR_CODE_BY_STATUS = {
    400: "BAD_REQUEST",
    401: "AUTH_TOKEN_INVALID",
    403: "USER_FORBIDDEN",
    429: "RATE_LIMITED",
    404: "NOT_FOUND",
    409: "CONFLICT",
    422: "VALIDATION_ERROR",
    500: "INTERNAL_SERVER_ERROR",
}

ERROR_CODE_BY_MESSAGE = {
    "Incorrect email or password": "AUTH_INVALID_CREDENTIALS",
    "Inactive user": "USER_INACTIVE",
    "Could not validate credentials": "AUTH_TOKEN_INVALID",
    "Too many failed login attempts. Please try again later.": "AUTH_RATE_LIMITED",
    "Captcha verification required.": "AUTH_CAPTCHA_REQUIRED",
    "Captcha is invalid or expired.": "AUTH_CAPTCHA_INVALID",
    "Slider captcha verification is invalid or expired.": "AUTH_SLIDER_CAPTCHA_INVALID",
    "SMS verification code is invalid or expired.": "AUTH_SMS_CODE_INVALID",
    "SMS verification is unavailable.": "AUTH_SMS_UNAVAILABLE",
    "Incorrect mobile or verification code": "AUTH_SMS_INVALID",
    "Invalid mobile number": "AUTH_MOBILE_INVALID",
    "SMS verification code was sent recently.": "AUTH_SMS_RESEND_LIMITED",
    "Too many SMS verification requests.": "AUTH_SMS_RATE_LIMITED",
    "Public registration is disabled": "AUTH_REGISTER_DISABLED",
    "Invalid tenant code": "TENANT_CODE_INVALID",
    "Email already exists": "USER_EMAIL_CONFLICT",
    "Mobile already exists": "USER_MOBILE_CONFLICT",
    "User with this mobile already exists": "USER_MOBILE_CONFLICT",
    "Tenant registration is not configured": "TENANT_REGISTER_NOT_CONFIGURED",
    "Tenant registration conflicts with existing data": "TENANT_REGISTER_CONFLICT",
    "MFA verification required.": "AUTH_MFA_REQUIRED",
    "MFA is disabled": "AUTH_MFA_DISABLED",
    "MFA is not configured.": "AUTH_MFA_NOT_CONFIGURED",
    "MFA has already been enabled.": "AUTH_MFA_ALREADY_ENABLED",
    "MFA verification code is invalid.": "AUTH_MFA_INVALID",
    "Current password is required": "AUTH_REAUTH_REQUIRED",
    "MFA setup is invalid. Please restart MFA setup.": "AUTH_MFA_SETUP_INVALID",
    "Enterprise OIDC is disabled": "AUTH_ENTERPRISE_OIDC_DISABLED",
    "Enterprise OIDC is not configured": "AUTH_ENTERPRISE_OIDC_NOT_CONFIGURED",
    "Enterprise OIDC state is invalid or expired": "AUTH_ENTERPRISE_OIDC_STATE_INVALID",
    "Enterprise OIDC login ticket is invalid or expired": "AUTH_ENTERPRISE_OIDC_TICKET_INVALID",
    "Enterprise OIDC identity is not linked to an active local user": "AUTH_ENTERPRISE_OIDC_USER_INVALID",
    "Enterprise OIDC identity token is invalid": "AUTH_ENTERPRISE_OIDC_TOKEN_INVALID",
    "QR code login is unavailable.": "AUTH_QR_UNAVAILABLE",
    "QR code login challenge is invalid or expired.": "AUTH_QR_EXPIRED",
    "QR code login credential is invalid.": "AUTH_QR_INVALID",
    "QR code login has not been confirmed.": "AUTH_QR_PENDING",
    "QR code login has already been confirmed.": "AUTH_QR_ALREADY_CONFIRMED",
    "QR code login tenant does not match the current tenant.": "AUTH_QR_TENANT_MISMATCH",
    "User not found": "USER_NOT_FOUND",
    "Built-in administrator cannot be modified": "USER_PROTECTED",
    "User has no active tenant": "TENANT_MEMBERSHIP_REQUIRED",
    "Tenant context is invalid": "TENANT_CONTEXT_INVALID",
    "Tenant not found": "TENANT_NOT_FOUND",
    "Tenant code already exists": "TENANT_CODE_CONFLICT",
    "Default tenant cannot be disabled": "TENANT_DEFAULT_PROTECTED",
    "Default tenant code cannot be changed": "TENANT_DEFAULT_PROTECTED",
    "Default tenant cannot be modified": "TENANT_DEFAULT_PROTECTED",
    "Default tenant plan cannot be modified": "TENANT_DEFAULT_PLAN_PROTECTED",
    "Tenant member quota exceeded": "TENANT_MEMBER_QUOTA_EXCEEDED",
    "Tenant file quota exceeded": "TENANT_FILE_QUOTA_EXCEEDED",
    "Tenant storage quota exceeded": "TENANT_STORAGE_QUOTA_EXCEEDED",
    "Not enough permissions": "ITEM_FORBIDDEN",
    "The user doesn't have enough privileges": "USER_FORBIDDEN",
    "Module is not installed": "MODULE_NOT_INSTALLED",
    "Module is unavailable": "MODULE_UNAVAILABLE",
    "Tenant module entitlement is required": "TENANT_MODULE_ENTITLEMENT_REQUIRED",
    "Tenant module is disabled": "TENANT_MODULE_DISABLED",
    "Platform module cannot be disabled": "PLATFORM_MODULE_REQUIRED",
    "Platform module entitlement cannot be managed": "PLATFORM_MODULE_REQUIRED",
    "ERP resource code already exists": "ERP_RESOURCE_CODE_CONFLICT",
    "Product unit is in use": "ERP_RESOURCE_IN_USE",
    "Product category is in use": "ERP_RESOURCE_IN_USE",
    "Product category cannot be its own parent": "ERP_CATEGORY_CYCLE",
    "Product category hierarchy is cyclic": "ERP_CATEGORY_CYCLE",
    "Inventory document requires at least one line": "ERP_DOCUMENT_LINES_REQUIRED",
    "Inventory effect cannot be zero": "ERP_DOCUMENT_LINES_REQUIRED",
    "Stock is insufficient": "ERP_STOCK_INSUFFICIENT",
    "Product is unavailable": "ERP_MASTER_DATA_UNAVAILABLE",
    "Warehouse is unavailable": "ERP_MASTER_DATA_UNAVAILABLE",
    "Stock document version conflict": "ERP_DOCUMENT_VERSION_CONFLICT",
    "Stock document has no reversible posting": "ERP_DOCUMENT_STATE_CONFLICT",
    "Stock snapshot is stale": "ERP_STOCK_SNAPSHOT_STALE",
}


def resolve_error_code(*, status_code: int, detail: str, path: str) -> str:
    """Keep ERP business failures distinguishable without changing legacy APIs."""

    mapped = ERROR_CODE_BY_MESSAGE.get(detail)
    if mapped is not None:
        return mapped
    if "/erp" not in path:
        return ERROR_CODE_BY_STATUS.get(status_code, "REQUEST_ERROR")
    if "Idempotency" in detail or "Idempotency-Key" in detail:
        return "ERP_IDEMPOTENCY_CONFLICT"
    if detail.endswith(" not found"):
        return "ERP_RESOURCE_NOT_FOUND"
    if " is inactive" in detail:
        return "ERP_MASTER_DATA_INACTIVE"
    if " is unavailable" in detail:
        return "ERP_MASTER_DATA_UNAVAILABLE"
    if "version conflict" in detail:
        return "ERP_DOCUMENT_VERSION_CONFLICT"
    if "exceeds" in detail:
        return (
            "ERP_SETTLEMENT_LIMIT_EXCEEDED"
            if "Settlement" in detail or "settlement" in detail
            else "ERP_QUANTITY_EXCEEDED"
        )
    if any(
        phrase in detail
        for phrase in (
            "must be approved",
            "must be draft",
            "downstream",
            "no reversible posting",
            "cannot be changed after document approval",
            "cannot repeat",
        )
    ):
        return "ERP_DOCUMENT_STATE_CONFLICT"
    return ERROR_CODE_BY_STATUS.get(status_code, "REQUEST_ERROR")


def error_response(
    *, status_code: int, code: str, message: str, details: dict | list | None = None
) -> JSONResponse:
    return JSONResponse(
        status_code=status_code,
        content={
            "code": code,
            "message": message,
            "details": details or {},
        },
    )


if settings.SENTRY_DSN and settings.ENVIRONMENT != "local":
    sentry_sdk.init(dsn=str(settings.SENTRY_DSN), enable_tracing=True)


@asynccontextmanager
async def lifespan(_app: FastAPI):
    manifest = get_runtime_manifest()
    definitions = get_module_definitions()
    configure_event_deliveries(definitions[module.code] for module in manifest.modules)
    with Session(engine) as session:
        validate_module_runtime(session)
    yield


app = FastAPI(
    title=settings.PROJECT_NAME,
    openapi_url=f"{settings.API_V1_STR}/openapi.json",
    generate_unique_id_function=custom_generate_unique_id,
    lifespan=lifespan,
)

app.middleware("http")(audit_operation_middleware)
app.middleware("http")(metrics_middleware)


@app.exception_handler(HTTPException)
async def http_exception_handler(_request: Request, exc: HTTPException) -> JSONResponse:
    detail = exc.detail if isinstance(exc.detail, str) else "Request failed"
    return error_response(
        status_code=exc.status_code,
        code=resolve_error_code(
            status_code=exc.status_code, detail=detail, path=_request.url.path
        ),
        message=detail,
        details={} if isinstance(exc.detail, str) else {"detail": exc.detail},
    )


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(
    _request: Request, exc: RequestValidationError
) -> JSONResponse:
    return error_response(
        status_code=422,
        code="VALIDATION_ERROR",
        message="Request validation failed",
        details={"errors": exc.errors()},
    )


# Set all CORS enabled origins
if settings.all_cors_origins:
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.all_cors_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

app.include_router(api_router, prefix=settings.API_V1_STR)


@app.get("/metrics", include_in_schema=False, tags=["metrics"])
def read_metrics(request: Request):
    if not settings.METRICS_ENABLED:
        raise HTTPException(status_code=404, detail="Metrics are disabled")
    if settings.METRICS_AUTH_TOKEN:
        expected_authorization = f"Bearer {settings.METRICS_AUTH_TOKEN}"
        if request.headers.get("authorization") != expected_authorization:
            raise HTTPException(status_code=401, detail="Metrics authentication failed")
    return build_metrics_response()
