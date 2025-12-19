import json
import os
import glob
import sys
from pathlib import Path
import networkx as nx
import numpy as np
from sklearn.metrics.pairwise import cosine_similarity
from dotenv import load_dotenv

# --- Plotly ライブラリ ---
import plotly.graph_objects as go

# ローカルでベクトル化するためのライブラリ
from sentence_transformers import SentenceTransformer

# ★重要: Hugging Face公式クライアントを使用
from huggingface_hub import InferenceClient

# --- 1. 環境設定 ---
load_dotenv()

# --- 2. モデル設定 ---

# 【Embedding】ローカル実行
LOCAL_EMBED_MODEL_NAME = "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2"

# 【Generation】API実行 (Qwen2.5-7B)
GEN_MODEL_ID = "Qwen/Qwen2.5-7B-Instruct"

# --- 3. 関数定義 ---

def get_embeddings_local(texts):
    """ローカルAIでベクトル化"""
    if not texts: return []
    
    print(f"ローカルAI({LOCAL_EMBED_MODEL_NAME})でベクトル化中...")
    try:
        model = SentenceTransformer(LOCAL_EMBED_MODEL_NAME)
        embeddings = model.encode(texts)
        return embeddings
    except Exception as e:
        print(f"Local Embedding Error: {e}")
        return [[] for _ in texts]

def generate_next_steps(history_titles):
    """閲覧履歴から次のキーワードをAI提案 (InferenceClient使用)"""
    if not history_titles: return []

    context = ", ".join(history_titles[-3:])
    
    # プロンプト
    prompt = f"""<|im_start|>system
あなたはユーザーの関心を広げるアシスタントです。<|im_end|>
<|im_start|>user
ユーザーの閲覧履歴: "{context}"
これに基づき、次に検索すべき「関連するキーワード」を3つ提案してください。
条件: 日本語, カンマ区切り, 説明不要。
例: Python 非同期, イベントループ, 並列処理<|im_end|>
<|im_start|>assistant
"""
    
    token = os.getenv("HF_TOKEN")
    if not token:
        print("Error: .envに HF_TOKEN が設定されていません")
        return ["トークン未設定"]

    print(f"AI({GEN_MODEL_ID})が未来の可能性を計算中...")
    
    try:
        client = InferenceClient(token=token)
        
        response = client.chat.completions.create(
            model=GEN_MODEL_ID,
            messages=[{"role": "user", "content": prompt}],
            max_tokens=50,
            temperature=0.7
        )
        
        generated_text = response.choices[0].message.content.strip()
        suggestions = [s.strip() for s in generated_text.replace('\n', ',').split(',') if s.strip()]
        return suggestions[:3]

    except Exception as e:
        print(f"Generation Error: {e}")
        if "429" in str(e) or "410" in str(e) or "500" in str(e) or "503" in str(e):
            print("Qwenが応答しないため、軽量モデル(Phi-3.5)で再試行します...")
            try:
                fallback_model = "microsoft/Phi-3.5-mini-instruct"
                response = client.chat.completions.create(
                    model=fallback_model,
                    messages=[{"role": "user", "content": prompt}],
                    max_tokens=50
                )
                generated_text = response.choices[0].message.content.strip()
                suggestions = [s.strip() for s in generated_text.replace('\n', ',').split(',') if s.strip()]
                return suggestions[:3]
            except Exception as e2:
                print(f"Fallback Error: {e2}")

        return ["AI提案(混雑中)"]

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
    
    titles = [item['title'] for item in sorted_data]
    embeddings = get_embeddings_local(titles)
    
    prev_node = None
    last_node = None
    
    for i, entry in enumerate(sorted_data):
        current_url = entry['url']
        label = entry['title'][:15] + "..." if len(entry['title']) > 15 else entry['title']
        search_word = entry.get('searchWord')
        vector = embeddings[i] if i < len(embeddings) else None
        
        # ノード属性
        G.add_node(current_url, label=label, full_title=entry['title'], 
                   type='history', vector=vector)
        
        # エッジ属性
        if prev_node:
            edge_label = f"Search: {search_word}" if search_word else "Link"
            G.add_edge(prev_node, current_url, label=edge_label, style='solid')
            
        prev_node = current_url
        last_node = current_url

    # 未来ノード
    if last_node:
        suggestions = generate_next_steps(titles)
        print(f"AI提案キーワード: {suggestions}")
        
        suggestion_vecs = get_embeddings_local(suggestions)
        
        for i, word in enumerate(suggestions):
            sug_id = f"suggestion_{i}"
            vec = suggestion_vecs[i] if i < len(suggestion_vecs) else None
            
            G.add_node(sug_id, label=word, full_title=f"AI Suggestion: {word}", 
                       type='suggestion', vector=vec)
            
            G.add_edge(last_node, sug_id, label="Next?", style='dotted')
            
    return G

# --- 6. レイアウト・描画 (Plotly版) ---

