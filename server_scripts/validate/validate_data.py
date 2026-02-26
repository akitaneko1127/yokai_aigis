#!/usr/bin/env python3
"""
教師データ品質検証スクリプト
生成データのJSON妥当性、禁止表現、必須フィールドをチェック

使用方法:
  python validate_data.py --input /path/to/data/raw/ --config ../configs/generation_config.yaml
"""

import argparse
import json
import re
import sys
from collections import Counter, defaultdict
from pathlib import Path

import yaml


def load_config(config_path: str) -> dict:
    with open(config_path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)


def check_forbidden_expressions(text: str, forbidden_list: list[str]) -> list[str]:
    """禁止表現の検出"""
    found = []
    for expr in forbidden_list:
        if expr in text:
            found.append(expr)
    return found


def check_character_consistency(data: dict, youkai_config: dict) -> list[str]:
    """キャラクター一致チェック"""
    issues = []
    output = data.get("output", {})
    if isinstance(output, str):
        return issues

    conversations = output.get("conversation", [])
    for conv in conversations:
        speaker = conv.get("speaker", "")
        text = conv.get("text", "")

        if speaker in youkai_config:
            yconf = youkai_config[speaker]
            first_person = yconf["first_person"]
            # 一人称チェック（他の妖怪の一人称を使っていないか）
            other_fps = [
                yc["first_person"]
                for yid, yc in youkai_config.items()
                if yid != speaker and yc["first_person"] != first_person
            ]
            for ofp in other_fps:
                if ofp in text and ofp not in first_person:
                    issues.append(f"{speaker}が他の妖怪の一人称「{ofp}」を使用")

    return issues


def validate_single(data: dict, config: dict) -> dict:
    """1件のデータを検証"""
    result = {
        "valid": True,
        "errors": [],
        "warnings": [],
    }

    # 1. 必須フィールド
    for field in ["task_type", "instruction"]:
        if field not in data:
            result["errors"].append(f"必須フィールド欠落: {field}")
            result["valid"] = False

    # input/output
    if "input" not in data and "output" not in data:
        result["errors"].append("input または output フィールドが必要")
        result["valid"] = False

    # 2. task_type の妥当性
    valid_types = ["youkai_hazard", "evacuation_qa", "route_guidance", "disaster_scenario", "local_info"]
    if data.get("task_type") not in valid_types:
        result["errors"].append(f"不正なtask_type: {data.get('task_type')}")
        result["valid"] = False

    # 3. 禁止表現
    text = json.dumps(data, ensure_ascii=False)
    forbidden = config.get("quality", {}).get("forbidden_expressions", [])
    found = check_forbidden_expressions(text, forbidden)
    if found:
        result["errors"].append(f"禁止表現: {', '.join(found)}")
        result["valid"] = False

    # 4. 文字数チェック（会話テキスト）
    output = data.get("output", {})
    if isinstance(output, dict):
        conversations = output.get("conversation", [])
        for i, conv in enumerate(conversations):
            text_content = conv.get("text", "")
            if len(text_content) < 10:
                result["warnings"].append(f"会話{i}: テキストが短すぎます ({len(text_content)}文字)")
            elif len(text_content) > 600:
                result["warnings"].append(f"会話{i}: テキストが長すぎます ({len(text_content)}文字)")

    # 5. キャラクター一致（youkai_hazardのみ）
    if data.get("task_type") == "youkai_hazard":
        char_issues = check_character_consistency(data, config.get("youkai", {}))
        for issue in char_issues:
            result["warnings"].append(f"キャラクター不一致: {issue}")

    # 6. emotionフィールド
    valid_emotions = [
        "friendly", "teaching", "thinking", "suggesting", "reassuring",
        "warm", "calm", "serious", "warning", "hopeful", "supportive",
    ]
    if isinstance(output, dict):
        for conv in output.get("conversation", []):
            emotion = conv.get("emotion", "")
            if emotion and emotion not in valid_emotions:
                result["warnings"].append(f"不明なemotion: {emotion}")

    return result


