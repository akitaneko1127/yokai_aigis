// 位置情報
export interface Location {
  lat: number;
  lng: number;
  address?: string;
}

// リスクスコア
export interface RiskScore {
  youkai_id: string;
  youkai_name: string;
  youkai_emoji: string;
  score: number;
  level: '安心' | '注意' | '警戒' | '要対策';
  details: Record<string, unknown>;
}

// 妖怪メッセージ
export interface YoukaiMessage {
  speaker: string;
  speaker_name: string;
  speaker_emoji: string;
  emotion: 'friendly' | 'warm' | 'reassuring' | 'relieved' | 'calm' | 'teaching' | 'thinking' | 'curious' | 'serious' | 'suggesting' | 'warning';
  text: string;
  tag?: 'monument' | 'shelter' | null;
}

// 主要リスク
export interface MainRisk {
  youkai: string;
  risk_type: string;
  level: string;
}

// アクション
export interface Action {
  category: string;
  content: string;
}

// サマリー
export interface Summary {
  main_risks: MainRisk[];
  actions: Action[];
  reassurance: string;
}

// 隠れリスク
export interface HiddenRisk {
  id: string;
  type: string;
  title: string;
  description: string;
  confidence: number;
  severity: 'low' | 'medium' | 'high' | 'critical';
  reasoning?: string;
}

// リスク複合分析
export interface RiskCombinationAnalysis {
  combined_score: number;
  combination_type: string;
  notes: string;
}

// データ品質
export interface DataQuality {
  completeness: number;
  missing_data: string[];
  confidence_overall: number;
}

// AI分析結果
export interface AIAnalysis {
  hidden_risks: HiddenRisk[];
  risk_combination_analysis?: RiskCombinationAnalysis;
  data_quality?: DataQuality;
}

// メタデータ
export interface Metadata {
  youkai_appeared: string[];
  conversation_tone: string;
  total_turns: number;
  generation_timestamp: string;
  prompt_version: string;
}

// 妖怪応答
export interface YoukaiResponse {
  conversation: YoukaiMessage[];
  summary: Summary;
  ai_analysis: AIAnalysis;
  metadata: Metadata;
}

// 歴史的発見項目
export interface HistoricalFinding {
  category: 'terrain' | 'water' | 'development' | 'disaster';
  title: string;
  description: string;
  risk_implication: string;
  confidence: number;
  source: string;
}

// 歴史的土地利用分析
export interface HistoricalLandAnalysis {
  has_historical_data: boolean;
  terrain_type?: string;
  terrain_code?: string;
  era_analysis?: string;
  findings: HistoricalFinding[];
  summary: string;
  recommended_map_layer?: string;
}

// 近傍の自然災害伝承碑
export interface NearbyMonument {
  name: string;
  disaster_type: string;
  disaster_name: string;
  description: string;
  distance_km: number;
  lat: number;
  lng: number;
}

// 近傍の指定緊急避難場所
export interface NearbyShelter {
  name: string;
  address: string;
  disaster_types: string[];
  distance_km: number;
  lat: number;
  lng: number;
}

// ハザード応答
export interface HazardResponse {
  location: Location;
  risk_scores: RiskScore[];
  youkai_response: YoukaiResponse;
  historical_analysis?: HistoricalLandAnalysis;
  nearby_monuments?: NearbyMonument[];
  nearby_shelters?: NearbyShelter[];
  raw_data?: Record<string, unknown>;
}

// 妖怪情報
export interface YoukaiInfo {
  id: string;
  name: string;
  emoji: string;
  domain: string;
  personality: string;
  rarity: string;
}
