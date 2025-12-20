"""
Next Node Recommendation Service

パス順序と時間帯×訪問頻度から候補ノードを算出する推薦アルゴリズム。
"""

from datetime import datetime
from urllib.parse import urlparse
from typing import Optional
from collections import Counter, defaultdict
import math

from app.schemas import HistoryItem, Node, PathItem, NextNode


# ============================================================================
# ヘルパー関数
# ============================================================================

def classify_time_period(timestamp: int) -> str:
    """
    UNIXタイムスタンプ（ミリ秒）を時間帯に分類する。

    Args:
        timestamp: UNIXタイムスタンプ（ミリ秒単位）

    Returns:
        時間帯文字列: "morning", "afternoon", "evening", "night"
    """
    # ミリ秒を秒に変換してdatetimeオブジェクト作成
    dt = datetime.fromtimestamp(timestamp / 1000)
    hour = dt.hour

    if 6 <= hour < 12:
        return "morning"
    elif 12 <= hour < 18:
        return "afternoon"
    elif 18 <= hour < 23:
        return "evening"
    else:
        return "night"


def extract_visit_sequences(path: list[PathItem], n: int = 3) -> list[tuple[str, ...]]:
    """
    パスからN-gramシーケンスを抽出する。

    Args:
        path: 時系列の訪問パス
        n: N-gramのサイズ（デフォルト: 3 = トライグラム）

    Returns:
        ノードIDのN-gramリスト
    """
    if len(path) < n:
        return []

    # 連続する重複を削除（A→A→B → A→B）
    deduplicated = []
    prev_id = None
    for item in path:
        if item.node_id != prev_id:
            deduplicated.append(item.node_id)
            prev_id = item.node_id

    # N-gramを抽出
    sequences = []
    for i in range(len(deduplicated) - n + 1):
        sequences.append(tuple(deduplicated[i:i+n]))

    return sequences


def extract_domain_from_url(url: str) -> str:
    """URLからドメインを抽出する。"""
    parsed = urlparse(url)
    return parsed.netloc or "unknown"


# ============================================================================
# パターン分析関数
# ============================================================================

def analyze_transition_patterns(path: list[PathItem]) -> dict[tuple[str, str], dict[str, int]]:
    """
    訪問パスから遷移パターン（Markov連鎖）を分析する。

    Args:
        path: 時系列の訪問パス

    Returns:
        遷移マップ: {(node_a, node_b): {next_node: count}}
    """
    # トライグラムを抽出
    trigrams = extract_visit_sequences(path, n=3)

    # 遷移マップを構築
    transition_map = defaultdict(lambda: defaultdict(int))

    for seq in trigrams:
        if len(seq) == 3:
            prefix = (seq[0], seq[1])  # 最初の2ノード
            next_node = seq[2]  # 3番目のノード
            transition_map[prefix][next_node] += 1

    return dict(transition_map)


def analyze_domain_transition_patterns(
    history: list[HistoryItem],
    n: int = 3
) -> dict[tuple[str, str], dict[str, int]]:
    """
    履歴データから直接ドメイン遷移パターンを分析する。

    既存のanalyze_transition_patterns()と異なり、ノードIDではなく
    履歴URLから直接ドメインを抽出してトライグラム分析を行う。
    これにより、グラフに未表示のドメインも推薦候補になる。

    Args:
        history: 履歴アイテムのリスト（時系列順）
        n: N-gramのサイズ（デフォルト: 3）

    Returns:
        ドメイン遷移マップ: {(domain_a, domain_b): {next_domain: count}}
    """
    if len(history) < n:
        return {}

    # 履歴を時系列順にソート
    sorted_history = sorted(history, key=lambda x: x.visitTime)

    # ドメインシーケンス抽出（重複除去）
    domain_sequence = []
    prev_domain = None
    for item in sorted_history:
        domain = extract_domain_from_url(item.url)
        if domain != prev_domain:
            domain_sequence.append(domain)
            prev_domain = domain

    # トライグラム抽出
    transition_map = defaultdict(lambda: defaultdict(int))
    for i in range(len(domain_sequence) - n + 1):
        if n == 3:
            prefix = (domain_sequence[i], domain_sequence[i+1])
            next_domain = domain_sequence[i+2]
            transition_map[prefix][next_domain] += 1

    return dict(transition_map)


