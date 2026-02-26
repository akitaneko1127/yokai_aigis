"""国土交通省 不動産情報ライブラリAPI連携サービス"""
import httpx
import math
from typing import Dict, Any, Optional
from ..config import settings


def lat_lon_to_tile(lat: float, lon: float, zoom: int) -> tuple:
    """緯度経度をXYZタイル座標に変換"""
    n = 2 ** zoom
    x = int((lon + 180.0) / 360.0 * n)
    lat_rad = math.radians(lat)
    y = int((1.0 - math.asinh(math.tan(lat_rad)) / math.pi) / 2.0 * n)
    return x, y, zoom


class ReinfollibApiService:
    """不動産情報ライブラリAPI連携サービス

    API参考: https://www.reinfolib.mlit.go.jp/help/apiManual/

    2025年11月更新のエンドポイント:
    - XKT025: 液状化発生傾向図・地形分類
    - XKT026: 洪水浸水想定区域
    - XKT027: 高潮浸水想定区域
    - XKT028: 津波浸水想定
    - XKT029: 土砂災害警戒区域

    パラメータ: x, y, z (XYZタイル座標), response_format (geojson/pbf)
    """

    def __init__(self):
        self.base_url = settings.REINFOLIB_BASE_URL
        self.api_key = settings.REINFOLIB_API_KEY
        self.headers = {
            "Ocp-Apim-Subscription-Key": self.api_key
        }

    async def get_hazard_info(self, lat: float, lng: float) -> Dict[str, Any]:
        """
        ハザード情報を取得

        参考: https://www.reinfolib.mlit.go.jp/help/apiManual/
        """
        result = {
            "flood": None,
            "inland_flood": None,  # 内水氾濫
            "landslide": None,
            "tsunami": None,
            "storm_surge": None,
            "liquefaction": None,  # 液状化
            "terrain": None,  # 地形分類
        }

        # Windows環境対応のためのtimeout設定
        timeout = httpx.Timeout(30.0, connect=10.0)
        async with httpx.AsyncClient(timeout=timeout, verify=True) as client:
            # 洪水浸水想定区域
            try:
                flood_data = await self._fetch_flood_hazard(client, lat, lng)
                result["flood"] = flood_data
            except Exception as e:
                print(f"洪水データ取得エラー: {e}")

            # 土砂災害警戒区域
            try:
                landslide_data = await self._fetch_landslide_hazard(client, lat, lng)
                result["landslide"] = landslide_data
            except Exception as e:
                print(f"土砂災害データ取得エラー: {e}")

            # 津波浸水想定区域
            try:
                tsunami_data = await self._fetch_tsunami_hazard(client, lat, lng)
                result["tsunami"] = tsunami_data
            except Exception as e:
                print(f"津波データ取得エラー: {e}")

            # 高潮浸水想定区域
            try:
                storm_surge_data = await self._fetch_storm_surge_hazard(client, lat, lng)
                result["storm_surge"] = storm_surge_data
            except Exception as e:
                print(f"高潮データ取得エラー: {e}")

            # 内水浸水想定区域
            try:
                inland_flood_data = await self._fetch_inland_flood_hazard(client, lat, lng)
                result["inland_flood"] = inland_flood_data
            except Exception as e:
                print(f"内水浸水データ取得エラー: {e}")

            # 液状化危険度
            try:
                liquefaction_data = await self._fetch_liquefaction_hazard(client, lat, lng)
                result["liquefaction"] = liquefaction_data
            except Exception as e:
                print(f"液状化データ取得エラー: {e}")

            # 地形分類（地盤リスク）
            try:
                terrain_data = await self._fetch_terrain_classification(client, lat, lng)
                result["terrain"] = terrain_data
            except Exception as e:
                import traceback
                print(f"地形分類データ取得エラー: {e}")
                traceback.print_exc()

        return result

    async def _fetch_flood_hazard(
        self, client: httpx.AsyncClient, lat: float, lng: float
    ) -> Optional[Dict[str, Any]]:
        """洪水浸水想定区域を取得"""
        # APIエンドポイント: /XKT026 (洪水浸水想定区域) - 2025年11月更新
        x, y, z = lat_lon_to_tile(lat, lng, 15)
        url = f"{self.base_url}/XKT026"
        params = {
            "x": x,
            "y": y,
            "z": z,
            "response_format": "geojson"
        }

        response = await client.get(url, headers=self.headers, params=params)

        if response.status_code == 200:
            data = response.json()
            return self._parse_flood_data(data)
        return None

    async def _fetch_landslide_hazard(
        self, client: httpx.AsyncClient, lat: float, lng: float
    ) -> Optional[Dict[str, Any]]:
        """土砂災害警戒区域を取得"""
        # APIエンドポイント: /XKT029 (土砂災害警戒区域) - 2025年11月更新
        x, y, z = lat_lon_to_tile(lat, lng, 15)
        url = f"{self.base_url}/XKT029"
        params = {
            "x": x,
            "y": y,
            "z": z,
            "response_format": "geojson"
        }

        response = await client.get(url, headers=self.headers, params=params)

        if response.status_code == 200:
            data = response.json()
            return self._parse_landslide_data(data)
        return None

    async def _fetch_tsunami_hazard(
        self, client: httpx.AsyncClient, lat: float, lng: float
    ) -> Optional[Dict[str, Any]]:
        """津波浸水想定区域を取得"""
        # APIエンドポイント: /XKT028 (津波浸水想定) - 2025年11月更新
        x, y, z = lat_lon_to_tile(lat, lng, 15)
        url = f"{self.base_url}/XKT028"
        params = {
            "x": x,
            "y": y,
            "z": z,
            "response_format": "geojson"
        }

        response = await client.get(url, headers=self.headers, params=params)

        if response.status_code == 200:
            data = response.json()
            return self._parse_tsunami_data(data)
        return None

    async def _fetch_storm_surge_hazard(
        self, client: httpx.AsyncClient, lat: float, lng: float
    ) -> Optional[Dict[str, Any]]:
        """高潮浸水想定区域を取得"""
        # APIエンドポイント: /XKT027 (高潮浸水想定区域) - 2025年11月更新
        x, y, z = lat_lon_to_tile(lat, lng, 15)
        url = f"{self.base_url}/XKT027"
        params = {
            "x": x,
            "y": y,
            "z": z,
            "response_format": "geojson"
        }

        response = await client.get(url, headers=self.headers, params=params)

        if response.status_code == 200:
            data = response.json()
            return self._parse_storm_surge_data(data)
        return None

    async def _fetch_inland_flood_hazard(
        self, client: httpx.AsyncClient, lat: float, lng: float
    ) -> Optional[Dict[str, Any]]:
        """内水浸水想定区域を取得"""
        # APIエンドポイント: /XKT002 (内水浸水想定区域)
        x, y, z = lat_lon_to_tile(lat, lng, 15)
        url = f"{self.base_url}/XKT002"
        params = {
            "x": x,
            "y": y,
            "z": z,
            "response_format": "geojson"
        }

        response = await client.get(url, headers=self.headers, params=params)

        if response.status_code == 200:
            data = response.json()
            return self._parse_inland_flood_data(data)
        return None

    async def _fetch_liquefaction_hazard(
        self, client: httpx.AsyncClient, lat: float, lng: float
    ) -> Optional[Dict[str, Any]]:
        """液状化発生傾向・地形分類を取得"""
        # APIエンドポイント: /XKT025 (液状化発生傾向図・地形分類) - 2025年11月更新
        x, y, z = lat_lon_to_tile(lat, lng, 15)
        url = f"{self.base_url}/XKT025"
        params = {
            "x": x,
            "y": y,
            "z": z,
            "response_format": "geojson"
        }

        response = await client.get(url, headers=self.headers, params=params)

        if response.status_code == 200:
            data = response.json()
            return self._parse_liquefaction_data(data)
        return None

    async def _fetch_terrain_classification(
        self, client: httpx.AsyncClient, lat: float, lng: float
    ) -> Optional[Dict[str, Any]]:
        """地形分類を取得（液状化発生傾向図と同じエンドポイント）"""
        # APIエンドポイント: /XKT025 (液状化発生傾向図・地形分類) - 2025年11月更新
        x, y, z = lat_lon_to_tile(lat, lng, 15)
        url = f"{self.base_url}/XKT025"
        params = {
            "x": x,
            "y": y,
            "z": z,
            "response_format": "geojson"
        }

        response = await client.get(url, headers=self.headers, params=params)

        if response.status_code == 200:
            data = response.json()
            return self._parse_terrain_data(data)
        return None

    def _parse_flood_data(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """洪水データをパース"""
        result = {
            "has_risk": False,
            "depth": None,
            "depth_rank": None,
            "river_name": None
        }

        if "features" in data and len(data["features"]) > 0:
            result["has_risk"] = True
            feature = data["features"][0]
            props = feature.get("properties", {})

            # 浸水深ランク (A1_001など)
            depth_rank = props.get("A1_001") or props.get("depth_rank")
            if depth_rank:
                result["depth_rank"] = depth_rank
                result["depth"] = self._convert_depth_rank(depth_rank)

            # 河川名
            result["river_name"] = props.get("river_name") or props.get("A1_002")

        return result

    def _parse_landslide_data(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """土砂災害データをパース"""
        result = {
            "has_risk": False,
            "warning_zone": False,
            "special_warning_zone": False,
            "landslide_type": None
        }

        if "features" in data and len(data["features"]) > 0:
            result["has_risk"] = True
            feature = data["features"][0]
            props = feature.get("properties", {})

            # 警戒区域の種類
            zone_type = props.get("A1_001") or props.get("zone_type")
            if zone_type == "1":
                result["warning_zone"] = True
            elif zone_type == "2":
                result["special_warning_zone"] = True
                result["warning_zone"] = True

            # 土砂災害の種類
            result["landslide_type"] = props.get("A1_002") or props.get("landslide_type")

        return result

    def _parse_tsunami_data(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """津波データをパース"""
        result = {
            "has_risk": False,
            "depth": None,
            "depth_rank": None
        }

        if "features" in data and len(data["features"]) > 0:
            result["has_risk"] = True
            feature = data["features"][0]
            props = feature.get("properties", {})

            depth_rank = props.get("A1_001") or props.get("depth_rank")
            if depth_rank:
                result["depth_rank"] = depth_rank
                result["depth"] = self._convert_depth_rank(depth_rank)

        return result

    def _parse_storm_surge_data(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """高潮データをパース"""
        result = {
            "has_risk": False,
            "depth": None,
            "depth_rank": None
        }

        if "features" in data and len(data["features"]) > 0:
            result["has_risk"] = True
            feature = data["features"][0]
            props = feature.get("properties", {})

            depth_rank = props.get("A1_001") or props.get("depth_rank")
            if depth_rank:
                result["depth_rank"] = depth_rank
                result["depth"] = self._convert_depth_rank(depth_rank)

        return result

    def _parse_inland_flood_data(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """内水浸水データをパース"""
        result = {
            "has_risk": False,
            "depth": None,
            "depth_rank": None
        }

        if "features" in data and len(data["features"]) > 0:
            result["has_risk"] = True
            feature = data["features"][0]
            props = feature.get("properties", {})

            depth_rank = props.get("A1_001") or props.get("depth_rank")
            if depth_rank:
                result["depth_rank"] = depth_rank
                result["depth"] = self._convert_depth_rank(depth_rank)

        return result

    def _parse_liquefaction_data(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """液状化データをパース

        XKT025 APIのレスポンス形式（2024年10月更新）:
        - liquefaction_tendency_level: 液状化傾向レベル（1=非常に液状化しやすい, 2=液状化しやすい, 3=液状化しにくい, 4=非常に液状化しにくい）
        - note: 液状化傾向の説明（例: "非常に液状化しやすい"）
        - topographic_classification_code: 地形分類コード
        - topographic_classification_name_ja: 地形分類名（日本語）
        """
        result = {
            "has_risk": False,
            "risk_level": None,
            "risk_rank": None,
            "note": None
        }

        if "features" in data and len(data["features"]) > 0:
            result["has_risk"] = True
            feature = data["features"][0]
            props = feature.get("properties", {})

            # 液状化傾向レベル（新しいAPI形式）
            tendency_level = props.get("liquefaction_tendency_level")
            note = props.get("note")

            if tendency_level is not None:
                # APIのlevelは1=最もリスク高い、4=最もリスク低いなので反転
                # risk_rankは1=低い、4=非常に高いにマッピング
                level_to_rank = {1: 4, 2: 3, 3: 2, 4: 1}
                result["risk_rank"] = level_to_rank.get(int(tendency_level), 2)
                result["risk_level"] = note or self._convert_liquefaction_rank(result["risk_rank"])
                result["note"] = note
            elif note:
                # noteがある場合はそれを使用
                result["risk_level"] = note
                # noteから危険度を推定
                if "非常に液状化しやすい" in note:
                    result["risk_rank"] = 4
                elif "液状化しやすい" in note:
                    result["risk_rank"] = 3
                elif "液状化しにくい" in note and "非常に" not in note:
                    result["risk_rank"] = 2
                elif "非常に液状化しにくい" in note:
                    result["risk_rank"] = 1
                else:
                    result["risk_rank"] = 2  # デフォルト

            # 旧形式のフォールバック
            if result["risk_rank"] is None:
                risk_rank = props.get("A1_001") or props.get("risk_rank")
                if risk_rank:
                    result["risk_rank"] = risk_rank
                    result["risk_level"] = self._convert_liquefaction_rank(risk_rank)

        return result

    def _parse_terrain_data(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """地形分類データをパース

        XKT025 APIのレスポンス形式（2024年10月更新）:
        - topographic_classification_code: 地形分類コード（新コード体系）
        - topographic_classification_name_ja: 地形分類名（日本語）
        """
        result = {
            "has_data": False,
            "terrain_type": None,
            "terrain_code": None,
            "ground_condition": None,
            "former_land_use": None  # 過去の土地利用（埋立地、水田等）
        }

        if "features" in data and len(data["features"]) > 0:
            result["has_data"] = True
            feature = data["features"][0]
            props = feature.get("properties", {})

            # 新しいAPI形式: topographic_classification_code, topographic_classification_name_ja
            terrain_code = props.get("topographic_classification_code")
            terrain_name = props.get("topographic_classification_name_ja")

            if terrain_code is not None:
                # 新しいコード体系を旧コード体系にマッピング
                result["terrain_code"] = self._map_new_terrain_code(terrain_code)
                result["terrain_type"] = terrain_name or self._convert_terrain_code(result["terrain_code"])
                result["ground_condition"] = self._get_ground_condition(result["terrain_code"])
                result["former_land_use"] = self._get_former_land_use(result["terrain_code"])
            elif terrain_name:
                # 名前からコードを逆引き
                result["terrain_type"] = terrain_name
                result["terrain_code"] = self._get_terrain_code_from_name(terrain_name)
                if result["terrain_code"]:
                    result["ground_condition"] = self._get_ground_condition(result["terrain_code"])
                    result["former_land_use"] = self._get_former_land_use(result["terrain_code"])

            # 旧形式のフォールバック
            if result["terrain_code"] is None:
                terrain_code = props.get("A1_001") or props.get("terrain_code")
                if terrain_code:
                    result["terrain_code"] = terrain_code
                    result["terrain_type"] = self._convert_terrain_code(terrain_code)
                    result["ground_condition"] = self._get_ground_condition(terrain_code)
                    result["former_land_use"] = self._get_former_land_use(terrain_code)

        return result

    def _map_new_terrain_code(self, new_code: int) -> str:
        """新しい地形分類コードを旧コード体系にマッピング

        XKT025 APIの新コード体系（2024年10月更新）から、
        アプリ内部で使用する旧コード体系への変換
        """
        # 新API -> 旧コード のマッピング（液状化傾向図ベース）
        new_to_old = {
            1: "1",   # 山地
            2: "2",   # 丘陵
            3: "3",   # 山麓堆積地形
            4: "4",   # 火山地形
            5: "5",   # 台地・段丘
            6: "6",   # 低地
            7: "7",   # 沖積低地
            8: "8",   # 谷底低地
            9: "9",   # 後背湿地
            10: "10", # 氾濫平野
            11: "11", # 自然堤防
            12: "12", # 旧河道
            13: "13", # 干拓地
            14: "14", # 埋立地（旧コード）
            15: "15", # 砂州・砂丘
            16: "16", # デルタ
            # 新コード体系での追加マッピング
            17: "3",  # 扇状地 -> 山麓堆積地形
            18: "11", # 砂礫州 -> 自然堤防
            19: "13", # 干潟 -> 干拓地
            20: "14", # 埋立地（新コード）
            21: "9",  # 旧湖沼 -> 後背湿地
            22: "12", # 旧水路 -> 旧河道
        }
        return new_to_old.get(int(new_code), str(new_code))

    def _get_terrain_code_from_name(self, name: str) -> Optional[str]:
        """地形分類名からコードを取得"""
        name_to_code = {
            "山地": "1",
            "丘陵": "2",
            "山麓堆積地形": "3",
            "扇状地": "3",
            "火山地形": "4",
            "台地・段丘": "5",
            "台地": "5",
            "段丘": "5",
            "低地": "6",
            "沖積低地": "7",
            "谷底低地": "8",
            "後背湿地": "9",
            "氾濫平野": "10",
            "自然堤防": "11",
            "旧河道": "12",
            "干拓地": "13",
            "埋立地": "14",
            "砂州・砂丘": "15",
            "砂州": "15",
            "砂丘": "15",
            "デルタ": "16",
            "三角州": "16",
        }
        return name_to_code.get(name)

    def _convert_depth_rank(self, rank: str) -> str:
        """浸水深ランクを文字列に変換"""
        rank_map = {
            "1": "0.5m未満",
            "2": "0.5m〜1.0m",
            "3": "1.0m〜2.0m",
            "4": "2.0m〜3.0m",
            "5": "3.0m〜5.0m",
            "6": "5.0m以上",
        }
        return rank_map.get(str(rank), f"ランク{rank}")

    def _convert_liquefaction_rank(self, rank: str) -> str:
        """液状化危険度ランクを文字列に変換"""
        rank_map = {
            "1": "液状化の可能性が低い",
            "2": "液状化の可能性がある",
            "3": "液状化の可能性が高い",
            "4": "液状化の可能性が非常に高い",
        }
        return rank_map.get(str(rank), f"ランク{rank}")

    def _convert_terrain_code(self, code: str) -> str:
        """地形分類コードを文字列に変換"""
        terrain_map = {
            "1": "山地",
            "2": "丘陵",
            "3": "山麓堆積地形",
            "4": "火山地形",
            "5": "台地・段丘",
            "6": "低地",
            "7": "沖積低地",
            "8": "谷底低地",
            "9": "後背湿地",
            "10": "氾濫平野",
            "11": "自然堤防",
            "12": "旧河道",
            "13": "干拓地",
            "14": "埋立地",
            "15": "砂州・砂丘",
            "16": "デルタ",
        }
        return terrain_map.get(str(code), f"地形分類{code}")

    def _get_ground_condition(self, code: str) -> str:
        """地形分類から地盤状況を判定"""
        # 軟弱地盤のリスクが高い地形
        soft_ground = ["6", "7", "8", "9", "10", "12", "13", "14", "16"]
        medium_ground = ["3", "11", "15"]

        if str(code) in soft_ground:
            return "軟弱地盤の可能性が高い"
        elif str(code) in medium_ground:
            return "地盤の状態に注意"
        else:
            return "比較的良好な地盤"

    def _get_former_land_use(self, code: str) -> Optional[str]:
        """地形分類から過去の土地利用を推定"""
        former_use_map = {
            "9": "かつて湿地帯だった可能性",
            "12": "かつて川が流れていた場所",
            "13": "かつて海・湖沼だった干拓地",
            "14": "かつて海・湖沼だった埋立地",
        }
        return former_use_map.get(str(code))
