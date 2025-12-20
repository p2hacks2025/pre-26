"""API依存関係"""

from __future__ import annotations

from typing import Annotated

from fastapi import Depends

from app.clients.gemini import GeminiClient, default_gemini_client


def get_gemini_client() -> GeminiClient:
    """Geminiクライアントのシングルトンを返す."""
    return default_gemini_client


GeminiClientDep = Annotated[GeminiClient, Depends(get_gemini_client)]

__all__ = ["GeminiClientDep", "get_gemini_client"]
