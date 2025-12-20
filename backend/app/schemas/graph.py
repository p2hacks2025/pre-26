"""グラフ表示に関連するスキーマ"""

from __future__ import annotations

from pydantic import BaseModel


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
