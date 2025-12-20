"""アプリケーション設定"""
from pydantic_settings import BaseSettings
from typing import Optional


class Settings(BaseSettings):
    """アプリケーション設定

    環境変数または.envファイルから読み込む
    """
    APP_NAME: str = "History Visualizer API"
    DEBUG: bool = True

    # Gemini API設定
    GEMINI_API_KEY: Optional[str] = None

    class Config:
        # プロジェクトルートとbackend直下の両方から環境変数を読み込む
        env_file = (".env", "../.env")
        env_file_encoding = "utf-8"


settings = Settings()
