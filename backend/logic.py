import os
import json
import networkx as nx
import numpy as np
from sklearn.metrics.pairwise import cosine_similarity
from dotenv import load_dotenv
from sentence_transformers import SentenceTransformer
from huggingface_hub import InferenceClient
import plotly.graph_objects as go

# 環境変数の読み込み
load_dotenv()

# モデル設定
LOCAL_EMBED_MODEL_NAME = "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2"
GEN_MODEL_ID = "Qwen/Qwen2.5-7B-Instruct"

# モデルの初期化
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
        return []

def generate_next_steps(history_titles):
    """AIによる次の一手提案"""
    if not history_titles: return []
    
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
        # トークンがない場合はダミーを返す（エラーにしない）
        return ["AI提案(トークンなし)"]

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
        return ["AI提案エラー"]

def create_graph_data(log_data):
    """
    ログデータのリストを受け取り、PlotlyのFigure(JSON互換辞書)を返す
    """
    # デバッグ: データが来ているか確認
    print(f"[Logic] Processing {len(log_data)} logs...")

    if not log_data:
        print("[Logic] No data provided.")
        return None

    try:
        # 1. グラフ構築
        G = nx.DiGraph()
        sorted_data = sorted(log_data, key=lambda x: x.get('timestamp', ''))
        
        titles = [item.get('title', 'No Title') for item in sorted_data]
        embeddings = get_embeddings_local(titles)
        
        prev_node = None
        last_node = None
        start_node = sorted_data[0]['url'] if sorted_data else None

        # 履歴ノード
        for i, entry in enumerate(sorted_data):
            current_url = entry['url']
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

        # AI提案ノード
        if last_node:
            suggestions = generate_next_steps(titles)
            suggestion_vecs = get_embeddings_local(suggestions)
            
            for i, word in enumerate(suggestions):
                sug_id = f"suggestion_{i}"
                vec = suggestion_vecs[i] if len(suggestion_vecs) > i else None
                G.add_node(sug_id, label=word, full_title=f"AI Suggestion: {word}", type='suggestion', vector=vec)
                G.add_edge(last_node, sug_id, label="Next?", style='dotted')

        # 2. パス計算
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
        pos = nx.spring_layout(G, k=0.7, seed=42) # 簡易版レイアウト（エラー回避優先）

        # 4. Plotly Traces生成
        edge_x, edge_y = [], []
        dedge_x, dedge_y = [], []
        edge_annotations = []
        
        node_x_hist, node_y_hist, text_hist, custom_hist = [], [], [], []
        node_x_sug, node_y_sug, text_sug, custom_sug = [], [], [], []

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

        for node in G.nodes():
            if node not in pos: continue
            x, y = pos[node]
            attr = G.nodes[node]
            info = f"<b>{attr.get('label')}</b><br>{attr.get('full_title')}"
            path = path_texts.get(node, "")

            if attr.get('type') == 'suggestion':
                node_x_sug.append(x); node_y_sug.append(y)
                text_sug.append(info); custom_sug.append(path)
            else:
                node_x_hist.append(x); node_y_hist.append(y)
                text_hist.append(info); custom_hist.append(path)

        # Figure構築
        fig = go.Figure()
        
        fig.add_trace(go.Scatter(x=edge_x, y=edge_y, mode='lines', line=dict(color='gray', width=2), hoverinfo='none'))
        fig.add_trace(go.Scatter(x=dedge_x, y=dedge_y, mode='lines', line=dict(color='orange', width=3, dash='dot'), hoverinfo='none'))
        
        fig.add_trace(go.Scatter(
            x=node_x_hist, y=node_y_hist, mode='markers+text', textposition="top center",
            hoverinfo='text', hovertext=text_hist, customdata=custom_hist,
            marker=dict(size=20, color='skyblue', line_width=2)
        ))
        
        fig.add_trace(go.Scatter(
            x=node_x_sug, y=node_y_sug, mode='markers+text', textposition="top center",
            hoverinfo='text', hovertext=text_sug, customdata=custom_sug,
            marker=dict(size=25, color='gold', line_width=2)
        ))

        fig.update_layout(
            title='Browsing History Graph', showlegend=False, hovermode='closest',
            margin=dict(b=20,l=5,r=5,t=40), annotations=edge_annotations,
            xaxis=dict(showgrid=False, zeroline=False, showticklabels=False),
            yaxis=dict(showgrid=False, zeroline=False, showticklabels=False)
        )
        
        print("[Logic] Graph created successfully.")
        # ★重要: ここでJSONを返さないと、呼び出し元にはNoneが返ります
        return json.loads(fig.to_json())

    except Exception as e:
        print(f"[Logic] Error: {e}")
        import traceback
        traceback.print_exc()
        return None