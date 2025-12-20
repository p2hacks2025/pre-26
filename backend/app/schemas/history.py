"""履歴関連のスキーマ"""

from __future__ import annotations

from typing import Optional

from pydantic import BaseModel


class HistoryItem(BaseModel):
    url: str
    title: str
    visitTime: int
    visitCount: int


class AnalyzeRequest(BaseModel):
    history: list[HistoryItem]
    currentTime: int
    startTime: int
    endTime: int
    maxNodes: Optional[int] = 50
