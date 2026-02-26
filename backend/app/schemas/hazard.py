"""ハザードマップ関連のスキーマ"""
from pydantic import BaseModel
from typing import List, Optional, Dict, Any
from datetime import datetime


class LocationRequest(BaseModel):
    """位置情報リクエスト"""
    lat: float
    lng: float
    address: Optional[str] = None


class RiskScore(BaseModel):
    """リスクスコア"""
    youkai_id: str
    youkai_name: str
    youkai_emoji: str
    score: int  # 0-100
    level: str  # 安心, 注意, 警戒, 要対策
    details: Dict[str, Any] = {}


class YoukaiMessage(BaseModel):
    """妖怪のメッセージ"""
    speaker: str
    speaker_name: str
    speaker_emoji: str
    emotion: str  # friendly, warm, reassuring, relieved, calm, teaching, thinking, curious, serious, suggesting, warning
    text: str
    tag: Optional[str] = None  # "monument"=伝承碑, "shelter"=避難場所, None=通常


class HiddenRisk(BaseModel):
    """隠れリスク（AIが発見した複合リスク）"""
    id: str
    type: str  # 時系列, 経路, 季節, 時間帯, 複合地域, インフラ, 地形
    title: str
    description: str
    confidence: float  # 0.0-1.0
    severity: str  # low, medium, high, critical
    reasoning: Optional[str] = None


class RiskCombinationAnalysis(BaseModel):
    """複合リスク分析"""
    combined_score: int
    combination_type: str
    notes: str


class DataQuality(BaseModel):
    """データ品質情報"""
    completeness: float  # 0.0-1.0
    missing_data: List[str] = []
    confidence_overall: float  # 0.0-1.0


class AIAnalysis(BaseModel):
    """AI分析結果"""
    hidden_risks: List[HiddenRisk] = []
    risk_combination_analysis: Optional[RiskCombinationAnalysis] = None
    data_quality: Optional[DataQuality] = None


class MainRisk(BaseModel):
    """主要リスク"""
    youkai: str
    risk_type: str
    level: str


class Action(BaseModel):
    """推奨アクション"""
    category: str
    content: str


class Summary(BaseModel):
    """サマリー"""
    main_risks: List[MainRisk] = []
    actions: List[Action] = []
    reassurance: str = ""


class Metadata(BaseModel):
    """メタデータ"""
    youkai_appeared: List[str] = []
    conversation_tone: str = "reassuring"
    total_turns: int = 0
    generation_timestamp: str = ""
    prompt_version: str = "v1.0"


class YoukaiResponse(BaseModel):
    """妖怪の応答"""
    conversation: List[YoukaiMessage]
    summary: Summary
    ai_analysis: AIAnalysis = AIAnalysis()
    metadata: Metadata = Metadata()


class NearbyMonument(BaseModel):
    """近傍の自然災害伝承碑"""
    name: str
    disaster_type: str
    disaster_name: str
    description: str
    distance_km: float
    lat: float
    lng: float


class NearbyShelter(BaseModel):
    """近傍の指定緊急避難場所"""
    name: str
    address: str
    disaster_types: List[str] = []
    distance_km: float
    lat: float
    lng: float


class HazardResponse(BaseModel):
    """ハザードマップ応答"""
    location: Dict[str, Any]
    risk_scores: List[RiskScore]
    youkai_response: YoukaiResponse
    historical_analysis: Optional["HistoricalLandAnalysis"] = None
    nearby_monuments: List[NearbyMonument] = []
    nearby_shelters: List[NearbyShelter] = []
    raw_data: Optional[Dict[str, Any]] = None


class YoukaiInfo(BaseModel):
    """妖怪情報"""
    id: str
    name: str
    emoji: str
    domain: str
    personality: str
    rarity: str = "★★☆☆☆"  # レア度


class HistoricalFinding(BaseModel):
    """歴史的発見項目"""
    category: str  # terrain, water, development, disaster
    title: str
    description: str
    risk_implication: str  # この歴史がどうリスクに影響するか
    confidence: float  # 0.0-1.0
    source: str  # データソース


class HistoricalLandAnalysis(BaseModel):
    """歴史的土地利用分析"""
    has_historical_data: bool = False
    terrain_type: Optional[str] = None
    terrain_code: Optional[str] = None
    era_analysis: Optional[str] = None  # 時代による分析
    findings: List[HistoricalFinding] = []
    summary: str = ""  # 総合的な歴史分析サマリー
    recommended_map_layer: Optional[str] = None  # 比較に最適な地図レイヤーID
