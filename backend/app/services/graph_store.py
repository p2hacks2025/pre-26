"""グラフデータのメモリストア

ハッカソン用にサーバメモリでグラフ情報を保持。
UUIDをキーにしてNetworkXグラフやメタ情報を保存する。
"""
import uuid
from typing import Dict, Any, Optional
from datetime import datetime, timedelta


class GraphStore:
    """グラフデータを一時保存するストア"""

    def __init__(self):
        # {uuid: {"graph_data": {...}, "created_at": datetime, "nodes": [...], "edges": [...]}}
        self._store: Dict[str, Dict[str, Any]] = {}
        # デフォルトで30分後に削除（メモリ節約）
        self._ttl_minutes = 30

    def generate_uuid(self) -> str:
        """新しいUUIDを生成"""
        return str(uuid.uuid4())

    def save(self, session_uuid: str, graph_data: Dict[str, Any]) -> None:
        """グラフデータを保存

        Args:
            session_uuid: セッションUUID
            graph_data: 保存するグラフデータ（nodes, edges, pathなど）
        """
        self._store[session_uuid] = {
            "graph_data": graph_data,
            "created_at": datetime.now(),
        }
        # 古いデータを削除
        self._cleanup_old_data()

    def get(self, session_uuid: str) -> Optional[Dict[str, Any]]:
        """UUIDでグラフデータを取得

        Args:
            session_uuid: セッションUUID

        Returns:
            グラフデータ、存在しない場合はNone
        """
        data = self._store.get(session_uuid)
        if data:
            return data["graph_data"]
        return None

    def _cleanup_old_data(self) -> None:
        """TTLを過ぎたデータを削除"""
        now = datetime.now()
        expired_keys = [
            key for key, value in self._store.items()
            if now - value["created_at"] > timedelta(minutes=self._ttl_minutes)
        ]
        for key in expired_keys:
            del self._store[key]

    def delete(self, session_uuid: str) -> bool:
        """指定したUUIDのデータを削除

        Args:
            session_uuid: セッションUUID

        Returns:
            削除成功した場合True
        """
        if session_uuid in self._store:
            del self._store[session_uuid]
            return True
        return False


# グローバルインスタンス（ハッカソン用のシンプルな実装）
graph_store = GraphStore()
