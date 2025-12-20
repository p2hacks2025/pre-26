"""Gemini API連携サービス"""
import json
import logging
from typing import Optional
from datetime import datetime
from urllib.parse import urlparse

from app.clients.gemini import GeminiClient, default_gemini_client


logger = logging.getLogger(__name__)


def _resolve_client(client: Optional[GeminiClient]) -> GeminiClient:
    """DI経由のクライアントが無い場合はデフォルトを返す."""
    return client or default_gemini_client


def generate_search_keywords(
    path_nodes_info: list[dict],
    client: Optional[GeminiClient] = None,
) -> list[str]:
    """パス上のノード情報から検索キーワードを生成

    Args:
        path_nodes_info: パス上のノード情報のリスト
            例: [{"id": "node_0", "label": "github.com", "url": "https://github.com", ...}, ...]

    Returns:
        検索キーワードのリスト（最大3つ）
    """
    client = _resolve_client(client)

    if not client.is_available:
        # API keyが設定されていない場合はフォールバック
        return _generate_fallback_keywords(path_nodes_info)

    try:
        # hover_hintsの最初の要素（タイトルなど）を含めて経路を作成
        path_labels = " → ".join([
            f"{node['label']} ({node['hover_hints'][0] if node.get('hover_hints') else ''})" 
            for node in path_nodes_info
        ])
        
        # 詳細リストにもタイトルとURLを両方含める
        path_urls = "\n".join([
            f"- {node['label']} ({node['hover_hints'][0] if node.get('hover_hints') else ''}): {node['url']}" 
            for node in path_nodes_info
        ])

        prompt = f"""
ユーザーは以下の経路でWebサイトを閲覧しました：

閲覧経路:
{path_labels}

各サイトの詳細:
{path_urls}

この閲覧履歴から、ユーザーの関心事や調査内容を分析し、次に検索すべき具体的なキーワードを3つ提案してください。

要件:
1. パス上のサイト間の関連性を重視する
2. ユーザーが何を調べようとしているか推測する
3. 検索エンジンで実際に使えるキーワードにする（技術用語、サービス名など）
4. 各キーワードは簡潔に（2〜5単語程度）

出力形式: JSON配列のみを返してください。説明文は不要です。
例: ["キーワード1", "キーワード2", "キーワード3"]
"""

        response_text = client.generate_content(prompt)
        if not response_text:
            return _generate_fallback_keywords(path_nodes_info)

        # JSONとして解析を試みる
        try:
            # コードブロックのマークダウンを除去
            if response_text.startswith("```"):
                response_text = response_text.split("```")[1]
                if response_text.startswith("json"):
                    response_text = response_text[4:]
                response_text = response_text.strip()

            keywords = json.loads(response_text)

            # リストでない場合やキーワードが3つ未満の場合は調整
            if not isinstance(keywords, list):
                keywords = [str(keywords)]

            # 最大3つに制限
            keywords = keywords[:3]

            # 空の場合はフォールバック
            if not keywords:
                return _generate_fallback_keywords(path_nodes_info)

            return keywords

        except json.JSONDecodeError:
            # JSONパースに失敗した場合は、レスポンステキストを分割
            lines = [line.strip() for line in response_text.split('\n') if line.strip()]
            keywords = []
            for line in lines:
                # 引用符やマーカーを除去
                cleaned = line.strip('"\'- •*')
                if cleaned and len(cleaned) < 100:  # 長すぎる行は除外
                    keywords.append(cleaned)

            keywords = keywords[:3]

            if not keywords:
                return _generate_fallback_keywords(path_nodes_info)

            return keywords

    except Exception as e:
        logger.error(f"Gemini API Error: {e}")
        # エラー時はフォールバック
        return _generate_fallback_keywords(path_nodes_info)


def _generate_fallback_keywords(path_nodes_info: list[dict]) -> list[str]:
    """Gemini APIが使えない場合のフォールバックキーワード生成

    Args:
        path_nodes_info: パス上のノード情報のリスト

    Returns:
        シンプルなキーワードのリスト
    """
    if not path_nodes_info:
        return ["おすすめサイト", "関連情報", "次のステップ"]

    start_label = path_nodes_info[0]['label']
    end_label = path_nodes_info[-1]['label']

    keywords = [
        f"{start_label} 関連",
        f"{end_label} 詳細",
        f"{start_label} から {end_label}"
    ]

    return keywords