def analyze_time_based_patterns(
    history: list[HistoryItem],
    nodes_dict: dict[str, Node]
) -> dict[str, dict[str, dict[str, float]]]:
    """
    履歴データから時間帯別の訪問パターンを分析する。

    Args:
        history: 履歴アイテムのリスト
        nodes_dict: 既存ノードの辞書（ドメイン→node_id のマッピング用）

    Returns:
        時間帯別パターン: {period: {domain: {"visit_count": X, "avg_engagement": Y}}}
    """
    # ドメイン→ノードIDのマッピングを作成
    domain_to_nodes = {}
    for node in nodes_dict.values():
        domain = extract_domain_from_url(node.url)
        domain_to_nodes[domain] = node

    # 時間帯別にデータを集計
    time_patterns = {
        "morning": defaultdict(lambda: {"visits": [], "counts": []}),
        "afternoon": defaultdict(lambda: {"visits": [], "counts": []}),
        "evening": defaultdict(lambda: {"visits": [], "counts": []}),
        "night": defaultdict(lambda: {"visits": [], "counts": []})
    }

    for item in history:
        period = classify_time_period(item.visitTime)
        domain = extract_domain_from_url(item.url)

        time_patterns[period][domain]["visits"].append(1)
        time_patterns[period][domain]["counts"].append(item.visitCount)

    # 集計結果を計算
    result = {}
    for period, domains in time_patterns.items():
        result[period] = {}
        for domain, data in domains.items():
            visit_count = len(data["visits"])
            avg_engagement = sum(data["counts"]) / len(data["counts"]) if data["counts"] else 0

            result[period][domain] = {
                "visit_count": visit_count,
                "avg_engagement": avg_engagement
            }

    return result


# ============================================================================
# スコア計算関数
# ============================================================================

def calculate_path_scores(
    nodes_dict: dict[str, Node],
    path: list[PathItem],
    transition_patterns: dict[tuple[str, str], dict[str, int]]
) -> list[tuple[str, float, str]]:
    """
    パス順序ベースのスコアを計算する。

    Args:
        nodes_dict: 既存ノードの辞書
        path: 訪問パス
        transition_patterns: 遷移パターンマップ

    Returns:
        [(domain, score, reason), ...] のリスト
    """
    if len(path) < 2:
        return []

    # 最後の2ノードを取得
    last_two = (path[-2].node_id, path[-1].node_id)

    # 遷移パターンから次の候補を取得
    if last_two not in transition_patterns:
        return []

    next_candidates = transition_patterns[last_two]
    total_transitions = sum(next_candidates.values())

    # スコアを計算
    results = []
    for node_id, count in next_candidates.items():
        if node_id in nodes_dict:
            node = nodes_dict[node_id]
            domain = extract_domain_from_url(node.url)
            score = (count / total_transitions) * 100

            # 遷移経路のラベルを取得
            label_a = nodes_dict[last_two[0]].label
            label_b = nodes_dict[last_two[1]].label

            percentage = int(score)
            reason = f"「{label_a} → {label_b}」の後、{percentage}%の確率でアクセスしています"

            results.append((domain, score, reason))

    return results


def calculate_time_scores(
    current_time: int,
    time_patterns: dict[str, dict[str, dict[str, float]]],
    existing_domains: set[str]
) -> list[tuple[str, float, str]]:
    """
    時間帯ベースのスコアを計算する。

    Args:
        current_time: 現在時刻のタイムスタンプ
        time_patterns: 時間帯別パターン
        existing_domains: 既存のドメインセット（除外用）

    Returns:
        [(domain, score, reason), ...] のリスト
    """
    # 現在の時間帯を取得
    current_period = classify_time_period(current_time)

    if current_period not in time_patterns:
        return []

    period_data = time_patterns[current_period]

    # スコアを計算
    results = []
    for domain, stats in period_data.items():
        # 既存ドメインは除外
        if domain in existing_domains:
            continue

        visit_count = stats["visit_count"]
        avg_engagement = stats["avg_engagement"]

        # スコア = 訪問頻度60% + 平均エンゲージメント40%
        score = (visit_count * 0.6) + (avg_engagement * 0.4)

        # 時間帯の日本語表記
        period_jp = {
            "morning": "朝",
            "afternoon": "昼",
            "evening": "夕方",
            "night": "夜"
        }.get(current_period, current_period)

        reason = f"{period_jp}の時間帯によくアクセスしています（過去{visit_count}回）"

        results.append((domain, score, reason))

    return results


# ============================================================================
# 統合関数
# ============================================================================

