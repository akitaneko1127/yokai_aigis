"""妖怪ハザードマップ バックエンドAPI"""
import sys
import asyncio

# Windows環境でのasyncio設定
if sys.platform == "win32":
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .config import settings
from .routers import hazard_router, youkai_router

app = FastAPI(
    title="妖怪ハザードマップ API",
    description="土地の災害リスクを妖怪たちが優しく教えてくれるAPIです",
    version="1.0.0"
)

# CORS設定
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ルーター登録
app.include_router(hazard_router)
app.include_router(youkai_router)


@app.get("/")
async def root():
    """ルートエンドポイント"""
    return {
        "message": "妖怪ハザードマップAPIへようこそ！",
        "docs": "/docs",
        "youkai": ["🥒河童", "🐟大ナマズ", "🕷️土蜘蛛", "🔥火車", "❄️雪女", "🌋ヒノカグツチ"]
    }