def classify_time_period_jp(timestamp: int) -> str:
    """時間帯を日本語で返す

    Args:
        timestamp: UNIXタイムスタンプ（ミリ秒）

    Returns:
        時間帯の日本語表現
    """
    dt = datetime.fromtimestamp(timestamp / 1000)
    hour = dt.hour

    if 6 <= hour < 12:
        return "朝"
    elif 12 <= hour < 18:
        return "昼"
    elif 18 <= hour < 23:
        return "夕方"
    else:
        return "夜"


def generate_next_domain_recommendation(
    history: list[dict],
    current_time: int,
    max_history: int = 10,
    client: Optional[GeminiClient] = None,
) -> Optional[dict]:
    """最近の閲覧履歴から次に訪問しそうなドメインを推薦

    Args:
        history: 履歴アイテムのリスト（HistoryItemのdict形式）
        current_time: 現在時刻のタイムスタンプ（ミリ秒）
        max_history: プロンプトに含める履歴の最大数

    Returns:
        推薦結果: {"domain": str, "reason": str, "confidence": float}
        失敗時はNone
    """
    client = _resolve_client(client)
    if not client.is_available:
        return None

    try:
        # 最新の履歴を取得（時系列逆順でソート）
        sorted_history = sorted(
            history,
            key=lambda x: x.get("visitTime", 0),
            reverse=True
        )[:max_history]

        # 履歴リストを作成
        history_lines = []
        for i, item in enumerate(sorted_history, 1):
            domain = urlparse(item["url"]).netloc or "unknown"
            title = item.get("title", domain)
            history_lines.append(f"{i}. {domain} - {title[:50]}")

        history_text = "\n".join(history_lines)

        # 現在の時刻情報
        dt = datetime.fromtimestamp(current_time / 1000)
        time_info = f"{dt.hour}時{dt.minute}分（{classify_time_period_jp(current_time)}）"

        prompt = f"""あなたはユーザーのWeb閲覧履歴を分析するAIアシスタントです。

ユーザーの最近の閲覧履歴（新しい順）:
{history_text}

現在時刻: {time_info}

この閲覧パターンから、ユーザーが次に訪問する可能性が高いWebサイトのドメインを1つ推薦してください。

要件:
1. 履歴に含まれていない新しいドメインを推薦する
2. ユーザーの関心事や調査内容のコンテキストを理解する
3. 実際に存在する有名なサイトのドメインを推薦する（例: qiita.com, zenn.dev, medium.comなど）
4. 推薦理由は簡潔に（50文字以内、日本語）
5. 信頼度は0.0-1.0で評価

出力形式（JSONのみ、説明文不要）:
{{
  "domain": "推薦ドメイン（例: qiita.com）",
  "reason": "推薦理由（50文字以内）",
  "confidence": 0.8
}}"""

        response_text = client.generate_content(prompt)
        if not response_text:
            return None

        # JSONパース（既存のコードと同様の処理）
        if response_text.startswith("```"):
            response_text = response_text.split("```")[1]
            if response_text.startswith("json"):
                response_text = response_text[4:]
            response_text = response_text.strip()

        result = json.loads(response_text)

        # バリデーション
        if not isinstance(result, dict):
            return None

        if "domain" not in result or "reason" not in result:
            return None

        # confidenceがない場合はデフォルト値
        if "confidence" not in result:
            result["confidence"] = 0.7

        return result

    except Exception as e:
        logger.error(f"Gemini recommendation error: {e}")
        return None


