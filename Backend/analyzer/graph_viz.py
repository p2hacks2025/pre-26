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
load_dotenv()

# 日本語フォント設定 (WindowsはMS Gothic)
plt.rcParams['font.family'] = 'MS Gothic'

# --- ★ここを修正しました★ ---

# 埋め込みモデル (Embedding): 'E5-large' (精度が高く、APIも安定しています)
# 元のMiniLMが410エラーで消滅したため変更
EMBED_API_URL = "https://api-inference.huggingface.co/models/intfloat/multilingual-e5-large"

# 生成モデル (Text Generation): 'Zephyr-7b-beta' (Mistralベースで日本語に強く、利用規約同意なしですぐ使えます)
# 元のMistral-v0.3は権限エラーが出るため変更
GEN_API_URL = "https://api-inference.huggingface.co/models/HuggingFaceH4/zephyr-7b-beta"

# -----------------------------

# --- 2. API関連関数 ---

def get_hf_headers():
    token = os.getenv("HF_TOKEN")
    if not token:
        raise ValueError("【エラー】環境変数 'HF_TOKEN' が読み込めませんでした。.envファイルを確認してください。")
    return {"Authorization": f"Bearer {token}"}

def get_embeddings(texts):
    """テキストをベクトル化"""
    if not texts: return []
    headers = get_hf_headers()
    
    # E5モデルは "query: " という接頭辞をつけるのが作法ですが、
    # 簡易的にそのまま投げても動きます。今回はそのまま投げます。
    payload = {"inputs": texts, "options": {"wait_for_model": True}}
    
    try:
        response = requests.post(EMBED_API_URL, headers=headers, json=payload)
        response.raise_for_status()
        return response.json()
    except Exception as e:
        print(f"Embedding API Warning: {e}")
        # エラー時は空リストを返してグラフ描画だけは止めない
        return [[] for _ in texts]

def generate_next_steps(history_titles):
    """
    閲覧履歴(タイトル)をもとに、次に検索すべきキーワードをAIに考えさせる
    """
    if not history_titles:
        return []

    # 直近3件くらいの履歴を使う
    context = ", ".join(history_titles[-3:])
    
    # プロンプト（AIへの命令）
    prompt = f"""<|system|>
あなたは優秀な学習アシスタントです。ユーザーの関心を広げるための提案を行います。</s>
<|user|>
ユーザーの閲覧履歴: "{context}"
これに基づき、ユーザーが次に検索すべき「関連する発展的なキーワード」を3つ提案してください。

条件:
1. 日本語で出力すること。
2. キーワードのみをカンマ区切りで出力すること。余計な説明は不要。
3. 出力例: Python 非同期処理, イベントループ, 並行プログラミング</s>
<|assistant|>"""
    
    headers = get_hf_headers()
    payload = {
        "inputs": prompt,
        "parameters": {
            "max_new_tokens": 50,
            "return_full_text": False,
            "temperature": 0.7
        }
    }
    
    print("AIが未来の可能性を計算中...")
    try:
        response = requests.post(GEN_API_URL, headers=headers, json=payload)
        response.raise_for_status()
        result = response.json()
        
        # 結果の解析
        generated_text = result[0]['generated_text'].strip()
        suggestions = [s.strip() for s in generated_text.replace('\n', ',').split(',') if s.strip()]
        return suggestions[:3]
    except Exception as e:
        print(f"Generation API Warning: {e}")
        # エラー時はダミーを表示
        return ["AI提案(通信エラー)"]

# --- 3. ログ読み込み ---

def get_latest_search_log():
    home = str(Path.home())
    downloads_dir = os.path.join(home, "Downloads")
    search_pattern = os.path.join(downloads_dir, "search_log_*.json")
    list_of_files = glob.glob(search_pattern)
    return max(list_of_files, key=os.path.getctime) if list_of_files else None

# --- 4. グラフ生成 ---

