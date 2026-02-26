#!/usr/bin/env python3
"""
マージ済みモデルの自動評価スクリプト
テストデータ(14,200件)に対して推論し、品質を定量評価

使用方法:
  python evaluate_model.py --test-file ~/youkai-hazard/data/cleaned/test.jsonl --api-url http://localhost:8001/v1 --output ~/youkai-hazard/evaluation/eval_results.json

評価指標:
  - JSON生成成功率（構造化出力としてパースできるか）
  - スキーマ準拠率（task_type別の必須フィールドが存在するか）
  - キャラクター一貫性（妖怪の口調・一人称が正しいか）
  - 禁止表現の回避率
  - 応答速度（トークン/秒）
"""

import argparse
import asyncio
import json
import re
import sys
import time
from collections import Counter, defaultdict
from pathlib import Path

import aiohttp

# task_type別システムプロンプト
SYSTEM_PROMPTS = {
    "youkai_hazard": "あなたは妖怪ハザードマップの案内役です。妖怪キャラクターの口調を使い、地域の災害リスクについてわかりやすく説明してください。出力は指定されたJSON形式で返してください。",
    "evacuation_qa": "あなたは災害時避難支援AIです。避難所に関する質問に対して、正確で分かりやすい情報を提供してください。出力は指定されたJSON形式で返してください。",
    "route_guidance": "あなたは避難経路案内AIです。ユーザーの現在地と状況に基づき、安全な避難経路を案内してください。出力は指定されたJSON形式で返してください。",
    "disaster_scenario": "あなたは災害対応AIです。発生した災害の種別に応じて、適切な避難行動を案内してください。出力は指定されたJSON形式で返してください。",
    "local_info": "あなたは地域防災情報AIです。地域固有の災害リスクや避難に関する情報を提供してください。出力は指定されたJSON形式で返してください。",
}

# task_type別の必須フィールド
REQUIRED_FIELDS = {
    "youkai_hazard": ["conversation"],
    "evacuation_qa": ["shelters"],
    "route_guidance": ["steps"],
    "disaster_scenario": ["timeline"],
    "local_info": ["local_knowledge"],
}

# 禁止表現
HARD_REJECT = ["死ぬぞ", "逃げ場がない", "住むべきではない", "引っ越した方がいい", "諦めろ", "もう助からない", "遺体"]

# task_type別デフォルトmax_tokens（youkai_hazardは構造が複雑で長くなるため大きめに設定）
MAX_TOKENS_BY_TYPE = {
    "youkai_hazard": 1024,
    "evacuation_qa": 512,
    "route_guidance": 512,
    "disaster_scenario": 512,
    "local_info": 512,
}

# 妖怪一人称マッピング
YOUKAI_FIRST_PERSON = {
    "kappa": "ワシ", "namazu": "ワシ", "tsuchigumo": "拙者",
    "kasha": "ワガハイ", "yukionna": "わたし", "hinokagutsuchi": "我",
}


def strip_markdown_fences(text: str) -> str:
    """マークダウンコードフェンス（```json ... ```）を除去"""
    # ```json\n...\n``` or ```\n...\n```
    stripped = re.sub(r"^```(?:json)?\s*\n?", "", text.strip())
    stripped = re.sub(r"\n?```\s*$", "", stripped)
    return stripped.strip()


def repair_truncated_json(text: str) -> str:
    """トランケーションされたJSONの閉じ括弧を補完"""
    # 末尾の不完全な文字列リテラルを閉じる
    # 開いている引用符を数える
    in_string = False
    escape_next = False
    for ch in text:
        if escape_next:
            escape_next = False
            continue
        if ch == '\\':
            escape_next = True
            continue
        if ch == '"':
            in_string = not in_string
    if in_string:
        text += '"'

    # 閉じ括弧の補完
    open_braces = text.count('{') - text.count('}')
    open_brackets = text.count('[') - text.count(']')
    text += ']' * max(0, open_brackets) + '}' * max(0, open_braces)
    return text


