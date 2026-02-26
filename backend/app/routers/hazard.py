"""ハザードマップ関連のルーター（LLM統合 + 歴史的土地分析機能 + TTS音声合成）"""
import logging
from fastapi import APIRouter, HTTPException
from fastapi.responses import Response
from pydantic import BaseModel
from typing import Dict, Any

from ..schemas.hazard import LocationRequest, HazardResponse
from ..services.reinfolib_api import ReinfollibApiService
from ..services.risk_calculator import RiskCalculator
from ..services.youkai_responder import YoukaiResponder
from ..services.historical_analyzer import HistoricalLandAnalyzer
from ..services.monument_service import MonumentService
from ..services.shelter_service import ShelterService
from ..schemas.hazard import NearbyMonument, NearbyShelter
from ..config import settings

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/hazard", tags=["hazard"])


@router.post("/analyze", response_model=HazardResponse)
async def analyze_location(request: LocationRequest):
    """
    指定した位置のハザード情報を分析し、妖怪たちの応答を生成

    - **lat**: 緯度
    - **lng**: 経度
    - **address**: 住所（オプション）

    LLMが有効な場合は自然な妖怪会話を生成。
    LLM無効または接続失敗時はテンプレート応答にフォールバック。
    """
    try:
        # 不動産情報ライブラリAPIからハザード情報を取得
        api_service = ReinfollibApiService()
        hazard_data = await api_service.get_hazard_info(request.lat, request.lng)

        # リスクスコアを計算
        risk_scores = RiskCalculator.calculate_all_risks(hazard_data)

        # 位置情報
        location_data = {
            "lat": request.lat,
            "lng": request.lng,
            "address": request.address
        }

        # 歴史的土地利用分析
        historical_analysis = HistoricalLandAnalyzer.analyze(hazard_data)

        # 歴史分析のサマリーをLLMに渡す用
        historical_summary = ""
        if historical_analysis and historical_analysis.has_historical_data:
            historical_summary = historical_analysis.summary

        # 自然災害伝承碑の近傍検索
        monuments = MonumentService.find_nearby(request.lat, request.lng)
        monument_text = MonumentService.format_for_prompt(monuments)
        if monuments:
            logger.info("伝承碑 %d件発見（最近: %.1fkm）", len(monuments), monuments[0].distance_km)

        # 指定緊急避難場所の近傍検索
        shelters = await ShelterService.find_nearby(request.lat, request.lng)
        shelter_text = ShelterService.format_for_prompt(shelters)
        if shelters:
            logger.info("避難所 %d件発見（最近: %.1fkm）", len(shelters), shelters[0].distance_km)

        # LLM用の追加コンテキスト（伝承碑 + 避難所）
        extra_context = "\n".join(filter(None, [monument_text, shelter_text]))

        # LLMで妖怪応答を生成（失敗時はNone）
        youkai_response = await YoukaiResponder.generate_response_with_llm(
            risk_scores,
            location_data=location_data,
            historical_summary=historical_summary,
            monument_text=extra_context,
        )

        # LLM失敗時はテンプレートにフォールバック
        if youkai_response is None:
            logger.info("テンプレートモードで応答を生成")
            youkai_response = YoukaiResponder.generate_response(
                risk_scores,
                location_data=location_data,
                monuments=monuments,
                shelters=shelters,
            )
        else:
            # LLM応答に伝承碑・避難所の言及がない場合、テンプレートメッセージを補完
            youkai_response = YoukaiResponder.supplement_monument_shelter(
                youkai_response, risk_scores, monuments, shelters
            )

        # レスポンス用に伝承碑・避難所データを変換
        nearby_monuments = [
            NearbyMonument(
                name=m.name,
                disaster_type=m.disaster_type,
                disaster_name=m.disaster_name,
                description=m.description[:200],
                distance_km=m.distance_km,
                lat=m.lat,
                lng=m.lng,
            )
            for m in monuments
        ]
        nearby_shelters = [
            NearbyShelter(
                name=s.name,
                address=s.address,
                disaster_types=s.disaster_types,
                distance_km=s.distance_km,
                lat=s.lat,
                lng=s.lng,
            )
            for s in shelters
        ]

        return HazardResponse(
            location=location_data,
            risk_scores=risk_scores,
            youkai_response=youkai_response,
            historical_analysis=historical_analysis,
            nearby_monuments=nearby_monuments,
            nearby_shelters=nearby_shelters,
            raw_data=hazard_data
        )

    except Exception as e:
        import traceback
        print(f"Error analyzing location: {e}")
        traceback.print_exc()
        raise HTTPException(
            status_code=500,
            detail=f"位置情報の分析中にエラーが発生しました: {str(e)}"
        )


