from fastapi.testclient import TestClient

from app.core.cache import CacheNamespace, redis_cache
from app.core.config import settings
from tests.utils.utils import random_lower_string


def _delete_dictionary_type(
    client: TestClient,
    headers: dict[str, str],
    type_id: str,
    item_id: str | None = None,
) -> None:
    if item_id:
        client.delete(
            f"{settings.API_V1_STR}/dictionary-items/{item_id}",
            headers=headers,
        )
    client.delete(
        f"{settings.API_V1_STR}/dictionary-types/{type_id}",
        headers=headers,
    )


def test_superuser_can_read_seeded_dictionary_items(
    client: TestClient, superuser_token_headers: dict[str, str]
) -> None:
    response = client.get(
        f"{settings.API_V1_STR}/dictionaries/user_status/items",
        headers=superuser_token_headers,
    )

    assert response.status_code == 200
    items = response.json()
    values = {item["value"] for item in items}
    assert {"active", "inactive"}.issubset(values)


def test_normal_user_cannot_manage_dictionary_types(
    client: TestClient, normal_user_token_headers: dict[str, str]
) -> None:
    response = client.get(
        f"{settings.API_V1_STR}/dictionary-types",
        headers=normal_user_token_headers,
    )

    assert response.status_code == 403


def test_superuser_can_create_dictionary_type_and_item(
    client: TestClient, superuser_token_headers: dict[str, str]
) -> None:
    dictionary_code = f"dict_{random_lower_string()}"
    type_id: str | None = None
    item_id: str | None = None
    try:
        create_type_response = client.post(
            f"{settings.API_V1_STR}/dictionary-types",
            headers=superuser_token_headers,
            json={
                "code": dictionary_code,
                "name": "测试字典",
                "description": "Dictionary test",
                "is_active": True,
            },
        )

        assert create_type_response.status_code == 200
        dictionary_type = create_type_response.json()
        type_id = dictionary_type["id"]
        assert dictionary_type["code"] == dictionary_code

        create_item_response = client.post(
            f"{settings.API_V1_STR}/dictionary-items",
            headers=superuser_token_headers,
            json={
                "type_id": type_id,
                "label": "测试项",
                "value": "test",
                "color": "blue",
                "sort": 0,
                "is_active": True,
            },
        )
        assert create_item_response.status_code == 200
        item = create_item_response.json()
        item_id = item["id"]
        assert item["value"] == "test"

        public_items_response = client.get(
            f"{settings.API_V1_STR}/dictionaries/{dictionary_code}/items",
            headers=superuser_token_headers,
        )
        assert public_items_response.status_code == 200
        assert public_items_response.json()[0]["label"] == "测试项"
    finally:
        if type_id:
            _delete_dictionary_type(
                client,
                superuser_token_headers,
                type_id,
                item_id,
            )


def test_dictionary_item_value_must_be_unique_in_type(
    client: TestClient, superuser_token_headers: dict[str, str]
) -> None:
    dictionary_code = f"dict_{random_lower_string()}"
    type_id: str | None = None
    item_id: str | None = None
    try:
        create_type_response = client.post(
            f"{settings.API_V1_STR}/dictionary-types",
            headers=superuser_token_headers,
            json={
                "code": dictionary_code,
                "name": "测试字典",
                "is_active": True,
            },
        )
        assert create_type_response.status_code == 200
        type_id = create_type_response.json()["id"]

        payload = {
            "type_id": type_id,
            "label": "测试项",
            "value": "same",
            "sort": 0,
            "is_active": True,
        }
        create_item_response = client.post(
            f"{settings.API_V1_STR}/dictionary-items",
            headers=superuser_token_headers,
            json=payload,
        )
        assert create_item_response.status_code == 200
        item_id = create_item_response.json()["id"]

        duplicate_response = client.post(
            f"{settings.API_V1_STR}/dictionary-items",
            headers=superuser_token_headers,
            json={**payload, "label": "重复项"},
        )
        assert duplicate_response.status_code == 409
    finally:
        if type_id:
            _delete_dictionary_type(
                client,
                superuser_token_headers,
                type_id,
                item_id,
            )


