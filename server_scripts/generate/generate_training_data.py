#!/usr/bin/env python3
"""
妖怪ハザードマップ 教師データ生成スクリプト
Qwen3-32B (vLLM) を使用して全12カテゴリ142,000件の教師データを生成

使用方法:
  python generate_training_data.py --config ../configs/generation_config.yaml
  python generate_training_data.py --config ../configs/generation_config.yaml --category cat1_basic --count 100
  python generate_training_data.py --config ../configs/generation_config.yaml --category cat1_basic --resume
"""

import argparse
import asyncio
import json
import os
import random
import re
import sys
import time
from datetime import datetime
from pathlib import Path
from typing import Any, Optional

import aiohttp
import yaml
from tqdm import tqdm

# ============================================================
# 共通システムプロンプト
# ============================================================

SYSTEM_PROMPT = """あなたは「妖怪ハザードマップ」の学習データ生成AIです。
日本の伝統的な妖怪たちが、土地の災害リスクについて住民に優しく知恵を授ける会話データを生成してください。

# 基本理念

妖怪たちは「恐怖の象徴」ではなく【土地の守り神】です。
長年その土地に住み、土地の特徴を熟知した「優しい先輩住民」として振る舞います。

目的：
1. 住民に土地の特徴を「知識」として伝える
2. 具体的な備えを「一緒に確認しよう」と提案する
3. 「知っていれば怖くない」という安心感を与える
4. 人間が気づきにくい複合リスクを発見して伝える

# 表現のガイドライン

## 避けてほしい表現の方向性
以下のような表現は、住民に不安を与えるため使わないようにしてください。
代わりに、知識として伝え、備えを促す前向きな表現を使ってください。

1. 不安を煽る方向の表現 → 「知っておくと安心」の方向へ
   - 「逃げ場がない」→「避難経路を複数確認しておくと安心じゃ」
   - 「住むべきではない」→「この土地ならではの備えを一緒に確認しよう」
   - 「死ぬぞ」→「身の安全を守る行動を確認しておこう」
2. 過去の災害の数字や被害の詳細 → 教訓として何を学ぶかに焦点を当てる
   - 「○人が犠牲になった」→「過去の経験から学んで、今はしっかり対策が取られておる」
3. 断定的に否定する表現 → 具体的な備えの提案へ
   - 「この土地は最悪」→「この土地にはいくつか気をつけるとよい点がある」
4. 不安な気持ちのまま終わる → 必ず安心感や前向きな言葉で結ぶ

※ 行政用語（「土砂災害警戒区域」「浸水想定区域」等）はそのまま正確に使ってください。
※ 自然災害伝承碑の内容を参照する場合も、教訓と備えに焦点を当ててください。

## 推奨表現
| 状況 | 推奨表現 |
|------|----------|
| リスクを伝える時 | 「〜に気をつけるとよいぞ」「〜を知っておくと安心じゃ」 |
| 備えを促す時 | 「一緒に確認しておこうかの」「これを準備しておくとよいぞ」 |
| 安心させる時 | 「知っていれば怖くないぞ」「備えがあれば大丈夫じゃ」 |
| 締めくくり | 「ワシらが見守っておるからの」「お主なら大丈夫じゃ」 |

# リスクレベル別の表現トーン
| レベル | スコア | トーン |
|--------|--------|--------|
| 安心 | 0-30% | のんびり、雑談風 |
| 注意 | 30-60% | 丁寧に説明 |
| 警戒 | 60-85% | しっかり具体的に |
| 要対策 | 85%+ | 真剣だが希望を持たせる |

出力は必ず有効なJSON形式で返してください。JSON以外のテキストは含めないでください。
"""

# ============================================================
# リスクレベル定義
# ============================================================

RISK_LEVELS = {
    "安心": (0, 30),
    "注意": (30, 60),
    "警戒": (60, 85),
    "要対策": (85, 100),
}

# ============================================================
# 地域別サンプルデータ
# ============================================================

SAMPLE_LOCATIONS = {
    "tokyo": [
        {"address": "東京都江東区豊洲", "lat": 35.6547, "lng": 139.7932, "elevation": 2.0, "terrain": "埋立地", "chars": ["低地", "海抜2m以下", "河川近傍"]},
        {"address": "東京都墨田区押上", "lat": 35.7101, "lng": 139.8107, "elevation": 1.5, "terrain": "低地", "chars": ["海抜0m地帯", "河川近傍"]},
        {"address": "東京都荒川区南千住", "lat": 35.7353, "lng": 139.8012, "elevation": 2.5, "terrain": "低地", "chars": ["河川近傍", "木造密集"]},
        {"address": "東京都世田谷区成城", "lat": 35.6413, "lng": 139.5972, "elevation": 35.0, "terrain": "台地", "chars": ["台地上", "崖線沿い"]},
        {"address": "東京都港区芝浦", "lat": 35.6359, "lng": 139.7507, "elevation": 3.0, "terrain": "埋立地", "chars": ["湾岸", "高潮リスク"]},
        {"address": "東京都大田区蒲田", "lat": 35.5625, "lng": 139.7162, "elevation": 4.0, "terrain": "低地", "chars": ["多摩川近傍", "住宅密集"]},
        {"address": "東京都足立区綾瀬", "lat": 35.7627, "lng": 139.8267, "elevation": 1.0, "terrain": "低地", "chars": ["海抜0m地帯", "河川氾濫リスク"]},
        {"address": "東京都新宿区歌舞伎町", "lat": 35.6938, "lng": 139.7034, "elevation": 30.0, "terrain": "丘陵地", "chars": ["繁華街", "火災リスク", "帰宅困難"]},
    ],
    "sendai": [
        {"address": "仙台市宮城野区岡田", "lat": 38.2519, "lng": 140.9782, "elevation": 2.0, "terrain": "沿岸部", "chars": ["沿岸部", "津波リスク"]},
        {"address": "仙台市若林区荒浜", "lat": 38.2206, "lng": 140.9607, "elevation": 1.5, "terrain": "沿岸部", "chars": ["沿岸低地", "津波浸水域"]},
        {"address": "仙台市青葉区八幡", "lat": 38.2659, "lng": 140.8537, "elevation": 50.0, "terrain": "丘陵地", "chars": ["丘陵地", "地すべり注意"]},
        {"address": "仙台市太白区長町", "lat": 38.2278, "lng": 140.8757, "elevation": 10.0, "terrain": "河川近傍", "chars": ["広瀬川近傍", "洪水リスク"]},
    ],
    "akita": [
        {"address": "秋田県秋田市土崎港", "lat": 39.7570, "lng": 140.0764, "elevation": 5.0, "terrain": "沿岸部", "chars": ["日本海側", "冬季風雪"]},
        {"address": "秋田県横手市", "lat": 39.3116, "lng": 140.5566, "elevation": 60.0, "terrain": "盆地", "chars": ["豪雪地帯", "内陸盆地"]},
        {"address": "秋田県由利本荘市", "lat": 39.3863, "lng": 140.0493, "elevation": 10.0, "terrain": "河川近傍", "chars": ["子吉川流域", "洪水リスク"]},
        {"address": "秋田県湯沢市", "lat": 39.1645, "lng": 140.4938, "elevation": 120.0, "terrain": "山間部", "chars": ["特別豪雪地帯", "山間部"]},
    ],
}

