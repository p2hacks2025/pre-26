# P2HACKS2025 アピールシート

## プロダクト名
KiraNavi
<img width="1920" height="1080" alt="consept" src="https://github.com/user-attachments/assets/950eae12-bfea-403c-98a7-520749eddc0e" />


## コンセプト


## 対象ユーザ

## 利用の流れ
1. **バックエンドサーバの軌道**  
   - `cd pre-26/backend` で移動し、初回は `make setup`、以降は `make run` を実行してサーバーを起動します。  
2. **Chrome 拡張機能を読み込む**  
   - `chrome://extensions` でデベロッパーモードを有効にし、「パッケージ化されていない拡張機能を読み込む」から `/extension` ディレクトリを選択します。  
   - 履歴アクセス権限が求められるので許可します。
3. **ダッシュボードを操作する**  
   - ツールバーの SparkNavi アイコンをクリックするとダッシュボードがタブで開きます。  
   - 「同期」を押すとブラウザ履歴が取得され、起動中のバックエンドに解析リクエストが送信されます。  
   - ノードを 2 つ選択すると、右側にAIによる提案や履歴が表示されます。バックエンドに接続できない場合はモックデータが自動表示されます。

## 推しポイント
- 閲覧サイトの創刊を分析して可視化
- 検索に最適なキーワードを提案

## スクリーンショット(任意)
<img width="2845" height="1504" alt="image" src="https://github.com/user-attachments/assets/f7ac9f33-abeb-4ea5-a728-2b033c4c6f9d" />

## 開発体制

### 役割分担
<img width="1920" height="1080" alt="member" src="https://github.com/user-attachments/assets/2e3818b8-240d-47c0-9cf9-b97965fa7eed" />


### アイディア出しの工夫
- マインドマップを使ったテーマの発散
<img width="1920" height="1080" alt="p22025_mindmap" src="https://github.com/user-attachments/assets/83c0ac99-1d09-4566-9cd0-a24d6f7d53b1" />

- KJ法を利用したテーマの分析
<img width="1920" height="1080" alt="p22025_kj" src="https://github.com/user-attachments/assets/42e5d6b6-93f5-4ed4-9c28-560c0b255075" />



### 開発における工夫した点
- Plotlyを利用し、検索履歴をネットワークグラフとして表示したこと
- Vibe Codingを実践し、クリーンなコード設計を目指したこと
- 1 on 1 MTGの実施

## 開発技術

### 利用したプログラミング言語
- JavaScript
- Python
- HTML
- CSS

### 利用したフレームワーク・ライブラリ
- Plotly.js
- Plotly
- NetworkX
- FastAPI
- Pydantic
- Typing
- Math
- Logging
- Gemini API
- datetime
- uuid
- urllib
- json

### その他開発に使用したツール・サービス
- Git/GitHub
- Figma
- Canva
- Affinity
- Claude Code
- Gemini
- ChatGPT
