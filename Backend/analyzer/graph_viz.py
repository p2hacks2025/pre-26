import json
import os
import glob
from pathlib import Path
import networkx as nx
import matplotlib.pyplot as plt

# --- 日本語フォントの設定（Windows用） ---
# グラフの文字化けを防ぐため、MS Gothicなどを指定します
plt.rcParams['font.family'] = 'MS Gothic'

def get_latest_search_log():
    """ダウンロードフォルダから最新のsearch_log_*.jsonを取得"""
    home = str(Path.home())
    downloads_dir = os.path.join(home, "Downloads")
    search_pattern = os.path.join(downloads_dir, "search_log_*.json")
    
    list_of_files = glob.glob(search_pattern)
    if not list_of_files:
        return None
    return max(list_of_files, key=os.path.getctime)

def create_browse_graph(data):
    """ログデータからNetworkXのグラフを生成"""
    G = nx.DiGraph() # 有向グラフ（矢印あり）
    
    # データを時系列順に確実にする
    sorted_data = sorted(data, key=lambda x: x['timestamp'])
    
    prev_node = None
    
    for i, entry in enumerate(sorted_data):
        # ノードの識別子としてURLを使用（長いのでラベルはタイトルにする）
        current_url = entry['url']
        title = entry['title'][:15] + "..." # 長すぎるので省略
        search_word = entry.get('searchWord')
        
        # 1. 閲覧ページをノードとして追加
        G.add_node(current_url, label=title, type='page', color='skyblue')
        
        # 2. 直前のページから現在のページへ遷移エッジを追加（軌跡）
        if prev_node:
            G.add_edge(prev_node, current_url, relation='next', color='black')
            
        # 3. 検索ワードがある場合、検索ワードもノードにして繋ぐ
        if search_word:
            word_node = f"Search: {search_word}"
            G.add_node(word_node, label=search_word, type='keyword', color='orange')
            G.add_edge(word_node, current_url, relation='searched', color='red')
            
        prev_node = current_url
        
    return G

def draw_graph(G):
    """グラフを描画"""
    plt.figure(figsize=(12, 8))
    
    # ノードの配置決定（spring_layoutが一般的）
    pos = nx.spring_layout(G, k=0.8) # kを大きくするとノード間が広がる
    
    # ノードの色分け
    colors = [G.nodes[n].get('color', 'grey') for n in G.nodes]
    
    # ラベルの用意
    labels = {n: G.nodes[n].get('label', '') for n in G.nodes}
    
    # 描画
    nx.draw(G, pos, 
            with_labels=True, 
            labels=labels, 
            node_color=colors, 
            node_size=2000, 
            font_size=10,
            font_family='MS Gothic', # ここでもフォント指定
            edge_color='gray',
            arrowsize=20)
            
    plt.title("Browsing Trajectory & Search Words")
    plt.show()

# --- メイン実行 ---
if __name__ == "__main__":
    json_file = get_latest_search_log()
    
    if json_file:
        print(f"Reading: {os.path.basename(json_file)}")
        with open(json_file, 'r', encoding='utf-8') as f:
            log_data = json.load(f)
            
        # グラフ作成と描画
        graph = create_browse_graph(log_data)
        print(f"Nodes: {graph.number_of_nodes()}, Edges: {graph.number_of_edges()}")
        draw_graph(graph)
    else:
        print("ログファイルが見つかりません。拡張機能からJSONを保存してください。")