def apply_semantic_layout(G):
    nodes_with_vec = [n for n in G.nodes if G.nodes[n].get('vector') is not None]
    
    valid_vectors = []
    valid_nodes = []
    for n in nodes_with_vec:
        v = G.nodes[n]['vector']
        if isinstance(v, (list, np.ndarray)) and len(v) > 0:
            valid_vectors.append(v)
            valid_nodes.append(n)
            
    # ベクトルがない場合は通常のSpring Layout
    if not valid_vectors:
        return nx.spring_layout(G, k=0.9, seed=42)

    try:
        sim_matrix = cosine_similarity(valid_vectors)
    except Exception as e:
        return nx.spring_layout(G, k=0.9, seed=42)
    
    layout_G = G.copy()
    threshold = 0.4
    
    # 類似度が高いノード間に引力を働かせるためのエッジを追加
    for i in range(len(valid_nodes)):
        for j in range(i + 1, len(valid_nodes)):
            sim = sim_matrix[i][j]
            if sim > threshold:
                u = valid_nodes[i]
                v = valid_nodes[j]
                layout_G.add_edge(u, v, weight=sim * 3)
    
    return nx.spring_layout(layout_G, weight='weight', k=0.7, seed=42)

def draw_graph(G):
    # レイアウト計算
    pos = apply_semantic_layout(G)
    
    # --- エッジの作成 ---
    edge_x_solid, edge_y_solid = [], []
    edge_x_dotted, edge_y_dotted = [], []
    edge_annotations = [] # エッジラベル用

    for u, v, data in G.edges(data=True):
        x0, y0 = pos[u]
        x1, y1 = pos[v]
        
        # 線種による振り分け
        if data.get('style') == 'dotted':
            edge_x_dotted.extend([x0, x1, None])
            edge_y_dotted.extend([y0, y1, None])
            color = 'orange'
        else:
            edge_x_solid.extend([x0, x1, None])
            edge_y_solid.extend([y0, y1, None])
            color = 'gray'

        # エッジラベル（中間地点に配置）
        label_text = data.get('label', '')
        if label_text:
            edge_annotations.append(
                dict(
                    x=(x0 + x1) / 2,
                    y=(y0 + y1) / 2,
                    xref="x", yref="y",
                    text=label_text,
                    showarrow=False,
                    font=dict(size=10, color=color),
                    bgcolor="rgba(255,255,255,0.7)"
                )
            )

    # 実線エッジのトレース
    edge_trace_solid = go.Scatter(
        x=edge_x_solid, y=edge_y_solid,
        line=dict(width=2, color='gray'),
        hoverinfo='none',
        mode='lines'
    )

    # 点線エッジのトレース
    edge_trace_dotted = go.Scatter(
        x=edge_x_dotted, y=edge_y_dotted,
        line=dict(width=3, color='orange', dash='dot'),
        hoverinfo='none',
        mode='lines'
    )

    # --- ノードの作成 ---
    node_x_hist, node_y_hist = [], []
    node_text_hist = []
    
    node_x_sug, node_y_sug = [], []
    node_text_sug = []

    for node in G.nodes():
        x, y = pos[node]
        attr = G.nodes[node]
        full_title = attr.get('full_title', node)
        label = attr.get('label', node)
        
        # ホバーテキスト作成
        hover_info = f"<b>{label}</b><br>{full_title}"

        if attr.get('type') == 'suggestion':
            node_x_sug.append(x)
            node_y_sug.append(y)
            node_text_sug.append(hover_info)
        else:
            node_x_hist.append(x)
            node_y_hist.append(y)
            node_text_hist.append(hover_info)

    # 履歴ノードのトレース
    node_trace_hist = go.Scatter(
        x=node_x_hist, y=node_y_hist,
        mode='markers+text',
        textposition="top center",
        hoverinfo='text',
        hovertext=node_text_hist,
        marker=dict(
            showscale=False,
            color='skyblue',
            size=20,
            line_width=2))

    # 提案ノードのトレース
    node_trace_sug = go.Scatter(
        x=node_x_sug, y=node_y_sug,
        mode='markers+text',
        textposition="top center",
        hoverinfo='text',
        hovertext=node_text_sug,
        marker=dict(
            showscale=False,
            color='gold',
            size=25,
            line_width=2))

    # --- グラフの統合 ---
    fig = go.Figure(data=[edge_trace_solid, edge_trace_dotted, node_trace_hist, node_trace_sug],
                    layout=go.Layout(
                        title='Knowledge Graph with AI Suggestions (Plotly)',
                        titlefont_size=16,
                        showlegend=False,
                        hovermode='closest',
                        margin=dict(b=20,l=5,r=5,t=40),
                        annotations=edge_annotations, # エッジラベルを追加
                        xaxis=dict(showgrid=False, zeroline=False, showticklabels=False),
                        yaxis=dict(showgrid=False, zeroline=False, showticklabels=False))
                    )
    
    print("グラフを描画します...")
    fig.show()

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