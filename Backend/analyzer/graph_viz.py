import json
import os
import glob
import sys
import webbrowser
from pathlib import Path
import networkx as nx
import numpy as np
from sklearn.metrics.pairwise import cosine_similarity
from dotenv import load_dotenv

# Plotly ライブラリ
import plotly.graph_objects as go
import plotly.io as pio

from sentence_transformers import SentenceTransformer
from huggingface_hub import InferenceClient

# --- 1. 環境設定 ---
load_dotenv()

# --- 2. モデル設定 ---
LOCAL_EMBED_MODEL_NAME = "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2"
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
    """閲覧履歴から次のキーワードをAI提案"""
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
    
    # 始点ノードを特定するためにリストの先頭を記録
    start_node_id = sorted_data[0]['url'] if sorted_data else None

    for i, entry in enumerate(sorted_data):
        current_url = entry['url']
        label = entry['title'][:15] + "..." if len(entry['title']) > 15 else entry['title']
        search_word = entry.get('searchWord')
        vector = embeddings[i] if i < len(embeddings) else None
        
        G.add_node(current_url, label=label, full_title=entry['title'], 
                   type='history', vector=vector)
        
        if prev_node:
            edge_label = f"Search: {search_word}" if search_word else "Link"
            G.add_edge(prev_node, current_url, label=edge_label, style='solid')
            
        prev_node = current_url
        last_node = current_url

    # 未来ノード
    if last_node:
        suggestions = generate_next_steps(titles)
        suggestion_vecs = get_embeddings_local(suggestions)
        
        for i, word in enumerate(suggestions):
            sug_id = f"suggestion_{i}"
            vec = suggestion_vecs[i] if i < len(suggestion_vecs) else None
            
            G.add_node(sug_id, label=word, full_title=f"AI Suggestion: {word}", 
                       type='suggestion', vector=vec)
            
            G.add_edge(last_node, sug_id, label="Next?", style='dotted')

    # グラフオブジェクトに始点情報を付与しておく
    G.graph['start_node'] = start_node_id
    return G

# --- 6. パス計算とレイアウト ---

