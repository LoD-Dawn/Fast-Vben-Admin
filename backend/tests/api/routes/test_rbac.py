import re
from pathlib import Path

from fastapi.testclient import TestClient
from sqlmodel import Session, select

from app import crud
from app.core.config import settings
from app.models import Menu, Role, RoleMenu, UserCreate, UserRole
from tests.utils.user import user_authentication_headers
from tests.utils.utils import random_lower_string


def test_required_permissions_are_seeded(db: Session) -> None:
    backend_root = Path(__file__).resolve().parents[3]
    permission_pattern = re.compile(r'require_permission\("([^"]+)"\)')
    required_permissions: set[str] = set()

    for route_file in (backend_root / "app" / "api" / "routes").glob("*.py"):
        required_permissions.update(permission_pattern.findall(route_file.read_text()))

    seeded_permissions = {
        permission
        for permission in db.exec(select(Menu.permission_code)).all()
        if permission
    }

    assert required_permissions <= seeded_permissions


def test_seeded_menu_components_exist(db: Session) -> None:
    project_root = Path(__file__).resolve().parents[4]
    frontend_src = project_root / "frontend" / "apps" / "web-antd" / "src"
    menus = db.exec(select(Menu).where(Menu.component != None)).all()  # noqa: E711

    missing_components = []
    for menu in menus:
        assert menu.component
        if not menu.component.startswith("#/"):
            continue
        component_path = frontend_src / menu.component.removeprefix("#/")
        if not component_path.exists():
            missing_components.append(menu.component)

    assert missing_components == []


def test_superuser_can_read_seeded_menus(
    client: TestClient, superuser_token_headers: dict[str, str]
) -> None:
    response = client.get(
        f"{settings.API_V1_STR}/menus/me",
        headers=superuser_token_headers,
    )

    assert response.status_code == 200
    menus = response.json()
    permission_codes = {menu["permission_code"] for menu in menus}
    assert "system:user:list" in permission_codes
    assert "system:role:list" in permission_codes
    assert "system:menu:list" in permission_codes


def test_list_pagination_is_normalized(
    client: TestClient, superuser_token_headers: dict[str, str]
) -> None:
    invalid_response = client.get(
        f"{settings.API_V1_STR}/roles",
        headers=superuser_token_headers,
        params={"page": 0},
    )
    assert invalid_response.status_code == 422

    capped_response = client.get(
        f"{settings.API_V1_STR}/roles",
        headers=superuser_token_headers,
        params={"page_size": 1000},
    )
    assert capped_response.status_code == 200
    assert capped_response.json()["page_size"] == 100


def test_superuser_can_read_permissions(
    client: TestClient, superuser_token_headers: dict[str, str]
) -> None:
    response = client.get(
        f"{settings.API_V1_STR}/permissions/me",
        headers=superuser_token_headers,
    )

    assert response.status_code == 200
    permissions = set(response.json())
    assert "system:user:list" in permissions
    assert "system:role:update" in permissions
    assert "system:department:create" in permissions


def test_normal_user_cannot_read_roles(
    client: TestClient, normal_user_token_headers: dict[str, str]
) -> None:
    response = client.get(
        f"{settings.API_V1_STR}/roles",
        headers=normal_user_token_headers,
    )

    assert response.status_code == 403


def test_superuser_can_create_role_and_assign_menus(
    client: TestClient, superuser_token_headers: dict[str, str]
) -> None:
    role_code = f"role_{random_lower_string()}"
    create_role_response = client.post(
        f"{settings.API_V1_STR}/roles",
        headers=superuser_token_headers,
        json={
            "code": role_code,
            "name": f"测试角色_{role_code}",
            "description": "RBAC test role",
            "sort": 90,
            "is_active": True,
            "is_system": False,
        },
    )

    assert create_role_response.status_code == 200
    role = create_role_response.json()
    assert role["code"] == role_code

    try:
        menus_response = client.get(
            f"{settings.API_V1_STR}/menus",
            headers=superuser_token_headers,
        )
        assert menus_response.status_code == 200
        menu_ids = [
            menu["id"]
            for menu in menus_response.json()["items"]
            if menu["permission_code"] in {"system:user:list", "system:role:list"}
        ]
        assert len(menu_ids) == 2

        assign_response = client.put(
            f"{settings.API_V1_STR}/roles/{role['id']}/menus",
            headers=superuser_token_headers,
            json={"menu_ids": menu_ids},
        )
        assert assign_response.status_code == 200
        assert set(assign_response.json()) == set(menu_ids)

        read_response = client.get(
            f"{settings.API_V1_STR}/roles/{role['id']}/menus",
            headers=superuser_token_headers,
        )
        assert read_response.status_code == 200
        assert set(read_response.json()) == set(menu_ids)
    finally:
        delete_response = client.delete(
            f"{settings.API_V1_STR}/roles/{role['id']}",
            headers=superuser_token_headers,
        )
        assert delete_response.status_code == 204


def test_superuser_can_create_department(
    client: TestClient, superuser_token_headers: dict[str, str]
) -> None:
    department_code = f"dept_{random_lower_string()}"
    response = client.post(
        f"{settings.API_V1_STR}/departments",
        headers=superuser_token_headers,
        json={
            "code": department_code,
            "name": f"测试部门_{department_code}",
            "sort": 10,
            "is_active": True,
        },
    )

    assert response.status_code == 200
    department = response.json()
    assert department["code"] == department_code
    assert department["name"] == f"测试部门_{department_code}"

    delete_response = client.delete(
        f"{settings.API_V1_STR}/departments/{department['id']}",
        headers=superuser_token_headers,
    )
    assert delete_response.status_code == 204


