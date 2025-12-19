.PHONY: help setup install run dev clean test

# デフォルトターゲット
help:
	@echo "利用可能なコマンド:"
	@echo "  make setup    - 仮想環境を作成して依存関係をインストール"
	@echo "  make install  - 依存関係のみをインストール"
	@echo "  make run      - サーバーを起動"
	@echo "  make dev      - 開発モード（ホットリロード）でサーバーを起動"
	@echo "  make clean    - 仮想環境とキャッシュを削除"
	@echo "  make test     - テストを実行"

# 仮想環境の作成と依存関係のインストール
setup:
	@echo "仮想環境を作成中..."
	python3 -m venv .venv
	@echo "依存関係をインストール中..."
	.venv/bin/pip install --upgrade pip
	.venv/bin/pip install -r requirements.txt
	@echo ""
	@echo "セットアップ完了！"
	@echo "サーバーを起動するには: make dev"

# 依存関係のみをインストール
install:
	.venv/bin/pip install -r requirements.txt

# 本番モードでサーバーを起動
run:
	.venv/bin/uvicorn app.main:app --host 0.0.0.0 --port 8080

# 開発モード（ホットリロード）でサーバーを起動
dev:
	@echo "開発サーバーを起動中..."
	@echo "API: http://localhost:8080"
	@echo "Docs: http://localhost:8080/docs"
	@echo ""
	.venv/bin/uvicorn app.main:app --reload --host 0.0.0.0 --port 8080

# 仮想環境とキャッシュを削除
clean:
	@echo "クリーンアップ中..."
	rm -rf .venv
	rm -rf __pycache__
	find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
	find . -type f -name "*.pyc" -delete
	@echo "クリーンアップ完了"

# テストを実行（pytest がある場合）
test:
	.venv/bin/pytest -v
