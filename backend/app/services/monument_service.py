"""自然災害伝承碑の近傍検索サービス"""

import json
import math
import os
import logging
from dataclasses import dataclass
from typing import List, Optional

logger = logging.getLogger(__name__)

# GeoJSONファイルのパス（プロジェクトルートからの相対パス）
GEOJSON_PATH = os.path.join(
    os.path.dirname(__file__), "..", "..", "..", "20260129_GeoJSON", "20260129.geojson"
)


@dataclass
class Monument:
    id: str
    name: str
    built_year: str
    location: str
    disaster_name: str
    disaster_type: str
    description: str
    lat: float
    lng: float
    distance_km: float = 0.0


def _haversine_km(lat1: float, lng1: float, lat2: float, lng2: float) -> float:
    """2点間の距離をkmで計算"""
    R = 6371.0
    dlat = math.radians(lat2 - lat1)
    dlng = math.radians(lng2 - lng1)
    a = (
        math.sin(dlat / 2) ** 2
        + math.cos(math.radians(lat1))
        * math.cos(math.radians(lat2))
        * math.sin(dlng / 2) ** 2
    )
    return R * 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))


class MonumentService:
    """自然災害伝承碑GeoJSONを読み込み、近傍検索を提供する"""

    _features: Optional[list] = None

    @classmethod
    def _load(cls) -> list:
        if cls._features is not None:
            return cls._features

        path = os.path.normpath(GEOJSON_PATH)
        if not os.path.exists(path):
            logger.warning("伝承碑GeoJSONが見つかりません: %s", path)
            cls._features = []
            return cls._features

        with open(path, encoding="utf-8") as f:
            data = json.load(f)

        cls._features = data.get("features", [])
        logger.info("伝承碑データ読み込み完了: %d件", len(cls._features))
        return cls._features

    @classmethod
    def find_nearby(
        cls, lat: float, lng: float, radius_km: float = 10.0, max_results: int = 3
    ) -> List[Monument]:
        """指定座標から半径radius_km以内の伝承碑を近い順に返す"""
        features = cls._load()
        results: List[Monument] = []

        for feat in features:
            coords = feat.get("geometry", {}).get("coordinates", [])
            if len(coords) < 2:
                continue

            # GeoJSON: [lng, lat]
            m_lng, m_lat = coords[0], coords[1]
            dist = _haversine_km(lat, lng, m_lat, m_lng)

            if dist <= radius_km:
                props = feat.get("properties", {})
                results.append(
                    Monument(
                        id=props.get("ID", ""),
                        name=props.get("碑名", ""),
                        built_year=props.get("建立年", ""),
                        location=props.get("所在地", ""),
                        disaster_name=props.get("災害名", ""),
                        disaster_type=props.get("災害種別", ""),
                        description=props.get("伝承内容", ""),
                        lat=m_lat,
                        lng=m_lng,
                        distance_km=round(dist, 2),
                    )
                )

        results.sort(key=lambda m: m.distance_km)
        return results[:max_results]

    @classmethod
    def format_for_prompt(cls, monuments: List[Monument]) -> str:
        """LLMプロンプト用にフォーマット"""
        if not monuments:
            return ""

        lines = ["## 付近の自然災害伝承碑"]
        for i, m in enumerate(monuments, 1):
            lines.append(
                f"{i}. 「{m.name}」（{m.disaster_type}、約{m.distance_km}km先）"
            )
            lines.append(f"   災害: {m.disaster_name}")
            # 伝承内容は200文字に制限（トークン節約）
            desc = m.description[:200] + ("..." if len(m.description) > 200 else "")
            lines.append(f"   教訓: {desc}")

        lines.append("")
        lines.append(
            "上記の伝承碑データがある場合、会話の中で「この近くには過去にこんな災害があった」"
            "という形で自然に言及し、先人の教訓を伝えてください。"
        )
        return "\n".join(lines)
