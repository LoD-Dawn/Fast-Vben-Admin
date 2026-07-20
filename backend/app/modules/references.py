from sqlmodel import Session

from app.core.config import settings


class ReferenceGuardUnavailableError(ValueError):
    """Raised when an installed module cannot attest to a destructive action."""


def find_references(
    *, session: Session, reference_type: str, reference_id, tenant_id=None
) -> dict[str, int]:
    """Return reference counts, failing closed for required guards."""
    from app.modules.manifest import build_manifest, load_manifest_file
    from app.modules.registry import get_module_definitions

    manifest = (
        load_manifest_file(settings.BUILD_MANIFEST_PATH)
        if settings.BUILD_MANIFEST_PATH is not None
        else build_manifest(edition=settings.APP_EDITION)
    )
    definitions = get_module_definitions()
    references: dict[str, int] = {}
    for module in manifest.modules:
        definition = definitions[module.code]
        guard_spec = next(
            (
                guard
                for guard in definition.reference_guards
                if guard.reference_type == reference_type
            ),
            None,
        )
        if guard_spec is None:
            continue
        if guard_spec.handler is None:
            raise ReferenceGuardUnavailableError(
                f"Reference guard unavailable for installed module: {module.code}"
            )
        try:
            count = guard_spec.handler(session, reference_type, reference_id, tenant_id)
        except Exception as exc:
            raise ReferenceGuardUnavailableError(
                f"Reference guard failed for installed module: {module.code}"
            ) from exc
        if count > 0:
            references[module.code] = count
    return references


def assert_no_references(
    *, session: Session, reference_type: str, reference_id, tenant_id=None
) -> None:
    references = find_references(
        session=session,
        reference_type=reference_type,
        reference_id=reference_id,
        tenant_id=tenant_id,
    )
    if references:
        details = ", ".join(f"{module}={count}" for module, count in references.items())
        raise ValueError(f"Master data still has module references: {details}")