def calculate_domain_pattern_scores(
    history: list[HistoryItem],
    domain_patterns: dict[tuple[str, str], dict[str, int]],
    existing_domains: set[str]
) -> list[tuple[str, float, str]]:
    """
    履歴ドメインパターンからスコアを計算する。

    Args:
        history: 履歴アイテムのリスト
        domain_patterns: ドメイン遷移マップ
        existing_domains: 既存のドメインセット（除外用）

    Returns:
        [(domain, score, reason), ...] のリスト
    """
    if len(history) < 2:
        return []

    # 最新の履歴から直近2ドメインを取得
    sorted_history = sorted(history, key=lambda x: x.visitTime, reverse=True)

    # 重複を除去しながら直近2ドメインを取得
    recent_domains = []
    prev_domain = None
    for item in sorted_history:
        domain = extract_domain_from_url(item.url)
        if domain != prev_domain:
            recent_domains.append(domain)
            prev_domain = domain
        if len(recent_domains) >= 2:
            break

    if len(recent_domains) < 2:
        return []

    last_two = (recent_domains[1], recent_domains[0])  # 古→新の順

    # パターンから次の候補を取得
    if last_two not in domain_patterns:
        return []

    next_candidates = domain_patterns[last_two]
    total_transitions = sum(next_candidates.values())

    # スコアを計算
    results = []
    for domain, count in next_candidates.items():
        # 既存ドメインは除外
        if domain in existing_domains:
            continue

        probability = (count / total_transitions) * 100
        score = probability

        reason = f"「{last_two[0]} → {last_two[1]}」の後、{int(probability)}%の確率で訪問しています"

        results.append((domain, score, reason))

    return results


def merge_recommendations(
    domain_pattern_candidates: list[tuple[str, float, str]],
    path_candidates: list[tuple[str, float, str]],
    time_candidates: list[tuple[str, float, str]],
    gemini_candidate: Optional[dict] = None
) -> list[tuple[str, float, str, str]]:
    """
    複数のスコアリング手法の候補を統合してランキングする。

    Args:
        domain_pattern_candidates: 履歴ドメインパターン候補
        path_candidates: パスベース候補（既存実装）
        time_candidates: 時間ベース候補
        gemini_candidate: Gemini推薦結果 {"domain": str, "reason": str, "confidence": float}

    Returns:
        統合候補 [(domain, final_score, method, reason), ...] （スコア降順）
    """
    # ドメインごとにスコアと理由を集約
    domain_scores = defaultdict(lambda: {"score": 0.0, "methods": [], "reasons": []})

    # 1. 履歴ドメインパターン分析（重み40%）
    for domain, score, reason in domain_pattern_candidates:
        weighted_score = score * 0.4
        domain_scores[domain]["score"] += weighted_score
        domain_scores[domain]["methods"].append("domain_pattern")
        domain_scores[domain]["reasons"].append(reason)

    # 2. パスベース分析（重み0% - 既存ノードのみなので使わない）
    # domain_patternで代替されるため無効化

    # 3. 時間ベース分析（重み20%）
    for domain, score, reason in time_candidates:
        weighted_score = score * 0.2
        domain_scores[domain]["score"] += weighted_score
        domain_scores[domain]["methods"].append("time")
        domain_scores[domain]["reasons"].append(reason)

    # 4. Gemini推薦（重み40%、confidenceでスケーリング）
    if gemini_candidate and "domain" in gemini_candidate:
        domain = gemini_candidate["domain"]
        confidence = gemini_candidate.get("confidence", 0.7)
        base_score = 100  # 基準スコア
        weighted_score = base_score * confidence * 0.4

        domain_scores[domain]["score"] += weighted_score
        domain_scores[domain]["methods"].append("gemini")
        domain_scores[domain]["reasons"].append(gemini_candidate["reason"])

    # 統合結果を作成
    results = []
    for domain, data in domain_scores.items():
        final_score = data["score"]

        # メソッド名を結合
        if len(data["methods"]) > 1:
            method = "combined"
        else:
            method = data["methods"][0] if data["methods"] else "unknown"

        # 理由を結合（最大2つ）
        combined_reason = " / ".join(data["reasons"][:2])

        results.append((domain, final_score, method, combined_reason))

    # スコア降順でソート
    results.sort(key=lambda x: x[1], reverse=True)

    return results


