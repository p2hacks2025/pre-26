"""API依存関係"""

from __future__ import annotations

from typing import Annotated

from fastapi import Depends

from app.clients.gemini import GeminiClient, default_gemini_client
from app.repositories.graph_store_repository import GraphStoreRepository
from app.repositories.in_memory_graph_store import default_graph_store


def get_gemini_client() -> GeminiClient:
    """Geminiクライアントのシングルトンを返す."""
    return default_gemini_client


def get_graph_store() -> GraphStoreRepository:
    """グラフストア実装を返す."""
    return default_graph_store


GeminiClientDep = Annotated[GeminiClient, Depends(get_gemini_client)]
GraphStoreDep = Annotated[GraphStoreRepository, Depends(get_graph_store)]

__all__ = ["GeminiClientDep", "GraphStoreDep", "get_gemini_client", "get_graph_store"]
