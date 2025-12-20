"""Gemini APIクライアント"""

from __future__ import annotations

import logging
from typing import Optional

import google.generativeai as genai

from app.config import settings

logger = logging.getLogger(__name__)


class GeminiClient:
    """Gemini APIとの通信を担当する薄いクライアント."""

    def __init__(
        self,
        api_key: Optional[str] = None,
        primary_model: str = "gemini-2.5-flash-lite",
        fallback_model: str = "gemini-2.0-flash-exp",
    ) -> None:
        self.api_key = api_key or settings.GEMINI_API_KEY
        self.primary_model = primary_model
        self.fallback_model = fallback_model
        self._model = None

        if self.api_key:
            try:
                genai.configure(api_key=self.api_key)
                self._model = genai.GenerativeModel(self.primary_model)
            except Exception as exc:  # pragma: no cover - API初期化失敗時
                logger.warning(
                    "Failed to initialize Gemini primary model (%s): %s",
                    self.primary_model,
                    exc,
                )
                try:
                    self._model = genai.GenerativeModel(self.fallback_model)
                except Exception as fallback_exc:  # pragma: no cover
                    logger.error(
                        "Failed to initialize Gemini fallback model (%s): %s",
                        self.fallback_model,
                        fallback_exc,
                    )
                    self._model = None

    @property
    def is_available(self) -> bool:
        """APIキーとモデルが利用可能か判定."""
        return self._model is not None

    def generate_content(self, prompt: str) -> Optional[str]:
        """プロンプトを送信しテキストレスポンスを返す."""
        if not self.is_available:
            return None

        try:
            response = self._model.generate_content(prompt)
            text = (response.text or "").strip()
            return text or None
        except Exception as exc:  # pragma: no cover - API呼び出し失敗
            logger.error("Gemini generate_content error: %s", exc)
            return None


default_gemini_client = GeminiClient()

__all__ = ["GeminiClient", "default_gemini_client"]
