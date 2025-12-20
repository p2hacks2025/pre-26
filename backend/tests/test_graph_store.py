from datetime import datetime, timedelta

from app.repositories.in_memory_graph_store import InMemoryGraphStore


def test_save_and_get_roundtrip() -> None:
    store = InMemoryGraphStore(ttl_minutes=30)
    session_uuid = store.generate_uuid()
    payload = {"nodes": [], "edges": []}

    store.save(session_uuid, payload)

    assert store.get(session_uuid) == payload


def test_delete_removes_session() -> None:
    store = InMemoryGraphStore(ttl_minutes=30)
    session_uuid = store.generate_uuid()
    store.save(session_uuid, {})

    assert store.delete(session_uuid) is True
    assert store.get(session_uuid) is None
    assert store.delete(session_uuid) is False


def test_get_discards_expired_entries() -> None:
    store = InMemoryGraphStore(ttl_minutes=30)
    session_uuid = store.generate_uuid()
    store.save(session_uuid, {"nodes": []})

    # 直接ストアを書き換えてTTLを過ぎた状態を再現
    store._store[session_uuid]["created_at"] = datetime.now() - timedelta(minutes=31)

    assert store.get(session_uuid) is None
    assert session_uuid not in store._store