def validate_file(file_path: Path, config: dict) -> dict:
    """1ファイル分を検証"""
    stats = {
        "file": str(file_path),
        "total": 0,
        "valid": 0,
        "invalid": 0,
        "parse_errors": 0,
        "warnings_count": 0,
        "task_type_dist": Counter(),
        "error_types": Counter(),
        "sample_errors": [],
    }

    with open(file_path, "r", encoding="utf-8") as f:
        for line_num, line in enumerate(f, 1):
            line = line.strip()
            if not line:
                continue

            stats["total"] += 1

            try:
                data = json.loads(line)
            except json.JSONDecodeError as e:
                stats["parse_errors"] += 1
                stats["invalid"] += 1
                if len(stats["sample_errors"]) < 10:
                    stats["sample_errors"].append(f"Line {line_num}: JSONパースエラー: {e}")
                continue

            result = validate_single(data, config)
            stats["task_type_dist"][data.get("task_type", "unknown")] += 1

            if result["valid"]:
                stats["valid"] += 1
            else:
                stats["invalid"] += 1
                for err in result["errors"]:
                    stats["error_types"][err.split(":")[0]] += 1
                if len(stats["sample_errors"]) < 10:
                    stats["sample_errors"].append(f"Line {line_num}: {'; '.join(result['errors'])}")

            stats["warnings_count"] += len(result["warnings"])

    return stats


def main():
    parser = argparse.ArgumentParser(description="教師データ品質検証")
    parser.add_argument("--input", required=True, help="検証対象ディレクトリ")
    parser.add_argument("--config", required=True, help="設定ファイルパス")
    args = parser.parse_args()

    config = load_config(args.config)
    input_dir = Path(args.input)

    jsonl_files = sorted(input_dir.glob("*.jsonl"))
    if not jsonl_files:
        print(f"[ERROR] JSONLファイルが見つかりません: {input_dir}")
        sys.exit(1)

    print("=" * 70)
    print("妖怪ハザードマップ 教師データ品質検証")
    print(f"対象: {input_dir}")
    print(f"ファイル数: {len(jsonl_files)}")
    print("=" * 70)

    grand_stats = {
        "total_files": len(jsonl_files),
        "total_records": 0,
        "total_valid": 0,
        "total_invalid": 0,
        "total_parse_errors": 0,
        "task_type_dist": Counter(),
        "all_errors": [],
    }

    for fpath in jsonl_files:
        print(f"\n--- {fpath.name} ---")
        stats = validate_file(fpath, config)

        print(f"  総数: {stats['total']}")
        print(f"  有効: {stats['valid']} ({stats['valid']/max(stats['total'],1)*100:.1f}%)")
        print(f"  無効: {stats['invalid']}")
        print(f"  パースエラー: {stats['parse_errors']}")
        print(f"  警告: {stats['warnings_count']}")

        if stats["task_type_dist"]:
            print(f"  task_type分布: {dict(stats['task_type_dist'])}")

        if stats["error_types"]:
            print(f"  エラー種別: {dict(stats['error_types'])}")

        if stats["sample_errors"]:
            print("  サンプルエラー:")
            for err in stats["sample_errors"][:5]:
                print(f"    - {err}")

        grand_stats["total_records"] += stats["total"]
        grand_stats["total_valid"] += stats["valid"]
        grand_stats["total_invalid"] += stats["invalid"]
        grand_stats["total_parse_errors"] += stats["parse_errors"]
        grand_stats["task_type_dist"] += stats["task_type_dist"]

    # サマリー
    print(f"\n{'='*70}")
    print("全体サマリー")
    print(f"{'='*70}")
    print(f"ファイル数: {grand_stats['total_files']}")
    print(f"総レコード数: {grand_stats['total_records']:,}")
    print(f"有効: {grand_stats['total_valid']:,} ({grand_stats['total_valid']/max(grand_stats['total_records'],1)*100:.1f}%)")
    print(f"無効: {grand_stats['total_invalid']:,}")
    print(f"パースエラー: {grand_stats['total_parse_errors']:,}")
    print(f"\ntask_type分布:")
    for tt, count in sorted(grand_stats["task_type_dist"].items()):
        print(f"  {tt}: {count:,}")

    target = 142000
    print(f"\n目標件数: {target:,}")
    print(f"達成率: {grand_stats['total_valid']/target*100:.1f}%")
    remaining = target - grand_stats["total_valid"]
    if remaining > 0:
        print(f"残り: {remaining:,}件")
    else:
        print("目標達成!")


if __name__ == "__main__":
    main()
