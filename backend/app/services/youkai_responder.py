"""妖怪応答生成サービス"""
import json
import logging
import random
import re
from typing import List, Dict, Any, Optional
from datetime import datetime
import uuid

from ..schemas.hazard import (
    RiskScore, YoukaiResponse, YoukaiMessage,
    Summary, MainRisk, Action, AIAnalysis, HiddenRisk,
    RiskCombinationAnalysis, DataQuality, Metadata
)
from ..models.youkai import YOUKAI_CONFIG, Youkai
from ..config import settings

logger = logging.getLogger(__name__)


def _truncate_at_sentence(text: str, max_chars: int = 120) -> str:
    """テキストを文末（。）で区切って max_chars 以内に収める。
    途中で切れることを防ぐ。"""
    if len(text) <= max_chars:
        return text
    # 句点で区切り、max_chars に収まる分だけ採用
    sentences = re.split(r'(?<=。)', text)
    result = ""
    for s in sentences:
        if not s:
            continue
        if len(result) + len(s) > max_chars:
            break
        result += s
    return result if result else text[:max_chars]


# LLM用システムプロンプト
YOUKAI_SYSTEM_PROMPT = """あなたは「妖怪ハザードマップ」の案内役AIです。
妖怪キャラクターの口調を使い、地域の災害リスクについてわかりやすく説明してください。

## 出力JSON形式
以下のJSON形式で出力してください。マークダウンフェンスや説明文は付けず、JSONのみを出力してください。

{
  "conversation": [
    {
      "speaker": "妖怪ID（kappa/namazu/tsuchigumo/tengu/kasha/yukionna/hinokagutsuchi）",
      "speaker_name": "妖怪名",
      "speaker_emoji": "絵文字",
      "emotion": "感情（friendly/warm/reassuring/relieved/calm/teaching/thinking/curious/serious/suggesting/warning）",
      "text": "セリフ"
    }
  ],
  "summary": {
    "main_risks": [{"youkai": "妖怪名", "risk_type": "リスク種別", "level": "安心/注意/警戒/要対策"}],
    "actions": [{"category": "カテゴリ", "content": "対策内容"}],
    "reassurance": "安心メッセージ"
  },
  "ai_analysis": {
    "hidden_risks": [
      {
        "id": "hr_xxxxxxxx",
        "type": "リスクタイプ",
        "title": "タイトル",
        "description": "説明",
        "confidence": 0.7,
        "severity": "low/medium/high/critical",
        "reasoning": "推論根拠"
      }
    ]
  }
}

## 妖怪キャラクター
- 河童(kappa) 🥒: 一人称「ワシ」、「〜じゃ」「〜のう」語尾、水害担当
- 大ナマズ(namazu) 🐟: 一人称「ワシ」、「〜じゃ」「〜ぞ」語尾、地震担当
- 土蜘蛛(tsuchigumo) 🕷️: 一人称「拙者」、「〜でござる」語尾、土砂災害担当
- 天狗(tengu) 🌪️: 一人称「某(それがし)」、「〜であろう」「〜ぞよ」語尾、風災担当
- 火車(kasha) 🔥: 一人称「ワガハイ」、「〜にゃ」「〜だにゃ」語尾、火災担当
- 雪女(yukionna) ❄️: 一人称「わたし」、「〜よ」「〜わ」語尾、雪害担当
- ヒノカグツチ(hinokagutsuchi) 🌋: 一人称「我」、「〜である」「〜なり」語尾、火山担当

## 重要ルール
- 各妖怪の一人称・語尾を厳守すること。「〜ます」「〜です」「〜ください」等の丁寧語は絶対に使わない。hidden_risksのdescriptionも妖怪の口調で書くこと
- 恐怖を煽らない。「死ぬ」「逃げ場がない」「住むべきではない」等の禁止表現は使わない
- 必ず安心感を持たせる表現で締める
- リスクレベルに応じた適切なトーンで話す
- 会話は3〜6ターン程度
- 伝承碑や避難場所について言及するターンは、メインの妖怪とは別の妖怪に担当させ、会話に変化を持たせること
- 必ず「避難場所」「避難経路」について具体的に言及すること（例: 最寄りの避難所の確認、複数の避難ルートの準備、家族との集合場所の取り決め等）
- actionsには必ず避難関連のアクションを含めること
- 付近の自然災害伝承碑データが提供された場合、必ず会話の中で碑の名前と伝承内容を具体的に引用し「この近くに○○という伝承碑がある。昔△△という災害があり、先人は□□と伝えている」という形で言及すること。伝承碑データがある場合に言及しないのは禁止
- 付近の避難場所データが提供された場合、必ず施設名と距離を具体的に挙げて「近くの○○（約△km）が避難場所として使える」と案内すること"""


