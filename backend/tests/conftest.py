from collections.abc import Generator

import pytest
from fastapi.testclient import TestClient
from sqlmodel import Session, delete, select

from app.core.config import settings
from app.core.database import engine
from app.main import app
from app.models import (
    DictionaryItem,
    DictionaryType,
    EventDelivery,
    InboxReceipt,
    OutboxEvent,
    TenantPlan,
    TenantPlanModule,
    User,
)
from app.modules.items.infrastructure.models import Item
from app.platform.bootstrap import init_db
from tests.utils.user import authentication_token_from_email
from tests.utils.utils import get_superuser_token_headers


@pytest.fixture(scope="session", autouse=True)
def disable_slider_captcha() -> Generator[None]:
    original = settings.LOGIN_SLIDER_CAPTCHA_ENABLED
    settings.LOGIN_SLIDER_CAPTCHA_ENABLED = False
    yield
    settings.LOGIN_SLIDER_CAPTCHA_ENABLED = original


def cleanup_test_dictionaries(session: Session) -> None:
    test_types = session.exec(
        select(DictionaryType).where(DictionaryType.name == "测试字典")
    ).all()
    for type_ in test_types:
        items = session.exec(
            select(DictionaryItem).where(DictionaryItem.type_id == type_.id)
        ).all()
        for item in items:
            session.delete(item)
        session.delete(type_)
    session.commit()


def ensure_test_items_entitlement(session: Session) -> None:
    """Tests explicitly model an operator-granted Items entitlement."""
    plan = session.exec(select(TenantPlan).where(TenantPlan.code == "standard")).one()
    mapping = session.get(TenantPlanModule, (plan.id, "items"))
    if mapping is None:
        session.add(
            TenantPlanModule(
                plan_id=plan.id,
                module_code="items",
                is_enabled=True,
            )
        )
    else:
        mapping.is_enabled = True
        session.add(mapping)
    session.commit()


@pytest.fixture(scope="session")
def db() -> Generator[Session]:
    with Session(engine) as session:
        init_db(session)
        ensure_test_items_entitlement(session)
        cleanup_test_dictionaries(session)
        session.execute(delete(EventDelivery))
        session.execute(delete(InboxReceipt))
        session.execute(delete(OutboxEvent))
        session.commit()
        yield session
        cleanup_test_dictionaries(session)
        session.execute(delete(EventDelivery))
        session.execute(delete(InboxReceipt))
        session.execute(delete(OutboxEvent))
        statement = delete(Item)
        session.execute(statement)
        statement = delete(User).where(User.email != settings.FIRST_SUPERUSER)
        session.execute(statement)
        session.commit()


@pytest.fixture(scope="module")
def client(db: Session) -> Generator[TestClient]:
    _ = db  # Ensure database initialization precedes application lifespan startup.
    with TestClient(app) as c:
        yield c


@pytest.fixture(scope="module")
def superuser_token_headers(client: TestClient) -> dict[str, str]:
    return get_superuser_token_headers(client)


@pytest.fixture(scope="module")
def normal_user_token_headers(client: TestClient, db: Session) -> dict[str, str]:
    return authentication_token_from_email(
        client=client, email=settings.EMAIL_TEST_USER, db=db
    )