def filter_existing_nodes(
    candidates: list[tuple[str, float, str, str]],
    nodes_dict: dict[str, Node]
) -> list[tuple[str, float, str, str]]:
    """
    既存ノードを候補から除外する。

    Args:
        candidates: 候補リスト [(domain, score, method, reason), ...]
        nodes_dict: 既存ノードの辞書

    Returns:
        新しいドメインのみの候補リスト
    """
    # 既存ドメインを抽出
    existing_domains = set()
    for node in nodes_dict.values():
        domain = extract_domain_from_url(node.url)
        existing_domains.add(domain)

    # 既存ドメイン以外の候補のみを返す
    return [
        (domain, score, method, reason)
        for domain, score, method, reason in candidates
        if domain not in existing_domains
    ]


def calculate_next_node_position(
    candidate: tuple[str, float, str, str],
    nodes_dict: dict[str, Node],
    path: list[PathItem],
    index: int = 0
) -> NextNode:
    """
    推薦ノードの座標を計算してNextNodeオブジェクトを作成する。

    Args:
        candidate: (domain, score, method, reason) のタプル
        nodes_dict: 既存ノードの辞書
        path: 訪問パス
        index: 候補のインデックス（複数候補時の配置用）

    Returns:
        NextNodeオブジェクト
    """
    domain, score, method, reason = candidate

    # 最後のノードの座標を取得
    if path and path[-1].node_id in nodes_dict:
        last_node = nodes_dict[path[-1].node_id]

        # 複数候補の場合は角度をずらす
        base_angle = 45
        angle_offset = index * 30  # 30度ずつずらす
        angle = (base_angle + angle_offset) * (math.pi / 180)
        distance = 150

        x = last_node.x + distance * math.cos(angle)
        y = last_node.y + distance * math.sin(angle)
    else:
        # パスが空の場合はデフォルト位置
        x = 100.0 * (index + 1)
        y = 100.0 * (index + 1)

    return NextNode(
        id=f"next_{index}",
        label=domain,
        url=f"https://{domain}",
        x=x,
        y=y,
        reason=reason
    )


# ============================================================================
# メイン関数
# ============================================================================

def generate_next_nodes(
    history: list[HistoryItem],
    nodes_dict: dict[str, Node],
    path: list[PathItem],
    current_time: int,
    max_candidates: int = 1
) -> list[NextNode]:
    """
    履歴パターン、時間帯、Gemini AIを統合して次の推薦ノードを生成する。

    Args:
        history: 履歴データ
        nodes_dict: 既存ノードの辞書
        path: 訪問パス
        current_time: 現在時刻
        max_candidates: 返す候補の最大数（デフォルト: 1）

    Returns:
        推薦ノードのリスト
    """
    # 既存ドメインを抽出
    existing_domains = set()
    for node in nodes_dict.values():
        domain = extract_domain_from_url(node.url)
        existing_domains.add(domain)

    # Step 1: 履歴ドメインパターン分析（新規）
    domain_patterns = analyze_domain_transition_patterns(history, n=3)
    domain_pattern_candidates = calculate_domain_pattern_scores(
        history, domain_patterns, existing_domains
    )

    # Step 2: 時間ベース分析
    time_patterns = analyze_time_based_patterns(history, nodes_dict)
    time_candidates = calculate_time_scores(current_time, time_patterns, existing_domains)

    # Step 3: Gemini推薦を取得
    from app.services.gemini_service import generate_next_domain_recommendation

    # historyをdict形式に変換
    history_dicts = [
        {
            "url": item.url,
            "title": item.title,
            "visitTime": item.visitTime,
            "visitCount": item.visitCount
        }
        for item in history
    ]

    gemini_candidate = generate_next_domain_recommendation(
        history_dicts, current_time, max_history=10
    )

    # Step 4: スコア統合
    merged_candidates = merge_recommendations(
        domain_pattern_candidates,
        [],  # path_candidatesは使わない
        time_candidates,
        gemini_candidate
    )

    # Step 5: 既存ノード除外（既に各候補生成時に除外済みだが念のため）
    new_candidates = filter_existing_nodes(merged_candidates, nodes_dict)

    # Step 6: スコア閾値でフィルタリング（最低スコア5.0以上）
    filtered_candidates = [
        candidate for candidate in new_candidates
        if candidate[1] >= 5.0
    ]

    # Step 7: NextNodeオブジェクト作成（top N）
    next_nodes = []
    for i, candidate in enumerate(filtered_candidates[:max_candidates]):
        next_node = calculate_next_node_position(
            candidate, nodes_dict, path, index=i
        )
        next_nodes.append(next_node)

    return next_nodes
