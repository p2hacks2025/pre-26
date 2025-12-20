"""In-memory implementation of the GraphStoreRepository."""

from __future__ import annotations

import uuid
from datetime import datetime, timedelta
from typing import Any, Dict, Optional

from .graph_store_repository import GraphStoreRepository


class InMemoryGraphStore(GraphStoreRepository):
    """Simple TTL-based in-memory graph store."""

    def __init__(self, ttl_minutes: int = 30) -> None:
        self._store: Dict[str, Dict[str, Any]] = {}
        self._ttl = timedelta(minutes=ttl_minutes)

    def generate_uuid(self) -> str:
        return str(uuid.uuid4())

    def save(self, session_uuid: str, graph_data: Dict[str, Any]) -> None:
        self._store[session_uuid] = {
            "graph_data": graph_data,
            "created_at": datetime.now(),
        }
        self._cleanup()

    def get(self, session_uuid: str) -> Optional[Dict[str, Any]]:
        record = self._store.get(session_uuid)
        if not record:
            return None
        if self._is_expired(record["created_at"]):
            del self._store[session_uuid]
            return None
        return record["graph_data"]

    def delete(self, session_uuid: str) -> bool:
        if session_uuid in self._store:
            del self._store[session_uuid]
            return True
        return False

    # ------------------------------------------------------------------

    def _is_expired(self, created_at: datetime) -> bool:
        return datetime.now() - created_at > self._ttl

    def _cleanup(self) -> None:
        expired_keys = [key for key, value in self._store.items() if self._is_expired(value["created_at"])]
        for key in expired_keys:
            del self._store[key]


default_graph_store = InMemoryGraphStore()

__all__ = ["InMemoryGraphStore", "default_graph_store"]