# ============================================================
# ユーティリティ
# ============================================================

def load_config(config_path: str) -> dict:
    with open(config_path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)


def random_risk_score(youkai_id: str, terrain: str) -> dict:
    """地形に基づいてリスクスコアをランダム生成"""
    # 地形とリスクの相関
    terrain_risk_bias = {
        "沿岸部": {"kappa": 70, "namazu": 40, "tsuchigumo": 10},
        "河川近傍": {"kappa": 65, "namazu": 30, "tsuchigumo": 15},
        "埋立地": {"kappa": 60, "namazu": 70, "tsuchigumo": 5},
        "斜面地": {"kappa": 20, "namazu": 30, "tsuchigumo": 70},
        "低地": {"kappa": 75, "namazu": 50, "tsuchigumo": 5},
        "山間部": {"kappa": 30, "namazu": 20, "tsuchigumo": 60, "yukionna": 50},
        "盆地": {"kappa": 40, "namazu": 30, "yukionna": 60},
        "台地": {"kappa": 15, "namazu": 25, "tsuchigumo": 20},
        "丘陵地": {"kappa": 20, "namazu": 25, "tsuchigumo": 40},
        "平野部": {"kappa": 50, "namazu": 35, "tsuchigumo": 10},
    }
    bias = terrain_risk_bias.get(terrain, {})
    base = bias.get(youkai_id, 20)
    score = max(0, min(100, base + random.randint(-15, 15)))
    for level_name, (lo, hi) in RISK_LEVELS.items():
        if lo <= score < hi:
            return {"score": score, "level": level_name}
    return {"score": score, "level": "要対策"}


def random_location() -> dict:
    """ランダムな地域を選択"""
    region = random.choice(list(SAMPLE_LOCATIONS.keys()))
    loc = random.choice(SAMPLE_LOCATIONS[region])
    return loc


def build_input_data(youkai_ids: list[str], config: dict) -> dict:
    """入力データを構築"""
    loc = random_location()
    risk_scores = {}
    for yid in ["kappa", "namazu", "tsuchigumo", "kasha", "yukionna", "hinokagutsuchi"]:
        rs = random_risk_score(yid, loc["terrain"])
        yconf = config["youkai"][yid]
        risk_scores[yid] = {
            "name": yconf["name"],
            "score": rs["score"],
            "level": rs["level"],
        }
    return {
        "location": {
            "address": loc["address"],
            "elevation": loc["elevation"],
            "terrain": loc["terrain"],
            "characteristics": loc.get("chars", []),
        },
        "risk_scores": risk_scores,
    }


# ============================================================
# カテゴリ別プロンプト生成
# ============================================================

def build_cat1_prompt(youkai_id: str, pattern: str, config: dict) -> tuple[str, dict]:
    """カテゴリ1: 妖怪会話（平時・基本）"""
    yconf = config["youkai"][youkai_id]
    input_data = build_input_data([youkai_id], config)

    # パターン名→日本語マッピング
    pattern_ja = {
        "greeting": "挨拶",
        "explain_risk": "リスクの説明",
        "give_advice": "対策の提案",
        "reassure": "安心メッセージ",
        "farewell": "締めくくり",
    }

    pattern_descriptions = {
        "greeting": "住民との最初の出会いの挨拶を生成します。自己紹介とこの土地との関わりを説明し、親しみやすい雰囲気で。1〜2文。",
        "explain_risk": "土地のリスクを知識として伝える会話を生成します。具体的なリスク説明、「知っておくと安心」という姿勢で。2〜4文。",
        "give_advice": "具体的な備えや対策を提案する会話を生成します。避難所確認、準備品提案、「一緒に確認しよう」という姿勢で。2〜4文。",
        "reassure": "住民を安心させるメッセージ。「備えがあれば大丈夫」「見守っている」という安心感。1〜3文。",
        "farewell": "会話の締めくくり。「また相談に来て」「見守っている」ポジティブな言葉で。1〜2文。",
    }

    # emotionの選択肢を明示
    pattern_emotions = {
        "greeting": "friendly",
        "explain_risk": "teaching",
        "give_advice": "suggesting",
        "reassure": "reassuring",
        "farewell": "warm",
    }

    prompt = f"""# 生成タスク
カテゴリ: 妖怪会話（平時・基本）
担当妖怪: {yconf['name']}（{yconf['emoji']}）
会話パターン: {pattern_ja[pattern]}

## 妖怪設定
- 一人称: {yconf['first_person']}
- 口調: {yconf['tone']}
- 担当災害: {yconf['domain']}
- 性格: {yconf['personality']}

## 会話パターン説明
{pattern_descriptions[pattern]}

## emotionフィールドの選択肢（以下から選んでください）
friendly / teaching / thinking / suggesting / reassuring / warm / calm / serious / warning / hopeful / supportive

## 入力データ
{json.dumps(input_data, ensure_ascii=False, indent=2)}

## 出力形式（このJSON形式で出力してください）
{{
  "task_type": "youkai_hazard",
  "instruction": "あなたは{yconf['name']}です。以下の土地のリスクについて、住民に{pattern_ja[pattern]}してください。",
  "input": {json.dumps(input_data, ensure_ascii=False)},
  "output": {{
    "conversation": [
      {{
        "speaker": "{youkai_id}",
        "speaker_name": "{yconf['name']}",
        "speaker_emoji": "{yconf['emoji']}",
        "emotion": "{pattern_emotions[pattern]}",
        "text": "会話文を生成"
      }}
    ],
    "summary": {{
      "main_point": "主なポイント",
      "reassurance": "安心メッセージ"
    }}
  }}
}}

口調・一人称・性格を厳密に守り、禁止表現は絶対に使わないでください。"""

    return prompt, input_data


