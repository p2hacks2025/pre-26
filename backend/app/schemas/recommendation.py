"""推薦・分析レスポンススキーマ"""

from __future__ import annotations

from pydantic import BaseModel

from .graph import Edge, Node, PathItem


class NextNode(BaseModel):
    id: str
    label: str
    url: str
    x: float
    y: float
    reason: str


class RecommendQuery(BaseModel):
    query: str
    reason: str


class AnalyzeResponse(BaseModel):
    nodes: list[Node]
    edges: list[Edge]
    path: list[PathItem]
    next_nodes: list[NextNode]
    recommend_queries: list[RecommendQuery]
    uuid: str
