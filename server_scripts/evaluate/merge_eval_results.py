#!/usr/bin/env python3
"""
分割評価結果を統合するスクリプト

使用方法:
  python merge_eval_results.py \
    --parts ~/youkai-hazard/evaluation/eval_part1.json \
           ~/youkai-hazard/evaluation/eval_part2.json \
           ~/youkai-hazard/evaluation/eval_part3.json \
    --output ~/youkai-hazard/evaluation/eval_results.json
"""

import argparse
import json
from pathlib import Path


def merge_results(part_files, output_file):
    parts = []
    for f in part_files:
        with open(f, "r", encoding="utf-8") as fh:
            parts.append(json.load(fh))

    total_records = sum(p["total_records"] for p in parts)
    total_errors = sum(p["errors"] for p in parts)

    # task_type別の集計をマージ
    merged_by_type = {}
    for p in parts:
        for task_type, stats in p["by_task_type"].items():
            if task_type not in merged_by_type:
                merged_by_type[task_type] = {
                    "count": 0, "json_valid": 0, "schema_valid": 0,
                    "no_forbidden": 0, "character_ok": 0,
                }
            for key in ["count", "json_valid", "schema_valid", "no_forbidden", "character_ok"]:
                merged_by_type[task_type][key] += stats[key]

    # overall集計
    overall = {"total": total_records, "json_valid": 0, "schema_valid": 0, "no_forbidden": 0, "character_ok": 0}
    for stats in merged_by_type.values():
        overall["json_valid"] += stats["json_valid"]
        overall["schema_valid"] += stats["schema_valid"]
        overall["no_forbidden"] += stats["no_forbidden"]
        overall["character_ok"] += stats["character_ok"]

    # パフォーマンス集計
    total_tokens = sum(p["performance"]["total_tokens"] for p in parts)
    total_time = sum(p["performance"]["total_time_sec"] for p in parts)

    # 結果出力
    print("=" * 60)
    print(f"統合評価結果 ({total_records:,}件, エラー: {total_errors}件)")
    print("=" * 60)

    for task_type in sorted(merged_by_type.keys()):
        s = merged_by_type[task_type]
        n = s["count"]
        print(f"\n--- {task_type} ({n:,}件) ---")
        print(f"  JSON生成成功率:    {s['json_valid']/n*100:6.2f}%  ({s['json_valid']:,}/{n:,})")
        print(f"  スキーマ準拠率:    {s['schema_valid']/n*100:6.2f}%  ({s['schema_valid']:,}/{n:,})")
        print(f"  禁止表現回避率:    {s['no_forbidden']/n*100:6.2f}%  ({s['no_forbidden']:,}/{n:,})")
        if task_type == "youkai_hazard":
            print(f"  キャラクター一貫性: {s['character_ok']/n*100:6.2f}%  ({s['character_ok']:,}/{n:,})")

    print(f"\n{'='*60}")
    print(f"全体サマリー")
    print(f"{'='*60}")
    n = total_records
    print(f"  JSON生成成功率:    {overall['json_valid']/n*100:6.2f}%")
    print(f"  スキーマ準拠率:    {overall['schema_valid']/n*100:6.2f}%")
    print(f"  禁止表現回避率:    {overall['no_forbidden']/n*100:6.2f}%")
    print(f"  キャラクター一貫性: {overall['character_ok']/n*100:6.2f}%")
    if total_time > 0:
        print(f"  平均応答速度:      {total_tokens/total_time:.1f} tokens/sec")
        print(f"  合計トークン数:    {total_tokens:,}")
        print(f"  合計推論時間:      {total_time/3600:.1f}時間")

    # JSON保存
    result_data = {
        "test_file": "merged (test_part1 + test_part2 + test_part3)",
        "model": parts[0]["model"],
        "total_records": total_records,
        "errors": total_errors,
        "overall": {k: v / n * 100 if k != "total" else v for k, v in overall.items()},
        "by_task_type": merged_by_type,
        "performance": {
            "total_tokens": total_tokens,
            "total_time_sec": round(total_time, 1),
            "tokens_per_sec": round(total_tokens / total_time, 1) if total_time > 0 else 0,
        },
    }

    output_path = Path(output_file)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(result_data, f, ensure_ascii=False, indent=2)
    print(f"\n結果保存: {output_file}")


def main():
    parser = argparse.ArgumentParser(description="分割評価結果の統合")
    parser.add_argument("--parts", nargs="+", required=True, help="分割結果JSONファイル")
    parser.add_argument("--output", required=True, help="統合結果の出力先")
    args = parser.parse_args()
    merge_results(args.parts, args.output)


if __name__ == "__main__":
    main()