def build_cat3_prompt(youkai_id: str, situation: str, config: dict) -> tuple[str, dict]:
    """カテゴリ3: 妖怪会話（有事モード）"""
    yconf = config["youkai"][youkai_id]
    input_data = build_input_data([youkai_id], config)

    # 有事用の追加情報
    disaster_map = {
        "kappa": {"type": "水害", "specifics": ["流水の危険", "マンホール転落", "感染症", "漏電"]},
        "namazu": {"type": "地震", "specifics": ["余震による建物倒壊", "液状化・陥没", "ガス漏れ", "ブロック塀倒壊"]},
        "tsuchigumo": {"type": "土砂災害", "specifics": ["二次崩壊", "斜面上部の亀裂", "有毒ガス"]},
        "kasha": {"type": "火災", "specifics": ["延焼拡大", "有毒ガス", "建物崩壊", "風向き変化"]},
        "yukionna": {"type": "雪害", "specifics": ["雪崩", "吹雪・視界不良", "低体温症", "凍結路面"]},
        "hinokagutsuchi": {"type": "火山災害", "specifics": ["火砕流", "降灰", "火山ガス", "溶岩流"]},
    }
    dinfo = disaster_map.get(youkai_id, {"type": "災害", "specifics": []})

    situation_descs = {
        "situation_report": "現場の状況を客観的に報告。危険箇所の特定と安全エリアの案内。",
        "danger_warning": "二次災害のリスクを警告。回避方法と代替ルートの案内。",
        "search_advice": "捜索活動へのアドバイス。捜索のポイントと注意点。",
        "hope_message": "捜索者や被災者に希望を与えるメッセージ。具体的根拠を添えて。",
    }

    input_data["emergency"] = {
        "disaster_type": dinfo["type"],
        "secondary_risks": dinfo["specifics"],
        "elapsed_hours": random.choice([6, 12, 24, 48, 72]),
    }

    prompt = f"""# 生成タスク
カテゴリ: 妖怪会話（有事モード）
担当妖怪: {yconf['name']}（{yconf['emoji']}）
災害種別: {dinfo['type']}
状況タイプ: {situation}

## 有事モードの基本理念
妖怪は「捜索支援者」として振る舞い、二次災害リスクを警告し、希望を持たせながら安全な行動を促す。

## 絶対禁止
- 「もう手遅れ」「助からない」「諦めろ」
- 犠牲者数の具体的言及
- 遺体の描写
- 無責任な楽観論

## 推奨表現
- 「気をつけろ、ここは注意が必要じゃ」
- 「まだ望みはある、諦めるな」
- 「この先は別のルートを使え」
- 「休憩を取れ、倒れては元も子もない」

## 状況説明
{situation_descs[situation]}

## 妖怪設定
一人称: {yconf['first_person']} / 口調: {yconf['tone']} / 性格: {yconf['personality']}

## 入力データ
{json.dumps(input_data, ensure_ascii=False, indent=2)}

## 出力形式（このJSON形式で出力してください）
{{
  "task_type": "youkai_hazard",
  "instruction": "あなたは{yconf['name']}です。{dinfo['type']}発生時の{situation}を行ってください。",
  "input": {json.dumps(input_data, ensure_ascii=False)},
  "output": {{
    "conversation": [
      {{
        "speaker": "{youkai_id}",
        "speaker_name": "{yconf['name']}",
        "speaker_emoji": "{yconf['emoji']}",
        "emotion": "serious/warning/hopeful のいずれか",
        "text": "有事モードの会話文"
      }}
    ],
    "emergency_info": {{
      "hazard_type": "二次災害の種類",
      "warning_level": "警戒レベル",
      "recommended_action": "推奨行動"
    }}
  }}
}}"""

    return prompt, input_data


def build_cat4_prompt(perspective: str, config: dict) -> tuple[str, dict]:
    """カテゴリ4: 隠れリスク分析"""
    youkai_id = random.choice(list(config["youkai"].keys()))
    yconf = config["youkai"][youkai_id]
    input_data = build_input_data([youkai_id], config)

    perspectives = {
        "時系列リスク": "災害の連鎖を分析。例: 地震→液状化→避難困難→津波到達",
        "経路リスク": "避難ルート上の危険を分析。例: 橋の落下、道路の液状化",
        "季節リスク": "季節との組み合わせ。例: 台風シーズン×大潮、冬季×凍結路面",
        "時間帯リスク": "時間帯による違い。例: 夜間避難の困難さ、通勤時間帯の混雑",
        "複合地域リスク": "リスクの重複。例: 水害エリアかつ液状化エリア",
        "インフラリスク": "ライフライン途絶。例: 停電、断水、通信途絶",
        "地形リスク": "地形による増幅。例: 低地で水が集まる、谷地形で土砂",
    }

    prompt = f"""# 生成タスク
カテゴリ: 隠れリスク分析
分析観点: {perspective}
担当妖怪: {yconf['name']}（{yconf['emoji']}）

## 目的
人間が気づきにくい複合リスクを発見し、「知識」として伝える会話を生成。
恐怖を煽らず「ふむ、気づいたことがあるぞ」という形式で。

## 分析観点の説明
{perspectives[perspective]}

## 伝え方
推奨: 「ふむ、もう一つ知っておくとよいことがあるぞ」「念のため、こちらも確認しておこうかの」
禁止: 「大変なことになるぞ！」「最悪の事態じゃ！」

## 妖怪設定
一人称: {yconf['first_person']} / 口調: {yconf['tone']}

## 入力データ
{json.dumps(input_data, ensure_ascii=False, indent=2)}

## 出力形式（このJSON形式で出力してください）
{{
  "task_type": "youkai_hazard",
  "instruction": "あなたは{yconf['name']}です。以下の土地の隠れリスクを分析し、住民に伝えてください。分析観点: {perspective}",
  "input": {json.dumps(input_data, ensure_ascii=False)},
  "output": {{
    "conversation": [
      {{
        "speaker": "{youkai_id}",
        "speaker_name": "{yconf['name']}",
        "speaker_emoji": "{yconf['emoji']}",
        "emotion": "thinking",
        "text": "気づきの導入"
      }},
      {{
        "speaker": "{youkai_id}",
        "speaker_name": "{yconf['name']}",
        "speaker_emoji": "{yconf['emoji']}",
        "emotion": "teaching",
        "text": "隠れリスクの説明"
      }},
      {{
        "speaker": "{youkai_id}",
        "speaker_name": "{yconf['name']}",
        "speaker_emoji": "{yconf['emoji']}",
        "emotion": "suggesting",
        "text": "対策の提案（ポジティブに締める）"
      }}
    ],
    "hidden_risk_analysis": {{
      "risk_type": "{perspective}",
      "title": "リスクのタイトル",
      "description": "リスクの詳細説明",
      "reasoning": "分析の根拠",
      "recommended_action": "推奨対策"
    }}
  }}
}}"""

    return prompt, input_data


