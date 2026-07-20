import uuid
from dataclasses import replace

import pytest
from sqlmodel import Session

from app import crud
from app.models import Tenant, UserCreate
from app.modules.contracts import ReferenceGuardSpec
from app.modules.items.infrastructure.models import Item
from app.modules.references import (
    ReferenceGuardUnavailableError,
    assert_no_references,
    find_references,
)
from app.modules.registry import MODULE_DEFINITIONS
from tests.utils.utils import random_email, random_lower_string


def test_reference_guard_reports_item_user_references(db: Session) -> None:
    tenant = db.get(Tenant, uuid.UUID("00000000-0000-4000-8000-000000000001"))
    assert tenant is not None
    user = crud.create_user(
        session=db,
        user_create=UserCreate(
            email=random_email(), password=f"pA{random_lower_string()}123!"
        ),
    )
    item = Item(title="reference guard", owner_id=user.id, tenant_id=tenant.id)
    db.add(item)
    db.commit()
    try:
        assert find_references(
            session=db,
            reference_type="user",
            reference_id=user.id,
            tenant_id=tenant.id,
        ) == {"items": 1}
        with pytest.raises(ValueError, match="items=1"):
            assert_no_references(
                session=db,
                reference_type="user",
                reference_id=user.id,
                tenant_id=tenant.id,
            )
    finally:
        db.delete(item)
        db.delete(user)
        db.commit()


def test_missing_installed_module_reference_guard_fails_closed(db: Session) -> None:
    original = MODULE_DEFINITIONS["items"]
    MODULE_DEFINITIONS["items"] = replace(
        original,
        reference_guards=(ReferenceGuardSpec("user", None),),
    )
    try:
        with pytest.raises(ReferenceGuardUnavailableError, match="items"):
            find_references(
                session=db,
                reference_type="user",
                reference_id=uuid.uuid4(),
            )
    finally:
        MODULE_DEFINITIONS["items"] = original
