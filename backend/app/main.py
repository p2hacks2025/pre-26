from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.v1 import router as api_v1_router

app = FastAPI(
    title="History Visualizer API",
    description="Chrome履歴をネットワークグラフとして可視化するAPI",
    version="1.0.0",
)

# CORS設定（デモ優先で全許可）
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ルーターの登録
app.include_router(api_v1_router)


@app.get("/")
async def root():
    return {"message": "History Visualizer API", "docs": "/docs"}


@app.get("/health")
async def health_check():
    return {"status": "ok"}
