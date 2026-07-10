from fastapi.testclient import TestClient
from sqlmodel import Session, delete, select

from app import crud
from app.core.config import settings
from app.models import Menu, Post, Role, RoleMenu, UserCreate, UserPost, UserRole
from tests.utils.user import user_authentication_headers
from tests.utils.utils import random_lower_string


def test_superuser_can_create_list_update_and_delete_post(
    client: TestClient, superuser_token_headers: dict[str, str]
) -> None:
    post_code = f"post_{random_lower_string()}"
    create_response = client.post(
        f"{settings.API_V1_STR}/posts",
        headers=superuser_token_headers,
        json={
            "code": post_code,
            "name": f"测试岗位_{post_code}",
            "sort": 10,
            "is_active": True,
            "remark": "Post test",
        },
    )

    assert create_response.status_code == 200
    post = create_response.json()
    assert post["code"] == post_code

    try:
        list_response = client.get(
            f"{settings.API_V1_STR}/posts",
            headers=superuser_token_headers,
            params={"keyword": post_code},
        )
        assert list_response.status_code == 200
        assert list_response.json()["total"] >= 1

        update_response = client.patch(
            f"{settings.API_V1_STR}/posts/{post['id']}",
            headers=superuser_token_headers,
            json={"name": "测试岗位_已更新", "is_active": False},
        )
        assert update_response.status_code == 200
        updated_post = update_response.json()
        assert updated_post["name"] == "测试岗位_已更新"
        assert updated_post["is_active"] is False
    finally:
        delete_response = client.delete(
            f"{settings.API_V1_STR}/posts/{post['id']}",
            headers=superuser_token_headers,
        )
        assert delete_response.status_code == 204


def test_create_post_rejects_duplicate_code(
    client: TestClient, superuser_token_headers: dict[str, str]
) -> None:
    post_code = f"post_{random_lower_string()}"
    payload = {"code": post_code, "name": post_code, "sort": 10}
    first_response = client.post(
        f"{settings.API_V1_STR}/posts",
        headers=superuser_token_headers,
        json=payload,
    )
    assert first_response.status_code == 200
    post = first_response.json()

    try:
        duplicate_response = client.post(
            f"{settings.API_V1_STR}/posts",
            headers=superuser_token_headers,
            json=payload,
        )
        assert duplicate_response.status_code == 409
    finally:
        client.delete(
            f"{settings.API_V1_STR}/posts/{post['id']}",
            headers=superuser_token_headers,
        )


def test_delete_post_with_users_is_blocked(
    client: TestClient,
    db: Session,
    superuser_token_headers: dict[str, str],
) -> None:
    post = Post(code=f"post_{random_lower_string()}", name="Bound post")
    user = crud.create_user(
        session=db,
        user_create=UserCreate(
            email=f"{random_lower_string()}@example.com",
            password=random_lower_string(),
        ),
    )
    db.add(post)
    db.flush()
    db.add(UserPost(user_id=user.id, post_id=post.id))
    db.commit()

    try:
        response = client.delete(
            f"{settings.API_V1_STR}/posts/{post.id}",
            headers=superuser_token_headers,
        )
        assert response.status_code == 400
        assert response.json()["message"] == "Post has users"
    finally:
        db.exec(delete(UserPost).where(UserPost.user_id == user.id))
        db.delete(user)
        db.delete(post)
        db.commit()


def test_normal_user_cannot_read_posts(
    client: TestClient, normal_user_token_headers: dict[str, str]
) -> None:
    response = client.get(
        f"{settings.API_V1_STR}/posts",
        headers=normal_user_token_headers,
    )

    assert response.status_code == 403


def test_non_superuser_with_post_permission_can_read_posts(
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
        code=f"post_manager_{random_lower_string()}",
        name="Post manager",
        is_active=True,
    )
    db.add(role)
    db.flush()
    post_list_menu = db.exec(
        select(Menu).where(Menu.permission_code == "system:post:list")
    ).first()
    assert post_list_menu
    db.add(UserRole(user_id=user.id, role_id=role.id))
    db.add(RoleMenu(role_id=role.id, menu_id=post_list_menu.id))
    db.commit()

    headers = user_authentication_headers(
        client=client,
        email=user.email,
        password=password,
    )
    try:
        response = client.get(f"{settings.API_V1_STR}/posts", headers=headers)
        assert response.status_code == 200
        assert "items" in response.json()
    finally:
        db.delete(user)
        db.delete(role)
        db.commit()
