import os
import json
import networkx as nx
import numpy as np
from sklearn.metrics.pairwise import cosine_similarity
from dotenv import load_dotenv
from sentence_transformers import SentenceTransformer
from huggingface_hub import InferenceClient
import plotly.graph_objects as go

# 環境変数の読み込み (.envファイルが backend/ ディレクトリにあることを想定)
load_dotenv()

# モデル設定
LOCAL_EMBED_MODEL_NAME = "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2"
GEN_MODEL_ID = "Qwen/Qwen2.5-7B-Instruct"

# モデルの初期化（起動時に一度だけロード）
print("Loading Embedding Model...")
try:
    embed_model = SentenceTransformer(LOCAL_EMBED_MODEL_NAME)
    print("Embedding Model Loaded.")
except Exception as e:
    print(f"Failed to load embedding model: {e}")
    embed_model = None

def get_embeddings_local(texts):
    """テキストリストをベクトル化"""
    if not texts or embed_model is None:
        return []
    try:
        return embed_model.encode(texts)
    except Exception as e:
        print(f"Embedding Error: {e}")
        return [[] for _ in texts]

def generate_next_steps(history_titles):
    """閲覧履歴から次のキーワードをAI提案"""
    if not history_titles: return []
    
    # 直近3件を文脈とする
    context = ", ".join(history_titles[-3:])
    
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
        print("Warning: HF_TOKEN is not set.")
        return ["トークン未設定"]

    try:
        client = InferenceClient(token=token)
        response = client.chat.completions.create(
            model=GEN_MODEL_ID,
            messages=[{"role": "user", "content": prompt}],
            max_tokens=50,
            temperature=0.7
        )
        generated_text = response.choices[0].message.content.strip()
        # カンマまたは改行で区切ってリスト化
        suggestions = [s.strip() for s in generated_text.replace('\n', ',').split(',') if s.strip()]
        return suggestions[:3]
    except Exception as e:
        print(f"Generation Error: {e}")
        return ["AI提案エラー"]

def create_graph_data(log_data):
    """
    ログデータのリストを受け取り、PlotlyのFigure(JSON互換辞書)を返す
    """
    if not log_data:
        return None

    # 1. グラフ構築
    G = nx.DiGraph()
    # タイムスタンプ順にソート
    sorted_data = sorted(log_data, key=lambda x: x.get('timestamp', ''))
    
    titles = [item.get('title', 'No Title') for item in sorted_data]
    embeddings = get_embeddings_local(titles)
    
    prev_node = None
    last_node = None
    start_node = sorted_data[0]['url'] if sorted_data else None

    # 履歴ノードの追加
    for i, entry in enumerate(sorted_data):
        current_url = entry['url']
        # ラベル用にタイトルを短縮
        full_title = entry.get('title', 'No Title')
        label = full_title[:15] + "..." if len(full_title) > 15 else full_title
        search_word = entry.get('searchWord')
        
        vector = embeddings[i] if len(embeddings) > i else None
        
        G.add_node(current_url, label=label, full_title=full_title, type='history', vector=vector)
        
        if prev_node:
            edge_label = f"Search: {search_word}" if search_word else "Link"
            G.add_edge(prev_node, current_url, label=edge_label, style='solid')
            
        prev_node = current_url
        last_node = current_url

    # 未来ノード（AI提案）の追加
    if last_node:
        suggestions = generate_next_steps(titles)
        suggestion_vecs = get_embeddings_local(suggestions)
        
        for i, word in enumerate(suggestions):
            sug_id = f"suggestion_{i}"
            vec = suggestion_vecs[i] if len(suggestion_vecs) > i else None
            
            G.add_node(sug_id, label=word, full_title=f"AI Suggestion: {word}", type='suggestion', vector=vec)
            G.add_edge(last_node, sug_id, label="Next?", style='dotted')

    # 2. パス計算 (始点からの道のり)
    path_texts = {}
    if start_node and start_node in G:
        for node in G.nodes():
            try:
                path = nx.shortest_path(G, source=start_node, target=node)
                steps = [f"{idx+1}. {G.nodes[p].get('label','?')}" for idx, p in enumerate(path)]
                path_texts[node] = "\n".join(steps)
            except:
                path_texts[node] = "経路なし"

    # 3. レイアウト計算
    # ベクトルがあるノードのみで類似度計算を行い、親和性レイアウトを作る簡易実装
    try:
        # ベクトルを持つノードを抽出
        nodes_with_vec = [n for n in G.nodes if G.nodes[n].get('vector') is not None]
        valid_vectors = [G.nodes[n]['vector'] for n in nodes_with_vec]
        
        if len(valid_vectors) > 1:
            sim_matrix = cosine_similarity(valid_vectors)
            layout_G = G.copy()
            threshold = 0.4
            for i in range(len(nodes_with_vec)):
                for j in range(i + 1, len(nodes_with_vec)):
                    sim = sim_matrix[i][j]
                    if sim > threshold:
                        u, v = nodes_with_vec[i], nodes_with_vec[j]
                        layout_G.add_edge(u, v, weight=sim * 3)
            pos = nx.spring_layout(layout_G, weight='weight', k=0.7, seed=42)
        else:
            pos = nx.spring_layout(G, k=0.7, seed=42)
    except Exception as e:
        print(f"Layout warning: {e}")
        pos = nx.spring_layout(G, k=0.7, seed=42)

    # 4. Plotly Traces作成
    edge_x, edge_y = [], []     # 実線
    dedge_x, dedge_y = [], []   # 点線
    edge_annotations = []
    
    node_x_hist, node_y_hist, text_hist, custom_hist = [], [], [], []
    node_x_sug, node_y_sug, text_sug, custom_sug = [], [], [], []

    # エッジの生成
    for u, v, d in G.edges(data=True):
        if u not in pos or v not in pos: continue
        x0, y0 = pos[u]
        x1, y1 = pos[v]
        
        if d.get('style') == 'dotted':
            dedge_x.extend([x0, x1, None])
            dedge_y.extend([y0, y1, None])
        else:
            edge_x.extend([x0, x1, None])
            edge_y.extend([y0, y1, None])
        
        if d.get('label'):
            edge_annotations.append(dict(
                x=(x0+x1)/2, y=(y0+y1)/2, xref="x", yref="y", text=d['label'], showarrow=False,
                font=dict(size=10, color="gray"), bgcolor="rgba(255,255,255,0.7)"
            ))

    # ノードの生成
    for node in G.nodes():
        if node not in pos: continue
        x, y = pos[node]
        attr = G.nodes[node]
        
        # ホバー情報
        info = f"<b>{attr.get('label')}</b><br>{attr.get('full_title')}"
        # クリック時のパス情報
        path = path_texts.get(node, "")

        if attr.get('type') == 'suggestion':
            node_x_sug