def classify_failure(content: str, record: dict) -> str:
    """失敗パターンを分類して返す
    (A) truncated - JSONが途中で切れている
    (B) markdown_wrapped - JSON前後にマークダウンや説明文
    (C) syntax_error - JSON構文エラー
    (D) schema_violation - conversationフィールド欠落等のスキーマ違反
    (E) api_error - APIエラー（content=None）
    """
    if content is None:
        return "api_error"

    # マークダウン除去してからチェック
    cleaned = strip_markdown_fences(content)

    # トランケーション判定: 開き括弧と閉じ括弧の不一致
    open_b = cleaned.count('{') - cleaned.count('}')
    open_k = cleaned.count('[') - cleaned.count(']')
    if open_b > 0 or open_k > 0:
        return "truncated"

    # マークダウンフェンス付きかチェック
    if content.strip().startswith("```"):
        return "markdown_wrapped"

    # JSONパースを試みる
    try:
        parsed = json.loads(cleaned)
    except json.JSONDecodeError:
        # JSON部分抽出
        match = re.search(r'\{.*\}', cleaned, re.DOTALL)
        if match:
            try:
                parsed = json.loads(match.group())
            except json.JSONDecodeError:
                return "syntax_error"
        else:
            return "syntax_error"

    # スキーマチェック
    task_type = record.get("task_type", "youkai_hazard")
    required = REQUIRED_FIELDS.get(task_type, [])
    if not all(field in parsed for field in required):
        return "schema_violation"

    return "unknown"


async def call_api(session, api_url, model_name, messages, semaphore, max_tokens=512, json_mode=False):
    """vLLM APIにリクエスト送信"""
    async with semaphore:
        payload = {
            "model": model_name,
            "messages": messages,
            "max_tokens": max_tokens,
            "temperature": 0.1,
        }
        if json_mode:
            payload["response_format"] = {"type": "json_object"}
        try:
            start = time.time()
            async with session.post(
                f"{api_url}/chat/completions",
                json=payload,
                timeout=aiohttp.ClientTimeout(total=120),
            ) as resp:
                if resp.status != 200:
                    return None, 0, 0
                data = await resp.json()
                elapsed = time.time() - start
                content = data["choices"][0]["message"]["content"]
                tokens = data["usage"]["completion_tokens"]
                return content, elapsed, tokens
        except Exception:
            return None, 0, 0


def build_messages(record):
    """テストデータからメッセージを構築"""
    task_type = record.get("task_type", "youkai_hazard")
    instruction = record.get("instruction", "")
    input_data = record.get("input", "")

    system_prompt = SYSTEM_PROMPTS.get(task_type, SYSTEM_PROMPTS["youkai_hazard"])

    if isinstance(input_data, dict):
        input_text = json.dumps(input_data, ensure_ascii=False, indent=2)
    elif isinstance(input_data, str):
        input_text = input_data
    else:
        input_text = str(input_data)

    user_content = f"{instruction}\n\n{input_text}" if input_text else instruction

    return [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": user_content},
    ]


def evaluate_response(content, record):
    """応答を評価して結果を返す"""
    result = {
        "json_valid": False,
        "schema_valid": False,
        "no_forbidden": True,
        "character_ok": True,
    }

    if content is None:
        return result

    # 禁止表現チェック
    for expr in HARD_REJECT:
        if expr in content:
            result["no_forbidden"] = False
            break

    # JSONパースチェック（段階的に修復を試みる）
    cleaned = strip_markdown_fences(content)
    parsed = None

    # Step 1: そのままパース
    try:
        parsed = json.loads(cleaned)
        result["json_valid"] = True
    except json.JSONDecodeError:
        pass

    # Step 2: JSON部分を正規表現で抽出
    if parsed is None:
        match = re.search(r'\{.*\}', cleaned, re.DOTALL)
        if match:
            try:
                parsed = json.loads(match.group())
                result["json_valid"] = True
            except json.JSONDecodeError:
                pass

    # Step 3: トランケーション修復
    if parsed is None:
        repaired = repair_truncated_json(cleaned)
        try:
            parsed = json.loads(repaired)
            result["json_valid"] = True
        except json.JSONDecodeError:
            # 最後にJSON部分抽出+修復
            match = re.search(r'\{.*', repaired, re.DOTALL)
            if match:
                try:
                    parsed = json.loads(repair_truncated_json(match.group()))
                    result["json_valid"] = True
                except json.JSONDecodeError:
                    return result
            else:
                return result

    # スキーマチェック
    task_type = record.get("task_type", "youkai_hazard")
    required = REQUIRED_FIELDS.get(task_type, [])
    if all(field in parsed for field in required):
        result["schema_valid"] = True

    # キャラクター一貫性（youkai_hazardのみ）
    if task_type == "youkai_hazard" and "conversation" in parsed:
        convs = parsed["conversation"]
        if isinstance(convs, list):
            for conv in convs:
                speaker = conv.get("speaker", "")
                text = conv.get("text", "")
                if speaker in YOUKAI_FIRST_PERSON:
                    expected_fp = YOUKAI_FIRST_PERSON[speaker]
                    # 他の妖怪の一人称を使っていないかチェック
                    other_fps = [fp for sid, fp in YOUKAI_FIRST_PERSON.items() if sid != speaker and fp != expected_fp]
                    for ofp in other_fps:
                        if ofp in text:
                            result["character_ok"] = False
                            break

    return result


