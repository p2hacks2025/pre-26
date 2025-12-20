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
    uuid: str  # セッションUUID（グラフデータをサーバに保存）


class SuggestRequest(BaseModel):
    """次に検索すべき場所の提案リクエスト"""
    uuid: str  # セッションUUID
    node_id_1: str  # 基準ノード1
    node_id_2: str  # 基準ノード2


class SuggestedNode(BaseModel):
    """提案された新ノード"""
    id: str
    label: str
    url: str
    x: float
    y: float
    size: int
    hover_hints: list[str]
    reason: str  # 提案理由


class SuggestedEdge(BaseModel):
    """提案ノードと既存ノードを繋ぐエッジ"""
    source: str
    target: str
    weight: int


class SuggestResponse(BaseModel):
    """提案レスポンス"""
    suggested_nodes: list[SuggestedNode]
    suggested_edges: list[SuggestedEdge]
    search_queries: list[str]  # Geminiが生成した検索キーワード
    path_nodes: list[str]  # 2ノード間の最短パス上のノードID
