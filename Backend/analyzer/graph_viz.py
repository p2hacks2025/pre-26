import json
import os
import glob
from pathlib import Path
import networkx as nx
import matplotlib.pyplot as plt
import requests
import time

# --- 設定 ---
# 日本語フォント設定 (WindowsはMS Gothic, MacはHiragino Sansなど適宜変更)
plt.rcParams['font.family'] = 'MS Gothic' 

# Hugging Face API設定
# セキュアに扱うため、環境変数 `HF_TOKEN` から読み込みます。
# ※ 実行環境に設定されていない場合はプレースホルダが使われます（その場合は注意喚起が出ます）。
HF_TOKEN_PLACEHOLDER = "hf_xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx"
API_URL = "https://api-inference.huggingface.co/models/sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2"

def get_hf_token():
    """環境変数から HF_TOKEN を取得（未設定ならプレースホルダを返す）"""
    return os.environ.get("HF_TOKEN", HF_TOKEN_PLACEHOLDER)

def build_hf_headers():
    token = get_hf_token()
    return {"Authorization": f"Bearer {token}"}

# --- 関数定義 ---

def get_latest_search_log():
    """ダウンロードフォルダから最新のsearch_log_*.jsonを取得"""
    home = str(Path.home())
    downloads_dir = os.path.join(home, "Downloads")
    search_pattern = os.path.join(downloads_dir, "search_log_*.json")
    
    list_of_files = glob.glob(search_pattern)
    if not list_of_files:
        return None
    return max(list_of_files, key=os.path.getctime)

def get_embeddings(texts):
    """Hugging Face APIを使ってテキストをベクトル化"""
    if not texts:
        return []
    
    payload = {
        "inputs": texts,
        "options": {"wait_for_model": True}
    }
    
    try:
        # APIレート制限を考慮して少し待つなどの処理を入れても良い
        headers = build_hf_headers()
        response = requests.post(API_URL, headers=headers, json=payload)
        response.raise_for_status()
        return response.json()
    except Exception as e:
        print(f"Embedding Error: {e}")
        # エラー時はダミー(空リスト等)を返して処理を止めない
        return [[] for _ in texts]

def create_trajectory_graph(data):
    """
    検索ワードをノードにせず、ページ遷移の軌跡としてグラフを作成
    """
    G = nx.DiGraph()
    
    # 時系列順にソート
    sorted_data = sorted(data, key=lambda x: x['timestamp'])
    
    # 1. ベクトル化の準備（今回はタイトルを使用）
    # 全件一括でAPIに投げると重い場合があるので、実運用ではバッチ分割を推奨
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
            # 検索ワードがあればエッジのラベルにする
            edge_label = search_word if search_word else ""
            
            # エッジの色：検索経由なら赤、ただのリンク遷移なら黒、などの区別も可能
            edge_color = 'red' if search_word else 'black'
            
            G.add_edge(prev_node, current_url, 
                       label=edge_label, 
                       color=edge_color)
            
        prev_node = current_url
        
    return G

def draw_graph(G):
    """描画処理"""
    plt.figure(figsize=(12, 8))
    
    # レイアウト: spring_layout で「つながり」を可視化
    # ※将来的にはここでベクトルの類似度(weight)を使った配置計算を行う
    pos = nx.spring_layout(G, k=0.9, seed=42)
    
    # ノード描画
    nx.draw_networkx_nodes(G, pos, node_size=1500, node_color='skyblue', alpha=0.9)
    
    # ラベル描画
    node_labels = {n: G.nodes[n]['label'] for n in G.nodes}
    nx.draw_networkx_labels(G, pos, labels=node_labels, font_family='MS Gothic', font_size=9)
    
    # エッジ描画
    edge_colors = [G[u][v]['color'] for u, v in G.edges]
    nx.draw_networkx_edges(G, pos, edge_color=edge_colors, arrowsize=20, width=2)
    
    # エッジラベル（検索ワード）描画
    edge_labels = { (u,v): G[u][v]['label'] for u,v in G.edges if G[u][v]['label'] }
    nx.draw_networkx_edge_labels(G, pos, edge_labels=edge_labels, font_family='MS Gothic', font_size=8)
    
    plt.title("User's Knowledge Trajectory (with AI Embeddings)")
    plt.axis('off')
    plt.show()

# --- メイン実行 ---
if __name__ == "__main__":
    # 実行時に HF_TOKEN がプレースホルダのままかどうかを通知
    if get_hf_token() == HF_TOKEN_PLACEHOLDER:
        print("WARNING: HF_TOKEN が未設定です。環境変数 HF_TOKEN を設定してください。API 呼び出しは失敗する可能性があります。")

    json_file = get_latest_search_log()
    
    if json_file:
        print(f"Reading: {os.path.basename(json_file)}")
        with open(json_file, 'r', encoding='utf-8') as f:
            log_data = json.load(f)
            
        # グラフ作成
        graph = create_trajectory_graph(log_data)
        
        print(f"Nodes: {graph.number_of_nodes()}, Edges: {graph.number_of_edges()}")
        print("描画します...")
        draw_graph(graph)
    else:
        print("ログファイルが見つかりません。")