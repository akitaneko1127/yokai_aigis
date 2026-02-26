"""歴史的土地利用分析サービス"""
from typing import Dict, Any, List, Optional
from ..schemas.hazard import HistoricalLandAnalysis, HistoricalFinding


# 地形分類コードと詳細な歴史的背景
TERRAIN_HISTORY = {
    "1": {
        "name": "山地",
        "era": "太古からの隆起地形",
        "history": "地殻変動により形成された安定した地形。古くから人の居住は少なく、自然災害では土砂災害に注意が必要。",
        "risk_factors": ["急傾斜地崩壊", "土石流"],
        "positive_factors": ["地盤が安定", "液状化リスク低"],
        "recommended_map": "gsi_std"
    },
    "2": {
        "name": "丘陵",
        "era": "古い地層が浸食された地形",
        "history": "比較的安定した地形だが、宅地開発による切土・盛土の境界に注意。昭和以降の開発地では地盤のばらつきあり。",
        "risk_factors": ["切土・盛土境界の不同沈下", "崖崩れ"],
        "positive_factors": ["水害リスク低", "基本的に安定した地盤"],
        "recommended_map": "gsi_ort_old"
    },
    "3": {
        "name": "山麓堆積地形",
        "era": "山から流出した土砂が堆積",
        "history": "扇状地など、過去の土石流や洪水で運ばれた土砂が堆積。古くから集落が形成されやすい地形。",
        "risk_factors": ["土石流", "地下水による液状化"],
        "positive_factors": ["水はけが良い", "比較的安定"],
        "recommended_map": "gsi_std"
    },
    "4": {
        "name": "火山地形",
        "era": "火山活動により形成",
        "history": "火山灰や溶岩で形成された地形。関東ローム層など肥沃な土地だが、火山灰土は地震時に揺れやすい特性あり。",
        "risk_factors": ["火山噴火", "地震時の揺れ増幅"],
        "positive_factors": ["水はけが良い", "液状化リスク低"],
        "recommended_map": "gsi_std"
    },
    "5": {
        "name": "台地・段丘",
        "era": "古い河川が形成した段丘面",
        "history": "数万年前の河川堆積物が隆起した安定地形。武蔵野台地など、古くから人が住み着いた良好な住宅地。",
        "risk_factors": ["台地端部のがけ崩れ"],
        "positive_factors": ["洪水リスク低", "地盤が安定", "液状化リスク低"],
        "recommended_map": "gsi_rapid"
    },
    "6": {
        "name": "低地",
        "era": "沖積平野の低い部分",
        "history": "河川の氾濫や海面上昇で形成された軟弱地盤。江戸時代以降に開発が進んだ地域が多い。",
        "risk_factors": ["洪水", "液状化", "地盤沈下"],
        "positive_factors": ["平坦で利用しやすい"],
        "recommended_map": "gsi_swale"
    },
    "7": {
        "name": "沖積低地",
        "era": "最終氷期以降に堆積した地形",
        "history": "約2万年前以降、海面上昇とともに河川が運んだ土砂が堆積。非常に軟弱な地盤で、かつては湿地や水田だったことが多い。",
        "risk_factors": ["洪水", "液状化", "地盤沈下", "地震時の揺れ増幅"],
        "positive_factors": [],
        "recommended_map": "gsi_swale"
    },
    "8": {
        "name": "谷底低地",
        "era": "山間の谷に形成された低地",
        "history": "山から流れる水が溜まりやすい地形。かつては水田として利用され、現代は住宅地として開発されていることがある。",
        "risk_factors": ["内水氾濫", "土砂災害", "軟弱地盤"],
        "positive_factors": [],
        "recommended_map": "gsi_rapid"
    },
    "9": {
        "name": "後背湿地",
        "era": "自然堤防の背後に形成された低湿地",
        "history": "河川の自然堤防の背後にできた排水の悪い湿地。かつては水田や蓮田として利用。明治〜昭和期に埋め立てられ住宅地化した場所も多い。",
        "risk_factors": ["洪水", "液状化", "地盤沈下", "内水氾濫"],
        "positive_factors": [],
        "recommended_map": "gsi_swale"
    },
    "10": {
        "name": "氾濫平野",
        "era": "河川の氾濫で形成された平野",
        "history": "繰り返す洪水で土砂が堆積した地形。肥沃な農地として利用されてきたが、洪水リスクが高い。近代の治水で住宅地化が進んだ。",
        "risk_factors": ["洪水", "液状化", "内水氾濫"],
        "positive_factors": ["平坦で利用しやすい"],
        "recommended_map": "gsi_flood"
    },
    "11": {
        "name": "自然堤防",
        "era": "河川沿いに形成された微高地",
        "history": "洪水時に河川沿いに堆積した砂質土の微高地。周囲より1〜2m高く、古くから集落や街道が発達。比較的安定した地盤。",
        "risk_factors": ["大規模洪水時の浸水"],
        "positive_factors": ["周囲より水害リスク低", "砂質で液状化リスク中程度"],
        "recommended_map": "gsi_flood"
    },
    "12": {
        "name": "旧河道",
        "era": "かつて川が流れていた跡",
        "history": "河川が流路を変えた後に残った旧い川筋。非常に軟弱な地盤で、地震時の液状化リスクが極めて高い。明治以降の地図で確認可能。",
        "risk_factors": ["液状化（極めて高い）", "地盤沈下", "不同沈下"],
        "positive_factors": [],
        "recommended_map": "konjaku_tokyo_meiji"
    },
    "13": {
        "name": "干拓地",
        "era": "海や湖沼を干拓した土地",
        "history": "江戸時代〜近代にかけて海や湖沼を堤防で囲み排水して造成。海面より低い土地も多く、堤防決壊時のリスクが高い。",
        "risk_factors": ["高潮", "洪水", "液状化", "地盤沈下"],
        "positive_factors": [],
        "recommended_map": "konjaku_tokyo_meiji"
    },
    "14": {
        "name": "埋立地",
        "era": "海や湿地を埋め立てた土地",
        "history": "明治以降、特に高度成長期に多く造成。ゴミや建設残土で埋め立てられた場所もあり、地盤の品質にばらつきが大きい。",
        "risk_factors": ["液状化（極めて高い）", "地盤沈下", "高潮", "津波"],
        "positive_factors": [],
        "recommended_map": "gsi_ort_usa"
    },
    "15": {
        "name": "砂州・砂丘",
        "era": "波や風で形成された砂地",
        "history": "海岸沿いに波や風で運ばれた砂が堆積。水はけは良いが、地震時の液状化リスクあり。津波被害を受けやすい位置にある場合も。",
        "risk_factors": ["津波", "高潮", "液状化"],
        "positive_factors": ["水はけが良い"],
        "recommended_map": "gsi_ort_old"
    },
    "16": {
        "name": "デルタ",
        "era": "河川の河口に形成された三角州",
        "history": "河川が運んだ土砂が河口に堆積して形成。広島、大阪など大都市の中心部に多い。非常に軟弱な地盤。",
        "risk_factors": ["洪水", "高潮", "液状化", "地盤沈下", "津波"],
        "positive_factors": ["平坦で利用しやすい"],
        "recommended_map": "konjaku_hiroshima_meiji"
    }
}