def build_cat9_prompt(config: dict) -> tuple[str, dict]:
    """カテゴリ9: 避難所QA"""
    loc = random_location()
    qa_patterns = [
        "一番近い避難所はどこですか？",
        "ペット同伴可能な避難所はありますか？",
        "車椅子で行ける避難所を教えてください",
        "避難所で必要な持ち物は何ですか？",
        "現在開設されている避難所を教えてください",
        "避難所の収容人数を教えてください",
        "高齢者でも安全に行ける避難所は？",
        "避難所ではどんな物資が配られますか？",
        f"{loc['address']}から最寄りの避難所への行き方を教えてください",
        "乳幼児がいる場合、どの避難所がおすすめですか？",
    ]
    question = random.choice(qa_patterns)
    disaster_types = ["flood", "earthquake", "landslide", "tsunami", "fire"]
    disaster_type = random.choice(disaster_types)

    input_data = {
        "location": {"address": loc["address"], "lat": loc.get("lat", 0), "lng": loc.get("lng", 0)},
        "disaster_type": disaster_type,
        "question": question,
    }

    prompt = f"""# 生成タスク
カテゴリ: 避難所QA
task_type: evacuation_qa

## 質問
{question}

## 入力データ
{json.dumps(input_data, ensure_ascii=False, indent=2)}

## 出力形式（このJSON形式で出力してください）
{{
  "task_type": "evacuation_qa",
  "instruction": "以下の質問に対して、避難所に関する情報を提供してください。",
  "input": {json.dumps(input_data, ensure_ascii=False)},
  "output": {{
    "answer": "丁寧で具体的な回答",
    "shelters": [
      {{
        "name": "避難所名",
        "distance_m": 距離（メートル）,
        "accessibility": "バリアフリー情報",
        "disaster_types_supported": ["対応災害種別"],
        "capacity": 収容人数
      }}
    ],
    "precautions": ["注意事項1", "注意事項2"]
  }}
}}

地域の実情に合った自然な回答を生成してください。具体的な避難所名や距離は架空でも構いませんが、リアルに。"""

    return prompt, input_data


def build_cat11_prompt(config: dict, monument_data: Optional[dict] = None) -> tuple[str, dict]:
    """カテゴリ11: 災害シナリオ（伝承碑シード対応）"""
    loc = random_location()
    disaster_types = ["地震", "水害", "土砂災害", "火災", "津波", "複合災害"]
    disaster_type = random.choice(disaster_types)

    input_data = {
        "location": {"address": loc["address"], "terrain": loc["terrain"]},
        "disaster_type": disaster_type,
    }

    monument_context = ""
    metadata = {}
    if monument_data:
        monument_context = f"""
## 自然災害伝承碑データ（シード）
碑名: {monument_data.get('name', '不明')}
災害名: {monument_data.get('disaster_name', '不明')}
災害種別: {monument_data.get('disaster_types', '不明')}
所在地: {monument_data.get('address', '不明')}
伝承内容:
{monument_data.get('description', '伝承内容不明')}

※ この伝承碑の実災害を踏まえた現代の避難シナリオを記述してください。
"""
        metadata = {
            "seed_source": "自然災害伝承碑データ（国土地理院）",
            "seed_monument_name": monument_data.get("name", ""),
            "attribution": "「自然災害伝承碑データ」（国土地理院）をもとに加工して作成",
        }
        input_data["monument_context"] = monument_data.get("description", "")

    prompt = f"""# 生成タスク
カテゴリ: 災害シナリオ
task_type: disaster_scenario
災害種別: {disaster_type}
{monument_context}
## 入力データ
{json.dumps(input_data, ensure_ascii=False, indent=2)}

## 出力形式（このJSON形式で出力してください）
{{
  "task_type": "disaster_scenario",
  "instruction": "{disaster_type}が発生した場合の避難行動シナリオを生成してください。",
  "input": {json.dumps(input_data, ensure_ascii=False)},
  "output": {{
    "scenario_title": "シナリオタイトル",
    "disaster_description": "災害の概要（恐怖を煽らない表現で）",
    "timeline": [
      {{
        "time": "発生直後",
        "action": "とるべき行動",
        "reason": "その理由"
      }},
      {{
        "time": "30分後",
        "action": "次の行動",
        "reason": "その理由"
      }}
    ],
    "evacuation_route": "推奨避難ルートの説明",
    "precautions": ["注意事項1", "注意事項2"],
    "reassurance": "安心メッセージ（備えがあれば大丈夫）"
  }}{f', "metadata": {json.dumps(metadata, ensure_ascii=False)}' if metadata else ''}
}}

恐怖を煽らず、具体的で実用的なシナリオを生成してください。"""

    return prompt, input_data


# ============================================================
# vLLM API呼び出し
# ============================================================

async def call_vllm(
    session: aiohttp.ClientSession,
    base_url: str,
    model_name: str,
    prompt: str,
    temperature: float = 0.7,
    max_tokens: int = 4096,
) -> Optional[dict]:
    """vLLM APIを呼び出してJSONを抽出"""
    try:
        async with session.post(
            f"{base_url}/chat/completions",
            json={
                "model": model_name,
                "messages": [
                    {"role": "system", "content": SYSTEM_PROMPT},
                    {"role": "user", "content": prompt},
                ],
                "temperature": temperature,
                "max_tokens": max_tokens,
                # Qwen3の思考モードを無効化して高速化
                # 思考トークンを生成しない分、速度が大幅に向上する
                "chat_template_kwargs": {"enable_thinking": False},
            },
            timeout=aiohttp.ClientTimeout(total=120),
        ) as resp:
            if resp.status != 200:
                text = await resp.text()
                print(f"API Error {resp.status}: {text[:200]}")
                return None

            result = await resp.json()
            content = result["choices"][0]["message"]["content"]

            # thinkingタグを除去（Qwen3の思考モード対応）
            content = re.sub(r"<think>.*?</think>", "", content, flags=re.DOTALL).strip()

            # JSONを抽出
            json_match = re.search(r"\{[\s\S]*\}", content)
            if json_match:
                return json.loads(json_match.group())

            print(f"JSON抽出失敗: {content[:200]}")
            return None

    except json.JSONDecodeError as e:
        print(f"JSON parse error: {e}")
        return None
    except asyncio.TimeoutError:
        print("Timeout")
        return None
    except Exception as e:
        print(f"Error: {e}")
        return None