def test_disabled_role_does_not_grant_permissions(
    client: TestClient, db: Session
) -> None:
    password = random_lower_string()
    user = crud.create_user(
        session=db,
        user_create=UserCreate(
            email=f"{random_lower_string()}@example.com",
            password=password,
        ),
    )
    role = Role(
        code=f"disabled_{random_lower_string()}",
        name="Disabled role",
        is_active=False,
    )
    db.add(role)
    db.flush()
    menu = db.exec(
        select(Menu).where(Menu.permission_code == "system:role:list")
    ).first()
    assert menu
    db.add(UserRole(user_id=user.id, role_id=role.id))
    db.add(RoleMenu(role_id=role.id, menu_id=menu.id))
    db.commit()

    headers = user_authentication_headers(
        client=client,
        email=user.email,
        password=password,
    )
    try:
        response = client.get(f"{settings.API_V1_STR}/roles", headers=headers)
        assert response.status_code == 403

        permissions_response = client.get(
            f"{settings.API_V1_STR}/permissions/me",
            headers=headers,
        )
        assert permissions_response.status_code == 200
        assert "system:role:list" not in permissions_response.json()
    finally:
        db.delete(user)
        db.delete(role)
        db.commit()


def test_non_superuser_with_user_permission_can_read_users(
    client: TestClient, db: Session
) -> None:
    password = random_lower_string()
    user = crud.create_user(
        session=db,
        user_create=UserCreate(
            email=f"{random_lower_string()}@example.com",
            password=password,
        ),
    )
    role = Role(
        code=f"user_manager_{random_lower_string()}",
        name="User manager",
        is_active=True,
    )
    db.add(role)
    db.flush()
    menu = db.exec(
        select(Menu).where(Menu.permission_code == "system:user:list")
    ).first()
    assert menu
    db.add(UserRole(user_id=user.id, role_id=role.id))
    db.add(RoleMenu(role_id=role.id, menu_id=menu.id))
    db.commit()

    headers = user_authentication_headers(
        client=client,
        email=user.email,
        password=password,
    )
    try:
        response = client.get(f"{settings.API_V1_STR}/users", headers=headers)
        assert response.status_code == 200
        assert "items" in response.json()
    finally:
        db.delete(user)
        db.delete(role)
        db.commit()


def test_menu_parent_cannot_be_descendant(
    client: TestClient, superuser_token_headers: dict[str, str]
) -> None:
    root_response = client.post(
        f"{settings.API_V1_STR}/menus",
        headers=superuser_token_headers,
        json={
            "title": f"root_{random_lower_string()}",
            "type": "directory",
            "route_path": f"/root-{random_lower_string()}",
            "route_name": f"Root{random_lower_string()}",
            "sort": 900,
        },
    )
    assert root_response.status_code == 200
    root = root_response.json()
    child_response = client.post(
        f"{settings.API_V1_STR}/menus",
        headers=superuser_token_headers,
        json={
            "title": f"child_{random_lower_string()}",
            "type": "menu",
            "parent_id": root["id"],
            "route_path": f"/child-{random_lower_string()}",
            "route_name": f"Child{random_lower_string()}",
            "component": "#/views/items/index.vue",
            "sort": 901,
        },
    )
    assert child_response.status_code == 200
    child = child_response.json()
    try:
        response = client.patch(
            f"{settings.API_V1_STR}/menus/{root['id']}",
            headers=superuser_token_headers,
            json={"parent_id": child["id"]},
        )
        assert response.status_code == 400
    finally:
        client.delete(
            f"{settings.API_V1_STR}/menus/{child['id']}",
            headers=superuser_token_headers,
        )
        client.delete(
            f"{settings.API_V1_STR}/menus/{root['id']}",
            headers=superuser_token_headers,
        )


def test_department_parent_cannot_be_descendant(
    client: TestClient, superuser_token_headers: dict[str, str]
) -> None:
    root_code = f"dept_{random_lower_string()}"
    child_code = f"dept_{random_lower_string()}"
    root_response = client.post(
        f"{settings.API_V1_STR}/departments",
        headers=superuser_token_headers,
        json={"code": root_code, "name": root_code, "sort": 900},
    )
    assert root_response.status_code == 200
    root = root_response.json()
    child_response = client.post(
        f"{settings.API_V1_STR}/departments",
        headers=superuser_token_headers,
        json={
            "code": child_code,
            "name": child_code,
            "parent_id": root["id"],
            "sort": 901,
        },
    )
    assert child_response.status_code == 200
    child = child_response.json()
    try:
        response = client.patch(
            f"{settings.API_V1_STR}/departments/{root['id']}",
            headers=superuser_token_headers,
            json={"parent_id": child["id"]},
        )
        assert response.status_code == 400
    finally:
        client.delete(
            f"{settings.API_V1_STR}/departments/{child['id']}",
            headers=superuser_token_headers,
        )
        client.delete(
            f"{settings.API_V1_STR}/departments/{root['id']}",
            headers=superuser_token_headers,
        )