class HistoricalLandAnalyzer:
    """歴史的土地利用分析サービス"""

    @staticmethod
    def analyze(hazard_data: Dict[str, Any]) -> HistoricalLandAnalysis:
        """ハザードデータから歴史的土地利用を分析"""
        terrain = hazard_data.get("terrain")
        liquefaction = hazard_data.get("liquefaction")
        flood = hazard_data.get("flood")
        tsunami = hazard_data.get("tsunami")
        storm_surge = hazard_data.get("storm_surge")
        inland_flood = hazard_data.get("inland_flood")

        # 地形データがなくても、他のハザードデータから分析可能
        has_any_data = (
            (terrain and terrain.get("has_data")) or
            (liquefaction and liquefaction.get("has_risk")) or
            (flood and flood.get("has_risk")) or
            (tsunami and tsunami.get("has_risk")) or
            (storm_surge and storm_surge.get("has_risk")) or
            (inland_flood and inland_flood.get("has_risk"))
        )

        if not has_any_data:
            return HistoricalLandAnalysis(
                has_historical_data=False,
                summary="この地点のハザードデータが取得できませんでした。"
            )

        # 地形データがない場合は他のデータから推定
        if not terrain or not terrain.get("has_data"):
            return HistoricalLandAnalyzer._analyze_from_hazard_data(hazard_data)

        terrain_code = str(terrain.get("terrain_code", ""))
        terrain_type = terrain.get("terrain_type", "")
        history_info = TERRAIN_HISTORY.get(terrain_code, {})

        findings: List[HistoricalFinding] = []

        # 地形に基づく分析
        if history_info:
            findings.append(HistoricalFinding(
                category="terrain",
                title=f"地形分類: {history_info.get('name', terrain_type)}",
                description=history_info.get("history", ""),
                risk_implication=HistoricalLandAnalyzer._get_risk_implication(history_info),
                confidence=0.9,
                source="国土地理院 地形分類データ"
            ))

        # 水害履歴の分析
        water_related_codes = ["6", "7", "8", "9", "10", "12", "13", "14", "16"]
        if terrain_code in water_related_codes:
            findings.append(HistoricalFinding(
                category="water",
                title="水辺に関連する土地履歴",
                description=HistoricalLandAnalyzer._get_water_history(terrain_code),
                risk_implication="大雨や地震の際に水害・液状化リスクが高まります。",
                confidence=0.85,
                source="地形分類・治水地形分類図"
            ))

        # 埋立・干拓の分析
        if terrain_code in ["13", "14"]:
            era = "江戸時代〜明治" if terrain_code == "13" else "明治以降（特に昭和30年代〜）"
            findings.append(HistoricalFinding(
                category="development",
                title="人工的に造成された土地",
                description=f"この土地は{era}に{'干拓' if terrain_code == '13' else '埋立'}により造成されました。"
                           f"元は{'海や湖沼' if terrain_code == '13' else '海、湿地、または低地'}でした。",
                risk_implication="地盤が不安定で、液状化・地盤沈下のリスクが高いです。建物の基礎設計に注意が必要です。",
                confidence=0.9,
                source="地形分類データ"
            ))

        # 旧河道の分析
        if terrain_code == "12":
            findings.append(HistoricalFinding(
                category="water",
                title="旧河道（かつての川の跡）",
                description="この場所にはかつて川が流れていました。河川改修や流路変更により陸地化しましたが、"
                           "地下には水を含みやすい砂や泥が残っています。",
                risk_implication="地震時の液状化リスクが極めて高く、建物の不同沈下（傾き）が発生しやすい危険な地盤です。",
                confidence=0.95,
                source="地形分類データ・旧版地図"
            ))

        # 液状化データとの複合分析
        if liquefaction and liquefaction.get("has_risk"):
            risk_rank = liquefaction.get("risk_rank")
            if risk_rank and int(risk_rank) >= 3:
                findings.append(HistoricalFinding(
                    category="disaster",
                    title="液状化履歴・リスク評価",
                    description=f"この地域は液状化の可能性が{'高い' if risk_rank == '3' else '非常に高い'}と評価されています。"
                               f"過去の地形（{terrain_type}）が液状化リスクの要因となっています。",
                    risk_implication="大地震の際、地盤が液体のように流動化し、建物の沈下・傾斜、マンホールの浮上などが発生する恐れがあります。",
                    confidence=0.9,
                    source="不動産情報ライブラリ 液状化危険度"
                ))

        # 総合サマリーの生成
        summary = HistoricalLandAnalyzer._generate_summary(
            terrain_code, terrain_type, history_info, findings
        )

        return HistoricalLandAnalysis(
            has_historical_data=True,
            terrain_type=terrain_type,
            terrain_code=terrain_code,
            era_analysis=history_info.get("era", ""),
            findings=findings,
            summary=summary,
            recommended_map_layer=history_info.get("recommended_map")
        )

    @staticmethod
    def _get_risk_implication(history_info: Dict[str, Any]) -> str:
        """リスクへの影響を文字列化"""
        risk_factors = history_info.get("risk_factors", [])
        positive_factors = history_info.get("positive_factors", [])

        parts = []
        if risk_factors:
            parts.append(f"注意すべきリスク: {', '.join(risk_factors)}")
        if positive_factors:
            parts.append(f"良い点: {', '.join(positive_factors)}")

        return "。".join(parts) if parts else "特記事項なし"

    @staticmethod
    def _get_water_history(terrain_code: str) -> str:
        """水に関連する土地の歴史説明"""
        descriptions = {
            "6": "低地は河川の氾濫や海面変動で形成された低い平坦地です。水が集まりやすく、かつては湿地や水田として利用されていました。",
            "7": "沖積低地は最終氷期以降（約2万年前〜）に河川が運んだ土砂が堆積した新しい地層です。地盤が非常に軟弱で、かつては多くが湿地でした。",
            "8": "谷底低地は山間の谷に水と土砂が溜まってできた地形です。周囲から水が集まるため、内水氾濫のリスクがあります。",
            "9": "後背湿地は河川の自然堤防の背後にできた低湿地です。水はけが悪く、かつては水田や蓮田として利用されていました。",
            "10": "氾濫平野は河川の繰り返す氾濫で形成されました。肥沃な農地として利用されてきましたが、本来は洪水が前提の土地です。",
            "12": "旧河道はかつて川が流れていた場所です。河川改修や自然の流路変更により陸地化しましたが、地盤は非常に軟弱です。",
            "13": "干拓地は海や湖沼を堤防で囲み、水を排出して造った土地です。海面より低い場所も多く、堤防が決壊すると大きな被害が出ます。",
            "14": "埋立地は海、湿地、低地などを土砂やゴミで埋め立てた人工的な土地です。地盤の品質にばらつきがあり、液状化リスクが高いです。",
            "16": "デルタ（三角州）は河川が海に注ぐ河口部に土砂が堆積して形成されました。広島や大阪の中心部など、大都市に多い地形です。"
        }
        return descriptions.get(terrain_code, "水に関連した履歴のある土地です。")

    @staticmethod
    def _generate_summary(
        terrain_code: str,
        terrain_type: str,
        history_info: Dict[str, Any],
        findings: List[HistoricalFinding]
    ) -> str:
        """総合的なサマリーを生成"""
        if not history_info:
            if terrain_type:
                return f"この場所は「{terrain_type}」に分類されています。詳細は地盤調査をお勧めします。"
            else:
                return "この地点の地形分類データが取得できませんでした。他のハザードデータを参照してください。"

        risk_factors = history_info.get("risk_factors", [])
        positive_factors = history_info.get("positive_factors", [])

        # 危険度に応じたサマリー
        high_risk_codes = ["7", "9", "12", "13", "14", "16"]
        medium_risk_codes = ["6", "8", "10"]
        low_risk_codes = ["1", "2", "5"]

        if terrain_code in high_risk_codes:
            base = f"この場所は「{terrain_type}」で、**歴史的に見て災害リスクが高い土地**です。"
            detail = history_info.get("history", "")
            warning = f"特に{', '.join(risk_factors[:2])}に注意が必要です。" if risk_factors else ""
            advice = "建物の基礎設計や保険加入を慎重に検討することをお勧めします。"
        elif terrain_code in medium_risk_codes:
            base = f"この場所は「{terrain_type}」で、**一定の災害リスクがある土地**です。"
            detail = history_info.get("history", "")
            warning = f"{', '.join(risk_factors[:2])}への備えが必要です。" if risk_factors else ""
            advice = "ハザードマップを確認し、避難経路を把握しておきましょう。"
        elif terrain_code in low_risk_codes:
            base = f"この場所は「{terrain_type}」で、**比較的安定した地形**です。"
            detail = history_info.get("history", "")
            if positive_factors:
                warning = f"良い点: {', '.join(positive_factors)}。"
            else:
                warning = ""
            if risk_factors:
                advice = f"ただし、{', '.join(risk_factors[:1])}には注意してください。"
            else:
                advice = ""
        else:
            base = f"この場所は「{terrain_type}」に分類されています。"
            detail = history_info.get("history", "")
            warning = ""
            advice = "詳細は地盤調査をお勧めします。"

        return f"{base}\n\n{detail}\n\n{warning}{advice}"

    @staticmethod
    def _analyze_from_hazard_data(hazard_data: Dict[str, Any]) -> HistoricalLandAnalysis:
        """地形データがない場合、他のハザードデータから歴史を推定"""
        findings: List[HistoricalFinding] = []
        summary_parts = []
        recommended_map = "gsi_ort_old"  # デフォルトは1960年代航空写真

        liquefaction = hazard_data.get("liquefaction")
        flood = hazard_data.get("flood")
        tsunami = hazard_data.get("tsunami")
        storm_surge = hazard_data.get("storm_surge")
        inland_flood = hazard_data.get("inland_flood")

        # 液状化リスクから土地の歴史を推定
        if liquefaction and liquefaction.get("has_risk"):
            risk_rank = liquefaction.get("risk_rank")
            risk_level = liquefaction.get("risk_level", "")

            if risk_rank:
                rank_int = int(risk_rank)
                if rank_int >= 3:
                    findings.append(HistoricalFinding(
                        category="terrain",
                        title="軟弱地盤の可能性が高い土地",
                        description="液状化リスクが高いことから、この土地はかつて河川、湿地、埋立地、"
                                   "または海岸近くだった可能性があります。砂質の軟弱な地盤が地下に存在します。",
                        risk_implication="大地震の際に地盤が液状化し、建物の沈下・傾斜、ライフラインの損傷が発生する恐れがあります。",
                        confidence=0.85,
                        source="不動産情報ライブラリ 液状化危険度"
                    ))
                    summary_parts.append(f"液状化リスクが「{risk_level}」と評価されており、軟弱地盤の可能性が高いです。")
                    recommended_map = "gsi_swale"  # 低湿地マップを推奨
                elif rank_int >= 2:
                    findings.append(HistoricalFinding(
                        category="terrain",
                        title="地盤に注意が必要な土地",
                        description="液状化の可能性があることから、地盤が比較的軟弱な場所と推定されます。",
                        risk_implication="地震時に液状化が発生する可能性があります。建物の基礎設計を確認することをお勧めします。",
                        confidence=0.7,
                        source="不動産情報ライブラリ 液状化危険度"
                    ))
                    summary_parts.append(f"液状化の可能性があり（{risk_level}）、地盤に注意が必要です。")

        # 洪水リスクから土地の歴史を推定
        if flood and flood.get("has_risk"):
            depth = flood.get("depth", "")
            river_name = flood.get("river_name", "近隣の河川")

            findings.append(HistoricalFinding(
                category="water",
                title="洪水浸水想定区域",
                description=f"この場所は{river_name}の氾濫時に浸水が想定される区域です。"
                           f"歴史的に河川の氾濫が繰り返されてきた低地である可能性が高いです。",
                risk_implication=f"想定浸水深: {depth}。避難場所と避難経路の確認が重要です。",
                confidence=0.9,
                source="国土交通省 洪水浸水想定区域図"
            ))
            summary_parts.append(f"洪水浸水想定区域（想定浸水深: {depth}）に含まれています。")
            if recommended_map == "gsi_ort_old":
                recommended_map = "gsi_flood"

        # 津波リスクから土地の歴史を推定
        if tsunami and tsunami.get("has_risk"):
            depth = tsunami.get("depth", "")

            findings.append(HistoricalFinding(
                category="water",
                title="津波浸水想定区域",
                description="この場所は津波浸水が想定される区域です。海岸に近い低地、または過去に海だった可能性があります。",
                risk_implication=f"想定浸水深: {depth}。津波警報時は直ちに高台への避難が必要です。",
                confidence=0.9,
                source="国土交通省 津波浸水想定区域図"
            ))
            summary_parts.append(f"津波浸水想定区域（想定浸水深: {depth}）に含まれています。")
            recommended_map = "konjaku_tokyo_meiji"  # 海岸線の変化を確認

        # 高潮リスクから土地の歴史を推定
        if storm_surge and storm_surge.get("has_risk"):
            depth = storm_surge.get("depth", "")

            findings.append(HistoricalFinding(
                category="water",
                title="高潮浸水想定区域",
                description="この場所は高潮による浸水が想定される区域です。海抜が低く、海岸や河口に近い低地と推定されます。"
                           "埋立地や干拓地である可能性もあります。",
                risk_implication=f"想定浸水深: {depth}。台風接近時は高潮警報に注意してください。",
                confidence=0.85,
                source="国土交通省 高潮浸水想定区域図"
            ))
            summary_parts.append(f"高潮浸水想定区域（想定浸水深: {depth}）に含まれています。")

        # 内水氾濫リスクから土地の歴史を推定
        if inland_flood and inland_flood.get("has_risk"):
            depth = inland_flood.get("depth", "")

            findings.append(HistoricalFinding(
                category="water",
                title="内水浸水想定区域",
                description="この場所は下水道の排水能力を超える大雨時に浸水が想定される区域です。"
                           "周囲より低い土地、または過去に水田・湿地だった可能性があります。",
                risk_implication=f"想定浸水深: {depth}。大雨時は地下室や低い場所からの避難を。",
                confidence=0.8,
                source="国土交通省 内水浸水想定区域図"
            ))
            summary_parts.append(f"内水浸水想定区域に含まれています。")

        # サマリー生成
        if findings:
            if len(summary_parts) >= 2:
                summary = "**複数の災害リスクが確認されました。**\n\n"
                summary += "\n".join(f"・{p}" for p in summary_parts)
                summary += "\n\n歴史的に水害や地盤に関するリスクがある土地と推定されます。古い地図を確認し、土地の成り立ちを把握することをお勧めします。"
            else:
                summary = summary_parts[0] if summary_parts else "ハザードデータから土地の特性を分析しました。"
                summary += "\n\n古い地図と比較することで、土地の歴史的な変化を確認できます。"
        else:
            summary = "この地点では特筆すべき災害リスクは確認されませんでした。比較的安全な土地と推定されます。"

        return HistoricalLandAnalysis(
            has_historical_data=True,
            terrain_type=None,
            terrain_code=None,
            era_analysis="ハザードデータからの推定",
            findings=findings,
            summary=summary,
            recommended_map_layer=recommended_map
        )
