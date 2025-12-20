# P2HACKS2025 アピールシート

## プロダクト名・コンセプト

<img width="1920" height="1080" alt="kiranavi" src="https://github.com/user-attachments/assets/1db705a9-476d-4470-883b-b9f0966fccd7" />

## 対象ユーザ
<img width="1920" height="1080" alt="persona" src="https://github.com/user-attachments/assets/6912b019-5a95-4300-9048-034996c64b65" />


## 利用の流れ
1. **バックエンドサーバの起動**  
   - `cd pre-26/backend` で移動し、初回は `make setup`、以降は `make run` を実行してサーバーを起動します。  
2. **Chrome 拡張機能を読み込む**  
   - `chrome://extensions` でデベロッパーモードを有効にし、「パッケージ化されていない拡張機能を読み込む」から `/extension` ディレクトリを選択します。  
   - 履歴のアクセス権限が求められるので許可します。
3. **ダッシュボードを操作する**  
   - ツールバーの SparkNavi アイコンをクリックするとダッシュボードがタブで開きます。  
   - 「同期」を押すとブラウザの閲覧履歴が取得され、起動中のバックエンドに解析リクエストが送信されます。  
   - ノードを 2 つ選択すると、右側にAIによる提案や履歴が表示されます。バックエンドに接続できない場合はモックデータが自動表示されます。

## 推しポイント
- 閲覧サイトの相関を分析して可視化
- 次の検索に最適なキーワードを提案 & クリックするだけですぐ調べられる

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
- Plotlyを用いた閲覧履歴の関係性をネットワークグラフによって可視化
- Vibe Codingを実践しつつも、クリーンなコード設計の両立を目指したこと
- 目的とするプログラムの実装を明確することで、迷うことなく Vibe Codingの実践をおこなったこと
- 1 on 1 MTGを通じた密なコミュニケーションとったこと
- 会議中の議論をその場でFigmaに可視化することで、共通認識の形成を加速し、プロダクトに関するイメージの齟齬を未然に防いだこと
- 

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