def test_superuser_can_read_and_update_settings(
    client: TestClient, superuser_token_headers: dict[str, str]
) -> None:
    list_response = client.get(
        f"{settings.API_V1_STR}/settings",
        headers=superuser_token_headers,
    )
    assert list_response.status_code == 200
    keys = {setting["key"] for setting in list_response.json()["items"]}
    assert "system.name" in keys

    update_response = client.patch(
        f"{settings.API_V1_STR}/settings/system.name",
        headers=superuser_token_headers,
        json={"value": "Fast Vben Admin Test"},
    )
    assert update_response.status_code == 200
    assert update_response.json()["value"] == "Fast Vben Admin Test"


def test_public_settings_are_readable(client: TestClient) -> None:
    response = client.get(f"{settings.API_V1_STR}/settings/public")

    assert response.status_code == 200
    keys = {setting["key"] for setting in response.json()}
    assert "system.name" in keys
    assert "auth.allow_register" in keys


def test_public_settings_use_cached_payload(client: TestClient, monkeypatch) -> None:
    cache_store: dict[str, list[dict[str, object]]] = {}

    def fake_get_json(key: str) -> list[dict[str, object]] | None:
        return cache_store.get(key)

    def fake_set_json(
        key: str,
        value: list[dict[str, object]],
        *,
        _ttl_seconds: int | None = None,
    ) -> None:
        cache_store[key] = value

    monkeypatch.setattr(redis_cache, "get_json", fake_get_json)
    monkeypatch.setattr(redis_cache, "set_json", fake_set_json)

    first_response = client.get(f"{settings.API_V1_STR}/settings/public")
    assert first_response.status_code == 200
    assert cache_store

    cache_key = next(iter(cache_store))
    cache_store[cache_key][0]["value"] = "Cached Settings Value"

    second_response = client.get(f"{settings.API_V1_STR}/settings/public")
    assert second_response.status_code == 200
    assert any(
        setting["value"] == "Cached Settings Value"
        for setting in second_response.json()
    )


def test_updating_setting_bumps_public_settings_cache_namespace(
    client: TestClient, superuser_token_headers: dict[str, str], monkeypatch
) -> None:
    bumped_namespaces: list[str] = []
    monkeypatch.setattr(
        redis_cache,
        "bump_namespace",
        lambda namespace: bumped_namespaces.append(namespace),
    )

    response = client.patch(
        f"{settings.API_V1_STR}/settings/system.name",
        headers=superuser_token_headers,
        json={"value": "Fast Vben Admin Cache Test"},
    )

    assert response.status_code == 200
    assert CacheNamespace.PUBLIC_SETTINGS in bumped_namespaces


def test_json_setting_value_must_be_valid_json(
    client: TestClient, superuser_token_headers: dict[str, str]
) -> None:
    response = client.patch(
        f"{settings.API_V1_STR}/settings/system.name",
        headers=superuser_token_headers,
        json={"value_type": "json", "value": "{not-json"},
    )

    assert response.status_code == 400
    assert response.json()["message"] == "Setting value must be JSON"


def test_updating_dictionary_item_bumps_dictionary_cache_namespace(
    client: TestClient, superuser_token_headers: dict[str, str], monkeypatch
) -> None:
    bumped_namespaces: list[str] = []
    monkeypatch.setattr(
        redis_cache,
        "bump_namespace",
        lambda namespace: bumped_namespaces.append(namespace),
    )
    dictionary_code = f"dict_{random_lower_string()}"
    type_id: str | None = None
    item_id: str | None = None
    try:
        create_type_response = client.post(
            f"{settings.API_V1_STR}/dictionary-types",
            headers=superuser_token_headers,
            json={
                "code": dictionary_code,
                "name": "测试字典",
                "is_active": True,
            },
        )
        assert create_type_response.status_code == 200
        type_id = create_type_response.json()["id"]

        create_item_response = client.post(
            f"{settings.API_V1_STR}/dictionary-items",
            headers=superuser_token_headers,
            json={
                "type_id": type_id,
                "label": "测试项",
                "value": "cache-test",
                "sort": 0,
                "is_active": True,
            },
        )
        assert create_item_response.status_code == 200
        item_id = create_item_response.json()["id"]

        update_response = client.patch(
            f"{settings.API_V1_STR}/dictionary-items/{item_id}",
            headers=superuser_token_headers,
            json={"label": "更新后的测试项"},
        )
        assert update_response.status_code == 200
        assert CacheNamespace.DICTIONARY_ITEMS in bumped_namespaces
    finally:
        if type_id:
            _delete_dictionary_type(
                client,
                superuser_token_headers,
                type_id,
                item_id,
            )