def calculate_paths(G):
    """始点から各ノードまでのパスを計算し、フォーマット済み文字列の辞書を返す"""
    start_node = G.graph.get('start_node')
    path_texts = {}
    
    if not start_node or start_node not in G:
        return path_texts

    for node in G.nodes():
        try:
            # 始点から現在のノードまでの最短パス（ノードIDのリスト）を取得
            path = nx.shortest_path(G, source=start_node, target=node)
            
            # パスを読みやすいテキストに変換
            steps = []
            for idx, p_node in enumerate(path):
                title = G.nodes[p_node].get('label', 'Unknown')
                steps.append(f"{idx + 1}. {title}")
            
            # ポップアップ表示用のテキスト
            path_texts[node] = "\\n".join(steps) # JSのalert用に改行文字をエスケープ
            
        except nx.NetworkXNoPath:
            path_texts[node] = "始点からの経路が見つかりません"
        except Exception as e:
            path_texts[node] = f"Error: {e}"
            
    return path_texts

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
    pos = apply_semantic_layout(G)
    
    # パス情報の事前計算
    path_info_map = calculate_paths(G)
    
    # --- エッジの作成 ---
    edge_x_solid, edge_y_solid = [], []
    edge_x_dotted, edge_y_dotted = [], []
    edge_annotations = []

    for u, v, data in G.edges(data=True):
        x0, y0 = pos[u]
        x1, y1 = pos[v]
        
        if data.get('style') == 'dotted':
            edge_x_dotted.extend([x0, x1, None])
            edge_y_dotted.extend([y0, y1, None])
            color = 'orange'
        else:
            edge_x_solid.extend([x0, x1, None])
            edge_y_solid.extend([y0, y1, None])
            color = 'gray'

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

    edge_trace_solid = go.Scatter(
        x=edge_x_solid, y=edge_y_solid,
        line=dict(width=2, color='gray'),
        hoverinfo='none',
        mode='lines'
    )

    edge_trace_dotted = go.Scatter(
        x=edge_x_dotted, y=edge_y_dotted,
        line=dict(width=3, color='orange', dash='dot'),
        hoverinfo='none',
        mode='lines'
    )

    # --- ノードの作成 ---
    # 履歴ノード
    node_x_hist, node_y_hist = [], []
    node_text_hist = []
    node_custom_hist = [] # パス情報を格納
    
    # 提案ノード
    node_x_sug, node_y_sug = [], []
    node_text_sug = []
    node_custom_sug = [] # パス情報を格納

    for node in G.nodes():
        x, y = pos[node]
        attr = G.nodes[node]
        full_title = attr.get('full_title', node)
        label = attr.get('label', node)
        
        hover_info = f"<b>{label}</b><br>{full_title}"
        path_info = path_info_map.get(node, "経路情報なし") # 計算したパスを取得

        if attr.get('type') == 'suggestion':
            node_x_sug.append(x)
            node_y_sug.append(y)
            node_text_sug.append(hover_info)
            node_custom_sug.append(path_info)
        else:
            node_x_hist.append(x)
            node_y_hist.append(y)
            node_text_hist.append(hover_info)
            node_custom_hist.append(path_info)

    node_trace_hist = go.Scatter(
        x=node_x_hist, y=node_y_hist,
        mode='markers+text',
        textposition="top center",
        hoverinfo='text',
        hovertext=node_text_hist,
        customdata=node_custom_hist, # ★ここにパス情報を埋め込む
        marker=dict(size=20, color='skyblue', line_width=2)
    )

    node_trace_sug = go.Scatter(
        x=node_x_sug, y=node_y_sug,
        mode='markers+text',
        textposition="top center",
        hoverinfo='text',
        hovertext=node_text_sug,
        customdata=node_custom_sug, # ★ここにパス情報を埋め込む
        marker=dict(size=25, color='gold', line_width=2)
    )

    # --- グラフ構成 ---
    fig = go.Figure(
        data=[edge_trace_solid, edge_trace_dotted, node_trace_hist, node_trace_sug],
        layout=go.Layout(
            title='Browsing History Graph (Click Node to see Path)',
            showlegend=False,
            hovermode='closest',
            margin=dict(b=20,l=5,r=5,t=40),
            annotations=edge_annotations,
            xaxis=dict(showgrid=False, zeroline=False, showticklabels=False),
            yaxis=dict(showgrid=False, zeroline=False, showticklabels=False)
        )
    )

    # --- HTMLとして保存し、JSイベントを注入 ---
    # グラフのDIV IDを取得（HTML埋め込み時に必要）
    plot_div_id = "my_graph_div"
    
    # PlotlyのHTML生成（divタグのみ）
    plot_html = pio.to_html(fig, full_html=False, include_plotlyjs='cdn', div_id=plot_div_id)

    # カスタムHTMLテンプレート
    html_content = f"""
    <html>
    <head>
        <title>Knowledge Graph</title>
        <meta charset="utf-8">
        <style>
            body {{ font-family: sans-serif; margin: 0; padding: 20px; }}
            #info {{ margin-bottom: 10px; color: #555; }}
        </style>
    </head>
    <body>
        <div id="info">ノードをクリックすると、始点からの道のりが表示されます。</div>
        {plot_html}
        
        <script>
            // グラフ要素を取得
            var myPlot = document.getElementById('{plot_div_id}');
            
            // クリックイベントのリスナーを追加
            myPlot.on('plotly_click', function(data){{
                var pts = '';
                // クリックされたポイントのcustomdata（パス情報）を取得
                if (data.points.length > 0) {{
                    var pathText = data.points[0].customdata;
                    if (pathText) {{
                        // alertでポップアップ表示（改行文字\nはPython側で処理済み）
                        alert("【始点からの道のり】\\n\\n" + pathText);
                    }}
                }}
            }});
        </script>
    </body>
    </html>
    """

    # ファイルに書き出し
    output_file = "graph_with_path.html"
    with open(output_file, "w", encoding="utf-8") as f:
        f.write(html_content)

    print(f"グラフを保存しました: {output_file}")
    
    # ブラウザで開く
    webbrowser.open('file://' + os.path.realpath(output_file))

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