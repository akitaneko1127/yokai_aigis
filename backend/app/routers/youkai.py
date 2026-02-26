"""妖怪関連のルーター"""
from fastapi import APIRouter
from typing import List

from ..schemas.hazard import YoukaiInfo
from ..models.youkai import YOUKAI_CONFIG

router = APIRouter(prefix="/api/youkai", tags=["youkai"])


@router.get("/list", response_model=List[YoukaiInfo])
async def get_youkai_list():
    """全妖怪の一覧を取得"""
    return [
        YoukaiInfo(
            id=youkai.id,
            name=youkai.name,
            emoji=youkai.emoji,
            domain=youkai.domain,
            personality=youkai.personality,
            rarity=youkai.rarity
        )
        for youkai in YOUKAI_CONFIG.values()
    ]


@router.get("/{youkai_id}", response_model=YoukaiInfo)
async def get_youkai(youkai_id: str):
    """指定した妖怪の情報を取得"""
    if youkai_id not in YOUKAI_CONFIG:
        return {"error": "Youkai not found"}

    youkai = YOUKAI_CONFIG[youkai_id]
    return YoukaiInfo(
        id=youkai.id,
        name=youkai.name,
        emoji=youkai.emoji,
        domain=youkai.domain,
        personality=youkai.personality,
        rarity=youkai.rarity
    )