def create_trajectory_graph(data):
    G = nx.DiGraph()
    sorted_data = sorted(data, key=lambda x: x['timestamp'])
    
    # --- A. 履歴ノードの構築 ---
    titles = [item['title'] for item in sorted_data]
    print(f"履歴をベクトル化中 ({len(titles)}件)...")
    embeddings = get_embeddings(titles)
    
    prev_node = None
    last_node = None
    
    for i, entry in enumerate(sorted_data):
        current_url = entry['url']
        label = entry['title'][:10] + "..." if len(entry['title']) > 10 else entry['title']
        search_word = entry.get('searchWord')
        vector = embeddings[i] if i < len(embeddings) else None
        
        # ノード追加
        G.add_node(current_url, label=label, full_title=entry['title'], 
                   type='history', vector=vector)
        
        if prev_node:
            G.add_edge(prev_node, current_url, label=search_word or "", style='solid')
            
        prev_node = current_url
        last_node = current_url

    # --- B. 未来ノード(AI提案)の追加 ---
    if last_node:
        suggestions = generate_next_steps(titles)
        print(f"AI提案キーワード: {suggestions}")
        
        # 提案ワードもベクトル化
        suggestion_vecs = get_embeddings(suggestions)
        
        for i, word in enumerate(suggestions):
            sug_id = f"suggestion_{i}"
            vec = suggestion_vecs[i] if i < len(suggestion_vecs) else None
            
            G.add_node(sug_id, label=word, full_title=word, 
                       type='suggestion', vector=vec)
            
            G.add_edge(last_node, sug_id, label="Next?", style='dotted')
            
    return G

# --- 5. レイアウト・描画 ---

def apply_semantic_layout(G):
    nodes_with_vec = [n for n in G.nodes if G.nodes[n].get('vector') is not None]
    
    # ベクトルデータの検証
    valid_nodes = []
    valid_vectors = []
    for n in nodes_with_vec:
        v = G.nodes[n]['vector']
        if isinstance(v, list) and len(v) > 0:
            valid_nodes.append(n)
            valid_vectors.append(v)
            
    if not valid_vectors:
        return nx.spring_layout(G, k=0.9, seed=42)

    try:
        sim_matrix = cosine_similarity(valid_vectors)
    except Exception as e:
        print(f"類似度計算スキップ: {e}")
        return nx.spring_layout(G, k=0.9, seed=42)
    
    layout_G = G.copy()
    threshold = 0.4
    
    for i in range(len(valid_nodes)):
        for j in range(i + 1, len(valid_nodes)):
            sim = sim_matrix[i][j]
            if sim > threshold:
                u = valid_nodes[i]
                v = valid_nodes[j]
                layout_G.add_edge(u, v, weight=sim * 3)
    
    return nx.spring_layout(layout_G, weight='weight', k=0.7, seed=42)

def draw_graph(G):
    plt.figure(figsize=(12, 8))
    pos = apply_semantic_layout(G)
    
    history_nodes = [n for n, attr in G.nodes(data=True) if attr.get('type') == 'history']
    suggest_nodes = [n for n, attr in G.nodes(data=True) if attr.get('type') == 'suggestion']
    
    # 描画
    nx.draw_networkx_nodes(G, pos, nodelist=history_nodes, node_color='skyblue', node_size=1500, alpha=0.9)
    nx.draw_networkx_nodes(G, pos, nodelist=suggest_nodes, node_color='gold', node_size=2000, alpha=1.0)
    
    solid_edges = [(u, v) for u, v, attr in G.edges(data=True) if attr.get('style') != 'dotted']
    dotted_edges = [(u, v) for u, v, attr in G.edges(data=True) if attr.get('style') == 'dotted']
    
    nx.draw_networkx_edges(G, pos, edgelist=solid_edges, edge_color='gray', width=2)
    nx.draw_networkx_edges(G, pos, edgelist=dotted_edges, edge_color='orange', style='dashed', width=3, arrowsize=25)
    
    node_labels = {n: G.nodes[n]['label'] for n in G.nodes}
    nx.draw_networkx_labels(G, pos, labels=node_labels, font_family='MS Gothic', font_size=9)
    
    edge_labels = { (u,v): "Next" for u,v in dotted_edges }
    nx.draw_networkx_edge_labels(G, pos, edge_labels=edge_labels, font_family='MS Gothic', font_size=8, font_color='orange')
    
    plt.title("Knowledge Graph with AI Suggestions")
    plt.axis('off')
    plt.show()

# --- 6. 実行 ---
if __name__ == "__main__":
    try:
        json_file = get_latest_search_log()
        if json_file:
            print(f"Reading: {os.path.basename(json_file)}")
            with open(json_file, 'r', encoding='utf-8') as f:
                log_data = json.load(f)
            
            graph = create_trajectory_graph(log_data)
            draw_graph(graph)
        else:
            print("ログファイルが見つかりません。")
    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()