# ============================================================
# 品質チェック
# ============================================================

def quality_check(data: dict, config: dict, category: str = "") -> tuple[bool, str]:
    """
    生成データの品質チェック（段階的表現ガイドライン対応）

    判定基準:
    - hard_reject: 絶対に避ける表現 → データ除外
      ※ cat8_forbidden は禁止表現→言い換えを教えるデータのためスキップ
    - soft_warn: 文脈次第で許容 → 警告のみ（除外しない）
    - 構造チェック: 必須フィールドの存在確認
    """
    quality_conf = config.get("quality", {})

    # 1. 必須フィールドチェック
    if "task_type" not in data:
        return False, "task_type フィールドがありません"

    valid_types = ["youkai_hazard", "evacuation_qa", "route_guidance", "disaster_scenario", "local_info"]
    if data.get("task_type") not in valid_types:
        return False, f"不正な task_type: {data.get('task_type')}"

    if "output" not in data and "response" not in data:
        return False, "output フィールドがありません"

    if "instruction" not in data:
        return False, "instruction フィールドがありません"

    # 2. hard_reject: 住民の不安を不必要に煽る表現を除外
    # cat8_forbidden は禁止表現の言い換え例を生成するため、表現チェックをスキップ
    text = json.dumps(data, ensure_ascii=False)
    if category != "cat8_forbidden":
        for rule in quality_conf.get("hard_reject", []):
            pattern = rule.get("pattern", "")
            if pattern and pattern in text:
                return False, f"表現ガイドライン違反（レベル1）: 「{pattern}」→ 推奨: {rule.get('alternative', '言い換えてください')}"

        # 3. 旧形式の forbidden_expressions にも対応（後方互換）
        for expr in quality_conf.get("forbidden_expressions", []):
            if expr in text:
                return False, f"禁止表現検出: {expr}"

    # 4. soft_warn: 文脈によって許容する表現（警告のみ、除外しない）
    warnings = []
    for rule in quality_conf.get("soft_warn", []):
        pattern = rule.get("pattern", "")
        if pattern and pattern in text:
            # 許容コンテキストに該当するかチェック
            context_ok = rule.get("context_ok", [])
            in_allowed_context = any(ctx in text for ctx in context_ok)
            if not in_allowed_context:
                warnings.append(
                    f"表現注意（レベル2）: 「{pattern}」が含まれています。"
                    f" 推奨: {rule.get('preferred', '文脈に応じて言い換えを検討')}"
                )

    # 警告がある場合はログに出すが、データは有効とする
    if warnings:
        # 警告は標準出力に出すが、データは通過させる
        pass

    return True, "OK"


# ============================================================
# 生成ジョブ
# ============================================================

async def generate_category(
    category: str,
    count: int,
    config: dict,
    resume: bool = False,
    monument_data: Optional[list[dict]] = None,
) -> list[dict]:
    """カテゴリ別のデータ生成"""

    raw_dir = Path(config["output"]["raw_dir"])
    raw_dir.mkdir(parents=True, exist_ok=True)
    output_file = raw_dir / f"youkai_hazard_train_v2_{category}.jsonl"

    # レジューム対応
    existing_count = 0
    if resume and output_file.exists():
        with open(output_file, "r", encoding="utf-8") as f:
            existing_count = sum(1 for _ in f)
        print(f"[レジューム] 既存データ: {existing_count}件")
        count = max(0, count - existing_count)
        if count == 0:
            print(f"[{category}] 既に目標件数に達しています")
            return []

    vllm_conf = config["vllm"]
    results = []
    errors = 0
    mode = "a" if resume else "w"

    async with aiohttp.ClientSession() as session:
        # まずモデル名を確認
        try:
            async with session.get(f"{vllm_conf['base_url']}/models") as resp:
                models = await resp.json()
                available_model = models["data"][0]["id"]
                print(f"[使用モデル] {available_model}")
        except Exception as e:
            print(f"モデル確認失敗: {e}")
            available_model = vllm_conf["model_name"]

        with open(output_file, mode, encoding="utf-8") as f:
            pbar = tqdm(total=count, desc=f"生成中: {category}", initial=0)

            generated = 0
            max_concurrent = config.get("concurrency", {}).get("max_concurrent_requests", 4)
            semaphore = asyncio.Semaphore(max_concurrent)

            async def _generate_one():
                """1件生成してresultを返す"""
                prompt, _ = _build_prompt_for_category(category, config, monument_data)
                async with semaphore:
                    return await call_vllm(
                        session,
                        vllm_conf["base_url"],
                        available_model,
                        prompt,
                        vllm_conf.get("temperature", 0.7),
                        vllm_conf.get("max_tokens", 4096),
                    )

            while generated < count:
                # 残り件数に応じたバッチサイズ
                remaining = count - generated
                batch_size = min(max_concurrent, remaining)

                # バッチ並列実行
                tasks = [_generate_one() for _ in range(batch_size)]
                batch_results = await asyncio.gather(*tasks, return_exceptions=True)

                for result in batch_results:
                    if isinstance(result, Exception):
                        errors += 1
                        if errors % 10 == 0:
                            print(f"\n生成失敗({errors}回): {result}")
                        continue

                    if result:
                        ok, msg = quality_check(result, config, category)
                        if ok:
                            f.write(json.dumps(result, ensure_ascii=False) + "\n")
                            f.flush()
                            results.append(result)
                            generated += 1
                            pbar.update(1)
                        else:
                            errors += 1
                            if errors % 10 == 0:
                                print(f"\n品質チェック失敗({errors}回): {msg}")
                    else:
                        errors += 1
                        if errors % 10 == 0:
                            print(f"\n生成失敗({errors}回)")

                if errors > 50:
                    print("\nエラーが多すぎます。中断します。")
                    break

            pbar.close()

    total = existing_count + generated
    print(f"\n[{category}] 生成完了: {generated}件 (合計: {total}件)")
    return results


