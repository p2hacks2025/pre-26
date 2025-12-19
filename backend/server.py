from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Optional, List
import uvicorn
import logic  # logic.py をインポート

app = FastAPI()

# CORS設定 (開発用: すべてのオリジンを許可)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 簡易データベース (メモリ内リスト)
# サーバー再起動で消えるため、永続化が必要ならファイルやDBへ保存する処理を追加してください
search_logs = []

class LogItem(BaseModel):
    timestamp: str
    title: str
    url: str
    searchWord: Optional[str] = None
    domain: str

@app.post("/api/log")
async def receive_log(item: LogItem):
    """拡張機能からログを受け取る"""
    print(f"Received Log: {item.title}")
    search_logs.append(item.dict())
    return {"status": "ok", "count": len(search_logs)}

@app.get("/api/graph")
async def get_graph():
    """グラフデータを生成して返す"""
    if not search_logs:
        return {"data": [], "layout": {}}
    
    try:
        fig_data = logic.create_graph_data(search_logs)
        return fig_data
    except Exception as e:
        print(f"Error generating graph: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/logs")
async def get_logs():
    """保存されているログ一覧を取得 (デバッグ用)"""
    return search_logs

@app.delete("/api/logs")
async def clear_logs():
    """ログを全消去"""
    global search_logs
    search_logs = []
    print("All logs cleared.")
    return {"status": "cleared"}

if __name__ == "__main__":
    uvicorn.run(app, host="127.0.0.1", port=8000)