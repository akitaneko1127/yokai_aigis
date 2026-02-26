"""リスクスコア計算サービス"""
from typing import Dict, Any, List
from ..schemas.hazard import RiskScore
from ..models.youkai import YOUKAI_CONFIG


class RiskCalculator:
    """リスクスコア計算サービス"""

    @staticmethod
    def calculate_all_risks(hazard_data: Dict[str, Any]) -> List[RiskScore]:
        """全妖怪のリスクスコアを計算"""
        risks = []

        # 河童（水害）
        kappa_score = RiskCalculator._calculate_water_risk(hazard_data)
        risks.append(kappa_score)

        # 大ナマズ（地震）
        namazu_score = RiskCalculator._calculate_earthquake_risk(hazard_data)
        risks.append(namazu_score)

        # 土蜘蛛（土砂災害）
        tsuchigumo_score = RiskCalculator._calculate_landslide_risk(hazard_data)
        risks.append(tsuchigumo_score)

        # 天狗（風災）- 基本スコア（API未対応）
        tengu_score = RiskCalculator._calculate_wind_risk(hazard_data)
        risks.append(tengu_score)

        # 火車（火災）- 基本スコア（API未対応）
        kasha_score = RiskCalculator._calculate_fire_risk(hazard_data)
        risks.append(kasha_score)

        # 雪女（雪害）- 基本スコア（API未対応）
        yukionna_score = RiskCalculator._calculate_snow_risk(hazard_data)
        risks.append(yukionna_score)

        # ヒノカグツチ（火山）- 基本スコア（API未対応）
        hinokagutsuchi_score = RiskCalculator._calculate_volcano_risk(hazard_data)
        risks.append(hinokagutsuchi_score)

        # スコア順にソート
        risks.sort(key=lambda x: x.score, reverse=True)

        return risks

    @staticmethod
    def _calculate_water_risk(hazard_data: Dict[str, Any]) -> RiskScore:
        """水害リスクを計算（河童）"""
        youkai = YOUKAI_CONFIG["kappa"]
        score = 0
        details = {}

        # 洪水リスク
        flood = hazard_data.get("flood")
        if flood and flood.get("has_risk"):
            depth_rank = flood.get("depth_rank")
            if depth_rank:
                rank_scores = {"1": 20, "2": 35, "3": 50, "4": 65, "5": 80, "6": 95}
                score = max(score, rank_scores.get(str(depth_rank), 30))
            else:
                score = max(score, 30)
            details["flood"] = {
                "depth": flood.get("depth"),
                "river_name": flood.get("river_name")
            }

        # 津波リスク
        tsunami = hazard_data.get("tsunami")
        if tsunami and tsunami.get("has_risk"):
            depth_rank = tsunami.get("depth_rank")
            if depth_rank:
                rank_scores = {"1": 30, "2": 45, "3": 60, "4": 75, "5": 90, "6": 100}
                score = max(score, rank_scores.get(str(depth_rank), 40))
            else:
                score = max(score, 40)
            details["tsunami"] = {
                "depth": tsunami.get("depth")
            }

        # 高潮リスク
        storm_surge = hazard_data.get("storm_surge")
        if storm_surge and storm_surge.get("has_risk"):
            depth_rank = storm_surge.get("depth_rank")
            if depth_rank:
                rank_scores = {"1": 15, "2": 30, "3": 45, "4": 60, "5": 75, "6": 90}
                score = max(score, rank_scores.get(str(depth_rank), 25))
            else:
                score = max(score, 25)
            details["storm_surge"] = {
                "depth": storm_surge.get("depth")
            }

        # 内水氾濫リスク
        inland_flood = hazard_data.get("inland_flood")
        if inland_flood and inland_flood.get("has_risk"):
            depth_rank = inland_flood.get("depth_rank")
            if depth_rank:
                rank_scores = {"1": 15, "2": 25, "3": 40, "4": 55, "5": 70, "6": 85}
                score = max(score, rank_scores.get(str(depth_rank), 20))
            else:
                score = max(score, 20)
            details["inland_flood"] = {
                "depth": inland_flood.get("depth"),
                "note": "下水道の排水能力を超える大雨時に浸水リスク"
            }

        # 地形分類から過去の土地利用（旧河道、埋立地等）を考慮
        terrain = hazard_data.get("terrain")
        if terrain and terrain.get("has_data"):
            terrain_code = terrain.get("terrain_code")
            # 水に関連する地形
            water_related = ["9", "10", "12", "13", "14", "16"]  # 後背湿地、氾濫平野、旧河道、干拓地、埋立地、デルタ
            if str(terrain_code) in water_related:
                score = max(score, 35)
                if "terrain" not in details:
                    details["terrain"] = {}
                details["terrain"]["former_water"] = terrain.get("former_land_use") or "水害に注意が必要な地形"

        level = RiskCalculator._score_to_level(score)

        return RiskScore(
            youkai_id="kappa",
            youkai_name=youkai.name,
            youkai_emoji=youkai.emoji,
            score=score,
            level=level,
            details=details
        )

    @staticmethod
    def _calculate_earthquake_risk(hazard_data: Dict[str, Any]) -> RiskScore:
        """地震リスクを計算（大ナマズ）

        地震リスクの評価根拠:
        - 液状化リスクデータ（不動産情報ライブラリAPI）
        - 地形分類データから軟弱地盤を評価
        - 埋立地・旧河道は液状化リスクが極めて高い（関東大震災・東日本大震災の事例）

        注意: 活断層・プレート境界のデータは不動産情報ライブラリAPIでは提供されていないため、
        液状化・地形データを主な根拠としています。

        参考文献:
        - 国土地理院「地形分類データ」
        - 地盤工学会「液状化被害の実態」
        - 防災科研 J-SHIS（地震ハザードステーション）
        """
        youkai = YOUKAI_CONFIG["namazu"]
        score = 0  # 根拠がない場合は0から開始
        details = {}
        score_reasons = []
        data_sources = []

        # 液状化リスク（主要な評価指標）
        liquefaction = hazard_data.get("liquefaction")
        if liquefaction and liquefaction.get("has_risk"):
            risk_rank = liquefaction.get("risk_rank")
            risk_level = liquefaction.get("risk_level")
            if risk_rank:
                # 液状化リスクランクに応じたスコア
                # ランク1: 液状化の可能性が低い、ランク4: 液状化の可能性が非常に高い
                rank_scores = {"1": 25, "2": 50, "3": 75, "4": 95}
                rank_explanations = {
                    "1": "液状化の可能性が低い地盤",
                    "2": "液状化の可能性がある地盤（やや危険）",
                    "3": "液状化の可能性が高い地盤（危険）",
                    "4": "液状化の可能性が非常に高い地盤（極めて危険）"
                }
                added_score = rank_scores.get(str(risk_rank), 30)
                score = max(score, added_score)
                explanation = rank_explanations.get(str(risk_rank), f"液状化リスクランク{risk_rank}")
                score_reasons.append(f"液状化リスク「{risk_level}」: {explanation}")
                data_sources.append("不動産情報ライブラリ 液状化危険度データ")
            details["liquefaction"] = {
                "risk_level": risk_level,
                "risk_rank": risk_rank,
                "explanation": "地震時に地下水を含む砂地盤が液体のように振る舞い、建物の沈下・傾斜を引き起こす"
            }

        # 地形分類から地盤リスクを評価
        terrain = hazard_data.get("terrain")
        if terrain and terrain.get("has_data"):
            terrain_code = terrain.get("terrain_code")
            terrain_type = terrain.get("terrain_type")
            ground_condition = terrain.get("ground_condition")
            former_land_use = terrain.get("former_land_use")

            # 地形コード別の地震リスク評価（地盤工学的観点から）
            terrain_risk_map = {
                # 高リスク（軟弱地盤・人工地盤）
                "12": {"score": 80, "reason": "旧河道は液状化リスクが極めて高い（関東大震災での被害事例多数）"},
                "14": {"score": 85, "reason": "埋立地は地盤が不均質で液状化・不同沈下のリスクが極めて高い（東日本大震災での浦安市の被害等）"},
                "13": {"score": 70, "reason": "干拓地は海面より低い場所も多く、軟弱な粘土・シルト層が厚い"},
                "16": {"score": 75, "reason": "デルタ（三角州）は河川堆積物による軟弱地盤で、地震の揺れが増幅されやすい"},
                # 中リスク（沖積低地）
                "7": {"score": 60, "reason": "沖積低地は過去2万年の堆積物で地盤が軟弱、揺れが増幅されやすい"},
                "9": {"score": 55, "reason": "後背湿地は排水が悪く、軟弱な粘土層が発達"},
                "10": {"score": 50, "reason": "氾濫平野は砂質の軟弱地盤が多く、液状化リスクあり"},
                "6": {"score": 45, "reason": "低地は一般に地盤が軟弱で揺れが増幅される傾向"},
                "8": {"score": 45, "reason": "谷底低地は軟弱な堆積物が溜まりやすい"},
                # 低〜中リスク
                "3": {"score": 30, "reason": "山麓堆積地形は地盤がやや不均質な場合がある"},
                "15": {"score": 35, "reason": "砂州・砂丘は砂質地盤で液状化の可能性がある"},
                "11": {"score": 25, "reason": "自然堤防は砂質で液状化の可能性があるが比較的安定"},
                "4": {"score": 20, "reason": "火山地形は火山灰土で揺れやすいが液状化リスクは低い"},
                # 低リスク（安定地盤）
                "5": {"score": 15, "reason": "台地・段丘は古い安定した地盤で地震に強い"},
                "2": {"score": 15, "reason": "丘陵は基本的に安定した地盤（ただし切土・盛土境界に注意）"},
                "1": {"score": 10, "reason": "山地は岩盤が多く地盤は安定（ただし土砂災害に注意）"},
            }

            terrain_risk = terrain_risk_map.get(str(terrain_code))
            if terrain_risk:
                terrain_score = terrain_risk["score"]
                score = max(score, terrain_score)
                score_reasons.append(f"地形「{terrain_type}」: {terrain_risk['reason']}")
                data_sources.append("国土地理院 地形分類データ")

            details["terrain"] = {
                "type": terrain_type,
                "ground_condition": ground_condition,
                "seismic_characteristic": terrain_risk["reason"] if terrain_risk else "地盤特性は不明"
            }

            if former_land_use:
                details["terrain"]["former_land_use"] = former_land_use

        # スコア根拠をnoteに追加
        if score_reasons:
            details["note"] = "【評価根拠】\n" + "\n".join(f"・{r}" for r in score_reasons)
            details["data_sources"] = data_sources
        else:
            # データがない場合は明示的に「評価不能」とする
            score = 0
            details["note"] = "この地点の地震リスクを評価するためのデータ（液状化・地形分類）が取得できませんでした。詳細な地盤調査をお勧めします。"
            details["data_sources"] = []

        # 評価方法の説明を追加
        details["evaluation_method"] = (
            "液状化リスクデータと地形分類データを組み合わせて評価。"
            "活断層・プレート境界情報は本APIでは提供されていないため、"
            "詳細は防災科研J-SHIS（地震ハザードステーション）を参照してください。"
        )

        # 前向きなアドバイスを追加（不安を煽りすぎない）
        if score >= 60:
            details["advice"] = (
                "【地震対策のポイント】\n"
                "・免震構造や耐震等級の高い建物を選ぶことで、地震の揺れを大幅に軽減できます\n"
                "・新耐震基準（1981年以降）の建物は、大地震でも倒壊しにくい設計です\n"
                "・家具の固定、非常用品の準備など、日頃の備えが大切です\n"
                "・地盤が軟弱でも、適切な基礎工事（杭基礎など）で安全性を確保できます"
            )
        elif score >= 30:
            details["advice"] = (
                "【地震対策のポイント】\n"
                "・家具の固定や非常用品の準備など、基本的な備えをしておきましょう\n"
                "・建物を選ぶ際は、耐震等級や建築年（新耐震基準かどうか）を確認すると安心です"
            )
        else:
            details["advice"] = (
                "この地域は比較的地盤が安定していますが、"
                "家具の固定など基本的な地震対策は行っておきましょう。"
            )

        level = RiskCalculator._score_to_level(score)

        return RiskScore(
            youkai_id="namazu",
            youkai_name=youkai.name,
            youkai_emoji=youkai.emoji,
            score=score,
            level=level,
            details=details
        )

    @staticmethod
    def _calculate_landslide_risk(hazard_data: Dict[str, Any]) -> RiskScore:
        """土砂災害リスクを計算（土蜘蛛）"""
        youkai = YOUKAI_CONFIG["tsuchigumo"]
        score = 0
        details = {}

        landslide = hazard_data.get("landslide")
        if landslide and landslide.get("has_risk"):
            if landslide.get("special_warning_zone"):
                score = 85  # 特別警戒区域
                details["zone_type"] = "土砂災害特別警戒区域（レッドゾーン）"
            elif landslide.get("warning_zone"):
                score = 60  # 警戒区域
                details["zone_type"] = "土砂災害警戒区域（イエローゾーン）"
            else:
                score = 30
                details["zone_type"] = "土砂災害注意区域"

            details["landslide_type"] = landslide.get("landslide_type")

        level = RiskCalculator._score_to_level(score)

        return RiskScore(
            youkai_id="tsuchigumo",
            youkai_name=youkai.name,
            youkai_emoji=youkai.emoji,
            score=score,
            level=level,
            details=details
        )

    @staticmethod
    def _calculate_wind_risk(hazard_data: Dict[str, Any]) -> RiskScore:
        """風災リスクを計算（天狗）"""
        youkai = YOUKAI_CONFIG["tengu"]
        score = 0
        details = {}

        # 高潮データがある場合は暴風のリスク指標として加点
        storm_surge = hazard_data.get("storm_surge")
        if storm_surge and storm_surge.get("has_risk"):
            depth_rank = storm_surge.get("depth_rank")
            if depth_rank:
                rank_scores = {"1": 10, "2": 20, "3": 30, "4": 40, "5": 50, "6": 60}
                score = max(score, rank_scores.get(str(depth_rank), 15))
            else:
                score = max(score, 15)
            details["storm_surge_wind"] = {
                "note": "高潮リスクがある地域は、暴風を伴う台風の影響を受けやすい傾向があります"
            }

        if not details:
            details["note"] = (
                "この地点の風災リスクを評価するための風速データがありません。\n"
                "台風や突風への基本的な備えをお勧めします。"
            )
            details["data_sources"] = []

        details["advice"] = (
            "窓や雨戸の補強、屋外の物の固定・収納、"
            "飛来物への対策をお勧めします。"
        )

        level = RiskCalculator._score_to_level(score)

        return RiskScore(
            youkai_id="tengu",
            youkai_name=youkai.name,
            youkai_emoji=youkai.emoji,
            score=score,
            level=level,
            details=details
        )

    @staticmethod
    def _calculate_fire_risk(hazard_data: Dict[str, Any]) -> RiskScore:
        """火災リスクを計算（火車）

        火災リスクの評価根拠:
        - 液状化地域は地震後の消火活動困難（阪神淡路大震災の教訓）
        - 建物密集度や木造率のデータがないため、地形からの火災リスク推定は行わない

        注意: 地形分類（埋立地等）から「古い市街地」を推定することは不正確
        （例：お台場は埋立地だが近代的な開発地域）

        参考文献:
        - 消防庁「消防白書」延焼危険度の考え方
        - 阪神淡路大震災の火災被害分析
        """
        youkai = YOUKAI_CONFIG["kasha"]
        score = 0  # データに基づかない推定は行わない
        details = {}
        score_reasons = []

        # 液状化リスク → 地震時の火災リスク
        # 液状化地域は水道管破損により消火活動が困難になる（阪神淡路大震災の教訓）
        liquefaction = hazard_data.get("liquefaction")
        if liquefaction and liquefaction.get("has_risk"):
            risk_rank = liquefaction.get("risk_rank")
            risk_level = liquefaction.get("risk_level")
            if risk_rank and int(risk_rank) >= 3:
                # 液状化リスクが高い場合のみ、地震後の消火困難リスクを評価
                score = max(score, 20 + int(risk_rank) * 5)
                score_reasons.append(
                    f"液状化リスク「{risk_level}」: 地震時に水道管破損で消火活動が困難になる可能性"
                )
                details["liquefaction_fire_risk"] = {
                    "risk_level": risk_level,
                    "note": "液状化地域は地震後の消火活動が困難になる場合があります（阪神淡路大震災の教訓）"
                }

        # スコア根拠をnoteに追加
        if score_reasons:
            details["note"] = "【評価根拠】\n" + "\n".join(f"・{r}" for r in score_reasons)
            details["data_sources"] = ["不動産情報ライブラリ 液状化危険度データ"]
        else:
            details["note"] = (
                "この地点の火災リスクを評価するための建物密集度データがありません。\n"
                "お住まいの地域の消防署や自治体のハザードマップで確認することをお勧めします。"
            )
            details["data_sources"] = []

        # アドバイスを追加
        details["advice"] = (
            "火災対策として、住宅用火災警報器の設置、消火器の準備、"
            "避難経路の確認をお勧めします。"
        )

        level = RiskCalculator._score_to_level(score)

        return RiskScore(
            youkai_id="kasha",
            youkai_name=youkai.name,
            youkai_emoji=youkai.emoji,
            score=score,
            level=level,
            details=details
        )

    @staticmethod
    def _calculate_snow_risk(hazard_data: Dict[str, Any]) -> RiskScore:
        """雪害リスクを計算（雪女）"""
        youkai = YOUKAI_CONFIG["yukionna"]
        # 地域によって異なるため基本スコア
        score = 0
        details = {
            "note": "豪雪地帯の場合は注意が必要です"
        }

        level = RiskCalculator._score_to_level(score)

        return RiskScore(
            youkai_id="yukionna",
            youkai_name=youkai.name,
            youkai_emoji=youkai.emoji,
            score=score,
            level=level,
            details=details
        )

    @staticmethod
    def _calculate_volcano_risk(hazard_data: Dict[str, Any]) -> RiskScore:
        """火山リスクを計算（ヒノカグツチ）"""
        youkai = YOUKAI_CONFIG["hinokagutsuchi"]
        # 活火山からの距離によって異なるため基本スコア
        score = 0
        details = {
            "note": "活火山周辺の場合は注意が必要です"
        }

        level = RiskCalculator._score_to_level(score)

        return RiskScore(
            youkai_id="hinokagutsuchi",
            youkai_name=youkai.name,
            youkai_emoji=youkai.emoji,
            score=score,
            level=level,
            details=details
        )

    @staticmethod
    def _score_to_level(score: int) -> str:
        """スコアをレベルに変換"""
        if score < 30:
            return "安心"
        elif score < 60:
            return "注意"
        elif score < 85:
            return "警戒"
        else:
            return "要対策"
