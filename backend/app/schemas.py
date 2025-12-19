from pydantic import BaseModel
from typing import Optional


class HistoryItem(BaseModel):
    url: str
    title: str
    visitTime: int
    visitCount: int


class AnalyzeRequest(BaseModel):
    history: list[HistoryItem]
    currentTime: int
    startTime: int
    endTime: int
    maxNodes: Optional[int] = 50


class Node(BaseModel):
    id: str
    url: str
    label: str
    x: float
    y: float
    size: int
    hover_hints: list[str]


class Edge(BaseModel):
    source: str
    target: str
    weight: int


class PathItem(BaseModel):
    node_id: str
    timestamp: int
    order: int


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