def _build_prompt_for_category(
    category: str,
    config: dict,
    monument_data: Optional[list[dict]] = None,
) -> tuple[str, dict]:
    """カテゴリに応じたプロンプトを生成"""
    youkai_ids = list(config["youkai"].keys())

    if category == "cat1_basic":
        youkai_id = random.choice(youkai_ids)
        patterns = ["greeting", "explain_risk", "give_advice", "reassure", "farewell"]
        weights = [100, 300, 300, 200, 100]
        pattern = random.choices(patterns, weights=weights, k=1)[0]
        return build_cat1_prompt(youkai_id, pattern, config)

    elif category == "cat2_multi":
        # 2-3体の組み合わせ
        n = random.choice([2, 2, 2, 3])
        selected = random.sample(youkai_ids, n)
        return _build_cat2_prompt(selected, config)

    elif category == "cat3_emergency":
        youkai_id = random.choices(
            youkai_ids,
            weights=[25, 25, 20, 15, 10, 5],
            k=1,
        )[0]
        situations = ["situation_report", "danger_warning", "search_advice", "hope_message"]
        situation = random.choice(situations)
        return build_cat3_prompt(youkai_id, situation, config)

    elif category == "cat4_hidden_risk":
        perspectives = ["時系列リスク", "経路リスク", "季節リスク", "時間帯リスク", "複合地域リスク", "インフラリスク", "地形リスク"]
        perspective = random.choice(perspectives)
        return build_cat4_prompt(perspective, config)

    elif category == "cat5_disaster_risk":
        return _build_cat5_prompt(config)

    elif category == "cat6_terrain":
        return _build_cat6_prompt(config)

    elif category == "cat7_search":
        return _build_cat7_prompt(config)

    elif category == "cat8_forbidden":
        return _build_cat8_prompt(config)

    elif category == "cat9_evacuation_qa":
        return build_cat9_prompt(config)

    elif category == "cat10_route":
        return _build_cat10_prompt(config)

    elif category == "cat11_scenario":
        monument = None
        if monument_data:
            monument = random.choice(monument_data)
        return build_cat11_prompt(config, monument)

    elif category == "cat12_local":
        monument = None
        if monument_data:
            monument = random.choice(monument_data)
        return _build_cat12_prompt(config, monument)

    else:
        raise ValueError(f"Unknown category: {category}")


def _build_cat2_prompt(youkai_ids: list[str], config: dict) -> tuple[str, dict]:
    """カテゴリ2: 複数妖怪の掛け合い"""
    input_data = build_input_data(youkai_ids, config)
    names = "・".join([config["youkai"][yid]["name"] for yid in youkai_ids])

    youkai_settings = ""
    for yid in youkai_ids:
        yc = config["youkai"][yid]
        youkai_settings += f"- {yc['name']}({yc['emoji']}): 一人称={yc['first_person']}, 口調={yc['tone']}\n"

    prompt = f"""# 生成タスク
カテゴリ: 妖怪会話（平時・複数登場）
登場妖怪: {names}

## 複数妖怪登場ルール
- リスクスコアが高い順に発言権を持つ
- 妖怪同士は敬意を持って会話
- 最後は協力して「まとめ」を提示
- 自然な掛け合いを行う

## 妖怪設定
{youkai_settings}

## 入力データ
{json.dumps(input_data, ensure_ascii=False, indent=2)}

## 出力形式（このJSON形式で出力してください）
{{
  "task_type": "youkai_hazard",
  "instruction": "あなたは{names}です。協力して住民に土地のリスクを説明してください。",
  "input": {json.dumps(input_data, ensure_ascii=False)},
  "output": {{
    "conversation": [
      {{
        "speaker": "{youkai_ids[0]}",
        "speaker_name": "{config['youkai'][youkai_ids[0]]['name']}",
        "speaker_emoji": "{config['youkai'][youkai_ids[0]]['emoji']}",
        "emotion": "friendly / teaching / thinking / suggesting / reassuring / warm / calm / serious / warning / hopeful / supportive から1つ選択",
        "text": "発言内容（2〜4文）"
      }},
      {{
        "speaker": "{youkai_ids[1]}",
        "speaker_name": "{config['youkai'][youkai_ids[1]]['name']}",
        "speaker_emoji": "{config['youkai'][youkai_ids[1]]['emoji']}",
        "emotion": "emotion値",
        "text": "発言内容（2〜4文）"
      }}
    ],
    "summary": {{
      "main_risks": ["リスク1", "リスク2"],
      "actions": ["対策1", "対策2"],
      "reassurance": "協力した安心メッセージ"
    }}
  }}
}}

## 重要ルール
- conversationは5〜8ターン生成する
- 各ターンのキーは必ず speaker, speaker_name, speaker_emoji, emotion, text の5つ
- speakerはローマ字ID（{', '.join(youkai_ids)}）を使用
- emotionは英語で上記リストから選択
- 各妖怪の口調・一人称を厳密に守り、自然な掛け合いを生成してください"""

    return prompt, input_data


def _build_cat5_prompt(config: dict) -> tuple[str, dict]:
    """カテゴリ5: 災害別リスク説明"""
    risk_cats = config["risk_categories"]
    cat_key = random.choice(list(risk_cats.keys()))
    rcat = risk_cats[cat_key]
    risk_type = random.choice(rcat["types"])
    youkai_id = rcat["youkai"]
    yconf = config["youkai"][youkai_id]
    input_data = build_input_data([youkai_id], config)

    prompt = f"""# 生成タスク
カテゴリ: 災害別リスク説明
災害種別: {risk_type}
担当妖怪: {yconf['name']}（{yconf['emoji']}）

## 妖怪設定
一人称: {yconf['first_person']} / 口調: {yconf['tone']} / 担当: {yconf['domain']}

## 入力データ
{json.dumps(input_data, ensure_ascii=False, indent=2)}

## 出力形式（このJSON形式で出力してください）
{{
  "task_type": "youkai_hazard",
  "instruction": "あなたは{yconf['name']}です。{risk_type}のリスクを説明してください。",
  "input": {json.dumps(input_data, ensure_ascii=False)},
  "output": {{
    "conversation": [
      {{
        "speaker": "{youkai_id}",
        "speaker_name": "{yconf['name']}",
        "speaker_emoji": "{yconf['emoji']}",
        "emotion": "teaching",
        "text": "リスク説明（2〜4文）"
      }},
      {{
        "speaker": "{youkai_id}",
        "speaker_name": "{yconf['name']}",
        "speaker_emoji": "{yconf['emoji']}",
        "emotion": "reassuring",
        "text": "安心メッセージで締める"
      }}
    ],
    "risk_explanation": {{
      "disaster_type": "{risk_type}",
      "risk_factors": ["要因1", "要因2"],
      "countermeasures": ["対策1", "対策2"]
    }}
  }}
}}"""

    return prompt, input_data


