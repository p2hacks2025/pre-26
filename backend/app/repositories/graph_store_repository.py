"""Repository abstraction for graph storage backends."""

from __future__ import annotations

from typing import Protocol, Any, Dict, Optional


class GraphStoreRepository(Protocol):
    """Protocol describing basic graph storage operations."""

    def save(self, session_uuid: str, graph_data: Dict[str, Any]) -> None:
        ...

    def get(self, session_uuid: str) -> Optional[Dict[str, Any]]:
        ...

    def delete(self, session_uuid: str) -> bool:
        ...
