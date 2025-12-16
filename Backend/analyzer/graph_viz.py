import json
import os
import glob
import sys
from pathlib import Path
import networkx as nx
import matplotlib.pyplot as plt
import requests
import numpy as np
from sklearn.metrics.pairwise import cosine_similarity
from dotenv import load_dotenv

# --- 1. 環境設定 ---
# .envファイルを読み込む
load_dotenv()

# 日本語フォント設定 (WindowsはMS Gothic)
plt.rcParams['font.family'] = 'MS Gothic'

# API設定
API_URL = "https://api-inference.huggingface.co/models/sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2"

# --- 2. API関連関数 ---

def get_hf_headers():
    """
    Hugging Face API用のヘッダーを生成する。
    トークンが未設定の場合はエラーを出して止める。
    """
    token = os.getenv("HF_TOKEN")
    if not token:
        # トークンが無い場合はここで明確にエラーを投げる
        raise ValueError("【エラー】環境変数 'HF_TOKEN' が読み込めませんでした。.envファイルを確認してください。")
    return {"Authorization": f"Bearer {token}"}

def get_embeddings(texts):
    """Hugging Face APIを使ってテキストをベクトル化"""
    if not texts:
        return []
    
    headers = get_hf_headers()
    
    payload = {
        "inputs": texts,
        "options": {"wait_for_model": True}
    }
    
    try:
        # APIレート制限を考慮して少し待つなどの処理を入れても良い
        response = requests.post(API_URL, headers=headers, json=payload)
        response.raise_for_status()
        return response.json()
    except Exception as e:
        print(f"Embedding Error: {e}")
        # エラー時はダミー(空リスト等)を返して処理を止めない
        return [[] for _ in texts]

# --- 3. ログ読み込み関数 ---

def get_latest_search_log():
    """ダウンロードフォルダから最新のsearch_log_*.jsonを取得"""
    home = str(Path.home())
    downloads_dir = os.path.join(home, "Downloads")
    search_pattern = os.path.join(downloads_dir, "search_log_*.json")
    
    list_of_files = glob.glob(search_pattern)
    if not list_of_files:
        return None
    return max(list_of_files, key=os.path.getctime)

# --- 4. グラフ生成ロジック ---

def create_trajectory_graph(data):
    """
    検索ワードをノードにせず、ページ遷移の軌跡としてグラフを作成
    """
    G = nx.DiGraph()
    
    # 時系列順にソート
    sorted_data = sorted(data, key=lambda x: x['timestamp'])
    
    # ベクトル化の準備（今回はタイトルを使用）
    titles = [item['title'] for item in sorted_data]
    print(f"AI処理中: {len(titles)}件のテキストをベクトル化しています...")
    embeddings = get_embeddings(titles)
    
    prev_node = None
    
    for i, entry in enumerate(sorted_data):
        current_url = entry['url']
        # 表示用ラベル（長い場合はカット）
        label = entry['title'][:15] + "..." if len(entry['title']) > 15 else entry['title']
        search_word = entry.get('searchWord')
        
        # ベクトルデータの取得（API失敗時はNone）
        vector = embeddings[i] if i < len(embeddings) else None
        
        # ノード追加（メタデータとしてベクトルやタイムスタンプを持たせる）
        G.add_node(current_url, 
                   label=label, 
                   title=entry['title'],
                   timestamp=entry['timestamp'],
                   vector=vector)
        
        # エッジ追加（軌跡）
        if prev_node:
            edge_label = search_word if search_word else ""
            edge_color = 'red' if search_word else 'black'
            
            G.add_edge(prev_node, current_url, 
                       label=edge_label, 
                       color=edge_color)
            
        prev_node = current_url
        
    return G

# --- 5. レイアウト・描画ロジック ---

def apply_semantic_layout(G):
    """
    ベクトル情報を使って、意味が似ているノード同士を近くに配置する座標を計算する
    """
    # ベクトルを持つノードだけ抽出
    nodes_with_vec = [n for n in G.nodes if G.nodes[n].get('vector') is not None]
    
    # データ不足なら通常のspring_layout
    if not nodes_with_vec:
        return nx.spring_layout(G, k=0.9, seed=42)
    
    # 類似度行列を作成
    vectors = []
    valid_nodes = []
    
    for n in nodes_with_vec:
        v = G.nodes[n]['vector']
        # APIエラー等で空リストや非数値が混ざっていないかチェック
        if isinstance(v, list) and len(v) > 0 and isinstance(v[0], float):
            vectors.append(v)
            valid_nodes.append(n)
            
    if not vectors:
        return nx.spring_layout(G, k=0.9, seed=42)

    vectors_np = np.array(vectors)

    # コサイン類似度を計算
    try:
        sim_matrix = cosine_similarity(vectors_np)
    except Exception as e:
        print(f"類似度計算エラー: {e}")
        return nx.spring_layout(G)
    
    # レイアウト計算用のグラフ
    layout_G = G.copy()
    
    threshold = 0.5  # 類似度のしきい値
    
    print("意味的配置を計算中...")
    for i in range(len(valid_nodes)):
        for j in range(i + 1, len(valid_nodes)):
            sim = sim_matrix[i][j]
            if sim > threshold:
                u = valid_nodes[i]
                v = valid_nodes[j]
                # 似ているほど強く引き寄せる
                layout_G.add_edge(u, v, weight=sim * 5) 

    # weightを使って配置計算
    pos = nx.spring_layout(layout_G, weight='weight', k=0.8, seed=42)
    return pos

def draw_graph(G):
    """描画処理"""
    plt.figure(figsize=(12, 8))
    
    # 意味的レイアウトを適用
    pos = apply_semantic_layout(G)
    
    # ノード描画
    nx.draw_networkx_nodes(G, pos, node_size=1500, node_color='skyblue', alpha=0.9)
    
    # ラベル描画
    node_labels = {n: G.nodes[n]['label'] for n in G.nodes}
    nx.draw_networkx_labels(G, pos, labels=node_labels, font_family='MS Gothic', font_size=9)
    
    # エッジ描画
    edge_colors = [G[u][v].get('color', 'black') for u, v in G.edges]
    nx.draw_networkx_edges(G, pos, edge_color=edge_colors, arrowsize=20, width=2)
    
    # エッジラベル（検索ワード）描画
    edge_labels = { (u,v): G[u][v]['label'] for u,v in G.edges if G[u][v].get('label') }
    nx.draw_networkx_edge_labels(G, pos, edge_labels=edge_labels, font_family='MS Gothic', font_size=8)
    
    plt.title("Semantic Trajectory Graph")
    plt.axis('off')
    plt.show()

# --- 6. メイン実行ブロック ---
if __name__ == "__main__":
    try:
        # ログ取得
        json_file = get_latest_search_log()
        
        if json_file:
            print(f"Reading: {os.path.basename(json_file)}")
            with open(json_file, 'r', encoding='utf-8') as f:
                log_data = json.load(f)
                
            # グラフ構築 (AI処理含む)
            graph = create_trajectory_graph(log_data)
            
            print(f"Nodes: {graph.number_of_nodes()}, Edges: {graph.number_of_edges()}")
            print("描画します...")
            
            # 描画 (意味的配置含む)
            draw_graph(graph)
        else:
            print("ログファイルが見つかりません。")
            
    except ValueError as e:
        print(e)
    except Exception as e:
        print(f"予期せぬエラーが発生しました: {e}")
        import traceback
        traceback.print_exc()