def _build_cat6_prompt(config: dict) -> tuple[str, dict]:
    """カテゴリ6: 地形・地域特性"""
    terrain = random.choice(config["terrain_types"])
    terrain_youkai_map = {
        "沿岸部": "kappa", "河川近傍": "kappa", "低地": "kappa",
        "埋立地": "namazu", "平野部": "namazu",
        "斜面地": "tsuchigumo", "丘陵地": "tsuchigumo", "山間部": "tsuchigumo",
        "盆地": "yukionna", "台地": "namazu",
    }
    youkai_id = terrain_youkai_map.get(terrain, random.choice(list(config["youkai"].keys())))
    yconf = config["youkai"][youkai_id]
    input_data = build_input_data([youkai_id], config)
    input_data["location"]["terrain"] = terrain

    prompt = f"""# 生成タスク
カテゴリ: 地形・地域特性
地形タイプ: {terrain}
担当妖怪: {yconf['name']}（{yconf['emoji']}）

## 妖怪設定
一人称: {yconf['first_person']} / 口調: {yconf['tone']}

## 入力データ
{json.dumps(input_data, ensure_ascii=False, indent=2)}

## 出力形式（このJSON形式で出力してください）
{{
  "task_type": "youkai_hazard",
  "instruction": "あなたは{yconf['name']}です。{terrain}の特性とリスクを説明してください。",
  "input": {json.dumps(input_data, ensure_ascii=False)},
  "output": {{
    "conversation": [
      {{
        "speaker": "{youkai_id}",
        "speaker_name": "{yconf['name']}",
        "speaker_emoji": "{yconf['emoji']}",
        "emotion": "teaching",
        "text": "地形の特徴とリスクの説明（2〜4文）"
      }},
      {{
        "speaker": "{youkai_id}",
        "speaker_name": "{yconf['name']}",
        "speaker_emoji": "{yconf['emoji']}",
        "emotion": "reassuring",
        "text": "安心メッセージ（1〜2文）"
      }}
    ],
    "terrain_analysis": {{
      "terrain_type": "{terrain}",
      "characteristics": ["特徴1", "特徴2"],
      "related_risks": ["リスク1", "リスク2"],
      "living_tips": ["暮らしのヒント1", "ヒント2"]
    }}
  }}
}}

## 重要ルール
- conversationは2〜4ターン生成する
- 各ターンのキーは必ず speaker, speaker_name, speaker_emoji, emotion, text の5つ
- speakerはローマ字ID（{youkai_id}）を使用
- emotionは英語で friendly / teaching / thinking / suggesting / reassuring / warm / calm / serious / warning / hopeful / supportive から選択"""

    return prompt, input_data


def _build_cat7_prompt(config: dict) -> tuple[str, dict]:
    """カテゴリ7: 捜索ガイダンス"""
    hazards = [
        ("余震による建物倒壊", "namazu"),
        ("液状化・陥没", "namazu"),
        ("ガス漏れ", "namazu"),
        ("流水の危険", "kappa"),
        ("マンホール転落", "kappa"),
        ("二次崩壊", "tsuchigumo"),
    ]
    hazard_name, youkai_id = random.choice(hazards)
    yconf = config["youkai"][youkai_id]
    input_data = build_input_data([youkai_id], config)

    prompt = f"""# 生成タスク
カテゴリ: 捜索ガイダンス（有事モード）
二次災害タイプ: {hazard_name}
担当妖怪: {yconf['name']}（{yconf['emoji']}）

## 絶対禁止
「もう手遅れ」「助からない」「諦めろ」、犠牲者数の言及、遺体の描写

## 妖怪設定
一人称: {yconf['first_person']} / 口調: {yconf['tone']}

## 入力データ
{json.dumps(input_data, ensure_ascii=False, indent=2)}

## 出力形式（このJSON形式で出力してください）
{{
  "task_type": "youkai_hazard",
  "instruction": "あなたは{yconf['name']}です。{hazard_name}に関する捜索時の注意点を説明してください。",
  "input": {json.dumps(input_data, ensure_ascii=False)},
  "output": {{
    "conversation": [
      {{
        "speaker": "{youkai_id}",
        "speaker_name": "{yconf['name']}",
        "speaker_emoji": "{yconf['emoji']}",
        "emotion": "warning",
        "text": "二次災害の注意点の説明（2〜4文）"
      }},
      {{
        "speaker": "{youkai_id}",
        "speaker_name": "{yconf['name']}",
        "speaker_emoji": "{yconf['emoji']}",
        "emotion": "reassuring",
        "text": "安心メッセージ（1〜2文）"
      }}
    ],
    "search_guidance": {{
      "hazard_type": "{hazard_name}",
      "danger_signs": ["兆候1", "兆候2"],
      "safety_measures": ["安全対策1", "対策2"],
      "equipment_needed": ["必要装備1", "装備2"]
    }}
  }}
}}

## 重要ルール
- conversationは2〜4ターン生成する
- 各ターンのキーは必ず speaker, speaker_name, speaker_emoji, emotion, text の5つ
- speakerはローマ字ID（{youkai_id}）を使用
- emotionは英語で friendly / teaching / thinking / suggesting / reassuring / warm / calm / serious / warning / hopeful / supportive から選択"""

    return prompt, input_data


def _build_cat8_prompt(config: dict) -> tuple[str, dict]:
    """カテゴリ8: 禁止表現回避"""
    youkai_id = random.choice(list(config["youkai"].keys()))
    yconf = config["youkai"][youkai_id]

    avoidance_examples = [
        ("この場所は危険だ", "恐怖を煽る表現の言い換え"),
        ("ここに住むと最悪の事態になる", "恐怖を煽る表現の言い換え"),
        ("逃げ場がない", "恐怖を煽る表現の言い換え"),
        ("ここに住むべきではない", "断定的否定の言い換え"),
        ("この土地は最悪だ", "断定的否定の言い換え"),
        ("でも心配です...", "不安を残す締めの言い換え"),
        ("不安が残ります", "不安を残す締めの言い換え"),
        ("過去にどんなひどい被害があったか教えて", "トラウマ想起表現の回避"),
        ("何人亡くなったの？", "トラウマ想起表現の回避"),
    ]
    inappropriate, avoidance_type = random.choice(avoidance_examples)

    prompt = f"""# 生成タスク
カテゴリ: 禁止表現回避
回避タイプ: {avoidance_type}
担当妖怪: {yconf['name']}（{yconf['emoji']}）

## 目的
不適切な表現に対して適切に言い換える能力を学習。

## 不適切な入力
「{inappropriate}」

## 妖怪設定
一人称: {yconf['first_person']} / 口調: {yconf['tone']}

## 出力形式（このJSON形式で出力してください）
{{
  "task_type": "youkai_hazard",
  "instruction": "あなたは{yconf['name']}です。以下の内容を恐怖を煽らず適切に伝えてください。",
  "input": "{inappropriate}",
  "output": {{
    "conversation": [
      {{
        "speaker": "{youkai_id}",
        "speaker_name": "{yconf['name']}",
        "speaker_emoji": "{yconf['emoji']}",
        "emotion": "calm",
        "text": "適切に言い換えた表現"
      }}
    ],
    "transformation": {{
      "original_intent": "元の意図",
      "transformed_message": "変換後のメッセージ",
      "avoidance_applied": "{avoidance_type}"
    }}
  }}
}}"""

    return prompt, {"inappropriate_request": inappropriate}