def generate_recommend_queries(
    history: list[dict],
    nodes_dict: dict,
    max_queries: int = 3,
    max_history: int = 20,
    client: Optional[GeminiClient] = None,
) -> list[dict]:
    """閲覧履歴全体から推薦検索クエリを生成

    Args:
        history: 履歴アイテムのリスト（HistoryItemのdict形式）
        nodes_dict: ノード辞書 {node_id: Node}
        max_queries: 生成する最大クエリ数（デフォルト: 3）
        max_history: プロンプトに含める履歴の最大数（デフォルト: 20）

    Returns:
        推薦クエリのリスト [{"query": str, "reason": str}, ...]
    """
    client = _resolve_client(client)
    if not client.is_available:
        # API keyが設定されていない場合はフォールバック
        return _generate_fallback_recommend_queries(nodes_dict)

    try:
        # 最新の履歴を取得（時系列逆順でソート）
        sorted_history = sorted(
            history,
            key=lambda x: x.get("visitTime", 0),
            reverse=True
        )[:max_history]

        # ドメインごとの訪問回数を集計
        domain_counts = {}
        for item in sorted_history:
            domain = urlparse(item.get("url", "")).netloc or "unknown"
            domain_counts[domain] = domain_counts.get(domain, 0) + 1

        # 頻度順にソート（上位5つ）
        top_domains = sorted(
            domain_counts.items(),
            key=lambda x: x[1],
            reverse=True
        )[:5]

        # 履歴リストを作成（タイトル付き）
        history_lines = []
        for i, item in enumerate(sorted_history[:15], 1):
            domain = urlparse(item.get("url", "")).netloc or "unknown"
            title = item.get("title", domain)[:50]
            visit_count = item.get("visitCount", 1)
            history_lines.append(f"{i}. {domain} - {title} (訪問回数: {visit_count})")

        history_text = "\n".join(history_lines)

        # 頻出ドメインリスト
        top_domains_text = "\n".join([f"- {domain} (訪問回数: {count})" for domain, count in top_domains])

        prompt = f"""あなたはユーザーのWeb閲覧履歴を分析するAIアシスタントです。

ユーザーの最近の閲覧履歴（新しい順）:
{history_text}

頻繁に訪問しているサイト:
{top_domains_text}

この閲覧パターンから、ユーザーの関心事や調査テーマを分析し、次に検索すべき具体的なキーワードを{max_queries}つ提案してください。

要件:
1. 閲覧履歴全体からユーザーの関心領域を推測する
2. 既に訪問したサイトの内容を深掘りするキーワードを提案
3. 検索エンジンで実際に使える具体的なキーワード（2〜5単語程度）
4. 各キーワードの推薦理由を簡潔に（30文字以内、日本語）
5. 技術者向けの専門的なキーワードも含める

出力形式（JSONのみ、説明文不要）:
[
  {{"query": "キーワード1", "reason": "推薦理由"}},
  {{"query": "キーワード2", "reason": "推薦理由"}},
  {{"query": "キーワード3", "reason": "推薦理由"}}
]"""

        response_text = client.generate_content(prompt)
        if not response_text:
            return _generate_fallback_recommend_queries(nodes_dict)

        # JSONパース（コードブロック除去）
        if response_text.startswith("```"):
            response_text = response_text.split("```")[1]
            if response_text.startswith("json"):
                response_text = response_text[4:]
            response_text = response_text.strip()

        queries = json.loads(response_text)

        # バリデーション
        if not isinstance(queries, list):
            queries = [queries]

        # 各要素が正しい形式かチェック
        valid_queries = []
        for q in queries:
            if isinstance(q, dict) and "query" in q and "reason" in q:
                valid_queries.append({
                    "query": str(q["query"])[:100],  # 最大100文字に制限
                    "reason": str(q["reason"])[:100]
                })

        # 最大数に制限
        valid_queries = valid_queries[:max_queries]

        # 空の場合はフォールバック
        if not valid_queries:
            return _generate_fallback_recommend_queries(nodes_dict)

        return valid_queries

    except Exception as e:
        logger.error(f"Gemini recommend queries error: {e}")
        # エラー時はフォールバック
        return _generate_fallback_recommend_queries(nodes_dict)


def _generate_fallback_recommend_queries(nodes_dict: dict) -> list[dict]:
    """Gemini APIが使えない場合のフォールバック推薦クエリ生成

    Args:
        nodes_dict: ノード辞書 {node_id: Node}

    Returns:
        シンプルな推薦クエリのリスト
    """
    if not nodes_dict or len(nodes_dict) == 0:
        return [
            {"query": "おすすめサイト", "reason": "閲覧履歴に基づく提案"},
            {"query": "関連情報", "reason": "興味のある分野の情報"},
            {"query": "最新トレンド", "reason": "話題のトピック"}
        ]

    # ノードからドメインを抽出（訪問回数が多い順にソート）
    nodes = sorted(
        nodes_dict.values(),
        key=lambda n: n.size,
        reverse=True
    )

    queries = []

    # 上位3つのドメインから推薦クエリを生成
    for i, node in enumerate(nodes[:3]):
        domain_label = node.label
        queries.append({
            "query": f"{domain_label} 使い方",
            "reason": "頻繁に訪問するサイトに関連"
        })

    # 3つ未満の場合は汎用的なクエリで補填
    while len(queries) < 3:
        queries.append({
            "query": "おすすめ情報",
            "reason": "閲覧パターンに基づく提案"
        })

    return queries[:3]
