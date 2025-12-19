from fastapi import APIRouter
from app.schemas import AnalyzeRequest, AnalyzeResponse, Node, Edge, PathItem, NextNode, RecommendQuery

router = APIRouter()


@router.post("/analyze", response_model=AnalyzeResponse)
async def analyze_history(request: AnalyzeRequest) -> AnalyzeResponse:
    """
    履歴データを解析してネットワークグラフ用データを返す
    P0: モックデータを返す骨格実装
    """
    # P0: 受け取った履歴から簡易的なノードを生成
    nodes = []
    edges = []
    path = []

    seen_domains = {}
    prev_node_id = None

    for i, item in enumerate(request.history[:request.maxNodes]):
        # URLからドメインを抽出
        from urllib.parse import urlparse
        parsed = urlparse(item.url)
        domain = parsed.netloc or "unknown"

        if domain not in seen_domains:
            node_id = f"node_{len(seen_domains)}"
            seen_domains[domain] = node_id

            # 簡易的な座標計算（P1で改善予定）
            x = (len(seen_domains) % 10) * 100.0
            y = (len(seen_domains) // 10) * 100.0

            nodes.append(Node(
                id=node_id,
                url=f"https://{domain}",
                label=domain,
                x=x,
                y=y,
                size=item.visitCount * 5,
                hover_hints=[item.title[:30] if item.title else domain]
            ))

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

    # P0: ダミーのnext_nodesとrecommend_queries
    next_nodes = [
        NextNode(
            id="next_1",
            label="おすすめサイト",
            url="https://example.com",
            x=500.0,
            y=500.0,
            reason="よく訪問するサイトと関連"
        )
    ]

    recommend_queries = [
        RecommendQuery(query="検索ワード例", reason="頻繁に訪問するサイトに関連")
    ]

    return AnalyzeResponse(
        nodes=nodes,
        edges=edges,
        path=path,
        next_nodes=next_nodes,
        recommend_queries=recommend_queries
    )