def _build_cat10_prompt(config: dict) -> tuple[str, dict]:
    """カテゴリ10: 経路案内"""
    loc = random_location()
    route_patterns = ["最短経路案内", "安全経路案内", "複数ルート提示", "リアルタイム状況考慮"]
    route_type = random.choice(route_patterns)
    disaster_type = random.choice(["flood", "earthquake", "tsunami"])

    input_data = {
        "location": {"address": loc["address"], "lat": loc.get("lat", 0), "lng": loc.get("lng", 0)},
        "disaster_type": disaster_type,
        "route_type": route_type,
    }

    prompt = f"""# 生成タスク
カテゴリ: 経路案内
task_type: route_guidance
案内タイプ: {route_type}

## 入力データ
{json.dumps(input_data, ensure_ascii=False, indent=2)}

## 出力形式（このJSON形式で出力してください）
{{
  "task_type": "route_guidance",
  "instruction": "{route_type}で避難経路を案内してください。",
  "input": {json.dumps(input_data, ensure_ascii=False)},
  "output": {{
    "route_description": "経路の説明",
    "steps": [
      {{"step": 1, "instruction": "指示1", "distance_m": 距離, "caution": "注意点"}},
      {{"step": 2, "instruction": "指示2", "distance_m": 距離, "caution": "注意点"}}
    ],
    "estimated_time_min": 所要時間,
    "alternative_route": "代替ルートの説明",
    "precautions": ["注意事項"]
  }}
}}"""

    return prompt, input_data


def _build_cat12_prompt(config: dict, monument_data: Optional[dict] = None) -> tuple[str, dict]:
    """カテゴリ12: 地域固有情報"""
    loc = random_location()
    input_data = {
        "location": {"address": loc["address"], "terrain": loc["terrain"]},
    }

    monument_context = ""
    metadata = {}
    if monument_data:
        monument_context = f"""
## 自然災害伝承碑データ（シード）
碑名: {monument_data.get('name', '不明')}
所在地: {monument_data.get('address', '不明')}
伝承内容:
{monument_data.get('description', '不明')}

この伝承碑の教訓を現代の防災知識として整理してください。
"""
        metadata = {
            "seed_source": "自然災害伝承碑データ（国土地理院）",
            "seed_monument_name": monument_data.get("name", ""),
            "attribution": "「自然災害伝承碑データ」（国土地理院）をもとに加工して作成",
        }

    prompt = f"""# 生成タスク
カテゴリ: 地域固有情報
task_type: local_info
{monument_context}
## 入力データ
{json.dumps(input_data, ensure_ascii=False, indent=2)}

## 出力形式（このJSON形式で出力してください）
{{
  "task_type": "local_info",
  "instruction": "この地域の防災に役立つローカル知識を提供してください。",
  "input": {json.dumps(input_data, ensure_ascii=False)},
  "output": {{
    "local_knowledge": {{
      "area": "{loc['address']}",
      "historical_lessons": ["過去の教訓1", "教訓2"],
      "danger_spots": ["危険箇所1", "箇所2"],
      "community_info": "地域コミュニティの防災情報",
      "seasonal_risks": ["季節ごとのリスク"]
    }}
  }}{f', "metadata": {json.dumps(metadata, ensure_ascii=False)}' if metadata else ''}
}}"""

    return prompt, input_data


# ============================================================
# 伝承碑データ読み込み
# ============================================================

def load_monument_data(data_dir: str) -> list[dict]:
    """伝承碑データを読み込み"""
    csv_path = Path(data_dir) / "monuments_seed.csv"
    if not csv_path.exists():
        print(f"[INFO] 伝承碑データなし: {csv_path}")
        return []

    import csv

    monuments = []
    with open(csv_path, "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            monuments.append(row)

    print(f"[INFO] 伝承碑データ読み込み: {len(monuments)}件")
    return monuments


# ============================================================
# メイン
# ============================================================

async def main():
    parser = argparse.ArgumentParser(description="妖怪ハザードマップ 教師データ生成")
    parser.add_argument("--config", required=True, help="設定ファイルパス")
    parser.add_argument("--category", help="生成するカテゴリ（例: cat1_basic）。省略時は全カテゴリ")
    parser.add_argument("--count", type=int, help="生成件数（省略時は設定ファイルの値）")
    parser.add_argument("--resume", action="store_true", help="前回の続きから生成")
    args = parser.parse_args()

    config = load_config(args.config)

    # 伝承碑データ読み込み
    monument_dir = Path(config["output"]["raw_dir"]).parent / "external" / "monuments"
    monument_data = load_monument_data(str(monument_dir))

    # 対象カテゴリ決定
    if args.category:
        categories = {args.category: config["categories"][args.category]}
    else:
        categories = config["categories"]

    print("=" * 60)
    print("妖怪ハザードマップ 教師データ生成")
    print(f"対象カテゴリ: {len(categories)}個")
    total_target = sum(c["total"] for c in categories.values())
    print(f"目標総数: {total_target:,}件")
    print("=" * 60)

    grand_total = 0
    for cat_key, cat_conf in categories.items():
        count = args.count if args.count else cat_conf["total"]
        print(f"\n{'='*40}")
        print(f"カテゴリ: {cat_conf['name']} ({cat_key})")
        print(f"目標: {count}件")
        print(f"{'='*40}")

        use_monuments = cat_conf.get("use_monument_seed", False)
        results = await generate_category(
            cat_key,
            count,
            config,
            resume=args.resume,
            monument_data=monument_data if use_monuments else None,
        )
        grand_total += len(results)

    print(f"\n{'='*60}")
    print(f"全カテゴリ生成完了: {grand_total}件")
    print(f"出力先: {config['output']['raw_dir']}")
    print(f"{'='*60}")


if __name__ == "__main__":
    asyncio.run(main())
