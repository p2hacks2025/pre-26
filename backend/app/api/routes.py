from fastapi import APIRouter, HTTPException
from app.schemas import (
    AnalyzeRequest, AnalyzeResponse, Node, Edge, PathItem, NextNode, RecommendQuery,
    SuggestRequest, SuggestResponse, SuggestedNode, SuggestedEdge
)
from app.services.graph_store import graph_store
from app.services.gemini_service import generate_search_keywords, generate_recommend_queries
from app.services.recommendation_service import generate_next_nodes
import math
import logging

logger = logging.getLogger(__name__)

router = APIRouter()


@router.post("/analyze", response_model=AnalyzeResponse)
async def analyze_history(request: AnalyzeRequest) -> AnalyzeResponse:
    """
    履歴データを解析してネットワークグラフ用データを返す
    """
    import networkx as nx
    from urllib.parse import urlparse

    # 受け取った履歴からノードとエッジを生成
    nodes_dict = {}  # {node_id: Node}
    edges = []
    path = []

    seen_domains = {}
    prev_node_id = None

    for i, item in enumerate(request.history[:request.maxNodes]):
        # URLからドメインを抽出
        parsed = urlparse(item.url)
        domain = parsed.netloc or "unknown"

        if domain not in seen_domains:
            node_id = f"node_{len(seen_domains)}"
            seen_domains[domain] = node_id

            # 仮の座標（後でレイアウト計算で上書き）
            nodes_dict[node_id] = Node(
                id=node_id,
                url=f"https://{domain}",
                label=domain,
                x=0.0,
                y=0.0,
                size=item.visitCount * 5,
                hover_hints=[item.title[:30] if item.title else domain]
            )

        node_id = seen_domains[domain]

        # パスに追加
        path.append(PathItem(
            node_id=node_id,
            timestamp=item.visitTime,
            order=i + 1
        ))

        # エッジを生成
        if prev_node_id and prev_node_id != node_id:
            edge_exists = any(
                e.source == prev_node_id and e.target == node_id
                for e in edges
            )
            if not edge_exists:
                edges.append(Edge(
                    source=prev_node_id,
                    target=node_id,
                    weight=1
                ))

        prev_node_id = node_id

    # NetworkXでグラフを構築してレイアウト計算
    G = nx.Graph()
    for node_id in nodes_dict:
        G.add_node(node_id)
    for edge in edges:
        G.add_edge(edge.source, edge.target, weight=edge.weight)

    # Spring layoutで座標計算（自然なネットワーク配置）
    if len(G.nodes()) > 0:
        pos = nx.spring_layout(G, k=2, iterations=50, scale=500, seed=42)

        # 計算された座標をノードに適用
        for node_id, (x, y) in pos.items():
            nodes_dict[node_id].x = float(x)
            nodes_dict[node_id].y = float(y)

    # Nodeのリストに変換
    nodes = list(nodes_dict.values())

    # パターン分析と候補ノード生成
    try:
        next_nodes = generate_next_nodes(
            history=request.history,
            nodes_dict=nodes_dict,
            path=path,
            current_time=request.currentTime,
            max_candidates=1
        )
    except Exception as e:
        logger.error(f"Error generating next nodes: {e}")
        # エラー時は空リストを返す（全体の処理は継続）
        next_nodes = []

    # 閲覧履歴全体から推薦クエリを生成
    try:
        queries_data = generate_recommend_queries(
            history=[item.model_dump() for item in request.history],
            nodes_dict=nodes_dict,
            max_queries=3
        )
        recommend_queries = [
            RecommendQuery(query=q["query"], reason=q["reason"])
            for q in queries_data
        ]
    except Exception as e:
        logger.error(f"Error generating recommend queries: {e}")
        # エラー時はフォールバッククエリを返す
        recommend_queries = [
            RecommendQuery(query="おすすめサイト", reason="閲覧履歴に基づく提案")
        ]

    # UUID生成とグラフデータ保存
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
        uuid=session_uuid
    )


@router.post("/suggest", response_model=SuggestResponse)
async def suggest_next_nodes(request: SuggestRequest) -> SuggestResponse:
    """
    次に検索すべき場所を提案する

    2つのノード間の距離を計算し、Gemini APIで検索キーワードを生成して
    新しいノードを提案する。
    """
    # UUIDでグラフデータを取得
    graph_data = graph_store.get(request.uuid)
    if not graph_data:
        raise HTTPException(status_code=404, detail="Session not found. UUID may have expired.")

    nodes = graph_data["nodes"]
    edges = graph_data["edges"]

    # 指定された2つのノードを検索
    node1 = next((n for n in nodes if n["id"] == request.node_id_1), None)
    node2 = next((n for n in nodes if n["id"] == request.node_id_2), None)

    if not node1 or not node2:
        raise HTTPException(status_code=400, detail="Specified node IDs not found in graph")

    # NetworkXでグラフを再構築
    import networkx as nx
    G = nx.Graph()
    for node in nodes:
        G.add_node(node["id"], **node)
    for edge in edges:
        G.add_edge(edge["source"], edge["target"], weight=edge["weight"])

    # 2ノード間の最短パスを計算
    try:
        shortest_path = nx.shortest_path(G, node1["id"], node2["id"])
        path_length = len(shortest_path) - 1
    except nx.NetworkXNoPath:
        raise HTTPException(status_code=400, detail="No path found between the two nodes")

    # パス上のノード情報を取得（Geminiへのプロンプト用）
    path_nodes_info = [next(n for n in nodes if n["id"] == node_id) for node_id in shortest_path]

    # Gemini APIで検索キーワードを生成
    search_queries = generate_search_keywords(path_nodes_info)

    # パスの中間地点のノードを取得（提案ノードの配置基準）
    mid_point_index = len(path_nodes_info) // 2
    mid_node = path_nodes_info[mid_point_index]

    # 提案ノードを生成
    suggested_nodes = []
    suggested_edges = []

    for i, keyword in enumerate(search_queries):
        node_id = f"suggested_{i}"

        # 中間ノードの周囲に円形配置（120度ずつ）
        angle = (i * 120) * (math.pi / 180)
        offset_distance = 100  # 中間ノードからの距離
        x = mid_node["x"] + offset_distance * math.cos(angle)
        y = mid_node["y"] + offset_distance * math.sin(angle)

        suggested_nodes.append(SuggestedNode(
            id=node_id,
            label=keyword,
            url=f"https://www.google.com/search?q={keyword}",
            x=x,
            y=y,
            size=25,
            hover_hints=[
                f"検索キーワード: {keyword}",
                f"パス長: {path_length}",
                f"経路: {' → '.join([n['label'] for n in path_nodes_info[:3]])}"
            ],
            reason=f"閲覧経路「{' → '.join([n['label'] for n in path_nodes_info])}」から推測"
        ))

        # 中間ノードと接続
        suggested_edges.append(SuggestedEdge(
            source=mid_node["id"],
            target=node_id,
            weight=1
        ))

    return SuggestResponse(
        suggested_nodes=suggested_nodes,
        suggested_edges=suggested_edges,
        search_queries=search_queries,
        path_nodes=[n["id"] for n in path_nodes_info]
    )
