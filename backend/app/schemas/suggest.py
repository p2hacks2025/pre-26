"""提案APIスキーマ"""

from __future__ import annotations

from pydantic import BaseModel


class SuggestRequest(BaseModel):
    uuid: str
    node_id_1: str
    node_id_2: str


class SuggestedNode(BaseModel):
    id: str
    label: str
    url: str
    x: float
    y: float
    size: int
    hover_hints: list[str]
    reason: str


class SuggestedEdge(BaseModel):
    source: str
    target: str
    weight: int


class SuggestResponse(BaseModel):
    suggested_nodes: list[SuggestedNode]
    suggested_edges: list[SuggestedEdge]
    search_queries: list[str]
    path_nodes: list[str]
