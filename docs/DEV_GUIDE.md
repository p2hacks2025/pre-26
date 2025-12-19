# 開発ガイド

## 前提条件

- Python 3.10+
- Node.js (Plotlyダウンロード用)
- Chrome ブラウザ

## セットアップ

### 1. Plotly.jsのダウンロード

```bash
cd pre-26/extension/vendor
curl -O https://cdn.plot.ly/plotly-2.27.0.min.js
mv plotly-2.27.0.min.js plotly.min.js
```

### 2. バックエンドの起動

```bash
cd pre-26/backend

# 仮想環境作成
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate

# 依存関係インストール
pip install -r requirements.txt

# サーバー起動
uvicorn app.main:app --host 127.0.0.1 --port 8080 --reload
```

APIドキュメント: http://127.0.0.1:8080/docs

### 3. Chrome拡張のロード

1. Chromeで `chrome://extensions/` を開く
2. 右上の「デベロッパーモード」をON
3. 「パッケージ化されていない拡張機能を読み込む」をクリック
4. `pre-26/extension` フォルダを選択

### 4. 動作確認

1. Chromeツールバーの拡張アイコンをクリック
2. 「History Visualizer」をクリック
3. ダッシュボードが新規タブで開く
4. 「同期」ボタンをクリック

## ディレクトリ構成

```
pre-26/
├── backend/
│   ├── app/
│   │   ├── api/routes.py      # APIエンドポイント
│   │   ├── schemas.py         # Pydanticモデル
│   │   ├── services/          # ビジネスロジック（P1で実装）
│   │   └── main.py            # FastAPIアプリ
│   └── requirements.txt
├── extension/
│   ├── manifest.json
│   ├── background/
│   │   └── service_worker.js  # Action→ダッシュボード起動
│   ├── ui/
│   │   ├── dashboard.html
│   │   ├── dashboard.js       # 履歴取得・API連携・Plotly描画
│   │   ├── dashboard.css
│   │   └── mock_response.json # バックエンド不在時のモック
│   ├── vendor/
│   │   └── plotly.min.js      # 要ダウンロード
│   └── assets/
│       └── bg_night_sky.jpg   # 背景画像（要追加）
└── docs/
    └── DEV_GUIDE.md
```

## トラブルシューティング

### バックエンドに接続できない

- バックエンドが `http://127.0.0.1:8080` で起動しているか確認
- モックデータで動作確認する場合は、そのまま「同期」を押すとモックが表示される

### 拡張が動かない

- `chrome://extensions/` でエラーが出ていないか確認
- 「詳細」→「エラー」を確認
- `plotly.min.js` が `vendor/` に存在するか確認

### 履歴が取得できない

- Chromeの閲覧履歴が空の可能性
- 拡張に `history` 権限が付与されているか確認