class SynthesizeRequest(BaseModel):
    text: str
    youkai_id: str


@router.post("/synthesize")
async def synthesize_speech(request: SynthesizeRequest):
    """テキストからVOICEVOX音声を合成

    - **text**: 読み上げるテキスト
    - **youkai_id**: 妖怪ID（speaker_idマッピングに使用）
    """
    if not settings.TTS_ENABLED:
        raise HTTPException(status_code=503, detail="TTS is disabled")

    from ..services.tts_client import tts_client, TTSClient

    speaker_id = TTSClient.get_speaker_id(request.youkai_id)
    wav_data = await tts_client.synthesize(request.text, speaker_id)

    if wav_data is None:
        raise HTTPException(status_code=502, detail="TTS synthesis failed")

    return Response(content=wav_data, media_type="audio/wav")


@router.get("/health")
async def health_check():
    """ヘルスチェック"""
    llm_status = "disabled"
    if settings.LLM_ENABLED:
        from ..services.llm_client import llm_client
        llm_status = "ok" if await llm_client.health_check() else "unavailable"

    tts_status = "disabled"
    if settings.TTS_ENABLED:
        from ..services.tts_client import tts_client
        tts_status = "ok" if await tts_client.health_check() else "unavailable"

    return {
        "status": "ok",
        "service": "youkai-hazard-map",
        "llm_enabled": settings.LLM_ENABLED,
        "llm_status": llm_status,
        "tts_enabled": settings.TTS_ENABLED,
        "tts_status": tts_status,
    }


@router.get("/test-api")
async def test_api():
    """API接続テスト"""
    import httpx

    try:
        timeout = httpx.Timeout(30.0, connect=10.0)
        async with httpx.AsyncClient(timeout=timeout) as client:
            headers = {"Ocp-Apim-Subscription-Key": settings.REINFOLIB_API_KEY}
            url = "https://www.reinfolib.mlit.go.jp/ex-api/external/XKT026"
            params = {"x": 14552, "y": 6451, "z": 15, "response_format": "geojson"}
            response = await client.get(url, headers=headers, params=params)
            return {
                "status": "ok",
                "api_status": response.status_code,
                "data_preview": str(response.text[:200])
            }
    except Exception as e:
        import traceback
        return {
            "status": "error",
            "error": str(e),
            "traceback": traceback.format_exc()
        }


@router.get("/debug-xkt025")
async def debug_xkt025(lat: float = 35.6295, lng: float = 139.7745):
    """XKT025 (液状化・地形分類) APIのレスポンスをデバッグ"""
    import httpx
    import math

    def lat_lon_to_tile(lat: float, lon: float, zoom: int) -> tuple:
        n = 2 ** zoom
        x = int((lon + 180.0) / 360.0 * n)
        lat_rad = math.radians(lat)
        y = int((1.0 - math.asinh(math.tan(lat_rad)) / math.pi) / 2.0 * n)
        return x, y, zoom

    try:
        x, y, z = lat_lon_to_tile(lat, lng, 15)
        timeout = httpx.Timeout(30.0, connect=10.0)
        async with httpx.AsyncClient(timeout=timeout) as client:
            headers = {"Ocp-Apim-Subscription-Key": settings.REINFOLIB_API_KEY}
            url = "https://www.reinfolib.mlit.go.jp/ex-api/external/XKT025"
            params = {"x": x, "y": y, "z": z, "response_format": "geojson"}
            response = await client.get(url, headers=headers, params=params)
            data = response.json()

            # Featureがあればその最初のプロパティを表示
            features_info = []
            if "features" in data:
                for i, feature in enumerate(data["features"][:3]):  # 最初の3件のみ
                    features_info.append({
                        "index": i,
                        "properties": feature.get("properties", {}),
                        "geometry_type": feature.get("geometry", {}).get("type")
                    })

            return {
                "status": "ok",
                "tile_coords": {"x": x, "y": y, "z": z},
                "api_status": response.status_code,
                "feature_count": len(data.get("features", [])),
                "collection_name": data.get("name"),
                "features_sample": features_info,
                "full_response_preview": str(response.text[:1000]) if len(response.text) > 1000 else response.text
            }
    except Exception as e:
        import traceback
        return {
            "status": "error",
            "error": str(e),
            "traceback": traceback.format_exc()
        }