class YoukaiResponder:
    """妖怪応答生成サービス"""

    @staticmethod
    async def generate_response_with_llm(
        risk_scores: List[RiskScore],
        location_data: Dict[str, Any] = None,
        historical_summary: str = "",
        monument_text: str = "",
    ) -> Optional[YoukaiResponse]:
        """LLMを使って妖怪応答を生成

        Returns:
            成功時はYoukaiResponse、LLM無効または失敗時はNone
        """
        if not settings.LLM_ENABLED:
            return None

        # 遅延インポート（LLM無効時にhttpx不要）
        from .llm_client import llm_client

        # 接続確認
        if not await llm_client.health_check():
            logger.warning("LLMサーバー接続不可、テンプレートモードにフォールバック")
            return None

        # 登場妖怪の決定
        active_youkai = [r for r in risk_scores if r.score >= 30][:3]
        if any(r.youkai_id == "hinokagutsuchi" for r in active_youkai):
            active_youkai = active_youkai[:2]

        # ユーザープロンプト構築
        user_prompt = YoukaiResponder._build_llm_prompt(
            risk_scores, active_youkai, location_data, historical_summary, monument_text
        )

        messages = [
            {"role": "system", "content": YOUKAI_SYSTEM_PROMPT},
            {"role": "user", "content": user_prompt},
        ]

        parsed = await llm_client.generate_json(
            messages=messages,
            max_tokens=settings.LLM_MAX_TOKENS_YOUKAI,
        )

        if parsed is None:
            logger.warning("LLM応答のJSONパース失敗、テンプレートにフォールバック")
            return None

        # パース結果をYoukaiResponseに変換
        try:
            return YoukaiResponder._parse_llm_response(parsed, active_youkai)
        except Exception as e:
            logger.warning(f"LLM応答の変換失敗: {e}")
            return None

    @staticmethod
    def _build_llm_prompt(
        risk_scores: List[RiskScore],
        active_youkai: List[RiskScore],
        location_data: Dict[str, Any] = None,
        historical_summary: str = "",
        monument_text: str = "",
    ) -> str:
        """LLMに渡すユーザープロンプトを構築"""
        parts = []

        # 位置情報
        if location_data:
            addr = location_data.get("address", "")
            lat = location_data.get("lat", "")
            lng = location_data.get("lng", "")
            parts.append(f"## 対象地点\n住所: {addr}\n緯度: {lat}, 経度: {lng}")

        # リスクスコア
        parts.append("## リスクスコア")
        for r in risk_scores:
            youkai = YOUKAI_CONFIG.get(r.youkai_id)
            name = youkai.name if youkai else r.youkai_id
            parts.append(f"- {name}({r.youkai_id}): スコア{r.score}/100 レベル:{r.level}")
            if r.details:
                details_str = json.dumps(r.details, ensure_ascii=False)
                parts.append(f"  詳細: {details_str}")

        # 登場妖怪
        if active_youkai:
            ids = [r.youkai_id for r in active_youkai]
            parts.append(f"\n## 登場させる妖怪\n{', '.join(ids)}")
            parts.append("リスクスコアが30以上の妖怪が会話に登場します。")
        else:
            parts.append("\n## 登場させる妖怪\nkappa")
            parts.append("リスクが低いため、河童が安心を伝えてください。")

        # 歴史的土地分析
        if historical_summary:
            parts.append(f"\n## 歴史的土地分析\n{historical_summary}")

        # 自然災害伝承碑・避難場所
        if monument_text:
            parts.append(f"\n{monument_text}")

        # 生成指示
        instructions = ["上記の情報に基づいて、妖怪たちの会話JSONを生成してください。"]
        if monument_text:
            instructions.append("【必須】伝承碑と避難場所のデータが上記にある場合、会話の中で必ず具体的な名前を挙げて言及してください。")
        parts.append("\n" + "\n".join(instructions))

        return "\n".join(parts)

    @staticmethod
    def _parse_llm_response(
        parsed: Dict[str, Any],
        active_youkai: List[RiskScore],
    ) -> YoukaiResponse:
        """LLMのJSON応答をYoukaiResponseに変換"""
        # conversation
        conversation = []
        for msg in parsed.get("conversation", []):
            text = msg.get("text", "")
            # テキスト内容からタグを自動判定
            tag = msg.get("tag", None)
            if not tag:
                if "伝承碑" in text or "碑" in text:
                    tag = "monument"
                elif "避難場所" in text or "避難所" in text:
                    tag = "shelter"
            conversation.append(YoukaiMessage(
                speaker=msg.get("speaker", "kappa"),
                speaker_name=msg.get("speaker_name", "河童"),
                speaker_emoji=msg.get("speaker_emoji", "🥒"),
                emotion=msg.get("emotion", "friendly"),
                text=text,
                tag=tag,
            ))

        if not conversation:
            raise ValueError("conversationが空です")

        # summary
        summary_data = parsed.get("summary", {})
        main_risks = [
            MainRisk(
                youkai=mr.get("youkai", ""),
                risk_type=mr.get("risk_type", ""),
                level=mr.get("level", "注意"),
            )
            for mr in summary_data.get("main_risks", [])
        ]
        actions = [
            Action(
                category=a.get("category", ""),
                content=a.get("content", ""),
            )
            for a in summary_data.get("actions", [])
        ]
        summary = Summary(
            main_risks=main_risks,
            actions=actions,
            reassurance=summary_data.get("reassurance", "備えがあれば安心です。"),
        )

        # ai_analysis
        analysis_data = parsed.get("ai_analysis", {})
        hidden_risks = [
            HiddenRisk(
                id=hr.get("id", f"hr_{uuid.uuid4().hex[:8]}"),
                type=hr.get("type", "複合リスク"),
                title=hr.get("title", ""),
                description=hr.get("description", ""),
                confidence=hr.get("confidence", 0.5),
                severity=hr.get("severity", "medium"),
                reasoning=hr.get("reasoning"),
            )
            for hr in analysis_data.get("hidden_risks", [])
        ]
        ai_analysis = AIAnalysis(hidden_risks=hidden_risks)

        # metadata
        youkai_ids = list({msg.speaker for msg in conversation})
        metadata = Metadata(
            youkai_appeared=youkai_ids,
            conversation_tone="reassuring",
            total_turns=len(conversation),
            generation_timestamp=datetime.now().isoformat() + "Z",
            prompt_version="v1.0-llm",
        )

        return YoukaiResponse(
            conversation=conversation,
            summary=summary,
            ai_analysis=ai_analysis,
            metadata=metadata,
        )

    @staticmethod
    def generate_response(
        risk_scores: List[RiskScore],
        location_data: Dict[str, Any] = None,
        monuments: List[Any] = None,
        shelters: List[Any] = None,
    ) -> YoukaiResponse:
        """リスクスコアに基づいてテンプレート応答を生成（フォールバック用）"""
        conversation = []
        main_risks = []
        actions = []

        # リスクスコアが30以上の妖怪を登場させる（最大3体）
        active_youkai = [r for r in risk_scores if r.score >= 30][:3]

        # ヒノカグツチがいる場合は最大2体
        if any(r.youkai_id == "hinokagutsuchi" for r in active_youkai):
            active_youkai = active_youkai[:2]

        if not active_youkai:
            # リスクがない場合は河童が挨拶
            youkai = YOUKAI_CONFIG["kappa"]
            conversation.append(YoukaiMessage(
                speaker="kappa",
                speaker_name=youkai.name,
                speaker_emoji=youkai.emoji,
                emotion="friendly",
                text="やあやあ！この土地は特に心配いらんぞ。" +
                     "基本の備えさえしておけば安心して暮らせるのじゃ。"
            ))

            # 伝承碑の言及
            monument_msgs = YoukaiResponder._generate_monument_messages(
                youkai, monuments
            )
            conversation.extend(monument_msgs)

            # 避難所の言及
            shelter_msgs = YoukaiResponder._generate_shelter_messages(
                youkai, shelters
            )
            conversation.extend(shelter_msgs)

            if not monument_msgs and not shelter_msgs:
                conversation.append(YoukaiMessage(
                    speaker="kappa",
                    speaker_name=youkai.name,
                    speaker_emoji=youkai.emoji,
                    emotion="warm",
                    text="何かあったらいつでも相談に来るんじゃぞ！"
                ))

            low_risk_actions = [Action(category="基本", content="基本的な防災準備をしておくと安心です")]
            if shelters:
                low_risk_actions.append(Action(
                    category="避難所",
                    content=f"最寄りの避難場所「{shelters[0].name}」（約{shelters[0].distance_km}km）を確認"
                ))

            return YoukaiResponse(
                conversation=conversation,
                summary=Summary(
                    main_risks=[],
                    actions=low_risk_actions,
                    reassurance="この土地は特にリスクが低いです。妖怪たちが見守っています。"
                ),
                ai_analysis=AIAnalysis(
                    hidden_risks=[],
                    data_quality=DataQuality(
                        completeness=1.0,
                        missing_data=[],
                        confidence_overall=0.9
                    )
                ),
                metadata=Metadata(
                    youkai_appeared=["kappa"],
                    conversation_tone="reassuring",
                    total_turns=1,
                    generation_timestamp=datetime.now().isoformat() + "Z",
                    prompt_version="v1.0"
                )
            )

        # メインの妖怪（最もリスクが高い）
        main_risk = active_youkai[0]
        main_youkai = YOUKAI_CONFIG[main_risk.youkai_id]

        # 1. オープニング（挨拶）
        conversation.append(YoukaiMessage(
            speaker=main_risk.youkai_id,
            speaker_name=main_youkai.name,
            speaker_emoji=main_youkai.emoji,
            emotion="friendly",
            text=main_youkai.greeting
        ))

        # 2. リスク説明
        risk_text = YoukaiResponder._generate_risk_explanation(
            main_youkai, main_risk
        )
        conversation.append(YoukaiMessage(
            speaker=main_risk.youkai_id,
            speaker_name=main_youkai.name,
            speaker_emoji=main_youkai.emoji,
            emotion="teaching",
            text=risk_text
        ))
        main_risks.append(MainRisk(
            youkai=main_youkai.name,
            risk_type=main_youkai.domain.split("（")[0],
            level=main_risk.level
        ))

        # 2体目以降の妖怪
        if len(active_youkai) > 1:
            for risk in active_youkai[1:]:
                youkai = YOUKAI_CONFIG[risk.youkai_id]
                sub_text = YoukaiResponder._generate_sub_explanation(youkai, risk)
                conversation.append(YoukaiMessage(
                    speaker=risk.youkai_id,
                    speaker_name=youkai.name,
                    speaker_emoji=youkai.emoji,
                    emotion="teaching",
                    text=sub_text
                ))
                main_risks.append(MainRisk(
                    youkai=youkai.name,
                    risk_type=youkai.domain.split("（")[0],
                    level=risk.level
                ))

        # 3. 隠れリスク発見（複合リスクがある場合）
        hidden_risks = YoukaiResponder._analyze_hidden_risks(active_youkai, location_data)
        if hidden_risks:
            hidden_comment = YoukaiResponder._generate_hidden_risk_comment(
                main_youkai, hidden_risks[0]
            )
            conversation.append(YoukaiMessage(
                speaker=main_risk.youkai_id,
                speaker_name=main_youkai.name,
                speaker_emoji=main_youkai.emoji,
                emotion="thinking",
                text=hidden_comment
            ))

        # 伝承碑・避難所の担当妖怪を決定（出番が少ない妖怪を優先）
        monument_youkai_id, shelter_youkai_id = YoukaiResponder._pick_rare_youkai_pair(
            main_risk.youkai_id
        )
        monument_youkai = YOUKAI_CONFIG[monument_youkai_id]
        shelter_youkai = YOUKAI_CONFIG[shelter_youkai_id]

        # 4. 伝承碑の言及（メイン以外の妖怪が担当）
        monument_msgs = YoukaiResponder._generate_monument_messages(
            monument_youkai, monuments
        )
        conversation.extend(monument_msgs)

        # 5. 対策提案 + 避難所の言及（さらに別の妖怪が担当）
        advice_text = YoukaiResponder._generate_advice(main_youkai, main_risk)
        conversation.append(YoukaiMessage(
            speaker=main_risk.youkai_id,
            speaker_name=main_youkai.name,
            speaker_emoji=main_youkai.emoji,
            emotion="suggesting",
            text=advice_text
        ))
        actions.extend(YoukaiResponder._get_actions(active_youkai))

        shelter_msgs = YoukaiResponder._generate_shelter_messages(
            shelter_youkai, shelters
        )
        conversation.extend(shelter_msgs)

        # 避難所アクション追加
        if shelters:
            actions.insert(0, Action(
                category="避難所",
                content=f"最寄りの避難場所「{shelters[0].name}」（約{shelters[0].distance_km}km）を確認"
            ))

        # 6. クロージング（安心メッセージ）
        reassure_text = YoukaiResponder._generate_reassurance(
            main_youkai, main_risk, len(active_youkai) > 1
        )
        conversation.append(YoukaiMessage(
            speaker=main_risk.youkai_id,
            speaker_name=main_youkai.name,
            speaker_emoji=main_youkai.emoji,
            emotion="warm",
            text=reassure_text
        ))

        # リスク複合分析
        risk_combination = YoukaiResponder._analyze_risk_combination(active_youkai)

        # 応答を構築
        return YoukaiResponse(
            conversation=conversation,
            summary=Summary(
                main_risks=main_risks,
                actions=actions,
                reassurance="備えがあれば安心して暮らせます。妖怪たちが見守っています。"
            ),
            ai_analysis=AIAnalysis(
                hidden_risks=hidden_risks,
                risk_combination_analysis=risk_combination,
                data_quality=DataQuality(
                    completeness=0.85,
                    missing_data=["詳細な地盤データ"] if any(r.youkai_id == "namazu" for r in active_youkai) else [],
                    confidence_overall=0.78
                )
            ),
            metadata=Metadata(
                youkai_appeared=list(dict.fromkeys(
                    [r.youkai_id for r in active_youkai]
                    + ([monument_youkai_id] if monument_msgs else [])
                    + ([shelter_youkai_id] if shelter_msgs else [])
                )),
                conversation_tone="reassuring",
                total_turns=len(conversation),
                generation_timestamp=datetime.now().isoformat() + "Z",
                prompt_version="v1.0"
            )
        )

    @staticmethod
    def supplement_monument_shelter(
        response: YoukaiResponse,
        risk_scores: List[RiskScore],
        monuments: List[Any] = None,
        shelters: List[Any] = None,
    ) -> YoukaiResponse:
        """LLM応答に伝承碑・避難所の言及がない場合、テンプレートメッセージを補完"""
        if not monuments and not shelters:
            return response

        # LLM応答のテキストを結合して伝承碑・避難所の言及があるか確認
        all_text = " ".join(msg.text for msg in response.conversation)

        # 担当妖怪を決定（出番が少ない妖怪を優先）
        active_youkai = [r for r in risk_scores if r.score >= 30][:3]
        main_id = active_youkai[0].youkai_id if active_youkai else "kappa"

        monument_youkai_id, shelter_youkai_id = YoukaiResponder._pick_rare_youkai_pair(
            main_id
        )
        monument_youkai = YOUKAI_CONFIG[monument_youkai_id]
        shelter_youkai = YOUKAI_CONFIG[shelter_youkai_id]

        # 伝承碑の補完
        has_monument = any(msg.tag == "monument" for msg in response.conversation) or "伝承碑" in all_text
        if monuments and not has_monument:
            logger.info("LLM応答に伝承碑の言及なし → テンプレートで補完（%s）", monument_youkai.name)
            monument_msgs = YoukaiResponder._generate_monument_messages(monument_youkai, monuments)
            insert_pos = max(0, len(response.conversation) - 1)
            for i, msg in enumerate(monument_msgs):
                response.conversation.insert(insert_pos + i, msg)

        # 避難所の補完
        has_shelter = any(msg.tag == "shelter" for msg in response.conversation) or "避難場所" in all_text or "避難所" in all_text
        if shelters and not has_shelter:
            logger.info("LLM応答に避難所の言及なし → テンプレートで補完（%s）", shelter_youkai.name)
            shelter_msgs = YoukaiResponder._generate_shelter_messages(shelter_youkai, shelters)
            insert_pos = max(0, len(response.conversation) - 1)
            for i, msg in enumerate(shelter_msgs):
                response.conversation.insert(insert_pos + i, msg)

        # メタデータ更新
        response.metadata.total_turns = len(response.conversation)

        return response

    # 出番が少ない妖怪（伝承碑・避難所で優先的に出す）
    _RARE_YOUKAI_IDS = ["tengu", "yukionna", "tsuchigumo", "hinokagutsuchi"]

    @staticmethod
    def _pick_rare_youkai_pair(exclude_id: str) -> tuple:
        """伝承碑・避難所の担当妖怪を選ぶ（出番が少ない妖怪を優先）

        Returns:
            (monument_youkai_id, shelter_youkai_id)
        """
        # 出番が少ない妖怪プールからメインを除外
        pool = [yid for yid in YoukaiResponder._RARE_YOUKAI_IDS if yid != exclude_id]
        random.shuffle(pool)

        if len(pool) >= 2:
            return pool[0], pool[1]
        elif len(pool) == 1:
            # メインが rare 妖怪の1体だった場合、残り1体 + 他から選ぶ
            fallback = [yid for yid in list(YOUKAI_CONFIG.keys())
                        if yid != exclude_id and yid != pool[0]]
            return pool[0], random.choice(fallback)
        else:
            # ありえないが安全策
            others = [yid for yid in list(YOUKAI_CONFIG.keys()) if yid != exclude_id]
            random.shuffle(others)
            return others[0], others[1]

    @staticmethod
    def _generate_risk_explanation(youkai: Youkai, risk: RiskScore) -> str:
        """リスク説明を生成"""
        if risk.level == "安心":
            return f"この土地は{youkai.domain}についてはあまり心配いらんぞ。" + \
                   "でも、基本の備えはしておくとよいのじゃ。"

        elif risk.level == "注意":
            details = risk.details
            text = youkai.explain_risk

            if risk.youkai_id == "kappa" and "flood" in details:
                flood = details["flood"]
                if flood.get("depth"):
                    text += f" 浸水想定は{flood['depth']}くらいじゃな。"

            return text

        elif risk.level == "警戒":
            base = youkai.explain_risk

            if risk.youkai_id == "kappa":
                base = "この辺りは水害に気をつけた方がよいのじゃ。" + \
                       "でもな、知っておけば備えられるからの。"

            elif risk.youkai_id == "tsuchigumo":
                details = risk.details
                if details.get("zone_type"):
                    base = f"この地は{details['zone_type']}に入っておるでござる。" + \
                           "大雨の時は特に注意が必要じゃな。"

            return base

        else:  # 要対策
            if risk.youkai_id == "kappa":
                return "この土地は水害への備えをしっかりしておく必要があるのじゃ。" + \
                       "でもな、準備さえしておけば大丈夫じゃ。一緒に確認しようかの。"

            elif risk.youkai_id == "tsuchigumo":
                return "この地は土砂災害への備えが重要でござる。" + \
                       "されど、恐れることはない。知識と備えがあれば安心じゃ。"

            return youkai.explain_risk

    @staticmethod
    def _generate_sub_explanation(youkai: Youkai, risk: RiskScore) -> str:
        """サブ妖怪の説明を生成"""
        if risk.level == "安心":
            return f"{youkai.first_person}の担当する{youkai.domain}は心配いらんぞ。"

        elif risk.level == "注意":
            if youkai.id == "namazu":
                return "ワシからも一言じゃ。地震への備えも少し考えておくとよいぞ。" + \
                       "家具の固定くらいはしておくと安心じゃ。"

            elif youkai.id == "tsuchigumo":
                return "...拙者からも。山や崖からは少し距離を取るがよい。" + \
                       "念のためでござる。"

            return f"{youkai.first_person}からも少し。{youkai.explain_risk}"

        else:
            return f"{youkai.first_person}からも伝えておこう。{youkai.explain_risk}"

    @staticmethod
    def _generate_advice(youkai: Youkai, risk: RiskScore) -> str:
        """対策提案を生成"""
        return youkai.give_advice

    @staticmethod
    def _generate_reassurance(
        youkai: Youkai, risk: RiskScore, has_others: bool
    ) -> str:
        """安心メッセージを生成"""
        if has_others:
            return f"{youkai.reassure} ワシらが見守っておるからの、安心して暮らすがよいぞ！"
        else:
            return youkai.reassure + " " + youkai.farewell

    @staticmethod
    def _analyze_hidden_risks(
        active_youkai: List[RiskScore],
        location_data: Dict[str, Any] = None
    ) -> List[HiddenRisk]:
        """隠れリスク（複合リスク）を分析"""
        hidden_risks = []

        youkai_ids = [r.youkai_id for r in active_youkai]

        # 水害 × 地震 の複合リスク
        if "kappa" in youkai_ids and "namazu" in youkai_ids:
            hidden_risks.append(HiddenRisk(
                id=f"hr_{uuid.uuid4().hex[:8]}",
                type="時系列リスク",
                title="地震後の津波・液状化複合リスク",
                description="地震で液状化が起きると避難経路が通れなくなることがある。津波にも備えて複数の避難ルートを確認しておくとよい",
                confidence=0.72,
                severity="medium",
                reasoning="水害リスクエリア + 液状化リスクの重複"
            ))

        # 水害 × 土砂災害 の複合リスク
        if "kappa" in youkai_ids and "tsuchigumo" in youkai_ids:
            hidden_risks.append(HiddenRisk(
                id=f"hr_{uuid.uuid4().hex[:8]}",
                type="複合地域リスク",
                title="大雨による水害・土砂災害の同時発生リスク",
                description="大雨の時は洪水と土砂災害が同時に起きることがある。警報の種類に関わらず早めの避難が大事",
                confidence=0.68,
                severity="medium",
                reasoning="水害リスク + 土砂災害リスクの重複地域"
            ))

        # 水害 × 風災 の複合リスク（台風時）
        if "kappa" in youkai_ids and "tengu" in youkai_ids:
            hidden_risks.append(HiddenRisk(
                id=f"hr_{uuid.uuid4().hex[:8]}",
                type="複合気象リスク",
                title="台風時の水害×暴風複合リスク",
                description="台風の時は暴風と大雨が同時に来て、水害と風災が重なることがある。早めの避難と窓の補強・浸水対策の両方が大事",
                confidence=0.70,
                severity="medium",
                reasoning="水害リスクエリア + 暴風リスクの重複"
            ))

        # 地震 × 火災 の複合リスク
        if "namazu" in youkai_ids and "kasha" in youkai_ids:
            kasha_risk = next((r for r in active_youkai if r.youkai_id == "kasha"), None)
            if kasha_risk and kasha_risk.score >= 30:
                hidden_risks.append(HiddenRisk(
                    id=f"hr_{uuid.uuid4().hex[:8]}",
                    type="時系列リスク",
                    title="地震後の火災発生リスク",
                    description="地震の後はガス漏れや電気系統のショートで火災が起きることがある。揺れが収まったらガスの元栓とブレーカーを確認すること",
                    confidence=0.65,
                    severity="medium",
                    reasoning="地震リスク + 建物密集地域"
                ))

        return hidden_risks

    @staticmethod
    def _rephrase_for_youkai(youkai_id: str, description: str) -> str:
        """丁寧語の説明文を妖怪の口調に変換する"""
        text = description.split("。")[0]
        # 丁寧語→妖怪口調の変換
        replacements = {
            "kappa": [
                ("可能性があります", "かもしれんのじゃ"),
                ("お勧めします", "勧めるぞ"),
                ("ください", "おくれ"),
                ("確認しておく", "確認しておく"),
            ],
            "namazu": [
                ("可能性があります", "かもしれんのじゃ"),
                ("お勧めします", "勧めるぞ"),
                ("ください", "くれ"),
            ],
            "tsuchigumo": [
                ("可能性があります", "可能性があるでござる"),
                ("お勧めします", "勧めるでござる"),
                ("ください", "くだされ"),
            ],
            "tengu": [
                ("可能性があります", "可能性があろう"),
                ("お勧めします", "勧めるぞよ"),
                ("ください", "おくれ"),
            ],
            "kasha": [
                ("可能性があります", "かもしれないにゃ"),
                ("お勧めします", "勧めるにゃ"),
                ("ください", "おくれにゃ"),
            ],
            "yukionna": [
                ("可能性があります", "可能性があるの"),
                ("お勧めします", "勧めるわ"),
                ("ください", "ちょうだいね"),
            ],
        }
        for old, new in replacements.get(youkai_id, []):
            text = text.replace(old, new)
        return text

    @staticmethod
    def _generate_hidden_risk_comment(youkai: Youkai, hidden_risk: HiddenRisk) -> str:
        """隠れリスクについての妖怪コメントを生成"""
        desc = hidden_risk.description.split("。")[0].rstrip("。")

        if youkai.id == "kappa":
            return f"ふむ、もう一つ知っておくとよいことがあるぞ。{desc}のじゃ。念のため確認しておこうかの。"
        elif youkai.id == "namazu":
            return f"ふむ、もう一つ知っておくとよいことがあるぞ。{desc}のじゃ。備えておくと安心じゃ。"
        elif youkai.id == "tsuchigumo":
            return f"...気づいたことがあるでござる。{desc}でござる。心得ておくがよいでござるな。"
        elif youkai.id == "tengu":
            return f"ふん、もう一つ伝えておこう。{desc}であろう。心得ておくがよいぞよ。"
        elif youkai.id == "kasha":
            return f"ふむ、もう一つ伝えておくにゃ。{desc}にゃ。気をつけるにゃ。"
        elif youkai.id == "yukionna":
            return f"もう一つ伝えておくわね。{desc}の。覚えておいてね。"
        else:
            return f"もう一つ知っておくとよいことがある。{desc}である。"

    @staticmethod
    def _analyze_risk_combination(active_youkai: List[RiskScore]) -> RiskCombinationAnalysis:
        """リスク複合分析"""
        if len(active_youkai) < 2:
            return None

        max_score = max(r.score for r in active_youkai)
        combination_type = " × ".join([
            YOUKAI_CONFIG[r.youkai_id].domain.split("（")[0]
            for r in active_youkai
        ])

        combined_score = min(100, max_score + sum(r.score for r in active_youkai[1:]) // 3)

        notes = f"{combination_type}が同時に存在するエリアです。" + \
                "それぞれのリスクに対する備えを行い、複合災害にも注意してください。"

        return RiskCombinationAnalysis(
            combined_score=combined_score,
            combination_type=combination_type,
            notes=notes
        )

    @staticmethod
    def _get_actions(active_youkai: List[RiskScore]) -> List[Action]:
        """対策リストを取得"""
        actions_config = {
            "kappa": [
                Action(category="避難所", content="ハザードマップで避難所・避難経路を確認"),
                Action(category="準備品", content="非常用持ち出し袋の準備"),
                Action(category="情報", content="気象情報をこまめにチェック")
            ],
            "namazu": [
                Action(category="家具", content="家具の固定・転倒防止"),
                Action(category="避難所", content="避難経路の確認"),
                Action(category="準備品", content="非常用持ち出し袋の準備")
            ],
            "tsuchigumo": [
                Action(category="確認", content="崖・斜面からの距離を確認"),
                Action(category="避難所", content="避難場所・経路の確認"),
                Action(category="判断", content="大雨時の避難判断基準を確認")
            ],
            "tengu": [
                Action(category="補強", content="窓・雨戸・シャッターの補強"),
                Action(category="対策", content="屋外の物を固定または収納"),
                Action(category="避難所", content="暴風時の避難場所・経路を確認")
            ],
            "kasha": [
                Action(category="確認", content="消火器の設置場所を確認"),
                Action(category="避難所", content="避難経路を2つ以上確保"),
                Action(category="習慣", content="火の元の確認を習慣化")
            ],
            "yukionna": [
                Action(category="安全", content="雪下ろしは複数人で"),
                Action(category="準備品", content="除雪用具の準備"),
                Action(category="点検", content="暖房器具の点検")
            ],
            "hinokagutsuchi": [
                Action(category="避難所", content="避難経路・避難場所の確認"),
                Action(category="情報", content="火山情報のチェック方法を確認"),
                Action(category="準備品", content="マスク・ゴーグルの準備")
            ]
        }

        result = []
        for risk in active_youkai:
            if risk.youkai_id in actions_config:
                result.extend(actions_config[risk.youkai_id])

        # 重複を除去
        seen = set()
        unique_actions = []
        for action in result:
            key = (action.category, action.content)
            if key not in seen:
                seen.add(key)
                unique_actions.append(action)

        return unique_actions

    @staticmethod
    def _generate_monument_messages(
        youkai: Youkai, monuments: List[Any] = None
    ) -> List[YoukaiMessage]:
        """伝承碑に関する会話メッセージを生成"""
        if not monuments:
            return []

        messages = []
        m = monuments[0]  # 最も近い伝承碑

        # 妖怪ごとの口調
        if youkai.id == "kappa":
            text = (
                f"そうじゃ、一つ大事なことを教えようかの。"
                f"この近くに「{m.name}」という自然災害伝承碑があるのじゃ。"
            )
            if m.disaster_name:
                text += f"「{m.disaster_name}」という災害を伝えておるぞ。"
            desc = _truncate_at_sentence(m.description, 200) if m.description else ""
            if desc:
                text += f"先人の教えによれば、{desc}"
        elif youkai.id == "namazu":
            text = (
                f"ワシからも伝えておくことがあるぞ。"
                f"ここから約{m.distance_km}kmの場所に「{m.name}」という伝承碑が立っておる。"
            )
            if m.disaster_name:
                text += f"昔、「{m.disaster_name}」があったことを伝えておるのじゃ。"
            desc = _truncate_at_sentence(m.description, 200) if m.description else ""
            if desc:
                text += f"その教訓は、{desc}"
        elif youkai.id == "tsuchigumo":
            text = (
                f"...拙者から一つ。この付近に「{m.name}」という自然災害伝承碑があるでござる。"
            )
            if m.disaster_name:
                text += f"「{m.disaster_name}」を後世に伝えるものでござるな。"
            desc = _truncate_at_sentence(m.description, 200) if m.description else ""
            if desc:
                text += f"碑にはこう記されておる。{desc}"
        elif youkai.id == "tengu":
            text = (
                f"某からも伝えておこう。"
                f"この近くに「{m.name}」という自然災害伝承碑があるぞよ。"
            )
            if m.disaster_name:
                text += f"「{m.disaster_name}」の記憶を留めておるのじゃ。"
            desc = m.description if m.description else ""
            if desc:
                text += f"先人の教えによれば、{desc}"
        elif youkai.id == "kasha":
            text = (
                f"ワガハイも知っておるにゃ。"
                f"この近くに「{m.name}」という伝承碑があるにゃ。"
            )
            if m.disaster_name:
                text += f"「{m.disaster_name}」のことを伝えておるにゃ。"
            desc = _truncate_at_sentence(m.description, 200) if m.description else ""
            if desc:
                text += f"先人はこう言っておるにゃ。{desc}"
        elif youkai.id == "yukionna":
            text = (
                f"わたしからも伝えておくわ。"
                f"この近くには「{m.name}」という自然災害伝承碑があるの。"
            )
            if m.disaster_name:
                text += f"「{m.disaster_name}」の記憶を残しているのよ。"
            desc = _truncate_at_sentence(m.description, 200) if m.description else ""
            if desc:
                text += f"先人たちの教えでは、{desc}"
        else:
            text = (
                f"この付近に「{m.name}」という自然災害伝承碑が存在する。"
            )
            if m.disaster_name:
                text += f"「{m.disaster_name}」を後世に伝えるものである。"
            desc = _truncate_at_sentence(m.description, 200) if m.description else ""
            if desc:
                text += f"碑には次のようにある。{desc}"

        messages.append(YoukaiMessage(
            speaker=youkai.id,
            speaker_name=youkai.name,
            speaker_emoji=youkai.emoji,
            emotion="calm",
            text=text,
            tag="monument",
        ))

        return messages

    @staticmethod
    def _generate_shelter_messages(
        youkai: Youkai, shelters: List[Any] = None
    ) -> List[YoukaiMessage]:
        """避難所に関する会話メッセージを生成"""
        if not shelters:
            return []

        messages = []
        s = shelters[0]  # 最も近い避難所
        types_str = "・".join(s.disaster_types[:3]) if s.disaster_types else ""

        if youkai.id == "kappa":
            text = (
                f"それとな、いざという時のために教えておくぞ。"
                f"近くの「{s.name}」が避難場所として使えるのじゃ。"
                f"ここから約{s.distance_km}kmじゃ。"
            )
            if types_str:
                text += f"{types_str}に対応しておるぞ。"
            text += "事前に場所を確認しておくとよいのう。"
        elif youkai.id == "namazu":
            text = (
                f"避難場所も確認しておくのじゃ。"
                f"近くの「{s.name}」が約{s.distance_km}kmのところにあるぞ。"
            )
            if types_str:
                text += f"{types_str}の際に利用できるのじゃ。"
            text += "家族との集合場所も決めておくとよいぞ。"
        elif youkai.id == "tsuchigumo":
            text = (
                f"避難場所でござるが、「{s.name}」が約{s.distance_km}kmの距離にあるでござる。"
            )
            if types_str:
                text += f"{types_str}に対応した避難場所でござる。"
            text += "複数の避難経路を確認しておくことを勧めるでござる。"
        elif youkai.id == "tengu":
            text = (
                f"避難場所も心得ておくがよい。"
                f"「{s.name}」が約{s.distance_km}kmの場所にあるぞよ。"
            )
            if types_str:
                text += f"{types_str}の際に利用できるであろう。"
            text += "風が強まる前に避難するのが肝要じゃ。"
        elif youkai.id == "kasha":
            text = (
                f"避難場所も知っておくにゃ。"
                f"「{s.name}」が約{s.distance_km}kmにあるにゃ。"
            )
            if types_str:
                text += f"{types_str}の時に使えるにゃ。"
            text += "いざという時に慌てないよう、場所を覚えておくにゃ。"
        elif youkai.id == "yukionna":
            text = (
                f"避難場所も確認しておいてね。"
                f"近くの「{s.name}」が約{s.distance_km}kmのところにあるわ。"
            )
            if types_str:
                text += f"{types_str}の際に利用できるの。"
            text += "事前に行き方を確認しておくと安心よ。"
        else:
            text = (
                f"避難場所として「{s.name}」が約{s.distance_km}kmの場所にある。"
            )
            if types_str:
                text += f"{types_str}に対応している。"
            text += "事前に確認しておくがよい。"

        # 2件目以降があれば補足
        if len(shelters) > 1:
            other_names = "、".join(f"「{sh.name}」" for sh in shelters[1:3])
            text += f" ほかにも{other_names}も近くにあるぞ。"

        messages.append(YoukaiMessage(
            speaker=youkai.id,
            speaker_name=youkai.name,
            speaker_emoji=youkai.emoji,
            emotion="friendly",
            text=text,
            tag="shelter",
        ))

        return messages
