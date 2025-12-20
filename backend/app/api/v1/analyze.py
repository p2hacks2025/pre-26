"""Analyze history endpoint."""

from __future__ import annotations

from fastapi import APIRouter

from app.api.deps import GeminiClientDep, GraphStoreDep

from app.schemas import (
    AnalyzeRequest,
    AnalyzeResponse,
    Edge,
    Node,
    PathItem,
    RecommendQuery,
)
from app.services.recommendation_service import generate_next_nodes

router = APIRouter(tags=["analyze"])


@router.post("/analyze", response_model=AnalyzeResponse)
async def analyze_history(
    request: AnalyzeRequest,
    gemini_client: GeminiClientDep,
    graph_store: GraphStoreDep,
) -> AnalyzeResponse:
    """履歴データを解析してネットワークグラフ用データを返す。"""
    import networkx as nx
    from urllib.parse import urlparse

    nodes_dict: dict[str, Node] = {}
    edges: list[Edge] = []
    path: list[PathItem] = []

    seen_domains: dict[str, str] = {}
    prev_node_id: str | None = None

    for i, item in enumerate(request.history[:request.maxNodes]):
        parsed = urlparse(item.url)
        domain = parsed.netloc or "unknown"

        if domain not in seen_domains:
            node_id = f"node_{len(seen_domains)}"
            seen_domains[domain] = node_id

            max_size = 100
            calculated_size = item.visitCount * 30
            node_size = min(calculated_size, max_size)

            nodes_dict[node_id] = Node(
                id=node_id,
                url=item.url,
                label=domain,
                x=0.0,
                y=0.0,
                size=node_size,
                hover_hints=[item.title[:30] if item.title else domain],
            )

        node_id = seen_domains[domain]

        path.append(
            PathItem(
                node_id=node_id,
                timestamp=item.visitTime,
                order=i + 1,
            )
        )

        if prev_node_id and prev_node_id != node_id:
            edge_exists = any(
                e.source == prev_node_id and e.target == node_id for e in edges
            )
            if not edge_exists:
                edges.append(
                    Edge(
                        source=prev_node_id,
                        target=node_id,
                        weight=1,
                    )
                )

        prev_node_id = node_id

    graph = nx.Graph()
    for node_id in nodes_dict:
        graph.add_node(node_id)
    for edge in edges:
        graph.add_edge(edge.source, edge.target, weight=edge.weight)

    if len(graph.nodes()) > 0:
        pos = nx.spring_layout(graph, k=2, iterations=50, scale=500, seed=42)
        for node_id, (x, y) in pos.items():
            nodes_dict[node_id].x = float(x)
            nodes_dict[node_id].y = float(y)

    nodes = list(nodes_dict.values())

    try:
        next_nodes = generate_next_nodes(
            history=request.history,
            nodes_dict=nodes_dict,
            path=path,
            current_time=request.currentTime,
            max_candidates=1,
            gemini_client=gemini_client,
        )
    except Exception as exc:  # pragma: no cover - fallback path
        import logging

        logging.getLogger(__name__).error("Error generating next nodes: %s", exc)
        next_nodes = []

    recommend_queries = [
        RecommendQuery(query="検索ワード例", reason="頻繁に訪問するサイトに関連")
    ]

    session_uuid = graph_store.generate_uuid()
    graph_data = {
        "nodes": [node.model_dump() for node in nodes],
        "edges": [edge.model_dump() for edge in edges],
        "path": [p.model_dump() for p in path],
    }
    graph_store.save(session_uuid, graph_data)

    return AnalyzeResponse(
        nodes=nodes,
        edges=edges,
        path=path,
        next_nodes=next_nodes,
        recommend_queries=recommend_queries,
        uuid=session_uuid,
    )


__all__ = ["analyze_history", "router"]
