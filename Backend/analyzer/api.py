import requests
import time
import os

# 1. Hugging Faceで取得したトークンを設定してください
HF_TOKEN = "hf_xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx" 

# モデルのエンドポイント (MiniLM-L12-v2)
API_URL = "https://api-inference.huggingface.co/models/sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2"
headers = {"Authorization": f"Bearer {HF_TOKEN}"}

def query_embedding(texts):
    """
    テキストのリストを受け取り、ベクトル(List[float])のリストを返す
    """
    payload = {
        "inputs": texts,
        "options": {"wait_for_model": True} # モデルがスリープしていても起動を待つ設定
    }
    
    try:
        response = requests.post(API_URL, headers=headers, json=payload)
        response.raise_for_status() # エラーなら例外を投げる
        return response.json()
    except Exception as e:
        print(f"Embedding API Error: {e}")
        # レート制限などで失敗した場合の空配列を返すなど、適宜ハンドリング
        return []

# --- 使用イメージ (graph_viz.py 等に組み込む際) ---
if __name__ == "__main__":
    # テストデータ
    sample_titles = [
        "Pythonの非同期処理入門",
        "美味しいカレーの作り方",
        "asyncioの使い方 - Qiita"
    ]
    
    print("ベクトル化中...")
    embeddings = query_embedding(sample_titles)
    
    # 戻り値の確認 (次元数など)
    if embeddings and isinstance(embeddings, list):
        print(f"ベクトル取得成功: {len(embeddings)}件")
        if len(embeddings) > 0:
            print(f"次元数: {len(embeddings[0])}") # 通常 384次元
    else:
        print("ベクトル取得失敗")