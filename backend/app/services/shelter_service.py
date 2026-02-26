"""指定緊急避難場所の近傍検索サービス（国土地理院ベクトルタイル）"""

import asyncio
import math
import logging
from dataclasses import dataclass, field
from typing import List

import httpx

logger = logging.getLogger(__name__)

# 国土地理院 指定緊急避難場所ベクトルタイル（災害種別ごとにレイヤーが分かれている）
# maxNativeZoom = 10（データはzoom 10にのみ存在）
GSI_SHELTER_LAYERS = [
    ("skhb01", "洪水"),
    ("skhb02", "崖崩れ・土石流・地滑り"),
    ("skhb03", "高潮"),
    ("skhb04", "地震"),
    ("skhb05", "津波"),
    ("skhb06", "大規模火事"),
    ("skhb07", "内水氾濫"),
    ("skhb08", "火山"),
]
GSI_TILE_URL = "https://maps.gsi.go.jp/xyz/{layer}/{z}/{x}/{y}.geojson"
NATIVE_ZOOM = 10


@dataclass
class Shelter:
    name: str
    address: str
    disaster_types: List[str] = field(default_factory=list)
    lat: float = 0.0
    lng: float = 0.0
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


def _lat_lon_to_tile(lat: float, lon: float, zoom: int) -> tuple:
    """緯度経度をXYZタイル座標に変換"""
    n = 2 ** zoom
    x = int((lon + 180.0) / 360.0 * n)
    lat_rad = math.radians(lat)
    y = int((1.0 - math.asinh(math.tan(lat_rad)) / math.pi) / 2.0 * n)
    return x, y


class ShelterService:
    """国土地理院の指定緊急避難場所データから近傍検索"""

    @staticmethod
    async def find_nearby(
        lat: float, lng: float, radius_km: float = 5.0, max_results: int = 3
    ) -> List[Shelter]:
        """指定座標から半径radius_km以内の避難所を近い順に返す

        全8災害種別レイヤーのタイルを並列取得し、
        施設名で統合（同一施設の災害種別をまとめる）。
        """
        cx, cy = _lat_lon_to_tile(lat, lng, NATIVE_ZOOM)

        # 中心 + 隣接4タイル（タイル境界付近の取りこぼし防止）
        tile_coords = list({(cx, cy), (cx - 1, cy), (cx + 1, cy), (cx, cy - 1), (cx, cy + 1)})

        # 全レイヤー × 全タイルを並列取得
        async with httpx.AsyncClient(timeout=10.0) as client:
            tasks = [
                ShelterService._fetch_tile(client, layer_id, tx, ty)
                for layer_id, _ in GSI_SHELTER_LAYERS
                for tx, ty in tile_coords
            ]
            results = await asyncio.gather(*tasks, return_exceptions=True)

        # results を (layer_index, tile_index) の順に並べ直す
        layer_results = []
        idx = 0
        for i in range(len(GSI_SHELTER_LAYERS)):
            combined = []
            for _ in tile_coords:
                r = results[idx]
                if not isinstance(r, Exception):
                    combined.extend(r)
                idx += 1
            layer_results.append(combined)
        results = layer_results

        # 施設名でグルーピング（同一施設は災害種別を統合）
        shelter_map: dict = {}  # name -> Shelter

        for i, result in enumerate(results):
            disaster_label = GSI_SHELTER_LAYERS[i][1]

            for feat in result:
                coords = feat.get("geometry", {}).get("coordinates", [])
                if len(coords) < 2:
                    continue

                s_lng, s_lat = coords[0], coords[1]
                dist = _haversine_km(lat, lng, s_lat, s_lng)

                if dist > radius_km:
                    continue

                props = feat.get("properties", {})
                name = props.get("name", "")
                if not name:
                    continue

                if name in shelter_map:
                    # 既存施設に災害種別を追加
                    if disaster_label not in shelter_map[name].disaster_types:
                        shelter_map[name].disaster_types.append(disaster_label)
                else:
                    shelter_map[name] = Shelter(
                        name=name,
                        address=props.get("address", ""),
                        disaster_types=[disaster_label],
                        lat=s_lat,
                        lng=s_lng,
                        distance_km=round(dist, 2),
                    )

        shelters = sorted(shelter_map.values(), key=lambda s: s.distance_km)
        return shelters[:max_results]

    @staticmethod
    async def _fetch_tile(
        client: httpx.AsyncClient, layer_id: str, x: int, y: int
    ) -> list:
        """1レイヤー・1タイル分のGeoJSONを取得"""
        url = GSI_TILE_URL.format(layer=layer_id, z=NATIVE_ZOOM, x=x, y=y)
        try:
            resp = await client.get(url)
            if resp.status_code != 200:
                return []
            data = resp.json()
            return data.get("features", [])
        except Exception as e:
            logger.debug("避難所タイル取得失敗 (%s/%d/%d): %s", layer_id, x, y, e)
            return []

    @staticmethod
    def format_for_prompt(shelters: List[Shelter]) -> str:
        """LLMプロンプト用にフォーマット"""
        if not shelters:
            return ""

        lines = ["## 付近の指定緊急避難場所"]
        for i, s in enumerate(shelters, 1):
            types_str = "・".join(s.disaster_types) if s.disaster_types else "指定避難所"
            lines.append(f"{i}. 「{s.name}」（約{s.distance_km}km先）")
            if s.address:
                lines.append(f"   住所: {s.address}")
            lines.append(f"   対応災害: {types_str}")

        lines.append("")
        lines.append(
            "上記の避難場所がある場合、会話の中で「近くの○○が避難場所として利用できる」"
            "という形で具体的な施設名を挙げて言及してください。"
        )
        return "\n".join(lines)
