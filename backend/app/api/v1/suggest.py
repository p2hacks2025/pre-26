"""Suggestion endpoints."""

from __future__ import annotations

import math
from typing import Any

from fastapi import APIRouter, HTTPException

from app.api.deps import GeminiClientDep

from app.schemas import (
    SuggestRequest,
    SuggestResponse,
    SuggestedEdge,
    SuggestedNode,
)
from app.services.gemini_service import generate_search_keywords
from app.services.graph_store import graph_store

router = APIRouter(tags=["suggest"])


@router.post("/suggest", response_model=SuggestResponse)
async def suggest_next_nodes(
    request: SuggestRequest,
    gemini_client: GeminiClientDep,
) -> SuggestResponse:
    """次に検索すべき場所を提案する。"""
    graph_data = graph_store.get(request.uuid)
    if not graph_data:
        raise HTTPException(
            status_code=404,
            detail="Session not found. UUID may have expired.",
        )

    nodes: list[dict[str, Any]] = graph_data["nodes"]
    edges: list[dict[str, Any]] = graph_data["edges"]

    node1 = next((n for n in nodes if n["id"] == request.node_id_1), None)
    node2 = next((n for n in nodes if n["id"] == request.node_id_2), None)

    if not node1 or not node2:
        raise HTTPException(
            status_code=400,
            detail="Specified node IDs not found in graph",
        )

    import networkx as nx

    graph = nx.Graph()
    for node in nodes:
        graph.add_node(node["id"], **node)
    for edge in edges:
        graph.add_edge(edge["source"], edge["target"], weight=edge["weight"])

    try:
        shortest_path = nx.shortest_path(graph, node1["id"], node2["id"])
        path_length = len(shortest_path) - 1
    except nx.NetworkXNoPath:
        raise HTTPException(
            status_code=400, detail="No path found between the two nodes"
        )

    path_nodes_info = [
        next(n for n in nodes if n["id"] == node_id) for node_id in shortest_path
    ]

    search_queries = generate_search_keywords(path_nodes_info, client=gemini_client)

    mid_point_index = len(path_nodes_info) // 2
    mid_node = path_nodes_info[mid_point_index]

    suggested_nodes: list[SuggestedNode] = []
    suggested_edges: list[SuggestedEdge] = []

    for i, keyword in enumerate(search_queries):
        node_id = f"suggested_{i}"

        angle = (i * 120) * (math.pi / 180)
        offset_distance = 100
        x = mid_node["x"] + offset_distance * math.cos(angle)
        y = mid_node["y"] + offset_distance * math.sin(angle)

        suggested_nodes.append(
            SuggestedNode(
                id=node_id,
                label=keyword,
                url=f"https://www.google.com/search?q={keyword}",
                x=x,
                y=y,
                size=25,
                hover_hints=[
                    f"検索キーワード: {keyword}",
                    f"パス長: {path_length}",
                    f"経路: {' → '.join([n['label'] for n in path_nodes_info[:3]])}",
                ],
                reason=f"閲覧経路「{' → '.join([n['label'] for n in path_nodes_info])}」から推測",
            )
        )

        suggested_edges.append(
            SuggestedEdge(
                source=mid_node["id"],
                target=node_id,
                weight=1,
            )
        )

    return SuggestResponse(
        suggested_nodes=suggested_nodes,
        suggested_edges=suggested_edges,
        search_queries=search_queries,
        path_nodes=[n["id"] for n in path_nodes_info],
    )


__all__ = ["router", "suggest_next_nodes"]
