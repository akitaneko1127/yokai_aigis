#!/usr/bin/env python3
"""
教師データ train/val/test 分割スクリプト
task_typeごとの層化抽出で8:1:1に分割

使用方法:
  python split_data.py --input ~/youkai-hazard/data/raw/ --output ~/youkai-hazard/data/cleaned/
  python split_data.py --input ~/youkai-hazard/data/raw/ --output ~/youkai-hazard/data/cleaned/ --seed 42
"""

import argparse
import json
import random
import sys
from collections import Counter, defaultdict
from pathlib import Path


def load_all_records(input_dir: str) -> list[dict]:
    """rawディレクトリの全JSONLファイルを読み込む"""
    records = []
    input_path = Path(input_dir)
    files = sorted(input_path.glob("*.jsonl"))

    if not files:
        print(f"エラー: {input_dir} にJSONLファイルが見つかりません", file=sys.stderr)
        sys.exit(1)

    for f in files:
        count = 0
        with open(f, "r", encoding="utf-8") as fh:
            for line_num, line in enumerate(fh, 1):
                line = line.strip()
                if not line:
                    continue
                try:
                    record = json.loads(line)
                    records.append(record)
                    count += 1
                except json.JSONDecodeError as e:
                    print(f"警告: {f.name} 行{line_num}: JSONパースエラー ({e})", file=sys.stderr)
        print(f"  読み込み: {count:>8,}件  {f.name}")

    return records


def stratified_split(
    records: list[dict],
    train_ratio: float = 0.8,
    val_ratio: float = 0.1,
    seed: int = 42,
) -> tuple[list[dict], list[dict], list[dict]]:
    """task_typeごとに層化抽出して分割"""
    rng = random.Random(seed)

    # task_typeでグループ化
    groups: dict[str, list[dict]] = defaultdict(list)
    for record in records:
        task_type = record.get("task_type", "unknown")
        groups[task_type].append(record)

    train_set, val_set, test_set = [], [], []

    for task_type in sorted(groups.keys()):
        group = groups[task_type]
        rng.shuffle(group)

        n = len(group)
        n_train = int(n * train_ratio)
        n_val = int(n * val_ratio)
        # 残りはtest（端数調整）

        train_set.extend(group[:n_train])
        val_set.extend(group[n_train : n_train + n_val])
        test_set.extend(group[n_train + n_val :])

    # 各セット内もシャッフル（task_type間の順序を混ぜる）
    rng.shuffle(train_set)
    rng.shuffle(val_set)
    rng.shuffle(test_set)

    return train_set, val_set, test_set


def save_jsonl(records: list[dict], output_path: Path) -> None:
    """JSONL形式で保存"""
    with open(output_path, "w", encoding="utf-8") as f:
        for record in records:
            f.write(json.dumps(record, ensure_ascii=False) + "\n")


def print_distribution(name: str, records: list[dict]) -> None:
    """task_type分布を表示"""
    counter = Counter(r.get("task_type", "unknown") for r in records)
    print(f"\n  {name} ({len(records):,}件):")
    for task_type, count in sorted(counter.items()):
        pct = count / len(records) * 100 if records else 0
        print(f"    {task_type:<25s} {count:>8,}  ({pct:5.1f}%)")


def main():
    parser = argparse.ArgumentParser(description="教師データ train/val/test 分割")
    parser.add_argument("--input", required=True, help="入力ディレクトリ（raw/）")
    parser.add_argument("--output", required=True, help="出力ディレクトリ（cleaned/）")
    parser.add_argument("--train-ratio", type=float, default=0.8, help="訓練データ比率 (default: 0.8)")
    parser.add_argument("--val-ratio", type=float, default=0.1, help="検証データ比率 (default: 0.1)")
    parser.add_argument("--seed", type=int, default=42, help="乱数シード (default: 42)")
    args = parser.parse_args()

    # 比率チェック
    test_ratio = 1.0 - args.train_ratio - args.val_ratio
    if test_ratio < 0 or test_ratio > 1:
        print("エラー: train_ratio + val_ratio は1.0以下にしてください", file=sys.stderr)
        sys.exit(1)

    print("=" * 60)
    print("教師データ分割 (層化抽出)")
    print(f"入力: {args.input}")
    print(f"出力: {args.output}")
    print(f"比率: train={args.train_ratio} / val={args.val_ratio} / test={test_ratio:.1f}")
    print(f"シード: {args.seed}")
    print("=" * 60)

    # 読み込み
    print("\n[1/3] データ読み込み...")
    records = load_all_records(args.input)
    print(f"\n  合計: {len(records):,}件")

    # 分割
    print("\n[2/3] 層化抽出で分割中...")
    train, val, test = stratified_split(
        records,
        train_ratio=args.train_ratio,
        val_ratio=args.val_ratio,
        seed=args.seed,
    )

    # 分布表示
    print_distribution("train", train)
    print_distribution("val", val)
    print_distribution("test", test)

    # 保存
    print("\n[3/3] 保存中...")
    output_path = Path(args.output)
    output_path.mkdir(parents=True, exist_ok=True)

    save_jsonl(train, output_path / "train.jsonl")
    save_jsonl(val, output_path / "val.jsonl")
    save_jsonl(test, output_path / "test.jsonl")

    print(f"\n  train.jsonl: {len(train):>8,}件")
    print(f"  val.jsonl:   {len(val):>8,}件")
    print(f"  test.jsonl:  {len(test):>8,}件")
    print(f"  合計:        {len(train) + len(val) + len(test):>8,}件")

    # 検算
    print("\n" + "=" * 60)
    if len(train) + len(val) + len(test) == len(records):
        print("検算OK: 入力件数と出力件数が一致")
    else:
        print("警告: 入力件数と出力件数が不一致!", file=sys.stderr)
    print("=" * 60)


if __name__ == "__main__":
    main()
