from app.core.cache import CacheNamespace, redis_cache
from app.platform.bootstrap import init_db


def test_init_db_invalidates_access_caches(db, monkeypatch) -> None:
    invalidated: list[CacheNamespace] = []
    monkeypatch.setattr(redis_cache, "bump_namespace", invalidated.append)

    init_db(db)

    assert CacheNamespace.RBAC in invalidated
    assert CacheNamespace.MODULE_ACCESS in invalidated
