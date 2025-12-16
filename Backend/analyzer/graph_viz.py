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

# ローカルでベクトル化するためのライブラリ
from sentence_transformers import SentenceTransformer

# --- 1. 環境設定 ---
load_dotenv()

# 日本語フォント設定
plt.rcParams['font.family'] = 'MS Gothic'

# --- 2. モデル設定 ---

# 【Embedding】ローカル実行用モデル
# APIエラー(410 Gone)を避けるため、ローカルで動かします
LOCAL_EMBED_MODEL_NAME = "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2"

GEN_API_URL = "https://router.huggingface.co/hf-inference/models/Qwen/Qwen2.5-7B-Instruct"

# --- 3. 関数定義 ---

def get_hf_headers():
    token = os.getenv("HF_TOKEN")
    if not token:
        print("Warning: HF_TOKEN not found. 生成AI機能は使えません。")
        return {}
    return {"Authorization": f"Bearer {token}"}

def get_embeddings_local(texts):
    """ローカルのSentenceTransformerでベクトル化"""
    if not texts: return []
    
    print(f"ローカルAI({LOCAL_EMBED_MODEL_NAME})でベクトル化中...")
    try:
        # 初回のみモデルダウンロード(約500MB)が発生します
        model = SentenceTransformer(LOCAL_EMBED_MODEL_NAME)
        embeddings = model.encode(texts)
        return embeddings
    except Exception as e:
        print(f"Local Embedding Error: {e}")
        return [[] for _ in texts]

def generate_next_steps(history_titles):
    """閲覧履歴から次のキーワードをAI提案"""
    if not history_titles: return []

    context = ", ".join(history_titles[-3:])
    
    # Qwen/Phi向けのプロンプト
    prompt = f"""<|im_start|>system
あなたはユーザーの関心を広げるアシスタントです。<|im_end|>
<|im_start|>user
ユーザーの閲覧履歴: "{context}"
これに基づき、次に検索すべき「関連するキーワード」を3つ提案してください。
条件: 日本語, カンマ区切り, 説明不要。
例: Python 非同期, イベントループ, 並列処理<|im_end|>
<|im_start|>assistant
"""
    
    headers = get_hf_headers()
    if not headers: return ["トークン未設定"]

    payload = {
        "inputs": prompt,
        "parameters": {
            "max_new_tokens": 50,
            "return_full_text": False,
            "temperature": 0.7
        }
    }
    
    print("AI(Qwen2.5)が未来の可能性を計算中...")
    try:
        response = requests.post(GEN_API_URL, headers=headers, json=payload)
        response.raise_for_status()
        result = response.json()
        
        # レスポンス解析
        generated_text = result[0]['generated_text'].strip()
        suggestions = [s.strip() for s in generated_text.replace('\n', ',').split(',') if s.strip()]
        return suggestions[:3]
    except Exception as e:
        print(f"Generation API Warning: {e}")
        # APIが混んでたりモデルが無い場合のエラーハンドリング
        return ["AI提案(API混雑)"]

# --- 4. ログ読み込み ---

def get_latest_search_log():
    home = str(Path.home())
    downloads_dir = os.path.join(home, "Downloads")
    search_pattern = os.path.join(downloads_dir, "search_log_*.json")
    list_of_files = glob.glob(search_pattern)
    return max(list_of_files, key=os.path.getctime) if list_of_files else None

# --- 5. グラフ生成 ---

def create_trajectory_graph(data):
    G = nx.DiGraph()
    sorted_data = sorted(data, key=lambda x: x['timestamp'])
    
    # 履歴をローカルAIでベクトル化
    titles = [item['title'] for item in sorted_data]
    embeddings = get_embeddings_local(titles)
    
    prev_node = None
    last_node = None
    
    for i, entry in enumerate(sorted_data):
        current_url = entry['url']
        label = entry['title'][:10] + "..." if len(entry['title']) > 10 else entry['title']
        search_word = entry.get('searchWord')
        vector = embeddings[i] if i < len(embeddings) else None
        
        G.add_node(current_url, label=label, full_title=entry['title'], 
                   type='history', vector=vector)
        
        if prev_node:
            G.add_edge(prev_node, current_url, label=search_word or "", style='solid')
            
        prev_node = current_url
        last_node = current_url

    # 未来ノード (APIで提案)
    if last_node:
        suggestions = generate_next_steps(titles)
        print(f"AI提案キーワード: {suggestions}")
        
        # 提案ワードもローカルでベクトル化
        suggestion_vecs = get_embeddings_local(suggestions)
        
        for i, word in enumerate(suggestions):
            sug_id = f"suggestion_{i}"
            vec = suggestion_vecs[i] if i < len(suggestion_vecs) else None
            
            G.add_node(sug_id, label=word, full_title=word, 
                       type='suggestion', vector=vec)
            
            G.add_edge(last_node, sug_id, label="Next?", style='dotted')
            
    return G

# --- 6. レイアウト・描画 ---

def apply_semantic_layout(G):
    nodes_with_vec = [n for n in G.nodes if G.nodes[n].get('vector') is not None]
    
    valid_vectors = []
    valid_nodes = []
    for n in nodes_with_vec:
        v = G.nodes[n]['vector']
        if isinstance(v, (list, np.ndarray)) and len(v) > 0:
            valid_vectors.append(v)
            valid_nodes.append(n)
            
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
    
    # ノードタイプ別の描画
    history_nodes = [n for n, attr in G.nodes(data=True) if attr.get('type') == 'history']
    suggest_nodes = [n for n, attr in G.nodes(data=True) if attr.get('type') == 'suggestion']
    
    nx.draw_networkx_nodes(G, pos, nodelist=history_nodes, node_color='skyblue', node_size=1500, alpha=0.9)
    nx.draw_networkx_nodes(G, pos, nodelist=suggest_nodes, node_color='gold', node_size=2000, alpha=1.0)
    
    # エッジ描画
    solid_edges = [(u, v) for u, v, attr in G.edges(data=True) if attr.get('style') != 'dotted']
    dotted_edges = [(u, v) for u, v, attr in G.edges(data=True) if attr.get('style') == 'dotted']
    
    nx.draw_networkx_edges(G, pos, edgelist=solid_edges, edge_color='gray', width=2)
    nx.draw_networkx_edges(G, pos, edgelist=dotted_edges, edge_color='orange', style='dashed', width=3, arrowsize=25)
    
    # ラベル描画
    node_labels = {n: G.nodes[n]['label'] for n in G.nodes}
    nx.draw_networkx_labels(G, pos, labels=node_labels, font_family='MS Gothic', font_size=9)
    
    edge_labels = { (u,v): "Next" for u,v in dotted_edges }
    nx.draw_networkx_edge_labels(G, pos, edge_labels=edge_labels, font_family='MS Gothic', font_size=8, font_color='orange')
    
    plt.title("Knowledge Graph with AI Suggestions (Qwen2.5)")
    plt.axis('off')
    plt.show()

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