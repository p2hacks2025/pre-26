import os
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
from typing import Optional
import uvicorn
import logic

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

search_logs = []

class LogItem(BaseModel):
    timestamp: str
    title: str
    url: str
    searchWord: Optional[str] = None
    domain: str

@app.post("/api/log")
async def receive_log(item: LogItem):
    print(f"Received Log: {item.title}")
    search_logs.append(item.dict())
    return {"status": "ok", "count": len(search_logs)}

@app.get("/api/graph")
async def get_graph():
    print(f"DEBUG: Generating graph for {len(search_logs)} items...")
    
    if not search_logs:
        return {"data": [], "layout": {}}
    
    try:
        fig_data = logic.create_graph_data(search_logs)
        
        # デバッグ: 結果がNoneになっていないか確認
        if fig_data is None:
            print("DEBUG: logic.create_graph_data returned None!")
            # フロントエンドにnullではなく空のグラフ設定を返してエラーを防ぐ
            return {"data": [], "layout": {}}
            
        return fig_data
    except Exception as e:
        print(f"Error generating graph: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.delete("/api/logs")
async def clear_logs():
    global search_logs
    search_logs = []
    print("All logs cleared.")
    return {"status": "cleared"}

if os.path.exists("frontend"):
    app.mount("/", StaticFiles(directory="frontend", html=True), name="static")

if __name__ == "__main__":
    uvicorn.run(app, host="127.0.0.1", port=8000)