async def run_evaluation(args):
    """評価メイン処理"""
    # テストデータ読み込み
    print("=" * 60)
    print("モデル自動評価")
    print(f"テストデータ: {args.test_file}")
    print(f"API: {args.api_url}")
    print(f"並列数: {args.concurrency}")
    print(f"max_tokens: {args.max_tokens}" + (" (タスク別自動)" if args.max_tokens == 0 else ""))
    if args.task_type:
        print(f"フィルタ: {args.task_type}")
    if args.failure_log:
        print(f"失敗ログ: {args.failure_log}")
    print("=" * 60)

    records = []
    with open(args.test_file, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                records.append(json.loads(line))

    # task_typeフィルタ
    if args.task_type:
        records = [r for r in records if r.get("task_type") == args.task_type]

    if args.limit:
        records = records[:args.limit]

    print(f"\n評価対象: {len(records):,}件")

    # モデル名取得
    async with aiohttp.ClientSession() as session:
        async with session.get(f"{args.api_url}/models") as resp:
            models_data = await resp.json()
            model_name = models_data["data"][0]["id"]
    print(f"モデル: {model_name}")

    # 評価実行
    semaphore = asyncio.Semaphore(args.concurrency)
    results_by_type = defaultdict(list)
    failure_counts = Counter()
    failure_log_entries = []
    total_tokens = 0
    total_time = 0.0
    errors = 0

    print(f"\n推論中...")

    async with aiohttp.ClientSession() as session:
        batch_size = 100
        for batch_start in range(0, len(records), batch_size):
            batch = records[batch_start:batch_start + batch_size]
            tasks = []
            for record in batch:
                messages = build_messages(record)
                # max_tokens決定: コマンドライン指定 > 0ならそれを使う、0ならtask_type別デフォルト
                task_type = record.get("task_type", "youkai_hazard")
                if args.max_tokens > 0:
                    mt = args.max_tokens
                else:
                    mt = MAX_TOKENS_BY_TYPE.get(task_type, 512)
                tasks.append(call_api(
                    session, args.api_url, model_name, messages, semaphore,
                    max_tokens=mt, json_mode=args.json_mode,
                ))

            responses = await asyncio.gather(*tasks)

            for record, (content, elapsed, tokens) in zip(batch, responses):
                task_type = record.get("task_type", "unknown")
                if content is None:
                    errors += 1
                    results_by_type[task_type].append({
                        "json_valid": False, "schema_valid": False,
                        "no_forbidden": True, "character_ok": True,
                    })
                    failure_counts["api_error"] += 1
                    if args.failure_log:
                        failure_log_entries.append({
                            "task_type": task_type,
                            "failure_type": "api_error",
                            "content": None,
                            "instruction": record.get("instruction", "")[:200],
                        })
                    continue

                total_tokens += tokens
                total_time += elapsed
                eval_result = evaluate_response(content, record)
                results_by_type[task_type].append(eval_result)

                # 失敗時のログ記録
                if not eval_result["json_valid"] or not eval_result["schema_valid"]:
                    failure_type = classify_failure(content, record)
                    failure_counts[failure_type] += 1
                    if args.failure_log:
                        failure_log_entries.append({
                            "task_type": task_type,
                            "failure_type": failure_type,
                            "json_valid": eval_result["json_valid"],
                            "schema_valid": eval_result["schema_valid"],
                            "content_length": len(content),
                            "content": content[:2000],
                            "instruction": record.get("instruction", "")[:200],
                        })

            done = min(batch_start + batch_size, len(records))
            print(f"  {done:>6,} / {len(records):,} ({done/len(records)*100:.1f}%)")

    # 結果集計
    print("\n" + "=" * 60)
    print("評価結果")
    print("=" * 60)

    overall = {"json_valid": 0, "schema_valid": 0, "no_forbidden": 0, "character_ok": 0, "total": 0}
    type_summaries = {}

    for task_type in sorted(results_by_type.keys()):
        items = results_by_type[task_type]
        n = len(items)
        summary = {
            "count": n,
            "json_valid": sum(1 for r in items if r["json_valid"]),
            "schema_valid": sum(1 for r in items if r["schema_valid"]),
            "no_forbidden": sum(1 for r in items if r["no_forbidden"]),
            "character_ok": sum(1 for r in items if r["character_ok"]),
        }
        type_summaries[task_type] = summary

        overall["total"] += n
        overall["json_valid"] += summary["json_valid"]
        overall["schema_valid"] += summary["schema_valid"]
        overall["no_forbidden"] += summary["no_forbidden"]
        overall["character_ok"] += summary["character_ok"]

        print(f"\n--- {task_type} ({n:,}件) ---")
        print(f"  JSON生成成功率:    {summary['json_valid']/n*100:6.2f}%  ({summary['json_valid']:,}/{n:,})")
        print(f"  スキーマ準拠率:    {summary['schema_valid']/n*100:6.2f}%  ({summary['schema_valid']:,}/{n:,})")
        print(f"  禁止表現回避率:    {summary['no_forbidden']/n*100:6.2f}%  ({summary['no_forbidden']:,}/{n:,})")
        if task_type == "youkai_hazard":
            print(f"  キャラクター一貫性: {summary['character_ok']/n*100:6.2f}%  ({summary['character_ok']:,}/{n:,})")

    n_total = overall["total"]
    print(f"\n{'='*60}")
    print(f"全体サマリー ({n_total:,}件, エラー: {errors}件)")
    print(f"{'='*60}")
    print(f"  JSON生成成功率:    {overall['json_valid']/n_total*100:6.2f}%")
    print(f"  スキーマ準拠率:    {overall['schema_valid']/n_total*100:6.2f}%")
    print(f"  禁止表現回避率:    {overall['no_forbidden']/n_total*100:6.2f}%")
    print(f"  キャラクター一貫性: {overall['character_ok']/n_total*100:6.2f}%")
    if total_time > 0:
        print(f"  平均応答速度:      {total_tokens/total_time:.1f} tokens/sec")
        print(f"  合計トークン数:    {total_tokens:,}")
        print(f"  合計推論時間:      {total_time/3600:.1f}時間")

    # 失敗パターン分析
    if failure_counts:
        print(f"\n{'='*60}")
        print("失敗パターン分析")
        print(f"{'='*60}")
        for ftype, count in failure_counts.most_common():
            label = {
                "truncated": "(A) トランケーション（JSON途中切れ）",
                "markdown_wrapped": "(B) マークダウンフェンス付き",
                "syntax_error": "(C) JSON構文エラー",
                "schema_violation": "(D) スキーマ違反（フィールド欠落）",
                "api_error": "(E) APIエラー",
                "unknown": "(?) 不明",
            }.get(ftype, ftype)
            print(f"  {label}: {count}件")

    # 失敗ログ保存
    if args.failure_log and failure_log_entries:
        failure_log_path = Path(args.failure_log)
        failure_log_path.parent.mkdir(parents=True, exist_ok=True)
        with open(failure_log_path, "w", encoding="utf-8") as f:
            for entry in failure_log_entries:
                f.write(json.dumps(entry, ensure_ascii=False) + "\n")
        print(f"\n失敗ログ保存: {args.failure_log} ({len(failure_log_entries)}件)")

    # 結果保存
    if args.output:
        output_path = Path(args.output)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        result_data = {
            "test_file": args.test_file,
            "model": model_name,
            "total_records": n_total,
            "errors": errors,
            "max_tokens": args.max_tokens if args.max_tokens > 0 else "auto",
            "task_type_filter": args.task_type,
            "json_mode": args.json_mode,
            "overall": {k: v / n_total * 100 if k != "total" else v for k, v in overall.items()},
            "by_task_type": type_summaries,
            "failure_patterns": dict(failure_counts) if failure_counts else {},
            "performance": {
                "total_tokens": total_tokens,
                "total_time_sec": round(total_time, 1),
                "tokens_per_sec": round(total_tokens / total_time, 1) if total_time > 0 else 0,
            },
        }
        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(result_data, f, ensure_ascii=False, indent=2)
        print(f"\n結果保存: {args.output}")


def main():
    parser = argparse.ArgumentParser(description="モデル自動評価")
    parser.add_argument("--test-file", required=True, help="テストデータJSONLファイル")
    parser.add_argument("--api-url", default="http://localhost:8001/v1", help="vLLM APIのURL")
    parser.add_argument("--output", default=None, help="結果出力先JSONファイル")
    parser.add_argument("--concurrency", type=int, default=8, help="並列リクエスト数")
    parser.add_argument("--limit", type=int, default=None, help="評価件数の上限（デバッグ用）")
    parser.add_argument("--max-tokens", type=int, default=0,
                        help="max_tokens値（0=task_type別自動: youkai_hazard=1024, 他=512）")
    parser.add_argument("--task-type", default=None,
                        help="特定のtask_typeのみ評価（例: youkai_hazard）")
    parser.add_argument("--failure-log", default=None,
                        help="失敗レスポンスのログ出力先JSONLファイル")
    parser.add_argument("--json-mode", action="store_true",
                        help="vLLMのJSON構造化出力モード（response_format: json_object）を有効化")
    args = parser.parse_args()

    asyncio.run(run_evaluation(args))


if __name__ == "__main__":
    main()
