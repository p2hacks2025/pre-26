import json
import os
import glob
from pathlib import Path

def get_latest_search_log():
    """
    ダウンロードフォルダから 'search_log_*.json' のパターンに一致する
    最新のファイルを見つけて読み込む関数
    """
    
    # 1. ダウンロードフォルダのパスを取得 (Windows/Mac/Linux対応)
    home = str(Path.home())
    
    # OSによってダウンロードフォルダの場所は概ねここですが、
    # 環境によって異なる場合はここを直接指定してください。
    downloads_dir = os.path.join(home, "Downloads")
    
    # 2. ファイルパターンの定義 (popup.jsで決めた命名規則)
    search_pattern = os.path.join(downloads_dir, "search_log_*.json")
    
    # 3. ファイルリストの取得
    list_of_files = glob.glob(search_pattern)
    
    if not list_of_files:
        print("エラー: ログファイルが見つかりません。")
        print(f"探索パス: {search_pattern}")
        return None

    # 4. 更新日時が最も新しいファイルを取得
    latest_file = max(list_of_files, key=os.path.getctime)
    
    print(f"最新のログファイルを検出しました: {os.path.basename(latest_file)}")
    
    # 5. JSON読み込み
    try:
        with open(latest_file, 'r', encoding='utf-8') as f:
            data = json.load(f)
            return data
    except Exception as e:
        print(f"読み込みエラー: {e}")
        return None

# --- メイン処理のプロトタイプ ---

if __name__ == "__main__":
    print("--- 自動読み込み開始 ---")
    
    # 自動でデータを取得
    log_data = get_latest_search_log()
    
    if log_data:
        print(f"\nデータ取得成功！ 全 {len(log_data)} 件")
        print("-" * 30)
        
        # サンプル: 中身を少し表示
        for i, entry in enumerate(log_data[:5]): # 最初の5件だけ表示
            ts = entry.get('timestamp', '')
            title = entry.get('title', 'No Title')
            word = entry.get('searchWord')
            
            print(f"[{i+1}] {ts}")
            print(f"   Title: {title}")
            if word:
                print(f"   ★検索ワード: {word}")
            print("-" * 30)
            
        print("\n...以降、NetworkXなどの処理へ続く...")
    else:
        print("処理を中断します。")